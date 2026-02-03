"""Model-1 电池模型（扩展）：二阶 Thevenin ECM（OCV-SOC + R0 + 两个极化支路 R1||C1 与 R2||C2）。

本模块对应赛题对“连续时间机理模型”的要求：
- 状态：SOC(t) + 两个极化电压状态 v1(t), v2(t)
- 输出：端电压 V_term(t)
- 在“恒功率负载”下：由 P=V*I + 电压方程联立得到二次方程，可出现不可行域（判别式 < 0）
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
class BatteryParams1ECM2RC:
    """Model-1（二阶 Thevenin 2RC）电池参数。"""

    capacity_Ah: float
    soc_min: float
    v_cut_V: float

    r0_ohm: float  # 默认常数（若提供 r0_curve 则由曲线覆盖）
    r1_ohm: float  # 默认常数（若提供 r1_curve 则由曲线覆盖）
    c1_F: float
    r2_ohm: float  # 默认常数（若提供 r2_curve 则由曲线覆盖）
    c2_F: float
    ocv: PiecewiseLinearOCV

    r0_curve: PiecewiseLinearCurve | None = None
    r1_curve: PiecewiseLinearCurve | None = None
    r2_curve: PiecewiseLinearCurve | None = None
    # 放电倍率-容量效应（rate-capacity effect），见 model1_ecm.py 的说明。
    rate_capacity_k_per_A: float = 0.0
    # OCV 迟滞（状态迟滞，推荐）：见 model1_ecm.py 的说明。
    hyst_M_V: float = 0.0
    hyst_gamma: float = 0.0
    hyst_i_thresh_A: float = 0.05
    hyst_M_curve: PiecewiseLinearCurve | None = None
    # 迟滞/慢恢复状态在休止段的回归时间常数（秒）；0 表示不启用（保持旧行为）
    hyst_relax_tau_s: float = 0.0
    # 额外的“低 SOC 扩散极化/恢复”状态（z∈[0,1]）：
    # - 设计动机：有些数据在深度放电末端出现远超 2RC 的额外压降，并在休止段呈现小时级缓慢回升。
    # - 与 h(t) 的区别：z 不区分充/放电方向，只表示“非平衡程度/扩散梯度”大小；电压项始终为负：V -= M(SOC)*z。
    # - 为避免对常规工作域造成干扰，推荐用 soc_thresh + i_thresh 做触发门控。
    diff_M_V: float = 0.0
    diff_gamma: float = 0.0
    diff_i_thresh_A: float = 0.5
    diff_soc_thresh: float = 0.1
    # 可选：额外门控——仅当端电压低于阈值时才允许 z 建立（用于把机制限定在“极端深放电”域）
    # - 典型取值：2.8~3.1 V（视数据而定）；0 表示不使用该门控。
    diff_v_thresh_V: float = 0.0
    # 可选：把“触发门控”从硬阈值改为软门控（Sigmoid 平滑），避免在阈值处产生不真实的折线/拐点。
    # - 0 表示仍用硬阈值（保持旧行为）。
    # - 建议量级：SOC 0.005~0.02，电压 0.02~0.10V，电流 0.05~0.20A（视数据采样与噪声而定）。
    diff_gate_soc_sigma: float = 0.0
    diff_gate_v_sigma_V: float = 0.0
    diff_gate_i_sigma_A: float = 0.0
    diff_relax_tau_s: float = 0.0
    # 可选：两阶段恢复（用于更贴近“深放电后几十秒~数分钟快速回弹 + 随后小时级缓慢回升”的形态）
    # - 当 z 较大（>=diff_relax_z_thresh）时，优先使用更快的时间常数 diff_relax_tau_init_s；
    # - 当 z 降到阈值以下后，回到 diff_relax_tau_s（慢恢复）。
    # - 典型取值：diff_relax_tau_init_s ~ 30~120 s，diff_relax_tau_s ~ 1~10 h。
    diff_relax_tau_init_s: float = 0.0
    diff_relax_z_thresh: float = 0.0
    # 可选：三阶段恢复（用于更贴近“秒级快速回弹 + 十秒~几十秒中速回升 + 分钟~小时慢恢复”的形态）
    # - 当 z ∈ [diff_relax_z_thresh_mid, diff_relax_z_thresh) 时，使用 diff_relax_tau_mid_s；
    # - 当 z < diff_relax_z_thresh_mid 时，回到 diff_relax_tau_s（慢恢复）。
    # - 若 diff_relax_tau_mid_s 或 diff_relax_z_thresh_mid 为 0，则保持“两阶段恢复”的旧行为。
    diff_relax_tau_mid_s: float = 0.0
    diff_relax_z_thresh_mid: float = 0.0
    # 可选：分段衰减——当电压回到较高水平时，用更快的时间常数让 z 更快消退（减少对“正常工作域/短休止”的干扰）
    diff_relax_tau_fast_s: float = 0.0
    diff_relax_v_thresh_V: float = 0.0
    diff_M_curve: PiecewiseLinearCurve | None = None
    # 与 z 状态耦合的“额外欧姆项”（单位：Ω；实际压降为 I * diff_R(soc) * z）
    # 作用：
    # - 在大电流、低 SOC 时增大瞬时压降与“关断瞬时跳变”（更贴近某些深放电数据）；
    # - 在休止段 (I≈0) 自动消失，不会把平台整体压得过低（平台偏低由 diff_M_curve 负责）。
    diff_R_ohm: float = 0.0
    diff_R_curve: PiecewiseLinearCurve | None = None

    def r0_ohm_at(self, soc: float) -> float:
        if self.r0_curve is not None:
            return float(self.r0_curve.value(soc))
        return float(self.r0_ohm)

    def r1_ohm_at(self, soc: float) -> float:
        if self.r1_curve is not None:
            return float(self.r1_curve.value(soc))
        return float(self.r1_ohm)

    def r2_ohm_at(self, soc: float) -> float:
        if self.r2_curve is not None:
            return float(self.r2_curve.value(soc))
        return float(self.r2_ohm)

    @staticmethod
    def from_json(path: str | Path) -> "BatteryParams1ECM2RC":
        """从配置 JSON 读取 2RC 参数。

支持字段（与 1RC 兼容扩展）：
- battery.ecm.R0_ohm / R1_ohm / C1_F / R2_ohm / C2_F
- battery.ecm.R0_curve / R1_curve / R2_curve（可选）
"""

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
        r2 = float(ecm.get("R2_ohm", 0.02))
        c2 = float(ecm.get("C2_F", 2000.0))
        k_rate = float(ecm.get("rate_capacity_k_per_A", 0.0))
        hyst_M_V = float(ecm.get("hyst_M_V", 0.0))
        hyst_gamma = float(ecm.get("hyst_gamma", 0.0))
        hyst_i = float(ecm.get("hyst_i_thresh_A", 0.05))
        hyst_relax_tau_s = float(ecm.get("hyst_relax_tau_s", 0.0))
        diff_M_V = float(ecm.get("diff_M_V", 0.0))
        diff_gamma = float(ecm.get("diff_gamma", 0.0))
        diff_i_thresh_A = float(ecm.get("diff_i_thresh_A", 0.5))
        diff_soc_thresh = float(ecm.get("diff_soc_thresh", 0.1))
        diff_v_thresh_V = float(ecm.get("diff_v_thresh_V", 0.0))
        diff_gate_soc_sigma = float(ecm.get("diff_gate_soc_sigma", 0.0))
        diff_gate_v_sigma_V = float(ecm.get("diff_gate_v_sigma_V", 0.0))
        diff_gate_i_sigma_A = float(ecm.get("diff_gate_i_sigma_A", 0.0))
        diff_relax_tau_s = float(ecm.get("diff_relax_tau_s", 0.0))
        diff_relax_tau_init_s = float(ecm.get("diff_relax_tau_init_s", 0.0))
        diff_relax_z_thresh = float(ecm.get("diff_relax_z_thresh", 0.0))
        diff_relax_tau_mid_s = float(ecm.get("diff_relax_tau_mid_s", 0.0))
        diff_relax_z_thresh_mid = float(ecm.get("diff_relax_z_thresh_mid", 0.0))
        diff_relax_tau_fast_s = float(ecm.get("diff_relax_tau_fast_s", 0.0))
        diff_relax_v_thresh_V = float(ecm.get("diff_relax_v_thresh_V", 0.0))
        diff_R_ohm = float(ecm.get("diff_R_ohm", 0.0))

        ocv_cfg = ecm.get("ocv_curve", {})
        ocv = PiecewiseLinearOCV.from_config(ocv_cfg)

        r0_curve = None
        r1_curve = None
        r2_curve = None
        if isinstance(ecm.get("R0_curve", None), dict):
            r0_curve = PiecewiseLinearCurve.from_config(ecm["R0_curve"])
        if isinstance(ecm.get("R1_curve", None), dict):
            r1_curve = PiecewiseLinearCurve.from_config(ecm["R1_curve"])
        if isinstance(ecm.get("R2_curve", None), dict):
            r2_curve = PiecewiseLinearCurve.from_config(ecm["R2_curve"])
        hyst_M_curve = None
        if isinstance(ecm.get("hyst_M_curve", None), dict):
            hyst_M_curve = PiecewiseLinearCurve.from_config(ecm["hyst_M_curve"])
        diff_M_curve = None
        if isinstance(ecm.get("diff_M_curve", None), dict):
            diff_M_curve = PiecewiseLinearCurve.from_config(ecm["diff_M_curve"])
        diff_R_curve = None
        if isinstance(ecm.get("diff_R_curve", None), dict):
            diff_R_curve = PiecewiseLinearCurve.from_config(ecm["diff_R_curve"])

        if cap_ah <= 0:
            raise ValueError("capacity_Ah must be positive")
        if r0 <= 0:
            raise ValueError("R0 must be positive")
        if r1 <= 0 or c1 <= 0:
            raise ValueError("R1 and C1 must be positive")
        if r2 <= 0 or c2 <= 0:
            raise ValueError("R2 and C2 must be positive")
        if v_cut <= 0:
            raise ValueError("V_cut_V must be positive")

        return BatteryParams1ECM2RC(
            capacity_Ah=cap_ah,
            soc_min=soc_min,
            v_cut_V=v_cut,
            r0_ohm=r0,
            r1_ohm=r1,
            c1_F=c1,
            r2_ohm=r2,
            c2_F=c2,
            ocv=ocv,
            r0_curve=r0_curve,
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            rate_capacity_k_per_A=k_rate,
            hyst_M_V=hyst_M_V,
            hyst_gamma=hyst_gamma,
            hyst_i_thresh_A=hyst_i,
            hyst_M_curve=hyst_M_curve,
            hyst_relax_tau_s=hyst_relax_tau_s,
            diff_M_V=diff_M_V,
            diff_gamma=diff_gamma,
            diff_i_thresh_A=diff_i_thresh_A,
            diff_soc_thresh=diff_soc_thresh,
            diff_v_thresh_V=diff_v_thresh_V,
            diff_gate_soc_sigma=diff_gate_soc_sigma,
            diff_gate_v_sigma_V=diff_gate_v_sigma_V,
            diff_gate_i_sigma_A=diff_gate_i_sigma_A,
            diff_relax_tau_s=diff_relax_tau_s,
            diff_relax_tau_init_s=diff_relax_tau_init_s,
            diff_relax_z_thresh=diff_relax_z_thresh,
            diff_relax_tau_mid_s=diff_relax_tau_mid_s,
            diff_relax_z_thresh_mid=diff_relax_z_thresh_mid,
            diff_relax_tau_fast_s=diff_relax_tau_fast_s,
            diff_relax_v_thresh_V=diff_relax_v_thresh_V,
            diff_M_curve=diff_M_curve,
            diff_R_ohm=diff_R_ohm,
            diff_R_curve=diff_R_curve,
        )


@dataclass(frozen=True)
class ECM2RCState:
    """2RC ECM 状态：SOC + 两个极化支路电压 v1/v2。"""

    soc: float
    v1_V: float
    v2_V: float


@dataclass(frozen=True)
class ECM2RCOutput:
    """给定功率需求时，2RC ECM 的瞬时电学量。"""

    I_A: float
    V_term_V: float
    OCV_V: float
    discriminant: float
    p_max_W: float
    discriminant_ok: bool


def solve_ecm2rc_instantaneous(
    state: ECM2RCState,
    *,
    p_W: float,
    params: BatteryParams1ECM2RC,
) -> ECM2RCOutput:
    """在给定功率需求 p_W 下求解电流 I 与端电压 V。

功率闭合：P = V*I，且
V = OCV(SOC) - I*R0 - v1 - v2
=> R0 I^2 - (OCV - v1 - v2) I + P = 0
"""

    p = max(0.0, float(p_W))
    ocv = float(params.ocv.ocv_v(state.soc))
    v1 = float(state.v1_V)
    v2 = float(state.v2_V)
    r0 = float(params.r0_ohm_at(state.soc))

    v_eq = ocv - v1 - v2
    p_max = (v_eq * v_eq) / (4.0 * r0) if r0 > 0 else 0.0

    if p <= 0.0:
        return ECM2RCOutput(I_A=0.0, V_term_V=v_eq, OCV_V=ocv, discriminant=v_eq * v_eq, p_max_W=p_max, discriminant_ok=True)

    disc = v_eq * v_eq - 4.0 * r0 * p
    if disc < 0.0:
        return ECM2RCOutput(
            I_A=float("nan"),
            V_term_V=float("nan"),
            OCV_V=ocv,
            discriminant=float(disc),
            p_max_W=p_max,
            discriminant_ok=False,
        )

    sqrt_disc = math.sqrt(disc)
    # 选取满足 P->0 时 I->0 的根
    i = (v_eq - sqrt_disc) / (2.0 * r0)
    i = max(0.0, float(i))
    v_term = ocv - i * r0 - v1 - v2
    return ECM2RCOutput(I_A=i, V_term_V=float(v_term), OCV_V=ocv, discriminant=float(disc), p_max_W=p_max, discriminant_ok=True)


def ecm2rc_derivatives(
    state: ECM2RCState,
    *,
    p_W: float,
    params: BatteryParams1ECM2RC,
) -> tuple[float, float, float, ECM2RCOutput]:
    """返回 (dSOC/dt, dv1/dt, dv2/dt, ecm_output)。"""

    out = solve_ecm2rc_instantaneous(state, p_W=p_W, params=params)
    if not out.discriminant_ok:
        return 0.0, 0.0, 0.0, out

    q_coulomb = float(params.capacity_Ah) * 3600.0
    k = float(params.rate_capacity_k_per_A)
    mult = 1.0 + k * float(out.I_A) if (k > 0 and out.I_A > 0) else 1.0
    d_soc = -(out.I_A / q_coulomb) * float(mult)

    tau1 = float(params.r1_ohm_at(state.soc)) * float(params.c1_F)
    tau2 = float(params.r2_ohm_at(state.soc)) * float(params.c2_F)
    dv1 = -(state.v1_V / tau1) + (out.I_A / float(params.c1_F))
    dv2 = -(state.v2_V / tau2) + (out.I_A / float(params.c2_F))
    return float(d_soc), float(dv1), float(dv2), out


def simulate_ecm2rc_current_control(
    *,
    soc0: float,
    v1_0_V: float,
    v2_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    r0_ohm: float,
    r0_curve: PiecewiseLinearCurve | None,
    c1_F: float,
    c2_F: float,
    r1_curve: PiecewiseLinearCurve,
    r2_curve: PiecewiseLinearCurve,
    rate_capacity_k_per_A: float = 0.0,
    # 迟滞/慢恢复状态（可选）：用于解释深放电后的“平台偏移 + 缓慢回升”的路径依赖
    hyst_M_V: float = 0.0,
    hyst_gamma: float = 0.0,
    hyst_i_thresh_A: float = 0.05,
    hyst_M_curve: PiecewiseLinearCurve | None = None,
    hyst_relax_tau_s: float = 0.0,
    h0: float = 0.0,
    return_h: bool = False,
    # 低 SOC 扩散极化/慢恢复（z 状态，见 BatteryParams1ECM2RC.diff_* 说明）
    diff_M_V: float = 0.0,
    diff_gamma: float = 0.0,
    diff_i_thresh_A: float = 0.5,
    diff_soc_thresh: float = 0.1,
    diff_v_thresh_V: float = 0.0,
    diff_gate_soc_sigma: float = 0.0,
    diff_gate_v_sigma_V: float = 0.0,
    diff_gate_i_sigma_A: float = 0.0,
    diff_relax_tau_s: float = 0.0,
    diff_relax_tau_init_s: float = 0.0,
    diff_relax_z_thresh: float = 0.0,
    diff_relax_tau_mid_s: float = 0.0,
    diff_relax_z_thresh_mid: float = 0.0,
    diff_relax_tau_fast_s: float = 0.0,
    diff_relax_v_thresh_V: float = 0.0,
    diff_M_curve: PiecewiseLinearCurve | None = None,
    diff_R_ohm: float = 0.0,
    diff_R_curve: PiecewiseLinearCurve | None = None,
    # 可选：用于 z 门控的“外部电压”（例如测量电压）。若为 None，则使用模型当前预测的端电压。
    # 说明：这在“用实测数据做验证/校准”时很有用，可避免“门控需要先触发才会变低”的自洽死锁。
    diff_v_gate_V: Any | None = None,
    z0: float = 0.0,
    return_z: bool = False,
    dt_s: list[float] | tuple[float, ...] | Any,
    i_A: list[float] | tuple[float, ...] | Any,
) -> tuple[Any, Any, Any, Any]:
    """电流控制下仿真：R0 常数 + R1(SOC)/R2(SOC) + C1/C2 常数。

默认返回 (soc, v1, v2, v_term) 四个数组（长度与 i_A 相同）。
若 return_h=True 且 return_z=False，则返回 (soc, v1, v2, h, v_term) 五个数组。
若 return_z=True 且 return_h=False，则返回 (soc, v1, v2, z, v_term) 五个数组。
若 return_h=True 且 return_z=True，则返回 (soc, v1, v2, h, z, v_term) 六个数组。
"""

    import numpy as np

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_gate = None if diff_v_gate_V is None else np.asarray(diff_v_gate_V, dtype=float)
    n = int(len(i_A))
    if n <= 0:
        return np.array([]), np.array([]), np.array([]), np.array([])
    if len(dt_s) != n:
        raise ValueError("dt_s 与 i_A 长度不一致")
    if v_gate is not None and len(v_gate) != n:
        raise ValueError("diff_v_gate_V 与 i_A 长度不一致")
    if capacity_Ah <= 0:
        raise ValueError("capacity_Ah must be positive")
    if r0_ohm <= 0 or c1_F <= 0 or c2_F <= 0:
        raise ValueError("r0_ohm/c1_F/c2_F must be positive")

    soc = float(soc0)
    v1 = float(v1_0_V)
    v2 = float(v2_0_V)
    h = float(h0)
    z = float(z0)
    q_coulomb = float(capacity_Ah) * 3600.0
    k_rate = float(rate_capacity_k_per_A)
    hyst_M0 = float(hyst_M_V)
    hyst_gamma0 = float(hyst_gamma)
    hyst_i = float(hyst_i_thresh_A)
    hyst_relax_tau = float(hyst_relax_tau_s)
    # 允许仅提供 hyst_M_curve（而不额外提供 hyst_M_V），避免配置重复与“静默不生效”。
    hyst_enabled = (hyst_gamma0 > 0.0) and (hyst_M0 > 0.0 or hyst_M_curve is not None)
    # 扩散极化/慢恢复（z 状态）：与 h 独立
    diff_M0 = float(diff_M_V)
    diff_gamma0 = float(diff_gamma)
    diff_i = float(diff_i_thresh_A)
    diff_soc_th = float(diff_soc_thresh)
    diff_v_th = float(diff_v_thresh_V)
    diff_soc_sigma = float(diff_gate_soc_sigma)
    diff_v_sigma = float(diff_gate_v_sigma_V)
    diff_i_sigma = float(diff_gate_i_sigma_A)
    diff_relax_tau = float(diff_relax_tau_s)
    diff_relax_tau_init = float(diff_relax_tau_init_s)
    diff_relax_z_th = float(diff_relax_z_thresh)
    diff_relax_tau_mid = float(diff_relax_tau_mid_s)
    diff_relax_z_th_mid = float(diff_relax_z_thresh_mid)
    diff_relax_tau_fast = float(diff_relax_tau_fast_s)
    diff_relax_v_th = float(diff_relax_v_thresh_V)
    diff_R0 = float(diff_R_ohm)
    diff_enabled = (diff_gamma0 > 0.0) and (diff_relax_tau > 0.0) and (
        (diff_M0 > 0.0 or diff_M_curve is not None) or (diff_R0 > 0.0 or diff_R_curve is not None)
    )

    soc_hist = np.zeros(n, dtype=float)
    v1_hist = np.zeros(n, dtype=float)
    v2_hist = np.zeros(n, dtype=float)
    h_hist = np.zeros(n, dtype=float)
    z_hist = np.zeros(n, dtype=float)
    v_hist = np.zeros(n, dtype=float)

    for k in range(n):
        i = float(i_A[k])
        dt = float(dt_s[k])

        soc_hist[k] = soc
        v1_hist[k] = v1
        v2_hist[k] = v2
        h_hist[k] = h
        z_hist[k] = z

        ocv_v = float(ocv.ocv_v(soc))
        ocv_eff = ocv_v
        if hyst_enabled:
            m = float(hyst_M_curve.value(soc)) if hyst_M_curve is not None else hyst_M0
            ocv_eff = ocv_eff - m * float(h)
        if diff_enabled:
            m2 = float(diff_M_curve.value(soc)) if diff_M_curve is not None else diff_M0
            ocv_eff = ocv_eff - m2 * float(z)
        r0 = float(r0_curve.value(soc)) if r0_curve is not None else float(r0_ohm)
        if diff_enabled:
            # 额外欧姆项：仅在 diff_enabled 时启用；I=0 时不会影响平台。
            r_extra = float(diff_R_curve.value(soc)) if diff_R_curve is not None else float(diff_R0)
            r0 = float(r0) + float(r_extra) * float(z)
        v_hist[k] = ocv_eff - i * r0 - v1 - v2

        # SOC 更新（库仑计数 + 放电倍率-容量效应）
        mult = 1.0 + k_rate * max(0.0, float(i)) if k_rate > 0 else 1.0
        soc = soc - (i * dt / q_coulomb) * float(mult)
        soc = min(1.0, max(0.0, float(soc)))

        # 迟滞/慢恢复状态更新：
        # - 充/放电：向 sign(I) 收敛
        # - 休止：向 0 衰减（可选）
        if hyst_enabled:
            if abs(i) >= hyst_i:
                target = 1.0 if i > 0 else -1.0
                dh = -float(hyst_gamma0) * (abs(i) / q_coulomb) * (float(h) - float(target))
                h = float(h) + float(dh) * float(dt)
                h = min(1.0, max(-1.0, float(h)))
            elif hyst_relax_tau > 0 and dt > 0:
                a_h = math.exp(-dt / float(hyst_relax_tau))
                h = float(h) * float(a_h)

        # 扩散极化/慢恢复状态 z 更新：
        # - 只在“低 SOC + 明显放电电流”时建立（触发门控，避免影响常规工作域）
        # - 休止/充电时缓慢回归到 0（用于生成“曲度/慢回升”）
        if diff_enabled and dt > 0:
            def _sigmoid01(x: float) -> float:
                # 数值稳定：避免 exp 溢出（这里 x 通常量级不大）
                x = max(-60.0, min(60.0, float(x)))
                return 1.0 / (1.0 + math.exp(-x))

            v_for_gate = float(v_gate[k]) if v_gate is not None else float(v_hist[k])
            # 触发门控：支持硬阈值与软门控（Sigmoid 平滑）
            if diff_soc_sigma <= 0.0 and diff_v_sigma <= 0.0 and diff_i_sigma <= 0.0:
                v_gate_ok = True if diff_v_th <= 0.0 else (float(v_for_gate) <= diff_v_th)
                gate = 1.0 if ((i >= diff_i) and (soc_hist[k] <= diff_soc_th) and v_gate_ok) else 0.0
            else:
                gi = 1.0 if diff_i_sigma <= 0.0 else _sigmoid01((float(i) - diff_i) / max(1e-12, float(diff_i_sigma)))
                gs = 1.0 if diff_soc_sigma <= 0.0 else _sigmoid01((diff_soc_th - float(soc_hist[k])) / max(1e-12, float(diff_soc_sigma)))
                if diff_v_th <= 0.0:
                    gv = 1.0
                else:
                    gv = 1.0 if diff_v_sigma <= 0.0 else _sigmoid01((diff_v_th - float(v_for_gate)) / max(1e-12, float(diff_v_sigma)))
                gate = float(gi) * float(gs) * float(gv)
                gate = min(1.0, max(0.0, float(gate)))

            # “建立”与“恢复”同时存在时，用 gate 做加权，实现连续过渡（避免折线）
            if gate > 0.0:
                # 向 1 收敛：z(t+dt)=1-(1-z)*exp(-a dt)，这里把速率缩放为 gate*a
                a = float(diff_gamma0) * (max(0.0, float(i)) / q_coulomb)
                a = max(0.0, float(a))
                z = 1.0 - (1.0 - float(z)) * math.exp(-float(gate) * float(a) * float(dt))

            if gate < 1.0:
                # 两阶段恢复：
                # - z 很大时，先用更快的 tau_init 把“深放电后快速回弹”刻画出来；
                # - z 降到阈值后，再用 tau_slow 让后续“平台期”更稳定（避免被曲度抹掉）。
                tau = float(diff_relax_tau)
                # 三阶段恢复（可选）：在两阶段的基础上补一个“中速回升”时间尺度（十秒~几十秒），用于拟合极深尖峰后的短时恢复形态。
                if diff_relax_tau_mid > 0.0 and diff_relax_z_th_mid > 0.0 and diff_relax_z_th > 0.0:
                    if diff_relax_tau_init > 0.0 and float(z) >= float(diff_relax_z_th):
                        tau = float(diff_relax_tau_init)
                    elif float(z) >= float(diff_relax_z_th_mid):
                        tau = float(diff_relax_tau_mid)
                    else:
                        tau = float(diff_relax_tau)
                else:
                    if diff_relax_tau_init > 0.0 and diff_relax_z_th > 0.0 and float(z) >= float(diff_relax_z_th):
                        tau = min(float(tau), float(diff_relax_tau_init))
                if diff_relax_tau_fast > 0.0 and diff_relax_v_th > 0.0:
                    # “电压回升后快速消退”：用外部电压（若提供）或当前预测端电压做判定
                    if float(v_for_gate) >= float(diff_relax_v_th):
                        tau = min(float(tau), float(diff_relax_tau_fast))
                z = float(z) * math.exp(-(1.0 - float(gate)) * float(dt) / max(1e-12, float(tau)))
            z = min(1.0, max(0.0, float(z)))

        # v1/v2 更新：逐步常系数近似（SOC 取步首）
        r1 = float(r1_curve.value(soc_hist[k]))
        r2 = float(r2_curve.value(soc_hist[k]))
        tau1 = float(r1) * float(c1_F)
        tau2 = float(r2) * float(c2_F)

        a1 = math.exp(-dt / tau1) if (dt > 0 and tau1 > 0) else 1.0
        a2 = math.exp(-dt / tau2) if (dt > 0 and tau2 > 0) else 1.0
        v1 = v1 * a1 + i * float(r1) * (1.0 - a1)
        v2 = v2 * a2 + i * float(r2) * (1.0 - a2)

    if return_h and return_z:
        return soc_hist, v1_hist, v2_hist, h_hist, z_hist, v_hist
    if return_h:
        return soc_hist, v1_hist, v2_hist, h_hist, v_hist
    if return_z:
        return soc_hist, v1_hist, v2_hist, z_hist, v_hist
    return soc_hist, v1_hist, v2_hist, v_hist
