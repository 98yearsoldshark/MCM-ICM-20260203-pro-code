# -*- coding: utf-8 -*-
# 匈牙利算法（Hungarian）：指派/匹配问题（线性和分配）
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../整数规划模型Python代码.docx（其中给了 scipy.optimize.linear_sum_assignment 示例）
#
# 说明：
# - 这里直接封装 SciPy 的 linear_sum_assignment（内部就是匈牙利算法/其变体）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import linear_sum_assignment

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def hungarian_assignment(cost: Union[np.ndarray, Sequence[Sequence[float]]], *, maximize: bool = False) -> Dict[str, Any]:
    """
    求解指派问题：min/max Σ cost[i, assign(i)]。

    Args:
        cost: 成本矩阵（m×n）。
        maximize: True 表示最大化（内部将 cost 转换为等价的最小化问题）。

    Returns:
        dict:
            - row_ind: 行索引（m_assign,)
            - col_ind: 列索引（m_assign,)
            - assignment: list[(row, col, cost_value)]
            - total_cost: 总成本（若 maximize=True，则为最大化目标的总收益）
    """
    C = np.asarray(cost, dtype=float)
    if C.ndim != 2:
        raise ValueError("cost 必须为二维矩阵。")

    if maximize:
        # 线性变换保持最优解：max C <=> min (C_max - C)
        Cmax = float(np.max(C))
        C_use = Cmax - C
    else:
        C_use = C

    row_ind, col_ind = linear_sum_assignment(C_use)
    row_ind = np.asarray(row_ind, dtype=int)
    col_ind = np.asarray(col_ind, dtype=int)

    if maximize:
        chosen = C[row_ind, col_ind]
        total = float(np.sum(chosen))
    else:
        chosen = C[row_ind, col_ind]
        total = float(np.sum(chosen))

    assignment = [(int(r), int(c), float(C[int(r), int(c)])) for r, c in zip(row_ind, col_ind)]
    return {"row_ind": row_ind, "col_ind": col_ind, "assignment": assignment, "total_cost": total, "maximize": bool(maximize)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：匈牙利算法求解指派问题。

    Args:
        data: 成本矩阵或 dict：
            - 直接传入 cost
            - dict: {'cost': cost}
        params: 参数：
            - maximize: bool（默认 False）

    Returns:
        dict: 见 hungarian_assignment()。
    """
    params = params or {}
    if isinstance(data, dict):
        cost = data.get("cost")
    else:
        cost = data
    if cost is None:
        raise ValueError("data 需要提供 cost。")
    return hungarian_assignment(cost, maximize=bool(params.get("maximize", False)))


if __name__ == "__main__":
    cost = np.array([[4, 1, 3], [2, 0, 5], [3, 2, 2]], dtype=float)
    out = solve(cost)
    print("assignment =", out["assignment"])
    print("total_cost =", out["total_cost"])

