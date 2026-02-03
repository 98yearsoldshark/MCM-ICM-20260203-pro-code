#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06（扩展图，箱线图）：用箱线图展示“公开测量数据支持的量级”，并叠加 Model-0/Model-1 的 TTE 点预测。

用途（面向论文叙事）：
- 雷达图适合展示“形状/相对关系”；箱线图更适合展示“分布与误差带”，从而体现
  “真实观测与机理模型之间存在偏差/不确定性”这一事实。
- AndroWatts 无场景标签：我们用可解释的代理特征做软分类（soft mapping），再对每类计算
  TTE 的加权分位数（例如 5/25/50/75/95%），形成箱线图统计量。

重要声明（与赛题 Q1 对齐）：
- 公开数据仅用于“量级支撑/合理性检验”，不替代连续时间机理模型；
- 箱线图中的 open data 并非逐时刻真值轨迹，而是由 AndroWatts 推得的“满电 TTE≈E/P”量级分布；
- 分类不确定性通过 soft mapping + 分位数范围体现。

输出（默认不覆盖旧图；若目标目录已存在，则会先归档旧文件）：
- `Q1材料/06-模型0vs模型1_TTE对比/other/opendata_support_soft_v1_boxplot/`
  - figure_paper.png / figure_study.png
  - data_opendata_support_soft_boxplot.csv
  - mapping_diagnostics_soft.csv
  - soft_params.json
  - about.md
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

from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0, simulate_model1_ecm
from mcm26a.viz.style import PlotMode, apply_style, savefig


COLOR_BLUE = "#008CFF"
COLOR_ORANGE = "#EC5A00"
COLOR_BLACK = "#222222"
COLOR_GRAY = "#999999"


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A

Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "06-模型0vs模型1_TTE对比"
OPEN_DATA_CSV_DEFAULT = ROOT_DIR / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"


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
    """百分位秩（0~1）：比固定阈值更稳健，可解释为“在该数据集中处于什么水平”。"""

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
    def need(name: str) -> pd.Series:
        if name not in df.columns:
            raise ValueError(f"open data missing column: {name}")
        return df[name]

    pow_cols = [c for c in df.columns if c.endswith("_ENERGY_AVG_UWS")]
    if not pow_cols:
        raise ValueError("open data missing *_ENERGY_AVG_UWS columns")

    p_total_W = df[pow_cols].sum(axis=1).astype(float) * 1e-6
    p_total_rank = _rank01(p_total_W)

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
    return pd.Series(_sigmoid((x - float(t)) / float(s)), index=x.index).clip(0.0, 1.0)


def _lo(x: pd.Series, *, t: float, s: float) -> pd.Series:
    return pd.Series(_sigmoid((float(t) - x) / float(s)), index=x.index).clip(0.0, 1.0)


def _between(x: pd.Series, *, a: float, b: float, s: float) -> pd.Series:
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

    # 概率“尖锐度”：>1 会让每条记录更接近“主导场景”（更像真实）。
    gamma: float = 4.0


def _soft_probs(ft: FeatureTable, p: SoftParams) -> pd.DataFrame:
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

    # 概率尖锐度：让每条记录更接近“主导场景”，但仍保留边界平滑。
    gamma = float(getattr(p, "gamma", 1.0))
    if gamma != 1.0:
        scores = scores.pow(gamma)

    eps = 1e-8
    denom = scores.sum(axis=1) + eps
    return scores.div(denom, axis=0)


def _weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    q = float(q)
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


def _n_eff(w: np.ndarray) -> float:
    sw = float(np.sum(w))
    s2 = float(np.sum(w * w))
    if sw <= 0.0 or s2 <= 0.0:
        return 0.0
    return (sw * sw) / s2


def _compute_soft_quantiles(ft: FeatureTable, probs: pd.DataFrame, *, energy_Wh: float) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """输出：每类的分位数统计 + 强度指标诊断（加权中位数）。"""

    pW = ft.p_total_W.astype(float).to_numpy()
    tte_h = float(energy_Wh) / np.maximum(pW, 1e-9)

    stats: dict[str, dict[str, float]] = {}
    diag: dict[str, dict[str, float]] = {}
    for sid in probs.columns.tolist():
        w = probs[sid].astype(float).to_numpy()
        stats[sid] = {
            "n_eff": _n_eff(w),
            "tte_q05": _weighted_quantile(tte_h, w, 0.05),
            "tte_q25": _weighted_quantile(tte_h, w, 0.25),
            "tte_q50": _weighted_quantile(tte_h, w, 0.50),
            "tte_q75": _weighted_quantile(tte_h, w, 0.75),
            "tte_q95": _weighted_quantile(tte_h, w, 0.95),
            "p_q50": _weighted_quantile(pW, w, 0.50),
        }

        diag[sid] = {
            "n_eff": stats[sid]["n_eff"],
            "screen_int_med": _weighted_quantile(ft.screen_int.to_numpy(dtype=float), w, 0.50),
            "cpu_int_med": _weighted_quantile(ft.cpu_int.to_numpy(dtype=float), w, 0.50),
            "gpu_int_med": _weighted_quantile(ft.gpu_int.to_numpy(dtype=float), w, 0.50),
            "wifi_int_med": _weighted_quantile(ft.wifi_int.to_numpy(dtype=float), w, 0.50),
            "infra_int_med": _weighted_quantile(ft.infra_int.to_numpy(dtype=float), w, 0.50),
            "P_total_W_med": _weighted_quantile(pW, w, 0.50),
        }

    return stats, diag


def _plot_box(
    *,
    labels: list[str],
    tte_m0: list[float],
    tte_m1: list[float],
    open_stats: list[dict[str, float]],
    open_n_eff: list[float],
    mode: PlotMode,
    lang: str,
    out_png: Path,
) -> None:
    style = apply_style(mode)

    fig = plt.figure(figsize=(9.0, 4.8))
    ax = plt.gca()

    # open data：用预计算分位数构造 bxp 统计字典
    bxp_stats = []
    for st in open_stats:
        bxp_stats.append(
            {
                "med": float(st["q50"]),
                "q1": float(st["q25"]),
                "q3": float(st["q75"]),
                "whislo": float(st["q05"]),
                "whishi": float(st["q95"]),
                "fliers": [],
            }
        )

    positions = np.arange(1, len(labels) + 1, dtype=float)
    bp = ax.bxp(bxp_stats, positions=positions, widths=0.55, showfliers=False, patch_artist=True)

    for box in bp["boxes"]:
        box.set(facecolor=COLOR_GRAY, alpha=0.18, edgecolor=COLOR_BLACK, linewidth=1.2)
    for med in bp["medians"]:
        med.set(color=COLOR_BLACK, linewidth=1.6)
    for w in bp["whiskers"]:
        w.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)
    for c in bp["caps"]:
        c.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)

    # 叠加模型点预测（轻微左右错位）
    ax.scatter(positions - 0.15, tte_m0, s=38, color=COLOR_BLUE, edgecolor="white", linewidth=0.6, zorder=4, label="Model-0 (SOC threshold)")
    ax.scatter(positions + 0.15, tte_m1, s=38, color=COLOR_ORANGE, edgecolor="white", linewidth=0.6, zorder=4, label="Model-1 (voltage cut-off)")

    # 轴与刻度
    ax.set_yscale("log")
    ticks = [2, 4, 8, 16, 32]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t}h" for t in ticks])

    ax.set_xticks(positions)
    ax.set_xticklabels(labels)

    if lang == "en":
        ax.set_ylabel("Time-to-Empty, TTE (hours)")
        title = "TTE Comparison Across Scenarios (Boxplot / Log Scale)"
        open_label = "Open data (AndroWatts, soft mapping)"
    else:
        ax.set_ylabel("耗尽时间 TTE（小时）")
        title = f"TTE 场景对比（箱线图/对数刻度）{style.title_suffix}"
        open_label = "公开数据（AndroWatts，软映射）"

    ax.set_title(title)

    # 为 open data 箱体加一个图例项
    ax.plot([], [], color=COLOR_BLACK, lw=0, marker="s", markersize=8, markerfacecolor=COLOR_GRAY, alpha=0.18, label=open_label)

    ax.legend(loc="upper right", frameon=False)

    if style.annotate:
        note = (
            "Notes: open-data boxes are derived from AndroWatts via rule-based *soft* mapping.\n"
            "Whiskers: 5%~95%; Box: 25%~75%; Median: 50%.\n"
            + "n_eff = [" + ", ".join(f"{x:.1f}" for x in open_n_eff) + "] (S1..S5)"
        ) if lang == "en" else (
            "说明：箱线图来自 AndroWatts 开源测量的‘量级支撑’，并通过规则化软映射得到。\n"
            "须：5%~95%；箱体：25%~75%；中位数：50%。\n"
            + "n_eff = [" + ", ".join(f"{x:.1f}" for x in open_n_eff) + "] (S1..S5)"
        )
        fig.text(0.01, 0.01, note, ha="left", va="bottom", fontsize=9)
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 1.0))
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1：公开数据量级支撑（箱线图，软分类）")
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
        default=str(Q1_DIR / "other" / "opendata_support_soft_v1_boxplot"),
        help="输出目录（默认写入 Q1-06/other/opendata_support_soft_v1_boxplot；不会覆盖旧图，会先归档）",
    )

    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    _archive_outputs(out_dir)

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

    # open data -> soft mapping -> quantiles
    od = pd.read_csv(Path(args.open_data))
    ft = _build_features(od)
    soft_params = SoftParams()
    probs = _soft_probs(ft, soft_params)
    qstats, diag = _compute_soft_quantiles(ft, probs, energy_Wh=float(batt0.energy_Wh))

    rows: list[list[object]] = []
    box_stats: list[dict[str, float]] = []
    n_eff: list[float] = []
    for sid in order:
        st = qstats[sid]
        rows.append(
            [
                sid,
                float(st["n_eff"]),
                float(st["tte_q05"]),
                float(st["tte_q25"]),
                float(st["tte_q50"]),
                float(st["tte_q75"]),
                float(st["tte_q95"]),
                float(st["p_q50"]),
            ]
        )
        box_stats.append(
            {
                "q05": float(st["tte_q05"]),
                "q25": float(st["tte_q25"]),
                "q50": float(st["tte_q50"]),
                "q75": float(st["tte_q75"]),
                "q95": float(st["tte_q95"]),
            }
        )
        n_eff.append(float(st["n_eff"]))

    _write_csv(
        out_dir / "data_opendata_support_soft_boxplot.csv",
        header=["scenario_id", "n_eff", "tte_q05_h", "tte_q25_h", "tte_q50_h", "tte_q75_h", "tte_q95_h", "P_total_W_median"],
        rows=rows,
    )

    diag_rows: list[list[object]] = []
    for sid in order:
        d = diag[sid]
        diag_rows.append([sid, d["n_eff"], d["screen_int_med"], d["cpu_int_med"], d["gpu_int_med"], d["wifi_int_med"], d["infra_int_med"], d["P_total_W_med"]])
    _write_csv(
        out_dir / "mapping_diagnostics_soft.csv",
        header=["scenario_id", "n_eff", "screen_int_med", "cpu_int_med", "gpu_int_med", "wifi_int_med", "infra_int_med", "P_total_W_med"],
        rows=diag_rows,
    )

    (out_dir / "soft_params.json").write_text(json.dumps(soft_params.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure_paper.png" if m == "paper" else "figure_study.png")
        _plot_box(
            labels=labels,
            tte_m0=tte0,
            tte_m1=tte1,
            open_stats=box_stats,
            open_n_eff=n_eff,
            mode=m,  # type: ignore[arg-type]
            lang=str(args.lang),
            out_png=out_png,
        )

    about = (
        "# about\n\n"
        "- 本目录输出：open data 的箱线图支撑（AndroWatts + 软映射），并叠加模型的点预测。\n"
        "- 胡须：5%~95%；箱体：25%~75%；中位数：50%。\n\n"
        "复现命令示例：\n\n"
        "```bash\n"
        "PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_boxplot_with_opendata_support_soft.py --lang en --mode both\n"
        "```\n"
    )
    (out_dir / "about.md").write_text(about, encoding="utf-8")

    print(f"[OK] 已生成箱线图版的公开数据量级支撑：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

