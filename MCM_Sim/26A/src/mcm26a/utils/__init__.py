"""通用小工具（单位、随机数、日志等）。"""

from .pwl import PiecewiseLinearCurve
from .units import hours_to_seconds, j_to_wh, seconds_to_hours, wh_to_j

__all__ = [
    "PiecewiseLinearCurve",
    "hours_to_seconds",
    "j_to_wh",
    "seconds_to_hours",
    "wh_to_j",
]
