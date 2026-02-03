from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from PIL import Image


def wear_to_height_field(
    wear_depth_mm: np.ndarray,
    *,
    z_max: float = 0.98,
    z_min: float = 0.78,
    robust_percentile: float = 99.5,
) -> np.ndarray:
    """将“磨损深度(mm)”映射为“高度场(z)”以匹配论文热力图配色直觉。

    论文热力图通常是“高度/相对高度”：
    - 未磨损区域更高（偏黄）
    - 磨损凹陷更低（偏蓝）

    这里做一个稳健归一：用高分位作为 max，避免少数极端值把整体压扁。
    """

    w = np.asarray(wear_depth_mm, dtype=float)
    if not np.any(np.isfinite(w)):
        return np.full_like(w, fill_value=z_max, dtype=float)

    w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
    w_ref = float(np.percentile(w, robust_percentile))
    if w_ref <= 0:
        return np.full_like(w, fill_value=z_max, dtype=float)

    w_norm = np.clip(w / w_ref, 0.0, 1.0)
    z = z_max - w_norm * (z_max - z_min)
    return z


def render_field_to_pil(
    field: np.ndarray,
    *,
    cmap_name: str = "viridis",
    flip_x: bool = True,
    flip_y: bool = True,
    out_size: Optional[Tuple[int, int]] = None,
) -> Image.Image:
    """将 2D 标量场渲染成彩色图片（不含坐标轴），便于与论文截图做对比。"""

    a = np.asarray(field, dtype=float)

    if flip_y:
        a = np.flipud(a)
    if flip_x:
        a = np.fliplr(a)

    # 归一到 [0,1]
    mn = float(np.min(a))
    mx = float(np.max(a))
    if mx > mn:
        n = (a - mn) / (mx - mn)
    else:
        n = np.zeros_like(a)

    import matplotlib.cm as cm

    cmap = cm.get_cmap(cmap_name)
    rgba = cmap(n)  # (ny,nx,4) float in [0,1]
    rgb = (rgba[:, :, :3] * 255.0).astype(np.uint8)
    img = Image.fromarray(rgb, mode="RGB")

    if out_size is not None:
        img = img.resize(out_size, Image.BILINEAR)
    return img

