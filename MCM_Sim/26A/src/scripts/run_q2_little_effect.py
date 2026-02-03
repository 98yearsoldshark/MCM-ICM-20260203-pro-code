#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：输出 “surprisingly little” 的定量证据（按场景），并生成对应图表。

赛题 Requirements 2 明确要求：
- 哪些活动/条件导致续航最大幅度下降？
- 哪些因素对模型“surprisingly little”（几乎不改变）？

我们这里给出一个可复现、可调的“影响很小”判定口径：
  little_band_h = max(abs_thresh_h, rel_thresh_pct * TTE_baseline_h)
若某因素的 |ΔTTE| <= little_band_h，则判为 “surprisingly little”。

说明：
- ΔTTE 来自 `out_reports/q2/component_drivers_matrix.csv`（组件级反事实，按场景）。
- TTE_baseline_h 来自 `out_reports/q2/tte_summary.csv`（基线，soc0=1.0，variant='-'）。
- 该脚本只做汇总与作图，不重新跑仿真；若上游 CSV 不存在，请先运行 run_q2_report.py。

输出：
- out_reports/q2/little_effect/
  - little_effect_factors.csv
  - little_effect_summary_by_scenario.csv
- out_plots/q2/{paper|study}/little_effect/
  - 01_little_effect_rank.png
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

from mcm26a.analysis.q2_drivers import component_driver_specs
from mcm26a.scenarios import load_scenarios_json
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


def _scenario_title(raw: dict, sid: str) -> str:
    return str(raw.get("scenarios", {}).get(str(sid), {}).get("title_zh", sid))


def _little_band_h(*, baseline_tte_h: float, abs_thresh_h: float, rel_thresh_pct: float) -> float:
    base = float(baseline_tte_h)
    if not np.isfinite(base) or base <= 0:
        return float("nan")
    return float(max(float(abs_thresh_h), float(rel_thresh_pct) / 100.0 * base))


def _build_baseline_tte_map(tte_summary_rows: list[dict[str, str]], *, soc0: float) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in tte_summary_rows:
        if str(r.get("variant", "-")) != "-":
            continue
        if abs(_safe_float(r.get("soc0", float("nan"))) - float(soc0)) > 1e-9:
            continue
        sid = str(r.get("scenario_id", ""))
        m = _safe_float(r.get("mean_h", float("nan")))
        if sid and np.isfinite(m):
            out[sid] = float(m)
    return out


def _plot_component_little_effect(
    raw: dict,
    *,
    matrix_rows: list[dict[str, str]],
    baseline_tte_h: dict[str, float],
    abs_thresh_h: float,
    rel_thresh_pct: float,
    mode: PlotMode,
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    comps = component_driver_specs()
    sids = sorted({str(r.get("scenario_id", "")) for r in matrix_rows if str(r.get("scenario_id", ""))})

    # (sid, comp_id) -> mean_delta_h
    mat: dict[tuple[str, str], float] = {}
    for r in matrix_rows:
        sid = str(r.get("scenario_id", ""))
        cid = str(r.get("component_id", ""))
        mat[(sid, cid)] = _safe_float(r.get("mean_delta_h", float("nan")), 0.0)

    # 2x3 子图，最多展示 6 个场景（当前 v0 仅 5 个）
    n = len(sids)
    ncols = 3
    nrows = int(np.ceil(n / ncols)) if n > 0 else 1
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(13.8, 3.8 * nrows), squeeze=False)

    for idx, sid in enumerate(sids):
        ax = axes[idx // ncols][idx % ncols]
        base = float(baseline_tte_h.get(sid, float("nan")))
        band = _little_band_h(baseline_tte_h=base, abs_thresh_h=abs_thresh_h, rel_thresh_pct=rel_thresh_pct)

        vals = [float(mat.get((sid, cid), 0.0)) for cid, _ in comps]
        x = np.arange(len(vals))

        # 用颜色区分 “little” 与 “non-little”
        colors = []
        for v in vals:
            if np.isfinite(band) and abs(float(v)) <= float(band):
                colors.append("#BDBDBD")  # 灰：影响小
            else:
                colors.append("#4C78A8")  # 蓝：影响明显

        ax.bar(x, vals, color=colors, alpha=0.92)
        ax.set_xticks(x)
        ax.set_xticklabels([t for _, t in comps], rotation=20, ha="right")
        ax.set_ylabel("ΔTTE（小时）")
        ax.set_title(_scenario_title(raw, sid) + style.title_suffix)
        ax.axhline(0.0, color="#333333", lw=0.8, alpha=0.6)

        if np.isfinite(band):
            ax.axhline(+band, color="#999999", lw=1.0, linestyle="--", alpha=0.8)
            ax.text(
                0.02,
                0.92,
                f"little 带宽：±{band:.2f}h\n基线 TTE≈{base:.1f}h",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=9 if style.annotate else 8,
                color="#333333",
            )

        if style.annotate:
            for j, v in enumerate(vals):
                ax.text(j, float(v), f"{v:+.2f}", ha="center", va="bottom", fontsize=8, color="#111111")

    # 关掉多余子图
    for k in range(n, nrows * ncols):
        axes[k // ncols][k % ncols].axis("off")

    fig.suptitle(f"Q2：哪些因素影响很大/很小（surprisingly little）{style.title_suffix}", y=0.995, fontsize=13)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.95))
        fig.text(
            0.02,
            0.02,
            "判定口径：little_band_h = max(abs_thresh_h, rel_thresh_pct·TTE_baseline)。\n"
            f"当前默认：abs_thresh_h={abs_thresh_h:.2f}h，rel_thresh_pct={rel_thresh_pct:.1f}% 。\n"
            "灰色柱：|ΔTTE| 落在 little 带宽内（影响 surprisingly little）。蓝色柱：影响更显著。\n"
            "注意：这里的“去掉某组件功耗”是理想化反事实，用于归因/敏感性，不等价于真实手机一定可实现的策略。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.95))

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 surprisingly little：定量输出 + 图表")
    ap.add_argument("--reports-dir", default=str(SRC_DIR / "out_reports" / "q2"), help="Q2 报表目录（默认 out_reports/q2）")
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "little_effect"), help="输出报表目录")
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"), help="输出图像根目录（默认 out_plots/q2）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置（用于标题）")
    ap.add_argument("--soc0", type=float, default=1.0, help="用于取基线 TTE 的 soc0（默认 1.0）")
    ap.add_argument("--abs-thresh-h", type=float, default=0.25, help="little 绝对阈值（小时），默认 0.25h=15min")
    ap.add_argument("--rel-thresh-pct", type=float, default=2.0, help="little 相对阈值（%），默认 2%")
    ap.add_argument("--topk", type=int, default=3, help="每场景输出 topk 的大影响与小影响因子")
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    out_reports = Path(args.out_reports)
    out_reports.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)

    # 上游输入
    p_comp_matrix = reports_dir / "component_drivers_matrix.csv"
    p_tte_summary = reports_dir / "tte_summary.csv"
    if not p_comp_matrix.exists() or not p_tte_summary.exists():
        raise FileNotFoundError("缺少上游报表，请先运行 run_q2_report.py 生成 component_drivers_matrix.csv 与 tte_summary.csv")

    comp_matrix = _read_csv(p_comp_matrix)
    tte_summary = _read_csv(p_tte_summary)

    base_map = _build_baseline_tte_map(tte_summary, soc0=float(args.soc0))

    abs_th = float(args.abs_thresh_h)
    rel_th = float(args.rel_thresh_pct)

    # 1) 生成 factors 明细表（按场景×组件）
    factors: list[dict[str, object]] = []
    for r in comp_matrix:
        sid = str(r.get("scenario_id", ""))
        cid = str(r.get("component_id", ""))
        title = str(r.get("title_zh", cid))
        d = _safe_float(r.get("mean_delta_h", float("nan")), 0.0)
        n = int(float(r.get("n", "0") or 0))
        base = float(base_map.get(sid, float("nan")))
        band = _little_band_h(baseline_tte_h=base, abs_thresh_h=abs_th, rel_thresh_pct=rel_th)
        delta_pct = float("nan")
        if np.isfinite(base) and abs(base) > 1e-12:
            delta_pct = float(d / base * 100.0)
        factors.append(
            {
                "scenario_id": sid,
                "scenario_title_zh": _scenario_title(raw, sid),
                "factor_type": "component",
                "factor_id": cid,
                "title_zh": title,
                "mean_delta_h": float(d),
                "baseline_tte_h": float(base) if np.isfinite(base) else float("nan"),
                "delta_pct": float(delta_pct) if np.isfinite(delta_pct) else float("nan"),
                "little_band_h": float(band) if np.isfinite(band) else float("nan"),
                "is_little": bool(np.isfinite(band) and abs(float(d)) <= float(band)),
                "n": int(n),
            }
        )

    out_factors = out_reports / "little_effect_factors.csv"
    _write_csv(
        out_factors,
        factors,
        fieldnames=[
            "scenario_id",
            "scenario_title_zh",
            "factor_type",
            "factor_id",
            "title_zh",
            "mean_delta_h",
            "baseline_tte_h",
            "delta_pct",
            "little_band_h",
            "is_little",
            "n",
        ],
    )

    # 2) 每个场景输出 topk 的“大影响/小影响”
    summary_rows: list[dict[str, object]] = []
    by_sid: dict[str, list[dict[str, object]]] = {}
    for f in factors:
        by_sid.setdefault(str(f["scenario_id"]), []).append(f)

    for sid, xs in sorted(by_sid.items(), key=lambda x: x[0]):
        xs2 = list(xs)
        # 大影响：按 delta_h 降序
        big = sorted(xs2, key=lambda r: float(r.get("mean_delta_h", 0.0)), reverse=True)[: int(args.topk)]
        # surprisingly little：先筛 is_little=True，再按 |delta_h| 升序
        little = [r for r in xs2 if bool(r.get("is_little", False))]
        little = sorted(little, key=lambda r: abs(float(r.get("mean_delta_h", 0.0))))[: int(args.topk)]
        summary_rows.append(
            {
                "scenario_id": sid,
                "scenario_title_zh": _scenario_title(raw, sid),
                "top_big": "；".join([f"{r['title_zh']}({float(r['mean_delta_h']):+.2f}h)" for r in big]),
                "top_little": "；".join([f"{r['title_zh']}({float(r['mean_delta_h']):+.2f}h)" for r in little]) if little else "无",
                "abs_thresh_h": abs_th,
                "rel_thresh_pct": rel_th,
            }
        )

    out_summary = out_reports / "little_effect_summary_by_scenario.csv"
    _write_csv(out_summary, summary_rows, fieldnames=["scenario_id", "scenario_title_zh", "top_big", "top_little", "abs_thresh_h", "rel_thresh_pct"])

    # 3) 图像：paper/study 两套
    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_plots = ensure_dir(Path(args.out_plots) / str(m) / "little_effect")
        _plot_component_little_effect(
            raw,
            matrix_rows=comp_matrix,
            baseline_tte_h=base_map,
            abs_thresh_h=abs_th,
            rel_thresh_pct=rel_th,
            mode=m,  # type: ignore[arg-type]
            out_path=out_plots / "01_little_effect_rank.png",
        )

    print("已生成：")
    print(f"- {out_factors}")
    print(f"- {out_summary}")
    print(f"- {Path(args.out_plots) / 'paper' / 'little_effect' / '01_little_effect_rank.png'}")
    print(f"- {Path(args.out_plots) / 'study' / 'little_effect' / '01_little_effect_rank.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
