# -*- coding: utf-8 -*-
# A* 算法：栅格路径规划（支持 4/8 邻域）
#
# 适用场景：二维地图/占用栅格（0 可通行，1 障碍），求最短（或近似最短）路径
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../二维路径规划相关（Dijkstra/蚁群等）

from __future__ import annotations

import heapq
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Coord = Tuple[int, int]


def _heuristic(a: Coord, b: Coord, kind: str) -> float:
    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    kind = str(kind).lower()
    if kind in {"manhattan", "l1"}:
        return float(dr + dc)
    if kind in {"euclidean", "l2"}:
        return float(np.hypot(dr, dc))
    raise ValueError("heuristic 必须为 manhattan 或 euclidean。")


def astar_grid(
    grid: Union[np.ndarray, List[List[int]]],
    *,
    start: Coord,
    goal: Coord,
    allow_diagonal: bool = False,
    heuristic: str = "manhattan",
) -> Dict[str, Any]:
    """
    A* 栅格最短路。

    Args:
        grid: (H×W) 数组，0 表示可通行，1 表示障碍（非 0 也可视为障碍）。
        start: (r,c) 起点。
        goal: (r,c) 终点。
        allow_diagonal: 是否允许对角移动（8 邻域）。
        heuristic: 启发函数（manhattan/euclidean）。

    Returns:
        dict:
            - path: list[(r,c)]，从 start 到 goal；若不可达为空列表
            - cost: 路径代价（不可达为 inf）
            - visited: 访问过的节点数（pop 出队次数）
    """
    G = np.asarray(grid, dtype=int)
    if G.ndim != 2:
        raise ValueError("grid 必须为二维数组。")
    H, W = G.shape

    def in_bounds(p: Coord) -> bool:
        return 0 <= p[0] < H and 0 <= p[1] < W

    def passable(p: Coord) -> bool:
        return int(G[p[0], p[1]]) == 0

    if not in_bounds(start) or not in_bounds(goal):
        raise ValueError("start/goal 必须在网格范围内。")
    if not passable(start) or not passable(goal):
        return {"path": [], "cost": float("inf"), "visited": 0}

    if allow_diagonal:
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    else:
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def step_cost(dr: int, dc: int) -> float:
        return float(np.hypot(dr, dc))

    # A*：f = g + h
    g_score = {start: 0.0}
    came_from: Dict[Coord, Coord] = {}

    pq: List[Tuple[float, Coord]] = []
    heapq.heappush(pq, (_heuristic(start, goal, heuristic), start))

    visited = 0
    closed = set()

    while pq:
        _, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        visited += 1
        if cur == goal:
            break
        closed.add(cur)

        cur_g = g_score[cur]
        for dr, dc in neighbors:
            nxt = (cur[0] + dr, cur[1] + dc)
            if not in_bounds(nxt) or not passable(nxt):
                continue
            tentative_g = cur_g + step_cost(dr, dc)
            if tentative_g < g_score.get(nxt, float("inf")):
                came_from[nxt] = cur
                g_score[nxt] = tentative_g
                f = tentative_g + _heuristic(nxt, goal, heuristic)
                heapq.heappush(pq, (f, nxt))

    if goal not in g_score:
        return {"path": [], "cost": float("inf"), "visited": visited}

    # 重建路径
    path: List[Coord] = [goal]
    cur = goal
    while cur != start:
        cur = came_from[cur]
        path.append(cur)
    path.reverse()
    return {"path": path, "cost": float(g_score[goal]), "visited": visited}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：A* 栅格路径规划。

    Args:
        data: dict，包含：
            - grid: 2D
            - start: (r,c)
            - goal: (r,c)
        params: 参数：
            - allow_diagonal: bool（默认 False）
            - heuristic: 'manhattan' | 'euclidean'

    Returns:
        dict: 见 astar_grid()。
    """
    params = params or {}
    if not isinstance(data, dict) or "grid" not in data or "start" not in data or "goal" not in data:
        raise TypeError("data 必须为 dict，且包含 grid/start/goal。")
    return astar_grid(
        data["grid"],
        start=tuple(data["start"]),
        goal=tuple(data["goal"]),
        allow_diagonal=bool(params.get("allow_diagonal", False)),
        heuristic=str(params.get("heuristic", "manhattan")),
    )


if __name__ == "__main__":
    # Mock Data：简单迷宫
    grid = np.array(
        [
            [0, 0, 0, 0, 0],
            [1, 1, 0, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 1, 1, 0, 0],
            [0, 0, 0, 0, 0],
        ],
        dtype=int,
    )
    out = solve({"grid": grid, "start": (0, 0), "goal": (4, 4)}, {"allow_diagonal": False})
    print("cost =", out["cost"])
    print("path =", out["path"])

