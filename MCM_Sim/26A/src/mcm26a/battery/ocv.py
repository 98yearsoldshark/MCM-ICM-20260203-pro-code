"""OCV(SOC) 曲线：用于把 SOC 映射为开路电压（Model-1/2/3 会用到）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PiecewiseLinearOCV:
    """分段线性 OCV 曲线：由若干 (soc, ocv_v) 点线性插值。"""

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("points must contain at least 2 points")
        xs = [p[0] for p in self.points]
        if any(xs[i] > xs[i + 1] for i in range(len(xs) - 1)):
            raise ValueError("points must be sorted by soc (ascending)")

    def ocv_v(self, soc: float) -> float:
        """线性插值（soc 超界则截断到 [0,1]）。"""

        x = float(soc)
        if x <= self.points[0][0]:
            return float(self.points[0][1])
        if x >= self.points[-1][0]:
            return float(self.points[-1][1])

        for (x0, y0), (x1, y1) in zip(self.points[:-1], self.points[1:]):
            if x0 <= x <= x1:
                if x1 == x0:
                    return float(y0)
                w = (x - x0) / (x1 - x0)
                return float(y0) * (1.0 - w) + float(y1) * w

        # 理论上不会到这里
        return float(self.points[-1][1])

    def soc_from_ocv_v(self, ocv_v: float) -> float:
        """由 OCV 反推 SOC（单调假设下的分段线性反插值）。

        说明：
        - 该方法假设 OCV 随 SOC 单调不减（在本项目的拟合中会强制单调）。
        - 若输入电压超出曲线范围，则截断到端点 SOC。
        - 该函数常用于“用休止段电压估计初始 SOC”的近似初始化。
        """

        v = float(ocv_v)
        v0 = float(self.points[0][1])
        v1 = float(self.points[-1][1])
        if v <= v0:
            return float(self.points[0][0])
        if v >= v1:
            return float(self.points[-1][0])

        for (s0, vv0), (s1, vv1) in zip(self.points[:-1], self.points[1:]):
            lo = float(vv0)
            hi = float(vv1)
            if lo <= v <= hi:
                if hi == lo:
                    return float(s0)
                w = (v - lo) / (hi - lo)
                return float(s0) * (1.0 - w) + float(s1) * w

        # 兜底：若曲线含极小非单调噪声，按“最近点”返回
        best_s = float(self.points[0][0])
        best_d = abs(v - float(self.points[0][1]))
        for s, vv in self.points[1:]:
            d = abs(v - float(vv))
            if d < best_d:
                best_d = d
                best_s = float(s)
        return best_s

    @staticmethod
    def from_config(cfg: dict[str, Any]) -> "PiecewiseLinearOCV":
        if str(cfg.get("type", "")).lower() not in ("piecewise_linear", "pwl", "linear"):
            raise ValueError("unsupported ocv_curve type; expected piecewise_linear")
        pts = cfg.get("points", [])
        if not isinstance(pts, list):
            raise ValueError("ocv_curve.points must be a list")
        points = []
        for p in pts:
            if not (isinstance(p, list) or isinstance(p, tuple)) or len(p) != 2:
                raise ValueError("each ocv point must be [soc, V]")
            points.append((float(p[0]), float(p[1])))
        points.sort(key=lambda t: t[0])
        return PiecewiseLinearOCV(points=tuple(points))
