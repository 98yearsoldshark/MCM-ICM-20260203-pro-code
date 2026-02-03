from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .grid import RectGrid
from .io_utils import ensure_dir


def plot_heatmap(
    wear_depth_mm: np.ndarray,
    grid: RectGrid,
    out_path: Path,
    *,
    title: Optional[str] = None,
    cmap: str = "inferno",
) -> None:
    """绘制磨损热力图（单位：mm）。"""

    import matplotlib.pyplot as plt

    ensure_dir(out_path.parent)

    fig, ax = plt.subplots(figsize=(7, 3.0), dpi=160)
    im = ax.imshow(
        wear_depth_mm,
        origin="lower",
        extent=grid.extent,
        cmap=cmap,
        aspect="auto",
    )
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    if title:
        ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("wear depth (mm)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_cross_section_y_mean(
    wear_depth_mm: np.ndarray,
    grid: RectGrid,
    out_path: Path,
    *,
    title: Optional[str] = None,
) -> None:
    """沿 x 求平均，得到 y 方向截面，用于观察“踏鼻边缘带”是否形成明显磨损峰。"""

    import matplotlib.pyplot as plt

    ensure_dir(out_path.parent)

    y = grid.y
    profile = np.mean(wear_depth_mm, axis=1)  # (ny,)

    fig, ax = plt.subplots(figsize=(6.0, 3.0), dpi=160)
    ax.plot(y, profile, lw=2)
    ax.set_xlabel("y (m)")
    ax.set_ylabel("mean wear depth (mm)")
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

