# -*- coding: utf-8 -*-
# NSGA-II：多目标优化的经典算法（简化实现，连续变量）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../多目标快速非支配排序遗传算法优化代码/nsga_2.m

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Objective = Callable[[np.ndarray], Sequence[float]]


@dataclass
class NSGA2Params:
    pop_size: int = 100
    generations: int = 200
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    mutation_sigma: float = 0.1
    seed: Optional[int] = 0
    elitism: bool = True  # 环境选择本身就是精英策略


def _init_pop(rng: np.random.Generator, bounds: np.ndarray, pop_size: int) -> np.ndarray:
    low, high = bounds[:, 0], bounds[:, 1]
    return rng.uniform(low, high, size=(pop_size, bounds.shape[0]))


def _clip(x: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    return np.clip(x, bounds[:, 0], bounds[:, 1])


def _evaluate(pop: np.ndarray, objective: Objective) -> np.ndarray:
    F = np.array([np.asarray(objective(x), dtype=float) for x in pop], dtype=float)
    if F.ndim != 2:
        raise ValueError("objective(x) 必须返回一维目标向量。")
    return F


def _dominates(a: np.ndarray, b: np.ndarray) -> bool:
    # 最小化：a 支配 b <=> a 在所有目标上不差且至少一个更好
    return np.all(a <= b) and np.any(a < b)


def non_dominated_sort(F: np.ndarray) -> Tuple[List[List[int]], np.ndarray]:
    """
    快速非支配排序。

    Args:
        F: 目标值矩阵 (N×M)。

    Returns:
        (fronts, rank)
        - fronts: list of fronts，每个 front 是个体索引列表（从 0 开始）
        - rank: (N,) 每个个体的等级（front0=0）
    """
    N = F.shape[0]
    S = [[] for _ in range(N)]  # S[p]：p 支配的集合
    n_dom = np.zeros(N, dtype=int)  # 被支配数量
    rank = np.full(N, -1, dtype=int)

    fronts: List[List[int]] = [[]]
    for p in range(N):
        for q in range(N):
            if p == q:
                continue
            if _dominates(F[p], F[q]):
                S[p].append(q)
            elif _dominates(F[q], F[p]):
                n_dom[p] += 1
        if n_dom[p] == 0:
            rank[p] = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in S[p]:
                n_dom[q] -= 1
                if n_dom[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
    fronts.pop()  # 移除最后一个空 front
    return fronts, rank


def crowding_distance(F: np.ndarray, front: Sequence[int]) -> np.ndarray:
    """
    拥挤距离（越大越优先保留多样性）。

    Args:
        F: (N×M)
        front: 当前 front 的索引集合

    Returns:
        (len(front),) 的拥挤距离
    """
    front = list(front)
    if len(front) == 0:
        return np.array([], dtype=float)
    M = F.shape[1]
    dist = np.zeros(len(front), dtype=float)
    fvals = F[front, :]

    for m in range(M):
        order = np.argsort(fvals[:, m])
        dist[order[0]] = np.inf
        dist[order[-1]] = np.inf
        fmin = float(fvals[order[0], m])
        fmax = float(fvals[order[-1], m])
        if fmax - fmin < 1e-12:
            continue
        for i in range(1, len(front) - 1):
            dist[order[i]] += (fvals[order[i + 1], m] - fvals[order[i - 1], m]) / (fmax - fmin)
    return dist


def _tournament_select(rng: np.random.Generator, rank: np.ndarray, crowd: np.ndarray) -> int:
    """二元锦标赛：先比 rank，再比 crowd（更大更好）。"""
    i, j = rng.integers(0, rank.size, size=2)
    if rank[i] < rank[j]:
        return int(i)
    if rank[j] < rank[i]:
        return int(j)
    # rank 相同，比拥挤距离
    return int(i) if crowd[i] > crowd[j] else int(j)


def _blend_crossover(rng: np.random.Generator, p1: np.ndarray, p2: np.ndarray, alpha: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    cmin = np.minimum(p1, p2)
    cmax = np.maximum(p1, p2)
    d = cmax - cmin
    low = cmin - alpha * d
    high = cmax + alpha * d
    return rng.uniform(low, high), rng.uniform(low, high)


def _mutate_gaussian(rng: np.random.Generator, x: np.ndarray, sigma: float, rate: float) -> np.ndarray:
    out = x.copy()
    mask = rng.random(out.size) < rate
    out[mask] = out[mask] + rng.normal(0.0, sigma, size=int(mask.sum()))
    return out


def nsga2(
    objective: Objective,
    bounds: Sequence[Tuple[float, float]],
    *,
    params: Optional[NSGA2Params] = None,
) -> Dict[str, Any]:
    """
    NSGA-II 多目标优化（最小化）。

    Args:
        objective: 目标函数，返回多个目标值（list/tuple/ndarray）。
        bounds: 变量边界。
        params: NSGA2Params。

    Returns:
        dict:
            - X: 最终种群 (N×d)
            - F: 最终目标值 (N×M)
            - fronts: 非支配分层
            - pareto_idx: 第一层（Pareto 前沿）索引
            - pareto_X/pareto_F: 第一层解集
    """
    p = params or NSGA2Params()
    bounds_arr = np.asarray(list(bounds), dtype=float)
    if bounds_arr.ndim != 2 or bounds_arr.shape[1] != 2:
        raise ValueError("bounds 必须为 (d×2)。")
    if np.any(bounds_arr[:, 0] >= bounds_arr[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")

    rng = np.random.default_rng(p.seed)
    X = _init_pop(rng, bounds_arr, int(p.pop_size))
    F = _evaluate(X, objective)
    N = X.shape[0]

    for _gen in range(int(p.generations)):
        fronts, rank = non_dominated_sort(F)

        # 计算每个个体的 crowding（对不同 front 分别计算，然后写回）
        crowd = np.zeros(N, dtype=float)
        for fr in fronts:
            cd = crowding_distance(F, fr)
            crowd[np.asarray(fr, dtype=int)] = cd

        # 生成子代
        children = []
        while len(children) < N:
            i1 = _tournament_select(rng, rank, crowd)
            i2 = _tournament_select(rng, rank, crowd)
            p1, p2 = X[i1], X[i2]

            if rng.random() < float(p.crossover_rate):
                c1, c2 = _blend_crossover(rng, p1, p2, alpha=0.5)
            else:
                c1, c2 = p1.copy(), p2.copy()

            sigma = float(p.mutation_sigma) * (bounds_arr[:, 1] - bounds_arr[:, 0])
            c1 = _mutate_gaussian(rng, c1, sigma=float(np.mean(sigma)), rate=float(p.mutation_rate))
            c2 = _mutate_gaussian(rng, c2, sigma=float(np.mean(sigma)), rate=float(p.mutation_rate))
            c1 = _clip(c1, bounds_arr)
            c2 = _clip(c2, bounds_arr)
            children.append(c1)
            if len(children) < N:
                children.append(c2)

        Xc = np.asarray(children, dtype=float)
        Fc = _evaluate(Xc, objective)

        # 合并父代+子代，做环境选择
        X_all = np.vstack([X, Xc])
        F_all = np.vstack([F, Fc])
        fronts_all, _rank_all = non_dominated_sort(F_all)

        new_idx = []
        for fr in fronts_all:
            if len(new_idx) + len(fr) <= N:
                new_idx.extend(fr)
            else:
                # 根据 crowding distance 选够 N 个
                cd = crowding_distance(F_all, fr)
                fr = np.asarray(fr, dtype=int)
                order = np.argsort(-cd)  # 大的优先
                need = N - len(new_idx)
                new_idx.extend(fr[order[:need]].tolist())
                break

        new_idx = np.asarray(new_idx, dtype=int)
        X = X_all[new_idx]
        F = F_all[new_idx]

    fronts, _ = non_dominated_sort(F)
    pareto_idx = np.asarray(fronts[0], dtype=int) if fronts else np.array([], dtype=int)
    return {
        "X": X,
        "F": F,
        "fronts": fronts,
        "pareto_idx": pareto_idx,
        "pareto_X": X[pareto_idx] if pareto_idx.size else np.empty((0, X.shape[1])),
        "pareto_F": F[pareto_idx] if pareto_idx.size else np.empty((0, F.shape[1])),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：NSGA-II 多目标优化。

    Args:
        data: dict，包含：
            - objective: callable，返回多目标值
            - bounds: list[(low,high)]
        params: NSGA2Params 字段。

    Returns:
        dict: nsga2() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "bounds" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 bounds。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    nsga_params = NSGA2Params(
        pop_size=int(params.get("pop_size", 100)),
        generations=int(params.get("generations", 200)),
        crossover_rate=float(params.get("crossover_rate", 0.9)),
        mutation_rate=float(params.get("mutation_rate", 0.1)),
        mutation_sigma=float(params.get("mutation_sigma", 0.1)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )
    return nsga2(objective, data["bounds"], params=nsga_params)


if __name__ == "__main__":
    # Mock Data：ZDT1（经典 2 目标测试函数），d=30
    def zdt1(x: np.ndarray) -> Sequence[float]:
        f1 = float(x[0])
        g = 1.0 + 9.0 * float(np.mean(x[1:]))
        h = 1.0 - np.sqrt(f1 / g)
        f2 = g * h
        return [f1, f2]

    bounds = [(0.0, 1.0)] * 30
    out = solve({"objective": zdt1, "bounds": bounds}, {"pop_size": 120, "generations": 200, "seed": 0})
    print("pareto size =", int(out["pareto_F"].shape[0]))
    print("pareto_F head =\\n", np.round(out["pareto_F"][:5], 4))

