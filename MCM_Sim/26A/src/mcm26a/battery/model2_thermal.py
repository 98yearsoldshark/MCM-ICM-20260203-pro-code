"""Model-2 电池模型：ECM + 热模型（温度影响内阻/有效容量），并输出电池温度轨迹。

设计原则：
- 仍保持“功耗需求（外生）”与“电池电-热动力学（内生）”解耦；
- 先用简单的集总热模型（单温度节点）跑通机理链路：
  高功耗 -> 发热 -> 温度变化 -> 内阻/容量变化 -> 端电压/续航变化；
- 参数全部为名义值/占位符，后续可用真实数据进行校准。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ocv import PiecewiseLinearOCV
from mcm26a.utils import PiecewiseLinearCurve


@dataclass(frozen=True)
class BatteryParams2Thermal:
    """Model-2（热-电耦合 ECM）电池参数。

    说明：
    - 仍采用 Thevenin 1RC：OCV(SOC) + R0 + (R1||C1)；
    - 新增集总热模型：dT/dt = (Q_gen - (T - T_amb)/R_th) / C_th；
    - 温度会影响：
      - R0, R1：低温增大（压降更大，续航更差），高温减小（但安全性更差，论文可讨论）；
      - Q_eff：低温有效容量下降（同样电流更快耗尽）。
    """

    # 参考/名义电学参数（T_ref 下）
    capacity_Ah_ref: float
    soc_min: float
    v_cut_V: float
    r0_ohm_ref: float
    r1_ohm_ref: float
    c1_F: float
    ocv: PiecewiseLinearOCV

    # 热参数
    t_ref_C: float
    t0_C: float
    c_th_J_per_K: float
    r_th_K_per_W: float

    # 把外部用电功率 P_total 视为“整机热源”的比例（≈1 表示几乎都变成热）
    eta_device_heat: float

    # 温度对参数的线性系数（每降低 1°C 的相对变化）
    r0_temp_coeff_per_C: float
    r1_temp_coeff_per_C: float
    capacity_temp_coeff_per_C: float

    # 数值稳定：把温度钳制到合理范围，避免外推导致参数负值
    temp_min_C: float
    temp_max_C: float

    # 可选：SOC 相关内阻曲线（若提供则覆盖 *_ohm_ref）
    r0_curve_ref: PiecewiseLinearCurve | None = None
    r1_curve_ref: PiecewiseLinearCurve | None = None

    @staticmethod
    def from_json(path: str | Path) -> "BatteryParams2Thermal":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        batt = obj.get("battery", obj)
        ecm = batt.get("ecm", {})
        th = batt.get("thermal", {})

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

        if cap_ah <= 0:
            raise ValueError("capacity_Ah_ref must be positive")
        if r0 <= 0 or r1 <= 0 or c1 <= 0:
            raise ValueError("ECM params must be positive")
        if v_cut <= 0:
            raise ValueError("V_cut_V must be positive")
        if c_th <= 0 or r_th <= 0:
            raise ValueError("thermal params must be positive")
        if not (0.0 <= eta <= 1.5):
            raise ValueError("eta_device_heat should be within a reasonable range")
        if tmin >= tmax:
            raise ValueError("min_temp_C must be < max_temp_C")

        return BatteryParams2Thermal(
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
        )

    def clamp_temp_C(self, temp_C: float) -> float:
        return min(float(self.temp_max_C), max(float(self.temp_min_C), float(temp_C)))

    def base_r0_ohm(self, soc: float) -> float:
        return float(self.r0_curve_ref.value(soc)) if self.r0_curve_ref is not None else float(self.r0_ohm_ref)

    def base_r1_ohm(self, soc: float) -> float:
        return float(self.r1_curve_ref.value(soc)) if self.r1_curve_ref is not None else float(self.r1_ohm_ref)

    def effective_r0_ohm(self, *, soc: float, temp_C: float) -> float:
        """低温 -> R0 增大；高温 -> R0 减小（线性近似+下限钳制）。"""

        t = self.clamp_temp_C(temp_C)
        scale = 1.0 + float(self.r0_temp_coeff_per_C) * (float(self.t_ref_C) - t)
        scale = max(0.2, float(scale))
        return self.base_r0_ohm(soc) * scale

    def effective_r1_ohm(self, *, soc: float, temp_C: float) -> float:
        t = self.clamp_temp_C(temp_C)
        scale = 1.0 + float(self.r1_temp_coeff_per_C) * (float(self.t_ref_C) - t)
        scale = max(0.2, float(scale))
        return self.base_r1_ohm(soc) * scale

    def effective_capacity_Ah(self, temp_C: float) -> float:
        """低温 -> 有效容量下降；高温暂不奖励（避免过度乐观）。"""

        t = self.clamp_temp_C(temp_C)
        cold = max(0.0, float(self.t_ref_C) - t)
        scale = 1.0 - float(self.capacity_temp_coeff_per_C) * cold
        scale = max(0.5, float(scale))  # 极端低温下也别让容量塌陷到 0
        return float(self.capacity_Ah_ref) * scale


@dataclass(frozen=True)
class ThermalECMState:
    """Model-2 状态：SOC + 极化电压 v1 + 温度。"""

    soc: float
    v1_V: float
    temp_C: float


@dataclass(frozen=True)
class ThermalECMOutput:
    """给定功率需求时的瞬时电-热量。"""

    I_A: float
    V_term_V: float
    OCV_V: float
    r0_ohm: float
    r1_ohm: float
    capacity_Ah: float
    q_gen_W: float
    discriminant_ok: bool


def solve_thermal_ecm_instantaneous(
    state: ThermalECMState,
    *,
    p_W: float,
    params: BatteryParams2Thermal,
) -> ThermalECMOutput:
    """在给定功率需求 p_W 下求解电流 I 与端电压 V（温度影响 R0/R1/Q）。"""

    p = max(0.0, float(p_W))
    ocv = float(params.ocv.ocv_v(state.soc))
    v1 = float(state.v1_V)
    r0 = float(params.effective_r0_ohm(soc=state.soc, temp_C=state.temp_C))
    r1 = float(params.effective_r1_ohm(soc=state.soc, temp_C=state.temp_C))
    cap = float(params.effective_capacity_Ah(state.temp_C))

    if p <= 0.0:
        v_term = ocv - v1
        return ThermalECMOutput(
            I_A=0.0,
            V_term_V=v_term,
            OCV_V=ocv,
            r0_ohm=r0,
            r1_ohm=r1,
            capacity_Ah=cap,
            q_gen_W=0.0,
            discriminant_ok=True,
        )

    # 功率闭合：P = V*I,  V = OCV - I*R0 - v1
    # => R0 I^2 - (OCV - v1) I + P = 0
    a = r0
    b = -(ocv - v1)
    c = p
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return ThermalECMOutput(
            I_A=float("nan"),
            V_term_V=float("nan"),
            OCV_V=ocv,
            r0_ohm=r0,
            r1_ohm=r1,
            capacity_Ah=cap,
            q_gen_W=float("nan"),
            discriminant_ok=False,
        )

    sqrt_disc = math.sqrt(disc)
    i = ((ocv - v1) - sqrt_disc) / (2.0 * r0)
    i = max(0.0, float(i))
    v_term = ocv - i * r0 - v1

    # 发热：外部功耗（整机）+ 电池内部损耗（R0 与 R1）
    q_device = float(params.eta_device_heat) * p
    q_r0 = i * i * r0
    q_r1 = 0.0 if r1 <= 0 else (v1 * v1 / r1)
    q_gen = q_device + q_r0 + q_r1

    return ThermalECMOutput(
        I_A=i,
        V_term_V=v_term,
        OCV_V=ocv,
        r0_ohm=r0,
        r1_ohm=r1,
        capacity_Ah=cap,
        q_gen_W=q_gen,
        discriminant_ok=True,
    )


def thermal_ecm_derivatives(
    state: ThermalECMState,
    *,
    p_W: float,
    ambient_temp_C: float,
    params: BatteryParams2Thermal,
) -> tuple[float, float, float, ThermalECMOutput]:
    """返回 (dSOC/dt, dv1/dt, dT/dt, output)。"""

    out = solve_thermal_ecm_instantaneous(state, p_W=p_W, params=params)
    if not out.discriminant_ok:
        return 0.0, 0.0, 0.0, out

    # dSOC/dt = -I / Q, 其中 Q = capacity_Ah * 3600 (Coulomb)
    q_coulomb = float(out.capacity_Ah) * 3600.0
    d_soc = 0.0 if q_coulomb <= 0 else (-out.I_A / q_coulomb)

    # dv1/dt = -v1/(R1*C1) + I/C1
    tau = float(out.r1_ohm) * float(params.c1_F)
    dv1 = 0.0 if tau <= 0 else (-(state.v1_V / tau) + (out.I_A / float(params.c1_F)))

    # dT/dt = (Q_gen - (T - T_amb)/R_th) / C_th
    t = float(params.clamp_temp_C(state.temp_C))
    t_amb = float(ambient_temp_C)
    q_loss = (t - t_amb) / float(params.r_th_K_per_W)
    d_temp = (float(out.q_gen_W) - q_loss) / float(params.c_th_J_per_K)

    return float(d_soc), float(dv1), float(d_temp), out
