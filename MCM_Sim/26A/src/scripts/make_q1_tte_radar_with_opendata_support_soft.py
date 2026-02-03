#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06（扩展图，V3-soft）：在 Model-0 vs Model-1 的 TTE 雷达图上叠加“公开测量数据支持的量级”，并使用更接近真实的软分类。

动机（面向赛题叙事）：
- 赛题 Q1 要求连续时间机理模型（SOC(t) 的 ODE/方程组）；数据只能用于“参数估计与验证”，不能替代模型。
- AndroWatts（开源测量）本身没有“场景标签”，因此场景划分应尽量可解释、可复现，并承认分类不确定性。
- 真实使用并非硬切换场景；用硬阈值分类会在边界处抖动、产生“过于完美”的错觉。

本脚本做法：
1) 用可观测代理特征构造 0~1 的无量纲强度指标（屏幕/CPU/GPU/WiFi/蜂窝基础设施/总功耗）。
2) 采用“模糊规则（sigmoid/窗口函数）”得到每条记录属于 S1~S5 的概率权重（soft assignment）。
3) 以权重统计每类功耗/续航的中位数与四分位距（IQR），在雷达图上用“中位数折线 + IQR 径向误差棒”展示不确定性。

输出（默认不覆盖旧图；若目标目录已存在，则会先归档旧文件）：
- `Q1材料/06-模型0vs模型1_TTE对比/other/opendata_support_soft_v1/`
  - figure_paper.png / figure_study.png
  - data_opendata_support_soft.csv（与图一致的统计表）
  - mapping_diagnostics_soft.csv（强度指标加权中位数，证明规则与直觉一致）
  - soft_params.json（本脚本使用的软阈值参数）
  - about.md（复现说明）
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
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
COLOR_GRAY = "#666666"


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


def _archive_outputs(out_dir: Path) -> None:
    """若 out_dir 已有输出，则先把旧文件移入 archived/ 时间戳子目录，避免覆盖。"""

    if not out_dir.exists():
        return

    patterns = ["*.png", "*.csv", "*.md", "*.json"]
    files: list[Path] = []
    for pat in patterns:
        files.extend(out_dir.glob(pat))
    if not files:
        return

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    arc = out_dir / "archived" / ts
    arc.mkdir(parents=True, exist_ok=True)
    for p in files:
        try:
            p.rename(arc / p.name)
        except OSError:
            # rename 失败时退化为 copy+unlink（跨设备/权限等）
            data = p.read_bytes()
            (arc / p.name).write_bytes(data)
            p.unlink(missing_ok=True)


def _write_csv(path: Path, *, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _rank01(s: pd.Series) -> pd.Series:
    """百分位秩（0~1）：比固定阈值更稳健，可解释为“在该数据集中处于什么水平”"""

    return s.rank(pct=True, method="average").clip(0.0, 1.0)


@dataclass(frozen=True)
class FeatureTable:
    p_total_W: pd.Series
    p_total_rank: pd.Series
    screen_int: pd.Series
    cpu_int: pd.Series
    gpu_int: pd.Series
    wifi_int: pd.Series
    infra_int: pd.Series


def _build_features(df: pd.DataFrame) -> FeatureTable:
    """从 aggregated.csv 构造强度特征（0~1）与总功耗（W）。"""

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

    # 组合强度（0~1）
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


def _sigmoid(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.asarray(z)))


def _hi(x: pd.Series, *, t: float, s: float) -> pd.Series:
    """高于阈值的隶属度：x>t 越高越接近 1。"""

    return pd.Series(_sigmoid((x - float(t)) / float(s)), index=x.index).clip(0.0, 1.0)


def _lo(x: pd.Series, *, t: float, s: float) -> pd.Series:
    """低于阈值的隶属度：x<t 越低越接近 1。"""

    return pd.Series(_sigmoid((float(t) - x) / float(s)), index=x.index).clip(0.0, 1.0)


def _between(x: pd.Series, *, a: float, b: float, s: float) -> pd.Series:
    """区间隶属度：在 [a,b] 内高，在外部平滑衰减。"""

    return (_hi(x, t=a, s=s) * _lo(x, t=b, s=s)).clip(0.0, 1.0)


@dataclass(frozen=True)
class SoftParams:
    """软分类阈值：全部是 0~1 的无量纲强度。"""

    # 屏幕开启门控（用于 S2~S5）
    s_on: float = 0.45
    s_slope: float = 0.06

    # S1（待机/轻度）
    s1_screen: float = 0.25
    s1_cpu: float = 0.35
    s1_gpu: float = 0.40
    s1_wifi: float = 0.60
    s1_p: float = 0.08

    # S4（游戏）
    s4_cpu: float = 0.88
    s4_gpu: float = 0.85
    s4_p: float = 0.985

    # S5（导航/通话）
    s5_wifi: float = 0.40
    s5_infra: float = 0.85
    s5_p: float = 0.95

    # S3（视频/直播）
    s3_wifi: float = 0.78
    s3_cpu_a: float = 0.25
    s3_cpu_b: float = 0.80
    s3_gpu_a: float = 0.25
    s3_gpu_b: float = 0.80

    # S2（浏览/社交）
    s2_wifi_a: float = 0.45
    s2_wifi_b: float = 0.78
    s2_cpu_a: float = 0.35
    s2_cpu_b: float = 0.85
    s2_gpu: float = 0.78
    s2_p: float = 0.55

    # 统一斜率（越大越“软”）
    slope: float = 0.04

    # 概率“尖锐度”：>1 会让每条记录更接近“主导场景”（更像真实：同一时刻通常由一种行为主导）。
    gamma: float = 4.0


def _soft_probs(ft: FeatureTable, p: SoftParams) -> pd.DataFrame:
    """为每条记录生成 S1~S5 的概率（soft assignment）。"""

    screen_on = _hi(ft.screen_int, t=p.s_on, s=p.s_slope)

    s1 = (
        _lo(ft.screen_int, t=p.s1_screen, s=p.slope)
        * _lo(ft.cpu_int, t=p.s1_cpu, s=p.slope)
        * _lo(ft.gpu_int, t=p.s1_gpu, s=p.slope)
        * _lo(ft.wifi_int, t=p.s1_wifi, s=p.slope)
        * _lo(ft.p_total_rank, t=p.s1_p, s=p.slope)
    )
    s4 = (
        screen_on
        * _hi(ft.cpu_int, t=p.s4_cpu, s=p.slope)
        * _hi(ft.gpu_int, t=p.s4_gpu, s=p.slope)
        * _hi(ft.p_total_rank, t=p.s4_p, s=p.slope)
    )
    s5 = (
        screen_on
        * _lo(ft.wifi_int, t=p.s5_wifi, s=p.slope)
        * _hi(ft.infra_int, t=p.s5_infra, s=p.slope)
        * _hi(ft.p_total_rank, t=p.s5_p, s=p.slope)
    )
    s3 = (
        screen_on
        * _hi(ft.wifi_int, t=p.s3_wifi, s=p.slope)
        * _between(ft.cpu_int, a=p.s3_cpu_a, b=p.s3_cpu_b, s=p.slope)
        * _between(ft.gpu_int, a=p.s3_gpu_a, b=p.s3_gpu_b, s=p.slope)
    )
    s2 = (
        screen_on
        * _between(ft.wifi_int, a=p.s2_wifi_a, b=p.s2_wifi_b, s=p.slope)
        * _between(ft.cpu_int, a=p.s2_cpu_a, b=p.s2_cpu_b, s=p.slope)
        * _lo(ft.gpu_int, t=p.s2_gpu, s=p.slope)
        * _lo(ft.p_total_rank, t=p.s2_p, s=p.slope)
    )

    scores = pd.DataFrame(
        {
            "S1_standby_light": s1,
            "S2_browse_social": s2,
            "S3_video_streaming": s3,
            "S4_gaming": s4,
            "S5_nav_call": s5,
        }
    ).clip(0.0, 1.0)

    # 概率尖锐度：让 soft assignment 更像真实（同一时刻通常由一种行为主导），同时仍保留边界平滑。
    gamma = float(getattr(p, "gamma", 1.0))
    if gamma != 1.0:
        scores = scores.pow(gamma)

    # 若一条记录对所有类别都接近 0，直接归一会产生 0/0；这里加一个很小的底噪，避免数值问题。
    eps = 1e-8
    denom = scores.sum(axis=1) + eps
    probs = scores.div(denom, axis=0)
    return probs


def _weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    """加权分位数（q in [0,1]）。"""

    q = float(q)
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be within [0,1]")

    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0.0)
    x = x[m]
    w = w[m]
    if x.size == 0:
        return float("nan")

    idx = np.argsort(x)
    x = x[idx]
    w = w[idx]
    cw = np.cumsum(w)
    if cw[-1] <= 0.0:
        return float("nan")
    target = q * cw[-1]
    j = int(np.searchsorted(cw, target, side="left"))
    j = min(max(j, 0), x.size - 1)
    return float(x[j])


@dataclass(frozen=True)
class ScenarioStats:
    n_eff: float
    p_W_median: float
    p_W_p25: float
    p_W_p75: float
    tte_h_median: float
    tte_h_p25: float
    tte_h_p75: float


def _compute_soft_stats(ft: FeatureTable, probs: pd.DataFrame, *, energy_Wh: float) -> dict[str, ScenarioStats]:
    """基于 soft 权重计算每类的功耗/续航统计（中位数 + IQR）。"""

    out: dict[str, ScenarioStats] = {}
    pW = ft.p_total_W.astype(float).to_numpy()
    tte_h = float(energy_Wh) / np.maximum(pW, 1e-9)

    for sid in probs.columns.tolist():
        w = probs[sid].astype(float).to_numpy()
        sw = float(np.sum(w))
        s2 = float(np.sum(w * w))
        n_eff = (sw * sw / s2) if (sw > 0.0 and s2 > 0.0) else 0.0

        out[sid] = ScenarioStats(
            n_eff=n_eff,
            p_W_median=_weighted_quantile(pW, w, 0.50),
            p_W_p25=_weighted_quantile(pW, w, 0.25),
            p_W_p75=_weighted_quantile(pW, w, 0.75),
            tte_h_median=_weighted_quantile(tte_h, w, 0.50),
            tte_h_p25=_weighted_quantile(tte_h, w, 0.25),
            tte_h_p75=_weighted_quantile(tte_h, w, 0.75),
        )

    return out


def _compute_soft_diagnostics(ft: FeatureTable, probs: pd.DataFrame) -> dict[str, dict[str, float]]:
    """输出强度指标的“加权中位数”，用于验证分类规则是否符合直觉。"""

    out: dict[str, dict[str, float]] = {}
    feats = {
        "screen_int": ft.screen_int.astype(float).to_numpy(),
        "cpu_int": ft.cpu_int.astype(float).to_numpy(),
        "gpu_int": ft.gpu_int.astype(float).to_numpy(),
        "wifi_int": ft.wifi_int.astype(float).to_numpy(),
        "infra_int": ft.infra_int.astype(float).to_numpy(),
        "p_total_W": ft.p_total_W.astype(float).to_numpy(),
    }

    for sid in probs.columns.tolist():
        w = probs[sid].astype(float).to_numpy()
        sw = float(np.sum(w))
        s2 = float(np.sum(w * w))
        n_eff = (sw * sw / s2) if (sw > 0.0 and s2 > 0.0) else 0.0
        out[sid] = {"n_eff": n_eff}
        for k, x in feats.items():
            out[sid][f"{k}_median"] = _weighted_quantile(x, w, 0.50)
    return out


def _plot_radar(
    *,
    labels: list[str],
    tte_m0: list[float],
    tte_m1: list[float],
    open_med: list[float],
    open_p25: list[float],
    open_p75: list[float],
    open_n: list[float],
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
    vo = [float(x) for x in open_med]

    ticks = [2.0, 4.0, 8.0, 16.0, 32.0]
    vmax = float(np.nanmax([np.nanmax(v0), np.nanmax(v1), np.nanmax(open_p75)]))
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
        labelo = "Open data (AndroWatts, soft mapping)"
        title = "TTE Comparison Across Scenarios (Radar / Log Scale)"
        if mode == "study":
            title += " (study)"
    else:
        label0 = "Model-0（SOC阈值）"
        label1 = "Model-1（截止电压）"
        labelo = "公开数据（AndroWatts，软映射）"
        title = f"不同场景下的耗尽时间 TTE 对比（雷达图/对数刻度）{style.title_suffix}"

    ax.plot(angles, v0, color=COLOR_BLUE, lw=2.2, marker="o", markersize=4.0, label=label0)
    ax.fill(angles, v0, color=COLOR_BLUE, alpha=0.12)

    ax.plot(angles, v1, color=COLOR_ORANGE, lw=2.2, marker="o", markersize=4.0, label=label1)
    ax.fill(angles, v1, color=COLOR_ORANGE, alpha=0.12)

    # open data：中位数折线 + IQR 径向误差棒
    ax.plot(angles, vo, color=COLOR_BLACK, lw=1.8, ls="--", marker="s", markersize=3.6, label=labelo)
    for a, lo, hi in zip(angles, open_p25, open_p75):
        if math.isfinite(float(lo)) and math.isfinite(float(hi)):
            ax.plot([a, a], [float(lo), float(hi)], color=COLOR_BLACK, alpha=0.35, lw=2.0, solid_capstyle="round")

    ax.set_title(title, pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 0.98))
        if lang == "en":
            note = (
                "Notes: The open-data polygon is NOT a ground-truth trajectory. It is an order-of-magnitude support derived\n"
                "from AndroWatts via a rule-based *soft* mapping. Radial bars indicate IQR (25%~75%).\n"
                + "n_eff = [" + ", ".join(f"{x:.1f}" for x in open_n) + "] (S1..S5)"
            )
        else:
            note = (
                "说明：开源数据折线不是逐时刻真值轨迹，而是由 AndroWatts 推得的‘量级支撑’。\n"
                "分类采用软映射（模糊规则），径向误差棒表示 IQR（25%~75%）。\n"
                + "n_eff = [" + ", ".join(f"{x:.1f}" for x in open_n) + "] (S1..S5)"
            )
        fig.text(0.01, 0.02, note, ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1：公开数据量级支撑（软分类版本）")
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
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式")
    ap.add_argument(
        "--out-dir",
        default=str(Q1_DIR / "other" / "opendata_support_soft_v1"),
        help="输出目录（默认写入 Q1-06/other/opendata_support_soft_v1；不会覆盖旧图，会先归档）",
    )

    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    _archive_outputs(out_dir)

    # 1) 计算模型目标 TTE（S1~S5）
    raw = load_scenarios_json(Path(args.scenarios))
    power = PowerParams0.from_json(Path(args.power))
    batt1 = BatteryParams1ECM.from_json(Path(args.phone))
    batt0 = BatteryParams0.from_json(Path(args.phone))

    order = ["S1_standby_light", "S2_browse_social", "S3_video_streaming", "S4_gaming", "S5_nav_call"]

    labels: list[str] = []
    tte0: list[float] = []
    tte1: list[float] = []

    for sid in order:
        sc = materialize_scenario(raw, sid)
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        labels.append(title_en if str(args.lang) == "en" else title_zh)

        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=float(args.soc0))
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=float(args.soc0), dt_s=float(args.dt))
        tte0.append(float("nan") if r0.tte_h is None else float(r0.tte_h))
        tte1.append(float("nan") if r1.tte_h is None else float(r1.tte_h))

    # 2) open data -> 特征 -> 软分类统计
    od = pd.read_csv(Path(args.open_data))
    ft = _build_features(od)
    soft_params = SoftParams()
    probs = _soft_probs(ft, soft_params)
    stats = _compute_soft_stats(ft, probs, energy_Wh=float(batt0.energy_Wh))
    diag = _compute_soft_diagnostics(ft, probs)

    # 3) 输出数据表（与图一致）
    rows: list[list[object]] = []
    open_med: list[float] = []
    open_p25: list[float] = []
    open_p75: list[float] = []
    open_n: list[float] = []
    for sid in order:
        st = stats[sid]
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        rows.append(
            [
                sid,
                title_zh,
                title_en,
                st.n_eff,
                st.p_W_median,
                st.p_W_p25,
                st.p_W_p75,
                st.tte_h_median,
                st.tte_h_p25,
                st.tte_h_p75,
            ]
        )
        open_med.append(float(st.tte_h_median))
        open_p25.append(float(st.tte_h_p25))
        open_p75.append(float(st.tte_h_p75))
        open_n.append(float(st.n_eff))

    _write_csv(
        out_dir / "data_opendata_support_soft.csv",
        header=[
            "scenario_id",
            "title_zh",
            "title_en",
            "n_eff",
            "P_total_W_median",
            "P_total_W_p25",
            "P_total_W_p75",
            "TTE_full_h_median",
            "TTE_full_h_p25",
            "TTE_full_h_p75",
        ],
        rows=rows,
    )

    # 诊断表：加权中位数强度
    diag_rows: list[list[object]] = []
    for sid in order:
        d = diag[sid]
        diag_rows.append(
            [
                sid,
                d["n_eff"],
                d["screen_int_median"],
                d["cpu_int_median"],
                d["gpu_int_median"],
                d["wifi_int_median"],
                d["infra_int_median"],
                d["p_total_W_median"],
            ]
        )
    _write_csv(
        out_dir / "mapping_diagnostics_soft.csv",
        header=[
            "scenario_id",
            "n_eff",
            "screen_int_median",
            "cpu_int_median",
            "gpu_int_median",
            "wifi_int_median",
            "infra_int_median",
            "P_total_W_median",
        ],
        rows=diag_rows,
    )

    (out_dir / "soft_params.json").write_text(json.dumps(soft_params.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4) 画图（paper/study）
    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure_paper.png" if m == "paper" else "figure_study.png")
        _plot_radar(
            labels=labels,
            tte_m0=tte0,
            tte_m1=tte1,
            open_med=open_med,
            open_p25=open_p25,
            open_p75=open_p75,
            open_n=open_n,
            mode=m,  # type: ignore[arg-type]
            out_png=out_png,
            lang=str(args.lang),
        )

    about = (
        "# about\n\n"
        "- 本目录输出的是：AndroWatts 开源测量推得的‘功耗/续航量级支撑’，不是逐时刻真值轨迹。\n"
        "- 场景划分采用软分类（模糊规则），目的是更贴近真实‘场景混合/边界不清晰’的使用特征。\n"
        "- 图中径向误差棒：IQR（25%~75%）。\n"
        "- 复现命令示例：\n\n"
        "```bash\n"
        "PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_radar_with_opendata_support_soft.py --lang en --mode both\n"
        "```\n"
    )
    (out_dir / "about.md").write_text(about, encoding="utf-8")

    print(f"[OK] 已生成软分类的公开数据量级支撑图：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
