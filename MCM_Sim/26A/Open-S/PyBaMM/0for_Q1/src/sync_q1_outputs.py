#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1 辅助脚本：把 PyBaMM 的关键 demo 输出复制到 `0for_Q1/outputs/`。

为什么要复制？
- `outputs/` 里会有很多 demo 产物；Q1 写作时我们只需要少量“核心对照图”。
- `0for_Q1/outputs/` 作为“论文 Q1 需要的精选材料”收口目录，避免后期找图困难。
"""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve()
    q1_dir = here.parents[1]
    project_root = q1_dir.parents[0]  # .../Open-S/PyBaMM

    src_out = project_root / "outputs"
    dst_out = q1_dir / "outputs"
    dst_out.mkdir(parents=True, exist_ok=True)

    keep = [
        "demo_03_phone_like_power_profile.png",
        "demo_03_phone_like_power_profile.csv",
        "demo_04_tte_vs_power.png",
        "demo_04_tte_vs_power.csv",
        # 可选：环境自检（方便交接时确认可复现）
        "demo_00_env_check.txt",
    ]

    missing = []
    copied = []
    for name in keep:
        src = src_out / name
        if not src.exists():
            missing.append(name)
            continue
        dst = dst_out / name
        shutil.copy2(src, dst)
        copied.append(name)

    print("[PyBaMM Q1] copied:", len(copied))
    for n in copied:
        print(" -", n)
    if missing:
        print("[PyBaMM Q1] missing:", len(missing))
        for n in missing:
            print(" -", n)
        print("提示：先运行 demos/run_all.py 或指定 demo，再执行本脚本。")
    print("[PyBaMM Q1] out_dir:", dst_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
