# -*- coding: utf-8 -*-
# DEA 数据包络分析（CCR/BCC，输入导向）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../评价与决策类题型参考代码.../基于EDA数据包络分析的综合评价代码.rar
#
# 说明：
# - 这里实现的是经典 DEA 线性规划形式（非“效率前沿”可视化）。
# - 依赖 scipy.optimize.linprog（HiGHS）。

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from scipy.optimize import linprog

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def dea_input_oriented(
    X: Union[np.ndarray, list],
    Y: Union[np.ndarray, list],
    *,
    returns_to_scale: str = "crs",
) -> Dict[str, Any]:
    """
    DEA 输入导向效率（CCR/BCC）。

    模型（对每个 DMU0）：

    min   θ
    s.t.  Σ_j λ_j x_ij ≤ θ x_i0        (∀ 输入 i)
          Σ_j λ_j y_rj ≥ y_r0          (∀ 输出 r)
          λ_j ≥ 0
          （BCC/VRS 额外）Σ_j λ_j = 1

    Args:
        X: 输入矩阵（n×m），n 个 DMU，m 个输入指标。
        Y: 输出矩阵（n×s），n 个 DMU，s 个输出指标。
        returns_to_scale: 规模报酬：
            - "crs": 常数规模报酬（CCR）
            - "vrs": 可变规模报酬（BCC）

    Returns:
        dict:
            - theta: (n,) 效率值（≤1 为无效率；=1 为 DEA 有效）
            - lambdas: (n×n) 每个 DMU 的 λ 向量
            - success: (n,) 是否求解成功
            - message: (n,) 求解器信息
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    if X.ndim != 2 or Y.ndim != 2:
        raise ValueError("X/Y 必须为二维矩阵。")
    if X.shape[0] != Y.shape[0]:
        raise ValueError("X 与 Y 的 DMU 数量（行数）必须一致。")
    if np.any(X < 0) or np.any(Y < 0):
        raise ValueError("DEA 通常要求 X/Y 非负。")

    rts = str(returns_to_scale).lower()
    if rts not in {"crs", "vrs"}:
        raise ValueError("returns_to_scale 必须为 'crs' 或 'vrs'。")

    n, m = X.shape
    _, s = Y.shape

    theta = np.full(n, np.nan, dtype=float)
    lambdas = np.full((n, n), np.nan, dtype=float)
    success = np.zeros(n, dtype=bool)
    message = np.array([""] * n, dtype=object)

    # 变量顺序：[theta, lambda_1, ..., lambda_n]
    c = np.zeros(n + 1, dtype=float)
    c[0] = 1.0  # min theta

    bounds = [(0.0, None)] + [(0.0, None)] * n  # theta>=0, lambda>=0

    for k in range(n):
        x0 = X[k, :]
        y0 = Y[k, :]

        A_ub = []
        b_ub = []

        # 输入约束：Σ λ_j x_ij - theta * x_i0 <= 0
        for i in range(m):
            row = np.zeros(n + 1, dtype=float)
            row[0] = -x0[i]
            row[1:] = X[:, i]
            A_ub.append(row)
            b_ub.append(0.0)

        # 输出约束：-Σ λ_j y_rj <= -y_r0
        for r in range(s):
            row = np.zeros(n + 1, dtype=float)
            row[0] = 0.0
            row[1:] = -Y[:, r]
            A_ub.append(row)
            b_ub.append(-y0[r])

        A_ub = np.vstack(A_ub)
        b_ub = np.asarray(b_ub, dtype=float)

        if rts == "vrs":
            # Σ λ_j = 1
            A_eq = np.zeros((1, n + 1), dtype=float)
            A_eq[0, 1:] = 1.0
            b_eq = np.array([1.0], dtype=float)
        else:
            A_eq = None
            b_eq = None

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        success[k] = bool(res.success)
        message[k] = str(res.message)
        if res.success and res.x is not None:
            theta[k] = float(res.x[0])
            lambdas[k, :] = res.x[1:]

    return {"theta": theta, "lambdas": lambdas, "success": success, "message": message, "returns_to_scale": rts}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：DEA 输入导向效率（CCR/BCC）。

    Args:
        data: dict，包含：
            - X: ndarray/list（n×m）输入
            - Y: ndarray/list（n×s）输出
        params: 参数：
            - returns_to_scale: 'crs' | 'vrs'

    Returns:
        dict: 见 dea_input_oriented() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "X" not in data or "Y" not in data:
        raise TypeError("data 必须为 dict，且包含 X 与 Y。")
    return dea_input_oriented(data["X"], data["Y"], returns_to_scale=str(params.get("returns_to_scale", "crs")))


if __name__ == "__main__":
    # Mock Data：6 个 DMU、2 个输入、1 个输出
    X = np.array(
        [
            [10, 8],
            [12, 9],
            [9, 7],
            [11, 8],
            [13, 10],
            [8, 6],
        ],
        dtype=float,
    )
    Y = np.array([[10], [11], [9], [10], [12], [8]], dtype=float)

    out = solve({"X": X, "Y": Y}, {"returns_to_scale": "crs"})
    print("theta =", np.round(out["theta"], 4))
    print("success =", out["success"])

