"""单位换算（尽量使用 SI；论文展示时再换算为小时等）。"""

from __future__ import annotations


def wh_to_j(energy_wh: float) -> float:
    """瓦时（Wh）转焦耳（J）。"""

    return float(energy_wh) * 3600.0


def j_to_wh(energy_j: float) -> float:
    """焦耳（J）转瓦时（Wh）。"""

    return float(energy_j) / 3600.0


def seconds_to_hours(t_s: float) -> float:
    """秒转小时。"""

    return float(t_s) / 3600.0


def hours_to_seconds(t_h: float) -> float:
    """小时转秒。"""

    return float(t_h) * 3600.0

