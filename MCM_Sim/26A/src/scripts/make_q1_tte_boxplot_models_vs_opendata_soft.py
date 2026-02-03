#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06（扩展图，箱线图叠加）：open data 的箱线图 + Model-0/Model-1 的“小箱线图”。

用户需求（本次改动）：
- open data（AndroWatts）已有箱线图；
- 希望把 Model-0 / Model-1 也做成“小箱线图”，便于叠加对比，更直观、更“好看”。

关键思路（符合赛题 Q1 的口径）：
- open data 只做“量级支撑”，不是逐时刻真值轨迹；
- Model-0/1 本身是连续时间机理模型；为了给出“预测不确定性”，我们对少量关键参数做
  *可解释的* 不确定性采样（UQ-lite），得到一组 TTE 样本，再画成小箱线图；
- 这样就能在论文中合理解释：“真实与模型之间存在误差/不确定性”，而不是硬贴合。

输出（默认不覆盖旧图；若目标目录已存在，会先归档旧文件）：
- `Q1材料/06-模型0vs模型1_TTE对比/other/opendata_support_soft_v1_boxplot_models/`
  - figure_paper.png / figure_study.png
  - data_opendata_support_boxplot.csv（open data：q05/q25/q50/q75/q95 + n_eff）
  - data_model_uq_boxplot.csv（model0/model1：q05/q25/q50/q75/q95 + n_samples）
  - soft_params.json（open data 的软分类参数）
  - uq_params.json（模型不确定性采样参数）
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
from matplotlib.patches import Patch

from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power.model0 import PowerParams0, ScreenParams0, LinearLoadParams0, GPSParams0
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
    """百分位秩（0~1）：可解释为“在该数据集中处于什么水平”。"""

    return s.rank(pct=True, method="average").clip(0.0, 1.0)


# ----------------------------
# AndroWatts：软分类（soft mapping）
# ----------------------------


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
    # 屏幕开启门控（用于 S2~S5）
    s_on: float = 0.45
    s_slope: float = 0.06
    # S1
    s1_screen: float = 0.25
    s1_cpu: float = 0.35
    s1_gpu: float = 0.40
    s1_wifi: float = 0.60
    s1_p: float = 0.08
    # S4
    s4_cpu: float = 0.88
    s4_gpu: float = 0.85
    s4_p: float = 0.985
    # S5
    s5_wifi: float = 0.40
    s5_infra: float = 0.85
    s5_p: float = 0.95
    # S3
    s3_wifi: float = 0.78
    s3_cpu_a: float = 0.25
    s3_cpu_b: float = 0.80
    s3_gpu_a: float = 0.25
    s3_gpu_b: float = 0.80
    # S2
    s2_wifi_a: float = 0.45
    s2_wifi_b: float = 0.78
    s2_cpu_a: float = 0.35
    s2_cpu_b: float = 0.85
    s2_gpu: float = 0.78
    s2_p: float = 0.55
    # 平滑/尖锐度
    slope: float = 0.04
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
    s4 = screen_on * _hi(ft.cpu_int, t=p.s4_cpu, s=p.slope) * _hi(ft.gpu_int, t=p.s4_gpu, s=p.slope) * _hi(ft.p_total_rank, t=p.s4_p, s=p.slope)
    s5 = screen_on * _lo(ft.wifi_int, t=p.s5_wifi, s=p.slope) * _hi(ft.infra_int, t=p.s5_infra, s=p.slope) * _hi(ft.p_total_rank, t=p.s5_p, s=p.slope)
    s3 = screen_on * _hi(ft.wifi_int, t=p.s3_wifi, s=p.slope) * _between(ft.cpu_int, a=p.s3_cpu_a, b=p.s3_cpu_b, s=p.slope) * _between(ft.gpu_int, a=p.s3_gpu_a, b=p.s3_gpu_b, s=p.slope)
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

    gamma = float(getattr(p, "gamma", 1.0))
    if gamma != 1.0:
        scores = scores.pow(gamma)

    eps = 1e-8
    denom = scores.sum(axis=1) + eps
    return scores.div(denom, axis=0)


def _weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    """加权分位数（q in [0,1]）。"""

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


def _compute_opendata_box_stats(ft: FeatureTable, probs: pd.DataFrame, *, energy_Wh: float) -> dict[str, dict[str, float]]:
    """open data：输出每类 TTE 的分位数（5/25/50/75/95）+ n_eff。"""

    pW = ft.p_total_W.astype(float).to_numpy()
    tte_h = float(energy_Wh) / np.maximum(pW, 1e-9)
    out: dict[str, dict[str, float]] = {}
    for sid in probs.columns.tolist():
        w = probs[sid].astype(float).to_numpy()
        out[sid] = {
            "n_eff": _n_eff(w),
            "q05": _weighted_quantile(tte_h, w, 0.05),
            "q25": _weighted_quantile(tte_h, w, 0.25),
            "q50": _weighted_quantile(tte_h, w, 0.50),
            "q75": _weighted_quantile(tte_h, w, 0.75),
            "q95": _weighted_quantile(tte_h, w, 0.95),
        }
    return out


# ----------------------------
# Model-0/1：轻量不确定性采样（UQ-lite）
# ----------------------------


@dataclass(frozen=True)
class UQParams:
    """模型不确定性采样参数（可解释、可复现）。"""

    # 电池容量比例（capacity/energy）：Uniform[a,b]
    cap_scale_a: float = 0.90
    cap_scale_b: float = 1.10

    # 功耗比例（设备/使用差异）：LogNormal(0,sigma) 并裁剪到 [min,max]
    p_log_sigma: float = 0.12
    p_scale_min: float = 0.70
    p_scale_max: float = 1.40

    # Model-1 额外：内阻比例（温度/老化/个体差异）：LogNormal(0,sigma) 并裁剪
    r_log_sigma: float = 0.10
    r_scale_min: float = 0.70
    r_scale_max: float = 1.50

    # Model-1 额外：截止电压微小偏差（系统/标定差异）
    vcut_delta_V: float = 0.03  # Normal(0, vcut_delta_V) 再裁剪到 [vcut_min, vcut_max]
    vcut_min: float = 3.20
    vcut_max: float = 3.40


def _scale_power_params(p: PowerParams0, *, scale: float) -> PowerParams0:
    """对功耗参数做全局比例缩放（W 量纲）。"""

    s = float(scale)
    return PowerParams0(
        base_W=float(p.base_W) * s,
        screen=ScreenParams0(P0_W=float(p.screen.P0_W) * s, k_W_per_nit=float(p.screen.k_W_per_nit) * s),
        cpu=LinearLoadParams0(k_W=float(p.cpu.k_W) * s),
        gpu=LinearLoadParams0(k_W=float(p.gpu.k_W) * s),
        gps=GPSParams0(P_W=float(p.gps.P_W) * s),
        background_level_W={k: float(v) * s for k, v in p.background_level_W.items()},
        signal_multiplier=dict(p.signal_multiplier),  # 无量纲：不缩放
        radio_activity_W={mode: {act: float(pw) * s for act, pw in acts.items()} for mode, acts in p.radio_activity_W.items()},
    )


def _sample_scales(rng: np.random.Generator, uq: UQParams) -> tuple[float, float, float, float]:
    """返回 (cap_scale, p_scale, r_scale, v_cut_V)。"""

    cap = float(rng.uniform(uq.cap_scale_a, uq.cap_scale_b))

    p_scale = float(np.exp(rng.normal(0.0, uq.p_log_sigma)))
    p_scale = float(np.clip(p_scale, uq.p_scale_min, uq.p_scale_max))

    r_scale = float(np.exp(rng.normal(0.0, uq.r_log_sigma)))
    r_scale = float(np.clip(r_scale, uq.r_scale_min, uq.r_scale_max))

    dv = float(rng.normal(0.0, uq.vcut_delta_V))
    vcut = float(np.clip(3.30 + dv, uq.vcut_min, uq.vcut_max))
    return cap, p_scale, r_scale, vcut


def _uq_model_samples(
    scenario,
    *,
    power_params: PowerParams0,
    batt0: BatteryParams0,
    batt1: BatteryParams1ECM,
    soc0: float,
    uq: UQParams,
    rng: np.random.Generator,
    n: int,
    dt_model1_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """返回 (model0_samples_h, model1_samples_h)。"""

    m0: list[float] = []
    m1: list[float] = []
    for _ in range(int(n)):
        cap_scale, p_scale, r_scale, vcut = _sample_scales(rng, uq)

        # 功耗缩放（两模型一致）
        p_scaled = _scale_power_params(power_params, scale=p_scale)

        # Model-0：能量（Wh）缩放
        batt0_s = BatteryParams0(energy_Wh=float(batt0.energy_Wh) * cap_scale, soc_min=float(batt0.soc_min))
        r0 = simulate_model0(scenario, power_params=p_scaled, battery_params=batt0_s, soc0=soc0)
        if r0.tte_h is not None and math.isfinite(float(r0.tte_h)) and float(r0.tte_h) > 0:
            m0.append(float(r0.tte_h))

        # Model-1：容量/内阻/截止电压缩放
        batt1_s = BatteryParams1ECM(
            capacity_Ah=float(batt1.capacity_Ah) * cap_scale,
            soc_min=float(batt1.soc_min),
            v_cut_V=float(vcut),
            r0_ohm=float(batt1.r0_ohm) * r_scale,
            r1_ohm=float(batt1.r1_ohm) * r_scale,
            c1_F=float(batt1.c1_F),
            ocv=batt1.ocv,
            r0_curve=batt1.r0_curve,
            r1_curve=batt1.r1_curve,
            rate_capacity_k_per_A=float(batt1.rate_capacity_k_per_A),
            ocv_hysteresis_V=float(batt1.ocv_hysteresis_V),
            ocv_hysteresis_i_thresh_A=float(batt1.ocv_hysteresis_i_thresh_A),
            hyst_M_V=float(batt1.hyst_M_V),
            hyst_gamma=float(batt1.hyst_gamma),
            hyst_i_thresh_A=float(batt1.hyst_i_thresh_A),
            hyst_M_curve=batt1.hyst_M_curve,
            hyst_relax_tau_s=float(batt1.hyst_relax_tau_s),
        )
        r1 = simulate_model1_ecm(scenario, power_params=p_scaled, battery_params=batt1_s, soc0=soc0, dt_s=float(dt_model1_s))
        if r1.tte_h is not None and math.isfinite(float(r1.tte_h)) and float(r1.tte_h) > 0:
            m1.append(float(r1.tte_h))

    return np.asarray(m0, dtype=float), np.asarray(m1, dtype=float)


def _box_stats_from_samples(x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if x.size == 0:
        return {"q05": float("nan"), "q25": float("nan"), "q50": float("nan"), "q75": float("nan"), "q95": float("nan")}
    return {
        "q05": float(np.percentile(x, 5)),
        "q25": float(np.percentile(x, 25)),
        "q50": float(np.percentile(x, 50)),
        "q75": float(np.percentile(x, 75)),
        "q95": float(np.percentile(x, 95)),
    }


def _plot_boxplot_overlay(
    *,
    labels: list[str],
    open_stats: list[dict[str, float]],
    open_n_eff: list[float],
    m0_stats: list[dict[str, float]],
    m1_stats: list[dict[str, float]],
    n_model_samples: int,
    mode: PlotMode,
    lang: str,
    out_png: Path,
) -> None:
    style = apply_style(mode)

    fig = plt.figure(figsize=(9.0, 4.8))
    ax = plt.gca()

    positions = np.arange(1, len(labels) + 1, dtype=float)

    # open data（大箱体）
    bxp_open = [
        {"med": st["q50"], "q1": st["q25"], "q3": st["q75"], "whislo": st["q05"], "whishi": st["q95"], "fliers": []}
        for st in open_stats
    ]
    bp = ax.bxp(bxp_open, positions=positions, widths=0.55, showfliers=False, patch_artist=True)
    for box in bp["boxes"]:
        box.set(facecolor=COLOR_GRAY, alpha=0.16, edgecolor=COLOR_BLACK, linewidth=1.2)
    for med in bp["medians"]:
        med.set(color=COLOR_BLACK, linewidth=1.6)
    for w in bp["whiskers"]:
        w.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)
    for c in bp["caps"]:
        c.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)

    # Model-0 / Model-1（小箱体：左右错位）
    dx = 0.22
    w_small = 0.18

    bxp_m0 = [
        {"med": st["q50"], "q1": st["q25"], "q3": st["q75"], "whislo": st["q05"], "whishi": st["q95"], "fliers": []}
        for st in m0_stats
    ]
    bxp_m1 = [
        {"med": st["q50"], "q1": st["q25"], "q3": st["q75"], "whislo": st["q05"], "whishi": st["q95"], "fliers": []}
        for st in m1_stats
    ]
    bp0 = ax.bxp(bxp_m0, positions=positions - dx, widths=w_small, showfliers=False, patch_artist=True)
    bp1 = ax.bxp(bxp_m1, positions=positions + dx, widths=w_small, showfliers=False, patch_artist=True)

    for box in bp0["boxes"]:
        box.set(facecolor=COLOR_BLUE, alpha=0.40, edgecolor=COLOR_BLUE, linewidth=1.0)
    for med in bp0["medians"]:
        med.set(color="white", linewidth=1.2)
    for w in bp0["whiskers"]:
        w.set(color=COLOR_BLUE, alpha=0.70, linewidth=1.0)
    for c in bp0["caps"]:
        c.set(color=COLOR_BLUE, alpha=0.70, linewidth=1.0)

    for box in bp1["boxes"]:
        box.set(facecolor=COLOR_ORANGE, alpha=0.40, edgecolor=COLOR_ORANGE, linewidth=1.0)
    for med in bp1["medians"]:
        med.set(color="white", linewidth=1.2)
    for w in bp1["whiskers"]:
        w.set(color=COLOR_ORANGE, alpha=0.70, linewidth=1.0)
    for c in bp1["caps"]:
        c.set(color=COLOR_ORANGE, alpha=0.70, linewidth=1.0)

    ax.set_yscale("log")
    ticks = [2, 4, 8, 16, 32]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t}h" for t in ticks])

    # 给顶部留出空间：用于标注“模型偏差”两行文字
    y_max = float(
        np.nanmax(
            [
                max(float(st["q95"]) for st in open_stats),
                max(float(st["q95"]) for st in m0_stats),
                max(float(st["q95"]) for st in m1_stats),
            ]
        )
    )
    if math.isfinite(y_max) and y_max > 0:
        ax.set_ylim(bottom=1.8, top=y_max * 1.45)

    ax.set_xticks(positions)
    ax.set_xticklabels(labels)

    if lang == "en":
        ax.set_ylabel("Time-to-Empty, TTE (hours)")
        title = "TTE Comparison Across Scenarios (Boxplot / Log Scale)"
        lab_open = "Open data (AndroWatts, soft mapping)"
        lab_m0 = "Model-0 (UQ-lite)"
        lab_m1 = "Model-1 (UQ-lite)"
    else:
        ax.set_ylabel("耗尽时间 TTE（小时）")
        title = f"TTE 场景对比（箱线图/对数刻度）{style.title_suffix}"
        lab_open = "公开数据（AndroWatts，软映射）"
        lab_m0 = "Model-0（不确定性）"
        lab_m1 = "Model-1（不确定性）"

    ax.set_title(title)

    handles = [
        Patch(facecolor=COLOR_GRAY, edgecolor=COLOR_BLACK, alpha=0.16, label=lab_open),
        Patch(facecolor=COLOR_BLUE, edgecolor=COLOR_BLUE, alpha=0.40, label=lab_m0),
        Patch(facecolor=COLOR_ORANGE, edgecolor=COLOR_ORANGE, alpha=0.40, label=lab_m1),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False)

    # 1) 每个场景标注“模型偏差”（基于中位数比）
    # 2) 每个场景标注覆盖度：n_eff(open) 与 n(model)
    for i, x in enumerate(positions):
        o_med = float(open_stats[i]["q50"])
        m0_med = float(m0_stats[i]["q50"])
        m1_med = float(m1_stats[i]["q50"])
        o_hi = float(open_stats[i]["q95"])
        m0_hi = float(m0_stats[i]["q95"])
        m1_hi = float(m1_stats[i]["q95"])
        y_local = float(np.nanmax([o_hi, m0_hi, m1_hi]))
        if math.isfinite(y_local) and y_local > 0 and math.isfinite(o_med) and o_med > 0:
            d0 = 100.0 * (m0_med / o_med - 1.0) if (math.isfinite(m0_med) and m0_med > 0) else float("nan")
            d1 = 100.0 * (m1_med / o_med - 1.0) if (math.isfinite(m1_med) and m1_med > 0) else float("nan")
            s0 = f"{d0:+.1f}%" if math.isfinite(d0) else "NA"
            s1 = f"{d1:+.1f}%" if math.isfinite(d1) else "NA"

            ax.text(
                x,
                y_local * 1.08,
                f"M0 vs Open: {s0}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=COLOR_BLUE,
            )
            ax.text(
                x,
                y_local * 1.20,
                f"M1 vs Open: {s1}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=COLOR_ORANGE,
            )

        # 覆盖度（放在 x 轴下方，避免受 log-y 影响）
        ne = float(open_n_eff[i])
        ne_s = f"{ne:.1f}" if math.isfinite(ne) else "NA"
        # S1 额外标记：公开数据缺少深度待机场景覆盖，因此仅能提供量级下界。
        # 为减少横向占用并避免与相邻场景重叠，† 注释单独成行。
        if i == 0:
            extra = "\u2020 lower bound" if lang == "en" else "\u2020 下界"
            cover = f"n_eff(open)={ne_s}\n" + f"n(model)={int(n_model_samples)}\n" + f"{extra}"
        else:
            cover = f"n_eff(open)={ne_s}\n" + f"n(model)={int(n_model_samples)}"
        ax.text(
            x,
            -0.16,
            cover,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=9 if mode == "paper" else 9,
            color=COLOR_BLACK,
        )

    if style.annotate:
        if lang == "en":
            note = (
                "Notes: Open-data boxes are derived from AndroWatts (TTE≈E/P) using rule-based *soft* mapping.\n"
                "Model boxes are UQ-lite samples by perturbing a few interpretable parameters (capacity/power/impedance/V_cut).\n"
                f"n_model = {int(n_model_samples)} per scenario/model; n_eff(open) = [" + ", ".join(f"{x:.1f}" for x in open_n_eff) + "]\n"
                "† S1 is a lower bound due to limited deep-standby coverage in the open dataset."
            )
        else:
            note = (
                "说明：灰色箱线图来自 AndroWatts 的‘量级支撑’（TTE≈E/P），并使用规则化软映射。\n"
                "蓝/橘小箱体为模型的轻量不确定性采样（容量/功耗/内阻/截止电压等可解释参数扰动）。\n"
                f"n_model = {int(n_model_samples)}（每场景/每模型）；n_eff(open) = [" + ", ".join(f"{x:.1f}" for x in open_n_eff) + "]\n"
                "† S1：由于公开数据集缺少深度待机覆盖，因此仅能提供量级下界。"
            )
        fig.text(0.01, 0.01, note, ha="left", va="bottom", fontsize=9)
        # 底部留白：需要容纳 2~3 行覆盖度文字 + 说明文字
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 1.0))
    else:
        # paper 版仍要给 x 轴下方的覆盖度文字留白（S1 为 3 行）
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 1.0))

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1：open data + 模型（小箱线图）叠加对比")
    ap.add_argument("--open-data", default=str(OPEN_DATA_CSV_DEFAULT), help="AndroWatts aggregated.csv 路径")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json"), help="Q1 五场景配置 JSON")
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v0.json"), help="功耗参数（用于 Model-0/Model-1）")
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"), help="电池参数（energy_Wh + ECM 参数）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt-model1", type=float, default=10.0, help="Model-1 UQ-lite 的积分步长（秒），取大可加速")
    ap.add_argument("--model-samples", type=int, default=250, help="每个场景/每个模型的 UQ-lite 采样次数")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式")
    ap.add_argument(
        "--out-dir",
        default=str(Q1_DIR / "other" / "opendata_support_soft_v1_boxplot_models"),
        help="输出目录（默认写入 Q1-06/other/opendata_support_soft_v1_boxplot_models；不会覆盖旧图，会先归档）",
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

    # 1) open data：软分类 -> 箱线图统计
    od = pd.read_csv(Path(args.open_data))
    ft = _build_features(od)
    soft_params = SoftParams()
    probs = _soft_probs(ft, soft_params)
    open_stats_by = _compute_opendata_box_stats(ft, probs, energy_Wh=float(batt0.energy_Wh))

    # 2) 模型：UQ-lite -> 小箱线图统计
    uq = UQParams()
    rng = np.random.default_rng(int(args.seed))

    labels: list[str] = []
    open_stats: list[dict[str, float]] = []
    open_n_eff: list[float] = []
    m0_stats: list[dict[str, float]] = []
    m1_stats: list[dict[str, float]] = []

    model_rows: list[list[object]] = []
    open_rows: list[list[object]] = []

    for sid in order:
        sc = materialize_scenario(raw, sid)
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        labels.append(title_en if str(args.lang) == "en" else title_zh)

        # open data
        o = open_stats_by[sid]
        open_stats.append({"q05": o["q05"], "q25": o["q25"], "q50": o["q50"], "q75": o["q75"], "q95": o["q95"]})
        open_n_eff.append(float(o["n_eff"]))
        open_rows.append([sid, float(o["n_eff"]), float(o["q05"]), float(o["q25"]), float(o["q50"]), float(o["q75"]), float(o["q95"])])

        # model uq
        m0_s, m1_s = _uq_model_samples(
            sc,
            power_params=power,
            batt0=batt0,
            batt1=batt1,
            soc0=float(args.soc0),
            uq=uq,
            rng=rng,
            n=int(args.model_samples),
            dt_model1_s=float(args.dt_model1),
        )
        st0 = _box_stats_from_samples(m0_s)
        st1 = _box_stats_from_samples(m1_s)
        m0_stats.append(st0)
        m1_stats.append(st1)
        model_rows.append([sid, "model0", int(m0_s.size), st0["q05"], st0["q25"], st0["q50"], st0["q75"], st0["q95"]])
        model_rows.append([sid, "model1", int(m1_s.size), st1["q05"], st1["q25"], st1["q50"], st1["q75"], st1["q95"]])

    _write_csv(
        out_dir / "data_opendata_support_boxplot.csv",
        header=["scenario_id", "n_eff", "q05_h", "q25_h", "q50_h", "q75_h", "q95_h"],
        rows=open_rows,
    )
    _write_csv(
        out_dir / "data_model_uq_boxplot.csv",
        header=["scenario_id", "model", "n_samples", "q05_h", "q25_h", "q50_h", "q75_h", "q95_h"],
        rows=model_rows,
    )

    (out_dir / "soft_params.json").write_text(json.dumps(soft_params.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "uq_params.json").write_text(json.dumps(uq.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure_paper.png" if m == "paper" else "figure_study.png")
        _plot_boxplot_overlay(
            labels=labels,
            open_stats=open_stats,
            open_n_eff=open_n_eff,
            m0_stats=m0_stats,
            m1_stats=m1_stats,
            n_model_samples=int(args.model_samples),
            mode=m,  # type: ignore[arg-type]
            lang=str(args.lang),
            out_png=out_png,
        )

    about = (
        "# about\n\n"
        "- 灰色箱线：AndroWatts 开源测量推得的 TTE≈E/P 量级分布（软分类映射）。\n"
        "- 蓝/橘小箱线：Model-0/Model-1 的轻量不确定性采样（UQ-lite），用于展示“预测不确定性”。\n"
        "- 复现命令示例：\n\n"
        "```bash\n"
        "PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_boxplot_models_vs_opendata_soft.py --lang en --mode both\n"
        "```\n"
    )
    (out_dir / "about.md").write_text(about, encoding="utf-8")

    print(f"[OK] 已生成：open data + 模型小箱线图叠加：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
