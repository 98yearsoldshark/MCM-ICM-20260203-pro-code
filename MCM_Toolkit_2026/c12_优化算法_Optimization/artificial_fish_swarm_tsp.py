# -*- coding: utf-8 -*-
# 人工鱼群算法（AFSA）求解 TSP（离散版本，基于资料中的 Matlab 实现）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/.../人工鱼群求解TSP问题源代码/*.m
#
# 说明：
# - 该实现尽量复刻资料中的“追尾/觅食/聚群/随机移动”四种行为与邻域距离定义
# - 与常见 2-opt/ACO/GA 不同：这里的“视野 Visual”对应的是“路径汉明距离阈值”
# - 适合：想快速试一个“不同于 GA/PSO/ACO 的离散群智能”做 TSP 基线/对照实验

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class AFSAParams:
    fish_num: int = 10
    max_iter: int = 200
    try_number: int = 500
    visual: int = 16
    delta: float = 0.8  # 拥挤度因子（邻域鱼数 / 总鱼数 < delta 才允许追随/聚群）
    seed: Optional[int] = 0


def _pairwise_distance_matrix(coords: np.ndarray) -> np.ndarray:
    coords = np.asarray(coords, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("coords 必须为 (n,2)。")
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def _path_length(D: np.ndarray, route: np.ndarray) -> float:
    route = np.asarray(route, dtype=int).reshape(-1)
    n = int(route.size)
    if D.shape != (n, n):
        raise ValueError("D 的形状必须为 (n,n)，n 等于 route 长度。")
    # 闭环：最后回到起点
    idx1 = route
    idx2 = np.roll(route, -1)
    return float(np.sum(D[idx1, idx2]))


def _route_distance(route1: np.ndarray, route2: np.ndarray) -> int:
    # 资料里的 distance.m：对应位置城市编号不同的个数（汉明距离）
    return int(np.sum(np.asarray(route1, dtype=int) != np.asarray(route2, dtype=int)))


def _k_neighborhood(routes: np.ndarray, i: int, visual: int) -> np.ndarray:
    Xi = routes[i]
    dist = np.sum(routes != Xi, axis=1)
    mask = (dist < int(visual)) & (np.arange(routes.shape[0]) != int(i))
    return routes[mask]


def _center_route(neighbors: np.ndarray, rng: np.random.Generator) -> Optional[np.ndarray]:
    if neighbors.size == 0:
        return None
    n_city = int(neighbors.shape[1])
    center: list[int] = []
    for j in range(n_city):
        candidates = neighbors[:, j].astype(int).tolist()
        # 模拟 Matlab 版本：优先选“该位置出现次数最多”的城市；并避免重复
        while candidates:
            vals, counts = np.unique(candidates, return_counts=True)
            pick = int(vals[int(np.argmax(counts))])
            if j == 0:
                center.append(pick)
                break
            if pick not in center:
                center.append(pick)
                break
            # 若重复，则移除该值后继续找次优，避免重复走同一个城市
            candidates = [v for v in candidates if v != pick]
        if len(center) == j:  # 没有可选（或都重复），随机补一个未出现的城市
            unused = [c for c in range(n_city) if c not in center]
            if not unused:
                # 理论上不应发生；兜底：返回 None 触发觅食行为
                return None
            center.append(int(rng.choice(unused)))
    return np.asarray(center, dtype=int)


def _prey(route: np.ndarray, D: np.ndarray, *, try_number: int, visual: int, rng: np.random.Generator) -> Tuple[np.ndarray, bool]:
    # 资料里的 AF_prey.m：随机选 DJ 个位置做“循环移位”，若变好则返回
    Xi = route.copy()
    Yi = _path_length(D, Xi)
    n_city = int(Xi.size)
    max_dj = int(min(max(1, visual), max(1, n_city - 1)))
    for _ in range(int(try_number)):
        dj = int(rng.integers(1, max_dj + 1))
        # Matlab 版本排除了第 1 个位置（1-based），即排除 route[0]
        positions = rng.choice(np.arange(1, n_city), size=dj, replace=False)
        X_try = Xi.copy()
        t = int(X_try[positions[0]])
        for k in range(dj - 1):
            X_try[positions[k]] = X_try[positions[k + 1]]
        X_try[positions[-1]] = t
        if _path_length(D, X_try) < Yi:
            return X_try, True
    return Xi, False


def _follow(
    routes: np.ndarray,
    i: int,
    D: np.ndarray,
    *,
    visual: int,
    delta: float,
    try_number: int,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, bool]:
    Xi = routes[i]
    Yi = _path_length(D, Xi)
    neighbors = _k_neighborhood(routes, i, visual=int(visual))
    nf = int(neighbors.shape[0])
    N = int(routes.shape[0])
    if nf == 0:
        return _prey(Xi, D, try_number=int(try_number), visual=int(visual), rng=rng)
    # 找邻域中最优路径
    y_neighbors = np.array([_path_length(D, r) for r in neighbors], dtype=float)
    best_idx = int(np.argmin(y_neighbors))
    Xmin = neighbors[best_idx].copy()
    Ymin = float(y_neighbors[best_idx])
    if (Ymin < Yi) and (nf / max(1, N) < float(delta)):
        return Xmin, True
    return _prey(Xi, D, try_number=int(try_number), visual=int(visual), rng=rng)


def _swarm(
    routes: np.ndarray,
    i: int,
    D: np.ndarray,
    *,
    visual: int,
    delta: float,
    try_number: int,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, bool]:
    Xi = routes[i]
    Yi = _path_length(D, Xi)
    neighbors = _k_neighborhood(routes, i, visual=int(visual))
    nf = int(neighbors.shape[0])
    N = int(routes.shape[0])
    Xc = _center_route(neighbors, rng=rng)
    if Xc is None:
        return _prey(Xi, D, try_number=int(try_number), visual=int(visual), rng=rng)
    Yc = _path_length(D, Xc)
    if (Yc < Yi) and (nf / max(1, N) < float(delta)):
        return Xc, True
    return _prey(Xi, D, try_number=int(try_number), visual=int(visual), rng=rng)


def _move_strategy(
    routes: np.ndarray,
    i: int,
    D: np.ndarray,
    *,
    visual: int,
    delta: float,
    try_number: int,
    rng: np.random.Generator,
) -> np.ndarray:
    # 资料里的 AF_movestrategy.m：追尾 -> 觅食 -> 聚群 -> 随机
    Xinext, ok = _follow(routes, i, D, visual=int(visual), delta=float(delta), try_number=int(try_number), rng=rng)
    if ok:
        return Xinext
    Xinext, ok = _prey(routes[i], D, try_number=int(try_number), visual=int(visual), rng=rng)
    if ok:
        return Xinext
    Xinext, ok = _swarm(routes, i, D, visual=int(visual), delta=float(delta), try_number=int(try_number), rng=rng)
    if ok:
        return Xinext
    # 随机移动
    return rng.permutation(routes.shape[1]).astype(int)


def artificial_fish_swarm_tsp(
    D: np.ndarray,
    *,
    params: Optional[AFSAParams] = None,
) -> Dict[str, Any]:
    """
    人工鱼群算法求解 TSP（最小化总路程）。

    Args:
        D: (n,n) 距离矩阵。
        params: AFSAParams。

    Returns:
        dict:
            - best_route: (n,) 0-based 城市序列（闭环请自行回到起点）
            - best_length: float
            - history_best: (max_iter,) 每次迭代最优长度
    """
    p = params or AFSAParams()
    D = np.asarray(D, dtype=float)
    if D.ndim != 2 or D.shape[0] != D.shape[1]:
        raise ValueError("D 必须为方阵 (n,n)。")
    n_city = int(D.shape[0])

    rng = np.random.default_rng(p.seed)

    fish_num = int(max(2, p.fish_num))
    routes = np.vstack([rng.permutation(n_city) for _ in range(fish_num)]).astype(int)

    curr_len = np.array([_path_length(D, r) for r in routes], dtype=float)
    best_idx = int(np.argmin(curr_len))
    best_route = routes[best_idx].copy()
    best_len = float(curr_len[best_idx])

    history_best = np.zeros(int(p.max_iter), dtype=float)
    for it in range(int(p.max_iter)):
        for i in range(fish_num):
            routes[i] = _move_strategy(
                routes,
                i,
                D,
                visual=int(p.visual),
                delta=float(p.delta),
                try_number=int(p.try_number),
                rng=rng,
            )

        curr_len = np.array([_path_length(D, r) for r in routes], dtype=float)
        gen_best_idx = int(np.argmin(curr_len))
        gen_best_len = float(curr_len[gen_best_idx])
        if gen_best_len < best_len:
            best_len = gen_best_len
            best_route = routes[gen_best_idx].copy()
        history_best[it] = best_len

    return {"best_route": best_route, "best_length": best_len, "history_best": history_best}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：人工鱼群算法求解 TSP（最小化路径长度）。

    Args:
        data: dict，包含：
            - coords: (n,2) 坐标（可选）
            - distance_matrix: (n,n) 距离矩阵（可选）
            二者至少提供其一；若同时提供，优先 distance_matrix。
        params: AFSAParams 字段：
            - fish_num, max_iter, try_number, visual, delta, seed

    Returns:
        dict: artificial_fish_swarm_tsp() 的返回值
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")
    if "distance_matrix" in data and data["distance_matrix"] is not None:
        D = np.asarray(data["distance_matrix"], dtype=float)
    elif "coords" in data and data["coords"] is not None:
        D = _pairwise_distance_matrix(np.asarray(data["coords"], dtype=float))
    else:
        raise TypeError("data 必须包含 distance_matrix 或 coords。")

    p = AFSAParams(
        fish_num=int(params.get("fish_num", 10)),
        max_iter=int(params.get("max_iter", 200)),
        try_number=int(params.get("try_number", 500)),
        visual=int(params.get("visual", 16)),
        delta=float(params.get("delta", 0.8)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )
    return artificial_fish_swarm_tsp(D, params=p)


if __name__ == "__main__":
    # Mock Data：随机坐标 TSP（不画图，仅输出最优长度）
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 100, size=(22, 2))
    out = solve({"coords": coords}, {"fish_num": 12, "max_iter": 60, "try_number": 200, "visual": 10, "delta": 0.8, "seed": 0})
    print("best_length =", round(float(out["best_length"]), 4))
    print("best_route (1-based) =", (out["best_route"] + 1).tolist())

