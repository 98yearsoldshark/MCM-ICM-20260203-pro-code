# -*- coding: utf-8 -*-
# 非线性规划（NLP）：scipy.optimize.minimize
#
# 美赛常见用法：
# - 目标函数是非线性的（可能非凸）
# - 约束包含：等式/不等式 + 变量边界
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../非线性规划模型Python代码.docx

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import Bounds, minimize

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_1d_float(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def _parse_bounds(bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]], n: int) -> Optional[Bounds]:
    if bounds is None:
        return None
    lb = np.array([(-np.inf if lo is None else float(lo)) for lo, _ in bounds], dtype=float)
    ub = np.array([(np.inf if hi is None else float(hi)) for _, hi in bounds], dtype=float)
    if lb.shape != (n,) or ub.shape != (n,):
        raise ValueError("bounds 长度必须等于变量个数 n。")
    return Bounds(lb=lb, ub=ub)


def solve_nlp(
    objective: Callable[[np.ndarray], float],
    *,
    x0: Union[np.ndarray, Sequence[float]],
    bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]] = None,
    constraints: Optional[Sequence[Any]] = None,
    method: str = "SLSQP",
    maximize: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    求解非线性规划：min/max objective(x)。

    Args:
        objective: 目标函数 f(x)。
        x0: 初值（n,）。
        bounds: 变量边界列表 length=n，每项 (low, high)。
        constraints: 约束列表（按 SciPy minimize 约定）：
            - dict: {'type': 'eq'|'ineq', 'fun': callable}
            - 或 Constraint 对象（trust-constr 等方法支持）
        method: minimize 的方法（常用：SLSQP、trust-constr、COBYLA 等）。
        maximize: True 表示最大化（内部求解最小化 -f）。
        options: 透传给 minimize 的 options。

    Returns:
        dict:
            - x: 最优解（n,）
            - fun: 最优目标值（已按 maximize 还原）
            - success/status/message
            - result: 原始 OptimizeResult
    """
    x0_arr = _to_1d_float(x0)
    n = int(x0_arr.size)
    bnds = _parse_bounds(bounds, n) if bounds is not None else None

    def obj_use(x: np.ndarray) -> float:
        v = float(objective(np.asarray(x, dtype=float)))
        return -v if maximize else v

    res = minimize(
        obj_use,
        x0_arr,
        method=str(method),
        bounds=bnds,
        constraints=constraints or (),
        options=options,
    )
    fun = float(res.fun)
    if maximize and np.isfinite(fun):
        fun = -fun

    return {"x": None if res.x is None else np.asarray(res.x, dtype=float), "fun": fun, "success": bool(res.success), "status": int(res.status), "message": str(res.message), "result": res}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：非线性规划。

    Args:
        data: dict，包含：
            - objective: callable
            - x0: 初值
            - bounds: list[(low, high)]（可选）
            - constraints: list（可选，按 SciPy minimize 约定）
        params: 参数：
            - method: str（默认 SLSQP）
            - maximize: bool（默认 False）
            - options: dict（可选）

    Returns:
        dict: 见 solve_nlp()。
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "x0" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 x0。")
    obj = data["objective"]
    if not callable(obj):
        raise TypeError("data['objective'] 必须为可调用函数 objective(x)->float。")

    return solve_nlp(
        obj,
        x0=data["x0"],
        bounds=data.get("bounds"),
        constraints=data.get("constraints"),
        method=str(params.get("method", "SLSQP")),
        maximize=bool(params.get("maximize", False)),
        options=params.get("options"),
    )


if __name__ == "__main__":
    # Mock Data：资料中的示例（SLSQP）
    def objective(x: np.ndarray) -> float:
        return float(x[0] ** 2 + x[1] ** 2 + x[2] ** 2 + 8)

    # 约束（注意：SLSQP 的 ineq 约束约定为 fun(x) >= 0）
    cons = [
        {"type": "ineq", "fun": lambda x: x[0] ** 2 - x[1] + x[2] ** 2},
        {"type": "ineq", "fun": lambda x: -(x[0] + x[1] ** 2 + x[2] ** 2 - 20)},
        {"type": "eq", "fun": lambda x: -x[0] - x[1] ** 2 + 2},
        {"type": "eq", "fun": lambda x: x[1] + 2 * x[2] ** 2 - 3},
    ]
    out = solve(
        {
            "objective": objective,
            "x0": [0, 0, 0],
            "bounds": [(0.0, None), (0.0, None), (0.0, None)],
            "constraints": cons,
        },
        {"method": "SLSQP"},
    )
    print("success =", out["success"], out["message"])
    print("x =", np.round(out["x"], 6))
    print("fun =", out["fun"])

