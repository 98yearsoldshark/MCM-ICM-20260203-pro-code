from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

import numpy as np

from .grid import RectGrid


def _normal_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    sigma = max(float(sigma), 1e-12)
    z = (x - mu) / sigma
    return (1.0 / (sigma * np.sqrt(2.0 * np.pi))) * np.exp(-0.5 * z * z)


def make_elliptical_gaussian_kernel(
    *,
    cell_m: float,
    sigma_x_m: float,
    sigma_y_m: float,
    size_m: float,
) -> np.ndarray:
    """生成椭圆高斯接触核（max=1），用于表示一次接触对周围网格的影响权重。"""

    if cell_m <= 0:
        raise ValueError("cell_m must be positive.")
    if sigma_x_m <= 0 or sigma_y_m <= 0:
        raise ValueError("sigma_x_m/sigma_y_m must be positive.")
    if size_m <= 0:
        raise ValueError("size_m must be positive.")

    half = 0.5 * size_m
    hx = int(np.ceil(half / cell_m))
    hy = int(np.ceil(half / cell_m))

    dx = np.arange(-hx, hx + 1) * cell_m
    dy = np.arange(-hy, hy + 1) * cell_m
    DX, DY = np.meshgrid(dx, dy)  # (ky, kx)

    k = np.exp(-0.5 * ((DX / sigma_x_m) ** 2 + (DY / sigma_y_m) ** 2))
    # 中心为 1（已经满足），这里显式做一次归一，避免数值误差。
    k /= float(np.max(k))
    return k.astype(float)


@dataclass(frozen=True)
class LaneComponent:
    mu_x_frac: float
    sigma_x_m: float
    weight: float


def _parse_lanes(lanes: List[Dict]) -> List[LaneComponent]:
    comps: List[LaneComponent] = []
    for lane in lanes:
        comps.append(
            LaneComponent(
                mu_x_frac=float(lane["mu_x_frac"]),
                sigma_x_m=float(lane["sigma_x_m"]),
                weight=float(lane["weight"]),
            )
        )
    if not comps:
        raise ValueError("lanes must be non-empty.")
    total_w = sum(c.weight for c in comps)
    if total_w <= 0:
        raise ValueError("sum(weights) must be positive.")
    # 归一化权重
    comps = [LaneComponent(c.mu_x_frac, c.sigma_x_m, c.weight / total_w) for c in comps]
    return comps


def center_prob_map_gmm_separable(
    *,
    grid: RectGrid,
    lanes: List[Dict],
    mu_y_frac: float,
    sigma_y_m: float,
) -> np.ndarray:
    """接触中心的概率质量函数（2D），用“x方向车道混合 + y方向单高斯”的可分布模型。"""

    comps = _parse_lanes(lanes)

    # x 方向：多车道混合
    px = np.zeros_like(grid.x, dtype=float)
    for c in comps:
        mu_x = float(c.mu_x_frac) * grid.width_m
        px += c.weight * _normal_pdf(grid.x, mu_x, c.sigma_x_m)

    # y 方向：单高斯（上行/下行用不同均值）
    mu_y = float(mu_y_frac) * grid.depth_m
    py = _normal_pdf(grid.y, mu_y, sigma_y_m)

    dens = np.outer(py, px)  # (ny, nx)
    # 转为 cell 概率质量：dens * cell_area，然后归一化
    prob = dens * grid.cell_area_m2
    s = float(np.sum(prob))
    if s <= 0:
        raise ValueError("probability mass is zero; check sigmas and geometry.")
    prob /= s
    return prob


def sample_center_counts(
    *,
    prob_map: np.ndarray,
    n_contacts: int,
    rng: np.random.Generator,
    method: Literal["poisson", "multinomial"] = "poisson",
) -> np.ndarray:
    """从中心概率图中采样“每个格点作为接触中心的次数”。"""

    if n_contacts <= 0:
        return np.zeros_like(prob_map, dtype=int)

    if method == "poisson":
        # 各 cell 独立 Poisson，速度快；总和不严格等于 n_contacts（但期望等于）。
        lam = n_contacts * prob_map
        return rng.poisson(lam=lam).astype(int)

    if method == "multinomial":
        flat_p = prob_map.ravel()
        flat_p = flat_p / float(np.sum(flat_p))
        counts = rng.multinomial(n=n_contacts, pvals=flat_p)
        return counts.reshape(prob_map.shape).astype(int)

    raise ValueError(f"Unknown sampling method: {method}")


def make_edge_band_mask(grid: RectGrid, band_m: float) -> np.ndarray:
    """返回“靠近 y=depth 的边缘带”mask（踏鼻附近）。"""

    band_m = float(band_m)
    if band_m <= 0:
        return np.zeros((grid.ny, grid.nx), dtype=bool)

    y_threshold = grid.depth_m - band_m
    return (grid.Y >= y_threshold)


def lane_prob_along_x(grid: RectGrid, lanes: List[Dict]) -> np.ndarray:
    """将车道混合分布投影到 x 轴，得到每个 x cell 的概率质量（和为1）。"""

    comps = _parse_lanes(lanes)
    dens = np.zeros_like(grid.x, dtype=float)
    for c in comps:
        mu_x = float(c.mu_x_frac) * grid.width_m
        dens += c.weight * _normal_pdf(grid.x, mu_x, c.sigma_x_m)

    # 转为 cell 概率质量：dens * cell_width，然后归一化
    prob = dens * grid.cell_m
    s = float(np.sum(prob))
    if s <= 0:
        raise ValueError("lane_prob_along_x mass is zero.")
    prob /= s
    return prob


def sample_edge_scuff_centers(
    *,
    grid: RectGrid,
    lanes: List[Dict],
    band_m: float,
    n_scuff: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """采样“踏鼻边缘带”的摩擦/刮擦接触中心计数图（2D）。

    - x: 按车道分布
    - y: 限制在 edge band 内，默认在 band 内均匀
    """

    if n_scuff <= 0:
        return np.zeros((grid.ny, grid.nx), dtype=int)

    mask = make_edge_band_mask(grid, band_m)
    if not np.any(mask):
        return np.zeros((grid.ny, grid.nx), dtype=int)

    x_prob = lane_prob_along_x(grid, lanes)
    x_counts = rng.multinomial(n=n_scuff, pvals=x_prob)  # (nx,)

    # y 在 band 内均匀分配
    band_rows = np.where(mask[:, 0])[0]  # 取任意一列即可，因为 mask 在行上是统一的
    if band_rows.size == 0:
        return np.zeros((grid.ny, grid.nx), dtype=int)

    out = np.zeros((grid.ny, grid.nx), dtype=int)
    for ix in range(grid.nx):
        c = int(x_counts[ix])
        if c <= 0:
            continue
        # 将 c 均匀撒到 band_rows 上（multinomial）
        row_counts = rng.multinomial(n=c, pvals=np.ones(band_rows.size) / band_rows.size)
        out[band_rows, ix] += row_counts.astype(int)

    return out

