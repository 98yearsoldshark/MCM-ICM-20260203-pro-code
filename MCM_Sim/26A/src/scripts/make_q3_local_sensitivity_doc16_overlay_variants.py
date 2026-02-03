#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc16：生成“叠加版 tornado”的多种绘制方式（不覆盖旧版）。

输入：
- doc16 的 CSV：`local_sensitivity_s1_s5_9params.csv`

输出（中文放 doc16 根目录；英文放 doc16/other）：
- v2：叠加线段版（图例移到右下）
- v3：双面板版（左：-5%，右：+5%）
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


PARAM_SYMBOL_EN = {
    "η0": "eta0",
    "SOH": "SOH",
    "α_R": "alpha_R",
    "hA": "hA",
    "k_b": "k_b",
    "k_cpu": "k_cpu",
    "k_gpu": "k_gpu",
    "b_{q,m}": "b_qm",
    "τ_m": "tau_m",
}

SCENARIO_LABEL_ZH = {
    "S1": "S1 待机",
    "S2": "S2 浏览/社交",
    "S3": "S3 视频",
    "S4": "S4 游戏",
    "S5": "S5 导航/通话",
}

SCENARIO_LABEL_EN = {
    "S1": "Standby/Light",
    "S2": "Browsing/Social Media",
    "S3": "Video/Live Streaming",
    "S4": "Gaming",
    "S5": "Navigation/Calling",
}

# 叠加版配色：4 色来自 Skip Gradient；待机用灰色避免“抢戏”。
SCENARIO_COLORS = {
    "S1": "#7a7a7a",  # standby (neutral gray)
    "S2": PALETTE_SKIP_GRADIENT[0],  # purple
    "S3": PALETTE_SKIP_GRADIENT[1],  # cyan
    "S4": PALETTE_SKIP_GRADIENT[2],  # teal
    "S5": PALETTE_SKIP_GRADIENT[3],  # deep teal
}

SEABORN_DEEP_5 = ("#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974")


def _scenario_colors_from_palette(name: str) -> dict[str, str]:
    """给 5 个场景分配更“分类色板（qualitative）”的颜色。

支持：
- tab10：Matplotlib 高对比默认色板（推荐）
- set2：Matplotlib Set2（更柔和）
- seaborn-deep：硬编码 seaborn deep 前 5 色（避免额外依赖）
"""

    name = str(name).strip().lower()
    if name in ("tab10", "tab"):
        cmap = plt.get_cmap("tab10")
        cols = [cmap(i) for i in range(5)]
        return {k: plt.matplotlib.colors.to_hex(cols[i]) for i, k in enumerate(["S1", "S2", "S3", "S4", "S5"])}
    if name in ("set2", "set"):
        cmap = plt.get_cmap("Set2")
        cols = [cmap(i) for i in range(5)]
        return {k: plt.matplotlib.colors.to_hex(cols[i]) for i, k in enumerate(["S1", "S2", "S3", "S4", "S5"])}
    if name in ("seaborn-deep", "deep", "sns-deep"):
        cols = list(SEABORN_DEEP_5)
        return {k: cols[i] for i, k in enumerate(["S1", "S2", "S3", "S4", "S5"])}
    raise ValueError(f"unknown palette: {name!r}")


def _load_rows(csv_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = dict(row)
            # 转数值
            for k in ["tte_base_h", "delta_minus_pct", "delta_plus_pct", "score_absmax_pct"]:
                try:
                    d[k] = float(d.get(k, "nan"))  # type: ignore[assignment]
                except Exception:
                    d[k] = float("nan")  # type: ignore[assignment]
            rows.append(d)
    return rows


def _pick(rows: list[dict[str, object]], scen: str, sym: str) -> tuple[float, float]:
    for r in rows:
        if str(r.get("scenario_code")) == scen and str(r.get("param_symbol")) == sym:
            return float(r["delta_minus_pct"]), float(r["delta_plus_pct"])
    return float("nan"), float("nan")


def _sorted_params(rows: list[dict[str, object]], scen_codes: list[str]) -> list[str]:
    syms = sorted({str(r["param_symbol"]) for r in rows})
    score: dict[str, float] = {}
    for sym in syms:
        vals = []
        for sc in scen_codes:
            dm, dp = _pick(rows, sc, sym)
            if np.isfinite(dm):
                vals.append(abs(float(dm)))
            if np.isfinite(dp):
                vals.append(abs(float(dp)))
        score[sym] = float(max(vals)) if vals else float("nan")
    syms = [s for s in syms if np.isfinite(score.get(s, float("nan")))]
    syms.sort(key=lambda s: float(score.get(s, float("nan"))), reverse=True)
    return syms


def _xlim(rows: list[dict[str, object]]) -> float:
    vals = []
    for r in rows:
        dm = float(r.get("delta_minus_pct", float("nan")))
        dp = float(r.get("delta_plus_pct", float("nan")))
        if np.isfinite(dm):
            vals.append(abs(dm))
        if np.isfinite(dp):
            vals.append(abs(dp))
    m = float(max(vals)) if vals else 1.0
    return max(1.0, m * 1.12)


def _legend_handles(lang: str, scen_codes: list[str]) -> tuple[list[Line2D], list[Line2D]]:
    scen_handles = []
    for sc in scen_codes:
        c = SCENARIO_COLORS.get(sc, "#333333")
        label = SCENARIO_LABEL_EN.get(sc, sc) if lang == "en" else SCENARIO_LABEL_ZH.get(sc, sc)
        scen_handles.append(Line2D([0], [0], color=c, lw=4, label=label))

    pert_handles = [
        Line2D([0], [0], marker="<", color="black", lw=0, markersize=8, label="-5%"),
        Line2D([0], [0], marker=">", color="black", lw=0, markersize=8, label="+5%"),
    ]
    return scen_handles, pert_handles


def _overlay_segments(
    rows: list[dict[str, object]],
    *,
    out_path: Path,
    lang: str,
    colors_by_scenario: dict[str, str] | None = None,
) -> None:
    style = apply_style("paper")
    scen_codes = ["S1", "S2", "S3", "S4", "S5"]
    params = _sorted_params(rows, scen_codes)
    base_y = np.arange(len(params))[::-1]

    xlim = _xlim(rows)
    offsets = np.linspace(-0.24, 0.24, num=len(scen_codes))

    fig, ax = plt.subplots(figsize=(12.8, 6.8))
    ax.axvline(0.0, color="#333333", linewidth=1.1)
    ax.grid(axis="x", linestyle="--", alpha=0.25)

    colors = colors_by_scenario or SCENARIO_COLORS

    for i, sc in enumerate(scen_codes):
        color = colors.get(sc, "#333333")
        alpha = 0.80 if sc == "S1" else 0.88
        lw = 2.8 if sc == "S1" else 3.2
        for j, sym in enumerate(params):
            dm, dp = _pick(rows, sc, sym)
            if not (np.isfinite(dm) and np.isfinite(dp)):
                continue
            y = float(base_y[j] + offsets[i])
            ax.plot([dm, dp], [y, y], color=color, linewidth=lw, alpha=alpha, solid_capstyle="round")
            ax.scatter([dm], [y], marker="<", s=42, color=color, edgecolor="white", linewidth=0.7, zorder=3)
            ax.scatter([dp], [y], marker=">", s=42, color=color, edgecolor="white", linewidth=0.7, zorder=3)

    if lang == "en":
        ylabels = [PARAM_SYMBOL_EN.get(s, s) for s in params]
        title = "Local sensitivity Tornado overlay (S1–S5, ±5% perturbation; 9 parameters)"
    else:
        ylabels = list(params)
        title = "局部敏感性 Tornado 叠加版（S1–S5，±5% 扰动；9 个参量）"

    ax.set_yticks(base_y)
    ax.set_yticklabels(ylabels, fontsize=11)
    ax.set_xlabel("ΔTTE (%)")
    ax.set_title(title)
    ax.set_xlim(-xlim, xlim)

    # 图例移到右下（满足用户要求：右上角信息标度下移）
    # 图例颜色要与实际绘图一致
    def _legend_handles2(lang0: str) -> tuple[list[Line2D], list[Line2D]]:
        scen_handles = []
        for sc in scen_codes:
            c = colors.get(sc, "#333333")
            label = SCENARIO_LABEL_EN.get(sc, sc) if lang0 == "en" else SCENARIO_LABEL_ZH.get(sc, sc)
            scen_handles.append(Line2D([0], [0], color=c, lw=4, label=label))
        pert_handles = [
            Line2D([0], [0], marker="<", color="black", lw=0, markersize=8, label="-5%"),
            Line2D([0], [0], marker=">", color="black", lw=0, markersize=8, label="+5%"),
        ]
        return scen_handles, pert_handles

    scen_handles, pert_handles = _legend_handles2(lang)
    leg1 = ax.legend(
        handles=scen_handles,
        loc="lower right",
        bbox_to_anchor=(0.995, 0.20),
        frameon=False,
        title=("Scenario" if lang == "en" else "场景"),
    )
    ax.add_artist(leg1)
    ax.legend(
        handles=pert_handles,
        loc="lower right",
        bbox_to_anchor=(0.995, 0.02),
        frameon=False,
        title=("Perturbation" if lang == "en" else "扰动"),
    )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig(fig, out_path, mode=style.mode)
    plt.close(fig)


def _overlay_split_panels(rows: list[dict[str, object]], *, out_path: Path, lang: str) -> None:
    """双面板：左=-5%，右=+5%，每面板用“点+细线”表达 5 个场景，减少杂乱。"""

    style = apply_style("paper")
    scen_codes = ["S1", "S2", "S3", "S4", "S5"]
    params = _sorted_params(rows, scen_codes)
    base_y = np.arange(len(params))[::-1]
    offsets = np.linspace(-0.22, 0.22, num=len(scen_codes))
    xlim = _xlim(rows)

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 6.6), sharey=True)
    axL, axR = axes
    for ax in axes:
        ax.axvline(0.0, color="#333333", linewidth=1.0)
        ax.grid(axis="x", linestyle="--", alpha=0.25)
        ax.set_xlim(-xlim, xlim)

    for i, sc in enumerate(scen_codes):
        color = SCENARIO_COLORS.get(sc, "#333333")
        alpha = 0.75 if sc == "S1" else 0.90
        for j, sym in enumerate(params):
            dm, dp = _pick(rows, sc, sym)
            if not (np.isfinite(dm) and np.isfinite(dp)):
                continue
            y = float(base_y[j] + offsets[i])
            # -5% panel
            axL.scatter([dm], [y], s=32, color=color, alpha=alpha, edgecolor="white", linewidth=0.6)
            axL.plot([0.0, dm], [y, y], color=color, alpha=alpha * 0.65, linewidth=1.6)
            # +5% panel
            axR.scatter([dp], [y], s=32, color=color, alpha=alpha, edgecolor="white", linewidth=0.6)
            axR.plot([0.0, dp], [y, y], color=color, alpha=alpha * 0.65, linewidth=1.6)

    if lang == "en":
        ylabels = [PARAM_SYMBOL_EN.get(s, s) for s in params]
        title = "Local sensitivity (split view): -5% vs +5% (S1–S5, 9 parameters)"
        axL.set_title("-5% perturbation")
        axR.set_title("+5% perturbation")
    else:
        ylabels = list(params)
        title = "局部敏感性（分栏）：-5% vs +5%（S1–S5，9 个参量）"
        axL.set_title("-5% 扰动")
        axR.set_title("+5% 扰动")

    axL.set_yticks(base_y)
    axL.set_yticklabels(ylabels, fontsize=11)
    axL.set_xlabel("ΔTTE (%)")
    axR.set_xlabel("ΔTTE (%)")
    fig.suptitle(title, y=0.98)

    scen_handles, _ = _legend_handles(lang, scen_codes)
    # 总图例放右下（图外边界附近）
    fig.legend(
        handles=scen_handles,
        loc="lower right",
        bbox_to_anchor=(0.985, 0.06),
        frameon=False,
        title=("Scenario" if lang == "en" else "场景"),
        ncols=1,
    )

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig(fig, out_path, mode=style.mode)
    plt.close(fig)


def _faceted_row_five_scenarios(rows: list[dict[str, object]], *, out_path: Path, lang: str) -> None:
    """横向拼接 5 个场景（每个子图一个 tornado，纵轴固定 9 参量，便于并排对比）。"""

    style = apply_style("paper")
    scen_codes = ["S1", "S2", "S3", "S4", "S5"]
    params = _sorted_params(rows, scen_codes)

    # 全局 x 轴范围：所有子图保持一致，保证横向对比公平
    xlim = _xlim(rows)

    # y 轴：固定顺序（按全场景最大 |Δ| 排序），各子图共享 y 轴
    base_y = np.arange(len(params))[::-1]

    # 同一子图中绘制两组 bar：-5% 与 +5%（用两色）
    c_minus = PALETTE_SKIP_GRADIENT[3]
    c_plus = PALETTE_SKIP_GRADIENT[0]
    height = 0.32
    offset = 0.18

    fig, axes = plt.subplots(1, 5, figsize=(20.0, 6.4), sharey=True)
    for ax, sc in zip(axes, scen_codes):
        ax.axvline(0.0, color="#333333", linewidth=1.0)
        ax.grid(axis="x", linestyle="--", alpha=0.25)
        ax.set_xlim(-xlim, xlim)

        dm_list = []
        dp_list = []
        for sym in params:
            dm, dp = _pick(rows, sc, sym)
            dm_list.append(float(dm))
            dp_list.append(float(dp))

        y0 = base_y.astype(float)
        ax.barh(y0 - offset, dm_list, height=height, color=c_minus, alpha=0.88)
        ax.barh(y0 + offset, dp_list, height=height, color=c_plus, alpha=0.88)

        if lang == "en":
            ax.set_title(SCENARIO_LABEL_EN.get(sc, sc))
        else:
            # 标题尽量短，避免横向 5 图拥挤
            ax.set_title(SCENARIO_LABEL_ZH.get(sc, sc))

        ax.set_xlabel("ΔTTE (%)")

    # y 轴标签只放最左侧
    if lang == "en":
        ylabels = [PARAM_SYMBOL_EN.get(s, s) for s in params]
        title = "Local sensitivity Tornado (5 scenarios, side-by-side; 9 parameters, ±5%)"
        legend_title = "Perturbation"
    else:
        ylabels = list(params)
        title = "局部敏感性 Tornado（五场景横向拼接；9 个参量；±5%）"
        legend_title = "扰动"

    axes[0].set_yticks(base_y)
    axes[0].set_yticklabels(ylabels, fontsize=11)

    # 其余子图不重复 y tick 标签（让画面更干净）
    for ax in axes[1:]:
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)

    fig.suptitle(title, y=0.985)

    # 图例：移到右下方（图外），避免遮挡任何子图
    handles = [
        Line2D([0], [0], color=c_minus, lw=6, label="-5%"),
        Line2D([0], [0], color=c_plus, lw=6, label="+5%"),
    ]
    fig.legend(
        handles=handles,
        loc="lower right",
        bbox_to_anchor=(0.985, 0.02),
        frameon=False,
        title=legend_title,
        ncols=1,
    )

    fig.tight_layout(rect=(0.0, 0.05, 1.0, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig(fig, out_path, mode=style.mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - doc16 叠加版 tornado 多种绘制方式（不覆盖旧版）")
    ap.add_argument(
        "--doc16-dir",
        default=str(
            SRC_DIR.parent
            / "论文"
            / "理论模型"
            / "论文阶段"
            / "Q3材料"
            / "16-生产需要的内容"
        ),
        help="doc16 输出目录",
    )
    ap.add_argument("--csv-name", default="local_sensitivity_s1_s5_9params.csv", help="输入 CSV 文件名")
    args = ap.parse_args()

    doc16_dir = Path(args.doc16_dir)
    other_dir = doc16_dir / "other"
    other_dir.mkdir(parents=True, exist_ok=True)

    csv_path = doc16_dir / str(args.csv_name)
    rows = _load_rows(csv_path)

    # v2：线段叠加（图例移至右下）
    _overlay_segments(rows, out_path=doc16_dir / "tornado_overlay_S1_S5_v2.png", lang="zh")
    _overlay_segments(rows, out_path=other_dir / "tornado_overlay_S1_S5_v2_en.png", lang="en")

    # v2b：改用分类色板（更高对比度），不覆盖 v2
    colors_tab10 = _scenario_colors_from_palette("tab10")
    _overlay_segments(
        rows,
        out_path=doc16_dir / "tornado_overlay_S1_S5_v2_tab10.png",
        lang="zh",
        colors_by_scenario=colors_tab10,
    )
    _overlay_segments(
        rows,
        out_path=other_dir / "tornado_overlay_S1_S5_v2_tab10_en.png",
        lang="en",
        colors_by_scenario=colors_tab10,
    )

    colors_deep = _scenario_colors_from_palette("seaborn-deep")
    _overlay_segments(
        rows,
        out_path=doc16_dir / "tornado_overlay_S1_S5_v2_deep.png",
        lang="zh",
        colors_by_scenario=colors_deep,
    )
    _overlay_segments(
        rows,
        out_path=other_dir / "tornado_overlay_S1_S5_v2_deep_en.png",
        lang="en",
        colors_by_scenario=colors_deep,
    )

    # v3：双面板（更清爽）
    _overlay_split_panels(rows, out_path=doc16_dir / "tornado_overlay_S1_S5_v3_split.png", lang="zh")
    _overlay_split_panels(rows, out_path=other_dir / "tornado_overlay_S1_S5_v3_split_en.png", lang="en")

    # v4：横向 5 个子图（每个子图一个场景）
    _faceted_row_five_scenarios(rows, out_path=doc16_dir / "tornado_row_S1_S5_v4.png", lang="zh")
    _faceted_row_five_scenarios(rows, out_path=other_dir / "tornado_row_S1_S5_v4_en.png", lang="en")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
