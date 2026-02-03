"""使用场景：确定性时间表与随机过程生成器。"""

from .schedule import Segment, Scenario, load_scenarios_json, materialize_scenario
from .transforms import (
    disable_gps,
    force_radio_mode,
    map_segments,
    set_background_level,
    set_brightness_for_screen_on,
    set_signal_quality,
)

__all__ = [
    "Segment",
    "Scenario",
    "load_scenarios_json",
    "materialize_scenario",
    "map_segments",
    "set_brightness_for_screen_on",
    "force_radio_mode",
    "set_signal_quality",
    "disable_gps",
    "set_background_level",
]
