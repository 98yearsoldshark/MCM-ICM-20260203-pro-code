"""
一键运行本目录下所有 demo。

用法：
  python demos/run_all.py

注意：
- 该脚本用 subprocess 逐个运行，确保每个 demo 像“独立脚本”一样工作。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    demos = [
        "demo_00_env_check.py",
        "demo_01_spm_basic.py",
        "demo_02_cccv_cycle.py",
        "demo_03_phone_like_power_profile.py",
        "demo_04_tte_vs_power.py",
    ]

    here = Path(__file__).resolve().parent
    for name in demos:
        path = here / name
        print(f"[run_all] running {name} ...", flush=True)
        subprocess.run([sys.executable, str(path)], check=True)

    print("[run_all] all demos finished. outputs -> ../outputs/", flush=True)


if __name__ == "__main__":
    main()
