"""2RC（双极化）ECM 在“电流控制”下的常参校准工具。

用途（对齐赛题/对齐验证数据）：
- 我们希望用尽量少的参数，捕捉“负载变化后的快速回弹 + 慢速恢复”两种时间尺度；
- 低电流 OCV 数据很难辨识 RC（压降太小），因此这里提供一个更适合“含脉冲/阶跃”的拟合器；
- 与 SOC 相关曲线版本相比，本模块先做 Model-1 的“常参 2RC”以便快速做消融实验：
  看看仅增加一个慢支路，是否就能显著改善休止段恢复形态与 TTE 预测。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from mcm26a.battery import PiecewiseLinearOCV
from mcm26a.battery.model1_ecm2rc import simulate_ecm2rc_current_control
from mcm26a.utils import PiecewiseLinearCurve


@dataclass(frozen=True)
class ECM2RCConstFitResult:
    r0_ohm: float
    r1_ohm: float
    c1_F: float
    r2_ohm: float
    c2_F: float
    rmse_V: float
    mae_V: float
    n: int


def _constant_curve(v: float) -> PiecewiseLinearCurve:
    return PiecewiseLinearCurve(points=((0.0, float(v)), (1.0, float(v))))


def fit_2rc_const_given_r0(
    *,
    soc0: float,
    v1_0_V: float,
    v2_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    r0_ohm: float,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask: np.ndarray,
    weights: np.ndarray | None = None,
    # 物理约束：用时间常数范围抑制“不可辨识导致的退化/吸收偏置”。
    # 经验上：
    # - 快支路 tau1：秒级（~0.5~200s）
    # - 慢支路 tau2：分钟级（~200~20000s）
    # 这能有效避免优化器把 tau2 拟合到数十小时、用 v2 吸收 OCV/SOC 标尺误差的退化解。
    tau1_bounds_s: tuple[float, float] = (0.5, 200.0),
    tau2_bounds_s: tuple[float, float] = (200.0, 20000.0),
    r1_bounds_ohm: tuple[float, float] = (1e-4, 2.0),
    r2_bounds_ohm: tuple[float, float] = (1e-4, 2.0),
    x0: np.ndarray | None = None,
) -> ECM2RCConstFitResult:
    """固定 R0 时拟合常参 2RC：R1/C1 + R2/C2。

参数化（对数域，推荐）：
- x = [log(R1), log(tau1), log(R2), log(tau2)]
  其中 tau=R*C，因此 C=tau/R。

这样做的原因：
- 直接拟合 (R, C) 时，(R 很大, C 很大) 会把 tau 拉到极端大值（数小时甚至数十小时），
  优化器容易让 v2 吸收本该由 OCV/SOC 解释的慢趋势，导致“快支路消失/不可辨识”。我们在实践中确实遇到过。
- 把 tau 作为一等公民，并给 tau 设合理范围，可以显著提升 2RC 的可辨识性与可解释性。

拟合建议：
- mask 应覆盖“负载阶跃后的休止段”（恢复）与“负载段”（压降），否则 2RC 仍可能不可辨识。
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if float(capacity_Ah) <= 0:
        raise ValueError("capacity_Ah must be positive")
    if float(r0_ohm) <= 0:
        raise ValueError("r0_ohm must be positive")
    if int(mask.sum()) <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    if x0 is None:
        # 初值：秒级 + 分钟级两条支路（量级参考文献与工程经验）
        # - R1=10mΩ, tau1=20s
        # - R2=20mΩ, tau2=600s
        x0 = np.log([0.010, 20.0, 0.020, 600.0])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != 4:
        raise ValueError("x0 长度必须为 4")

    # 边界（对数域）：用 tau 范围约束时间尺度，避免退化解。
    r1_lo, r1_hi = (float(r1_bounds_ohm[0]), float(r1_bounds_ohm[1]))
    r2_lo, r2_hi = (float(r2_bounds_ohm[0]), float(r2_bounds_ohm[1]))
    tau1_lo, tau1_hi = (float(tau1_bounds_s[0]), float(tau1_bounds_s[1]))
    tau2_lo, tau2_hi = (float(tau2_bounds_s[0]), float(tau2_bounds_s[1]))
    if not (0 < r1_lo < r1_hi and 0 < r2_lo < r2_hi and 0 < tau1_lo < tau1_hi and 0 < tau2_lo < tau2_hi):
        raise ValueError("r/tau 的 bounds 必须为正且满足 (lo < hi)")
    lb = np.log([r1_lo, tau1_lo, r2_lo, tau2_lo])
    ub = np.log([r1_hi, tau1_hi, r2_hi, tau2_hi])
    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[float, float, float, float]:
        """把参数向量转成 (r1,c1,r2,c2)。"""

        r1 = float(np.exp(x[0]))
        tau1 = float(np.exp(x[1]))
        r2 = float(np.exp(x[2]))
        tau2 = float(np.exp(x[3]))

        # C = tau / R
        c1 = float(tau1 / max(1e-18, r1))
        c2 = float(tau2 / max(1e-18, r2))
        return r1, c1, r2, c2

    def _residuals(x: np.ndarray) -> np.ndarray:
        r1, c1, r2, c2 = _unpack(x)
        _, _, _, v_pred = simulate_ecm2rc_current_control(
            soc0=float(soc0),
            v1_0_V=float(v1_0_V),
            v2_0_V=float(v2_0_V),
            capacity_Ah=float(capacity_Ah),
            ocv=ocv,
            r0_ohm=float(r0_ohm),
            r0_curve=None,
            c1_F=float(c1),
            c2_F=float(c2),
            r1_curve=_constant_curve(float(r1)),
            r2_curve=_constant_curve(float(r2)),
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))
    r1, c1, r2, c2 = _unpack(res.x)
    # 统一命名：v1=快支路，v2=慢支路（若优化器反过来了，则交换以便可视化更直观）
    tau1 = float(r1) * float(c1)
    tau2 = float(r2) * float(c2)
    if tau1 > tau2:
        r1, c1, r2, c2 = float(r2), float(c2), float(r1), float(c1)
    return ECM2RCConstFitResult(
        r0_ohm=float(r0_ohm),
        r1_ohm=float(r1),
        c1_F=float(c1),
        r2_ohm=float(r2),
        c2_F=float(c2),
        rmse_V=float(rmse),
        mae_V=float(mae),
        n=int(mask.sum()),
    )
