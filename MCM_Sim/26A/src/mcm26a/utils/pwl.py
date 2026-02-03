"""分段线性曲线工具：用于把 x（例如 SOC）映射为某个参数值。

说明：
- 本项目里 OCV(SOC) 已有单独实现；但 R0(SOC)、R1(SOC) 等也常需要“分段线性 + 截断外推”。
- 这里抽象成通用 PiecewiseLinearCurve，避免在多个模块里重复写插值逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PiecewiseLinearCurve:
    """通用分段线性曲线：由若干 (x, y) 点线性插值。"""

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("points 必须至少包含 2 个点")
        xs = [p[0] for p in self.points]
        if any(xs[i] > xs[i + 1] for i in range(len(xs) - 1)):
            raise ValueError("points 必须按 x 升序排序")

    def value(self, x: float) -> float:
        """线性插值（x 超界则截断到端点）。"""

        xx = float(x)
        if xx <= self.points[0][0]:
            return float(self.points[0][1])
        if xx >= self.points[-1][0]:
            return float(self.points[-1][1])

        for (x0, y0), (x1, y1) in zip(self.points[:-1], self.points[1:]):
            if x0 <= xx <= x1:
                if x1 == x0:
                    return float(y0)
                w = (xx - x0) / (x1 - x0)
                return float(y0) * (1.0 - w) + float(y1) * w

        # 理论上不会到这里
        return float(self.points[-1][1])

    @staticmethod
    def from_config(cfg: dict[str, Any]) -> "PiecewiseLinearCurve":
        t = str(cfg.get("type", "")).lower()
        if t not in ("piecewise_linear", "pwl", "linear"):
            raise ValueError("unsupported curve type; expected piecewise_linear")

        pts = cfg.get("points", [])
        if not isinstance(pts, list):
            raise ValueError("curve.points 必须是 list")

        points: list[tuple[float, float]] = []
        for p in pts:
            if not (isinstance(p, list) or isinstance(p, tuple)) or len(p) != 2:
                raise ValueError("每个点必须是 [x, y]")
            points.append((float(p[0]), float(p[1])))
        points.sort(key=lambda kv: kv[0])
        return PiecewiseLinearCurve(points=tuple(points))

