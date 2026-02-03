#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：批量生成 Model-0 可视化图（paper/study 两套）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.viz import make_model0_plot_batch
from mcm26a.viz.model0_plots import PlotBatchConfig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - 生成 Model-0 图像（paper/study）")
    ap.add_argument(
        "--out-dir",
        default=str(SRC_DIR / "out_plots"),
        help="输出目录（会自动创建 paper/ 与 study/ 子目录）",
    )
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON 路径",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数 JSON 路径",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v0.json"),
        help="电池参数 JSON 路径（Model-0）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--uq-samples", type=int, default=800, help="UQ 采样次数（建议 200~5000）")
    ap.add_argument("--uq-seed", type=int, default=1, help="UQ 随机种子（可复现）")
    ap.add_argument(
        "--mode",
        default="",
        help="只生成指定模式：paper 或 study；留空则两种模式都生成",
    )
    args = ap.parse_args()

    cfg = PlotBatchConfig(
        scenarios_path=Path(args.scenarios),
        power_params_path=Path(args.power),
        phone_params_path=Path(args.phone),
        out_dir=Path(args.out_dir),
        soc0=float(args.soc0),
        uq_samples=int(args.uq_samples),
        uq_seed=int(args.uq_seed),
    )

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        paths = make_model0_plot_batch(cfg, mode=m)  # type: ignore[arg-type]
        print(f"[{m}] generated {len(paths)} figures -> {Path(args.out_dir) / 'model0' / m}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
