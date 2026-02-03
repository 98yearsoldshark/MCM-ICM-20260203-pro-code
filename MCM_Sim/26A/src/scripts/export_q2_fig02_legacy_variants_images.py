#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出“图 02 的旧版（场景自带 variants 拼盘）”图片到论文材料目录 other/。

用途：
- 之前我们把图 02 升级为 no12 口径的“统一 OAT 条件开关”（x 轴更干净、可解释）。
- 但用户希望把旧版图也留存下来（用于对照/复盘），并强调保留“当时的配色”。

本脚本会：
1) 读取 out_reports/q2/variants_stats.csv（场景自带 variants 的统计；旧版图的数据口径）
2) 生成一张 legacy paper 图 + 一张 legacy study 图（不覆盖现有 figure.png/figure_study.png）
3) 输出到：
   MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/02-Q2-变体对比_条件变化对TTE影响/other/

注意：
- 旧版图的特点就是“列很多、很多场景 N/A”，这里刻意保留这种风格；
  同时保持与旧版一致的色标范围（vmin=-80%, vmax=20%, vcenter=0%）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
REPO_DIR = SRC_DIR.parent.parent  # .../MCM_Sim

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.scenarios import load_scenarios_json
from mcm26a.viz.style import apply_style, savefig
from mcm26a.viz.q2_plots import _scenario_ids, _scenario_title, _variant_label_zh, _glossary_text


def _load_variants_stats_csv(path: Path, *, soc0: float) -> tuple[pd.DataFrame, dict[str, dict[str, dict[str, float]]]]:
    df = pd.read_csv(path)
    df = df[df["soc0"].astype(float) == float(soc0)].copy()
    if df.empty:
        raise RuntimeError(f"{path} 中找不到 soc0={soc0} 的行")

    stats: dict[str, dict[str, dict[str, float]]] = {}
    for row in df.to_dict(orient="records"):
        sid = str(row.get("scenario_id", ""))
        v = str(row.get("variant", "-"))
        stats.setdefault(sid, {})[v] = {
            "mean_h": float(row.get("mean_h", float("nan"))),
        }
    return df, stats


def _plot_legacy_variant_matrix(
    raw: dict,
    *,
    stats: dict[str, dict[str, dict[str, float]]],
    soc0: float,
    mode: str,
    out_path: Path,
) -> None:
    style = apply_style(mode)  # paper/study

    sids = _scenario_ids(raw)
    ylabels = [_scenario_title(raw, sid) for sid in sids]

    # 旧版：用“场景自带 variants 拼盘”，因此列会很多且大量 N/A（灰色空格）。
    all_variants: set[str] = set()
    for sid in sids:
        for v in stats.get(sid, {}).keys():
            if v != "-":
                all_variants.add(str(v))

    # 旧版列顺序：按照旧 variants 的常见顺序，未知的放最后（字典序）
    preferred = [
        "high_brightness",
        "wifi_poor_signal",
        "cellular_good_signal",
        "cellular_poor_signal",
        "cellular_stream",
        "cellular_browse",
        "wifi_navigation",
        "online_game",
        "rural_poor_signal",
        "poor_signal_standby",
        "poor_signal_rest",
        "local_play",
        "cold_outdoor",
        "hot_summer",
    ]
    preferred_idx = {k: i for i, k in enumerate(preferred)}

    def _vkey(v: str) -> tuple[int, str]:
        return (preferred_idx.get(v, 10_000), v)

    vlist = sorted(list(all_variants), key=_vkey)

    mat = np.full((len(sids), len(vlist)), np.nan, dtype=float)
    ann = [["" for _ in vlist] for _ in sids]

    for i, sid in enumerate(sids):
        base = float(stats.get(sid, {}).get("-", {}).get("mean_h", float("nan")))
        for j, v in enumerate(vlist):
            if v not in (stats.get(sid, {}) or {}):
                continue
            m = float(stats[sid][v].get("mean_h", float("nan")))
            if not (np.isfinite(base) and base > 1e-9 and np.isfinite(m)):
                continue
            dpct = (m - base) / base * 100.0
            mat[i, j] = float(dpct)
            if style.annotate:
                ann[i][j] = f"{dpct:+.0f}%\n({m-base:+.1f}h)"
            else:
                ann[i][j] = f"{dpct:+.0f}%"

    # 旧版配色（保持当时口径）：负值红、正值绿；固定范围便于跨图比较
    vmin, vmax = -80.0, 20.0
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
    cmap = plt.cm.get_cmap("RdYlGn").copy()
    cmap.set_bad("#F0F0F0")

    # 列很多：宽度固定为旧版风格（避免“修复后又不像旧图”）
    fig, ax = plt.subplots(figsize=(11.6, 4.6))
    im = ax.imshow(np.ma.masked_invalid(mat), cmap=cmap, norm=norm, aspect="auto")

    ax.set_yticks(np.arange(len(sids)))
    ax.set_yticklabels(ylabels)
    ax.set_xticks(np.arange(len(vlist)))
    ax.set_xticklabels([_variant_label_zh(v) for v in vlist], rotation=15, ha="right")
    ax.set_title(f"Q2：条件变体对续航的相对影响（SOC0={int(round(100*soc0))}%）{style.title_suffix}")

    ax.set_xticks(np.arange(-0.5, len(vlist), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sids), 1), minor=True)
    ax.grid(which="minor", color="#000000", alpha=0.08, linestyle="-", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(len(sids)):
        for j in range(len(vlist)):
            if not ann[i][j]:
                continue
            val = mat[i, j]
            color = "white" if np.isfinite(val) and abs(float(val)) > 35 else "#111111"
            ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=8, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.92)
    cbar.set_label("相对变化：ΔTTE / TTE_baseline（%）")

    if style.annotate:
        # 旧版学习图：保留“长说明”（会更挤，但这正是旧版特征）
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：每个格子表示“在同一场景下，仅改变某个条件（variant）”时，TTE 相对 baseline 的变化百分比。\n"
            "灰色空格表示该场景未定义该变体（不适用）。\n"
            "红色越深表示续航缩短越严重；绿色表示续航反而变长。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="导出 Q2 图 02 旧版（场景自带 variants 拼盘）图片")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0（默认 1.0）")
    ap.add_argument(
        "--variants-stats",
        default=str(SRC_DIR / "out_reports" / "q2" / "variants_stats.csv"),
        help="旧版 variants 统计表（默认 out_reports/q2/variants_stats.csv）",
    )
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON（默认 configs/scenarios_v0.json）",
    )
    ap.add_argument(
        "--out-dir",
        default=str(
            REPO_DIR
            / "26A"
            / "论文"
            / "理论模型"
            / "论文阶段"
            / "Q2材料"
            / "02-Q2-变体对比_条件变化对TTE影响"
            / "other"
        ),
        help="输出目录（默认写入论文材料 02/.../other）",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(Path(args.scenarios))
    _df, stats = _load_variants_stats_csv(Path(args.variants_stats), soc0=float(args.soc0))

    # 不覆盖现有 figure.png/figure_study.png：用 legacy 前缀保存
    out_paper = out_dir / "legacy_05_variants_compare_paper.png"
    out_study = out_dir / "legacy_05_variants_compare_study.png"

    _plot_legacy_variant_matrix(raw, stats=stats, soc0=float(args.soc0), mode="paper", out_path=out_paper)
    _plot_legacy_variant_matrix(raw, stats=stats, soc0=float(args.soc0), mode="study", out_path=out_study)

    print(f"已输出旧版图（paper）：{out_paper}")
    print(f"已输出旧版图（study）：{out_study}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
