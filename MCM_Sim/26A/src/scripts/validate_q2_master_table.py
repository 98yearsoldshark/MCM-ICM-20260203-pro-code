#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 数据集驱动验证：AndroWatts（手机侧）× 电池老化状态表（Mendeley 派生）。

目标（对齐赛题）：
- 赛题要求连续时间机理模型输出 SOC(t) 与 TTE，并说明“为什么会差这么多”。
- 本脚本用两个公开数据源做“参数锚定/验证式实验”（不是黑盒拟合）：
  1) AndroWatts：给出 1000 条手机负载测量的功耗量级与分解（短时聚合）；
  2) Mendeley 派生电池状态表：给出 36 个老化状态（SOH + OCV(SOC)）用于历史/老化敏感性。

做法：
- 从 AndroWatts 中按“总功耗分位数”挑选 3 条代表性负载（轻/中/重）；
- 以“观测功耗分解”作为恒定功率输入，驱动 Model-3 电池 ODE，计算 TTE；
- 对每条负载，扫描 36 个电池状态，得到 TTE vs SOH 的曲线与“提前关机剩余 SOC”。

输出：
- out_reports/q2/validation_master_table/tte_by_state.csv
- out_plots/q2/{paper|study}/observed_master_table/
  - 01_tte_vs_soh.png
  - 02_soc_end_vs_soh.png

注意：
- 这里用“观测功耗”作为输入是为了隔离电池端机理（否则会混入功耗模型误差）。
- 论文写作时应明确：该实验用于“老化对续航影响”的量级与趋势展示，不替代 Q2 主线场景仿真。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.andro_watts import build_cases, load_aggregated_csv
from mcm26a.observed.mcm2026_battery_state import apply_battery_state_to_model3, load_battery_state_table
from mcm26a.power.model0 import PowerBreakdown, PowerParams0
from mcm26a.scenarios import Scenario, Segment
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


@dataclass
class _ConstantPowerModel:
    """恒定功率模型：每个 dt 返回同一个功耗分解（用于“电池端隔离验证”）。"""

    breakdown: PowerBreakdown

    def reset(self) -> None:  # noqa: D401 - 简短接口
        """与 StatefulPowerModel1 对齐的空实现。"""

    def step(self, seg: Segment, *, dt_s: float, battery_temp_C: float | None = None) -> PowerBreakdown:  # noqa: ARG002
        return self.breakdown


def _pick_cases_by_percentiles(cases, percentiles: list[float]) -> list[int]:
    """按总功耗分位数选择“最接近该分位点”的样本索引（保证尽量不重复）。"""

    ps = np.array([c.obs.total_w for c in cases], dtype=float)
    ps = np.where(np.isfinite(ps), ps, np.nan)
    out_idx: list[int] = []
    used: set[int] = set()
    for p in percentiles:
        target = float(np.nanpercentile(ps, float(p)))
        dist = np.abs(ps - target)
        order = np.argsort(dist)
        pick = None
        for i in order.tolist():
            if int(i) not in used:
                pick = int(i)
                break
        if pick is None:
            pick = int(order[0]) if order.size else 0
        used.add(int(pick))
        out_idx.append(int(pick))
    return out_idx


def _make_constant_scenario_from_case(case, *, cycle_s: float = 60.0) -> Scenario:
    """把 AndroWattsCase 映射成一个“恒定外生输入”的重复场景。"""

    seg0: Segment = case.segment
    seg = Segment(
        duration_s=float(cycle_s),
        ambient_temp_c=float(seg0.ambient_temp_c),
        screen_on=bool(seg0.screen_on),
        brightness_nits=float(seg0.brightness_nits),
        activity=str(seg0.activity),
        cpu_load=float(seg0.cpu_load),
        gpu_load=float(seg0.gpu_load),
        radio_mode=str(seg0.radio_mode),
        signal_quality=str(seg0.signal_quality),
        net_activity=str(seg0.net_activity),
        net_throughput_MBps=float(getattr(seg0, "net_throughput_MBps", float("nan"))),
        gps_on=bool(seg0.gps_on),
        background_level=str(seg0.background_level),
        screen_apl=float(getattr(seg0, "screen_apl", float("nan"))),
    )
    return Scenario(
        scenario_id=f"aw_case_{int(case.test_id)}",
        title_zh=f"AndroWatts 样本 {int(case.test_id)}（恒定负载）",
        description_zh="用公开测量的功耗分解作为恒定输入，循环重复直到电池耗尽。",
        repeat=True,
        cycle_s=float(cycle_s),
        schedule=(seg,),
    )


def _plot_tte_vs_soh(rows: list[dict[str, object]], *, mode: PlotMode) -> object:
    import matplotlib.pyplot as plt
    import pandas as pd

    style = apply_style(mode)

    df = pd.DataFrame(rows)
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    df["battery_state_label"] = pd.Categorical(df["battery_state_label"], categories=order, ordered=True)

    # 先按“老化档位”聚合（每档位包含多个 cell/dataset），画均值+误差带；
    # 同时在学习版叠加原始散点（避免把离散状态误读为连续曲线）。
    agg = (
        df.groupby(["load_label", "battery_state_label"], observed=False)
        .agg(
            SOH_mean=("SOH", "mean"),
            tte_mean=("tte_h", "mean"),
            tte_min=("tte_h", "min"),
            tte_max=("tte_h", "max"),
            obs_total_w=("obs_total_w", "mean"),
        )
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    for k, (load_label, g) in enumerate(agg.groupby("load_label", observed=False)):
        g = g.sort_values("battery_state_label")
        x = g["SOH_mean"].to_numpy(dtype=float)
        y = g["tte_mean"].to_numpy(dtype=float)
        ylo = g["tte_min"].to_numpy(dtype=float)
        yhi = g["tte_max"].to_numpy(dtype=float)
        p = float(g["obs_total_w"].iloc[0])

        color = colors[k % len(colors)]
        # 均值连线（更稳健、更美观）
        ax.plot(x, y, marker="o", ms=4.0, lw=2.0, color=color, label=f"{load_label}（P≈{p:.2f}W）")
        # 误差带：用 min~max 表示“不同电芯/数据集差异”（一种结构不确定性）
        ax.vlines(x, ylo, yhi, colors=color, alpha=0.25, lw=3.0)

        if style.annotate:
            sub = df[df["load_label"] == load_label]
            ax.scatter(
                sub["SOH"].to_numpy(dtype=float),
                sub["tte_h"].to_numpy(dtype=float),
                s=12,
                color=color,
                alpha=0.18,
                edgecolors="none",
                zorder=2,
            )

    ax.set_xlabel("SOH（容量健康度）")
    ax.set_ylabel("TTE（小时）")
    ax.set_title(f"老化状态对续航的影响：TTE vs SOH{style.title_suffix}")
    ax.set_xlim(0.58, 1.02)
    ax.legend(frameon=False, loc="best")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：点线为“按老化档位聚合后的均值”（new→eol），竖向误差棒为同一档位内不同电芯/数据集的最小~最大范围。\n"
            "学习版浅色散点为 36 个离散电池状态的原始结果（避免把离散状态误读为连续曲线）。\n"
            "实验做法：用 AndroWatts 的观测功耗分解作为恒定输入，驱动 Model-3 电池 ODE 直到欠压/耗尽。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_soc_end_vs_soh(rows: list[dict[str, object]], *, mode: PlotMode) -> object:
    import matplotlib.pyplot as plt
    import pandas as pd

    style = apply_style(mode)

    df = pd.DataFrame(rows)
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    df["battery_state_label"] = pd.Categorical(df["battery_state_label"], categories=order, ordered=True)

    agg = (
        df.groupby(["load_label", "battery_state_label"], observed=False)
        .agg(
            SOH_mean=("SOH", "mean"),
            soc_mean=("soc_end", "mean"),
            soc_min=("soc_end", "min"),
            soc_max=("soc_end", "max"),
        )
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    for k, (load_label, g) in enumerate(agg.groupby("load_label", observed=False)):
        g = g.sort_values("battery_state_label")
        x = g["SOH_mean"].to_numpy(dtype=float)
        y = g["soc_mean"].to_numpy(dtype=float)
        ylo = g["soc_min"].to_numpy(dtype=float)
        yhi = g["soc_max"].to_numpy(dtype=float)

        color = colors[k % len(colors)]
        ax.plot(x, y, marker="o", ms=4.0, lw=2.0, color=color, label=str(load_label))
        ax.vlines(x, ylo, yhi, colors=color, alpha=0.25, lw=3.0)

        if style.annotate:
            sub = df[df["load_label"] == load_label]
            # 用 marker 区分终止机制：cutoff（提前欠压） vs soc_min（耗尽到下限）
            is_cut = sub["status"].astype(str) == "cutoff"
            ax.scatter(
                sub.loc[~is_cut, "SOH"].to_numpy(dtype=float),
                sub.loc[~is_cut, "soc_end"].to_numpy(dtype=float),
                s=14,
                color=color,
                alpha=0.20,
                marker="o",
                edgecolors="none",
                zorder=2,
            )
            ax.scatter(
                sub.loc[is_cut, "SOH"].to_numpy(dtype=float),
                sub.loc[is_cut, "soc_end"].to_numpy(dtype=float),
                s=18,
                color=color,
                alpha=0.22,
                marker="^",
                edgecolors="none",
                zorder=2,
            )

    ax.set_xlabel("SOH（容量健康度）")
    ax.set_ylabel("终止时剩余 SOC")
    ax.set_title(f"提前关机证据：终止时 SOC vs SOH{style.title_suffix}")
    ax.set_xlim(0.58, 1.02)
    ax.set_ylim(-0.02, 0.22)
    ax.legend(frameon=False, loc="best")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：点线为按老化档位聚合的均值，竖向误差棒为同档位内不同电芯/数据集的范围。\n"
            "学习版用不同形状区分终止机制：○=SOC_min（耗尽到下限），▲=cutoff（欠压提前关机，SOC 仍明显>0）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 数据集驱动验证：AndroWatts × 电池老化状态表")
    ap.add_argument(
        "--aggregated",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
        help="AndroWatts aggregated.csv 路径",
    )
    ap.add_argument(
        "--battery-states",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
        help="电池状态表 CSV 路径（36 个状态）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="Model-3 电池参数 JSON（作为基准骨架）",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="占位：simulate_model3_aging 需要 power_params 参数（此处不使用功耗模型）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（默认 1.0）")
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒）")
    ap.add_argument("--cycle-s", type=float, default=60.0, help="恒定场景的周期长度（秒）")
    ap.add_argument("--percentiles", default="10,50,90", help="选择代表性负载的功耗分位数（逗号分隔）")
    ap.add_argument("--r-growth-k", type=float, default=1.0, help="经验内阻增长映射系数 k（r_growth=k*(1/SOH-1)）")
    ap.add_argument(
        "--capacity-mode",
        default="cap_loss_from_soh",
        choices=["cap_loss_from_soh", "scale_capacity_ref"],
        help="用 SOH 表示老化的方式：cap_loss 或直接缩放容量",
    )
    ap.add_argument("--out-report-dir", default=str(SRC_DIR / "out_reports" / "q2" / "validation_master_table"))
    ap.add_argument("--out-plot-dir", default=str(SRC_DIR / "out_plots"))
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    # 1) 读取 AndroWatts：构造 cases（含观测功耗分解 + 映射段）
    df = load_aggregated_csv(args.aggregated)
    cases = build_cases(df, max_n=None, seed=0, max_screen_nits=500.0)

    # 2) 选 3 条代表性负载（按总功耗分位数）
    percentiles = [float(x.strip()) for x in str(args.percentiles).split(",") if x.strip()]
    idxs = _pick_cases_by_percentiles(cases, percentiles=percentiles)
    picked = [cases[i] for i in idxs]
    load_labels = ["轻负载", "中负载", "重负载"][: len(picked)]

    # 3) 读取电池状态表，并把 OCV/ SOH 映射到 Model-3
    base_batt = BatteryParams3Aging.from_json(args.phone)
    dummy_power = PowerParams0.from_json(args.power)
    states = load_battery_state_table(args.battery_states)

    # 4) 扫描：对每条负载 × 每个电池状态计算 TTE
    rows: list[dict[str, object]] = []
    for load_i, (label, case) in enumerate(zip(load_labels, picked)):
        scen = _make_constant_scenario_from_case(case, cycle_s=float(args.cycle_s))
        obs_bd = PowerBreakdown(
            base_w=float(case.obs.base_w),
            screen_w=float(case.obs.screen_w),
            cpu_w=float(case.obs.cpu_w),
            gpu_w=float(case.obs.gpu_w),
            radio_w=float(case.obs.radio_w),
            gps_w=float(case.obs.gps_w),
            background_w=float(case.obs.background_w),
            interaction_w=0.0,
            other_w=float(case.obs.other_w),
        )
        pm = _ConstantPowerModel(breakdown=obs_bd)

        for st in states:
            batt_i, cap_loss0, r0_g0, r1_g0 = apply_battery_state_to_model3(
                base_batt,
                st,
                capacity_mode=str(args.capacity_mode),  # type: ignore[arg-type]
                r_growth_k=float(args.r_growth_k),
                n_ocv_points=101,
            )

            r = simulate_model3_aging(
                scen,
                power_params=dummy_power,
                power_model=pm,
                battery_params=batt_i,
                soc0=float(args.soc0),
                temp0_C=float(case.segment.ambient_temp_c),
                cap_loss0_frac=float(cap_loss0),
                r0_growth0_frac=float(r0_g0),
                r1_growth0_frac=float(r1_g0),
                variant=str(st.battery_state_label),
                dt_s=float(args.dt),
            )

            rows.append(
                {
                    "load_label": str(label),
                    "phone_case_id": int(case.test_id),
                    "obs_total_w": float(case.obs.total_w),
                    "battery_state_id": str(st.battery_state_id),
                    "battery_state_label": str(st.battery_state_label),
                    "battery_dataset": int(st.battery_dataset),
                    "battery_cell": str(st.battery_cell),
                    "SOH": float(st.SOH),
                    "cap_loss0_frac": float(cap_loss0),
                    "r0_growth0_frac": float(r0_g0),
                    "r1_growth0_frac": float(r1_g0),
                    "tte_h": (None if r.tte_h is None else float(r.tte_h)),
                    "status": str(r.status),
                    "soc_end": float(r.soc_end),
                    "temp_peak_C": float(r.temp_peak_C),
                }
            )

    out_report = ensure_dir(args.out_report_dir)
    out_csv = out_report / "tte_by_state.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    out_plot_root = ensure_dir(args.out_plot_dir) / "q2"
    modes: list[PlotMode] = ["paper", "study"] if not args.mode else [str(args.mode)]  # type: ignore[list-item]
    for mode in modes:
        out_plot = ensure_dir(out_plot_root / mode / "observed_master_table")
        fig1 = _plot_tte_vs_soh(rows, mode=mode)
        savefig(fig1, out_plot / "01_tte_vs_soh.png", mode=mode)

        fig2 = _plot_soc_end_vs_soh(rows, mode=mode)
        savefig(fig2, out_plot / "02_soc_end_vs_soh.png", mode=mode)

    print("Q2 master-table(概念) 验证完成：")
    print(f"- report: {out_csv}")
    print(f"- plots : {out_plot_root}/{{paper|study}}/observed_master_table/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
