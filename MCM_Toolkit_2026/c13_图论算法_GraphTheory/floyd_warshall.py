# -*- coding: utf-8 -*-
# Floyd-Warshall 全源最短路：适合点数不大（O(n^3)）
#
# 参考来源（资料目录）：部分资料包中常见 Floyd/Dijkstra/Prim/Kruskal

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def floyd_warshall(adj_matrix: Union[np.ndarray, Sequence[Sequence[float]]]) -> Dict[str, Any]:
    """
    Floyd-Warshall 计算全源最短路。

    Args:
        adj_matrix: (n×n) 邻接矩阵，无边用 np.inf；对角线为 0。

    Returns:
        dict:
            - dist: (n×n) 最短距离
            - nxt: (n×n) 下一跳矩阵，用于重建路径；不可达为 -1
    """
    dist = np.asarray(adj_matrix, dtype=float).copy()
    if dist.ndim != 2 or dist.shape[0] != dist.shape[1]:
        raise ValueError("adj_matrix 必须为方阵。")
    n = dist.shape[0]

    nxt = np.full((n, n), -1, dtype=int)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if np.isfinite(dist[i, j]):
                nxt[i, j] = j

    for k in range(n):
        for i in range(n):
            dik = dist[i, k]
            if not np.isfinite(dik):
                continue
            for j in range(n):
                nd = dik + dist[k, j]
                if nd < dist[i, j]:
                    dist[i, j] = nd
                    nxt[i, j] = nxt[i, k]

    return {"dist": dist, "nxt": nxt}


def reconstruct_path(nxt: np.ndarray, u: int, v: int) -> List[int]:
    """由 nxt 矩阵重建 u->v 路径。"""
    u = int(u)
    v = int(v)
    if nxt[u, v] == -1:
        return []
    path = [u]
    while u != v:
        u = int(nxt[u, v])
        if u == -1:
            return []
        path.append(u)
    return path


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Floyd-Warshall。

    Args:
        data: 邻接矩阵或 dict：
            - 直接传入 adj_matrix
            - dict: {'adj_matrix': adj_matrix}
        params: 参数：
            - path: (u,v) | None（若提供则返回该路径）

    Returns:
        dict:
            - dist/nxt
            - path（可选）
    """
    params = params or {}
    if isinstance(data, dict):
        A = data.get("adj_matrix")
    else:
        A = data
    if A is None:
        raise ValueError("data 需要提供邻接矩阵 adj_matrix。")

    out = floyd_warshall(A)
    if params.get("path") is not None:
        u, v = params["path"]
        out["path"] = reconstruct_path(out["nxt"], int(u), int(v))
    return out


if __name__ == "__main__":
    inf = float("inf")
    A = np.array(
        [
            [0, 3, inf, 7],
            [8, 0, 2, inf],
            [5, inf, 0, 1],
            [2, inf, inf, 0],
        ],
        dtype=float,
    )
    out = solve(A, {"path": (0, 2)})
    print("dist[0,2] =", out["dist"][0, 2])
    print("path 0->2 =", out["path"])

