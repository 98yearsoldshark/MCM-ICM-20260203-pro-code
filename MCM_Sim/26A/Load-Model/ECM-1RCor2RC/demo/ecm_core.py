"""
最小可用 ECM（Thevenin）1RC/2RC 实现（电流输入版）。

约定：
- I>0 表示放电（SOC 下降）
- 端电压：V = OCV(SOC) - I*R0 - sum(Vj)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


@dataclass(frozen=True)
class PiecewiseLinearOCV:
    """分段线性 OCV-SOC 曲线（含导数，EKF 需要 dOCV/dSOC）。"""

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
        """分段常数导数；在折点处返回“所在区间”的斜率。"""

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


@dataclass(frozen=True)
class ECM1RCState:
    soc: float
    v1_V: float


@dataclass(frozen=True)
class ECM2RCState:
    soc: float
    v1_V: float
    v2_V: float


def step_1rc(state: ECM1RCState, *, I_A: float, dt_s: float, p: ECM1RCParams) -> Tuple[ECM1RCState, float]:
    """单步更新（电流输入）。返回 (new_state, V_terminal)。"""

    dt = float(dt_s)
    i = float(I_A)

    soc = float(state.soc) - dt * i / p.q_coulomb
    soc = _clamp(soc, 0.0, 1.0)

    tau1 = float(p.r1_ohm) * float(p.c1_F)
    a1 = math.exp(-dt / tau1)
    b1 = float(p.r1_ohm) * (1.0 - a1)
    v1 = a1 * float(state.v1_V) + b1 * i

    v_term = float(p.ocv.ocv(soc)) - i * float(p.r0_ohm) - v1
    return ECM1RCState(soc=soc, v1_V=v1), v_term


def step_2rc(state: ECM2RCState, *, I_A: float, dt_s: float, p: ECM2RCParams) -> Tuple[ECM2RCState, float]:
    """单步更新（电流输入）。返回 (new_state, V_terminal)。"""

    dt = float(dt_s)
    i = float(I_A)

    soc = float(state.soc) - dt * i / p.q_coulomb
    soc = _clamp(soc, 0.0, 1.0)

    tau1 = float(p.r1_ohm) * float(p.c1_F)
    a1 = math.exp(-dt / tau1)
    b1 = float(p.r1_ohm) * (1.0 - a1)
    v1 = a1 * float(state.v1_V) + b1 * i

    tau2 = float(p.r2_ohm) * float(p.c2_F)
    a2 = math.exp(-dt / tau2)
    b2 = float(p.r2_ohm) * (1.0 - a2)
    v2 = a2 * float(state.v2_V) + b2 * i

    v_term = float(p.ocv.ocv(soc)) - i * float(p.r0_ohm) - v1 - v2
    return ECM2RCState(soc=soc, v1_V=v1, v2_V=v2), v_term


def load_1rc_params_from_mcm_json(path: str) -> ECM1RCParams:
    """读取本仓库 26A 的 ECM 配置风格（如 phone_default_v1_ecm.json）。"""

    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    batt = obj.get("battery", obj)
    ecm = batt.get("ecm", {})

    cap_ah = float(batt["capacity_mAh"]) / 1000.0
    r0 = float(ecm["R0_ohm"])
    r1 = float(ecm["R1_ohm"])
    c1 = float(ecm["C1_F"])

    ocv_cfg = ecm.get("ocv_curve", {})
    pts = ocv_cfg.get("points", None)
    if not isinstance(pts, list):
        raise ValueError("ocv_curve.points missing or not a list")
    ocv = PiecewiseLinearOCV.from_points(pts)

    return ECM1RCParams(capacity_Ah=cap_ah, r0_ohm=r0, r1_ohm=r1, c1_F=c1, ocv=ocv)


def simulate_1rc(
    *,
    params: ECM1RCParams,
    soc0: float,
    dt_s: float,
    current_A: Sequence[float],
) -> Tuple[List[ECM1RCState], List[float]]:
    s = ECM1RCState(soc=float(soc0), v1_V=0.0)
    states: List[ECM1RCState] = [s]
    volts: List[float] = [float(params.ocv.ocv(s.soc))]
    for i in current_A:
        s, v = step_1rc(s, I_A=float(i), dt_s=float(dt_s), p=params)
        states.append(s)
        volts.append(float(v))
    return states, volts


def simulate_2rc(
    *,
    params: ECM2RCParams,
    soc0: float,
    dt_s: float,
    current_A: Sequence[float],
) -> Tuple[List[ECM2RCState], List[float]]:
    s = ECM2RCState(soc=float(soc0), v1_V=0.0, v2_V=0.0)
    states: List[ECM2RCState] = [s]
    volts: List[float] = [float(params.ocv.ocv(s.soc))]
    for i in current_A:
        s, v = step_2rc(s, I_A=float(i), dt_s=float(dt_s), p=params)
        states.append(s)
        volts.append(float(v))
    return states, volts


def make_pulse_current(
    *,
    dt_s: float,
    segments: Sequence[Tuple[float, float]],
) -> List[float]:
    """生成简单电流序列：segments 为 [(duration_s, I_A), ...]。"""

    dt = float(dt_s)
    out: List[float] = []
    for dur_s, i_a in segments:
        n = max(0, int(round(float(dur_s) / dt)))
        out.extend([float(i_a)] * n)
    return out

