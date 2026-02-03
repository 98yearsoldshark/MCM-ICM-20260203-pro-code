# -*- coding: utf-8 -*-
# 线性规划（LP）：scipy.optimize.linprog 的轻量封装
#
# 美赛中常见：资源分配、运输、选址、排产等（连续变量场景）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import linprog

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def solve_lp(
    c: Union[Sequence[float], np.ndarray],
    *,
    A_ub: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_ub: Optional[Union[np.ndarray, Sequence[float]]] = None,
    A_eq: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_eq: Optional[Union[np.ndarray, Sequence[float]]] = None,
    bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]] = None,
    maximize: bool = False,
) -> Dict[str, Any]:
    """
    线性规划求解。

    Args:
        c: 目标系数（n,）。
        A_ub, b_ub: 不等式约束 A_ub x <= b_ub。
        A_eq, b_eq: 等式约束 A_eq x == b_eq。
        bounds: 变量边界列表 length=n；每项为 (low, high)，可为 None。
        maximize: True 表示最大化 c^T x（内部转为最小化 -c^T x）。

    Returns:
        dict:
            - x: 最优解（n,）或 None
            - fun: 目标值（最小化的值；若 maximize=True 则已还原为最大化目标值）
            - success/message/status
            - result: 原始 scipy OptimizeResult
    """
    c_arr = np.asarray(c, dtype=float).reshape(-1)
    if maximize:
        c_use = -c_arr
    else:
        c_use = c_arr

    res = linprog(
        c_use,
        A_ub=None if A_ub is None else np.asarray(A_ub, dtype=float),
        b_ub=None if b_ub is None else np.asarray(b_ub, dtype=float),
        A_eq=None if A_eq is None else np.asarray(A_eq, dtype=float),
        b_eq=None if b_eq is None else np.asarray(b_eq, dtype=float),
        bounds=bounds,
        method="highs",
    )

    x = None if res.x is None else np.asarray(res.x, dtype=float)
    fun = float(res.fun) if res.fun is not None else np.nan
    if maximize and np.isfinite(fun):
        fun = -fun

    return {"x": x, "fun": fun, "success": bool(res.success), "status": int(res.status), "message": str(res.message), "result": res}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：线性规划。

    Args:
        data: dict，包含：
            - c: 目标系数
            - A_ub, b_ub, A_eq, b_eq, bounds（可选）
        params: 参数：
            - maximize: bool

    Returns:
        dict: 见 solve_lp() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "c" not in data:
        raise TypeError("data 必须为 dict，且包含目标系数 c。")
    return solve_lp(
        data["c"],
        A_ub=data.get("A_ub"),
        b_ub=data.get("b_ub"),
        A_eq=data.get("A_eq"),
        b_eq=data.get("b_eq"),
        bounds=data.get("bounds"),
        maximize=bool(params.get("maximize", False)),
    )


if __name__ == "__main__":
    # Mock Data：最大化 3x + 2y
    # s.t. x + y <= 4
    #      x <= 2
    #      y <= 3
    #      x,y >= 0
    out = solve(
        {
            "c": [3, 2],
            "A_ub": [[1, 1], [1, 0], [0, 1]],
            "b_ub": [4, 2, 3],
            "bounds": [(0, None), (0, None)],
        },
        {"maximize": True},
    )
    print("success =", out["success"], out["message"])
    print("x =", out["x"])
    print("objective =", out["fun"])

