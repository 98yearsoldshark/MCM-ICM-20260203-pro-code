"""
Demo 00：环境自检（版本/依赖/基本 import）。

产物：
- outputs/demo_00_env_check.txt
"""

from __future__ import annotations

from _demo_utils import disable_pybamm_telemetry, outputs_dir


def main() -> None:
    disable_pybamm_telemetry()

    import sys

    import casadi
    import matplotlib
    import numpy as np
    import pybamm

    lines = [
        f"python: {sys.version.replace(chr(10), ' ')}",
        f"pybamm: {pybamm.__version__}",
        f"casadi: {casadi.__version__}",
        f"numpy: {np.__version__}",
        f"matplotlib: {matplotlib.__version__}",
    ]
    text = "\n".join(lines) + "\n"
    print(text, end="")

    out = outputs_dir()
    (out / "demo_00_env_check.txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
