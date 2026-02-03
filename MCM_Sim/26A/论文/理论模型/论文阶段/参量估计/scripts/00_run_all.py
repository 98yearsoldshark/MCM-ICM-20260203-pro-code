#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键生成参量估计全部产物（推荐入口）。

从仓库根目录运行：
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/00_run_all.py"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(script: Path) -> None:
    print(f"[run] {script.name}")
    subprocess.run([sys.executable, str(script)], check=True)


def main() -> None:
    this_dir = Path(__file__).resolve().parent
    _run(this_dir / "01_fit_brightness_screen.py")
    _run(this_dir / "02_fit_load_cpu_gpu.py")
    _run(this_dir / "03_fit_network_tail.py")
    _run(this_dir / "04_fit_throughput_power.py")
    _run(this_dir / "05_fit_temperature_time_curve.py")
    _run(this_dir / "99_build_param_summary.py")
    _run(this_dir / "10_generate_suggested_configs.py")
    print("[ok] 参量估计产物已生成。")


if __name__ == "__main__":
    main()
