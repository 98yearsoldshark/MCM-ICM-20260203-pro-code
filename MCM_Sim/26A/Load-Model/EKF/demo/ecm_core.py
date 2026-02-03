"""
EKF demo 依赖的最小 ECM（Thevenin）1RC/2RC（电流输入版）。

注意：本文件与 `ECM-1RCor2RC/demo/ecm_core.py` 基本一致，单独拷贝一份是为了让 EKF demo
可以“单目录直接运行”（便于交接，不需要跨目录 import）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


@dataclass(frozen=True)
class PiecewiseLinearOCV:
    points: Tuple[Tuple[float, float], ...]  # (soc, ocv_V)

    @staticmethod
    def from_points(points: Sequence[Sequence[float]]) -> "PiecewiseLinearOCV":
        pts: List[Tuple[float, float]] = []
        for p in points:
            if len(p) != 2:
                raise ValueError("each point must be [soc, V]")
            pts.append((float(p[0]), float(p[1])))
        pts.sort(key=lambda t: t[0])
        if len(pts) < 2:
            raise ValueError("need at least 2 points")
        return PiecewiseLinearOCV(points=tuple(pts))

    def ocv(self, soc: float) -> float:
        x = _clamp(soc, 0.0, 1.0)
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
        return float(self.points[-1][1])

    def docv_dsoc(self, soc: float) -> float:
        x = _clamp(soc, 0.0, 1.0)
        if x <= self.points[0][0]:
            x0, y0 = self.points[0]
            x1, y1 = self.points[1]
            return 0.0 if x1 == x0 else (y1 - y0) / (x1 - x0)
        if x >= self.points[-1][0]:
            x0, y0 = self.points[-2]
            x1, y1 = self.points[-1]
            return 0.0 if x1 == x0 else (y1 - y0) / (x1 - x0)

        for (x0, y0), (x1, y1) in zip(self.points[:-1], self.points[1:]):
            if x0 <= x <= x1:
                return 0.0 if x1 == x0 else (y1 - y0) / (x1 - x0)
        x0, y0 = self.points[-2]
        x1, y1 = self.points[-1]
        return 0.0 if x1 == x0 else (y1 - y0) / (x1 - x0)


@dataclass(frozen=True)
class ECM1RCParams:
    capacity_Ah: float
    r0_ohm: float
    r1_ohm: float
    c1_F: float
    ocv: PiecewiseLinearOCV

    @property
    def q_coulomb(self) -> float:
        return 3600.0 * float(self.capacity_Ah)


@dataclass(frozen=True)
class ECM2RCParams:
    capacity_Ah: float
    r0_ohm: float
    r1_ohm: float
    c1_F: float
    r2_ohm: float
    c2_F: float
    ocv: PiecewiseLinearOCV

    @property
    def q_coulomb(self) -> float:
        return 3600.0 * float(self.capacity_Ah)


def step_1rc_x(x, *, I_A: float, dt_s: float, p: ECM1RCParams):
    """状态单步（用于 EKF）：x=[soc, v1] -> x_next"""

    soc, v1 = float(x[0]), float(x[1])
    dt = float(dt_s)
    i = float(I_A)

    soc = _clamp(soc - dt * i / p.q_coulomb, 0.0, 1.0)

    tau1 = float(p.r1_ohm) * float(p.c1_F)
    a1 = math.exp(-dt / tau1)
    b1 = float(p.r1_ohm) * (1.0 - a1)
    v1 = a1 * v1 + b1 * i
    return [soc, v1], a1


def step_2rc_x(x, *, I_A: float, dt_s: float, p: ECM2RCParams):
    """状态单步（用于 EKF）：x=[soc, v1, v2] -> x_next"""

    soc, v1, v2 = float(x[0]), float(x[1]), float(x[2])
    dt = float(dt_s)
    i = float(I_A)

    soc = _clamp(soc - dt * i / p.q_coulomb, 0.0, 1.0)

    tau1 = float(p.r1_ohm) * float(p.c1_F)
    a1 = math.exp(-dt / tau1)
    b1 = float(p.r1_ohm) * (1.0 - a1)
    v1 = a1 * v1 + b1 * i

    tau2 = float(p.r2_ohm) * float(p.c2_F)
    a2 = math.exp(-dt / tau2)
    b2 = float(p.r2_ohm) * (1.0 - a2)
    v2 = a2 * v2 + b2 * i

    return [soc, v1, v2], a1, a2


def h_1rc(x, *, I_A: float, p: ECM1RCParams) -> float:
    soc, v1 = float(x[0]), float(x[1])
    i = float(I_A)
    return float(p.ocv.ocv(soc)) - i * float(p.r0_ohm) - v1


def h_2rc(x, *, I_A: float, p: ECM2RCParams) -> float:
    soc, v1, v2 = float(x[0]), float(x[1]), float(x[2])
    i = float(I_A)
    return float(p.ocv.ocv(soc)) - i * float(p.r0_ohm) - v1 - v2

