"""Model-1 电池模型：等效电路 ECM（OCV-SOC + R0 + 一阶极化支路 R1||C1）。"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ocv import PiecewiseLinearOCV
from mcm26a.utils import PiecewiseLinearCurve


@dataclass(frozen=True)
class BatteryParams1ECM:
    """Model-1（ECM）电池参数。"""

    capacity_Ah: float
    soc_min: float
    v_cut_V: float
    r0_ohm: float  # 默认常数（若提供 r0_curve 则由曲线覆盖）
    r1_ohm: float  # 默认常数（若提供 r1_curve 则由曲线覆盖）
    c1_F: float
    ocv: PiecewiseLinearOCV
    r0_curve: PiecewiseLinearCurve | None = None
    r1_curve: PiecewiseLinearCurve | None = None
    # 放电倍率-容量效应（rate-capacity effect）：
    # 用一个简单线性模型近似“高电流放电可用容量下降”的现象。
    # - 当 I>0（放电）时：SOC 积分加速系数 = 1 + k*I
    # - 当 I<=0（充电）时：保持 1（不改充电库仑效率）
    rate_capacity_k_per_A: float = 0.0
    # OCV 迟滞（charge/discharge hysteresis）的极简近似：
    # - 放电（I>+thresh）：OCV_eff = OCV - hyst_V
    # - 充电（I<-thresh）：OCV_eff = OCV + hyst_V
    # - 小电流：不施加迟滞项
    ocv_hysteresis_V: float = 0.0
    ocv_hysteresis_i_thresh_A: float = 0.2

    # OCV 迟滞（推荐：状态迟滞）
    # 用状态 h(t)∈[-1,1] 表示“路径记忆”，在充/放电时向 sign(I) 收敛，在休止段保持。
    # 端电压使用：V = OCV(SOC) - I*R0 - v1 - M(SOC)*h
    # - M 越大，充/放电平台差异越明显；可用于解释深放电后休止平台偏低等现象。
    # - gamma 控制 h 的收敛速度（随 |I|/Q 缩放），越大越“更快记住当前方向”。
    hyst_M_V: float = 0.0
    hyst_gamma: float = 0.0
    hyst_i_thresh_A: float = 0.05
    hyst_M_curve: PiecewiseLinearCurve | None = None
    # 迟滞/慢恢复状态在休止段的“回归”时间常数（秒）：
    # - 0 表示不启用（保持旧行为：休止段不改变 h）
    # - >0 表示在 |I|<hyst_i_thresh_A 时，h 以 exp(-dt/tau) 向 0 衰减
    hyst_relax_tau_s: float = 0.0

    def r0_ohm_at(self, soc: float) -> float:
        """在给定 SOC 下的 R0（支持 SOC 相关）。"""

        if self.r0_curve is not None:
            return float(self.r0_curve.value(soc))
        return float(self.r0_ohm)

    def r1_ohm_at(self, soc: float) -> float:
        """在给定 SOC 下的 R1（支持 SOC 相关）。"""

        if self.r1_curve is not None:
            return float(self.r1_curve.value(soc))
        return float(self.r1_ohm)

    @staticmethod
    def from_json(path: str | Path) -> "BatteryParams1ECM":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        batt = obj.get("battery", obj)
        ecm = batt.get("ecm", {})

        cap_ah = float(batt["capacity_mAh"]) / 1000.0
        soc_min = float(batt.get("soc_min", 0.0))
        v_cut = float(ecm.get("V_cut_V", 3.3))

        r0 = float(ecm.get("R0_ohm", 0.08))
        r1 = float(ecm.get("R1_ohm", 0.02))
        c1 = float(ecm.get("C1_F", 2000.0))
        k_rate = float(ecm.get("rate_capacity_k_per_A", 0.0))
        hyst_V = float(ecm.get("ocv_hysteresis_V", 0.0))
        hyst_i = float(ecm.get("ocv_hysteresis_i_thresh_A", 0.2))
        # 状态迟滞（新）
        hyst_M_V = float(ecm.get("hyst_M_V", 0.0))
        hyst_gamma = float(ecm.get("hyst_gamma", 0.0))
        hyst_i2 = float(ecm.get("hyst_i_thresh_A", 0.05))
        hyst_relax_tau_s = float(ecm.get("hyst_relax_tau_s", 0.0))

        ocv_cfg = ecm.get("ocv_curve", {})
        ocv = PiecewiseLinearOCV.from_config(ocv_cfg)

        r0_curve = None
        r1_curve = None
        if isinstance(ecm.get("R0_curve", None), dict):
            r0_curve = PiecewiseLinearCurve.from_config(ecm["R0_curve"])
        if isinstance(ecm.get("R1_curve", None), dict):
            r1_curve = PiecewiseLinearCurve.from_config(ecm["R1_curve"])
        hyst_M_curve = None
        if isinstance(ecm.get("hyst_M_curve", None), dict):
            hyst_M_curve = PiecewiseLinearCurve.from_config(ecm["hyst_M_curve"])

        if cap_ah <= 0:
            raise ValueError("capacity_Ah must be positive")
        if r0 <= 0:
            raise ValueError("R0 must be positive")
        if r1 <= 0 or c1 <= 0:
            raise ValueError("R1 and C1 must be positive")
        if v_cut <= 0:
            raise ValueError("V_cut_V must be positive")

        return BatteryParams1ECM(
            capacity_Ah=cap_ah,
            soc_min=soc_min,
            v_cut_V=v_cut,
            r0_ohm=r0,
            r1_ohm=r1,
            c1_F=c1,
            ocv=ocv,
            r0_curve=r0_curve,
            r1_curve=r1_curve,
            rate_capacity_k_per_A=k_rate,
            ocv_hysteresis_V=hyst_V,
            ocv_hysteresis_i_thresh_A=hyst_i,
            hyst_M_V=hyst_M_V,
            hyst_gamma=hyst_gamma,
            hyst_i_thresh_A=hyst_i2,
            hyst_M_curve=hyst_M_curve,
            hyst_relax_tau_s=hyst_relax_tau_s,
        )


@dataclass(frozen=True)
class ECMState:
    """ECM 状态：SOC + 极化支路电压 v1。"""

    soc: float
    v1_V: float


@dataclass(frozen=True)
class ECMOutput:
    """给定功率需求时，ECM 的瞬时电学量。"""

    I_A: float
    V_term_V: float
    OCV_V: float
    discriminant: float
    p_max_W: float
    discriminant_ok: bool


def solve_ecm_instantaneous(
    state: ECMState,
    *,
    p_W: float,
    params: BatteryParams1ECM,
) -> ECMOutput:
    """在给定功率需求 p_W 下求解电流 I 与端电压 V。

    采用功率闭合：P = V*I，且 V = OCV(SOC) - I*R0 - v1
    => R0 I^2 - (OCV - v1) I + P = 0
    """

    p = max(0.0, float(p_W))
    ocv = float(params.ocv.ocv_v(state.soc))
    v1 = float(state.v1_V)
    r0 = float(params.r0_ohm_at(state.soc))

    v_eq = ocv - v1  # 等效开路端电压（合并极化项）
    p_max = (v_eq * v_eq) / (4.0 * r0) if r0 > 0 else 0.0

    # P=0 时直接返回 0 电流（避免数值误差）
    if p <= 0.0:
        v_term = v_eq
        disc0 = v_eq * v_eq
        return ECMOutput(I_A=0.0, V_term_V=v_term, OCV_V=ocv, discriminant=disc0, p_max_W=p_max, discriminant_ok=True)

    a = r0
    b = -(ocv - v1)
    c = p

    disc = b * b - 4.0 * a * c  # (OCV - v1)^2 - 4 R0 P
    if disc < 0.0:
        # 需求功率过大：在该 SOC 与参数下无法满足
        return ECMOutput(
            I_A=float("nan"),
            V_term_V=float("nan"),
            OCV_V=ocv,
            discriminant=float(disc),
            p_max_W=p_max,
            discriminant_ok=False,
        )

    sqrt_disc = math.sqrt(disc)
    # 选取满足 P->0 时 I->0 的根
    i = ((ocv - v1) - sqrt_disc) / (2.0 * r0)
    i = max(0.0, i)
    v_term = ocv - i * r0 - v1
    return ECMOutput(
        I_A=i,
        V_term_V=v_term,
        OCV_V=ocv,
        discriminant=float(disc),
        p_max_W=p_max,
        discriminant_ok=True,
    )


def ecm_derivatives(state: ECMState, *, p_W: float, params: BatteryParams1ECM) -> tuple[float, float, ECMOutput]:
    """返回 (dSOC/dt, dv1/dt, ecm_output)。"""

    out = solve_ecm_instantaneous(state, p_W=p_W, params=params)
    if not out.discriminant_ok:
        return 0.0, 0.0, out

    # dSOC/dt = - I / Q_eff
    # Q_eff 用一个简化的“倍率-容量”模型：放电越大，可用容量越小（SOC 积分更快）。
    q_coulomb = float(params.capacity_Ah) * 3600.0
    k = float(params.rate_capacity_k_per_A)
    mult = 1.0 + k * float(out.I_A) if (k > 0 and out.I_A > 0) else 1.0
    d_soc = -(out.I_A / q_coulomb) * float(mult)

    # dv1/dt = -v1/(R1*C1) + I/C1
    tau = float(params.r1_ohm_at(state.soc)) * float(params.c1_F)
    dv1 = -(state.v1_V / tau) + (out.I_A / float(params.c1_F))
    return d_soc, dv1, out
