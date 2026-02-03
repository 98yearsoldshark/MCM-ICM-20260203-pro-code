# -*- coding: utf-8 -*-
# Prim 最小生成树（MST）：适合稠密图（邻接矩阵 O(n^2) 实现）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Edge = Tuple[int, int, float]


def prim_mst(adj_matrix: Union[np.ndarray, Sequence[Sequence[float]]], *, start: int = 0) -> Dict[str, Any]:
    """
    Prim 最小生成树（无向图）。

    Args:
        adj_matrix: (n×n) 邻接矩阵，无边为 inf，对角线为 0。
        start: 起点（默认 0）。

    Returns:
        dict:
            - mst_edges: MST 边列表
            - total_weight: 总权重
            - is_connected: 是否连通（若不连通则为最小生成森林的一棵树）
    """
    A = np.asarray(adj_matrix, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("adj_matrix 必须为方阵。")
    n = A.shape[0]
    start = int(start)
    if not (0 <= start < n):
        raise ValueError("start 必须在 [0,n) 内。")

    in_mst = np.zeros(n, dtype=bool)
    key = np.full(n, np.inf, dtype=float)
    parent = np.full(n, -1, dtype=int)

    key[start] = 0.0
    for _ in range(n):
        # 选取不在 MST 中且 key 最小的点
        u = int(np.argmin(np.where(in_mst, np.inf, key)))
        if not np.isfinite(key[u]):
            break  # 不连通
        in_mst[u] = True

        # 松弛相邻点
        for v in range(n):
            w = float(A[u, v])
            if not in_mst[v] and np.isfinite(w) and w < key[v]:
                key[v] = w
                parent[v] = u

    mst_edges: List[Edge] = []
    total = 0.0
    for v in range(n):
        u = int(parent[v])
        if u != -1:
            w = float(A[u, v])
            mst_edges.append((u, v, w))
            total += w

    is_connected = bool(np.all(in_mst))
    return {"mst_edges": mst_edges, "total_weight": float(total), "is_connected": is_connected}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Prim MST。

    Args:
        data: 邻接矩阵或 dict：
            - 直接传入 adj_matrix
            - dict: {'adj_matrix': adj_matrix}
        params: 参数：
            - start: int（默认 0）

    Returns:
        dict: prim_mst() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        A = data.get("adj_matrix")
    else:
        A = data
    if A is None:
        raise ValueError("data 需要提供邻接矩阵 adj_matrix。")
    return prim_mst(A, start=int(params.get("start", 0)))


if __name__ == "__main__":
    inf = float("inf")
    A = np.array(
        [
            [0, 2, inf, 6, inf],
            [2, 0, 3, 8, 5],
            [inf, 3, 0, inf, 7],
            [6, 8, inf, 0, 9],
            [inf, 5, 7, 9, 0],
        ],
        dtype=float,
    )
    out = solve(A, {"start": 0})
    print("total_weight =", out["total_weight"])
    print("mst_edges =", out["mst_edges"])

