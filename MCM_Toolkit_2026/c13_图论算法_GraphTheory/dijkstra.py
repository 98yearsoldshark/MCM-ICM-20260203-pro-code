# -*- coding: utf-8 -*-
# Dijkstra 最短路（非负权）：支持邻接矩阵/边列表输入
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../DijkstraPlan.m

from __future__ import annotations

import heapq
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Edge = Tuple[int, int, float]


def _build_adj(n: int, edges: Sequence[Edge], directed: bool) -> List[List[Tuple[int, float]]]:
    adj: List[List[Tuple[int, float]]] = [[] for _ in range(n)]
    for u, v, w in edges:
        if w < 0:
            raise ValueError("Dijkstra 不支持负权边。")
        adj[u].append((v, float(w)))
        if not directed:
            adj[v].append((u, float(w)))
    return adj


def dijkstra(
    n: int,
    *,
    source: int = 0,
    edges: Optional[Sequence[Edge]] = None,
    adj_matrix: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    directed: bool = False,
) -> Dict[str, Any]:
    """
    Dijkstra 单源最短路。

    Args:
        n: 节点数（0..n-1）。
        source: 源点。
        edges: 边列表 [(u,v,w), ...]。
        adj_matrix: 邻接矩阵（n×n），无边用 np.inf；对角线应为 0。
        directed: 是否有向图（edges 输入时生效）。

    Returns:
        dict:
            - dist: (n,) 最短距离（不可达为 inf）
            - prev: (n,) 前驱节点（不可达为 -1）
    """
    if n <= 0:
        raise ValueError("n 必须 > 0。")
    source = int(source)
    if not (0 <= source < n):
        raise ValueError("source 必须在 [0,n) 内。")

    if adj_matrix is not None and edges is not None:
        raise ValueError("edges 与 adj_matrix 二选一。")

    if adj_matrix is not None:
        A = np.asarray(adj_matrix, dtype=float)
        if A.shape != (n, n):
            raise ValueError("adj_matrix 形状必须为 (n×n)。")
        if np.any(A < 0):
            raise ValueError("Dijkstra 不支持负权边。")
        adj = [[] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                w = float(A[i, j])
                if i == j:
                    continue
                if np.isfinite(w):
                    adj[i].append((j, w))
    else:
        if edges is None:
            raise ValueError("必须提供 edges 或 adj_matrix。")
        adj = _build_adj(n, edges, directed=bool(directed))

    dist = np.full(n, np.inf, dtype=float)
    prev = np.full(n, -1, dtype=int)
    dist[source] = 0.0

    pq: List[Tuple[float, int]] = [(0.0, source)]
    visited = np.zeros(n, dtype=bool)

    while pq:
        d_u, u = heapq.heappop(pq)
        if visited[u]:
            continue
        visited[u] = True
        if d_u > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d_u + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    return {"dist": dist, "prev": prev}


def reconstruct_path(prev: np.ndarray, target: int) -> List[int]:
    """由 prev 重建从源点到 target 的路径（需要 prev 来自 dijkstra）。"""
    target = int(target)
    path = []
    cur = target
    while cur != -1:
        path.append(cur)
        cur = int(prev[cur])
    path.reverse()
    return path


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Dijkstra 最短路。

    Args:
        data: dict，包含：
            - n: int
            - edges: list[(u,v,w)] 或 adj_matrix: (n×n)
        params: 参数：
            - source: int（默认 0）
            - directed: bool（默认 False，仅 edges 模式）
            - target: int | None（若提供则额外返回 path）

    Returns:
        dict:
            - dist/prev
            - path（可选）
    """
    params = params or {}
    if not isinstance(data, dict) or "n" not in data:
        raise TypeError("data 必须为 dict，且包含 n。")

    out = dijkstra(
        int(data["n"]),
        source=int(params.get("source", 0)),
        edges=data.get("edges"),
        adj_matrix=data.get("adj_matrix"),
        directed=bool(params.get("directed", False)),
    )
    if params.get("target") is not None:
        target = int(params["target"])
        out["path"] = reconstruct_path(out["prev"], target)
    return out


if __name__ == "__main__":
    # Mock Data：6 个点的无向图
    edges = [
        (0, 1, 7),
        (0, 2, 9),
        (0, 5, 14),
        (1, 2, 10),
        (1, 3, 15),
        (2, 3, 11),
        (2, 5, 2),
        (3, 4, 6),
        (4, 5, 9),
    ]
    out = solve({"n": 6, "edges": edges}, {"source": 0, "target": 4})
    print("dist =", out["dist"])
    print("path 0->4 =", out["path"])

