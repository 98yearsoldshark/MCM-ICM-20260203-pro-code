# -*- coding: utf-8 -*-
# 二次规划（QP）：min 1/2 x^T P x + q^T x
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../二次规划模型Python代码.docx（示例使用 cvxopt.solvers.qp）
#
# 说明：
# - 本文件默认用 SciPy 的 trust-constr 求解（依赖更少；适合竞赛快速用）
# - 若你本机安装了 cvxopt，可通过 params['solver']="cvxopt" 使用其专用 QP 求解器

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, minimize

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_1d_float(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def _to_2d_float(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 2:
        raise ValueError("矩阵必须为二维。")
    return arr


def _parse_bounds(bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]], n: int) -> Optional[Bounds]:
    if bounds is None:
        return None
    lb = np.array([(-np.inf if lo is None else float(lo)) for lo, _ in bounds], dtype=float)
    ub = np.array([(np.inf if hi is None else float(hi)) for _, hi in bounds], dtype=float)
    if lb.shape != (n,) or ub.shape != (n,):
        raise ValueError("bounds 长度必须等于变量个数 n。")
    return Bounds(lb=lb, ub=ub)


def _default_x0(n: int, bounds: Optional[Bounds]) -> np.ndarray:
    x0 = np.zeros(n, dtype=float)
    if bounds is None:
        return x0
    lb = np.asarray(bounds.lb, dtype=float)
    ub = np.asarray(bounds.ub, dtype=float)
    # 尽量给一个可行/不太极端的初值
    for i in range(n):
        lo, hi = lb[i], ub[i]
        if np.isfinite(lo) and np.isfinite(hi):
            x0[i] = 0.5 * (lo + hi)
        elif np.isfinite(lo) and not np.isfinite(hi):
            x0[i] = max(0.0, lo)
        elif not np.isfinite(lo) and np.isfinite(hi):
            x0[i] = min(0.0, hi)
        else:
            x0[i] = 0.0
    return x0


def _solve_qp_scipy(
    P: np.ndarray,
    q: np.ndarray,
    *,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[Bounds] = None,
    x0: Optional[np.ndarray] = None,
    method: str = "trust-constr",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    n = int(q.size)

    def fun(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        return float(0.5 * x @ P @ x + q @ x)

    def jac(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(-1)
        return (P @ x + q).astype(float)

    def hess(_x: np.ndarray) -> np.ndarray:
        return P

    cons = []
    if A_ub is not None:
        cons.append(LinearConstraint(A_ub, lb=-np.inf * np.ones(int(b_ub.size)), ub=b_ub))
    if A_eq is not None:
        cons.append(LinearConstraint(A_eq, lb=b_eq, ub=b_eq))

    x0_use = _default_x0(n, bounds) if x0 is None else np.asarray(x0, dtype=float).reshape(-1)
    res = minimize(
        fun,
        x0_use,
        method=str(method),
        jac=jac,
        hess=hess if str(method).lower() in {"trust-constr"} else None,
        bounds=bounds,
        constraints=cons,
        options=options,
    )
    return {"x": None if res.x is None else np.asarray(res.x, dtype=float), "fun": float(res.fun), "success": bool(res.success), "status": int(res.status), "message": str(res.message), "result": res, "solver_used": "scipy"}


def _solve_qp_cvxopt(
    P: np.ndarray,
    q: np.ndarray,
    *,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[Bounds] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        from cvxopt import matrix, solvers  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("未安装 cvxopt：请改用 solver='scipy' 或自行 pip install cvxopt。") from e

    show_progress = False
    if options and isinstance(options, dict):
        # cvxopt 的求解器参数通过 solvers.options 配置
        for k, v in options.items():
            if k == "show_progress":
                show_progress = bool(v)
            else:
                solvers.options[k] = v
    # 默认不要输出迭代日志（除非用户显式开启）
    solvers.options["show_progress"] = show_progress

    Pm = matrix(P)
    qm = matrix(q)

    # 拼 Gx<=h：A_ub + bounds
    G_list = []
    h_list = []
    if A_ub is not None:
        G_list.append(A_ub)
        h_list.append(b_ub.reshape(-1))

    if bounds is not None:
        lb = np.asarray(bounds.lb, dtype=float).reshape(-1)
        ub = np.asarray(bounds.ub, dtype=float).reshape(-1)
        n = int(q.size)
        I = np.eye(n, dtype=float)
        for i in range(n):
            if np.isfinite(ub[i]):
                G_list.append(I[i : i + 1, :])
                h_list.append(np.array([ub[i]], dtype=float))
            if np.isfinite(lb[i]):
                G_list.append(-I[i : i + 1, :])
                h_list.append(np.array([-lb[i]], dtype=float))

    if G_list:
        Gm = matrix(np.vstack(G_list))
        hm = matrix(np.concatenate(h_list))
    else:
        Gm, hm = None, None

    Am = None if A_eq is None else matrix(A_eq)
    bm = None if b_eq is None else matrix(b_eq.reshape(-1))

    res = solvers.qp(Pm, qm, Gm, hm, Am, bm)
    x = np.array(res["x"], dtype=float).reshape(-1)
    fun = float(0.5 * x @ P @ x + q @ x)
    return {"x": x, "fun": fun, "success": True, "status": 0, "message": "ok", "result": res, "solver_used": "cvxopt"}


def solve_qp(
    P: Union[np.ndarray, Sequence[Sequence[float]]],
    q: Union[np.ndarray, Sequence[float]],
    *,
    A_ub: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_ub: Optional[Union[np.ndarray, Sequence[float]]] = None,
    A_eq: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    b_eq: Optional[Union[np.ndarray, Sequence[float]]] = None,
    bounds: Optional[Sequence[Tuple[Optional[float], Optional[float]]]] = None,
    x0: Optional[Union[np.ndarray, Sequence[float]]] = None,
    solver: str = "scipy",
    method: str = "trust-constr",
    maximize: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    求解二次规划（QP）。

    Args:
        P: (n×n) 对称矩阵（通常要求半正定以保证凸）。
        q: (n,) 向量。
        A_ub, b_ub: 不等式约束 A_ub x <= b_ub。
        A_eq, b_eq: 等式约束 A_eq x == b_eq。
        bounds: 变量边界列表 length=n。
        x0: 初值（SciPy 求解时使用）。
        solver: "scipy"（默认）或 "cvxopt"（需自行安装 cvxopt）。
        method: SciPy minimize 的 method（默认 trust-constr）。
        maximize: True 表示最大化（仅对 SciPy 求解做简单支持）。
        options: solver 参数（SciPy options 或 cvxopt solvers.options）。

    Returns:
        dict: x/fun/success/message/result/solver_used
    """
    P_arr = _to_2d_float(P)
    q_arr = _to_1d_float(q)
    if P_arr.shape[0] != P_arr.shape[1]:
        raise ValueError("P 必须为方阵。")
    n = int(P_arr.shape[0])
    if q_arr.shape != (n,):
        raise ValueError("q 长度必须与 P 维度一致。")

    Aub = None if A_ub is None else _to_2d_float(A_ub)
    bub = None if b_ub is None else _to_1d_float(b_ub)
    if (Aub is None) ^ (bub is None):
        raise ValueError("A_ub 与 b_ub 必须同时提供或同时为 None。")
    if Aub is not None:
        if Aub.shape[1] != n:
            raise ValueError("A_ub 维度必须为 (m×n)。")
        if bub.shape != (Aub.shape[0],):
            raise ValueError("b_ub 长度必须等于 A_ub 行数。")

    Aeq = None if A_eq is None else _to_2d_float(A_eq)
    beq = None if b_eq is None else _to_1d_float(b_eq)
    if (Aeq is None) ^ (beq is None):
        raise ValueError("A_eq 与 b_eq 必须同时提供或同时为 None。")
    if Aeq is not None:
        if Aeq.shape[1] != n:
            raise ValueError("A_eq 维度必须为 (k×n)。")
        if beq.shape != (Aeq.shape[0],):
            raise ValueError("b_eq 长度必须等于 A_eq 行数。")

    bnds = _parse_bounds(bounds, n)
    x0_arr = None if x0 is None else _to_1d_float(x0)

    if str(solver).lower() == "cvxopt":
        if maximize:
            raise ValueError("cvxopt 求解器不支持 maximize=True（需要凸性保证且符号会改变）。")
        return _solve_qp_cvxopt(P_arr, q_arr, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=bnds, options=options)

    # SciPy：maximize 通过目标取负实现（不保证一定是凸问题）
    P_use = -P_arr if maximize else P_arr
    q_use = -q_arr if maximize else q_arr
    out = _solve_qp_scipy(P_use, q_use, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=bnds, x0=x0_arr, method=method, options=options)
    if maximize and np.isfinite(out["fun"]):
        out["fun"] = -float(out["fun"])
    return out


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：二次规划（QP）。

    Args:
        data: dict，包含：
            - P, q
            - A_ub/b_ub/A_eq/b_eq/bounds/x0（可选）
        params:
            - solver: "scipy" | "cvxopt"
            - method: SciPy method（默认 trust-constr）
            - maximize: bool（默认 False）
            - options: dict
    """
    params = params or {}
    if not isinstance(data, dict) or "P" not in data or "q" not in data:
        raise TypeError("data 必须为 dict，且包含 P 与 q。")
    return solve_qp(
        data["P"],
        data["q"],
        A_ub=data.get("A_ub"),
        b_ub=data.get("b_ub"),
        A_eq=data.get("A_eq"),
        b_eq=data.get("b_eq"),
        bounds=data.get("bounds"),
        x0=data.get("x0"),
        solver=str(params.get("solver", "scipy")),
        method=str(params.get("method", "trust-constr")),
        maximize=bool(params.get("maximize", False)),
        options=params.get("options"),
    )


if __name__ == "__main__":
    # Mock Data：资料中的 cvxopt 示例（这里用 SciPy 也可解）
    # min 1/2 x^T P x + q^T x
    # s.t. x >= 0
    #      x1 + x2 = 1
    P = [[4.0, 1.0], [1.0, 2.0]]
    q = [1.0, 1.0]
    A_ub = [[-1.0, 0.0], [0.0, -1.0]]  # -x <= 0
    b_ub = [0.0, 0.0]
    A_eq = [[1.0, 1.0]]
    b_eq = [1.0]

    out = solve(
        {"P": P, "q": q, "A_ub": A_ub, "b_ub": b_ub, "A_eq": A_eq, "b_eq": b_eq},
        {"solver": "scipy", "method": "trust-constr"},
    )
    print("success =", out["success"], out["message"])
    print("x =", np.round(out["x"], 6))
    print("fun =", out["fun"])
