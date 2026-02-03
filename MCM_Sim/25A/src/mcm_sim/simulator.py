from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
from .io_utils import ensure_dir, save_json
from .metrics import compute_metrics
from .traffic_models import generate_daily_traffic_series
from .viz import plot_cross_section_y_mean, plot_heatmap


@dataclass(frozen=True)
class SimulationResult:
    run_dir: Path
    wear_depth_mm: np.ndarray  # (ny, nx)
    metrics: Dict[str, Any]
    metrics_over_time: list[Dict[str, Any]]


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_nested(d: Dict[str, Any], keys: Tuple[str, ...], default: Any) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def simulate_wear_forward(
    *,
    config: Dict[str, Any],
    project_dir: Path,
    run_name: Optional[str] = None,
) -> SimulationResult:
    """正向磨损仿真主入口（矩形表面 + 接触核 + Poisson 客流）。

    参数设计的目标是“可解释 + 可迁移”：
    - traffic：决定事件强度（一天有多少次接触）
    - contact：决定事件“落在哪里/覆盖多大面积”
    - wear：决定一次事件“磨掉多少”
    """

    rng = np.random.default_rng(int(config.get("random_seed", 0)))

    # -------- surface/grid --------
    surface = config.get("surface", {})
    width_m = float(surface.get("width_m", 1.2))
    depth_m = float(surface.get("depth_m", 0.3))
    cell_m = float(surface.get("cell_m", 0.005))
    grid: RectGrid = make_rect_grid(width_m=width_m, depth_m=depth_m, cell_m=cell_m)

    # -------- traffic --------
    traffic = config.get("traffic", {})
    n_days = int(traffic.get("n_days", 365))
    mean_daily_footfalls = float(traffic.get("mean_daily_footfalls", 3000.0))
    up_ratio = float(traffic.get("up_ratio", 0.5))
    day_profile = traffic.get("day_profile")
    seasonality = traffic.get("seasonality")
    daily_noise = traffic.get("daily_noise")

    traffic_series = generate_daily_traffic_series(
        n_days=n_days,
        mean_daily_footfalls=mean_daily_footfalls,
        up_ratio=up_ratio,
        rng=rng,
        day_profile=day_profile,
        seasonality=seasonality,
        daily_noise=daily_noise,
    )

    # -------- contact --------
    contact = config.get("contact", {})
    center_dist = contact.get("center_distribution", {})
    lanes = center_dist.get("lanes", [])
    mu_y_up_frac = float(center_dist.get("mu_y_up_frac", 0.75))
    mu_y_down_frac = float(center_dist.get("mu_y_down_frac", 0.85))
    sigma_y_m = float(center_dist.get("sigma_y_m", 0.06))

    sampling_method = str(_get_nested(contact, ("sampling", "method"), "poisson"))

    # 预计算：中心概率图（上/下行不同 y 均值）
    prob_up = center_prob_map_gmm_separable(
        grid=grid,
        lanes=lanes,
        mu_y_frac=mu_y_up_frac,
        sigma_y_m=sigma_y_m,
    )
    prob_down = center_prob_map_gmm_separable(
        grid=grid,
        lanes=lanes,
        mu_y_frac=mu_y_down_frac,
        sigma_y_m=sigma_y_m,
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

    # -------- output --------
    out_cfg = config.get("output", {})
    run_dir_base = Path(project_dir) / str(out_cfg.get("run_dir", "runs"))
    ensure_dir(run_dir_base)

    run_tag = run_name or f"run_{_timestamp()}"
    run_dir = ensure_dir(run_dir_base / run_tag)
    snapshots_dir = ensure_dir(run_dir / "snapshots")

    save_every_days = int(out_cfg.get("save_every_days", 30))
    make_plots = bool(out_cfg.get("make_plots", True))

    # 保存“实际使用的 config 快照”，便于论文复现
    save_json(run_dir / "config.used.json", config)

    # -------- simulate --------
    wear_depth_mm = np.zeros((grid.ny, grid.nx), dtype=float)
    metrics_over_time: list[Dict[str, Any]] = []

    cum_contacts = 0
    for day in range(n_days):
        n_up = int(traffic_series.up[day])
        n_down = int(traffic_series.down[day])
        n_total = n_up + n_down
        cum_contacts += n_total

        # 采样“接触中心次数图”（上/下行）
        counts_up = sample_center_counts(
            prob_map=prob_up, n_contacts=n_up, rng=rng, method=sampling_method
        )
        counts_down = sample_center_counts(
            prob_map=prob_down, n_contacts=n_down, rng=rng, method=sampling_method
        )
        center_counts = counts_up + counts_down

        # normal wear：中心次数图与足底接触核卷积
        equiv_contacts = convolve2d_same(center_counts, footprint_kernel)

        # edge scuff：在踏鼻边缘带采样额外接触，并叠加更强的磨损
        if edge_scuff_enabled and scuff_kernel is not None and edge_fraction > 0:
            n_scuff = int(rng.binomial(n=n_total, p=min(max(edge_fraction, 0.0), 1.0)))
            scuff_centers = sample_edge_scuff_centers(
                grid=grid, lanes=lanes, band_m=edge_band_m, n_scuff=n_scuff, rng=rng
            )
            equiv_scuff = convolve2d_same(scuff_centers, scuff_kernel)
            equiv_contacts = equiv_contacts + edge_scuff_multiplier * equiv_scuff

        # Archard-like：把“等效接触数”转换为磨损深度增量
        wear_depth_mm += wear_per_contact_peak_mm * equiv_contacts

        need_snapshot = (save_every_days > 0) and ((day + 1) % save_every_days == 0)
        is_last = (day == n_days - 1)
        if need_snapshot or is_last:
            day_tag = f"day_{day+1:04d}"
            np.save(snapshots_dir / f"{day_tag}_wear_depth_mm.npy", wear_depth_mm)

            snap_metrics = compute_metrics(wear_depth_mm, grid)
            snap_metrics.update(
                {
                    "day": int(day + 1),
                    "cum_contacts": int(cum_contacts),
                }
            )
            metrics_over_time.append(snap_metrics)

            if make_plots:
                plot_heatmap(
                    wear_depth_mm,
                    grid,
                    snapshots_dir / f"{day_tag}_wear_heatmap.png",
                    title=f"Wear depth (mm) - day {day+1}",
                )
                plot_cross_section_y_mean(
                    wear_depth_mm,
                    grid,
                    snapshots_dir / f"{day_tag}_cross_section_y_mean.png",
                    title=f"Mean profile vs y - day {day+1}",
                )

    # -------- save final --------
    np.save(run_dir / "wear_depth_final.npy", wear_depth_mm)
    if make_plots:
        plot_heatmap(wear_depth_mm, grid, run_dir / "wear_heatmap_final.png", title="Final wear depth (mm)")
        plot_cross_section_y_mean(
            wear_depth_mm, grid, run_dir / "cross_section_y_mean_final.png", title="Final mean profile vs y"
        )

    metrics = compute_metrics(wear_depth_mm, grid)
    metrics["traffic_summary"] = {
        "n_days": int(n_days),
        "cum_contacts": int(np.sum(traffic_series.total)),
        "mean_daily_contacts_simulated": float(np.mean(traffic_series.total)),
        "up_ratio_empirical": float(np.sum(traffic_series.up) / max(1, np.sum(traffic_series.total))),
    }
    save_json(run_dir / "metrics.json", metrics)
    save_json(run_dir / "metrics_over_time.json", metrics_over_time)

    return SimulationResult(
        run_dir=run_dir,
        wear_depth_mm=wear_depth_mm,
        metrics=metrics,
        metrics_over_time=metrics_over_time,
    )

