#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：端到端复现套件（一键生成“满分口径”核心证据）。

目标（对齐赛题 Q2 的硬性评分点）：
- 给出连续时间机理模型下的 TTE 预测（多场景×多 SOC0）；
- 量化不确定性（UQ）并输出 drivers / “surprisingly little” 的证据；
- 与公开观测或可验证的代理行为做对照（功耗量级、网络 J/MB、长时间范围等）；
- 给出数值稳定性（dt sweep）与关键不变量/终止机制统计。

本脚本做什么：
- 串行调用多个 scripts/*，把“跑一次就全出齐”固化成可复现实验口径。

注意：
- 该套件只会新增 out_reports/out_plots 下的产物，不会改动核心模型结构；
- 运行时间取决于 UQ 样本数（默认使用中等设置，便于日常迭代；冲刺论文可把 UQ 调大）。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent


def _run(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q2：端到端复现套件（生成报表+图像+对照验证）")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="Q2 功耗参数 JSON（建议使用已校准版本）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="Model-3 电池参数 JSON",
    )
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="主线仿真步长（秒）")
    ap.add_argument("--uq-samples", type=int, default=120, help="UQ 样本数（冲刺论文可提高到 300~500）")
    ap.add_argument("--uq-seed", type=int, default=1, help="UQ 随机种子")
    ap.add_argument("--driver-seeds", type=int, default=40, help="drivers 估计的随机种子数")
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    py = sys.executable

    # 1) 公开数据对照（功耗量级/组件分解）
    _run(
        [
            py,
            str(SRC_DIR / "scripts" / "validate_q2_open_data.py"),
            "--power",
            str(args.power),
            "--max-n",
            "250",
            "--seeds-per-case",
            "20",
            "--dt",
            "1.0",
        ]
    )

    # 2) 通信对照（Monsoon+iPerf：ΔP vs throughput, J/MB）
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_smartphone_measurements.py"), "--mode", "paper"])
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_smartphone_measurements.py"), "--mode", "study"])

    # 3) 长时间范围对照（user_behavior：日耗电→等效 TTE）
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_user_behavior.py"), "--power", str(args.power), "--mode", "paper"])
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_user_behavior.py"), "--power", str(args.power), "--mode", "study"])

    # 4) 老化敏感性（AndroWatts×电池状态表：TTE vs SOH）
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_master_table.py"), "--mode", "paper"])
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_master_table.py"), "--mode", "study"])

    # 5) 代理 TTE（恒流 I_obs）：更接近“真值/上界”的对照链条
    _run([py, str(SRC_DIR / "scripts" / "validate_q2_tte_proxy_current.py")])

    # 6) 数值稳定性（dt sweep）
    _run(
        [
            py,
            str(SRC_DIR / "scripts" / "run_q2_numerical_stability.py"),
            "--power",
            str(args.power),
            "--phone",
            str(args.phone),
            "--scenarios",
            str(args.scenarios),
            "--dt-list",
            "10,5,2,1",
        ]
    )

    # 7) Q2 主线报表（UQ + PRCC/Spearman + drivers）
    _run(
        [
            py,
            str(SRC_DIR / "scripts" / "run_q2_report.py"),
            "--scenarios",
            str(args.scenarios),
            "--power",
            str(args.power),
            "--phone",
            str(args.phone),
            "--dt",
            str(float(args.dt)),
            "--uq-samples",
            str(int(args.uq_samples)),
            "--uq-seed",
            str(int(args.uq_seed)),
            "--driver-seeds",
            str(int(args.driver_seeds)),
        ]
    )

    # 8) Q2 图像（TTE 矩阵、UQ、drivers 等）
    _run(
        [
            py,
            str(SRC_DIR / "scripts" / "make_q2_plots.py"),
            "--scenarios",
            str(args.scenarios),
            "--power",
            str(args.power),
            "--phone",
            str(args.phone),
            "--dt",
            str(float(args.dt)),
            "--uq-samples",
            "60",
            "--uq-seed",
            str(int(args.uq_seed)),
            "--driver-seeds",
            str(int(max(25, int(args.driver_seeds) // 2))),
        ]
        + ([] if not str(args.mode).strip() else ["--mode", str(args.mode)])
    )

    # 9) Recommendations 自动汇总（把 drivers 翻译成“可执行建议”表格+草稿）
    _run([py, str(SRC_DIR / "scripts" / "run_q2_recommendations.py")])

    print("Q2 full suite 完成：")
    print("- 报表：MCM_Sim/26A/src/out_reports/q2/")
    print("- 图像：MCM_Sim/26A/src/out_plots/q2/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

