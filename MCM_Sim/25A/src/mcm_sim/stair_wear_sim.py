from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .io_utils import load_json
from .simulator import SimulationResult, simulate_wear_forward


def solve(data: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """楼梯踏步磨损正向仿真：人流/材料 -> 磨损热力图。

    你可以把它理解为“事件驱动的物理磨损累积”：
    - 每天有 N 次“脚步接触事件”（traffic model 生成）
    - 每次接触落点服从车道/方向偏好（contact center distribution）
    - 一次接触在足底范围内造成微小磨损（contact kernel + wear law）
    - 长期累计得到磨损形貌（wear depth heatmap）

    Args:
        data: 预留参数。未来可以传入真实客流时间序列/节假日表等；当前实现不使用。
        params: 参数字典。支持：
            - config_path: str | Path，JSON 配置文件路径
            - config: dict，直接传配置（优先级高于 config_path）
            - project_dir: str | Path，输出 runs/ 的根目录（默认：本文件所在的 src/）
            - run_name: str，可选，输出子目录名

    Returns:
        dict:
            - run_dir: str，输出目录
            - wear_depth_mm: np.ndarray，二维磨损深度（mm）
            - metrics: dict
            - metrics_over_time: list[dict]
    """

    if "config" in params:
        config = params["config"]
    else:
        config_path = Path(params.get("config_path", ""))
        if not config_path:
            raise ValueError("params must provide 'config' or 'config_path'.")
        config = load_json(config_path)

    project_dir = Path(params.get("project_dir", Path(__file__).resolve().parents[1]))
    run_name = params.get("run_name")

    result: SimulationResult = simulate_wear_forward(
        config=config,
        project_dir=project_dir,
        run_name=run_name,
    )

    return {
        "run_dir": str(result.run_dir),
        "wear_depth_mm": result.wear_depth_mm,
        "metrics": result.metrics,
        "metrics_over_time": result.metrics_over_time,
    }


if __name__ == "__main__":
    # Demo：直接运行本文件会读取默认配置并输出到 src/runs/ 下。
    this_dir = Path(__file__).resolve().parents[1]
    cfg_path = this_dir / "configs" / "stair_default.json"
    out = solve(
        data=None,
        params={
            "config_path": cfg_path,
            "project_dir": this_dir,
            "run_name": None,
        },
    )
    wear: np.ndarray = out["wear_depth_mm"]
    print("run_dir:", out["run_dir"])
    print("wear_depth_mm shape:", wear.shape)
    print("max wear (mm):", float(np.max(wear)))

