"""SOC 相关 ECM（Model-1 扩展）在“电流控制”下的校准工具。

为什么需要它？
- 只用 1RC 且参数常数时，往往能在高 SOC/高电压区拟合得很好，但在低 SOC 区会出现系统性误差：
  放电末端与随后的长休止段电压回升幅度很大（例如 0.3~0.5V），而高 SOC 区压降却很小。
- 这暗示内阻/极化阻抗随 SOC 强烈变化；因此我们引入 R1(SOC)（可选再扩展到 R0(SOC)）。

本模块先做一个“足够简单但能修正主要误差结构”的版本：
- OCV(SOC) 固定（来自上一阶段的低电流 OCV 拟合）
- R0 为常数（先不增加维度）
- R1 为分段线性曲线 R1(SOC)，并且在实现上保证 R1 随 SOC 下降而不减（单调增加）
- C1 为常数，因此 tau(SOC)=R1(SOC)*C1 会自动在低 SOC 变大（解释长时间松弛）

注意：
- 本模块仍然只需要一条 (t, I, V) 数据即可跑通闭环；但为了避免过拟合，曲线结点数不要太多。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from mcm26a.battery import PiecewiseLinearOCV
from mcm26a.utils import PiecewiseLinearCurve


@dataclass(frozen=True)
class ECMSOCDepFitResult:
    """SOC 相关 ECM 拟合结果（当前版本：R0 常数 + R1(SOC) + C1 常数）。"""

    r0_ohm: float
    c1_F: float
    r1_curve: PiecewiseLinearCurve
    rmse_V: float
    mae_V: float
    n: int


@dataclass(frozen=True)
class ECMSOCDepFitResultR0R1:
    """SOC 相关 ECM 拟合结果：R0(SOC) + R1(SOC) + C1 常数。"""

    r0_curve: PiecewiseLinearCurve
    c1_F: float
    r1_curve: PiecewiseLinearCurve
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


def simulate_ecm_current_control_r1_soc(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    r0_ohm: float,
    c1_F: float,
    r1_curve: PiecewiseLinearCurve,
    rate_capacity_k_per_A: float = 0.0,
    # 迟滞（两种模式）：
    # - “静态迟滞”（旧版）：以常数电压偏置近似充/放电 OCV 差异，仅在 |I|>=阈值时施加。
    # - “状态迟滞”（推荐）：用状态 h(t) 表示路径记忆，解释“平台偏移/深放电后的低平台”等现象。
    ocv_hysteresis_V: float = 0.0,
    ocv_hysteresis_i_thresh_A: float = 0.2,
    hyst_M_V: float = 0.0,
    hyst_gamma: float = 0.0,
    hyst_i_thresh_A: float = 0.05,
    hyst_M_curve: PiecewiseLinearCurve | None = None,
    hyst_relax_tau_s: float = 0.0,
    h0: float = 0.0,
    return_h: bool = False,
    dt_s: np.ndarray,
    i_A: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """电流控制下仿真：R0 常数 + R1(SOC) + C1 常数。

默认返回 (soc, v1, v_term) 三个数组（长度与 i_A 相同）。
若 return_h=True，则返回 (soc, v1, h, v_term) 四个数组。
"""

    n = int(len(i_A))
    if n <= 0:
        return np.array([]), np.array([]), np.array([])
    if len(dt_s) != n:
        raise ValueError("dt_s 与 i_A 长度不一致")
    if capacity_Ah <= 0:
        raise ValueError("capacity_Ah must be positive")
    if r0_ohm <= 0 or c1_F <= 0:
        raise ValueError("r0_ohm/c1_F must be positive")

    soc = float(soc0)
    v1 = float(v1_0_V)
    h = float(h0)
    q_coulomb = float(capacity_Ah) * 3600.0
    k_rate = float(rate_capacity_k_per_A)
    hyst_static = float(ocv_hysteresis_V)
    hyst_static_i = float(ocv_hysteresis_i_thresh_A)
    hyst_M0 = float(hyst_M_V)
    hyst_gamma0 = float(hyst_gamma)
    hyst_i = float(hyst_i_thresh_A)
    hyst_relax_tau = float(hyst_relax_tau_s)
    # 允许仅提供 hyst_M_curve（而不额外提供 hyst_M_V），避免配置重复与“静默不生效”。
    hyst_enabled = (hyst_gamma0 > 0.0) and (hyst_M0 > 0.0 or hyst_M_curve is not None)

    soc_hist = np.zeros(n, dtype=float)
    v1_hist = np.zeros(n, dtype=float)
    h_hist = np.zeros(n, dtype=float)
    v_hist = np.zeros(n, dtype=float)

    for k in range(n):
        i = float(i_A[k])
        dt = float(dt_s[k])

        soc_hist[k] = soc
        v1_hist[k] = v1
        h_hist[k] = h

        ocv_v = float(ocv.ocv_v(soc))

        # 迟滞项：优先使用“状态迟滞”，若未启用则回退到“静态迟滞”（兼容旧配置）。
        ocv_eff = ocv_v
        if hyst_enabled:
            m = float(hyst_M_curve.value(soc)) if hyst_M_curve is not None else hyst_M0
            # 约定：放电 i>0 时希望电压偏低；充电 i<0 时希望电压偏高
            # => V = OCV - M*h，其中 h≈sign(i)，h=+1（放电）给 -M，h=-1（充电）给 +M
            ocv_eff = ocv_eff - m * float(h)
        elif hyst_static > 0 and abs(i) >= hyst_static_i:
            # 静态迟滞：只在明显充/放电时施加，避免在近零电流处给噪声“添油”。
            ocv_eff = ocv_eff + (hyst_static if i < 0 else -hyst_static)

        v_hist[k] = ocv_eff - i * float(r0_ohm) - v1

        # SOC 更新（放电倍率-容量效应：仅对放电 i>0 生效）
        mult = 1.0 + k_rate * max(0.0, float(i)) if k_rate > 0 else 1.0
        soc = soc - (i * dt / q_coulomb) * float(mult)
        soc = min(1.0, max(0.0, float(soc)))

        # 迟滞/慢恢复状态更新（两段式）：
        # - 充/放电：向 sign(I) 收敛
        # - 休止：向 0 衰减（可选；用于解释“深放电后平台缓慢回升”的曲度）
        if hyst_enabled:
            if abs(i) >= hyst_i:
                target = 1.0 if i > 0 else -1.0
                # 一个简单、稳定、可解释的动力学：
                # - 单位“通量”尺度：|I|/Q
                # - gamma 控制收敛速度（gamma 越大，越快贴近 target）
                dh = -float(hyst_gamma0) * (abs(i) / q_coulomb) * (float(h) - float(target))
                h = float(h) + float(dh) * float(dt)
                h = min(1.0, max(-1.0, float(h)))
            elif hyst_relax_tau > 0 and dt > 0:
                # 休止段回归：指数衰减更稳健（避免 dt 大时欧拉不稳定）
                a_h = math.exp(-dt / float(hyst_relax_tau))
                h = float(h) * float(a_h)

        # v1 更新：tau=R1(SOC)*C1（逐步常系数近似）
        r1 = float(r1_curve.value(soc_hist[k]))
        tau = float(r1) * float(c1_F)
        a = math.exp(-dt / tau) if (dt > 0 and tau > 0) else 1.0
        v1 = v1 * a + i * float(r1) * (1.0 - a)

    if return_h:
        # type: ignore[return-value]
        return soc_hist, v1_hist, h_hist, v_hist
    return soc_hist, v1_hist, v_hist


def simulate_ecm_current_control_r0_r1_soc(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    r0_curve: PiecewiseLinearCurve,
    c1_F: float,
    r1_curve: PiecewiseLinearCurve,
    rate_capacity_k_per_A: float = 0.0,
    ocv_hysteresis_V: float = 0.0,
    ocv_hysteresis_i_thresh_A: float = 0.2,
    hyst_M_V: float = 0.0,
    hyst_gamma: float = 0.0,
    hyst_i_thresh_A: float = 0.05,
    hyst_M_curve: PiecewiseLinearCurve | None = None,
    hyst_relax_tau_s: float = 0.0,
    h0: float = 0.0,
    return_h: bool = False,
    dt_s: np.ndarray,
    i_A: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """电流控制下仿真：R0(SOC) + R1(SOC) + C1 常数。"""

    n = int(len(i_A))
    if n <= 0:
        return np.array([]), np.array([]), np.array([])
    if len(dt_s) != n:
        raise ValueError("dt_s 与 i_A 长度不一致")
    if capacity_Ah <= 0:
        raise ValueError("capacity_Ah must be positive")
    if c1_F <= 0:
        raise ValueError("c1_F must be positive")

    soc = float(soc0)
    v1 = float(v1_0_V)
    h = float(h0)
    q_coulomb = float(capacity_Ah) * 3600.0
    k_rate = float(rate_capacity_k_per_A)
    hyst_static = float(ocv_hysteresis_V)
    hyst_static_i = float(ocv_hysteresis_i_thresh_A)
    hyst_M0 = float(hyst_M_V)
    hyst_gamma0 = float(hyst_gamma)
    hyst_i = float(hyst_i_thresh_A)
    hyst_relax_tau = float(hyst_relax_tau_s)
    # 允许仅提供 hyst_M_curve（而不额外提供 hyst_M_V），避免配置重复与“静默不生效”。
    hyst_enabled = (hyst_gamma0 > 0.0) and (hyst_M0 > 0.0 or hyst_M_curve is not None)

    soc_hist = np.zeros(n, dtype=float)
    v1_hist = np.zeros(n, dtype=float)
    h_hist = np.zeros(n, dtype=float)
    v_hist = np.zeros(n, dtype=float)

    for k in range(n):
        i = float(i_A[k])
        dt = float(dt_s[k])

        soc_hist[k] = soc
        v1_hist[k] = v1
        h_hist[k] = h

        ocv_v = float(ocv.ocv_v(soc))
        ocv_eff = ocv_v
        if hyst_enabled:
            m = float(hyst_M_curve.value(soc)) if hyst_M_curve is not None else hyst_M0
            ocv_eff = ocv_eff - m * float(h)
        elif hyst_static > 0 and abs(i) >= hyst_static_i:
            ocv_eff = ocv_eff + (hyst_static if i < 0 else -hyst_static)
        r0 = float(r0_curve.value(soc_hist[k]))
        v_hist[k] = ocv_eff - i * r0 - v1

        # SOC 更新（放电倍率-容量效应：仅对放电 i>0 生效）
        mult = 1.0 + k_rate * max(0.0, float(i)) if k_rate > 0 else 1.0
        soc = soc - (i * dt / q_coulomb) * float(mult)
        soc = min(1.0, max(0.0, float(soc)))

        if hyst_enabled:
            if abs(i) >= hyst_i:
                target = 1.0 if i > 0 else -1.0
                dh = -float(hyst_gamma0) * (abs(i) / q_coulomb) * (float(h) - float(target))
                h = float(h) + float(dh) * float(dt)
                h = min(1.0, max(-1.0, float(h)))
            elif hyst_relax_tau > 0 and dt > 0:
                a_h = math.exp(-dt / float(hyst_relax_tau))
                h = float(h) * float(a_h)

        # v1 更新（逐步常系数近似）
        r1 = float(r1_curve.value(soc_hist[k]))
        tau = float(r1) * float(c1_F)
        a = math.exp(-dt / tau) if (dt > 0 and tau > 0) else 1.0
        v1 = v1 * a + i * float(r1) * (1.0 - a)

    if return_h:
        # type: ignore[return-value]
        return soc_hist, v1_hist, h_hist, v_hist
    return soc_hist, v1_hist, v_hist


def fit_r0_c1_and_r1_curve(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask: np.ndarray,
    weights: np.ndarray | None = None,
    soc_knots_desc: tuple[float, ...] = (1.0, 0.2, 0.1, 0.05, 0.0),
    x0: np.ndarray | None = None,
) -> ECMSOCDepFitResult:
    """拟合参数：R0（常数）、C1（常数）、R1(SOC)（分段线性 + 单调约束）。

参数向量（对数/正增量参数化）：
- x[0] = log(R0)
- x[1] = log(C1)
- x[2] = log(R1@SOC=1.0)
- x[3:] = log(ΔR1_i)  (Δ>0，保证 SOC 越低 R1 越大)
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        # 负权重没有意义，这里直接取绝对值；0 表示不计入目标函数
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    if x0 is None:
        # 初值策略：给一个“高 SOC 小、低 SOC 大”的粗略形状
        # - R0：0.05Ω（量级）
        # - C1：2000F（量级）
        # - R1@1.0：0.02Ω
        # - 增量：把低 SOC 拉到 ~4~5Ω（只是起点，拟合会自行调整）
        inc_guess = np.log(np.full(n_inc, 1.5, dtype=float))
        x0 = np.concatenate([np.log([0.05, 2000.0, 0.02]), inc_guess])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != 3 + n_inc:
        raise ValueError(f"x0 长度应为 {3+n_inc}")

    # 物理边界（对数域）
    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)
    # R0
    lb[0], ub[0] = math.log(0.005), math.log(2.0)
    # C1
    lb[1], ub[1] = math.log(1.0), math.log(1e6)
    # R1@1
    lb[2], ub[2] = math.log(0.001), math.log(2.0)
    # ΔR1
    for j in range(3, len(x0)):
        lb[j], ub[j] = math.log(1e-6), math.log(20.0)

    # 初值裁剪
    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[float, float, PiecewiseLinearCurve]:
        r0 = float(np.exp(x[0]))
        c1 = float(np.exp(x[1]))
        r1_1 = float(np.exp(x[2]))
        inc = np.exp(x[3:])
        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=inc)
        return r0, c1, r1_curve

    def _residuals(x: np.ndarray) -> np.ndarray:
        r0, c1, r1_curve = _unpack(x)
        _, _, v_pred = simulate_ecm_current_control_r1_soc(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            r0_ohm=r0,
            c1_F=c1,
            r1_curve=r1_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))
    r0, c1, r1_curve = _unpack(res.x)
    return ECMSOCDepFitResult(r0_ohm=r0, c1_F=c1, r1_curve=r1_curve, rmse_V=rmse, mae_V=mae, n=int(mask.sum()))


def fit_c1_and_r1_curve_given_r0(
    *,
    soc0: float,
    v1_0_V: float,
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
) -> ECMSOCDepFitResult:
    """在固定 R0 的前提下拟合：C1（常数）+ R1(SOC)（单调分段线性）。

动机：
- 低电流数据中 R0 往往不可辨识，容易被拟合到极小（导致在脉冲数据上压降严重低估）；
- 先用“含电流阶跃/脉冲”的数据估计 R0，再固定 R0，只在低电流数据上拟合松弛项（R1/C1），更稳健。

参数向量（对数/正增量参数化）：
- x[0] = log(C1)
- x[1] = log(R1@SOC=1.0)
- x[2:] = log(ΔR1_i)  (Δ>0，保证 SOC 越低 R1 越大)
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

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    if x0 is None:
        # 初值：C1=2000F，R1@1.0=0.02Ω，低 SOC 增量粗略给 1.0（对数域）
        inc_guess = np.log(np.full(n_inc, 1.0, dtype=float))
        x0 = np.concatenate([np.log([2000.0, 0.02]), inc_guess])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != 2 + n_inc:
        raise ValueError(f"x0 长度应为 {2+n_inc}")

    # 物理边界（对数域）
    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)
    # C1
    lb[0], ub[0] = math.log(1.0), math.log(1e6)
    # R1@1
    lb[1], ub[1] = math.log(0.001), math.log(2.0)
    # ΔR1
    for j in range(2, len(x0)):
        lb[j], ub[j] = math.log(1e-6), math.log(20.0)

    # 初值裁剪
    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[float, PiecewiseLinearCurve]:
        c1 = float(np.exp(x[0]))
        r1_1 = float(np.exp(x[1]))
        inc = np.exp(x[2:])
        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=inc)
        return c1, r1_curve

    def _residuals(x: np.ndarray) -> np.ndarray:
        c1, r1_curve = _unpack(x)
        _, _, v_pred = simulate_ecm_current_control_r1_soc(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            r0_ohm=float(r0_ohm),
            c1_F=c1,
            r1_curve=r1_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))
    c1, r1_curve = _unpack(res.x)
    return ECMSOCDepFitResult(
        r0_ohm=float(r0_ohm),
        c1_F=c1,
        r1_curve=r1_curve,
        rmse_V=rmse,
        mae_V=mae,
        n=int(mask.sum()),
    )


def fit_r0_curve_c1_and_r1_curve(
    *,
    soc0: float,
    v1_0_V: float,
    capacity_Ah: float,
    ocv: PiecewiseLinearOCV,
    dt_s: np.ndarray,
    i_A: np.ndarray,
    v_meas_V: np.ndarray,
    mask: np.ndarray,
    weights: np.ndarray | None = None,
    soc_knots_desc: tuple[float, ...] = (1.0, 0.2, 0.1, 0.05, 0.0),
    x0: np.ndarray | None = None,
) -> ECMSOCDepFitResultR0R1:
    """拟合：R0(SOC) + R1(SOC) + C1（常数）。

参数向量（对数/正增量参数化）：
- R0@SOC=1.0 + 各段 ΔR0_i（Δ>0，保证 SOC 越低 R0 越大）
- log(C1)
- R1@SOC=1.0 + 各段 ΔR1_i（Δ>0，保证 SOC 越低 R1 越大）
"""

    dt_s = np.asarray(dt_s, dtype=float)
    i_A = np.asarray(i_A, dtype=float)
    v_meas_V = np.asarray(v_meas_V, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if not (len(dt_s) == len(i_A) == len(v_meas_V) == len(mask)):
        raise ValueError("数组长度不一致")
    if mask.sum() <= 200:
        raise ValueError("有效拟合点太少，请放宽 mask 或检查数据")

    if weights is None:
        w = np.ones_like(v_meas_V, dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(v_meas_V):
            raise ValueError("weights 长度不一致")
        w = np.abs(w)

    n_inc = len(soc_knots_desc) - 1
    dim = 3 + 2 * n_inc
    if x0 is None:
        # 初值：高 SOC 小、低 SOC 大
        # R0: 0.03Ω 起步；每段 +0.05Ω（总 ~0.23Ω）
        # C1: 2000F
        # R1: 0.02Ω 起步；每段 +0.8Ω（总 ~3.2Ω）
        x_r0_1 = math.log(0.03)
        x_dr0 = np.log(np.full(n_inc, 0.05, dtype=float))
        x_c1 = math.log(2000.0)
        x_r1_1 = math.log(0.02)
        x_dr1 = np.log(np.full(n_inc, 0.8, dtype=float))
        x0 = np.concatenate([[x_r0_1], x_dr0, [x_c1, x_r1_1], x_dr1])
    x0 = np.asarray(x0, dtype=float)
    if len(x0) != dim:
        raise ValueError(f"x0 长度应为 {dim}")

    # 物理边界（对数域）
    lb = np.full_like(x0, -np.inf, dtype=float)
    ub = np.full_like(x0, np.inf, dtype=float)
    # R0@1
    lb[0], ub[0] = math.log(0.001), math.log(2.0)
    # ΔR0
    for j in range(1, 1 + n_inc):
        lb[j], ub[j] = math.log(1e-6), math.log(20.0)
    # C1
    idx_c1 = 1 + n_inc
    lb[idx_c1], ub[idx_c1] = math.log(1.0), math.log(1e6)
    # R1@1
    idx_r1_1 = idx_c1 + 1
    lb[idx_r1_1], ub[idx_r1_1] = math.log(0.001), math.log(5.0)
    # ΔR1
    for j in range(idx_r1_1 + 1, dim):
        lb[j], ub[j] = math.log(1e-6), math.log(50.0)

    x0 = np.minimum(np.maximum(x0, lb + 1e-12), ub - 1e-12)

    def _unpack(x: np.ndarray) -> tuple[PiecewiseLinearCurve, float, PiecewiseLinearCurve]:
        r0_1 = float(np.exp(x[0]))
        dr0 = np.exp(x[1 : 1 + n_inc])
        c1 = float(np.exp(x[idx_c1]))
        r1_1 = float(np.exp(x[idx_r1_1]))
        dr1 = np.exp(x[idx_r1_1 + 1 :])
        r0_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r0_1, increments=dr0)
        r1_curve = _build_monotone_increasing_curve(soc_knots_desc=soc_knots_desc, y_at_soc1=r1_1, increments=dr1)
        return r0_curve, c1, r1_curve

    def _residuals(x: np.ndarray) -> np.ndarray:
        r0_curve, c1, r1_curve = _unpack(x)
        _, _, v_pred = simulate_ecm_current_control_r0_r1_soc(
            soc0=soc0,
            v1_0_V=v1_0_V,
            capacity_Ah=capacity_Ah,
            ocv=ocv,
            r0_curve=r0_curve,
            c1_F=c1,
            r1_curve=r1_curve,
            dt_s=dt_s,
            i_A=i_A,
        )
        r = v_pred - v_meas_V
        return (w * r)[mask]

    res = least_squares(_residuals, x0=x0, bounds=(lb, ub), method="trf")
    r = _residuals(res.x)
    rmse = float(np.sqrt(np.mean(r * r)))
    mae = float(np.mean(np.abs(r)))
    r0_curve, c1, r1_curve = _unpack(res.x)
    return ECMSOCDepFitResultR0R1(
        r0_curve=r0_curve,
        c1_F=c1,
        r1_curve=r1_curve,
        rmse_V=rmse,
        mae_V=mae,
        n=int(mask.sum()),
    )
