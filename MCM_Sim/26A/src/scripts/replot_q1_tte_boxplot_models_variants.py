#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06（重绘工具）：基于已生成的统计 CSV，批量重绘“叠加三套箱线图”的版式参数。

用途：
- 你已经有了 `opendata_support_soft_v1_boxplot_models/` 下的统计结果（open data + model0/model1 UQ-lite）；
- 现在只想调“版式参数”（例如横轴刻度间距），不希望重新跑 UQ 采样，也不希望覆盖旧图；
- 本脚本只读 CSV/JSON，输出多张不同参数的 PNG（文件名带后缀）。

默认输入（可用参数覆盖）：
- 统计目录：`Q1材料/06.../other/opendata_support_soft_v1_boxplot_models/`
  - data_opendata_support_boxplot.csv
  - data_model_uq_boxplot.csv
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.patches import Rectangle

from mcm26a.scenarios import load_scenarios_json
from mcm26a.viz.style import PlotMode, apply_style, savefig


COLOR_BLUE = "#008CFF"
COLOR_ORANGE = "#EC5A00"
COLOR_BLACK = "#222222"
COLOR_GRAY = "#999999"


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A

Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "06-模型0vs模型1_TTE对比"
DEFAULT_STATS_DIR = Q1_DIR / "other" / "opendata_support_soft_v1_boxplot_models"


def _add_px_ruler(
    ax: plt.Axes,
    *,
    lengths_px: tuple[int, ...] = (1, 10, 100),
    shift_x_px: float = 0.0,
) -> None:
    """在图的右下角添加像素标尺（用于人工感知 PNG 尺寸）。

    说明：
    - matplotlib 的 `figsize` 用英寸，导出像素由 DPI 决定；
    - 为了让你在查看 PNG 时能直观估计“长度≈多少像素”，这里画一组 1/10/100 px 的标尺。
    - 只用于“阅读/学习”，论文图一般不需要。
    """

    fig = ax.figure
    # 需要先 draw 才能得到 Axes 在画布上的真实像素 bbox。
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    w_px = float(bbox.width)
    if not math.isfinite(w_px) or w_px <= 0:
        return

    x_right = 0.985
    y0 = 0.07
    vgap = 0.038
    pad_x = 0.006

    # 支持“整体右移/左移”（像素 -> axes fraction）
    if math.isfinite(float(shift_x_px)) and float(shift_x_px) != 0.0:
        x_right = float(x_right) + float(shift_x_px) / w_px

    lens = tuple(int(x) for x in lengths_px if int(x) > 0)
    if not lens:
        return
    lens = tuple(sorted(set(lens)))

    max_frac = max(lens) / w_px
    # 预留给文本的宽度（axes fraction，经验值）
    text_w = 0.065
    rect = Rectangle(
        (x_right - max_frac - text_w - 2 * pad_x, y0 - 0.03),
        max_frac + text_w + 3 * pad_x,
        (len(lens) - 1) * vgap + 0.09,
        transform=ax.transAxes,
        facecolor="white",
        alpha=0.75,
        edgecolor="none",
        zorder=6,
        clip_on=False,
    )
    ax.add_patch(rect)

    for i, L in enumerate(lens):
        frac = float(L) / w_px
        y = y0 + i * vgap
        x0 = x_right - frac
        ax.plot(
            [x0, x_right],
            [y, y],
            transform=ax.transAxes,
            color=COLOR_BLACK,
            lw=1.6,
            solid_capstyle="butt",
            zorder=7,
            clip_on=False,
        )
        ax.text(
            x0 - pad_x,
            y,
            f"{L}px",
            transform=ax.transAxes,
            ha="right",
            va="center",
            fontsize=8,
            color=COLOR_BLACK,
            zorder=7,
            clip_on=False,
        )


def _draw_shifted_y_axis_line(ax: plt.Axes, *, shift_px: float) -> None:
    """将 y 轴“竖线+刻度线”向右平移 shift_px（像素），但不移动 y 轴刻度文本。

    说明：
    - 这相当于“在图内部画一根 y 轴”，并把默认 y 轴的 tick mark 隐藏，只保留 tick label。
    - 适合做版式对齐（例如给左侧腾出空间），而不改变读者看到的刻度文字位置。
    """

    if not (math.isfinite(float(shift_px)) and float(shift_px) != 0.0):
        return

    fig = ax.figure
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    w_px = float(bbox.width)
    if not math.isfinite(w_px) or w_px <= 0:
        return

    frac = float(shift_px) / w_px
    frac = max(0.0, min(0.9, frac))  # 防止画到图外/太靠右

    # 隐藏默认 y 轴竖线，避免出现“双竖线”
    ax.spines["left"].set_visible(False)
    # 隐藏默认 tick mark，但保留 tick label（文字）
    ax.tick_params(axis="y", which="both", length=0)

    # 画新的竖线（从底到顶）
    ax.plot([frac, frac], [0.0, 1.0], transform=ax.transAxes, color=COLOR_BLACK, lw=1.6, zorder=5)

    # 画新的 tick mark（与文字对齐）
    ticks = list(ax.get_yticks())
    # tick mark 的长度（像素）-> axes fraction
    tick_len_px = 6.0
    tick_len_frac = tick_len_px / w_px
    trans = ax.get_yaxis_transform()  # x: axes, y: data
    for y in ticks:
        if not math.isfinite(float(y)):
            continue
        ax.plot(
            [frac - tick_len_frac, frac],
            [float(y), float(y)],
            transform=trans,
            color=COLOR_BLACK,
            lw=1.2,
            solid_capstyle="butt",
            zorder=5,
        )


def _shift_y_axis(ax: plt.Axes, *, shift_px: float) -> None:
    """将 y 轴（竖线+刻度+刻度文字）整体向右平移 shift_px（像素）。"""

    if not (math.isfinite(float(shift_px)) and float(shift_px) != 0.0):
        return

    fig = ax.figure
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    w_px = float(bbox.width)
    if not math.isfinite(w_px) or w_px <= 0:
        return

    frac = float(shift_px) / w_px
    frac = max(0.0, min(0.9, frac))
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_position(("axes", frac))
    ax.yaxis.set_ticks_position("left")
    ax.yaxis.set_label_position("left")


def _add_vline_from_right(ax: plt.Axes, *, offset_px: float) -> None:
    """在图的右侧，距离边界 offset_px（像素）的位置画竖直虚线（axes 坐标系）。"""

    if not (math.isfinite(float(offset_px)) and float(offset_px) > 0.0):
        return

    fig = ax.figure
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    w_px = float(bbox.width)
    if not math.isfinite(w_px) or w_px <= 0:
        return

    x_frac = 1.0 - float(offset_px) / w_px
    x_frac = max(0.0, min(1.0, x_frac))
    ax.plot(
        [x_frac, x_frac],
        [0.0, 1.0],
        transform=ax.transAxes,
        color=COLOR_BLACK,
        alpha=0.35,
        lw=1.2,
        linestyle="--",
        zorder=4,
    )


def _plot_boxplot_overlay_from_stats(
    *,
    labels: list[str],
    open_stats: list[dict[str, float]],
    open_n_eff: list[float],
    m0_stats: list[dict[str, float]],
    m1_stats: list[dict[str, float]],
    n_model_samples: int,
    x_gap: float,
    x_gap_add_px: float,
    layout: str,
    fig_w: float,
    y_tick_pad: float,
    y_text_shift_px: float,
    legend_anchor_x: float,
    legend_fontsize: float,
    y_axis_line_shift_px: float,
    y_axis_shift_px: float,
    right_dash_from_right_px: float,
    cover_fontsize: float,
    cover_up_px: float,
    px_ruler_shift_px: float,
    add_px_ruler: bool,
    mode: PlotMode,
    lang: str,
    out_png: Path,
) -> None:
    style = apply_style(mode)

    # 通过“类别中心间距”控制横向刻度距离（而不是简单缩小画布）。
    gap = float(x_gap)
    if gap <= 0:
        raise ValueError("x_gap must be positive")

    fig = plt.figure(figsize=(float(fig_w), 4.8))
    ax = plt.gca()

    n = len(labels)
    # 以“像素增量”的方式调整相邻刻度的间距：仅对 cluster 布局有效（xlim 固定）。
    if layout == "cluster" and math.isfinite(float(x_gap_add_px)) and float(x_gap_add_px) != 0.0:
        fig.canvas.draw()
        bbox = ax.get_window_extent()
        w_px = float(bbox.width)
        if math.isfinite(w_px) and w_px > 0:
            x_range = float(n)  # xlim=[0.5,n+0.5] => range=n
            gap = gap + float(x_gap_add_px) * x_range / w_px
            gap = float(np.clip(gap, 0.35, 1.80))
    if layout == "fill":
        # 让内容“铺满”横向：gap 只改变数据尺度，同时 xlim 也随之缩放（视觉差异不大，但适合保持紧凑铺满）。
        positions = 1.0 + gap * np.arange(n, dtype=float)
        xlim = (positions[0] - 0.75 * gap, positions[-1] + 0.75 * gap)
    elif layout == "cluster":
        # 让刻度“靠近”：positions 收缩，但 xlim 固定为 [0.5, n+0.5]，因此视觉上间距会明显变小。
        center = (n + 1) / 2.0
        base = np.arange(1.0, n + 1.0, dtype=float)
        positions = center + gap * (base - center)
        xlim = (0.5, n + 0.5)
    else:
        raise ValueError(f"unknown layout: {layout!r}")

    # open data（大箱体）
    bxp_open = [
        {"med": st["q50"], "q1": st["q25"], "q3": st["q75"], "whislo": st["q05"], "whishi": st["q95"], "fliers": []}
        for st in open_stats
    ]
    bp = ax.bxp(bxp_open, positions=positions, widths=0.55 * gap, showfliers=False, patch_artist=True)
    for box in bp["boxes"]:
        box.set(facecolor=COLOR_GRAY, alpha=0.16, edgecolor=COLOR_BLACK, linewidth=1.2)
    for med in bp["medians"]:
        med.set(color=COLOR_BLACK, linewidth=1.6)
    for w in bp["whiskers"]:
        w.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)
    for c in bp["caps"]:
        c.set(color=COLOR_BLACK, alpha=0.55, linewidth=1.2)

    # Model-0 / Model-1（小箱体：左右错位，参数随 gap 缩放）
    dx = 0.22 * gap
    w_small = 0.18 * gap
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

    # 对数刻度
    ax.set_yscale("log")
    ticks = [2, 4, 8, 16, 32]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t}h" for t in ticks])
    # y 轴文字像素级平移：将 px 换算为 point（matplotlib 的 pad/labelpad 单位是 point）
    shift_pt = 0.0
    if math.isfinite(float(y_text_shift_px)) and float(y_text_shift_px) != 0.0:
        shift_pt = 72.0 * float(y_text_shift_px) / float(fig.dpi)  # px -> pt
    axis_shift_pt = 0.0
    if math.isfinite(float(y_axis_shift_px)) and float(y_axis_shift_px) != 0.0:
        axis_shift_pt = 72.0 * float(y_axis_shift_px) / float(fig.dpi)  # px -> pt

    # 把 y 轴刻度标签向中心（右侧）微移：用于缩短横向长度时减少左边距占用
    # 约定：y_text_shift_px>0 表示“向右移动”，因此 pad 需要减小（更负/更小）
    # 约定：y_axis_shift_px>0 表示“y 轴整体向右移”，默认会带着文字一起走；
    # 为实现“只移动竖线+刻度，不移动 y 轴文字”，这里用 pad 的反向补偿抵消这部分位移。
    ax.tick_params(axis="y", which="major", pad=float(y_tick_pad) - float(shift_pt) + float(axis_shift_pt))

    ax.set_xlim(*xlim)

    # 给顶部留空间：用于标注“模型偏差”两行文字
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
    # y 轴标题：与刻度文字一起做“像素级定位”
    if math.isfinite(float(shift_pt)) or math.isfinite(float(axis_shift_pt)):
        if float(shift_pt) != 0.0 or float(axis_shift_pt) != 0.0:
            ax.yaxis.labelpad = float(ax.yaxis.labelpad) - float(shift_pt) + float(axis_shift_pt)

    handles = [
        Patch(facecolor=COLOR_GRAY, edgecolor=COLOR_BLACK, alpha=0.16, label=lab_open),
        Patch(facecolor=COLOR_BLUE, edgecolor=COLOR_BLUE, alpha=0.40, label=lab_m0),
        Patch(facecolor=COLOR_ORANGE, edgecolor=COLOR_ORANGE, alpha=0.40, label=lab_m1),
    ]
    ax.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(float(legend_anchor_x), 1.0),
        frameon=False,
        fontsize=float(legend_fontsize),
        handlelength=1.4,
        handleheight=0.8,
        labelspacing=0.35,
        borderpad=0.2,
    )

    # 顶部：模型偏差；底部：覆盖度
    cover_texts: list[plt.Text] = []
    for i, x in enumerate(positions):
        o_med = float(open_stats[i]["q50"])
        m0_med = float(m0_stats[i]["q50"])
        m1_med = float(m1_stats[i]["q50"])
        y_local = float(np.nanmax([float(open_stats[i]["q95"]), float(m0_stats[i]["q95"]), float(m1_stats[i]["q95"])]))
        if math.isfinite(y_local) and y_local > 0 and math.isfinite(o_med) and o_med > 0:
            d0 = 100.0 * (m0_med / o_med - 1.0) if (math.isfinite(m0_med) and m0_med > 0) else float("nan")
            d1 = 100.0 * (m1_med / o_med - 1.0) if (math.isfinite(m1_med) and m1_med > 0) else float("nan")
            s0 = f"{d0:+.1f}%" if math.isfinite(d0) else "NA"
            s1 = f"{d1:+.1f}%" if math.isfinite(d1) else "NA"
            ax.text(x, y_local * 1.08, f"M0 vs Open: {s0}", ha="center", va="bottom", fontsize=9, color=COLOR_BLUE)
            ax.text(x, y_local * 1.20, f"M1 vs Open: {s1}", ha="center", va="bottom", fontsize=9, color=COLOR_ORANGE)

        ne = float(open_n_eff[i])
        ne_s = f"{ne:.1f}" if math.isfinite(ne) else "NA"
        # S1 的“下界”注释单独成行：减少横向占用，避免与 S2 文本重叠
        if i == 0:
            extra2 = "\u2020 lower bound" if lang == "en" else "\u2020 下界"
            cover = f"n_eff(open)={ne_s}\n" + f"n(model)={int(n_model_samples)}\n" + f"{extra2}"
        else:
            cover = f"n_eff(open)={ne_s}\n" + f"n(model)={int(n_model_samples)}"
        t = ax.text(
            x,
            -0.16,
            cover,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=float(cover_fontsize),
            color=COLOR_BLACK,
        )
        cover_texts.append(t)

    if style.annotate:
        if lang == "en":
            note = (
                "Notes: Grey boxes are derived from AndroWatts (TTE≈E/P) using rule-based *soft* mapping.\n"
                "Blue/orange boxes are model UQ-lite samples by perturbing interpretable parameters.\n"
                "† S1 is a lower bound due to limited deep-standby coverage in the open dataset."
            )
        else:
            note = (
                "说明：灰色箱线图来自 AndroWatts 的‘量级支撑’（TTE≈E/P），并使用规则化软映射。\n"
                "蓝/橘小箱体为模型的轻量不确定性采样（可解释参数扰动）。\n"
                "† S1：由于公开数据集缺少深度待机覆盖，因此仅能提供量级下界。"
            )
        fig.text(0.01, 0.01, note, ha="left", va="bottom", fontsize=9)
        # 底部留白：需要容纳 2~3 行覆盖度文字 + 说明文字
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 1.0))
    else:
        # paper 版：仍要给 x 轴下方的覆盖度文字留白（S1 为 3 行）
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 1.0))

    # y 轴整体平移（竖线+刻度+文字）。若使用此项，不建议再用“仅竖线平移”。
    if math.isfinite(float(y_axis_shift_px)) and float(y_axis_shift_px) != 0.0:
        _shift_y_axis(ax, shift_px=float(y_axis_shift_px))
    elif math.isfinite(float(y_axis_line_shift_px)) and float(y_axis_line_shift_px) != 0.0:
        _draw_shifted_y_axis_line(ax, shift_px=float(y_axis_line_shift_px))

    if math.isfinite(float(right_dash_from_right_px)) and float(right_dash_from_right_px) > 0.0:
        _add_vline_from_right(ax, offset_px=float(right_dash_from_right_px))

    if add_px_ruler:
        _add_px_ruler(ax, shift_x_px=float(px_ruler_shift_px))

    # 覆盖度文字整体上移（像素 -> axes fraction）
    if cover_texts and math.isfinite(float(cover_up_px)) and float(cover_up_px) != 0.0:
        fig.canvas.draw()
        bbox = ax.get_window_extent()
        h_px = float(bbox.height)
        if math.isfinite(h_px) and h_px > 0:
            dy = float(cover_up_px) / h_px
            for t in cover_texts:
                tx, ty = t.get_position()
                t.set_position((tx, float(ty) + dy))

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1-06：重绘叠加箱线图（只调版式参数，不重跑 UQ）")
    ap.add_argument("--stats-dir", default=str(DEFAULT_STATS_DIR), help="统计结果目录（包含 data_*_boxplot.csv）")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json"),
        help="Q1 五场景配置 JSON（用于取 label）",
    )
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式")
    ap.add_argument("--x-gap", type=float, default=0.90, help="横轴类别中心间距（<1 更紧凑；默认 0.90）")
    ap.add_argument("--x-gap-add-px", type=float, default=0.0, help="在相邻刻度间距上额外增加的像素（仅对 cluster 有效）")
    ap.add_argument("--fig-w", type=float, default=8.6, help="画布宽度（英寸）：越小越“扁”（默认 8.6）")
    ap.add_argument("--y-tick-pad", type=float, default=-10.0, help="y 轴刻度标签 pad（负数向内移；默认 -10）")
    ap.add_argument("--y-text-shift-px", type=float, default=0.0, help="y 轴文字整体向右(+)/向左(-)移动的像素（刻度+轴标题）")
    ap.add_argument("--legend-x", type=float, default=0.92, help="图例 bbox_to_anchor 的 x（<1 向中心移动；默认 0.92）")
    ap.add_argument("--legend-fontsize", type=float, default=10.0, help="图例字号（默认 10）")
    ap.add_argument("--y-axis-line-shift-px", type=float, default=0.0, help="移动 y 轴竖线+刻度线的像素（刻度文字不动）")
    ap.add_argument("--y-axis-shift-px", type=float, default=0.0, help="y 轴整体（竖线+刻度+文字）向右(+)/向左(-)移动的像素")
    ap.add_argument("--right-dash-from-right-px", type=float, default=0.0, help="右侧距边界多少像素处画竖直虚线（0 表示不画）")
    ap.add_argument("--cover-fontsize", type=float, default=9.0, help="底部覆盖度文字字号（默认 9）")
    ap.add_argument("--cover-up-px", type=float, default=0.0, help="底部覆盖度文字整体上移的像素（默认 0）")
    ap.add_argument("--px-ruler-shift-px", type=float, default=0.0, help="右下角像素标尺整体右移(+)/左移(-)的像素（默认 0）")
    ap.add_argument("--px-ruler", action="store_true", help="在右下角添加 1/10/100 px 标尺（用于阅读，不建议论文图）")
    ap.add_argument(
        "--layout",
        default="cluster",
        choices=("cluster", "fill"),
        help="横向布局：cluster=刻度更靠近（更明显）；fill=铺满横向（旧行为）",
    )
    ap.add_argument(
        "--suffix",
        default="",
        help="输出文件名后缀（例如 xgap090）；为空则自动用 xgap<value> 命名",
    )

    args = ap.parse_args()

    stats_dir = Path(args.stats_dir).expanduser().resolve()
    if not stats_dir.exists():
        raise SystemExit(f"stats_dir not found: {stats_dir}")

    df_open = pd.read_csv(stats_dir / "data_opendata_support_boxplot.csv")
    df_model = pd.read_csv(stats_dir / "data_model_uq_boxplot.csv")

    raw = load_scenarios_json(Path(args.scenarios))
    order = ["S1_standby_light", "S2_browse_social", "S3_video_streaming", "S4_gaming", "S5_nav_call"]
    labels: list[str] = []
    for sid in order:
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        labels.append(title_en if str(args.lang) == "en" else title_zh)

    # open stats
    open_stats: list[dict[str, float]] = []
    open_n_eff: list[float] = []
    for sid in order:
        r = df_open.loc[df_open["scenario_id"] == sid].iloc[0]
        open_n_eff.append(float(r["n_eff"]))
        open_stats.append(
            {
                "q05": float(r["q05_h"]),
                "q25": float(r["q25_h"]),
                "q50": float(r["q50_h"]),
                "q75": float(r["q75_h"]),
                "q95": float(r["q95_h"]),
            }
        )

    # model stats
    def get_model_stats(model: str) -> tuple[list[dict[str, float]], int]:
        out: list[dict[str, float]] = []
        n_samples = None
        for sid in order:
            r = df_model.loc[(df_model["scenario_id"] == sid) & (df_model["model"] == model)].iloc[0]
            if n_samples is None:
                n_samples = int(r["n_samples"])
            out.append(
                {
                    "q05": float(r["q05_h"]),
                    "q25": float(r["q25_h"]),
                    "q50": float(r["q50_h"]),
                    "q75": float(r["q75_h"]),
                    "q95": float(r["q95_h"]),
                }
            )
        return out, int(n_samples or 0)

    m0_stats, n0 = get_model_stats("model0")
    m1_stats, n1 = get_model_stats("model1")
    n_model = min(n0, n1) if (n0 > 0 and n1 > 0) else max(n0, n1)

    suffix = str(args.suffix).strip()
    if not suffix:
        suffix = (
            f"{args.layout}_xgap{int(round(float(args.x_gap) * 100)):03d}"
            f"_w{int(round(float(args.fig_w) * 10)):03d}"
            f"_ypad{int(round(float(args.y_tick_pad))):+03d}"
            f"_leg{int(round(float(args.legend_x) * 100)):03d}"
        )

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = stats_dir / (f"figure_{m}_{suffix}.png")
        _plot_boxplot_overlay_from_stats(
            labels=labels,
            open_stats=open_stats,
            open_n_eff=open_n_eff,
            m0_stats=m0_stats,
            m1_stats=m1_stats,
            n_model_samples=int(n_model),
            x_gap=float(args.x_gap),
            x_gap_add_px=float(args.x_gap_add_px),
            layout=str(args.layout),
            fig_w=float(args.fig_w),
            y_tick_pad=float(args.y_tick_pad),
            y_text_shift_px=float(args.y_text_shift_px),
            legend_anchor_x=float(args.legend_x),
            legend_fontsize=float(args.legend_fontsize),
            y_axis_line_shift_px=float(args.y_axis_line_shift_px),
            y_axis_shift_px=float(args.y_axis_shift_px),
            right_dash_from_right_px=float(args.right_dash_from_right_px),
            cover_fontsize=float(args.cover_fontsize),
            cover_up_px=float(args.cover_up_px),
            px_ruler_shift_px=float(args.px_ruler_shift_px),
            add_px_ruler=bool(args.px_ruler),
            mode=m,  # type: ignore[arg-type]
            lang=str(args.lang),
            out_png=out_png,
        )

    print(f"[OK] replot done: {stats_dir} (suffix={suffix}, x_gap={args.x_gap})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
