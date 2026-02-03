# -*- coding: utf-8 -*-
# 数值仿真：按“年度分段常数资源”推进 ODE
#
# 核心思想：
# - 环境过程在年尺度上切换（Δ=1 year），每一年内部把 R 视为常数 R_k
# - 每一年用 solve_ivp 积分一次，把年末状态作为下一年的初值
# - 这样环境序列与动力学积分解耦，便于复现与配对对照（common random numbers）

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from .model0 import Model0Params, rhs_model0, x_from_resource
from .model1 import Model1Params, rhs_model1
from .model2 import Model2Params, rhs_model2
from .model3 import Model3Params, rhs_model3


@dataclass(frozen=True)
class SimConfig:
    years: int = 200
    steps_per_year: int = 12  # 每年输出多少个采样点（用于统计指标）
    solver_method: str = "RK45"
    rtol: float = 1e-6
    atol: float = 1e-9


RhsWithR = Callable[[float, np.ndarray, float], np.ndarray]
PostYearHook = Callable[[float, np.ndarray], None]


def simulate_piecewise_ode(
    *,
    rhs: RhsWithR,
    R_series: np.ndarray,
    y0: np.ndarray,
    config: SimConfig,
    post_year: PostYearHook | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """通用分段常数资源 ODE 推进器。

    约定：
    - 时间单位：年
    - 资源序列：每一年一个常数 R_k（长度=years）

    参数：
    - rhs(t, y, Rk)：右端项函数
    - post_year(Rk, y_end)：每一年结束后的“修正钩子”（可选，用于裁剪/重置诊断变量）
    """
    R_series = np.asarray(R_series, dtype=float)
    if R_series.ndim != 1:
        raise ValueError("R_series 需要是一维数组。")
    if len(R_series) != config.years:
        raise ValueError(f"R_series 长度 {len(R_series)} != years {config.years}")

    y = np.asarray(y0, dtype=float).copy()
    if y.ndim != 1:
        raise ValueError("y0 需要是一维状态向量。")

    t_all: list[float] = []
    y_all: list[np.ndarray] = []

    t0 = 0.0
    for k in range(config.years):
        Rk = float(R_series[k])
        t1 = t0 + 1.0

        t_eval = np.linspace(t0, t1, config.steps_per_year + 1)

        def f(t: float, y_vec: np.ndarray) -> np.ndarray:
            return rhs(t, y_vec, Rk)

        sol = solve_ivp(
            f,
            t_span=(t0, t1),
            y0=y,
            t_eval=t_eval,
            method=config.solver_method,
            rtol=config.rtol,
            atol=config.atol,
        )
        if not sol.success:
            raise RuntimeError(f"solve_ivp 在第 {k} 年积分失败：{sol.message}")

        # 拼接全年轨迹；除了第一年之外避免重复拼接边界点 t=t0
        if k == 0:
            t_all.extend(sol.t.tolist())
            y_all.extend(sol.y.T)
        else:
            t_all.extend(sol.t[1:].tolist())
            y_all.extend(sol.y.T[1:])

        y = sol.y[:, -1]
        # 数值安全：一般状态变量都应非负，这里做一次“软裁剪”
        y = np.maximum(y, 0.0)

        if post_year is not None:
            post_year(Rk, y)

        t0 = t1

    return np.asarray(t_all, dtype=float), np.asarray(y_all, dtype=float)


def simulate_timevarying_ode(
    *,
    rhs: Callable[[float, np.ndarray], np.ndarray],
    years: int,
    steps_per_year: int,
    y0: np.ndarray,
    solver_method: str = "RK45",
    rtol: float = 1e-6,
    atol: float = 1e-9,
) -> Tuple[np.ndarray, np.ndarray]:
    """通用“连续时间变资源”ODE 推进器（适合季节项 R(t)）。

    - 时间单位：年
    - 输出：每年 steps_per_year 个采样点（含起点/终点）
    """
    years = int(years)
    steps_per_year = int(steps_per_year)
    if years <= 0:
        raise ValueError("years 必须为正。")
    if steps_per_year <= 0:
        raise ValueError("steps_per_year 必须为正。")

    y0 = np.asarray(y0, dtype=float)
    if y0.ndim != 1:
        raise ValueError("y0 需要是一维状态向量。")

    t0, t1 = 0.0, float(years)
    t_eval = np.linspace(t0, t1, years * steps_per_year + 1)

    sol = solve_ivp(
        rhs,
        t_span=(t0, t1),
        y0=y0,
        t_eval=t_eval,
        method=str(solver_method),
        rtol=float(rtol),
        atol=float(atol),
    )
    if not sol.success:
        raise RuntimeError(f"solve_ivp 积分失败：{sol.message}")

    y = sol.y.T
    # 数值安全：一般状态变量应非负
    y = np.maximum(y, 0.0)
    return sol.t.astype(float), y.astype(float)


def simulate_model0_piecewise(
    *,
    params: Model0Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_series: np.ndarray,
    y0: np.ndarray,
    config: SimConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """按“每年分段常数资源 R_k”仿真 Model-0。

    返回：
      t_all: (n_points,)
      y_all: (n_points, n_states)
    """
    y0 = np.asarray(y0, dtype=float)
    if y0.shape != (6,):
        raise ValueError("Model-0 的 y0 需要是 (6,)：[H,L,J,M,F,x_bar]")

    def rhs(t: float, y_vec: np.ndarray, Rk: float) -> np.ndarray:
        return rhs_model0(
            t,
            y_vec,
            R=Rk,
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
        )

    def post_year(Rk: float, y_end: np.ndarray) -> None:
        # w==0 时 x_bar 对动力学无影响；为了让诊断值可读，每年末把它重置为当前 x
        if w <= 0:
            L = float(y_end[1])
            y_end[5] = x_from_resource(R=Rk, L=float(max(L, 0.0)), K_u=params.K_u, eps_L=params.eps_L)
        # 数值安全：把 x_bar 裁剪到 [0,1]
        y_end[5] = float(np.clip(y_end[5], 0.0, 1.0))

    return simulate_piecewise_ode(rhs=rhs, R_series=R_series, y0=y0, config=config, post_year=post_year)


def simulate_model0_timevarying(
    *,
    params: Model0Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_of_t: Callable[[float], float],
    y0: np.ndarray,
    config: SimConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Model-0 在连续时间变资源 R(t) 下的仿真（适合季节项）。"""
    y0 = np.asarray(y0, dtype=float)
    if y0.shape != (6,):
        raise ValueError("Model-0 的 y0 需要是 (6,)：[H,L,J,M,F,x_bar]")

    def f(t: float, y_vec: np.ndarray) -> np.ndarray:
        return rhs_model0(
            t,
            y_vec,
            R=float(R_of_t(float(t))),
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
        )

    return simulate_timevarying_ode(
        rhs=f,
        years=config.years,
        steps_per_year=config.steps_per_year,
        y0=y0,
        solver_method=config.solver_method,
        rtol=config.rtol,
        atol=config.atol,
    )


def simulate_model1_piecewise(
    *,
    params: Model1Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_series: np.ndarray,
    y0: np.ndarray,
    config: SimConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """按“每年分段常数资源 R_k”仿真 Model-1（含 B_L）。"""
    y0 = np.asarray(y0, dtype=float)
    if y0.shape != (7,):
        raise ValueError("Model-1 的 y0 需要是 (7,)：[H,L,J,M,F,x_bar,B_L]")

    def rhs(t: float, y_vec: np.ndarray, Rk: float) -> np.ndarray:
        return rhs_model1(
            t,
            y_vec,
            R=Rk,
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
        )

    def post_year(Rk: float, y_end: np.ndarray) -> None:
        if w <= 0:
            L = float(y_end[1])
            y_end[5] = x_from_resource(
                R=Rk,
                L=float(max(L, 0.0)),
                K_u=params.base.K_u,
                eps_L=params.base.eps_L,
            )
        y_end[5] = float(np.clip(y_end[5], 0.0, 1.0))

        # B_L 的自限裁剪（仅用于抑制数值误差的轻微越界）
        if params.bl.K_cap > 0:
            y_end[6] = float(np.clip(y_end[6], 0.0, params.bl.K_cap))

    return simulate_piecewise_ode(rhs=rhs, R_series=R_series, y0=y0, config=config, post_year=post_year)


def simulate_model2_piecewise(
    *,
    params: Model2Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_series: np.ndarray,
    y0: np.ndarray,
    config: SimConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """按“每年分段常数资源 R_k”仿真 Model-2（含 B_H）。"""
    y0 = np.asarray(y0, dtype=float)
    if y0.shape != (7,):
        raise ValueError("Model-2 的 y0 需要是 (7,)：[H,L,J,M,F,x_bar,B_H]")

    def rhs(t: float, y_vec: np.ndarray, Rk: float) -> np.ndarray:
        return rhs_model2(
            t,
            y_vec,
            R=Rk,
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
        )

    def post_year(Rk: float, y_end: np.ndarray) -> None:
        if w <= 0:
            L = float(y_end[1])
            y_end[5] = x_from_resource(
                R=Rk,
                L=float(max(L, 0.0)),
                K_u=params.base.K_u,
                eps_L=params.base.eps_L,
            )
        y_end[5] = float(np.clip(y_end[5], 0.0, 1.0))

        if params.bh.K_cap > 0:
            y_end[6] = float(np.clip(y_end[6], 0.0, params.bh.K_cap))

    return simulate_piecewise_ode(rhs=rhs, R_series=R_series, y0=y0, config=config, post_year=post_year)


def simulate_model3_piecewise(
    *,
    params: Model3Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_series: np.ndarray,
    y0: np.ndarray,
    config: SimConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """按“每年分段常数资源 R_k”仿真 Model-3（含 B_L 与 B_H）。"""
    y0 = np.asarray(y0, dtype=float)
    if y0.shape != (8,):
        raise ValueError("Model-3 的 y0 需要是 (8,)：[H,L,J,M,F,x_bar,B_L,B_H]")

    def rhs(t: float, y_vec: np.ndarray, Rk: float) -> np.ndarray:
        return rhs_model3(
            t,
            y_vec,
            R=Rk,
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
        )

    def post_year(Rk: float, y_end: np.ndarray) -> None:
        if w <= 0:
            L = float(y_end[1])
            y_end[5] = x_from_resource(
                R=Rk,
                L=float(max(L, 0.0)),
                K_u=params.base.K_u,
                eps_L=params.base.eps_L,
            )
        y_end[5] = float(np.clip(y_end[5], 0.0, 1.0))

        if params.bl.K_cap > 0:
            y_end[6] = float(np.clip(y_end[6], 0.0, params.bl.K_cap))
        if params.bh.K_cap > 0:
            y_end[7] = float(np.clip(y_end[7], 0.0, params.bh.K_cap))

    return simulate_piecewise_ode(rhs=rhs, R_series=R_series, y0=y0, config=config, post_year=post_year)


def steady_state_model0(
    *,
    params: Model0Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_const: float,
    y0: np.ndarray,
    years: int = 400,
    config: SimConfig | None = None,
) -> np.ndarray:
    """常值资源下通过长时间积分近似求稳态（用于 N_ref、阈值等）。"""
    if config is None:
        config = SimConfig(years=years, steps_per_year=12)
    R_series = np.full((config.years,), float(R_const), dtype=float)
    _, y = simulate_model0_piecewise(
        params=params,
        gamma=gamma,
        w=w,
        p_m_override=p_m_override,
        R_series=R_series,
        y0=y0,
        config=config,
    )
    return y[-1]


def steady_state_model1(
    *,
    params: Model1Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_const: float,
    y0: np.ndarray,
    years: int = 400,
    config: SimConfig | None = None,
) -> np.ndarray:
    """常值资源下近似求 Model-1 的稳态。"""
    if config is None:
        config = SimConfig(years=years, steps_per_year=12)
    R_series = np.full((config.years,), float(R_const), dtype=float)
    _, y = simulate_model1_piecewise(
        params=params,
        gamma=gamma,
        w=w,
        p_m_override=p_m_override,
        R_series=R_series,
        y0=y0,
        config=config,
    )
    return y[-1]


def steady_state_model2(
    *,
    params: Model2Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_const: float,
    y0: np.ndarray,
    years: int = 400,
    config: SimConfig | None = None,
) -> np.ndarray:
    """常值资源下近似求 Model-2 的稳态。"""
    if config is None:
        config = SimConfig(years=years, steps_per_year=12)
    R_series = np.full((config.years,), float(R_const), dtype=float)
    _, y = simulate_model2_piecewise(
        params=params,
        gamma=gamma,
        w=w,
        p_m_override=p_m_override,
        R_series=R_series,
        y0=y0,
        config=config,
    )
    return y[-1]


def steady_state_model3(
    *,
    params: Model3Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    R_const: float,
    y0: np.ndarray,
    years: int = 400,
    config: SimConfig | None = None,
) -> np.ndarray:
    """常值资源下近似求 Model-3 的稳态。"""
    if config is None:
        config = SimConfig(years=years, steps_per_year=12)
    R_series = np.full((config.years,), float(R_const), dtype=float)
    _, y = simulate_model3_piecewise(
        params=params,
        gamma=gamma,
        w=w,
        p_m_override=p_m_override,
        R_series=R_series,
        y0=y0,
        config=config,
    )
    return y[-1]
