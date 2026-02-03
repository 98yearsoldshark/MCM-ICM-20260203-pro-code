#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：输出“校准前/后”对核心结果的标准对比（避免像手调参数）。

说明：
- 只做对比汇总，不重新跑仿真（避免“大脚本”排查困难）。
- before/after 目录应为两次 run_q2_report.py 的输出目录（文件名保持一致）。

输出：
- out_reports/q2/calibration_effect/before_after_q2_core.csv
- out_plots/q2/{paper|study}/calibration_effect/01_tte_before_after.png
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

from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _safe_float(x: object, default: float = float("nan")) -> float:
    try:
        v = float(x)
    except Exception:
        return float(default)
    return float(v)


def _key(r: dict[str, str]) -> tuple[str, str, float]:
    return (str(r.get("scenario_id", "")), str(r.get("variant", "-")), _safe_float(r.get("soc0", float("nan"))))


def _join_by_key(before: list[dict[str, str]], after: list[dict[str, str]]) -> dict[tuple[str, str, float], tuple[dict[str, str], dict[str, str]]]:
    b = {_key(r): r for r in before}
    a = {_key(r): r for r in after}
    out: dict[tuple[str, str, float], tuple[dict[str, str], dict[str, str]]] = {}
    for k in sorted(set(b.keys()) & set(a.keys())):
        out[k] = (b[k], a[k])
    return out


def _plot_tte_before_after(points: list[dict[str, object]], *, mode: PlotMode, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    xs = np.array([float(p["before_mean_h"]) for p in points], dtype=float)
    ys = np.array([float(p["after_mean_h"]) for p in points], dtype=float)
    labs = [str(p["label"]) for p in points]

    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.scatter(xs, ys, s=38, alpha=0.85, color="#4C78A8", edgecolors="white", linewidths=0.6)

    lo = float(np.nanmin(np.concatenate([xs, ys]))) if xs.size and ys.size else 0.0
    hi = float(np.nanmax(np.concatenate([xs, ys]))) if xs.size and ys.size else 1.0
    lo = max(0.0, lo * 0.95)
    hi = hi * 1.05
    ax.plot([lo, hi], [lo, hi], color="#333333", lw=1.2, linestyle="--", alpha=0.75)

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("校准前：TTE 均值（小时）")
    ax.set_ylabel("校准后：TTE 均值（小时）")
    ax.set_title(f"Q2：校准前/后 TTE 对比（均值）{style.title_suffix}")

    if style.annotate:
        for x, y, lab in zip(xs.tolist(), ys.tolist(), labs):
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            ax.text(x, y, lab, fontsize=8, ha="left", va="bottom", alpha=0.9)

        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：每个点对应一个（场景 × 初始 SOC0）。\n"
            "落在虚线 y=x 上方表示“校准后预测的续航更长”，下方表示更短。\n"
            "该对比用于证明：功耗参数校准不仅改善短时功耗对照，也会改变 TTE/终止概率与 drivers 排名。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 校准前/后对比报表与图")
    ap.add_argument("--before", default=str(SRC_DIR / "out_reports" / "q2_compare" / "v2"), help="校准前 run_q2_report 输出目录")
    ap.add_argument("--after", default=str(SRC_DIR / "out_reports" / "q2_compare" / "awcal"), help="校准后 run_q2_report 输出目录")
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "calibration_effect"), help="输出报表目录")
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"), help="输出图像根目录（默认 out_plots/q2）")
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    before_dir = Path(args.before)
    after_dir = Path(args.after)
    out_reports = Path(args.out_reports)
    out_reports.mkdir(parents=True, exist_ok=True)

    # 1) TTE summary（核心）
    b_tte = _read_csv(before_dir / "tte_summary.csv")
    a_tte = _read_csv(after_dir / "tte_summary.csv")
    pairs_tte = _join_by_key(b_tte, a_tte)

    # 2) termination stats（终止概率）
    b_term = _read_csv(before_dir / "termination_stats.csv")
    a_term = _read_csv(after_dir / "termination_stats.csv")
    pairs_term = _join_by_key(b_term, a_term)

    # 3) drivers（动作/机制/组件）：按均值 ΔTTE 排名（整体）
    def _rank_map(rows: list[dict[str, str]], id_col: str, val_col: str) -> dict[str, int]:
        items = []
        for r in rows:
            fid = str(r.get(id_col, ""))
            v = _safe_float(r.get(val_col, float("nan")))
            if fid and np.isfinite(v):
                items.append((float(v), fid))
        items.sort(reverse=True)  # ΔTTE 越大越“重要”
        return {fid: i + 1 for i, (_v, fid) in enumerate(items)}

    b_drv = _read_csv(before_dir / "drivers_delta.csv")
    a_drv = _read_csv(after_dir / "drivers_delta.csv")
    rank_b_drv = _rank_map(b_drv, "action_id", "mean_delta_h")
    rank_a_drv = _rank_map(a_drv, "action_id", "mean_delta_h")

    b_comp = _read_csv(before_dir / "component_drivers_delta.csv")
    a_comp = _read_csv(after_dir / "component_drivers_delta.csv")
    rank_b_comp = _rank_map(b_comp, "component_id", "mean_delta_h")
    rank_a_comp = _rank_map(a_comp, "component_id", "mean_delta_h")

    b_mech = _read_csv(before_dir / "mechanism_drivers_delta.csv")
    a_mech = _read_csv(after_dir / "mechanism_drivers_delta.csv")
    rank_b_mech = _rank_map(b_mech, "mech_id", "mean_delta_h")
    rank_a_mech = _rank_map(a_mech, "mech_id", "mean_delta_h")

    # 4) 生成核心对比表：scenario × soc0（均值/区间 + 终止概率）
    out_rows: list[dict[str, object]] = []
    points: list[dict[str, object]] = []

    for (sid, vname, soc0), (rb, ra) in pairs_tte.items():
        if str(vname) != "-":
            continue
        tb = _safe_float(rb.get("mean_h", float("nan")))
        ta = _safe_float(ra.get("mean_h", float("nan")))
        p05b = _safe_float(rb.get("p05_h", float("nan")))
        p05a = _safe_float(ra.get("p05_h", float("nan")))
        p95b = _safe_float(rb.get("p95_h", float("nan")))
        p95a = _safe_float(ra.get("p95_h", float("nan")))

        term_b = pairs_term.get((sid, vname, soc0), (None, None))[0]  # type: ignore[index]
        term_a = pairs_term.get((sid, vname, soc0), (None, None))[1]  # type: ignore[index]

        def _term_val(rr: dict[str, str] | None, k: str) -> float:
            if rr is None:
                return float("nan")
            return _safe_float(rr.get(k, float("nan")))

        row = {
            "kind": "scenario",
            "scenario_id": str(sid),
            "soc0": float(soc0),
            "tte_mean_h_before": float(tb),
            "tte_mean_h_after": float(ta),
            "tte_mean_delta_h": float(ta - tb) if np.isfinite(tb) and np.isfinite(ta) else float("nan"),
            "tte_mean_delta_pct": float((ta - tb) / tb * 100.0) if np.isfinite(tb) and np.isfinite(ta) and abs(tb) > 1e-12 else float("nan"),
            "tte_p05_h_before": float(p05b),
            "tte_p05_h_after": float(p05a),
            "tte_p95_h_before": float(p95b),
            "tte_p95_h_after": float(p95a),
            "p_cutoff_before": _term_val(term_b, "p_cutoff"),
            "p_cutoff_after": _term_val(term_a, "p_cutoff"),
            "p_soc_min_before": _term_val(term_b, "p_soc_min"),
            "p_soc_min_after": _term_val(term_a, "p_soc_min"),
            "p_insufficient_power_before": _term_val(term_b, "p_insufficient_power"),
            "p_insufficient_power_after": _term_val(term_a, "p_insufficient_power"),
        }
        out_rows.append(row)

        if np.isfinite(tb) and np.isfinite(ta):
            points.append({"before_mean_h": tb, "after_mean_h": ta, "label": f"{sid}@{int(round(soc0*100))}%"})

    # 5) drivers 排名变化（补进同一张表，kind=drivers_*）
    def _append_drivers(kind: str, before_rows: list[dict[str, str]], after_rows: list[dict[str, str]], id_col: str, rank_b: dict[str, int], rank_a: dict[str, int]) -> None:
        b_map = {str(r.get(id_col, "")): r for r in before_rows}
        a_map = {str(r.get(id_col, "")): r for r in after_rows}
        for fid in sorted(set(b_map.keys()) & set(a_map.keys())):
            if not fid:
                continue
            rb = b_map[fid]
            ra = a_map[fid]
            out_rows.append(
                {
                    "kind": kind,
                    "factor_id": fid,
                    "title_zh": str(rb.get("title_zh", ra.get("title_zh", fid))),
                    "mean_delta_h_before": _safe_float(rb.get("mean_delta_h", float("nan"))),
                    "mean_delta_h_after": _safe_float(ra.get("mean_delta_h", float("nan"))),
                    "rank_before": int(rank_b.get(fid, 9999)),
                    "rank_after": int(rank_a.get(fid, 9999)),
                    "rank_shift": int(rank_b.get(fid, 9999)) - int(rank_a.get(fid, 9999)),
                }
            )

    _append_drivers("drivers_action", b_drv, a_drv, "action_id", rank_b_drv, rank_a_drv)
    _append_drivers("drivers_component", b_comp, a_comp, "component_id", rank_b_comp, rank_a_comp)
    _append_drivers("drivers_mechanism", b_mech, a_mech, "mech_id", rank_b_mech, rank_a_mech)

    out_csv = out_reports / "before_after_q2_core.csv"
    # 固定列集合（不强制每行都有所有列）
    fieldnames = sorted({k for r in out_rows for k in r.keys()})
    _write_csv(out_csv, out_rows, fieldnames=fieldnames)

    # 6) 图：TTE before/after
    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_plot_dir = ensure_dir(Path(args.out_plots) / str(m) / "calibration_effect")
        _plot_tte_before_after(points, mode=m, out_path=out_plot_dir / "01_tte_before_after.png")  # type: ignore[arg-type]

    print("已生成：")
    print(f"- {out_csv}")
    print(f"- {Path(args.out_plots) / 'paper' / 'calibration_effect' / '01_tte_before_after.png'}")
    print(f"- {Path(args.out_plots) / 'study' / 'calibration_effect' / '01_tte_before_after.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
