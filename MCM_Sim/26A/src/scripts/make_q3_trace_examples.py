#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q3 的“示例轨迹图”（paper/study 两套）。

动机（更贴近赛题 Q3：Sensitivity and Assumptions）：
- PRCC/消融图给出“总体规律”，但缺少直观的“曲线层面”证据；
- 本脚本补充少量“代表性轨迹”：
  1) 电池端结构假设：1RC vs 2RC（快+慢极化）在突发负载场景下的电压与极化分解；
  2) 外部条件变体：baseline vs poor_signal（弱信号）在混合日常场景下的电压轨迹对照。

约定：
- 时间计算统一用秒（SI），图中横轴以小时展示；
- 输出目录：out_plots/q3/{paper|study}/traces/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q2_drivers import power_mechanism_variant
from mcm26a.analysis.q3_sensitivity import _as_batt1_2rc_from_batt3, _as_batt1_from_batt3
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model1_ecm_trace, simulate_model3_aging_trace
from mcm26a.sim.model1_2rc import simulate_model1_ecm2rc_trace
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _sec_to_h(xs: list[float]) -> np.ndarray:
    return np.asarray(xs, dtype=float) / 3600.0


def _pick_poor_signal_variant(raw: dict, scenario_id: str) -> str | None:
    spec = (raw.get("scenarios", {}) or {}).get(str(scenario_id), {}) or {}
    variants = spec.get("variants", {}) or {}
    for name in sorted(str(k) for k in variants.keys()):
        if "poor_signal" in name:
            return name
    return None


def _plot_voltage_compare(
    *,
    t_h: np.ndarray,
    y1: np.ndarray,
    y2: np.ndarray,
    label1: str,
    label2: str,
    v_cut: float | None,
    title: str,
    mode: PlotMode,
):
    style = apply_style(mode)
    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    ax.plot(t_h, y1, label=label1, linewidth=2.0, color="#1F77B4")
    ax.plot(t_h, y2, label=label2, linewidth=2.0, color="#FF7F0E")
    if v_cut is not None and np.isfinite(float(v_cut)):
        ax.axhline(float(v_cut), color="#666666", linestyle="--", linewidth=1.2, alpha=0.8, label="截止电压")
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("端电压（V）")
    ax.set_title(f"{title}{style.title_suffix}")
    ax.legend(frameon=False, ncol=3, fontsize=9)

    if style.annotate:
        fig.subplots_adjust(bottom=0.25)
        fig.text(
            0.01,
            0.02,
            "说明：两条曲线使用相同随机种子（CRN）生成一致的功耗波动，仅比较电池端/外部条件的差异。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_polarization_decomp_2rc(
    *,
    t_h: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
    title: str,
    mode: PlotMode,
):
    style = apply_style(mode)
    fig, ax = plt.subplots(figsize=(10.6, 4.8))
    ax.plot(t_h, v1, label="快支路极化压降 v1", linewidth=2.0, color="#2CA02C")
    ax.plot(t_h, v2, label="慢支路极化压降 v2", linewidth=2.0, color="#FF7F0E")
    ax.plot(t_h, v1 + v2, label="总极化压降 v1+v2", linewidth=2.0, color="#D62728", alpha=0.95)
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("极化压降（V）")
    ax.set_title(f"{title}{style.title_suffix}")
    ax.legend(frameon=False, ncol=3, fontsize=9)

    if style.annotate:
        fig.subplots_adjust(bottom=0.28)
        fig.text(
            0.01,
            0.02,
            "说明：2RC 把单一极化支路拆成快/慢两条时间尺度。\n"
            "- v1 更快响应突发负载，解释“尖峰后快速回弹”；\n"
            "- v2 更慢衰减，解释“平台间略带曲度的恢复”。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_headroom_margin(
    *,
    t_h: np.ndarray,
    p: np.ndarray,
    pmax: np.ndarray,
    title: str,
    mode: PlotMode,
):
    style = apply_style(mode)
    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    with np.errstate(divide="ignore", invalid="ignore"):
        margin = 1.0 - p / pmax
    ax.plot(t_h, margin, linewidth=2.0, color="#4C78A8", label="裕量 1 - P/Pmax")
    ax.axhline(0.0, color="#666666", linewidth=1.0, alpha=0.6)
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("功率闭合裕量（无量纲）")
    ax.set_title(f"{title}{style.title_suffix}")
    ax.legend(frameon=False, fontsize=9)
    ax.set_ylim(-0.2, 1.05)

    if style.annotate:
        fig.subplots_adjust(bottom=0.25)
        fig.text(
            0.01,
            0.02,
            "说明：裕量越接近 0，表示越接近“不可供电/电压崩塌”边界（判别式趋近 0）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 示例轨迹图（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q3/paper 与 q3/study）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"),
        help="功耗参数 JSON 路径（stateful：RRC+Poisson后台+交互项）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（Model-3：热-电-老化）",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="轨迹积分步长（秒），建议 1~5")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power = PowerParams1Stateful.from_json(args.power)
    batt3 = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    dt_s = float(args.dt)
    if dt_s <= 0:
        raise ValueError("dt 必须为正")

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]

    # ----------------------------
    # 1) 结构假设：1RC vs 2RC（S5_burst_recovery）
    # ----------------------------
    sc_s5 = materialize_scenario(raw, "S5_burst_recovery")
    power_fixed = power_mechanism_variant(power, mech_id="no_thermal_throttle")
    batt1 = _as_batt1_from_batt3(batt3)
    batt2 = _as_batt1_2rc_from_batt3(batt3)

    # 两次仿真用同一个 seed：保证功耗随机过程一致
    seed0 = int(args.seed) * 1_000_000 + 123
    pm1 = StatefulPowerModel1(power_fixed, seed=seed0)
    pm2 = StatefulPowerModel1(power_fixed, seed=seed0)

    tr_1rc = simulate_model1_ecm_trace(
        sc_s5,
        power_params=power0_dummy,
        power_model=pm1,
        battery_params=batt1,
        soc0=1.0,
        dt_s=dt_s,
    )
    tr_2rc = simulate_model1_ecm2rc_trace(
        sc_s5,
        power_params=power0_dummy,
        power_model=pm2,
        battery_params=batt2,
        soc0=1.0,
        dt_s=dt_s,
    )

    t1_h = _sec_to_h(tr_1rc.t_s)
    v1 = np.asarray(tr_1rc.v_term_V, dtype=float)
    t2_h = _sec_to_h(tr_2rc.t_s)
    v2 = np.asarray(tr_2rc.v_term_V, dtype=float)

    for mode in modes:
        out_base = ensure_dir(Path(args.out_dir) / "q3" / mode / "traces")

        fig = _plot_voltage_compare(
            t_h=t1_h,
            y1=v1,
            y2=np.interp(t1_h, t2_h, v2, left=np.nan, right=np.nan),
            label1="1RC",
            label2="2RC（快+慢极化）",
            v_cut=float(batt1.v_cut_V),
            title="Q3 示例：S5 突发-恢复场景的电压轨迹（1RC vs 2RC）",
            mode=mode,  # type: ignore[arg-type]
        )
        p = out_base / "60_s5_voltage_1rc_vs_2rc.png"
        savefig(fig, p, mode=mode)  # type: ignore[arg-type]
        plt.close(fig)

        fig = _plot_polarization_decomp_2rc(
            t_h=t2_h,
            v1=np.asarray(tr_2rc.v1_V, dtype=float),
            v2=np.asarray(tr_2rc.v2_V, dtype=float),
            title="Q3 示例：S5 2RC 极化分解（快支路 vs 慢支路）",
            mode=mode,  # type: ignore[arg-type]
        )
        p = out_base / "61_s5_polarization_2rc_decomp.png"
        savefig(fig, p, mode=mode)  # type: ignore[arg-type]
        plt.close(fig)

        fig = _plot_headroom_margin(
            t_h=t1_h,
            p=np.asarray(tr_1rc.p_W, dtype=float),
            pmax=np.asarray(tr_1rc.p_max_W, dtype=float),
            title="Q3 示例：S5 供电裕量随时间变化（1RC）",
            mode=mode,  # type: ignore[arg-type]
        )
        p = out_base / "62_s5_headroom_margin_1rc.png"
        savefig(fig, p, mode=mode)  # type: ignore[arg-type]
        plt.close(fig)

    # ----------------------------
    # 2) 外部条件变体：baseline vs poor_signal（S4_mixed_day）
    # ----------------------------
    poor_v = _pick_poor_signal_variant(raw, "S4_mixed_day")
    if poor_v is None:
        return 0

    sc_s4_base = materialize_scenario(raw, "S4_mixed_day", variant=None)
    sc_s4_poor = materialize_scenario(raw, "S4_mixed_day", variant=poor_v)

    pm_base = StatefulPowerModel1(power, seed=int(args.seed) * 1_000_000 + 456)
    pm_poor = StatefulPowerModel1(power, seed=int(args.seed) * 1_000_000 + 456)

    tr_base = simulate_model3_aging_trace(
        sc_s4_base,
        power_params=power0_dummy,
        power_model=pm_base,
        battery_params=batt3,
        soc0=1.0,
        dt_s=dt_s,
    )
    tr_poor = simulate_model3_aging_trace(
        sc_s4_poor,
        power_params=power0_dummy,
        power_model=pm_poor,
        battery_params=batt3,
        soc0=1.0,
        dt_s=dt_s,
    )

    t_base_h = _sec_to_h(tr_base.t_s)
    v_base = np.asarray(tr_base.v_term_V, dtype=float)
    t_poor_h = _sec_to_h(tr_poor.t_s)
    v_poor = np.asarray(tr_poor.v_term_V, dtype=float)

    for mode in modes:
        out_base = ensure_dir(Path(args.out_dir) / "q3" / mode / "traces")
        fig = _plot_voltage_compare(
            t_h=t_base_h,
            y1=v_base,
            y2=np.interp(t_base_h, t_poor_h, v_poor, left=np.nan, right=np.nan),
            label1="baseline",
            label2=f"弱信号（{poor_v}）",
            v_cut=float(batt3.v_cut_V),
            title="Q3 示例：S4 混合日常场景的电压轨迹（baseline vs 弱信号）",
            mode=mode,  # type: ignore[arg-type]
        )
        p = out_base / "70_s4_voltage_baseline_vs_poor_signal.png"
        savefig(fig, p, mode=mode)  # type: ignore[arg-type]
        plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

