# -*- coding: utf-8 -*-
# 蚁群算法（ACO）求解 TSP（旅行商问题）：简化实现
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../基于蚁群算法.../TSP...

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


@dataclass
class ACOParams:
    n_ants: int = 30
    iterations: int = 200
    alpha: float = 1.0  # 信息素重要度
    beta: float = 3.0  # 启发函数重要度
    rho: float = 0.5  # 蒸发系数
    Q: float = 1.0  # 信息素增量常数
    seed: Optional[int] = 0
    deposit_best_only: bool = True  # 仅最优蚂蚁增量（更稳定）


def _distance_matrix_from_coords(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    D = np.sqrt(np.sum(diff**2, axis=2))
    return D


def _tour_length(tour: np.ndarray, D: np.ndarray) -> float:
    idx_from = tour
    idx_to = np.roll(tour, -1)
    return float(np.sum(D[idx_from, idx_to]))


def aco_tsp(
    distance_matrix: Union[np.ndarray, Sequence[Sequence[float]]],
    *,
    params: Optional[ACOParams] = None,
) -> Dict[str, Any]:
    """
    蚁群算法求解 TSP（最小化总路程）。

    Args:
        distance_matrix: (n×n) 距离矩阵，主对角线为 0。
        params: ACOParams。

    Returns:
        dict:
            - best_tour: ndarray (n,) 0-based 城市访问顺序
            - best_length: float
            - history_best: ndarray (iterations+1,)
    """
    p = params or ACOParams()
    D = np.asarray(distance_matrix, dtype=float)
    if D.ndim != 2 or D.shape[0] != D.shape[1]:
        raise ValueError("distance_matrix 必须为方阵。")
    n = D.shape[0]
    if n < 2:
        raise ValueError("城市数量 n 必须 >= 2。")
    if np.any(D < 0):
        raise ValueError("距离不能为负。")

    rng = np.random.default_rng(p.seed)
    eta = 1.0 / (D + 1e-12)
    np.fill_diagonal(eta, 0.0)

    tau = np.ones((n, n), dtype=float)
    np.fill_diagonal(tau, 0.0)

    best_tour = None
    best_len = float("inf")
    history_best = []

    for _it in range(int(p.iterations)):
        history_best.append(best_len)

        tours = np.zeros((int(p.n_ants), n), dtype=int)
        lengths = np.zeros(int(p.n_ants), dtype=float)

        for k in range(int(p.n_ants)):
            start = int(rng.integers(0, n))
            visited = np.zeros(n, dtype=bool)
            visited[start] = True
            tour = [start]
            cur = start
            for _step in range(n - 1):
                candidates = np.where(~visited)[0]
                desirability = (tau[cur, candidates] ** float(p.alpha)) * (eta[cur, candidates] ** float(p.beta))
                s = float(np.sum(desirability))
                if s <= 0:
                    # 退化：随机选一个未访问城市
                    nxt = int(rng.choice(candidates))
                else:
                    prob = desirability / s
                    nxt = int(rng.choice(candidates, p=prob))
                visited[nxt] = True
                tour.append(nxt)
                cur = nxt

            tour_arr = np.asarray(tour, dtype=int)
            tours[k, :] = tour_arr
            lengths[k] = _tour_length(tour_arr, D)

        # 更新全局最优
        k_best = int(np.argmin(lengths))
        if float(lengths[k_best]) < best_len:
            best_len = float(lengths[k_best])
            best_tour = tours[k_best].copy()

        # 信息素蒸发
        tau *= (1.0 - float(p.rho))

        # 信息素增量
        if bool(p.deposit_best_only):
            selected = [(best_tour, best_len)]
        else:
            selected = [(tours[i], float(lengths[i])) for i in range(tours.shape[0])]

        for tour_arr, L in selected:
            if tour_arr is None or not np.isfinite(L) or L <= 0:
                continue
            delta = float(p.Q) / L
            for i in range(n):
                a = int(tour_arr[i])
                b = int(tour_arr[(i + 1) % n])
                tau[a, b] += delta
                tau[b, a] += delta

    history_best.append(best_len)
    return {"best_tour": best_tour, "best_length": best_len, "history_best": np.asarray(history_best), "pheromone": tau}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：ACO 求解 TSP。

    Args:
        data: dict，二选一：
            - {'distance_matrix': D}
            - {'coords': coords} 其中 coords shape=(n,2) 或 (n,dim)
        params: ACO 参数（同 ACOParams 字段）。

    Returns:
        dict: 见 aco_tsp() 返回值。
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

    aco_params = ACOParams(
        n_ants=int(params.get("n_ants", 30)),
        iterations=int(params.get("iterations", 200)),
        alpha=float(params.get("alpha", 1.0)),
        beta=float(params.get("beta", 3.0)),
        rho=float(params.get("rho", 0.5)),
        Q=float(params.get("Q", 1.0)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
        deposit_best_only=bool(params.get("deposit_best_only", True)),
    )
    return aco_tsp(D, params=aco_params)


if __name__ == "__main__":
    # Mock Data：随机 20 个城市平面坐标
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 100, size=(20, 2))
    out = solve({"coords": coords}, {"n_ants": 40, "iterations": 200, "seed": 0})
    print("best_length =", round(out["best_length"], 3))
    print("best_tour (0-based) =", out["best_tour"][:10], "...")

