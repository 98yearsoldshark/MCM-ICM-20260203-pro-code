"""场景变换：用于构造“反事实/策略”情形（Model-0 起就能用）。"""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .schedule import Scenario, Segment


def map_segments(scenario: Scenario, fn: Callable[[int, Segment], Segment]) -> Scenario:
    """对场景的每个 segment 做映射，返回新场景。"""

    new_schedule = []
    for i, seg in enumerate(scenario.schedule):
        new_schedule.append(fn(i, seg))
    return replace(scenario, schedule=tuple(new_schedule))


def set_brightness_for_screen_on(scenario: Scenario, *, brightness_nits: float) -> Scenario:
    """把所有 screen_on 段的亮度改为指定值（nits）。"""

    b = float(brightness_nits)

    def _fn(_: int, seg: Segment) -> Segment:
        if not seg.screen_on:
            return seg
        return replace(seg, brightness_nits=b)

    return map_segments(scenario, _fn)


def force_radio_mode(scenario: Scenario, *, radio_mode: str) -> Scenario:
    """强制把所有段的 radio_mode 设为指定模式（wifi/lte/5g）。"""

    mode = str(radio_mode)

    def _fn(_: int, seg: Segment) -> Segment:
        return replace(seg, radio_mode=mode)

    return map_segments(scenario, _fn)


def set_signal_quality(scenario: Scenario, *, signal_quality: str) -> Scenario:
    """把所有段的信号质量设为 good/poor。"""

    q = str(signal_quality)

    def _fn(_: int, seg: Segment) -> Segment:
        return replace(seg, signal_quality=q)

    return map_segments(scenario, _fn)


def disable_gps(scenario: Scenario) -> Scenario:
    """关闭所有段的 GPS。"""

    def _fn(_: int, seg: Segment) -> Segment:
        if not seg.gps_on:
            return seg
        return replace(seg, gps_on=False)

    return map_segments(scenario, _fn)


def set_background_level(scenario: Scenario, *, level: str) -> Scenario:
    """把所有段的后台活动强度设为 low/medium/high。"""

    lv = str(level)

    def _fn(_: int, seg: Segment) -> Segment:
        return replace(seg, background_level=lv)

    return map_segments(scenario, _fn)

