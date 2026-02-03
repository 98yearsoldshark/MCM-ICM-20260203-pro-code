"""2RC（双极化）ECM 在“电流控制”下的 SOC 相关校准工具。

动机（来自 no3 的可用技术点 + 我们当前验证需求）：
- 1RC 往往只能用一个时间常数解释“恢复效应”；当数据同时包含“秒级回弹 + 分钟级恢复”时会吃力；
- 2RC（Thevenin 二阶）可以用两条 RC 支路拆分不同时间尺度；
- 但如果把 2RC 参数设为常数，往往无法同时解释高 SOC 与低 SOC（阻抗随 SOC 强烈变化）；
  因此这里实现“R1(SOC) + R2(SOC) 单调分段线性”的版本，并保持 C1/C2 为常数以控制维度。

说明：
- 该模块只处理“给定 I(t) 时，预测 V(t)”的校准；不涉及手机功耗模型；
- 单调约束：SOC 越低，R 越大（用正增量参数化实现），提升稳定性并减轻过拟合。
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
class ECM2RCSOCDepFitResult:
    """2RC（固定 R0）+ SOC 相关 R1/R2 的拟合结果。"""

    r0_ohm: float
    c1_F: float
    c2_F: float
    r1_curve: PiecewiseLinearCurve
    r2_curve: PiecewiseLinearCurve
    rmse_V: float
    mae_V: float
    n: int


@dataclass(frozen=True)
class ECM2RCSOCDepTauFitResult:
    """2RC（固定 R0）+ SOC 相关 R1/R2，且用“参考时间常数”约束可辨识性。

该版本的核心差异：
- 不直接在优化变量里用 (C1,C2)，而是用 (tau1_ref, tau2_ref) 作为主变量；
- 令 C1=tau1_ref/R1(SOC=1)，C2=tau2_ref/R2(SOC=1)，从而：
  - 在满电端控制时间尺度（避免退化到“超长 tau 吸收 OCV 偏差”）
  - 同时允许在低 SOC 端由于 R 上升导致 tau 变大（解释低电压段更明显的“曲度/慢恢复”）。
"""

    r0_ohm: float
    tau1_ref_s: float
    tau2_ref_s: float
    c1_F: float
    c2_F: float
    r1_curve: PiecewiseLinearCurve
    r2_curve: PiecewiseLinearCurve
    rmse_V: float
    mae_V: float
    n: int


@dataclass(frozen=True)
class ECM2RCSOCDepTauR0CurveFitResult:
    """2RC（R0(SOC)+R1(SOC)+R2(SOC)）+ (tau1_ref,tau2_ref) 的拟合结果。

动机：
- 仅用常数 R0 往往无法解释“低 SOC 下的超深尖峰”（瞬时压降明显变大）；
- 让 R0 随 SOC 单调上升（低 SOC 更大）可以在不污染休止段的前提下，
  改善放电脉冲/深放电端的“瞬时跳变”拟合。

为了控制维度，这里把 R0(SOC) 约束成“线性两点曲线”：
- R0@SOC=1 为 r0_1
- R0@SOC=0 为 r0_0
- 中间线性插值（单调：r0_0 >= r0_1）
"""

    r0_curve: PiecewiseLinearCurve
    r0_ohm_at1: float
    r0_ohm_at0: float
    tau1_ref_s: float
    tau2_ref_s: float
    c1_F: float
    c2_F: float
    r1_curve: PiecewiseLinearCurve
    r2_curve: PiecewiseLinearCurve
    rmse_V: float
    mae_V: float
    n: int


def _build_monotone_increasing_curve(
    *,
    soc_knots_desc: tuple[float, ...],
    y_at_soc1: float,
    increments: np.ndarray,
) -> PiecewiseLinearCurve:
    """把 (SOC 由高到低的结点) + 正增量，组装成“SOC 越低 y 越大”的曲线。"""

    if len(soc_knots_desc) < 2:
        raise ValueError("soc_knots_desc 至少需要 2 个结点")
    if abs(float(soc_knots_desc[0]) - 1.0) > 1e-12:
        raise ValueError("soc_knots_desc[0] 必须为 1.0（从满电端开始）")
    if any(soc_knots_desc[i] < soc_knots_desc[i + 1] for i in range(len(soc_knots_desc) - 1)):
        raise ValueError("soc_knots_desc 必须按 SOC 从高到低排序，例如 (1.0, 0.2, 0.0)")
    if len(increments) != len(soc_knots_desc) - 1:
        raise ValueError("increments 长度应为 len(soc_knots_desc)-1")

    vals_desc = [float(y_at_soc1)]
    cur = float(y_at_soc1)
    for inc in increments:
        cur = cur + float(inc)
        vals_desc.append(cur)

    pts = [(float(s), float(v)) for s, v in zip(soc_knots_desc, vals_desc)]
    # PiecewiseLinearCurve 需要按 x 升序
    pts.sort(key=lambda kv: kv[0])
    return PiecewiseLinearCurve(points=tuple(pts))


def fit_c1_c2_and_r1_r2_curves_given_r0(
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
    soc_knots_desc: tuple[float, ...] = (1.0, 0.2, 0.1, 0.05, 0.0),
    x0: np.ndarray | None = None,
) -> ECM2RCSOCDepFitResult:
    """在固定 R0 的前提下拟合：C1/C2（常数）+ R1(SOC)/R2(SOC)（单调分段线性）。

参数向量（对数/正增量参数化）：
- x: [ log(R1@1), log(ΔR1_1..ΔR1_n),
       log(R2@1), log(ΔR2_1..ΔR2_n),
       log(C1),  log(C2/C1) ]  (最后一项 >=0 保证 C2>=C1)
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")
    if float(r0_ohm) <= 0:
        raise ValueError("r0_ohm must be positive")
    if float(capacity_Ah) <= 0:
        raise ValueError("capacity_Ah must be positive")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    dim = 2 + 2 * n_inc + 2  # r1_1 + dr1... + r2_1 + dr2... + c1 + (c2/c1)

    if x0 is None:
        # 初值（沿用当前 1RC 的量级作为参考）：
        # - R1@1 与 R2@1 均设为 ~1mΩ 量级
        # - 低 SOC 增量先给 0.5Ω（对数域），“让模型能长出大阻抗”，再由数据收缩/分配
        # - C1 取 ~500F；C2 取 C1*10（慢支路）
        x_r1_1 = math.log(0.001)
        x_dr1 = np.log(np.full(n_inc, 0.5, dtype=float))
        x_r2_1 = math.log(0.001)
        x_dr2 = np.log(np.full(n_inc, 0.5, dtype=float))
        x_c1 = math.log(500.0)
        x_c2_ratio = math.log(10.0)
        x0 = np.concatenate([[x_r1_1], x_dr1, [x_r2_1], x_dr2, [x_c1, x_c2_ratio]])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != dim:
        raise ValueError(f"x0 长度应为 {dim}")

    # 边界（对数域）
    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)

    # R1@1, R2@1：允许更小的 mΩ 量级，同时给足上界以覆盖低 SOC 极端
    lb[0], ub[0] = math.log(1e-4), math.log(2.0)
    idx_r2_1 = 1 + n_inc
    lb[idx_r2_1], ub[idx_r2_1] = math.log(1e-4), math.log(2.0)

    # ΔR1, ΔR2（正增量）
    for j in range(1, 1 + n_inc):
        lb[j], ub[j] = math.log(1e-6), math.log(50.0)
    for j in range(idx_r2_1 + 1, idx_r2_1 + 1 + n_inc):
        lb[j], ub[j] = math.log(1e-6), math.log(50.0)

    # C1
    idx_c1 = 1 + n_inc + 1 + n_inc
    lb[idx_c1], ub[idx_c1] = math.log(1.0), math.log(1e6)
    # log(C2/C1) >= 0 保证 C2 >= C1；上界给到 e^6≈403 倍
    lb[idx_c1 + 1], ub[idx_c1 + 1] = 0.0, 6.0

    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[PiecewiseLinearCurve, PiecewiseLinearCurve, float, float]:
        x = np.asarray(x, dtype=float)
        r1_1 = float(np.exp(x[0]))
        dr1 = np.exp(x[1 : 1 + n_inc])
        r2_1 = float(np.exp(x[idx_r2_1]))
        dr2 = np.exp(x[idx_r2_1 + 1 : idx_r2_1 + 1 + n_inc])

        c1 = float(np.exp(x[idx_c1]))
        c2 = float(np.exp(x[idx_c1] + x[idx_c1 + 1]))

        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=dr1)
        r2_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r2_1, increments=dr2)
        return r1_curve, r2_curve, c1, c2

    def _residuals(x: np.ndarray) -> np.ndarray:
        r1_curve, r2_curve, c1, c2 = _unpack(x)
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
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))

    r1_curve, r2_curve, c1, c2 = _unpack(res.x)
    return ECM2RCSOCDepFitResult(
        r0_ohm=float(r0_ohm),
        c1_F=float(c1),
        c2_F=float(c2),
        r1_curve=r1_curve,
        r2_curve=r2_curve,
        rmse_V=rmse,
        mae_V=mae,
        n=int(mask.sum()),
    )


def fit_r1_r2_curves_and_taus_given_r0(
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
    soc_knots_desc: tuple[float, ...] = (1.0, 0.2, 0.1, 0.05, 0.0),
    # 参考时间常数（在 SOC=1.0 处）的物理范围约束
    tau1_bounds_s: tuple[float, float] = (0.5, 30.0),
    tau2_bounds_s: tuple[float, float] = (30.0, 20000.0),
    # 阻值范围（用于抑制数值退化；上界可按数据再调）
    r_bounds_ohm: tuple[float, float] = (1e-4, 5.0),
    dr_bounds_ohm: tuple[float, float] = (1e-6, 5.0),
    x0: np.ndarray | None = None,
) -> ECM2RCSOCDepTauFitResult:
    """固定 R0 时拟合：R1(SOC)/R2(SOC) + (tau1_ref,tau2_ref)。

为什么需要这个版本？
- 直接拟合 (R,C) 或 (C1,C2 + R 曲线) 时，容易出现“不可辨识退化解”：
  优化器把 tau2 拉到非常大，用慢支路去吸收本应由 OCV/SOC 标尺解释的慢趋势，
  结果导致 v1（快支路）在分解图里几乎看不到，且外推到验证集会变差。
- 本函数把“时间尺度”作为一等公民，并用 tau_ref 的物理范围把解空间收敛到更可解释区域。
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")
    if float(r0_ohm) <= 0:
        raise ValueError("r0_ohm must be positive")
    if float(capacity_Ah) <= 0:
        raise ValueError("capacity_Ah must be positive")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    dim = 2 + 2 * n_inc + 2  # r1_1 + dr1... + r2_1 + dr2... + tau1 + tau2

    if x0 is None:
        # 初值（面向“手机小电池 + 1A 放电/恢复”量级）：
        # - R1@1: 20mΩ，低 SOC 逐步增加
        # - R2@1: 30mΩ，低 SOC 增加更明显
        # - tau1_ref: ~5s（用于解释“几秒内的快速回弹”）
        # - tau2_ref: ~1000s（分钟级恢复）
        x_r1_1 = math.log(0.020)
        x_dr1 = np.log(np.full(n_inc, 0.05, dtype=float))
        x_r2_1 = math.log(0.030)
        x_dr2 = np.log(np.full(n_inc, 0.10, dtype=float))
        x_tau1 = math.log(5.0)
        x_tau2 = math.log(1200.0)
        x0 = np.concatenate([[x_r1_1], x_dr1, [x_r2_1], x_dr2, [x_tau1, x_tau2]])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != dim:
        raise ValueError(f"x0 长度应为 {dim}")

    r_lo, r_hi = float(r_bounds_ohm[0]), float(r_bounds_ohm[1])
    dr_lo, dr_hi = float(dr_bounds_ohm[0]), float(dr_bounds_ohm[1])
    tau1_lo, tau1_hi = float(tau1_bounds_s[0]), float(tau1_bounds_s[1])
    tau2_lo, tau2_hi = float(tau2_bounds_s[0]), float(tau2_bounds_s[1])
    if not (0 < r_lo < r_hi and 0 < dr_lo < dr_hi and 0 < tau1_lo < tau1_hi and 0 < tau2_lo < tau2_hi):
        raise ValueError("bounds 必须为正且满足 (lo < hi)")

    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)

    # R1@1, R2@1
    lb[0], ub[0] = math.log(r_lo), math.log(r_hi)
    idx_r2_1 = 1 + n_inc
    lb[idx_r2_1], ub[idx_r2_1] = math.log(r_lo), math.log(r_hi)

    # ΔR1, ΔR2
    for j in range(1, 1 + n_inc):
        lb[j], ub[j] = math.log(dr_lo), math.log(dr_hi)
    for j in range(idx_r2_1 + 1, idx_r2_1 + 1 + n_inc):
        lb[j], ub[j] = math.log(dr_lo), math.log(dr_hi)

    # tau1, tau2
    idx_tau1 = 1 + n_inc + 1 + n_inc
    lb[idx_tau1], ub[idx_tau1] = math.log(tau1_lo), math.log(tau1_hi)
    lb[idx_tau1 + 1], ub[idx_tau1 + 1] = math.log(tau2_lo), math.log(tau2_hi)

    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[PiecewiseLinearCurve, PiecewiseLinearCurve, float, float, float, float]:
        x = np.asarray(x, dtype=float)

        r1_1 = float(np.exp(x[0]))
        dr1 = np.exp(x[1 : 1 + n_inc])
        r2_1 = float(np.exp(x[idx_r2_1]))
        dr2 = np.exp(x[idx_r2_1 + 1 : idx_r2_1 + 1 + n_inc])

        tau1_ref = float(np.exp(x[idx_tau1]))
        tau2_ref = float(np.exp(x[idx_tau1 + 1]))

        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=dr1)
        r2_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r2_1, increments=dr2)

        # 由“参考时间常数”反推 C（保持 C 为常数；tau 会随 R(SOC) 改变）
        c1 = float(tau1_ref / max(1e-18, r1_1))
        c2 = float(tau2_ref / max(1e-18, r2_1))
        return r1_curve, r2_curve, c1, c2, tau1_ref, tau2_ref

    def _residuals(x: np.ndarray) -> np.ndarray:
        r1_curve, r2_curve, c1, c2, _, _ = _unpack(x)
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
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = np.asarray(v_pred, dtype=float) - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))

    r1_curve, r2_curve, c1, c2, tau1_ref, tau2_ref = _unpack(res.x)

    # 统一命名：v1=快支路，v2=慢支路（若时间尺度颠倒，则交换）
    tau1_at1 = float(r1_curve.value(1.0)) * float(c1)
    tau2_at1 = float(r2_curve.value(1.0)) * float(c2)
    if tau1_at1 > tau2_at1:
        r1_curve, r2_curve = r2_curve, r1_curve
        c1, c2 = float(c2), float(c1)
        tau1_ref, tau2_ref = float(tau2_ref), float(tau1_ref)

    return ECM2RCSOCDepTauFitResult(
        r0_ohm=float(r0_ohm),
        tau1_ref_s=float(tau1_ref),
        tau2_ref_s=float(tau2_ref),
        c1_F=float(c1),
        c2_F=float(c2),
        r1_curve=r1_curve,
        r2_curve=r2_curve,
        rmse_V=float(rmse),
        mae_V=float(mae),
        n=int(mask.sum()),
    )


def fit_r0_curve_and_r1_r2_curves_and_taus(
    *,
    soc0: float,
    v1_0_V: float,
    v2_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask: np.ndarray,
    weights: np.ndarray | None = None,
    soc_knots_desc: tuple[float, ...] = (1.0, 0.2, 0.1, 0.05, 0.0),
    # R0(SOC) 的线性端点范围
    r0_1_bounds_ohm: tuple[float, float] = (1e-4, 2.0),
    dr0_bounds_ohm: tuple[float, float] = (1e-6, 3.0),
    # 参考时间常数（在 SOC=1.0 处）
    tau1_bounds_s: tuple[float, float] = (0.5, 60.0),
    tau2_bounds_s: tuple[float, float] = (30.0, 20000.0),
    # R1/R2 范围（抑制退化解；上界可按数据再调）
    r_bounds_ohm: tuple[float, float] = (1e-4, 5.0),
    dr_bounds_ohm: tuple[float, float] = (1e-6, 5.0),
    x0: np.ndarray | None = None,
) -> ECM2RCSOCDepTauR0CurveFitResult:
    """拟合：R0(SOC)（线性两点）+ R1(SOC)/R2(SOC)（单调分段线性）+ (tau1_ref,tau2_ref)。

关键点：
- 把 R0 的低 SOC 上升单独交给“欧姆项”（只在 I!=0 时起作用），避免用慢支路去吸收尖峰；
- 仍用 tau_ref 约束时间尺度，降低不可辨识退化风险。
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")
    if float(capacity_Ah) <= 0:
        raise ValueError("capacity_Ah must be positive")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    dim = 2 + 2 + 2 * n_inc + 2  # r0_1 + dr0 + r1_1 + dr1.. + r2_1 + dr2.. + tau1 + tau2

    if x0 is None:
        # 初值：R0≈150mΩ，低 SOC 上升到 ≈350mΩ；R1/R2 为几十毫欧并在低 SOC 上升。
        x_r0_1 = math.log(0.15)
        x_dr0 = math.log(0.20)
        x_r1_1 = math.log(0.020)
        x_dr1 = np.log(np.full(n_inc, 0.05, dtype=float))
        x_r2_1 = math.log(0.030)
        x_dr2 = np.log(np.full(n_inc, 0.10, dtype=float))
        x_tau1 = math.log(5.0)
        x_tau2 = math.log(1200.0)
        x0 = np.concatenate([[x_r0_1, x_dr0, x_r1_1], x_dr1, [x_r2_1], x_dr2, [x_tau1, x_tau2]])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != dim:
        raise ValueError(f"x0 长度应为 {dim}")

    r0_1_lo, r0_1_hi = float(r0_1_bounds_ohm[0]), float(r0_1_bounds_ohm[1])
    dr0_lo, dr0_hi = float(dr0_bounds_ohm[0]), float(dr0_bounds_ohm[1])
    r_lo, r_hi = float(r_bounds_ohm[0]), float(r_bounds_ohm[1])
    dr_lo, dr_hi = float(dr_bounds_ohm[0]), float(dr_bounds_ohm[1])
    tau1_lo, tau1_hi = float(tau1_bounds_s[0]), float(tau1_bounds_s[1])
    tau2_lo, tau2_hi = float(tau2_bounds_s[0]), float(tau2_bounds_s[1])
    if not (0 < r0_1_lo < r0_1_hi and 0 < dr0_lo < dr0_hi):
        raise ValueError("r0 bounds 必须为正且满足 (lo < hi)")
    if not (0 < r_lo < r_hi and 0 < dr_lo < dr_hi and 0 < tau1_lo < tau1_hi and 0 < tau2_lo < tau2_hi):
        raise ValueError("bounds 必须为正且满足 (lo < hi)")

    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)

    # R0@1 与 ΔR0
    lb[0], ub[0] = math.log(r0_1_lo), math.log(r0_1_hi)
    lb[1], ub[1] = math.log(dr0_lo), math.log(dr0_hi)

    # R1@1
    lb[2], ub[2] = math.log(r_lo), math.log(r_hi)
    # ΔR1
    for j in range(3, 3 + n_inc):
        lb[j], ub[j] = math.log(dr_lo), math.log(dr_hi)

    # R2@1
    idx_r2_1 = 3 + n_inc
    lb[idx_r2_1], ub[idx_r2_1] = math.log(r_lo), math.log(r_hi)
    # ΔR2
    for j in range(idx_r2_1 + 1, idx_r2_1 + 1 + n_inc):
        lb[j], ub[j] = math.log(dr_lo), math.log(dr_hi)

    # tau1, tau2
    idx_tau1 = idx_r2_1 + 1 + n_inc
    lb[idx_tau1], ub[idx_tau1] = math.log(tau1_lo), math.log(tau1_hi)
    lb[idx_tau1 + 1], ub[idx_tau1 + 1] = math.log(tau2_lo), math.log(tau2_hi)

    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(
        x: np.ndarray,
    ) -> tuple[PiecewiseLinearCurve, float, float, PiecewiseLinearCurve, PiecewiseLinearCurve, float, float, float, float]:
        x = np.asarray(x, dtype=float)

        r0_1 = float(np.exp(x[0]))
        dr0 = float(np.exp(x[1]))
        r0_0 = float(r0_1 + dr0)
        r0_curve = PiecewiseLinearCurve(points=((0.0, r0_0), (1.0, r0_1)))

        r1_1 = float(np.exp(x[2]))
        dr1 = np.exp(x[3 : 3 + n_inc])

        r2_1 = float(np.exp(x[idx_r2_1]))
        dr2 = np.exp(x[idx_r2_1 + 1 : idx_r2_1 + 1 + n_inc])

        tau1_ref = float(np.exp(x[idx_tau1]))
        tau2_ref = float(np.exp(x[idx_tau1 + 1]))

        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=dr1)
        r2_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r2_1, increments=dr2)

        c1 = float(tau1_ref / max(1e-18, r1_1))
        c2 = float(tau2_ref / max(1e-18, r2_1))
        return r0_curve, r0_1, r0_0, r1_curve, r2_curve, c1, c2, tau1_ref, tau2_ref

    def _residuals(x: np.ndarray) -> np.ndarray:
        r0_curve, r0_1, _, r1_curve, r2_curve, c1, c2, _, _ = _unpack(x)
        _, _, _, v_pred = simulate_ecm2rc_current_control(
            soc0=float(soc0),
            v1_0_V=float(v1_0_V),
            v2_0_V=float(v2_0_V),
            capacity_Ah=float(capacity_Ah),
            ocv=ocv,
            r0_ohm=float(r0_1),
            r0_curve=r0_curve,
            c1_F=float(c1),
            c2_F=float(c2),
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = np.asarray(v_pred, dtype=float) - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))

    r0_curve, r0_1, r0_0, r1_curve, r2_curve, c1, c2, tau1_ref, tau2_ref = _unpack(res.x)

    # 统一命名：v1=快支路，v2=慢支路（若时间尺度颠倒，则交换）
    tau1_at1 = float(r1_curve.value(1.0)) * float(c1)
    tau2_at1 = float(r2_curve.value(1.0)) * float(c2)
    if tau1_at1 > tau2_at1:
        r1_curve, r2_curve = r2_curve, r1_curve
        c1, c2 = float(c2), float(c1)
        tau1_ref, tau2_ref = float(tau2_ref), float(tau1_ref)

    return ECM2RCSOCDepTauR0CurveFitResult(
        r0_curve=r0_curve,
        r0_ohm_at1=float(r0_1),
        r0_ohm_at0=float(r0_0),
        tau1_ref_s=float(tau1_ref),
        tau2_ref_s=float(tau2_ref),
        c1_F=float(c1),
        c2_F=float(c2),
        r1_curve=r1_curve,
        r2_curve=r2_curve,
        rmse_V=float(rmse),
        mae_V=float(mae),
        n=int(mask.sum()),
    )
