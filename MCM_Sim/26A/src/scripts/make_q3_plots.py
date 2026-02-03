#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：批量生成 Q3 图像（敏感性/消融/老化/波动），paper/study 两套。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.viz import make_q3_plot_batch
from mcm26a.viz.q3_plots import PlotBatchConfigQ3


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - 生成 Q3 图像（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q3/paper 与 q3/study）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--reports-dir",
        default=str(SRC_DIR / "out_reports" / "q3"),
        help="Q3 报表目录（默认 out_reports/q3；需先运行 scripts/run_q3_report.py）",
    )
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    cfg = PlotBatchConfigQ3(
        scenarios_path=Path(args.scenarios),
        reports_dir=Path(args.reports_dir),
        out_dir=Path(args.out_dir),
    )

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        paths = make_q3_plot_batch(cfg, mode=m)  # type: ignore[arg-type]
        print(f"[{m}] generated {len(paths)} figures -> {Path(args.out_dir) / 'q3' / m}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

