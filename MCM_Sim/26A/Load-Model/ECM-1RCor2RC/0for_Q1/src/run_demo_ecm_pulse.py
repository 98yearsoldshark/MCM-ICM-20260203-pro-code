#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1 演示入口：运行 ECM 1RC/2RC 脉冲响应 demo，并把图输出到本目录 outputs/。

说明：
- 本脚本本身不实现 ECM，只负责调用上级目录的 `demo/demo_ecm_pulse.py`；
- 这样做是为了把“Q1 论文会用到的 demo 入口”统一收口在 `0for_Q1/`。
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1 demo：ECM 1RC/2RC 脉冲响应（输出到 0for_Q1/outputs）")
    ap.add_argument("--show", action="store_true", help="弹窗显示（需要 GUI 环境）")
    ap.add_argument(
        "--out",
        default="",
        help="输出图片路径；留空则写到本目录 outputs/ecm_pulse_demo.png",
    )
    args = ap.parse_args()

    here = Path(__file__).resolve()
    q1_dir = here.parents[1]
    out = Path(args.out).expanduser().resolve() if str(args.out).strip() else (q1_dir / "outputs" / "ecm_pulse_demo.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    # q1_dir = .../ECM-1RCor2RC/0for_Q1，因此其 parent 才是 ECM-1RCor2RC 根目录
    demo_py = q1_dir.parents[0] / "demo" / "demo_ecm_pulse.py"
    if not demo_py.exists():
        raise FileNotFoundError(f"找不到 demo 脚本：{demo_py}")

    # 复用原 demo 的 CLI：--out / --show
    # demo 里用 `from ecm_core import ...`，因此需要把 demo 目录加到 sys.path
    sys.path.insert(0, str(demo_py.parent))
    sys.argv = [str(demo_py), "--out", str(out)] + (["--show"] if bool(args.show) else [])
    runpy.run_path(str(demo_py), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
