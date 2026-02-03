#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q3 数据集实验（AndroWatts）图像，paper/study 两套。

读取：
- out_reports/q3/observed_open_data/cases_tte.csv
- out_reports/q3/observed_open_data/variance_decomposition_usage.csv

输出：
- out_plots/q3/{paper|study}/observed_open_data/
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, PlotMode, apply_style, ensure_dir, savefig


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _fig_tte_vs_obs_power(rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    x = []
    y = []
    for r in rows:
        try:
            p = float(r.get("obs_total_w", "nan"))
            t = float(r.get("tte_mean_h", "nan"))
        except Exception:
            continue
        if np.isfinite(p) and np.isfinite(t) and p > 0:
            x.append(p)
            y.append(t)

    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)

    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    hb = ax.hexbin(xx, yy, gridsize=32, cmap="Blues", mincnt=1, linewidths=0.0, alpha=0.95)
    cbar = fig.colorbar(hb, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label("样本密度（格内点数）")

    ax.set_xlabel("观测总功耗（W，AndroWatts rail 聚合）")
    ax.set_ylabel("模型预测 TTE 均值（小时）")
    ax.set_title(f"Q3：真实状态样本的 TTE 分布（AndroWatts）{style.title_suffix}")
    ax.set_ylim(bottom=0.0)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：每个点对应一个 AndroWatts 聚合样本（约 30 秒的真实设备状态），我们将其映射为单段循环场景并预测耗尽时间。\n"
            "该图用于展示“使用状态分布（亮度/频率/流量等）”本身即可造成显著的续航差异（Q3：fluctuations in usage patterns）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_variance_decomposition_usage(rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)
    if not rows:
        raise ValueError("variance_decomposition_usage.csv 为空")
    r = rows[0]
    vb = float(r.get("var_between_usage_h2", "nan"))
    vw = float(r.get("var_within_seed_h2", "nan"))
    vt = float(r.get("var_total_h2", "nan"))
    fb = float(r.get("frac_between_usage", "nan"))
    fw = float(r.get("frac_within_seed", "nan"))

    def _fmt_pct(x: float) -> str:
        if not np.isfinite(x):
            return "?"
        v = float(x) * 100.0
        # 避免出现 0.0% 导致读者误判“真的为 0”
        if v < 0.05:
            return "<0.1%"
        return f"{v:.1f}%"

    # 用“水平 100% 堆叠条形图”避免 legend/文字遮挡（单一类别更直观、也更适合论文排版）。
    c_usage = PALETTE_SKIP_GRADIENT[0]  # 紫
    c_seed = PALETTE_SKIP_GRADIENT[3]  # 深绿（小块更容易看清）
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.barh([0], [fb], left=[0.0], color=c_usage, alpha=0.95, height=0.55, edgecolor="white", linewidth=1.2)
    ax.barh([0], [fw], left=[fb], color=c_seed, alpha=0.95, height=0.55, edgecolor="white", linewidth=1.2)
    ax.set_yticks([0])
    ax.set_yticklabels(["AndroWatts 样本集"])
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("方差占比（0~1）")
    title_main = f"Q3：TTE 波动来源分解（真实使用状态集）{style.title_suffix}"
    if np.isfinite(fb) and np.isfinite(fw):
        ax.set_title(f"{title_main}\n使用 {_fmt_pct(fb)} | 随机过程 {_fmt_pct(fw)}")
    else:
        ax.set_title(title_main)
    # 横向条形图更适合展示 x 轴网格
    ax.grid(axis="x", alpha=0.22)
    ax.grid(axis="y", visible=False)

    # 直接在条形上标注百分比，避免图例遮挡；小块则把字号调小。
    if np.isfinite(fb) and fb > 0:
        ax.text(
            fb / 2.0,
            0,
            f"使用状态 {_fmt_pct(fb)}",
            ha="center",
            va="center",
            fontsize=10,
            color="white",
        )
    if np.isfinite(fw) and fw > 0:
        # fw 较小时，块内文字容易被裁剪/拥挤：优先采用块外一行标注。
        if fw >= 0.12:
            ax.text(
                fb + fw / 2.0,
                0,
                f"随机过程 {_fmt_pct(fw)}",
                ha="center",
                va="center",
                fontsize=10,
                color="white",
            )
        else:
            ax.text(
                1.01,
                0,
                f"随机过程 {_fmt_pct(fw)}",
                transform=ax.get_yaxis_transform(),  # x 用轴坐标，避免被裁剪
                ha="left",
                va="center",
                fontsize=9,
                color="#333333",
            )

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：用 law of total variance 近似分解总体波动：Var(T)=Var(E[T|case])+E[Var(T|case)]。\n"
            f"绝对方差（h^2）：Var_usage={vb:.3g}，Var_seed={vw:.3g}，Var_total={vt:.3g}。\n"
            "若 seed 占比很小，表示“同一使用状态下的随机波动”较弱；续航差异主要来自状态本身差异或参数/老化差异。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 AndroWatts 数据集实验出图（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q3/paper 与 q3/study）")
    ap.add_argument(
        "--reports-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_open_data"),
        help="输入报表目录（默认 out_reports/q3/observed_open_data）",
    )
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    cases_path = reports_dir / "cases_tte.csv"
    decomp_path = reports_dir / "variance_decomposition_usage.csv"
    if not cases_path.exists() or not decomp_path.exists():
        raise FileNotFoundError("缺少报表文件：请先运行 scripts/run_q3_open_data_experiment.py")

    cases_rows = _read_csv(cases_path)
    decomp_rows = _read_csv(decomp_path)

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_dir = ensure_dir(Path(args.out_dir) / "q3" / str(m) / "observed_open_data")

        fig = _fig_tte_vs_obs_power(cases_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "01_tte_vs_obs_power.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        import matplotlib.pyplot as plt

        plt.close(fig)

        fig = _fig_variance_decomposition_usage(decomp_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "02_variance_decomposition_usage.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)

        print(f"[{m}] generated 2 figures -> {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
