# -*- coding: utf-8 -*-
# MILP/ILP 整数规划：scipy.optimize.milp（HiGHS）
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../整数规划模型Python代码.docx（其中示例其实混杂了匈牙利算法/随机搜索）
#
# 说明：
# - SciPy 的 milp 支持混合整数线性规划（Mixed-Integer Linear Programming）
# - 若你需要“0-1 规划”，把 integrality=1 且 bounds=(0,1) 即可

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def solve_milp(
    c: Union[Sequence[float], np.ndarray],
    *,
    A_ub: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_ub: Optional[Union[np.ndarray, Sequence[float]]] = None,
    A_eq: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_eq: Optional[Union[np.ndarray, Sequence[float]]] = None,
    bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]] = None,
    integrality: Optional[Sequence[int]] = None,
    maximize: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    求解 MILP/ILP：min/max c^T x。

    Args:
        c: 目标系数（n,）。
        A_ub, b_ub: 不等式约束 A_ub x <= b_ub。
        A_eq, b_eq: 等式约束 A_eq x == b_eq。
        bounds: 变量边界列表 length=n；每项为 (low, high)，可为 None。
        integrality: 变量整性列表 length=n：
            - 0：连续变量
            - 1：整数变量
            （更多类型见 SciPy 文档；此处主要覆盖 0/1）
        maximize: True 表示最大化（内部转换为最小化 -c）。
        options: 透传给 scipy.optimize.milp 的 options（例如 time_limit、mip_rel_gap 等）。

    Returns:
        dict:
            - x: 最优解（n,）或 None
            - fun: 目标值（已按 maximize 还原）
            - success/status/message
            - result: 原始 OptimizeResult
    """
    c_arr = np.asarray(c, dtype=float).reshape(-1)
    n = int(c_arr.size)
    c_use = -c_arr if maximize else c_arr

    constraints = []
    if A_ub is not None or b_ub is not None:
        if A_ub is None or b_ub is None:
            raise ValueError("A_ub 与 b_ub 必须同时提供或同时为 None。")
        Aub = np.asarray(A_ub, dtype=float)
        bub = np.asarray(b_ub, dtype=float).reshape(-1)
        if Aub.ndim != 2 or Aub.shape[1] != n:
            raise ValueError("A_ub 维度必须为 (m×n)。")
        if bub.shape[0] != Aub.shape[0]:
            raise ValueError("b_ub 长度必须等于 A_ub 行数。")
        constraints.append(LinearConstraint(Aub, lb=-np.inf, ub=bub))

    if A_eq is not None or b_eq is not None:
        if A_eq is None or b_eq is None:
            raise ValueError("A_eq 与 b_eq 必须同时提供或同时为 None。")
        Aeq = np.asarray(A_eq, dtype=float)
        beq = np.asarray(b_eq, dtype=float).reshape(-1)
        if Aeq.ndim != 2 or Aeq.shape[1] != n:
            raise ValueError("A_eq 维度必须为 (k×n)。")
        if beq.shape[0] != Aeq.shape[0]:
            raise ValueError("b_eq 长度必须等于 A_eq 行数。")
        constraints.append(LinearConstraint(Aeq, lb=beq, ub=beq))

    if bounds is None:
        bnds = Bounds(lb=-np.inf * np.ones(n), ub=np.inf * np.ones(n))
    else:
        lb = np.array([(-np.inf if lo is None else float(lo)) for lo, _ in bounds], dtype=float)
        ub = np.array([(np.inf if hi is None else float(hi)) for _, hi in bounds], dtype=float)
        if lb.shape != (n,) or ub.shape != (n,):
            raise ValueError("bounds 长度必须等于变量个数 n。")
        bnds = Bounds(lb=lb, ub=ub)

    if integrality is None:
        integ = None
    else:
        integ = np.asarray(list(integrality), dtype=int).reshape(-1)
        if integ.shape != (n,):
            raise ValueError("integrality 长度必须等于变量个数 n。")

    res = milp(c_use, integrality=integ, bounds=bnds, constraints=constraints or None, options=options)
    x = None if res.x is None else np.asarray(res.x, dtype=float)
    fun = float(res.fun) if res.fun is not None else np.nan
    if maximize and np.isfinite(fun):
        fun = -fun

    return {"x": x, "fun": fun, "success": bool(res.success), "status": int(res.status), "message": str(res.message), "result": res}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：MILP/ILP。

    Args:
        data: dict，包含：
            - c: 目标系数
            - A_ub/b_ub/A_eq/b_eq/bounds/integrality（可选）
        params: 参数：
            - maximize: bool
            - options: dict（透传给 scipy.optimize.milp）

    Returns:
        dict: 见 solve_milp()。
    """
    params = params or {}
    if not isinstance(data, dict) or "c" not in data:
        raise TypeError("data 必须为 dict，且包含 c。")
    return solve_milp(
        data["c"],
        A_ub=data.get("A_ub"),
        b_ub=data.get("b_ub"),
        A_eq=data.get("A_eq"),
        b_eq=data.get("b_eq"),
        bounds=data.get("bounds"),
        integrality=data.get("integrality"),
        maximize=bool(params.get("maximize", False)),
        options=params.get("options"),
    )


if __name__ == "__main__":
    # Mock Data：0-1 背包的 ILP 形式（小规模）
    # max 10x1 + 7x2 + 3x3
    # s.t. 4x1 + 3x2 + 2x3 <= 6
    # x_i ∈ {0,1}
    out = solve(
        {
            "c": [10, 7, 3],
            "A_ub": [[4, 3, 2]],
            "b_ub": [6],
            "bounds": [(0, 1), (0, 1), (0, 1)],
            "integrality": [1, 1, 1],
        },
        {"maximize": True},
    )
    print("success =", out["success"], out["message"])
    print("x =", out["x"])
    print("objective =", out["fun"])

