#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 doc16 的 CSV 明细重画 Tornado 图（中文全 9 参量 + 英文版本）。

使用场景：
- 计算已经完成（local_sensitivity_s1_s5_9params.csv 已存在）；
- 仅需要调整图形展示（例如：纵轴显示全部 9 个参量、补英文版）。

输入：
- `论文/理论模型/论文阶段/Q3材料/16-生产需要的内容/local_sensitivity_s1_s5_9params.csv`

输出（默认覆盖中文 5 张图，并把英文版放入 other/）：
- `tornado_S1_*.png` ~ `tornado_S5_*.png`（中文，9 参量）
- `other/tornado_S1_*_en.png` ~ `other/tornado_S5_*_en.png`（英文，9 参量）
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

SCENARIO_LABEL_EN = {
    "S1": "Standby/Light",
    "S2": "Browsing/Social Media",
    "S3": "Video/Live Streaming",
    "S4": "Gaming",
    "S5": "Navigation/Calling",
}

# 叠加版配色：4 色来自 Skip Gradient；待机用灰色避免“抢戏”。
SCENARIO_COLORS = {
    "S1": "#7a7a7a",  # standby
    "S2": "#845ec2",  # browse
    "S3": "#4ffbdf",  # video
    "S4": "#00c2a8",  # gaming
    "S5": "#008b74",  # navigation
}


def _plot_tornado(
    rows: list[dict[str, object]],
    *,
    title: str,
    out_path: Path,
    lang: str,
) -> None:
    style = apply_style("paper")

    # 颜色（Skip Gradient：+ 与 - 各取一色）
    c_plus = PALETTE_SKIP_GRADIENT[0]
    c_minus = PALETTE_SKIP_GRADIENT[3]

    # 按最大绝对影响排序
    rows_sorted = sorted(rows, key=lambda r: float(r.get("score_absmax_pct", float("nan"))), reverse=True)

    def _label(sym: str) -> str:
        return PARAM_SYMBOL_EN.get(sym, sym) if lang == "en" else sym

    labels = [_label(str(r["param_symbol"])) for r in rows_sorted][::-1]
    v_minus = [float(r["delta_minus_pct"]) for r in rows_sorted][::-1]
    v_plus = [float(r["delta_plus_pct"]) for r in rows_sorted][::-1]

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    ax.barh(y, v_minus, color=c_minus, alpha=0.88, label="-5%")
    ax.barh(y, v_plus, color=c_plus, alpha=0.88, label="+5%")
    ax.axvline(0.0, color="#333333", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("ΔTTE (%)")
    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.legend(loc="lower right", frameon=False, ncols=2)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig(fig, out_path, mode=style.mode)
    plt.close(fig)


def _plot_overlay_tornado(
    rows_all: list[dict[str, object]],
    *,
    out_path_zh: Path,
    out_path_en: Path,
) -> None:
    """把 S1~S5 叠加到一张“局部敏感性 tornado”里（更适合做跨场景对比）。"""

    style = apply_style("paper")

    # 按参数聚合，并按“全场景最大 |ΔTTE|”做 tornado 式排序
    param_syms = sorted({str(r["param_symbol"]) for r in rows_all})
    scen_codes = ["S1", "S2", "S3", "S4", "S5"]

    def _pick(rows: list[dict[str, object]], scen: str, sym: str) -> tuple[float, float]:
        for r in rows:
            if str(r.get("scenario_code")) == scen and str(r.get("param_symbol")) == sym:
                return float(r["delta_minus_pct"]), float(r["delta_plus_pct"])
        return float("nan"), float("nan")

    # 计算每个参数的全局“显著性”用于排序
    score: dict[str, float] = {}
    for sym in param_syms:
        vals = []
        for sc in scen_codes:
            dm, dp = _pick(rows_all, sc, sym)
            if np.isfinite(dm):
                vals.append(abs(float(dm)))
            if np.isfinite(dp):
                vals.append(abs(float(dp)))
        score[sym] = float(max(vals)) if vals else float("nan")

    param_syms = [s for s in param_syms if np.isfinite(score.get(s, float("nan")))]
    param_syms.sort(key=lambda s: float(score.get(s, float("nan"))), reverse=True)

    # x 轴范围：全局 max|Δ| 加边距
    all_abs = []
    for sym in param_syms:
        for sc in scen_codes:
            dm, dp = _pick(rows_all, sc, sym)
            if np.isfinite(dm):
                all_abs.append(abs(float(dm)))
            if np.isfinite(dp):
                all_abs.append(abs(float(dp)))
    max_abs = float(max(all_abs)) if all_abs else 1.0
    xlim = max(1.0, max_abs * 1.10)

    def _draw(lang: str, out_path: Path) -> None:
        fig, ax = plt.subplots(figsize=(12.6, 6.6))
        ax.axvline(0.0, color="#333333", linewidth=1.1)
        ax.grid(axis="x", linestyle="--", alpha=0.25)

        # 行间微偏移避免覆盖
        offsets = np.linspace(-0.22, 0.22, num=len(scen_codes))

        # y 从上到下
        base_y = np.arange(len(param_syms))[::-1]

        # 画每个场景：用“区间线段 + 端点箭头”表示 (-5%) 与 (+5%) 的 ΔTTE
        for i, sc in enumerate(scen_codes):
            color = SCENARIO_COLORS.get(sc, "#333333")
            for j, sym in enumerate(param_syms):
                dm, dp = _pick(rows_all, sc, sym)
                if not (np.isfinite(dm) and np.isfinite(dp)):
                    continue
                y = float(base_y[j] + offsets[i])
                ax.plot([dm, dp], [y, y], color=color, linewidth=3.0, alpha=0.85, solid_capstyle="round")
                ax.scatter([dm], [y], marker="<", s=42, color=color, edgecolor="white", linewidth=0.7, zorder=3)
                ax.scatter([dp], [y], marker=">", s=42, color=color, edgecolor="white", linewidth=0.7, zorder=3)

        # y 轴标签
        if lang == "en":
            ylabels = [PARAM_SYMBOL_EN.get(s, s) for s in param_syms]
            title = "Local sensitivity Tornado overlay (S1–S5, ±5% perturbation; 9 parameters)"
        else:
            ylabels = list(param_syms)
            title = "局部敏感性 Tornado 叠加版（S1–S5，±5% 扰动；9 个参量）"

        ax.set_yticks(base_y)
        ax.set_yticklabels(ylabels, fontsize=11)
        ax.set_xlabel("ΔTTE (%)")
        ax.set_title(title)
        ax.set_xlim(-xlim, xlim)

        # 图例：颜色=场景；箭头=扰动方向
        scen_handles = []
        for sc in scen_codes:
            c = SCENARIO_COLORS.get(sc, "#333333")
            label = SCENARIO_LABEL_EN.get(sc, sc) if lang == "en" else sc
            if lang != "en":
                # 中文场景名用 code + 简称，避免过长
                label = {
                    "S1": "S1 待机",
                    "S2": "S2 浏览/社交",
                    "S3": "S3 视频",
                    "S4": "S4 游戏",
                    "S5": "S5 导航/通话",
                }.get(sc, sc)
            scen_handles.append(Line2D([0], [0], color=c, lw=4, label=label))

        pert_handles = [
            Line2D([0], [0], marker="<", color="black", lw=0, markersize=8, label="-5%"),
            Line2D([0], [0], marker=">", color="black", lw=0, markersize=8, label="+5%"),
        ]

        leg1 = ax.legend(handles=scen_handles, loc="upper right", frameon=False, title=("Scenario" if lang == "en" else "场景"))
        ax.add_artist(leg1)
        ax.legend(handles=pert_handles, loc="lower right", frameon=False, title=("Perturbation" if lang == "en" else "扰动"))

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        savefig(fig, out_path, mode=style.mode)
        plt.close(fig)

    _draw("zh", out_path_zh)
    _draw("en", out_path_en)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - doc16 Tornado 重画（中文全参量 + 英文版）")
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
        help="doc16 输出目录（包含 local_sensitivity_s1_s5_9params.csv）",
    )
    ap.add_argument(
        "--csv-name",
        default="local_sensitivity_s1_s5_9params.csv",
        help="输入 CSV 文件名（相对 doc16-dir）",
    )
    args = ap.parse_args()

    doc16_dir = Path(args.doc16_dir)
    csv_path = doc16_dir / str(args.csv_name)
    if not csv_path.exists():
        raise FileNotFoundError(f"缺少输入 CSV：{csv_path}")

    rows_all: list[dict[str, object]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows_all.append(dict(row))

    # 保证数值列可用于排序/绘图
    for row in rows_all:
        for k in ["tte_base_h", "delta_minus_pct", "delta_plus_pct", "score_absmax_pct"]:
            try:
                row[k] = float(row.get(k, "nan"))  # type: ignore[assignment]
            except Exception:
                row[k] = float("nan")  # type: ignore[assignment]

    # 逐场景出图（中文覆盖原图；英文放 other/）
    other_dir = doc16_dir / "other"
    other_dir.mkdir(parents=True, exist_ok=True)

    for s_code in ["S1", "S2", "S3", "S4", "S5"]:
        d = [r for r in rows_all if str(r.get("scenario_code")) == s_code]
        if not d:
            continue
        sc_id = str(d[0].get("scenario_id"))
        sc_zh = str(d[0].get("scenario_label_zh"))
        t0 = float(d[0].get("tte_base_h", float("nan")))

        # 中文：9 参量（不裁剪）
        title_zh = f"局部敏感性 Tornado（{s_code}：{sc_zh}，±5% 扰动；基准 TTE={t0:.2f} h）"
        out_zh = doc16_dir / f"tornado_{s_code}_{sc_id}.png"
        _plot_tornado(d, title=title_zh, out_path=out_zh, lang="zh")

        # 英文：9 参量
        sc_en = SCENARIO_LABEL_EN.get(s_code, sc_id)
        title_en = f"Local sensitivity Tornado ({s_code}: {sc_en}, ±5% perturbation; baseline TTE={t0:.2f} h)"
        out_en = other_dir / f"tornado_{s_code}_{sc_id}_en.png"
        _plot_tornado(d, title=title_en, out_path=out_en, lang="en")

    # 叠加版：S1~S5 放在同一张图（中文 + 英文）
    overlay_zh = doc16_dir / "tornado_overlay_S1_S5.png"
    overlay_en = other_dir / "tornado_overlay_S1_S5_en.png"
    _plot_overlay_tornado(rows_all, out_path_zh=overlay_zh, out_path_en=overlay_en)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
