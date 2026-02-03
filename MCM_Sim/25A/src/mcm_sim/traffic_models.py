from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np


@dataclass(frozen=True)
class DailyTrafficSeries:
    """按天的人流序列（单位：人次/天或踏步接触次数/天）。"""

    total: np.ndarray  # (n_days,)
    up: np.ndarray  # (n_days,)
    down: np.ndarray  # (n_days,)


def _weekday_weekend_multiplier(day_index: int, weekday_multiplier: float, weekend_multiplier: float) -> float:
    # day_index=0 视为周一（只是约定，不影响长期统计）。
    dow = day_index % 7
    is_weekend = dow in (5, 6)
    return weekend_multiplier if is_weekend else weekday_multiplier


def _seasonality_multiplier(day_index: int, seasonality: Optional[Dict]) -> float:
    if not seasonality:
        return 1.0
    if seasonality.get("type") != "sinusoid":
        return 1.0

    amp = float(seasonality.get("amplitude", 0.0))
    period = float(seasonality.get("period_days", 365.0))
    phase = float(seasonality.get("phase_days", 0.0))
    # 1 + amp*sin(...)，并裁剪到非负，避免出现负流量。
    val = 1.0 + amp * np.sin(2.0 * np.pi * (day_index - phase) / period)
    return float(max(0.0, val))


def _daily_noise_multiplier(rng: np.random.Generator, daily_noise: Optional[Dict]) -> float:
    if not daily_noise:
        return 1.0
    if daily_noise.get("type") != "lognormal":
        return 1.0
    sigma = float(daily_noise.get("sigma", 0.0))
    if sigma <= 0:
        return 1.0
    # 以 1 为中位数的对数正态噪声（更贴近“客流波动”的右偏分布）。
    return float(rng.lognormal(mean=0.0, sigma=sigma))


def generate_daily_traffic_series(
    *,
    n_days: int,
    mean_daily_footfalls: float,
    up_ratio: float,
    rng: np.random.Generator,
    day_profile: Optional[Dict] = None,
    seasonality: Optional[Dict] = None,
    daily_noise: Optional[Dict] = None,
) -> DailyTrafficSeries:
    """生成按天人流（或接触次数）序列。

    这里采用“强度 -> Poisson 采样”的方式，适合长期模拟：
    - 周内/周末倍率
    - 年周期季节性
    - 日级别随机波动（对数正态）
    """

    if n_days <= 0:
        raise ValueError("n_days must be positive.")
    if mean_daily_footfalls < 0:
        raise ValueError("mean_daily_footfalls must be non-negative.")
    if not (0.0 <= up_ratio <= 1.0):
        raise ValueError("up_ratio must be in [0, 1].")

    total = np.zeros(n_days, dtype=int)
    up = np.zeros(n_days, dtype=int)
    down = np.zeros(n_days, dtype=int)

    profile_type = (day_profile or {}).get("type", "constant")
    weekday_mult = float((day_profile or {}).get("weekday_multiplier", 1.0))
    weekend_mult = float((day_profile or {}).get("weekend_multiplier", 1.0))

    for t in range(n_days):
        mult = 1.0
        if profile_type == "weekday_weekend":
            mult *= _weekday_weekend_multiplier(t, weekday_mult, weekend_mult)

        mult *= _seasonality_multiplier(t, seasonality)
        mult *= _daily_noise_multiplier(rng, daily_noise)

        lam = max(0.0, mean_daily_footfalls * mult)
        n = int(rng.poisson(lam=lam))

        n_up = int(rng.binomial(n=n, p=up_ratio))
        n_down = n - n_up

        total[t] = n
        up[t] = n_up
        down[t] = n_down

    return DailyTrafficSeries(total=total, up=up, down=down)

