from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RectGrid:
    """矩形参数面网格（用于踏步/扶手展开面等）。

    坐标约定：
    - x: [0, width) 方向（例如楼梯宽度方向）
    - y: [0, depth) 方向（例如踏步深度：y=0 靠近立板，y=depth 靠近踏面前沿/踏鼻）
    - 数组 shape 为 (ny, nx)，对应 (y, x)
    """

    width_m: float
    depth_m: float
    cell_m: float
    nx: int
    ny: int
    x: np.ndarray  # (nx,)
    y: np.ndarray  # (ny,)
    X: np.ndarray  # (ny, nx)
    Y: np.ndarray  # (ny, nx)
    cell_area_m2: float

    @property
    def extent(self) -> list[float]:
        """matplotlib imshow extent: [xmin, xmax, ymin, ymax]."""
        return [0.0, self.nx * self.cell_m, 0.0, self.ny * self.cell_m]


def make_rect_grid(width_m: float, depth_m: float, cell_m: float) -> RectGrid:
    if width_m <= 0 or depth_m <= 0 or cell_m <= 0:
        raise ValueError("width_m/depth_m/cell_m must be positive.")

    # 使用 floor，避免网格超过给定几何边界（剩余不足一个 cell 的边缘被忽略）。
    nx = max(1, int(np.floor(width_m / cell_m)))
    ny = max(1, int(np.floor(depth_m / cell_m)))

    x = (np.arange(nx) + 0.5) * cell_m
    y = (np.arange(ny) + 0.5) * cell_m
    X, Y = np.meshgrid(x, y)  # (ny, nx)

    return RectGrid(
        width_m=width_m,
        depth_m=depth_m,
        cell_m=cell_m,
        nx=nx,
        ny=ny,
        x=x,
        y=y,
        X=X,
        Y=Y,
        cell_area_m2=cell_m * cell_m,
    )

