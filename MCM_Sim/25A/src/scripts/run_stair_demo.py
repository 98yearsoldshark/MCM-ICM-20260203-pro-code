from __future__ import annotations

from pathlib import Path

import numpy as np

# 允许直接运行脚本（不要求安装成包）
import sys

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm_sim.stair_wear_sim import solve  # noqa: E402


def main() -> None:
    cfg_path = SRC_DIR / "configs" / "stair_default.json"
    out = solve(
        data=None,
        params={
            "config_path": cfg_path,
            "project_dir": SRC_DIR,
            "run_name": f"stair_demo_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}",
        },
    )

    wear = out["wear_depth_mm"]
    metrics = out["metrics"]

    print("run_dir:", out["run_dir"])
    print("wear_depth_mm:", wear.shape, "max(mm)=", float(np.max(wear)))
    print("volume_loss(liters):", float(metrics["volume_loss"]["liters"]))


if __name__ == "__main__":
    main()

