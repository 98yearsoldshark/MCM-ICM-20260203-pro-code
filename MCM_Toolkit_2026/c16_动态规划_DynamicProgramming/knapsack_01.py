# -*- coding: utf-8 -*-
# 0-1 背包问题（动态规划）：在容量约束下选择若干物品使总价值最大
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../0-1背包问题动态规划模型Python代码

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def knapsack_01(
    values: Sequence[float],
    weights: Sequence[int],
    capacity: int,
    *,
    return_items: bool = True,
    max_table_cells: int = 5_000_000,
) -> Dict[str, Any]:
    """
    0-1 背包（每个物品最多选 1 次）。

    Args:
        values: 物品价值 v_i（长度 n）。
        weights: 物品重量/体积 w_i（长度 n，非负整数）。
        capacity: 背包容量 C（非负整数）。
        return_items: 是否返回选中的物品索引（默认 True）。
        max_table_cells: 若需要回溯选取物品，会构建 DP 选择表（n×(C+1)）。
            当 n*(C+1) 超过该阈值时，为节省内存将不返回选中物品。

    Returns:
        dict:
            - max_value: 最大总价值
            - selected_indices: 选中物品的 0-based 索引（可能为空/None）
            - selected_weight: 选中物品总重量
            - selected_value: 选中物品总价值（与 max_value 一致）
    """
    v = np.asarray(list(values), dtype=float).reshape(-1)
    w = np.asarray(list(weights), dtype=int).reshape(-1)
    if v.shape != w.shape:
        raise ValueError("values 与 weights 长度必须一致。")
    if np.any(w < 0):
        raise ValueError("weights 必须为非负整数。")
    C = int(capacity)
    if C < 0:
        raise ValueError("capacity 必须为非负整数。")

    n = int(v.size)
    if n == 0 or C == 0:
        return {"max_value": 0.0, "selected_indices": [], "selected_weight": 0, "selected_value": 0.0}

    # dp[i][c]：前 i 个物品（0..i-1）在容量 c 下的最大价值
    # 为便于回溯，默认使用 2D；若太大则只做 1D，不返回选取集合。
    need_cells = n * (C + 1)
    if return_items and need_cells <= int(max_table_cells):
        dp = np.zeros((n + 1, C + 1), dtype=float)
        take = np.zeros((n + 1, C + 1), dtype=bool)

        for i in range(1, n + 1):
            wi = int(w[i - 1])
            vi = float(v[i - 1])
            for c in range(C + 1):
                # 不选
                best = dp[i - 1, c]
                chosen = False
                # 选
                if wi <= c:
                    cand = dp[i - 1, c - wi] + vi
                    if cand > best:
                        best = cand
                        chosen = True
                dp[i, c] = best
                take[i, c] = chosen

        max_value = float(dp[n, C])

        # 回溯选取集合
        selected: List[int] = []
        c = C
        for i in range(n, 0, -1):
            if take[i, c]:
                idx = i - 1
                selected.append(idx)
                c -= int(w[idx])
        selected.reverse()

        sel_w = int(np.sum(w[selected])) if selected else 0
        sel_v = float(np.sum(v[selected])) if selected else 0.0
        return {"max_value": max_value, "selected_indices": selected, "selected_weight": sel_w, "selected_value": sel_v}

    # 1D DP：只返回最优值（更省内存）
    dp1 = np.zeros(C + 1, dtype=float)
    for i in range(n):
        wi = int(w[i])
        vi = float(v[i])
        # 倒序遍历容量，避免重复使用同一物品
        for c in range(C, wi - 1, -1):
            dp1[c] = max(dp1[c], dp1[c - wi] + vi)

    return {
        "max_value": float(dp1[C]),
        "selected_indices": None,
        "selected_weight": None,
        "selected_value": None,
        "note": "容量/物品规模较大：为节省内存未返回选中集合（可调大 max_table_cells）。",
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：0-1 背包。

    Args:
        data: dict，包含：
            - values: list[float]
            - weights: list[int]
            - capacity: int
        params: 参数：
            - return_items: bool（默认 True）
            - max_table_cells: int（默认 5_000_000）

    Returns:
        dict: 见 knapsack_01()。
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")
    for k in ("values", "weights", "capacity"):
        if k not in data:
            raise ValueError(f"data 缺少必要字段：{k}")

    return knapsack_01(
        data["values"],
        data["weights"],
        int(data["capacity"]),
        return_items=bool(params.get("return_items", True)),
        max_table_cells=int(params.get("max_table_cells", 5_000_000)),
    )


if __name__ == "__main__":
    # Mock Data：随机 0-1 背包
    rng = np.random.default_rng(0)
    n = 15
    weights = rng.integers(1, 20, size=n).tolist()
    values = rng.integers(10, 80, size=n).tolist()
    capacity = 40

    out = solve({"values": values, "weights": weights, "capacity": capacity})
    print("capacity =", capacity)
    print("weights  =", weights)
    print("values   =", values)
    print("max_value =", out["max_value"])
    print("selected_indices =", out["selected_indices"])
    if out["selected_indices"] is not None:
        idx = out["selected_indices"]
        print("selected_weight =", out["selected_weight"])
        print("selected_value  =", out["selected_value"])

