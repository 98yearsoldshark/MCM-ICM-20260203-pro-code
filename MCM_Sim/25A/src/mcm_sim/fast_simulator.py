from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .contact_models import (
    center_prob_map_gmm_separable,
    make_elliptical_gaussian_kernel,
    sample_center_counts,
    sample_edge_scuff_centers,
)
from .convolution import convolve2d_same
from .grid import RectGrid, make_rect_grid


@dataclass(frozen=True)
class FastSimOutput:
    grid: RectGrid
    wear_depth_mm: np.ndarray
    debug: Dict[str, Any]


def _int_nonneg(x: Any) -> int:
    v = int(round(float(x)))
    return max(0, v)


def _compute_total_contacts(traffic: Dict[str, Any], rng: np.random.Generator) -> Tuple[int, int, int]:
    """返回 (n_total, n_up, n_down)。"""

    up_ratio = float(traffic.get("up_ratio", 0.5))
    up_ratio = float(np.clip(up_ratio, 0.0, 1.0))

    if "total_contacts_up" in traffic or "total_contacts_down" in traffic:
        n_up = _int_nonneg(traffic.get("total_contacts_up", 0))
        n_down = _int_nonneg(traffic.get("total_contacts_down", 0))
        return (n_up + n_down, n_up, n_down)

    if "total_contacts" in traffic:
        n_total = _int_nonneg(traffic.get("total_contacts", 0))
        n_up = int(rng.binomial(n=n_total, p=up_ratio))
        return (n_total, n_up, n_total - n_up)

    # fallback：用 n_days * mean_daily_footfalls 估算总接触次数
    n_days = int(traffic.get("n_days", 365))
    mean_daily = float(traffic.get("mean_daily_footfalls", 3000.0))
    n_total = _int_nonneg(n_days * mean_daily)
    n_up = int(rng.binomial(n=n_total, p=up_ratio))
    return (n_total, n_up, n_total - n_up)


def _simulate_phase(
    *,
    grid: RectGrid,
    prob_up: np.ndarray,
    prob_down: np.ndarray,
    footprint_kernel: np.ndarray,
    lanes: list,
    n_up: int,
    n_down: int,
    sampling_method: str,
    edge_scuff_enabled: bool,
    edge_band_m: float,
    edge_fraction: float,
    scuff_kernel: Optional[np.ndarray],
    edge_scuff_multiplier: float,
    wear_per_contact_peak_mm: float,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    n_total = int(n_up + n_down)

    counts_up = sample_center_counts(prob_map=prob_up, n_contacts=n_up, rng=rng, method=sampling_method)
    counts_down = sample_center_counts(prob_map=prob_down, n_contacts=n_down, rng=rng, method=sampling_method)
    center_counts = counts_up + counts_down

    equiv_contacts = convolve2d_same(center_counts, footprint_kernel)

    n_scuff = 0
    if edge_scuff_enabled and scuff_kernel is not None and edge_fraction > 0 and n_total > 0:
        edge_fraction = float(np.clip(edge_fraction, 0.0, 1.0))
        n_scuff = int(rng.binomial(n=n_total, p=edge_fraction))
        scuff_centers = sample_edge_scuff_centers(
            grid=grid, lanes=lanes, band_m=edge_band_m, n_scuff=n_scuff, rng=rng
        )
        equiv_scuff = convolve2d_same(scuff_centers, scuff_kernel)
        equiv_contacts = equiv_contacts + edge_scuff_multiplier * equiv_scuff

    wear_inc = wear_per_contact_peak_mm * equiv_contacts
    dbg = {"n_total": n_total, "n_up": int(n_up), "n_down": int(n_down), "n_edge_scuff": int(n_scuff)}
    return wear_inc, dbg


def simulate_wear_fast(config: Dict[str, Any], *, rng: Optional[np.random.Generator] = None) -> FastSimOutput:
    """快速生成最终磨损场（不做逐日循环），适合大规模参数实验/拟合对比。"""

    rng = rng or np.random.default_rng(int(config.get("random_seed", 0)))

    # -------- surface/grid --------
    surface = config.get("surface", {})
    grid = make_rect_grid(
        width_m=float(surface.get("width_m", 1.2)),
        depth_m=float(surface.get("depth_m", 0.3)),
        cell_m=float(surface.get("cell_m", 0.005)),
    )

    # -------- contact --------
    contact = config.get("contact", {})
    center_dist = contact.get("center_distribution", {})
    lanes = center_dist.get("lanes", [])
    mu_y_up_frac = float(center_dist.get("mu_y_up_frac", 0.75))
    mu_y_down_frac = float(center_dist.get("mu_y_down_frac", 0.85))
    sigma_y_m = float(center_dist.get("sigma_y_m", 0.06))
    sampling_method = str((contact.get("sampling") or {}).get("method", "poisson"))

    prob_up = center_prob_map_gmm_separable(
        grid=grid, lanes=lanes, mu_y_frac=mu_y_up_frac, sigma_y_m=sigma_y_m
    )
    prob_down = center_prob_map_gmm_separable(
        grid=grid, lanes=lanes, mu_y_frac=mu_y_down_frac, sigma_y_m=sigma_y_m
    )

    footprint_kernel_cfg = contact.get("footprint_kernel", {})
    footprint_kernel = make_elliptical_gaussian_kernel(
        cell_m=grid.cell_m,
        sigma_x_m=float(footprint_kernel_cfg.get("sigma_x_m", 0.055)),
        sigma_y_m=float(footprint_kernel_cfg.get("sigma_y_m", 0.095)),
        size_m=float(footprint_kernel_cfg.get("size_m", 0.35)),
    )

    edge_scuff_cfg = contact.get("edge_scuff", {})
    edge_scuff_enabled = bool(edge_scuff_cfg.get("enabled", False))
    edge_band_m = float(edge_scuff_cfg.get("band_m", 0.02))
    edge_fraction = float(edge_scuff_cfg.get("fraction_of_contacts", 0.0))

    scuff_kernel = None
    if edge_scuff_enabled:
        scuff_kernel_cfg = edge_scuff_cfg.get("kernel", {})
        scuff_kernel = make_elliptical_gaussian_kernel(
            cell_m=grid.cell_m,
            sigma_x_m=float(scuff_kernel_cfg.get("sigma_x_m", 0.06)),
            sigma_y_m=float(scuff_kernel_cfg.get("sigma_y_m", 0.015)),
            size_m=float(scuff_kernel_cfg.get("size_m", 0.20)),
        )

    # -------- wear law --------
    wear_cfg = config.get("wear", {})
    wear_per_contact_peak_mm = float(wear_cfg.get("wear_per_contact_peak_mm", 1e-7))
    edge_scuff_multiplier = float(wear_cfg.get("edge_scuff_multiplier", 5.0))

    # -------- traffic totals (aggregate) --------
    traffic = config.get("traffic", {})
    n_total, n_up, n_down = _compute_total_contacts(traffic, rng)

    wear_depth_mm = np.zeros((grid.ny, grid.nx), dtype=float)
    debug: Dict[str, Any] = {"phases": []}

    # -------- optional repair (two-phase) --------
    repair = config.get("repair") or {}
    repair_enabled = bool(repair.get("enabled", False))
    if repair_enabled:
        frac = float(repair.get("fraction", 0.5))
        frac = float(np.clip(frac, 0.0, 1.0))
        n_pre = int(round(n_total * frac))
        n_post = int(n_total - n_pre)

        # 这里假设 up/down 比例在 repair 前后不变
        n_up_pre = int(round(n_pre * (n_up / max(1, n_total))))
        n_down_pre = n_pre - n_up_pre
        n_up_post = n_up - n_up_pre
        n_down_post = n_down - n_down_pre

        inc1, dbg1 = _simulate_phase(
            grid=grid,
            prob_up=prob_up,
            prob_down=prob_down,
            footprint_kernel=footprint_kernel,
            lanes=lanes,
            n_up=n_up_pre,
            n_down=n_down_pre,
            sampling_method=sampling_method,
            edge_scuff_enabled=edge_scuff_enabled,
            edge_band_m=edge_band_m,
            edge_fraction=edge_fraction,
            scuff_kernel=scuff_kernel,
            edge_scuff_multiplier=edge_scuff_multiplier,
            wear_per_contact_peak_mm=wear_per_contact_peak_mm,
            rng=rng,
        )
        wear_depth_mm += inc1

        # repair/reset
        x0, x1 = repair.get("x_range_m", [0.0, grid.width_m])
        y0, y1 = repair.get("y_range_m", [0.0, grid.depth_m])
        reset_to = float(repair.get("reset_to_mm", 0.0))
        mask = (grid.X >= float(x0)) & (grid.X <= float(x1)) & (grid.Y >= float(y0)) & (grid.Y <= float(y1))
        wear_depth_mm[mask] = reset_to

        inc2, dbg2 = _simulate_phase(
            grid=grid,
            prob_up=prob_up,
            prob_down=prob_down,
            footprint_kernel=footprint_kernel,
            lanes=lanes,
            n_up=n_up_post,
            n_down=n_down_post,
            sampling_method=sampling_method,
            edge_scuff_enabled=edge_scuff_enabled,
            edge_band_m=edge_band_m,
            edge_fraction=edge_fraction,
            scuff_kernel=scuff_kernel,
            edge_scuff_multiplier=edge_scuff_multiplier,
            wear_per_contact_peak_mm=wear_per_contact_peak_mm,
            rng=rng,
        )
        wear_depth_mm += inc2

        debug["phases"] = [
            {"name": "pre_repair", **dbg1, "fraction": frac},
            {"name": "post_repair", **dbg2, "fraction": 1.0 - frac},
        ]
        debug["repair"] = {
            "enabled": True,
            "fraction": frac,
            "x_range_m": [float(x0), float(x1)],
            "y_range_m": [float(y0), float(y1)],
            "reset_to_mm": reset_to,
        }
    else:
        inc, dbg = _simulate_phase(
            grid=grid,
            prob_up=prob_up,
            prob_down=prob_down,
            footprint_kernel=footprint_kernel,
            lanes=lanes,
            n_up=n_up,
            n_down=n_down,
            sampling_method=sampling_method,
            edge_scuff_enabled=edge_scuff_enabled,
            edge_band_m=edge_band_m,
            edge_fraction=edge_fraction,
            scuff_kernel=scuff_kernel,
            edge_scuff_multiplier=edge_scuff_multiplier,
            wear_per_contact_peak_mm=wear_per_contact_peak_mm,
            rng=rng,
        )
        wear_depth_mm += inc
        debug["phases"] = [{"name": "single", **dbg}]

    debug["traffic_total"] = {"n_total": int(n_total), "n_up": int(n_up), "n_down": int(n_down)}
    return FastSimOutput(grid=grid, wear_depth_mm=wear_depth_mm, debug=debug)

