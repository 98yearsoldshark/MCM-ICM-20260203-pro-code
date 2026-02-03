# -*- coding: utf-8 -*-
# 常微分方程初值问题（IVP）：scipy.integrate.solve_ivp
#
# 参考来源（资料目录）：
# - 4、Python各类算法代码集合/41-2 .../08第8章 微分方程模型/...（多处示例使用 odeint / sympy.dsolve）
#
# 说明：
# - 推荐使用 solve_ivp（比 odeint 更现代，支持事件、多个方法等）
# - 本文件提供统一 solve 接口；核心仍是用户提供 dy/dt

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.integrate import solve_ivp

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def solve_ode_ivp(
    fun: Callable[[float, np.ndarray], np.ndarray],
    *,
    t_span: Tuple[float, float],
    y0: Union[np.ndarray, Sequence[float]],
    t_eval: Optional[Union[np.ndarray, Sequence[float]]] = None,
    method: str = "RK45",
    rtol: float = 1e-6,
    atol: Union[float, Sequence[float]] = 1e-9,
    args: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """
    求解 ODE 初值问题：y' = fun(t, y), y(t0)=y0。

    Args:
        fun: 右端函数 fun(t, y) -> dy/dt。
        t_span: (t0, t1)。
        y0: 初值（shape=(n,)）。
        t_eval: 需要输出的时间点（可选）。
        method: 求解方法（RK45/Radau/BDF/DOP853/LSODA 等，见 SciPy 文档）。
        rtol/atol: 误差控制。
        args: 额外参数序列（会传给 fun）。

    Returns:
        dict:
            - t: ndarray (m,)
            - y: ndarray (n,m)
            - success/message/status
            - result: 原始 ODE 结果对象（OdeResult）
    """
    y0_arr = np.asarray(y0, dtype=float).reshape(-1)
    if y0_arr.size == 0:
        raise ValueError("y0 不能为空。")
    t0, t1 = float(t_span[0]), float(t_span[1])
    if t0 == t1:
        raise ValueError("t_span 的起止时间不能相同。")
    t_eval_arr = None if t_eval is None else np.asarray(t_eval, dtype=float).reshape(-1)
    args = tuple(args) if args is not None else ()

    res = solve_ivp(
        fun,
        t_span=(t0, t1),
        y0=y0_arr,
        t_eval=t_eval_arr,
        method=str(method),
        rtol=float(rtol),
        atol=atol,
        args=args,
    )
    return {
        "t": np.asarray(res.t, dtype=float),
        "y": np.asarray(res.y, dtype=float),
        "success": bool(res.success),
        "status": int(res.status),
        "message": str(res.message),
        "result": res,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：ODE 初值问题（solve_ivp）。

    Args:
        data: dict，包含：
            - fun: callable
            - t_span: (t0,t1)
            - y0: array-like
            - t_eval: array-like（可选）
            - args: list（可选）
        params:
            - method/rtol/atol（可选）

    Returns:
        dict: 见 solve_ode_ivp()。
    """
    params = params or {}
    if not isinstance(data, dict) or "fun" not in data or "t_span" not in data or "y0" not in data:
        raise TypeError("data 必须为 dict，且包含 fun/t_span/y0。")
    fun = data["fun"]
    if not callable(fun):
        raise TypeError("data['fun'] 必须为可调用函数 fun(t,y)->dy/dt。")

    return solve_ode_ivp(
        fun,
        t_span=tuple(data["t_span"]),
        y0=data["y0"],
        t_eval=data.get("t_eval"),
        method=str(params.get("method", "RK45")),
        rtol=float(params.get("rtol", 1e-6)),
        atol=params.get("atol", 1e-9),
        args=data.get("args"),
    )


if __name__ == "__main__":
    # Mock Data：Lorenz 系统（资料中常见示例）
    def lorenz(t: float, xyz: np.ndarray, sigma: float = 10.0, rho: float = 28.0, beta: float = 8.0 / 3.0) -> np.ndarray:
        x, y, z = xyz
        return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z], dtype=float)

    t_eval = np.linspace(0.0, 30.0, 3001)
    out = solve(
        {"fun": lorenz, "t_span": (t_eval[0], t_eval[-1]), "y0": [0.0, 1.0, 0.0], "t_eval": t_eval},
        {"method": "RK45", "rtol": 1e-7, "atol": 1e-9},
    )
    print("success =", out["success"], out["message"])
    print("y(t_end) =", np.round(out["y"][:, -1], 6))

