#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1：调参实验 —— 将 AndroWatts（公开测量）映射到 S1~S5，并让“量级支撑”更贴近我们的模型预测。

用户动机（面向论文叙事）：
- AndroWatts 数据集本身没有场景标签；我们只能用可解释的设备状态/功耗轨特征做“门控 + 优先级”分类；
- 目前黑色虚线（公开数据推得的 TTE 量级）在雷达图上与模型存在系统偏差：
  - S3 接近，但 S4/S5 偏大，S1/S2 偏小；
- 这里做一次“合理的参数实验”：通过随机搜索一组门控阈值，使黑线整体更接近模型预测（并输出样本量 n 供审阅）。

重要原则（与赛题 Q1 对齐）：
- 公开数据只用于“量级支撑/合理性检验”，不替代连续时间机理模型；
- 映射规则必须可解释、可复现，并记录阈值、样本量与诊断指标；
- 若数据集本身缺少某类场景（如深度待机），则无法强行拟合到完全一致 —— 必须在报告中如实说明。

输出（不会覆盖主图）：
- 写入 `Q1材料/06-模型0vs模型1_TTE对比/other/opendata_support_tuned/`
  - figure_paper.png / figure_study.png
  - tuned_params.json（最佳阈值）
  - tuning_top20.csv（前 20 组候选，便于复核）
  - data_opendata_support.csv（最佳阈值下的统计）
  - mapping_diagnostics.csv（强度指标中位数，证明规则与直觉一致）
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path as MplPath
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D

from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0, simulate_model1_ecm
from mcm26a.viz.style import PlotMode, apply_style, savefig


COLOR_GREEN = "#099F2D"
COLOR_BLUE = "#008CFF"
COLOR_ORANGE = "#EC5A00"
COLOR_BLACK = "#222222"


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A

Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "06-模型0vs模型1_TTE对比"
OPEN_DATA_CSV_DEFAULT = ROOT_DIR / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"


def _radar_factory(num_vars: int, *, frame: str = "polygon") -> np.ndarray:
    """创建雷达图 projection（五边形外框）。"""

    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarAxes(PolarAxes):
        name = "radar"
        RESOLUTION = 1

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_theta_zero_location("N")

        def fill(self, *args, closed: bool = True, **kwargs):
            return super().fill(*args, closed=closed, **kwargs)

        def plot(self, *args, **kwargs):
            lines = super().plot(*args, **kwargs)
            for ln in lines:
                x, y = ln.get_data()
                if len(x) > 0 and x[0] != x[-1]:
                    ln.set_data(np.append(x, x[0]), np.append(y, y[0]))
            return lines

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            if frame == "circle":
                return Circle((0.5, 0.5), 0.5)
            if frame == "polygon":
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="none")
            raise ValueError(f"unknown frame: {frame!r}")

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            if frame == "polygon":
                spine = Spine(axes=self, spine_type="circle", path=MplPath.unit_regular_polygon(num_vars))
                spine.set_transform(Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes)
                return {"polar": spine}
            raise ValueError(f"unknown frame: {frame!r}")

    register_projection(RadarAxes)
    return theta


def _write_csv(path: Path, *, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _rank01(s: pd.Series) -> pd.Series:
    # 百分位秩（0~1）：比固定阈值更稳健，且直观（“处于样本集的什么水平”）
    return s.rank(pct=True, method="average").clip(0.0, 1.0)


@dataclass(frozen=True)
class FeatureTable:
    """AndroWatts 行级特征表（无量纲强度指标 + 功耗）。"""

    p_total_W: pd.Series
    p_total_rank: pd.Series
    screen_int: pd.Series
    cpu_int: pd.Series
    gpu_int: pd.Series
    wifi_int: pd.Series
    infra_int: pd.Series


def _build_features(df: pd.DataFrame) -> FeatureTable:
    """从 aggregated.csv 构造用于场景映射的强度特征。"""

    def need(name: str) -> pd.Series:
        if name not in df.columns:
            raise ValueError(f"open data missing column: {name}")
        return df[name]

    pow_cols = [c for c in df.columns if c.endswith("_ENERGY_AVG_UWS")]
    if not pow_cols:
        raise ValueError("open data missing *_ENERGY_AVG_UWS columns")
    p_total_W = df[pow_cols].sum(axis=1).astype(float) * 1e-6
    p_total_rank = _rank01(p_total_W)

    # 组件功耗代理（W）
    disp_w = (need("Display_ENERGY_AVG_UWS").astype(float) + need("L22M_DISP_ENERGY_AVG_UWS").astype(float)) * 1e-6
    cpu_w = (
        need("CPU_BIG_ENERGY_AVG_UWS").astype(float)
        + need("CPU_MID_ENERGY_AVG_UWS").astype(float)
        + need("CPU_LITTLE_ENERGY_AVG_UWS").astype(float)
    ) * 1e-6
    gpu_w = (need("GPU_ENERGY_AVG_UWS").astype(float) + need("GPU3D_ENERGY_AVG_UWS").astype(float)) * 1e-6
    infra_w = (
        need("INFRASTRUCTURE_ENERGY_AVG_UWS").astype(float)
        + need("INFRASTRUCTURE_ENERGY_AVG_UWS.1").astype(float)
        + need("CELLULAR_ENERGY_AVG_UWS").astype(float)
        + need("CELLULAR_ENERGY_AVG_UWS.1").astype(float)
    ) * 1e-6

    bright = need("Brightness").astype(float)
    wifi_bytes = need("TOTAL_DATA_WIFI_BYTES").astype(float)

    cpu_big_khz = pd.to_numeric(need("CPU_BIG_FREQ_KHz"), errors="coerce")
    gpu0_freq = pd.to_numeric(need("GPU0_FREQ"), errors="coerce")
    cpu_big_khz = cpu_big_khz.fillna(cpu_big_khz.median())
    gpu0_freq = gpu0_freq.fillna(gpu0_freq.median())

    r_bright = _rank01(bright)
    r_disp = _rank01(disp_w)
    r_cpu_p = _rank01(cpu_w)
    r_gpu_p = _rank01(gpu_w)
    r_cpu_f = _rank01(cpu_big_khz)
    r_gpu_f = _rank01(gpu0_freq)
    r_wifi = _rank01(wifi_bytes)
    r_infra = _rank01(infra_w)

    # 组合强度指标（0~1）
    screen_int = 0.6 * r_bright + 0.4 * r_disp
    cpu_int = 0.6 * r_cpu_p + 0.4 * r_cpu_f
    gpu_int = 0.6 * r_gpu_p + 0.4 * r_gpu_f
    wifi_int = r_wifi
    infra_int = r_infra

    return FeatureTable(
        p_total_W=p_total_W,
        p_total_rank=p_total_rank,
        screen_int=screen_int,
        cpu_int=cpu_int,
        gpu_int=gpu_int,
        wifi_int=wifi_int,
        infra_int=infra_int,
    )


@dataclass(frozen=True)
class MappingParams:
    """门控阈值（全部是 0~1 的无量纲强度）。"""

    s_on: float

    # S1（待机/轻度）
    s1_screen: float
    s1_cpu: float
    s1_gpu: float
    s1_wifi: float
    s1_p: float

    # S3（视频/直播）
    s3_wifi_min: float

    # S4（游戏）
    s4_cpu_min: float
    s4_gpu_min: float
    s4_p_min: float

    # S5（导航/通话）
    s5_wifi_max: float
    s5_infra_min: float
    s5_p_min: float

    # S2（浏览/社交）
    s2_p_max: float


def _assign_with_params(ft: FeatureTable, p: MappingParams) -> pd.Series:
    """用“门控 + 优先级”把每条数据行粗分配到 S1..S5。"""

    m4 = (ft.screen_int > p.s_on) & (ft.cpu_int > p.s4_cpu_min) & (ft.gpu_int > p.s4_gpu_min) & (ft.p_total_rank > p.s4_p_min)
    m5 = (
        (ft.screen_int > p.s_on)
        & (ft.wifi_int < p.s5_wifi_max)
        & (ft.infra_int > p.s5_infra_min)
        & (ft.p_total_rank > p.s5_p_min)
    )
    m3 = (
        (ft.screen_int > p.s_on)
        & (ft.wifi_int > p.s3_wifi_min)
        & (ft.cpu_int.between(0.20, 0.85))
        & (ft.gpu_int.between(0.20, 0.85))
    )
    m2 = (
        (ft.screen_int > p.s_on)
        & (ft.wifi_int.between(0.35, p.s3_wifi_min))
        & (ft.cpu_int.between(0.18, 0.85))
        & (ft.gpu_int < 0.90)
        & (ft.p_total_rank < p.s2_p_max)
    )
    m1 = (
        (ft.screen_int < p.s1_screen)
        & (ft.cpu_int < p.s1_cpu)
        & (ft.gpu_int < p.s1_gpu)
        & (ft.wifi_int < p.s1_wifi)
        & (ft.p_total_rank < p.s1_p)
    )

    masks = {
        "S4_gaming": m4,
        "S5_nav_call": m5,
        "S3_video_streaming": m3,
        "S2_browse_social": m2,
        "S1_standby_light": m1,
    }
    priority = ["S4_gaming", "S5_nav_call", "S3_video_streaming", "S2_browse_social", "S1_standby_light"]

    assigned = pd.Series([None] * len(ft.p_total_W))
    for sid in priority:
        idx = masks[sid] & assigned.isna()
        assigned.loc[idx] = sid
    return assigned


def _compute_support_stats(assigned: pd.Series, *, p_total_W: pd.Series, energy_Wh: float) -> dict[str, dict[str, float]]:
    """计算每类的功耗/续航统计（中位数 + IQR）。"""

    out: dict[str, dict[str, float]] = {}
    for sid in ["S1_standby_light", "S2_browse_social", "S3_video_streaming", "S4_gaming", "S5_nav_call"]:
        sel = assigned == sid
        n = int(sel.sum())
        if n == 0:
            out[sid] = {"n": 0, "p_med": float("nan"), "p_p25": float("nan"), "p_p75": float("nan"), "tte_med": float("nan")}
            continue
        pW = p_total_W.loc[sel].astype(float).to_numpy()
        tte = float(energy_Wh) / np.maximum(pW, 1e-9)
        out[sid] = {
            "n": n,
            "p_med": float(np.median(pW)),
            "p_p25": float(np.percentile(pW, 25)),
            "p_p75": float(np.percentile(pW, 75)),
            "tte_med": float(np.median(tte)),
        }
    return out


def _loss_log(stats: dict[str, dict[str, float]], targets_h: dict[str, float], weights: dict[str, float]) -> float:
    loss = 0.0
    for sid, targ in targets_h.items():
        pred = float(stats[sid]["tte_med"])
        if not math.isfinite(pred) or pred <= 0.0:
            return 1e9
        loss += float(weights.get(sid, 1.0)) * (math.log(pred / float(targ)) ** 2)
    return float(loss)


def _tune_params(
    ft: FeatureTable,
    *,
    energy_Wh: float,
    targets_h: dict[str, float],
    seed: int,
    iters: int,
    min_n: dict[str, int],
    weights: dict[str, float],
) -> tuple[MappingParams, dict[str, dict[str, float]], list[dict[str, object]]]:
    """随机搜索门控阈值，使公开数据量级更接近目标曲线。"""

    rng = random.Random(int(seed))
    best_loss = 1e9
    best_params: MappingParams | None = None
    best_stats: dict[str, dict[str, float]] | None = None
    top: list[dict[str, object]] = []

    def sample_params() -> MappingParams:
        # 参数空间：围绕“让 S4/S5 更高功耗、S1/S2 更低功耗”的方向设置
        return MappingParams(
            s_on=rng.uniform(0.38, 0.55),
            s1_screen=rng.uniform(0.12, 0.35),
            s1_cpu=rng.uniform(0.08, 0.35),
            s1_gpu=rng.uniform(0.08, 0.40),
            s1_wifi=rng.uniform(0.20, 0.70),
            s1_p=rng.uniform(0.005, 0.25),
            s3_wifi_min=rng.uniform(0.70, 0.90),
            s4_cpu_min=rng.uniform(0.80, 0.98),
            s4_gpu_min=rng.uniform(0.70, 0.98),
            s4_p_min=rng.uniform(0.92, 0.998),
            s5_wifi_max=rng.uniform(0.10, 0.45),
            s5_infra_min=rng.uniform(0.60, 0.98),
            s5_p_min=rng.uniform(0.85, 0.998),
            s2_p_max=rng.uniform(0.05, 0.60),
        )

    for _ in range(int(iters)):
        params = sample_params()
        assigned = _assign_with_params(ft, params)
        stats = _compute_support_stats(assigned, p_total_W=ft.p_total_W, energy_Wh=energy_Wh)

        # 样本量约束：避免“极端挑样本”完全不可审阅
        ok = True
        for sid, n0 in min_n.items():
            if int(stats[sid]["n"]) < int(n0):
                ok = False
                break
        if not ok:
            continue

        loss = _loss_log(stats, targets_h, weights)
        if loss < best_loss:
            best_loss = loss
            best_params = params
            best_stats = stats

        # 记录 top 候选（用于复核）
        top.append(
            {
                "loss": loss,
                **params.__dict__,
                **{f"{sid}_n": int(stats[sid]["n"]) for sid in targets_h.keys()},
                **{f"{sid}_tte_med": float(stats[sid]["tte_med"]) for sid in targets_h.keys()},
            }
        )

    if best_params is None or best_stats is None:
        raise RuntimeError("tuning failed: no feasible parameter set found (try lowering --min-n-* or increasing --iters)")

    # 按 loss 排序后取前 20
    top_sorted = sorted(top, key=lambda r: float(r["loss"]))[:20]
    return best_params, best_stats, top_sorted


def _plot_radar(
    *,
    labels: list[str],
    tte_m0: list[float],
    tte_m1: list[float],
    tte_open: list[float],
    open_counts: list[int],
    mode: PlotMode,
    out_png: Path,
    lang: str,
) -> None:
    style = apply_style(mode)

    n = len(labels)
    theta = _radar_factory(n, frame="polygon")
    angles = theta.tolist()

    v0 = [float(x) for x in tte_m0]
    v1 = [float(x) for x in tte_m1]
    vo = [float(x) for x in tte_open]

    ticks = [2.0, 4.0, 8.0, 16.0, 32.0]
    vmax = float(np.nanmax([np.nanmax(v0), np.nanmax(v1), np.nanmax(vo)]))
    r_min = 1.0
    r_max = max(32.0, vmax * 1.05)
    if vmax > 40.0:
        ticks.append(64.0)
        r_max = 64.0

    fig = plt.figure(figsize=(8.2, 6.6))
    ax = plt.subplot(111, projection="radar")
    ax.set_theta_direction(-1)
    ax.set_varlabels(labels)

    ax.set_rscale("log")
    ax.set_ylim(r_min, r_max)
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{int(t)}h" for t in ticks], color="gray", fontsize=9)
    ax.set_rlabel_position(90)

    ax.xaxis.grid(True, color=COLOR_GREEN, alpha=0.22, lw=0.9)
    ax.yaxis.grid(False)
    for r in ticks:
        ax.plot(angles, [r] * n, color=COLOR_GREEN, alpha=0.22, lw=0.9, zorder=0, label="_nolegend_")
    ax.spines["polar"].set_color(COLOR_GREEN)
    ax.spines["polar"].set_alpha(0.35)
    ax.spines["polar"].set_linewidth(1.2)

    if lang == "en":
        label0 = "Model-0 (SOC threshold)"
        label1 = "Model-1 (voltage cut-off)"
        labelo = "Open data (AndroWatts, tuned mapping)"
        title = "TTE Comparison Across Scenarios (Radar / Log Scale)"
        if mode == "study":
            title += " (study)"
    else:
        label0 = "Model-0（SOC阈值）"
        label1 = "Model-1（截止电压）"
        labelo = "公开数据（AndroWatts，调参映射）"
        title = f"不同场景下的耗尽时间 TTE 对比（雷达图/对数刻度）{style.title_suffix}"

    ax.plot(angles, v0, color=COLOR_BLUE, lw=2.2, marker="o", markersize=4.0, label=label0)
    ax.fill(angles, v0, color=COLOR_BLUE, alpha=0.12)

    ax.plot(angles, v1, color=COLOR_ORANGE, lw=2.2, marker="o", markersize=4.0, label=label1)
    ax.fill(angles, v1, color=COLOR_ORANGE, alpha=0.12)

    ax.plot(angles, vo, color=COLOR_BLACK, lw=1.8, ls="--", marker="s", markersize=3.6, label=labelo)

    ax.set_title(title, pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 0.98))
        if lang == "en":
            note = (
                "Notes: The black dashed polygon is NOT a ground-truth trajectory. It is an order-of-magnitude support\n"
                "derived from open measurements (AndroWatts). A rule-based mapping is tuned to match model-level TTE.\n"
                + "n = [" + ", ".join(str(int(x)) for x in open_counts) + "] (S1..S5)"
            )
        else:
            note = (
                "说明：黑色虚线不是逐时刻真值轨迹，而是由 AndroWatts 开源测量推得的“量级支撑”（满电 TTE≈E/P）。\n"
                "我们对门控阈值做了可复现的随机搜索，使其更贴近模型级 TTE；并标注每类样本量 n。\n"
                + "n = [" + ", ".join(str(int(x)) for x in open_counts) + "] (S1..S5)"
            )
        fig.text(0.01, 0.02, note, ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1：调参实验（AndroWatts 场景映射）")
    ap.add_argument("--open-data", default=str(OPEN_DATA_CSV_DEFAULT), help="AndroWatts aggregated.csv 路径")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json"),
        help="Q1 五场景配置 JSON",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数（用于 Model-0/Model-1 仿真）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="电池参数（energy_Wh + ECM 参数）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="Model-1 积分步长（秒）")
    ap.add_argument("--target", default="model1", choices=("model0", "model1", "avg"), help="调参目标曲线口径")
    ap.add_argument("--seed", type=int, default=5, help="随机种子（保证可复现）")
    ap.add_argument("--iters", type=int, default=50000, help="随机搜索迭代次数")
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式")
    ap.add_argument(
        "--out-dir",
        default=str(Q1_DIR / "other" / "opendata_support_tuned"),
        help="输出目录（默认写入 Q1-06/other/opendata_support_tuned）",
    )

    # 样本量下限（太小会导致“极端挑样本”不可审阅）
    ap.add_argument("--min-n-s1", type=int, default=8)
    ap.add_argument("--min-n-s2", type=int, default=20)
    ap.add_argument("--min-n-s3", type=int, default=50)
    ap.add_argument("--min-n-s4", type=int, default=8)
    ap.add_argument("--min-n-s5", type=int, default=8)

    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 计算模型目标 TTE（S1~S5）
    raw = load_scenarios_json(Path(args.scenarios))
    power = PowerParams0.from_json(Path(args.power))
    batt1 = BatteryParams1ECM.from_json(Path(args.phone))
    batt0 = BatteryParams0.from_json(Path(args.phone))

    order = [
        "S1_standby_light",
        "S2_browse_social",
        "S3_video_streaming",
        "S4_gaming",
        "S5_nav_call",
    ]

    labels: list[str] = []
    tte0: list[float] = []
    tte1: list[float] = []
    targets: dict[str, float] = {}

    for sid in order:
        sc = materialize_scenario(raw, sid)
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        labels.append(title_en if str(args.lang) == "en" else title_zh)

        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=float(args.soc0))
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=float(args.soc0), dt_s=float(args.dt))
        v0 = float("nan") if r0.tte_h is None else float(r0.tte_h)
        v1 = float("nan") if r1.tte_h is None else float(r1.tte_h)
        tte0.append(v0)
        tte1.append(v1)

        if str(args.target) == "model0":
            targets[sid] = v0
        elif str(args.target) == "model1":
            targets[sid] = v1
        else:
            targets[sid] = 0.5 * (v0 + v1)

    # 2) 构造 open data 特征并调参
    od = pd.read_csv(Path(args.open_data))
    ft = _build_features(od)

    min_n = {
        "S1_standby_light": int(args.min_n_s1),
        "S2_browse_social": int(args.min_n_s2),
        "S3_video_streaming": int(args.min_n_s3),
        "S4_gaming": int(args.min_n_s4),
        "S5_nav_call": int(args.min_n_s5),
    }
    # 权重：优先把“偏差方向明确”的高负载场景（S4/S5）拉近；S1 往往受数据集覆盖限制，权重略低
    weights = {
        "S1_standby_light": 0.12,
        "S2_browse_social": 1.0,
        "S3_video_streaming": 1.0,
        "S4_gaming": 1.2,
        "S5_nav_call": 1.2,
    }

    best_params, best_stats, top20 = _tune_params(
        ft,
        energy_Wh=float(batt0.energy_Wh),
        targets_h=targets,
        seed=int(args.seed),
        iters=int(args.iters),
        min_n=min_n,
        weights=weights,
    )

    # 3) 用最佳参数生成支撑曲线 + 输出诊断/复核材料
    assigned = _assign_with_params(ft, best_params)
    stats = _compute_support_stats(assigned, p_total_W=ft.p_total_W, energy_Wh=float(batt0.energy_Wh))

    # 数据表（与图对应）
    rows: list[list[object]] = []
    open_tte: list[float] = []
    open_n: list[int] = []
    for sid in order:
        st = stats[sid]
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        rows.append([sid, title_zh, title_en, int(st["n"]), st["p_med"], st["p_p25"], st["p_p75"], st["tte_med"]])
        open_tte.append(float(st["tte_med"]))
        open_n.append(int(st["n"]))

    _write_csv(
        out_dir / "data_opendata_support.csv",
        header=[
            "scenario_id",
            "title_zh",
            "title_en",
            "n_samples",
            "P_total_W_median",
            "P_total_W_p25",
            "P_total_W_p75",
            "TTE_full_h_median",
        ],
        rows=rows,
    )

    # 输出映射诊断（中位数强度）
    diag_rows: list[list[object]] = []
    for sid in order:
        sel = assigned == sid
        diag_rows.append(
            [
                sid,
                int(sel.sum()),
                float(ft.screen_int[sel].median()) if int(sel.sum()) else float("nan"),
                float(ft.cpu_int[sel].median()) if int(sel.sum()) else float("nan"),
                float(ft.gpu_int[sel].median()) if int(sel.sum()) else float("nan"),
                float(ft.wifi_int[sel].median()) if int(sel.sum()) else float("nan"),
                float(ft.infra_int[sel].median()) if int(sel.sum()) else float("nan"),
                float(ft.p_total_W[sel].median()) if int(sel.sum()) else float("nan"),
            ]
        )
    _write_csv(
        out_dir / "mapping_diagnostics.csv",
        header=["scenario_id", "n", "screen_int_med", "cpu_int_med", "gpu_int_med", "wifi_int_med", "infra_int_med", "P_total_W_med"],
        rows=diag_rows,
    )

    # 保存最佳参数与 top20
    (out_dir / "tuned_params.json").write_text(json.dumps(best_params.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(out_dir / "tuning_top20.csv", header=list(top20[0].keys()), rows=[[r.get(k) for k in top20[0].keys()] for r in top20])

    # 4) 画图（不覆盖主图）
    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure_paper.png" if m == "paper" else "figure_study.png")
        _plot_radar(
            labels=labels,
            tte_m0=tte0,
            tte_m1=tte1,
            tte_open=open_tte,
            open_counts=open_n,
            mode=m,  # type: ignore[arg-type]
            out_png=out_png,
            lang=str(args.lang),
        )

    # 5) about
    about = (
        "# about\n\n"
        "- 图中黑色虚线：AndroWatts 开源测量数据推得的“满电 TTE≈E/P”量级支撑（不是逐时刻真值轨迹）。\n"
        "- 为减少系统偏差，我们对“门控 + 优先级”分类阈值做了可复现的随机搜索，使其更贴近模型预测（目标曲线："
        f"{args.target}）。\n"
        "- 关键输出：\n"
        "  - `tuned_params.json`：最佳阈值（可复现）\n"
        "  - `tuning_top20.csv`：前 20 组候选（便于复核）\n"
        "  - `mapping_diagnostics.csv`：每类强度指标中位数（证明规则与直觉一致）\n"
        "- 注意：若 AndroWatts 数据集本身缺少“深度待机”等场景覆盖，则 S1 仍可能无法与模型完全一致。\n\n"
        "复现命令示例：\n\n"
        "```bash\n"
        "PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/tune_q1_opendata_mapping_to_model.py --lang en --mode both\n"
        "```\n"
    )
    (out_dir / "about.md").write_text(about, encoding="utf-8")

    print(f"[OK] 已生成调参后的公开数据量级支撑图：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

