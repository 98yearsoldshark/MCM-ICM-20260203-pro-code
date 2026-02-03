from __future__ import annotations

from typing import Any, Dict

import numpy as np

from .grid import RectGrid


def compute_metrics(wear_depth_mm: np.ndarray, grid: RectGrid) -> Dict[str, Any]:
    wear_depth_mm = np.asarray(wear_depth_mm, dtype=float)

    max_depth = float(np.max(wear_depth_mm))
    mean_depth = float(np.mean(wear_depth_mm))

    # 体积损失：sum(depth * area)
    volume_loss_m3 = float(np.sum(wear_depth_mm) * 1e-3 * grid.cell_area_m2)
    volume_loss_liters = volume_loss_m3 * 1000.0

    # 一个便于解释的“明显磨损面积”指标：超过 max 的 20% 的区域面积占比
    thr = 0.2 * max_depth if max_depth > 0 else 0.0
    area_frac = float(np.mean(wear_depth_mm >= thr)) if thr > 0 else 0.0

    return {
        "grid": {
            "width_m": grid.width_m,
            "depth_m": grid.depth_m,
            "cell_m": grid.cell_m,
            "nx": grid.nx,
            "ny": grid.ny,
        },
        "wear_depth_mm": {
            "max": max_depth,
            "mean": mean_depth,
        },
        "volume_loss": {
            "m3": volume_loss_m3,
            "liters": volume_loss_liters,
        },
        "area_fraction_ge_0p2_max": area_frac,
    }

