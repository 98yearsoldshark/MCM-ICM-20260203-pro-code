"""ECM（等效电路）在“电流控制”下的仿真与校准工具。

注意：
- 我们的手机续航仿真（Model-1/2/3）是“功率控制”（P 由场景/功耗模型给定）；
- 但公开电池数据集通常给的是“电流-电压”曲线，因此校准时更自然采用“电流控制”形式。

本模块提供：
- 在给定 I(t) 下快速仿真 ECM（使用极化电压的解析更新，避免数值积分误差）
- 基于最小二乘拟合 R0/R1/tau，并可迭代更新 OCV-SOC 曲线（只用一份数据也能闭环）
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import least_squares

from mcm26a.battery import PiecewiseLinearOCV


@dataclass(frozen=True)
class ECMFitResult:
    """一次拟合结果。"""

    r0_ohm: float
    r1_ohm: float
    c1_F: float
    tau_s: float
    rmse_V: float
    mae_V: float
    n: int


def simulate_ecm_current_control(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    r0_ohm: float,
    r1_ohm: float,
    tau_s: float,
    dt_s: np.ndarray,
    i_A: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """在电流控制下仿真 ECM，返回 (soc, v1_V, v_term_V) 三个数组（长度与 i_A 相同）。

约定：
- 电流 i_A > 0 表示放电；i_A < 0 表示充电；
- dSOC/dt = -i_A / (Q*3600)；
- v1 的解析更新：
  v1(t+dt) = v1*exp(-dt/tau) + i_A*R1*(1-exp(-dt/tau))
"""

    n = int(len(i_A))
    if n <= 0:
        return np.array([]), np.array([]), np.array([])
    if len(dt_s) != n:
        raise ValueError("dt_s 与 i_A 长度不一致")
    if capacity_Ah <= 0:
        raise ValueError("capacity_Ah must be positive")
    if r0_ohm <= 0 or r1_ohm <= 0 or tau_s <= 0:
        raise ValueError("r0/r1/tau must be positive")

    soc = float(soc0)
    v1 = float(v1_0_V)
    q_coulomb = float(capacity_Ah) * 3600.0

    soc_hist = np.zeros(n, dtype=float)
    v1_hist = np.zeros(n, dtype=float)
    v_hist = np.zeros(n, dtype=float)

    for k in range(n):
        i = float(i_A[k])
        dt = float(dt_s[k])

        soc_hist[k] = soc
        v1_hist[k] = v1

        ocv_v = float(ocv.ocv_v(soc))
        v_hist[k] = ocv_v - i * float(r0_ohm) - v1

        # 更新 SOC（欧拉足够；主要误差来自容量/OCV，而非数值积分）
        soc = soc - i * dt / q_coulomb
        soc = min(1.0, max(0.0, float(soc)))

        # 更新 v1（解析解）
        a = math.exp(-dt / float(tau_s)) if dt > 0 else 1.0
        v1 = v1 * a + i * float(r1_ohm) * (1.0 - a)

    return soc_hist, v1_hist, v_hist


def fit_r0_r1_tau(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask: np.ndarray,
    x0_log: np.ndarray,
    bounds_log: tuple[np.ndarray, np.ndarray] | None = None,
) -> ECMFitResult:
    """固定 OCV 曲线与容量，仅拟合 (R0, R1, tau)。

    说明：
    - 这里对参数引入物理边界（bounds），避免在“参数不可辨识”的情况下出现明显不物理的最优解
      （例如 tau->0 使极化瞬间消失，从而把所有动态都吸收到 R0 中）。
    - bounds 作用在 log 参数上：x = (log R0, log R1, log tau)。
    """

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 50:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")

    if bounds_log is None:
        # 缺省物理边界（经验范围，足够宽但能排除明显不合理值）
        # - R0/R1：手机电池等效内阻通常在 mΩ~几百 mΩ 量级；这里放宽到 [1e-4, 1]Ω
        # - tau：极化/扩散时间常数通常为秒到数千秒；这里放宽到 [1, 20000]s
        lb = np.log(np.array([1e-4, 1e-4, 1.0], dtype=float))
        ub = np.log(np.array([1.0, 1.0, 20000.0], dtype=float))
        bounds_log = (lb, ub)

    lb, ub = (np.asarray(bounds_log[0], dtype=float), np.asarray(bounds_log[1], dtype=float))
    if lb.shape != (3,) or ub.shape != (3,):
        raise ValueError("bounds_log 形状应为 (3,), (3,)")
    # 确保初值在边界内（避免 least_squares 直接报错）
    x0 = np.asarray(x0_log, dtype=float)
    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _residuals(xlog: np.ndarray) -> np.ndarray:
        r0 = float(np.exp(xlog[0]))
        r1 = float(np.exp(xlog[1]))
        tau = float(np.exp(xlog[2]))
        _, _, v_pred = simulate_ecm_current_control(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            r0_ohm=r0,
            r1_ohm=r1,
            tau_s=tau,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return r[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))

    r0 = float(np.exp(res.x[0]))
    r1 = float(np.exp(res.x[1]))
    tau = float(np.exp(res.x[2]))
    c1 = tau / r1
    return ECMFitResult(r0_ohm=r0, r1_ohm=r1, c1_F=float(c1), tau_s=tau, rmse_V=rmse, mae_V=mae, n=int(mask.sum()))


def fit_ocv_from_samples(
    soc: np.ndarray,
    ocv_est_V: np.ndarray,
    *,
    n_points: int = 21,
    window: float = 0.02,
) -> PiecewiseLinearOCV:
    """用 (SOC, OCV_est) 样本拟合一条分段线性、单调不减的 OCV 曲线。"""

    soc = np.asarray(soc, dtype=float)
    ocv_est_V = np.asarray(ocv_est_V, dtype=float)
    if len(soc) != len(ocv_est_V):
        raise ValueError("soc 与 ocv_est_V 长度不一致")
    if int(n_points) < 5:
        raise ValueError("n_points 太小，建议 >= 5")

    pts: list[tuple[float, float]] = []
    edges = np.linspace(0.0, 1.0, int(n_points))
    for s in edges:
        lo = max(0.0, float(s) - float(window))
        hi = min(1.0, float(s) + float(window))
        m = (soc >= lo) & (soc <= hi) & np.isfinite(ocv_est_V)
        if not np.any(m):
            continue
        pts.append((float(s), float(np.median(ocv_est_V[m]))))

    if not pts:
        raise ValueError("无法从样本拟合 OCV（无有效点）")

    # 合并重复 SOC + 单调包络
    pts.sort(key=lambda x: x[0])
    merged: list[tuple[float, float]] = []
    for s, v in pts:
        if merged and abs(merged[-1][0] - s) <= 1e-12:
            merged[-1] = (merged[-1][0], max(merged[-1][1], v))
        else:
            merged.append((s, v))

    out: list[tuple[float, float]] = []
    last_v = -1e18
    for s, v in merged:
        v2 = v if v >= last_v else last_v
        out.append((s, v2))
        last_v = v2

    return PiecewiseLinearOCV(points=tuple(out))


def iterative_calibrate_ocv_and_resistance(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv0: PiecewiseLinearOCV,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask_fit: np.ndarray,
    n_ocv_points: int = 21,
    max_iter: int = 3,
    x0_log: np.ndarray | None = None,
    progress: Callable[[int, ECMFitResult], None] | None = None,
) -> tuple[PiecewiseLinearOCV, ECMFitResult]:
    """迭代校准：
    1) 固定 OCV，拟合 R0/R1/tau；
    2) 固定 R0/R1/tau，用 v_meas + I*R0 + v1 反推 OCV，并用分段线性拟合；
    重复若干次直到收敛（通常 2~3 次足够）。
    """

    ocv = ocv0
    xlog = np.asarray(x0_log, dtype=float) if x0_log is not None else np.log(np.array([0.08, 0.02, 40.0]))

    best_fit: ECMFitResult | None = None
    for it in range(1, int(max_iter) + 1):
        fit = fit_r0_r1_tau(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            dt_s=dt_s,
            i_A=i_A,
            v_meas_V=v_meas_V,
            mask=mask_fit,
            x0_log=xlog,
        )
        best_fit = fit
        if progress is not None:
            progress(it, fit)

        # 更新 OCV：用同一组参数把 v1 轨迹跑出来，然后反推 OCV_est
        soc_hist, v1_hist, _ = simulate_ecm_current_control(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            r0_ohm=fit.r0_ohm,
            r1_ohm=fit.r1_ohm,
            tau_s=fit.tau_s,
            dt_s=dt_s,
            i_A=i_A,
        )
        ocv_est = v_meas_V + i_A * float(fit.r0_ohm) + v1_hist
        ocv = fit_ocv_from_samples(soc_hist, ocv_est, n_points=int(n_ocv_points))

        # 下一轮从上次结果出发（提高收敛稳定）
        xlog = np.log(np.array([fit.r0_ohm, fit.r1_ohm, fit.tau_s], dtype=float))

    assert best_fit is not None
    return ocv, best_fit
