# -*- coding: utf-8 -*-
# 论文级图片重绘脚本：把旧 run 目录中的 runs.csv 重新画成更“可投论文”的图。
#
# 为什么需要它？
# - 仿真结果（runs.csv）可能已经生成，但早期绘图版本较朴素，色条/标注信息不足。
# - 本脚本只读 runs.csv 并重绘图片，不需要重新跑仿真（省时、可复现）。
#
# 用法：
#   1) 重绘单个 run 目录：
#      python MCM_Sim/24A/scripts/make_figures.py --in-dir MCM_Sim/24A/outputs/run-XXXX
#
#   2) 批量重绘 outputs 下所有 run 子目录：
#      python MCM_Sim/24A/scripts/make_figures.py --in-dir MCM_Sim/24A/outputs
#
# 输出：
# - 默认写到每个 run 目录下的 `figures_paper/` 子目录。

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parents[1]  # MCM_Sim/24A
SRC_DIR = THIS_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm24a.plotting import plot_bet_hedging_triptych, plot_grid_heatmap, plot_tradeoff_scatter  # noqa: E402


def _maybe_float_list(vals: pd.Series) -> list[float] | None:
    try:
        xs = sorted({float(x) for x in vals.dropna().tolist()})
        return xs
    except Exception:
        return None


def render_one(run_dir: Path, *, out_subdir: str = "figures_paper") -> None:
    runs_csv = run_dir / "runs.csv"
    if not runs_csv.exists():
        return

    df = pd.read_csv(runs_csv)
    out_dir = run_dir / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    gammas = _maybe_float_list(df.get("gamma", pd.Series([], dtype=float)))
    ws = _maybe_float_list(df.get("w", pd.Series([], dtype=float)))

    # bet-hedging / 风险指标
    if {"P_ext", "P_host", "mean_H"}.issubset(df.columns):
        plot_bet_hedging_triptych(
            df,
            gammas=gammas,
            ws=ws,
            out_path=out_dir / "bet_hedging_triptych.png",
            subtitle="paper: 网格线 + 数值标注 + 最优点星标",
            annotate=True,
        )
        plot_tradeoff_scatter(
            df,
            out_path=out_dir / "pareto_tradeoff.png",
            x_col="P_host",
            y_col="P_ext",
            title="策略风险权衡：P_host vs P_ext（越靠左下越好）",
            annotate_top_k=6,
            auto_zoom=True,
        )

    # Q3：恢复指标（当 P_ext 全为 0 时也往往有信息）
    if {"P_rec_N", "median_T_rec_N"}.issubset(df.columns):
        years = float(df["years"].iloc[0]) if "years" in df.columns and len(df) > 0 else float("nan")
        df2 = df.copy()
        for col in ["median_T_rec_N", "q10_T_rec_N", "q90_T_rec_N", "median_T_rec_H", "q10_T_rec_H", "q90_T_rec_H"]:
            if col in df2.columns and np.isfinite(years):
                df2[col] = df2[col].replace([np.inf, -np.inf], years)

        plot_grid_heatmap(
            df2,
            value_col="P_rec_N",
            gammas=gammas,
            ws=ws,
            title="恢复成功率 P_rec_N（从最坏低谷回升到 target）",
            out_path=out_dir / "P_rec_N.png",
            vmin=0.0,
            vmax=1.0,
            cmap="viridis",
            annotate=True,
        )

        if np.isfinite(years):
            plot_grid_heatmap(
                df2,
                value_col="median_T_rec_N",
                gammas=gammas,
                ws=ws,
                title=f"恢复时间 median_T_rec_N（inf 记为 {int(years)} 年）",
                out_path=out_dir / "median_T_rec_N.png",
                vmin=0.0,
                vmax=years,
                cmap="magma",
                annotate=True,
                fmt="{:.1f}",
            )

    # 尾部风险/几何平均：避免“概率饱和”导致图信息量不足
    if {"q10_min_N", "N_q"}.issubset(df.columns):
        N_q = float(df["N_q"].iloc[0]) if len(df) > 0 else 0.0
        plot_grid_heatmap(
            df,
            value_col="q10_min_N",
            gammas=gammas,
            ws=ws,
            title="尾部风险：q10_min_N（最坏低谷 10% 分位数）",
            out_path=out_dir / "q10_min_N.png",
            cmap="coolwarm",
            center=N_q,
            robust=True,
            annotate=True,
            fmt="{:.2f}",
            contour_levels=[N_q],
        )

    if {"q10_min_H", "H_safe"}.issubset(df.columns):
        H_safe = float(df["H_safe"].iloc[0]) if len(df) > 0 else 0.0
        plot_grid_heatmap(
            df,
            value_col="q10_min_H",
            gammas=gammas,
            ws=ws,
            title="尾部风险：q10_min_H（宿主最低谷 10% 分位数）",
            out_path=out_dir / "q10_min_H.png",
            cmap="coolwarm",
            center=H_safe,
            robust=True,
            annotate=True,
            fmt="{:.2f}",
            contour_levels=[H_safe],
        )

    if "geom_mean_N" in df.columns:
        plot_grid_heatmap(
            df,
            value_col="geom_mean_N",
            gammas=gammas,
            ws=ws,
            title="几何平均：geom_mean_N（burn-in 后）",
            out_path=out_dir / "geom_mean_N.png",
            robust=True,
            annotate=True,
            fmt="{:.2f}",
        )

    if "geom_mean_H" in df.columns:
        plot_grid_heatmap(
            df,
            value_col="geom_mean_H",
            gammas=gammas,
            ws=ws,
            title="几何平均：geom_mean_H（burn-in 后）",
            out_path=out_dir / "geom_mean_H.png",
            robust=True,
            annotate=True,
            fmt="{:.2f}",
        )

    # Q4 常值阈值（R0）
    if {"R0_BL", "R0_BH"}.issubset(df.columns):
        for col in ["R0_BL", "R0_BH"]:
            vals = df[col].to_numpy(dtype=float)
            vmax = float(np.nanmax(vals)) if np.isfinite(vals).any() else 2.0
            vmax = max(vmax, 1.2)
            plot_grid_heatmap(
                df,
                value_col=col,
                gammas=gammas,
                ws=ws,
                title=f"{col}（>1 可入侵）",
                out_path=out_dir / f"{col}.png",
                vmin=0.0,
                vmax=vmax,
                cmap="coolwarm",
                center=1.0,
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[1.0],
            )

    # Q4 随机环境（lambda）
    if {"lambda_BL", "lambda_BH"}.issubset(df.columns):
        for col in ["lambda_BL", "lambda_BH"]:
            vals = df[col].to_numpy(dtype=float)
            vmin = float(np.nanmin(vals)) if np.isfinite(vals).any() else -1.0
            vmax = float(np.nanmax(vals)) if np.isfinite(vals).any() else 1.0

            if vmin >= 0.0:
                cmap = "viridis"
                center = None
            elif vmax <= 0.0:
                cmap = "viridis_r"
                center = None
            else:
                cmap = "coolwarm"
                center = 0.0

            plot_grid_heatmap(
                df,
                value_col=col,
                gammas=gammas,
                ws=ws,
                title=f"{col}（>0 可入侵）",
                out_path=out_dir / f"{col}.png",
                vmin=vmin,
                vmax=vmax,
                cmap=cmap,
                center=center,
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[0.0] if center == 0.0 else None,
            )

    # Q3：常值局部稳定（max_real）
    if {"max_real"}.issubset(df.columns):
        plot_grid_heatmap(
            df,
            value_col="max_real",
            gammas=gammas,
            ws=ws,
            title="局部稳定性：max_real（<0 稳定）",
            out_path=out_dir / "max_real.png",
            cmap="coolwarm",
            center=0.0,
            robust=True,
            annotate=True,
            fmt="{:.3f}",
            contour_levels=[0.0],
        )

    print(f"已重绘：{run_dir} -> {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description="把 outputs 里的 runs.csv 重绘成论文级图片。")
    ap.add_argument("--in-dir", required=True, help="run 目录或 outputs 根目录。")
    ap.add_argument("--out-subdir", default="figures_paper", help="每个 run 目录下的输出子目录名。")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    if not in_dir.exists():
        raise FileNotFoundError(str(in_dir))

    if (in_dir / "runs.csv").exists():
        render_one(in_dir, out_subdir=str(args.out_subdir))
        return

    # 批量扫描：递归找到所有包含 runs.csv 的目录（适配 outputs/temp/… 的目录结构）
    run_dirs = sorted({p.parent for p in in_dir.rglob("runs.csv")})
    for run_dir in run_dirs:
        render_one(run_dir, out_subdir=str(args.out_subdir))


if __name__ == "__main__":
    main()
