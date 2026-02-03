# -*- coding: utf-8 -*-
# 最小烟雾测试：快速验证仿真入口是否能跑通、输出文件是否齐全。
#
# 用法：
#   python MCM_Sim/24A/scripts/smoke_test.py
#
# 说明：
# - 该脚本会在 `MCM_Sim/24A/outputs/` 下写入少量测试输出（已在 .gitignore 中忽略）。
# - 目的不是验证科学结论，只是避免后续大规模扫描前“跑不起来/输出不齐”的低级问题。

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def main() -> None:
    this = Path(__file__).resolve()
    root = this.parents[1]  # MCM_Sim/24A
    runner = root / "run_sim.py"
    # 约定：中间产物统一写到 outputs/temp，避免污染主输出目录
    out_root = root / "outputs" / "temp"
    out_root.mkdir(parents=True, exist_ok=True)

    py = sys.executable

    # 1) bet-hedging（小规模）
    out_bh = out_root / "_smoke_bet_hedging"
    _run(
        [
            py,
            str(runner),
            "bet-hedging",
            "--out-dir",
            str(out_bh),
            "--years",
            "30",
            "--reps",
            "10",
            "--steps-per-year",
            "6",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
        ]
    )
    _assert_exists(out_bh / "runs.csv")
    _assert_exists(out_bh / "config.json")
    _assert_exists(out_bh / "env_sequences.npz")
    _assert_exists(out_bh / "figures" / "bet_hedging_triptych.png")

    # 2) seasonal（小规模）
    out_sea = out_root / "_smoke_seasonal"
    _run(
        [
            py,
            str(runner),
            "seasonal",
            "--out-dir",
            str(out_sea),
            "--years",
            "10",
            "--steps-per-year",
            "12",
            "--R0",
            "2.0",
            "--A",
            "0.4",
            "--T",
            "1.0",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
        ]
    )
    _assert_exists(out_sea / "runs.csv")
    _assert_exists(out_sea / "config.json")
    _assert_exists(out_sea / "figures" / "seasonal_trajectories.png")

    # 3) stability（小规模）
    out_stab = out_root / "_smoke_stability"
    _run(
        [
            py,
            str(runner),
            "stability",
            "--out-dir",
            str(out_stab),
            "--years",
            "60",
            "--steps-per-year",
            "6",
            "--R0",
            "2.0",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
        ]
    )
    _assert_exists(out_stab / "runs.csv")
    _assert_exists(out_stab / "config.json")
    _assert_exists(out_stab / "figures" / "max_real.png")

    # 2) Q4 常值阈值（小规模）
    out_q4c = out_root / "_smoke_q4_constant"
    _run(
        [
            py,
            str(runner),
            "q4-constant",
            "--out-dir",
            str(out_q4c),
            "--years",
            "60",
            "--steps-per-year",
            "6",
            "--R0",
            "2.0",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
        ]
    )
    _assert_exists(out_q4c / "runs.csv")
    _assert_exists(out_q4c / "config.json")

    # 4) Q4 随机入侵指数（小规模）
    out_q4m = out_root / "_smoke_q4_markov"
    _run(
        [
            py,
            str(runner),
            "q4-markov",
            "--out-dir",
            str(out_q4m),
            "--years",
            "40",
            "--reps",
            "10",
            "--steps-per-year",
            "6",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
            "--p",
            "0.5",
        ]
    )
    _assert_exists(out_q4m / "runs.csv")
    _assert_exists(out_q4m / "config.json")
    _assert_exists(out_q4m / "env_sequences.npz")

    # 5) triad-markov（小规模，Model-1）
    out_tri = out_root / "_smoke_triad_markov"
    _run(
        [
            py,
            str(runner),
            "triad-markov",
            "--out-dir",
            str(out_tri),
            "--model",
            "1",
            "--years",
            "20",
            "--reps",
            "6",
            "--steps-per-year",
            "6",
            "--gammas",
            "1,2",
            "--ws",
            "0,2",
            "--p",
            "0.5",
        ]
    )
    _assert_exists(out_tri / "runs.csv")
    _assert_exists(out_tri / "config.json")
    _assert_exists(out_tri / "env_sequences.npz")
    _assert_exists(out_tri / "figures" / "trajectories_triad.png")

    print("OK：所有 smoke tests 通过。")


if __name__ == "__main__":
    main()
