#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2/论文 5.2.1：不同初始电量与环境温度对放电时间(TTE)影响的“高浓缩”对比图。

动机：
- 论文写作常需要“一张图讲清楚一个结论”；
- 原有轨迹图是 2x2 面板（SOC/V/T/P），信息全面但不够浓缩；
- 本脚本生成两张更适合放在论文段落 5.2.1 的图：
  1) 固定室温（默认 20°C）下，不同 SOC0 的 SOC(t) 叠加对比（四条线）；
  2) 固定场景与功耗随机种子，比较不同环境温度下的 TTE–SOC0 关系（三条线）。

输出（paper/study 两套）：
- src/out_plots/q2/{paper|study}/initial_soc_temperature/
  - 01_soc_overlay_T20C_<scenario_id>.png
  - 02_tte_vs_soc0_by_temp_<scenario_id>.png
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Scenario, load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging_trace
# 必须先导入 style（设置 MPLBACKEND/MPLCONFIGDIR），再导入 pyplot，避免无 GUI 环境崩溃。
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def _parse_float_list(s: str) -> list[float]:
    out: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    if not out:
        raise ValueError("列表参数不能为空")
    return out


def _override_ambient_temp(sc: Scenario, temp_c: float) -> Scenario:
    """把场景中每一段的 ambient_temp_c 统一覆写为 temp_c。"""

    schedule = tuple(replace(seg, ambient_temp_c=float(temp_c)) for seg in sc.schedule)
    return replace(sc, schedule=schedule)


def _override_batt_initial_temp(batt: BatteryParams3Aging, temp_c: float) -> BatteryParams3Aging:
    """把电池初始温度 t0_C 设置为环境温度；并确保温度范围覆盖 temp_c。"""

    tmin = float(batt.temp_min_C)
    tmax = float(batt.temp_max_C)
    if float(temp_c) < tmin:
        tmin = float(temp_c) - 5.0  # 给一点余量，避免边界钳制影响数值
    if float(temp_c) > tmax:
        tmax = float(temp_c) + 5.0
    return replace(batt, t0_C=float(temp_c), temp_min_C=float(tmin), temp_max_C=float(tmax))


def _simulate_once(
    sc: Scenario,
    *,
    soc0: float,
    temp_c: float,
    power1: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    dt_s: float,
    seed: int,
) -> dict[str, np.ndarray | float | str]:
    """运行一次 Model-3，返回用于画图的关键数组。"""

    sc_t = _override_ambient_temp(sc, temp_c=float(temp_c))
    batt_t = _override_batt_initial_temp(batt, temp_c=float(temp_c))

    # 重要：每次仿真都重新初始化 power_model，确保不同 SOC0/温度的对比
    # 使用相同的随机功耗轨迹（同 seed），避免“比较对象本身变了”。
    pm = StatefulPowerModel1(power1, seed=int(seed))
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    tr = simulate_model3_aging_trace(
        sc_t,
        power_params=power0_dummy,
        power_model=pm,
        battery_params=batt_t,
        soc0=float(soc0),
        dt_s=float(dt_s),
    )

    t_h = np.asarray(tr.t_s, dtype=float) / 3600.0
    soc_pct = np.asarray(tr.soc, dtype=float) * 100.0
    tte_h = float(t_h[-1]) if t_h.size else float("nan")

    return {
        "t_h": t_h,
        "soc_pct": soc_pct,
        "tte_h": tte_h,
        "status": str(tr.status),
    }


def _axis_labels_to_ends(
    ax,
    *,
    x_y: float = -0.06,
    y_x: float = -0.035,
    y_y: float = 1.0,
    y_va: str = "top",
) -> None:
    """把坐标轴标签移到“轴末端”附近（论文图更紧凑）。"""

    ax.xaxis.set_label_coords(1.0, float(x_y))
    ax.xaxis.label.set_horizontalalignment("right")
    ax.yaxis.set_label_coords(float(y_x), float(y_y))
    ax.yaxis.label.set_verticalalignment(str(y_va))


def _add_bottom_title(fig, text: str, *, y: float = 0.02, fontsize: int = 12) -> None:
    """把“图名/标题”放到图下（用户偏好的论文风格）。"""

    fig.text(0.5, float(y), str(text), ha="center", va="bottom", fontsize=int(fontsize))


def _temp_c_to_f_label(temp_c: float) -> str:
    """把摄氏度温度转为华氏度显示（论文图更直观）。"""

    f = float(temp_c) * 9.0 / 5.0 + 32.0
    # 整数温度不带小数，避免视觉噪声；否则保留 1 位小数（如 38°C -> 100.4°F）。
    if abs(f - round(f)) < 1e-9:
        return f"{int(round(f))}°F"
    return f"{f:.1f}°F"


def _plot_soc_overlay(
    *,
    mode: PlotMode,
    out_path: Path,
    sc: Scenario,
    temp_c: float,
    soc0_list: list[float],
    sims: dict[float, dict[str, np.ndarray | float | str]],
) -> None:
    style = apply_style(mode)

    # 用户需求：两张图都改为“偏向正方形”的论文图，便于横向拼接成一个组合图。
    fig_size = (6.2, 6.2) if mode == "paper" else (6.8, 6.8)
    fig, ax = plt.subplots(figsize=fig_size)

    # 图1配色（用户指定，4 条线）
    colors = ["#099F2D", "#005800", "#33618F", "#86AEE1"]

    max_tte = 0.0
    for soc0, c in zip(soc0_list, colors):
        r = sims[float(soc0)]
        t_h = np.asarray(r["t_h"], dtype=float)
        soc_pct = np.asarray(r["soc_pct"], dtype=float)
        tte_h = float(r["tte_h"])  # type: ignore[arg-type]
        max_tte = max(max_tte, float(tte_h))

        # 线末端加一个点：更直观显示“在哪儿结束（TTE）”
        label = f"SOC0={soc0*100:.0f}%"
        # 用户需求：交换 x/y 轴 -> SOC 做 y 轴，时间做 x 轴
        ax.plot(t_h, soc_pct, color=c, lw=2.6, label=label)
        if t_h.size:
            ax.plot([t_h[-1]], [soc_pct[-1]], marker="o", color=c, ms=5.5)

    ax.set_xlim(0.0, max_tte * 1.02 if max_tte > 0 else 1.0)
    ax.set_ylim(0.0, 105.0)

    # 场景英文名（论文图全英文更统一；若缺省则用 scenario_id 兜底）
    scenario_title_en_map = {
        "S0_standby": "Standby / Light Background",
        "S1_video": "Video Playback / Streaming",
        "S2_navigation": "Navigation (GPS + Map Data)",
        "S3_gaming": "Gaming (High CPU/GPU Load)",
        "S4_mixed_day": "Mixed Use (Typical Day)",
        "S5_burst_recovery": "Burst Load → Rest (Recovery Demo)",
    }
    sc_title_en = scenario_title_en_map.get(sc.scenario_id, sc.scenario_id)

    if mode == "paper":
        ax.set_xlabel("Time (h)")
        ax.set_ylabel("SOC (%)")
        bottom_title = f"{sc_title_en}: SOC vs time under different initial SOC0 (T_amb={temp_c:.0f}°C)"
        ax.set_title("")
        # 论文图：y 轴标签居中更稳（避免和 100% 刻度挤在一起/被裁切）
        ax.xaxis.set_label_coords(1.0, -0.06)
        ax.xaxis.label.set_horizontalalignment("right")
        ax.yaxis.set_label_coords(-0.10, 0.5)
        ax.yaxis.label.set_verticalalignment("center")
    else:
        ax.set_xlabel("时间（小时）")
        ax.set_ylabel("SOC（%）")
        ax.set_title(f"{sc.title_zh}：不同初始电量下 SOC–时间 轨迹（T_amb={temp_c:.0f}°C）{style.title_suffix}")

    ax.legend(frameon=False, loc="upper right")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "读图要点：\n"
            "- 四条线分别对应不同初始电量 SOC0；曲线终点即该条件下的 TTE（首次触发欠压/截止条件）。\n"
            "- 本图固定使用场景与功耗随机种子，仅改变 SOC0，便于做“单因素对比”。\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        # 为底部标题与“轴末端标签”预留空间（tight_layout 容易与 set_label_coords 打架）。
        fig.subplots_adjust(left=0.14, right=0.995, top=0.98, bottom=0.20)
        _add_bottom_title(fig, bottom_title, y=0.07, fontsize=12)

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def _plot_tte_vs_soc0_by_temp(
    *,
    mode: PlotMode,
    out_path: Path,
    sc: Scenario,
    temps_c: list[float],
    soc0_list: list[float],
    tte_by_temp: dict[float, list[float]],
) -> None:
    style = apply_style(mode)

    # 用户需求：两张图都改为“偏向正方形”的论文图，便于横向拼接。
    fig_size = (6.2, 6.2) if mode == "paper" else (6.8, 6.8)
    fig, ax = plt.subplots(figsize=fig_size)

    soc_pct = [float(s) * 100.0 for s in soc0_list]
    # 图2配色（用户指定，3 条温度线）
    cube = ["#099F2D", "#008CFF", "#EC5A00"]

    max_tte = 0.0
    for i, temp in enumerate(temps_c):
        ys = tte_by_temp[float(temp)]
        max_tte = max(max_tte, float(np.max(np.asarray(ys, dtype=float))))
        # 颜色按 temps_c 的顺序依次取（Cube Palette），简单直观。
        c = cube[i % 3]
        ax.plot(
            ys,  # x: TTE (h)
            soc_pct,  # y: SOC (%)
            color=c,
            lw=2.6,
            marker="o",
            ms=6.0,
            markeredgecolor="#222222",
            markeredgewidth=0.6,
            label=f"T_amb={_temp_c_to_f_label(temp)}",
        )

    ax.set_xlim(0.0, max_tte * 1.03 if max_tte > 0 else 1.0)
    ax.set_ylim(0.0, 105.0)
    ax.set_yticks([0, 25, 50, 75, 100])

    scenario_title_en_map = {
        "S0_standby": "Standby / Light Background",
        "S1_video": "Video Playback / Streaming",
        "S2_navigation": "Navigation (GPS + Map Data)",
        "S3_gaming": "Gaming (High CPU/GPU Load)",
        "S4_mixed_day": "Mixed Use (Typical Day)",
        "S5_burst_recovery": "Burst Load → Rest (Recovery Demo)",
    }
    sc_title_en = scenario_title_en_map.get(sc.scenario_id, sc.scenario_id)

    if mode == "paper":
        ax.set_xlabel("TTE (h)")
        ax.set_ylabel("SOC (%)")
        bottom_title = f"{sc_title_en}: TTE vs initial SOC0 under different ambient temperatures"
        ax.set_title("")
        ax.xaxis.set_label_coords(1.0, -0.06)
        ax.xaxis.label.set_horizontalalignment("right")
        ax.yaxis.set_label_coords(-0.10, 0.5)
        ax.yaxis.label.set_verticalalignment("center")
    else:
        ax.set_xlabel("耗尽时间 TTE（小时）")
        ax.set_ylabel("SOC（%）")
        ax.set_title(f"{sc.title_zh}：不同温度下的 TTE–初始SOC 关系{style.title_suffix}")

    ax.legend(frameon=False, loc="upper left")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "读图要点：\n"
            "- 三条线只改变环境温度 T_amb，其余保持一致（场景 schedule、功耗随机种子、参数）。\n"
            "- 低温会提高等效内阻并降低有效容量，从而更早触发欠压关机，导致 TTE 下降。\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.subplots_adjust(left=0.14, right=0.995, top=0.98, bottom=0.20)
        _add_bottom_title(fig, bottom_title, y=0.07, fontsize=12)

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def _plot_combined_overlay_and_tte(
    *,
    mode: PlotMode,
    out_path: Path,
    sc: Scenario,
    temp_room_c: float,
    soc0_list: list[float],
    sims_room: dict[float, dict[str, np.ndarray | float | str]],
    temps_c: list[float],
    tte_by_temp: dict[float, list[float]],
) -> None:
    """把两张图横向拼接（共享 y 轴 SOC），并用横向虚线在 SOC=25/50/75/100% 处连接两幅图。"""

    style = apply_style(mode)

    # 组合图：左（SOC–time，室温），右（TTE–SOC0，温度对照）
    # 论文排版更省空间：y 轴只有少量刻度，整张图高度可适当压缩。
    fig_size = (12.8, 4.4) if mode == "paper" else (13.2, 6.6)
    fig = plt.figure(figsize=fig_size)
    gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1.0, 1.0], wspace=0.18)
    ax_l = fig.add_subplot(gs[0, 0])
    ax_r = fig.add_subplot(gs[0, 1], sharey=ax_l)

    # ---------- 左：SOC–time（室温 20°C，四条线） ----------
    colors_soc = ["#099F2D", "#005800", "#33618F", "#86AEE1"]
    max_t = 0.0
    for soc0, c in zip(soc0_list, colors_soc):
        r = sims_room[float(soc0)]
        t_h = np.asarray(r["t_h"], dtype=float)
        soc_pct = np.asarray(r["soc_pct"], dtype=float)
        tte_h = float(r["tte_h"])  # type: ignore[arg-type]
        max_t = max(max_t, tte_h)
        ax_l.plot(t_h, soc_pct, color=c, lw=2.6, label=f"SOC0={soc0*100:.0f}%")
        if t_h.size:
            ax_l.plot([t_h[-1]], [soc_pct[-1]], marker="o", color=c, ms=5.5)

    ax_l.set_xlim(0.0, max_t * 1.02 if max_t > 0 else 1.0)
    ax_l.set_ylim(0.0, 105.0)
    ax_l.set_yticks([0, 25, 50, 75, 100])
    ax_l.legend(frameon=False, loc="upper right")

    # ---------- 右：TTE–SOC0（温度对照，三条线） ----------
    soc_pct_list = [float(s) * 100.0 for s in soc0_list]
    cube = ["#099F2D", "#008CFF", "#EC5A00"]  # 图2配色（用户指定）
    max_tte = 0.0
    for i, temp in enumerate(temps_c):
        xs = tte_by_temp[float(temp)]
        max_tte = max(max_tte, float(np.max(np.asarray(xs, dtype=float))))
        c = cube[i % 3]
        ax_r.plot(
            xs,
            soc_pct_list,
            color=c,
            lw=2.6,
            marker="o",
            ms=5.5,
            markeredgecolor="#222222",
            markeredgewidth=0.6,
            label=f"T_amb={_temp_c_to_f_label(temp)}",
        )

    ax_r.set_xlim(0.0, max_tte * 1.03 if max_tte > 0 else 1.0)
    ax_r.legend(frameon=False, loc="upper left")
    ax_r.tick_params(labelleft=False)  # 共享 y 轴，只在左侧显示刻度标签

    if mode == "paper":
        ax_l.set_xlabel("Time (h)")
        ax_l.set_ylabel("SOC (%)")
        # 让 y 轴标签始终清晰可见：不要贴在 100% 刻度附近，改为居中放置。
        # x 轴标签保持默认位置（避免与面板标题互相遮挡）
        ax_l.yaxis.set_label_coords(-0.12, 0.5)
        ax_l.yaxis.label.set_verticalalignment("center")

        ax_r.set_xlabel("TTE (h)")
        ax_r.set_ylabel("")
        # x 轴标签保持默认位置（避免与面板标题互相遮挡）

        # 面板标题放在各自图下
        ax_l.text(
            0.5,
            -0.22,
            f"(a) SOC vs time under different initial SOC0 (T_amb={temp_room_c:.0f}°C)",
            transform=ax_l.transAxes,
            ha="center",
            va="top",
            fontsize=11,
        )
        ax_r.text(
            0.5,
            -0.22,
            "(b) TTE vs initial SOC0 under different ambient temperatures",
            transform=ax_r.transAxes,
            ha="center",
            va="top",
            fontsize=11,
        )

        # 手动留白（tight_layout 容易与跨轴 artist 冲突）
        # 增大 bottom：让面板标题与 x 轴刻度/标签拉开距离，同时也压缩 y 方向“刻度间距”。
        fig.subplots_adjust(left=0.18, right=0.995, top=0.98, bottom=0.24, wspace=0.22)
    else:
        ax_l.set_xlabel("时间（小时）")
        ax_l.set_ylabel("SOC（%）")
        ax_r.set_xlabel("耗尽时间 TTE（小时）")
        ax_r.set_ylabel("")
        fig.suptitle(f"{sc.title_zh}：初始电量与温度的单因素对照（横向合并图）{style.title_suffix}", y=0.99, fontsize=12)
        fig.subplots_adjust(left=0.10, right=0.995, top=0.93, bottom=0.12, wspace=0.20)

    # ---------- 横向虚线：SOC=25/50/75/100% 串联左右两幅图 ----------
    fig.canvas.draw()
    ys_ref = [25.0, 50.0, 75.0, 100.0]
    l_pos = ax_l.get_position()
    r_pos = ax_r.get_position()
    inv = fig.transFigure.inverted()
    for y in ys_ref:
        _, y_disp = ax_l.transData.transform((0.0, float(y)))
        _, y_fig = inv.transform((0.0, y_disp))
        fig.add_artist(
            Line2D(
                [l_pos.x0, r_pos.x1],
                [y_fig, y_fig],
                transform=fig.transFigure,
                color="#666666",
                linestyle="--",
                linewidth=1.0,
                alpha=0.28,
                zorder=1,
            )
        )

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q2/论文 5.2.1：初始 SOC 与温度对 TTE 的对比图（paper/study）")
    ap.add_argument("--scenario", default="S4_mixed_day", help="场景 ID（默认 S4_mixed_day）")
    ap.add_argument("--tag", default="", help="输出文件名 tag（默认与 --scenario 相同；用于区分不同参数/消融版本）")
    ap.add_argument("--soc0-list", default="1.0,0.75,0.5,0.25", help="SOC0 列表（逗号分隔）")
    ap.add_argument("--temp-room", type=float, default=20.0, help="室温组 T_amb（默认 20°C）")
    ap.add_argument("--temp-list", default="20,-15,38", help="温度列表（逗号分隔，用于 TTE–SOC0 图）")
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒），默认 10s（足够平滑且更快）")
    ap.add_argument("--seed", type=int, default=1, help="功耗随机种子（固定代表性轨迹）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出根目录（默认 src/out_plots）")
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    raw = load_scenarios_json(Path(args.scenarios))
    sc = materialize_scenario(raw, str(args.scenario))

    soc0_list = _parse_float_list(str(args.soc0_list))
    temps_c = _parse_float_list(str(args.temp_list))

    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))

    out_root = Path(args.out_dir).expanduser().resolve() / "q2"
    out_sub = "initial_soc_temperature"
    tag = str(args.tag).strip() or str(args.scenario)

    modes: list[PlotMode] = ["paper", "study"] if not str(args.mode).strip() else [str(args.mode).strip()]  # type: ignore[list-item]
    for mode in modes:
        out_dir = ensure_dir(out_root / str(mode) / out_sub)

        # 图 1：室温（20°C）SOC 叠加
        sims: dict[float, dict[str, np.ndarray | float | str]] = {}
        for soc0 in soc0_list:
            sims[float(soc0)] = _simulate_once(
                sc,
                soc0=float(soc0),
                temp_c=float(args.temp_room),
                power1=power1,
                batt=batt,
                dt_s=float(args.dt),
                seed=int(args.seed),
            )

        out1 = out_dir / f"01_soc_overlay_T{float(args.temp_room):.0f}C_{tag}.png"
        _plot_soc_overlay(
            mode=mode,  # type: ignore[arg-type]
            out_path=out1,
            sc=sc,
            temp_c=float(args.temp_room),
            soc0_list=soc0_list,
            sims=sims,
        )

        # 图 2：不同温度下 TTE–SOC0
        tte_by_temp: dict[float, list[float]] = {}
        for temp in temps_c:
            ys: list[float] = []
            for soc0 in soc0_list:
                r = _simulate_once(
                    sc,
                    soc0=float(soc0),
                    temp_c=float(temp),
                    power1=power1,
                    batt=batt,
                    dt_s=float(args.dt),
                    seed=int(args.seed),
                )
                ys.append(float(r["tte_h"]))  # type: ignore[arg-type]
            tte_by_temp[float(temp)] = ys

        out2 = out_dir / f"02_tte_vs_soc0_by_temp_{tag}.png"
        _plot_tte_vs_soc0_by_temp(
            mode=mode,  # type: ignore[arg-type]
            out_path=out2,
            sc=sc,
            temps_c=temps_c,
            soc0_list=soc0_list,
            tte_by_temp=tte_by_temp,
        )

        # 图 3：合并图（两行面板 + 竖直虚线串联）
        out3 = out_dir / f"03_combined_soc_and_tte_{tag}.png"
        _plot_combined_overlay_and_tte(
            mode=mode,  # type: ignore[arg-type]
            out_path=out3,
            sc=sc,
            temp_room_c=float(args.temp_room),
            soc0_list=soc0_list,
            sims_room=sims,
            temps_c=temps_c,
            tte_by_temp=tte_by_temp,
        )

        print(f"[{mode}] wrote: {out1}")
        print(f"[{mode}] wrote: {out2}")
        print(f"[{mode}] wrote: {out3}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
