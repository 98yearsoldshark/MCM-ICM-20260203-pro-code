"""Model-3 电池模型：热-电耦合 ECM + 老化（容量衰减 + 内阻增长）。

定位：
- Model-1：ECM（OCV-SOC + R0 + 1RC），解释“高功率下压降导致提前关机”；
- Model-2：加入集总热模型，解释“高负载温升/低温续航下降”；
- Model-3：在 Model-2 基础上加入“老化状态”，解释“越用越不耐电/内阻变大导致更早 cutoff”。

注意：
- 本实现是“可校准的机理骨架”，默认参数为名义值，用于打通流程；
- 后续拿到真实数据后，可以把老化参数（per-Ah/per-day、温度加速系数、SOC 因子等）做系统校准。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ocv import PiecewiseLinearOCV
from mcm26a.utils import PiecewiseLinearCurve


def _q10_factor(temp_C: float, *, t_ref_C: float, q10: float) -> float:
    """Q10 温度加速模型：每升高 10°C，速率乘以 q10。"""

    return float(q10) ** ((float(temp_C) - float(t_ref_C)) / 10.0)


@dataclass(frozen=True)
class BatteryParams3Aging:
    """Model-3（ECM + 热 + 老化）参数。"""

    # 参考/名义电学参数（T_ref 下）
    capacity_Ah_ref: float
    soc_min: float
    v_cut_V: float
    r0_ohm_ref: float
    r1_ohm_ref: float
    c1_F: float
    ocv: PiecewiseLinearOCV

    # 热参数（同 Model-2）
    t_ref_C: float
    t0_C: float
    c_th_J_per_K: float
    r_th_K_per_W: float
    eta_device_heat: float

    # 温度对“瞬时电学参数”的影响（同 Model-2）
    r0_temp_coeff_per_C: float
    r1_temp_coeff_per_C: float
    capacity_temp_coeff_per_C: float
    temp_min_C: float
    temp_max_C: float

    # 老化：cycle aging（随电量吞吐量 |I| 积分）
    cap_fade_per_Ah: float
    r0_growth_per_Ah: float
    r1_growth_per_Ah: float
    aging_q10_cycle: float

    # 老化：calendar aging（随时间，在高温/高 SOC 下更快）
    cap_fade_per_day: float
    r0_growth_per_day: float
    aging_q10_calendar: float
    soc_calendar_k: float
    soc_calendar_ref: float

    # 上下限，避免数值外推导致参数非物理
    cap_loss_max_frac: float
    r_growth_max_frac: float

    # 可选：SOC 相关内阻曲线（若提供则覆盖 *_ohm_ref）
    r0_curve_ref: PiecewiseLinearCurve | None = None
    r1_curve_ref: PiecewiseLinearCurve | None = None

    @staticmethod
    def from_json(path: str | Path) -> "BatteryParams3Aging":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        batt = obj.get("battery", obj)
        ecm = batt.get("ecm", {})
        th = batt.get("thermal", {})
        ag = batt.get("aging", {})

        cap_ah = float(batt["capacity_mAh"]) / 1000.0
        soc_min = float(batt.get("soc_min", 0.0))
        v_cut = float(ecm.get("V_cut_V", 3.3))

        r0 = float(ecm.get("R0_ohm", 0.08))
        r1 = float(ecm.get("R1_ohm", 0.02))
        c1 = float(ecm.get("C1_F", 2000.0))

        ocv_cfg = ecm.get("ocv_curve", {})
        ocv = PiecewiseLinearOCV.from_config(ocv_cfg)

        r0_curve = None
        r1_curve = None
        if isinstance(ecm.get("R0_curve", None), dict):
            r0_curve = PiecewiseLinearCurve.from_config(ecm["R0_curve"])
        if isinstance(ecm.get("R1_curve", None), dict):
            r1_curve = PiecewiseLinearCurve.from_config(ecm["R1_curve"])

        t_ref = float(th.get("T_ref_C", 25.0))
        t0 = float(th.get("T0_C", t_ref))
        c_th = float(th.get("C_th_J_per_K", 250.0))
        r_th = float(th.get("R_th_K_per_W", 2.5))
        eta = float(th.get("eta_device_heat", 0.95))

        r0_k = float(th.get("r0_temp_coeff_per_C", 0.015))
        r1_k = float(th.get("r1_temp_coeff_per_C", 0.015))
        q_k = float(th.get("capacity_temp_coeff_per_C", 0.002))
        tmin = float(th.get("min_temp_C", -10.0))
        tmax = float(th.get("max_temp_C", 70.0))

        cap_per_ah = float(ag.get("cap_fade_per_Ah", 0.0))
        r0_per_ah = float(ag.get("r0_growth_per_Ah", 0.0))
        r1_per_ah = float(ag.get("r1_growth_per_Ah", 0.0))
        q10_cycle = float(ag.get("aging_q10_cycle", 2.0))

        cap_per_day = float(ag.get("cap_fade_per_day", 0.0))
        r0_per_day = float(ag.get("r0_growth_per_day", 0.0))
        q10_cal = float(ag.get("aging_q10_calendar", 2.0))
        soc_k = float(ag.get("soc_calendar_k", 0.0))
        soc_ref = float(ag.get("soc_calendar_ref", 0.5))

        cap_loss_max = float(ag.get("cap_loss_max_frac", 0.5))
        r_growth_max = float(ag.get("r_growth_max_frac", 2.0))

        if cap_ah <= 0:
            raise ValueError("capacity_Ah_ref must be positive")
        if r0 <= 0 or r1 <= 0 or c1 <= 0:
            raise ValueError("ECM params must be positive")
        if v_cut <= 0:
            raise ValueError("V_cut_V must be positive")
        if c_th <= 0 or r_th <= 0:
            raise ValueError("thermal params must be positive")
        if tmin >= tmax:
            raise ValueError("min_temp_C must be < max_temp_C")
        if q10_cycle <= 0 or q10_cal <= 0:
            raise ValueError("Q10 must be positive")
        if not (0.0 <= cap_loss_max <= 0.95):
            raise ValueError("cap_loss_max_frac out of range")
        if r_growth_max < 0.0:
            raise ValueError("r_growth_max_frac must be >= 0")

        return BatteryParams3Aging(
            capacity_Ah_ref=cap_ah,
            soc_min=soc_min,
            v_cut_V=v_cut,
            r0_ohm_ref=r0,
            r1_ohm_ref=r1,
            c1_F=c1,
            ocv=ocv,
            r0_curve_ref=r0_curve,
            r1_curve_ref=r1_curve,
            t_ref_C=t_ref,
            t0_C=t0,
            c_th_J_per_K=c_th,
            r_th_K_per_W=r_th,
            eta_device_heat=eta,
            r0_temp_coeff_per_C=r0_k,
            r1_temp_coeff_per_C=r1_k,
            capacity_temp_coeff_per_C=q_k,
            temp_min_C=tmin,
            temp_max_C=tmax,
            cap_fade_per_Ah=cap_per_ah,
            r0_growth_per_Ah=r0_per_ah,
            r1_growth_per_Ah=r1_per_ah,
            aging_q10_cycle=q10_cycle,
            cap_fade_per_day=cap_per_day,
            r0_growth_per_day=r0_per_day,
            aging_q10_calendar=q10_cal,
            soc_calendar_k=soc_k,
            soc_calendar_ref=soc_ref,
            cap_loss_max_frac=cap_loss_max,
            r_growth_max_frac=r_growth_max,
        )

    def clamp_temp_C(self, temp_C: float) -> float:
        return min(float(self.temp_max_C), max(float(self.temp_min_C), float(temp_C)))

    def _temp_scale_r(self, temp_C: float, *, coeff_per_C: float) -> float:
        t = self.clamp_temp_C(temp_C)
        scale = 1.0 + float(coeff_per_C) * (float(self.t_ref_C) - t)
        return max(0.2, float(scale))

    def _temp_scale_capacity(self, temp_C: float) -> float:
        t = self.clamp_temp_C(temp_C)
        cold = max(0.0, float(self.t_ref_C) - t)
        scale = 1.0 - float(self.capacity_temp_coeff_per_C) * cold
        return max(0.5, float(scale))

    def base_r0_ohm(self, soc: float) -> float:
        return float(self.r0_curve_ref.value(soc)) if self.r0_curve_ref is not None else float(self.r0_ohm_ref)

    def base_r1_ohm(self, soc: float) -> float:
        return float(self.r1_curve_ref.value(soc)) if self.r1_curve_ref is not None else float(self.r1_ohm_ref)

    def effective_r0_ohm(self, *, soc: float, temp_C: float, r0_growth_frac: float) -> float:
        return self.base_r0_ohm(soc) * (1.0 + float(r0_growth_frac)) * self._temp_scale_r(
            temp_C, coeff_per_C=self.r0_temp_coeff_per_C
        )

    def effective_r1_ohm(self, *, soc: float, temp_C: float, r1_growth_frac: float) -> float:
        return self.base_r1_ohm(soc) * (1.0 + float(r1_growth_frac)) * self._temp_scale_r(
            temp_C, coeff_per_C=self.r1_temp_coeff_per_C
        )

    def effective_capacity_Ah(self, *, temp_C: float, cap_loss_frac: float) -> float:
        soh = max(0.0, 1.0 - float(cap_loss_frac))
        return float(self.capacity_Ah_ref) * soh * self._temp_scale_capacity(temp_C)

    def calendar_soc_factor(self, soc: float) -> float:
        """高 SOC 加速（线性）：factor = 1 + k * max(0, soc - soc_ref)。"""

        return 1.0 + float(self.soc_calendar_k) * max(0.0, float(soc) - float(self.soc_calendar_ref))


@dataclass(frozen=True)
class AgingECMState:
    """Model-3 状态：SOC + 极化电压 v1 + 温度 + 老化状态（容量衰减/内阻增长）。"""

    soc: float
    v1_V: float
    temp_C: float
    cap_loss_frac: float
    r0_growth_frac: float
    r1_growth_frac: float


@dataclass(frozen=True)
class AgingECMOutput:
    """给定功率需求时的瞬时电-热-老化量。"""

    I_A: float
    V_term_V: float
    OCV_V: float
    capacity_Ah: float
    r0_ohm: float
    r1_ohm: float
    q_gen_W: float
    discriminant_ok: bool


def solve_aging_ecm_instantaneous(
    state: AgingECMState,
    *,
    p_W: float,
    params: BatteryParams3Aging,
) -> AgingECMOutput:
    """在给定功率需求 p_W 下求解电流 I 与端电压 V（同时考虑温度与老化影响）。"""

    p = max(0.0, float(p_W))
    ocv = float(params.ocv.ocv_v(state.soc))
    v1 = float(state.v1_V)
    r0 = float(params.effective_r0_ohm(soc=state.soc, temp_C=state.temp_C, r0_growth_frac=state.r0_growth_frac))
    r1 = float(params.effective_r1_ohm(soc=state.soc, temp_C=state.temp_C, r1_growth_frac=state.r1_growth_frac))
    cap = float(params.effective_capacity_Ah(temp_C=state.temp_C, cap_loss_frac=state.cap_loss_frac))

    if p <= 0.0:
        v_term = ocv - v1
        return AgingECMOutput(
            I_A=0.0,
            V_term_V=v_term,
            OCV_V=ocv,
            capacity_Ah=cap,
            r0_ohm=r0,
            r1_ohm=r1,
            q_gen_W=0.0,
            discriminant_ok=True,
        )

    # 功率闭合：P = V*I,  V = OCV - I*R0 - v1
    # => R0 I^2 - (OCV - v1) I + P = 0
    disc = (ocv - v1) ** 2 - 4.0 * r0 * p
    if disc < 0.0:
        return AgingECMOutput(
            I_A=float("nan"),
            V_term_V=float("nan"),
            OCV_V=ocv,
            capacity_Ah=cap,
            r0_ohm=r0,
            r1_ohm=r1,
            q_gen_W=float("nan"),
            discriminant_ok=False,
        )

    i = ((ocv - v1) - math.sqrt(disc)) / (2.0 * r0)
    i = max(0.0, float(i))
    v_term = ocv - i * r0 - v1

    # 发热：整机外部功耗 + 电池内部损耗（R0 与 R1）
    q_device = float(params.eta_device_heat) * p
    q_r0 = i * i * r0
    q_r1 = 0.0 if r1 <= 0 else (v1 * v1 / r1)
    q_gen = q_device + q_r0 + q_r1

    return AgingECMOutput(
        I_A=i,
        V_term_V=v_term,
        OCV_V=ocv,
        capacity_Ah=cap,
        r0_ohm=r0,
        r1_ohm=r1,
        q_gen_W=q_gen,
        discriminant_ok=True,
    )


def aging_ecm_derivatives(
    state: AgingECMState,
    *,
    p_W: float,
    ambient_temp_C: float,
    params: BatteryParams3Aging,
) -> tuple[float, float, float, float, float, float, AgingECMOutput]:
    """返回 (dSOC/dt, dv1/dt, dT/dt, dcap_loss/dt, dr0_grow/dt, dr1_grow/dt, output)。"""

    out = solve_aging_ecm_instantaneous(state, p_W=p_W, params=params)
    if not out.discriminant_ok:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, out

    # SOC 动力学
    q_coulomb = float(out.capacity_Ah) * 3600.0
    d_soc = 0.0 if q_coulomb <= 0 else (-out.I_A / q_coulomb)

    # 极化支路
    tau = float(out.r1_ohm) * float(params.c1_F)
    dv1 = 0.0 if tau <= 0 else (-(state.v1_V / tau) + (out.I_A / float(params.c1_F)))

    # 热模型
    t = float(params.clamp_temp_C(state.temp_C))
    t_amb = float(ambient_temp_C)
    q_loss = (t - t_amb) / float(params.r_th_K_per_W)
    d_temp = (float(out.q_gen_W) - q_loss) / float(params.c_th_J_per_K)

    # 老化速率：cycle aging（按 Ah 吞吐量）
    ah_rate = abs(float(out.I_A)) / 3600.0  # Ah/s
    f_cycle_T = _q10_factor(t, t_ref_C=params.t_ref_C, q10=params.aging_q10_cycle)
    d_cap_cycle = float(params.cap_fade_per_Ah) * ah_rate * f_cycle_T
    d_r0_cycle = float(params.r0_growth_per_Ah) * ah_rate * f_cycle_T
    d_r1_cycle = float(params.r1_growth_per_Ah) * ah_rate * f_cycle_T

    # 老化速率：calendar aging（按天）
    sec_per_day = 86400.0
    f_cal_T = _q10_factor(t, t_ref_C=params.t_ref_C, q10=params.aging_q10_calendar)
    f_soc = float(params.calendar_soc_factor(state.soc))
    d_cap_cal = float(params.cap_fade_per_day) / sec_per_day * f_cal_T * f_soc
    d_r0_cal = float(params.r0_growth_per_day) / sec_per_day * f_cal_T * f_soc

    d_cap = d_cap_cycle + d_cap_cal
    d_r0 = d_r0_cycle + d_r0_cal
    d_r1 = d_r1_cycle  # 先不加 calendar aging，保持最简

    # 若已到上限，停止继续增长（避免发散）
    if state.cap_loss_frac >= float(params.cap_loss_max_frac):
        d_cap = 0.0
    if state.r0_growth_frac >= float(params.r_growth_max_frac):
        d_r0 = 0.0
    if state.r1_growth_frac >= float(params.r_growth_max_frac):
        d_r1 = 0.0

    return float(d_soc), float(dv1), float(d_temp), float(d_cap), float(d_r0), float(d_r1), out
