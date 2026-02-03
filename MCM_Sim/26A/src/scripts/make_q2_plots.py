#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：批量生成 Q2 图像（TTE 矩阵 / 不确定性分布 / drivers，paper/study 两套）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.viz import make_q2_plot_batch
from mcm26a.viz.q2_plots import PlotBatchConfigQ2


def _parse_soc_list(s: str) -> tuple[float, ...]:
    xs = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    if not xs:
        raise ValueError("soc0-list 不能为空")
    return tuple(xs)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - 生成 Q2 图像（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q2/paper 与 q2/study）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON 路径（no7 升级 + AndroWatts 多目标校准版：更贴近公开测量的总功耗量级，且兼顾主要组件分解）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（Model-3：热-电-老化）",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="积分步长（秒），建议 1~10")
    ap.add_argument("--soc0-list", default="1.0,0.75,0.5,0.25", help="初始 SOC 列表，用逗号分隔")
    ap.add_argument("--uq-samples", type=int, default=40, help="UQ 采样次数（建议 40~2000；出图可先用 40）")
    ap.add_argument("--uq-seed", type=int, default=1, help="UQ 随机种子（可复现）")
    ap.add_argument("--driver-seeds", type=int, default=25, help="drivers 估计使用的随机种子数量（越大越稳）")
    ap.add_argument("--driver-soc0", type=float, default=1.0, help="drivers 图使用的 SOC0（默认 1.0）")
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    cfg = PlotBatchConfigQ2(
        scenarios_path=Path(args.scenarios),
        power_params_stateful_path=Path(args.power),
        phone_aging_path=Path(args.phone),
        out_dir=Path(args.out_dir),
        reports_dir=SRC_DIR / "out_reports" / "q2",
        dt_s=float(args.dt),
        soc0_list=_parse_soc_list(str(args.soc0_list)),
        uq_samples=int(args.uq_samples),
        uq_seed=int(args.uq_seed),
        driver_seeds=int(args.driver_seeds),
        driver_soc0=float(args.driver_soc0),
    )

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        paths = make_q2_plot_batch(cfg, mode=m)  # type: ignore[arg-type]
        print(f"[{m}] generated {len(paths)} figures -> {Path(args.out_dir) / 'q2' / m}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
