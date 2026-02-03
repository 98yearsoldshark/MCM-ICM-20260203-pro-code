"""Model-0 不确定性量化：对参数做采样，传播到 TTE 的分布与敏感性。"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from mcm26a.battery import BatteryParams0
from mcm26a.power.model0 import GPSParams0, LinearLoadParams0, PowerParams0, ScreenParams0


def _uniform(rng: random.Random, lo: float, hi: float) -> float:
    return lo + (hi - lo) * rng.random()


@dataclass(frozen=True)
class Model0UQSample:
    """Model-0 的采样参数（尽量用“组尺度因子”，减少维度）。"""

    battery_energy_scale: float
    base_scale: float
    screen_scale: float
    cpu_scale: float
    gpu_scale: float
    gps_scale: float
    background_scale: float
    radio_scale: float
    poor_signal_multiplier: float


def sample_model0_uq(rng: random.Random) -> Model0UQSample:
    """生成一组不确定性采样值。

    说明：这些范围是“无数据时的合理先验”，主要用于展示方法与稳健性；
    后续应结合真实测量缩小范围或改用贝叶斯后验。
    """

    return Model0UQSample(
        battery_energy_scale=_uniform(rng, 0.90, 1.10),
        base_scale=_uniform(rng, 0.70, 1.30),
        screen_scale=_uniform(rng, 0.70, 1.30),
        cpu_scale=_uniform(rng, 0.60, 1.40),
        gpu_scale=_uniform(rng, 0.60, 1.40),
        gps_scale=_uniform(rng, 0.70, 1.30),
        background_scale=_uniform(rng, 0.70, 1.30),
        radio_scale=_uniform(rng, 0.60, 1.60),
        poor_signal_multiplier=_uniform(rng, 1.2, 2.6),
    )


def apply_uq_sample(
    base_power: PowerParams0,
    base_battery: BatteryParams0,
    s: Model0UQSample,
) -> tuple[PowerParams0, BatteryParams0]:
    """把采样值应用到参数集，得到一组“抽样参数”。"""

    p = PowerParams0(
        base_W=base_power.base_W * s.base_scale,
        screen=ScreenParams0(
            P0_W=base_power.screen.P0_W * s.screen_scale,
            k_W_per_nit=base_power.screen.k_W_per_nit * s.screen_scale,
        ),
        cpu=LinearLoadParams0(k_W=base_power.cpu.k_W * s.cpu_scale),
        gpu=LinearLoadParams0(k_W=base_power.gpu.k_W * s.gpu_scale),
        gps=GPSParams0(P_W=base_power.gps.P_W * s.gps_scale),
        background_level_W={k: v * s.background_scale for k, v in base_power.background_level_W.items()},
        signal_multiplier={
            "good": 1.0,
            "poor": float(s.poor_signal_multiplier),
        },
        radio_activity_W={
            mode: {act: pw * s.radio_scale for act, pw in acts.items()}
            for mode, acts in base_power.radio_activity_W.items()
        },
    )

    b = replace(base_battery, energy_Wh=base_battery.energy_Wh * s.battery_energy_scale)
    return p, b

