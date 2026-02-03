# -*- coding: utf-8 -*-
# TSP 启发式求解：最近邻 / 2-opt / 退火（可作为 ACO/GA/PSO 的基线与后处理）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../TSP 相关（鱼群/蚁群/混合粒子群等）
#
# 说明：
# - 这里以“坐标点 -> 欧氏距离”作为默认距离；也支持直接输入距离矩阵
# - 输出 tour 为 0-based 的城市访问顺序（闭环长度按回到起点计算）

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _distance_matrix_from_coords(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    D = np.sqrt(np.sum(diff**2, axis=2))
    return D


def tour_length(tour: np.ndarray, D: np.ndarray) -> float:
    tour = np.asarray(tour, dtype=int).reshape(-1)
    idx_from = tour
    idx_to = np.roll(tour, -1)
    return float(np.sum(D[idx_from, idx_to]))


def nearest_neighbor_tour(D: np.ndarray, *, start: int = 0) -> np.ndarray:
    """最近邻构造初始解。"""
    n = D.shape[0]
    start = int(start)
    visited = np.zeros(n, dtype=bool)
    visited[start] = True
    tour = [start]
    cur = start
    for _ in range(n - 1):
        candidates = np.where(~visited)[0]
        nxt = int(candidates[np.argmin(D[cur, candidates])])
        visited[nxt] = True
        tour.append(nxt)
        cur = nxt
    return np.asarray(tour, dtype=int)


def two_opt(
    tour: np.ndarray,
    D: np.ndarray,
    *,
    max_iter: int = 2000,
) -> np.ndarray:
    """
    2-opt 局部搜索：反转一段子路径以减少长度（TSP 常用）。
    """
    tour = np.asarray(tour, dtype=int).copy()
    n = tour.size
    if n < 4:
        return tour

    best_len = tour_length(tour, D)
    improved = True
    it = 0
    while improved and it < int(max_iter):
        improved = False
        it += 1
        for i in range(1, n - 2):
            for k in range(i + 1, n - 1):
                # 交换边：(i-1,i) + (k,k+1) -> (i-1,k) + (i,k+1)
                a = tour[i - 1]
                b = tour[i]
                c = tour[k]
                d = tour[(k + 1) % n]
                delta = (D[a, c] + D[b, d]) - (D[a, b] + D[c, d])
                if delta < -1e-12:
                    tour[i : k + 1] = tour[i : k + 1][::-1]
                    best_len += float(delta)
                    improved = True
        # 若一轮没有改进则停止
    return tour


@dataclass
class SATSPParams:
    iterations: int = 5000
    T0: float = 1.0
    alpha: float = 0.999
    seed: Optional[int] = 0


def simulated_annealing_tsp(
    tour0: np.ndarray,
    D: np.ndarray,
    *,
    params: Optional[SATSPParams] = None,
) -> Dict[str, Any]:
    """
    TSP 的模拟退火：以 2-opt 作为邻域操作。
    """
    p = params or SATSPParams()
    rng = np.random.default_rng(p.seed)
    tour = np.asarray(tour0, dtype=int).copy()
    n = tour.size
    cur_len = tour_length(tour, D)
    best_tour = tour.copy()
    best_len = cur_len
    T = float(p.T0)
    history_best = []

    for _ in range(int(p.iterations)):
        history_best.append(best_len)

        # 随机选两个位置做 2-opt 反转
        i, k = sorted(rng.choice(np.arange(1, n - 1), size=2, replace=False))
        cand = tour.copy()
        cand[i : k + 1] = cand[i : k + 1][::-1]
        cand_len = tour_length(cand, D)

        delta = cand_len - cur_len
        if delta <= 0:
            accept = True
        else:
            accept = rng.random() < np.exp(-delta / max(T, 1e-12))

        if accept:
            tour = cand
            cur_len = cand_len
            if cur_len < best_len:
                best_len = cur_len
                best_tour = tour.copy()

        T *= float(p.alpha)

    history_best.append(best_len)
    return {"best_tour": best_tour, "best_length": float(best_len), "history_best": np.asarray(history_best)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：TSP 启发式求解。

    Args:
        data: dict，二选一：
            - {'coords': coords}  coords shape=(n,2) 或 (n,d)
            - {'distance_matrix': D} D shape=(n,n)
        params: 参数：
            - method: {'nearest','2opt','sa'}（默认 '2opt'）
            - start: int（最近邻起点，默认 0）
            - two_opt_max_iter: int（默认 2000）
            - sa_params: dict（iterations/T0/alpha/seed）

    Returns:
        dict:
            - best_tour/best_length
            - history_best（若 method='sa'）
            - distance_matrix
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")

    if "distance_matrix" in data and data["distance_matrix"] is not None:
        D = np.asarray(data["distance_matrix"], dtype=float)
    elif "coords" in data and data["coords"] is not None:
        coords = np.asarray(data["coords"], dtype=float)
        if coords.ndim != 2:
            raise ValueError("coords 必须为二维数组 (n×d)。")
        D = _distance_matrix_from_coords(coords)
    else:
        raise ValueError("data 需要提供 distance_matrix 或 coords。")

    if D.ndim != 2 or D.shape[0] != D.shape[1]:
        raise ValueError("distance_matrix 必须为方阵。")
    n = D.shape[0]
    if n < 2:
        raise ValueError("城市数量 n 必须 >= 2。")

    method = str(params.get("method", "2opt")).lower()
    start = int(params.get("start", 0))

    tour0 = nearest_neighbor_tour(D, start=start)
    if method == "nearest":
        best_tour = tour0
        best_len = tour_length(best_tour, D)
        return {"best_tour": best_tour, "best_length": best_len, "distance_matrix": D}

    tour = two_opt(tour0, D, max_iter=int(params.get("two_opt_max_iter", 2000)))
    if method == "2opt":
        best_len = tour_length(tour, D)
        return {"best_tour": tour, "best_length": best_len, "distance_matrix": D}

    if method == "sa":
        sa_cfg = dict(params.get("sa_params", {}) or {})
        sa_params = SATSPParams(
            iterations=int(sa_cfg.get("iterations", 5000)),
            T0=float(sa_cfg.get("T0", 1.0)),
            alpha=float(sa_cfg.get("alpha", 0.999)),
            seed=None if sa_cfg.get("seed") is None else int(sa_cfg.get("seed", 0)),
        )
        out = simulated_annealing_tsp(tour, D, params=sa_params)
        out["distance_matrix"] = D
        return out

    raise ValueError("method 必须为 nearest/2opt/sa 之一。")


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 100, size=(30, 2))

    out1 = solve({"coords": coords}, {"method": "nearest"})
    print("nearest length =", round(out1["best_length"], 3))

    out2 = solve({"coords": coords}, {"method": "2opt"})
    print("2opt length   =", round(out2["best_length"], 3))

    out3 = solve({"coords": coords}, {"method": "sa", "sa_params": {"iterations": 3000, "T0": 5.0, "alpha": 0.999, "seed": 0}})
    print("sa length     =", round(out3["best_length"], 3))

