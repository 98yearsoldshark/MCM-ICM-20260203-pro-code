"""Model-0 功耗模型：把“场景输入”映射为组件级功耗分解（可解释）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcm26a.scenarios import Segment


@dataclass(frozen=True)
class PowerBreakdown:
    """功耗分解（单位：W）。"""

    base_w: float
    screen_w: float
    cpu_w: float
    gpu_w: float
    radio_w: float
    gps_w: float
    background_w: float
    interaction_w: float = 0.0
    other_w: float = 0.0

    @property
    def total_w(self) -> float:
        return (
            self.base_w
            + self.screen_w
            + self.cpu_w
            + self.gpu_w
            + self.radio_w
            + self.gps_w
            + self.background_w
            + self.interaction_w
            + self.other_w
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "base_w": self.base_w,
            "screen_w": self.screen_w,
            "cpu_w": self.cpu_w,
            "gpu_w": self.gpu_w,
            "radio_w": self.radio_w,
            "gps_w": self.gps_w,
            "background_w": self.background_w,
            "interaction_w": self.interaction_w,
            "other_w": self.other_w,
            "total_w": self.total_w,
        }


@dataclass(frozen=True)
class ScreenParams0:
    """屏幕功耗：P = P0 + k * brightness_nits（仅在 screen_on 时生效）。"""

    P0_W: float
    k_W_per_nit: float


@dataclass(frozen=True)
class LinearLoadParams0:
    """线性负载功耗：P = k * load（load 范围建议 [0,1]）。"""

    k_W: float


@dataclass(frozen=True)
class GPSParams0:
    """GPS 功耗：开 -> 常值 P_W。"""

    P_W: float


@dataclass(frozen=True)
class PowerParams0:
    """Model-0 功耗参数（单位：W）。

    说明：
    - 该参数集用于先跑通 Model-0 的端到端流程，不对应任何特定机型真实测量。
    - 后续应通过真实数据或公开数据进行校准，并给出不确定性区间。
    """

    base_W: float
    screen: ScreenParams0
    cpu: LinearLoadParams0
    gpu: LinearLoadParams0
    gps: GPSParams0
    background_level_W: dict[str, float]
    signal_multiplier: dict[str, float]
    radio_activity_W: dict[str, dict[str, float]]

    @staticmethod
    def from_json(path: str | Path) -> "PowerParams0":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        return PowerParams0(
            base_W=float(obj["base_W"]),
            screen=ScreenParams0(
                P0_W=float(obj["screen"]["P0_W"]),
                k_W_per_nit=float(obj["screen"]["k_W_per_nit"]),
            ),
            cpu=LinearLoadParams0(k_W=float(obj["cpu"]["k_W"])),
            gpu=LinearLoadParams0(k_W=float(obj["gpu"]["k_W"])),
            gps=GPSParams0(P_W=float(obj["gps"]["P_W"])),
            background_level_W={str(k): float(v) for k, v in obj["background_level_W"].items()},
            signal_multiplier={str(k): float(v) for k, v in obj["signal_multiplier"].items()},
            radio_activity_W={
                str(mode): {str(act): float(pw) for act, pw in acts.items()}
                for mode, acts in obj["radio_activity_W"].items()
            },
        )


def compute_power_breakdown(seg: Segment, params: PowerParams0) -> PowerBreakdown:
    """由 Segment 计算功耗分解。"""

    base_w = float(params.base_W)

    screen_w = 0.0
    if seg.screen_on:
        screen_w = float(params.screen.P0_W) + float(params.screen.k_W_per_nit) * float(seg.brightness_nits)
        screen_w = max(0.0, screen_w)

    cpu_w = max(0.0, float(params.cpu.k_W) * float(seg.cpu_load))
    gpu_w = max(0.0, float(params.gpu.k_W) * float(seg.gpu_load))

    gps_w = float(params.gps.P_W) if seg.gps_on else 0.0

    background_w = float(params.background_level_W.get(seg.background_level, 0.0))

    # 无线功耗：按 radio_mode + net_activity 查表，再乘以信号强弱系数
    mode_table = params.radio_activity_W.get(seg.radio_mode, {})
    radio_base = float(mode_table.get(seg.net_activity, mode_table.get("idle", 0.0)))
    sig_mul = float(params.signal_multiplier.get(seg.signal_quality, 1.0))
    radio_w = max(0.0, radio_base * sig_mul)

    return PowerBreakdown(
        base_w=base_w,
        screen_w=screen_w,
        cpu_w=cpu_w,
        gpu_w=gpu_w,
        radio_w=radio_w,
        gps_w=gps_w,
        background_w=background_w,
        interaction_w=0.0,
        other_w=0.0,
    )
