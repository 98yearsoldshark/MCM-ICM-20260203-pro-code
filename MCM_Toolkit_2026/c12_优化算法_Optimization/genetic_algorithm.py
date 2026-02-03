# -*- coding: utf-8 -*-
# 遗传算法（GA）：连续变量全局优化（简化、可直接改）
#
# 参考来源（资料目录，Matlab 版本较多）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../GA*.m

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Objective = Callable[[np.ndarray], float]


@dataclass
class GAParams:
    pop_size: int = 50
    generations: int = 200
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    mutation_sigma: float = 0.1
    tournament_k: int = 3
    elitism: int = 1
    seed: Optional[int] = 0


def _init_population(rng: np.random.Generator, bounds: np.ndarray, pop_size: int) -> np.ndarray:
    low = bounds[:, 0]
    high = bounds[:, 1]
    return rng.uniform(low, high, size=(pop_size, bounds.shape[0]))


def _tournament_select(rng: np.random.Generator, fitness: np.ndarray, k: int) -> int:
    idx = rng.integers(0, fitness.size, size=k)
    best = idx[np.argmin(fitness[idx])]  # 目标是最小化
    return int(best)


def _blend_crossover(rng: np.random.Generator, p1: np.ndarray, p2: np.ndarray, alpha: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    # BLX-alpha：在 [min-αd, max+αd] 区间采样
    cmin = np.minimum(p1, p2)
    cmax = np.maximum(p1, p2)
    d = cmax - cmin
    low = cmin - alpha * d
    high = cmax + alpha * d
    c1 = rng.uniform(low, high)
    c2 = rng.uniform(low, high)
    return c1, c2


def _mutate_gaussian(rng: np.random.Generator, x: np.ndarray, sigma: float, mutation_rate: float) -> np.ndarray:
    out = x.copy()
    mask = rng.random(out.size) < mutation_rate
    out[mask] = out[mask] + rng.normal(0.0, sigma, size=int(mask.sum()))
    return out


def _clip_bounds(x: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    return np.clip(x, bounds[:, 0], bounds[:, 1])


def genetic_algorithm(
    objective: Objective,
    bounds: Sequence[Tuple[float, float]],
    *,
    params: Optional[GAParams] = None,
) -> Dict[str, Any]:
    """
    GA 连续优化（最小化）。

    Args:
        objective: 目标函数 f(x)->float（越小越好）。
        bounds: 变量边界 [(low,high), ...]。
        params: GAParams。

    Returns:
        dict:
            - x_best, f_best
            - history_best: 每代最优值
            - history_mean: 每代均值
    """
    p = params or GAParams()
    bounds_arr = np.asarray(list(bounds), dtype=float)
    if bounds_arr.ndim != 2 or bounds_arr.shape[1] != 2:
        raise ValueError("bounds 必须为 (d×2)。")
    if np.any(bounds_arr[:, 0] >= bounds_arr[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")
    d = bounds_arr.shape[0]

    rng = np.random.default_rng(p.seed)
    pop = _init_population(rng, bounds_arr, int(p.pop_size))

    history_best: List[float] = []
    history_mean: List[float] = []

    def eval_pop(Pop: np.ndarray) -> np.ndarray:
        return np.array([float(objective(ind)) for ind in Pop], dtype=float)

    fitness = eval_pop(pop)
    best_idx = int(np.argmin(fitness))
    x_best = pop[best_idx].copy()
    f_best = float(fitness[best_idx])

    for _gen in range(int(p.generations)):
        # 记录
        history_best.append(float(np.min(fitness)))
        history_mean.append(float(np.mean(fitness)))

        # 精英保留
        elite_n = int(max(0, p.elitism))
        elite_idx = np.argsort(fitness)[:elite_n]
        elites = pop[elite_idx].copy()

        # 生成下一代
        new_pop = []
        while len(new_pop) < int(p.pop_size) - elite_n:
            i1 = _tournament_select(rng, fitness, int(p.tournament_k))
            i2 = _tournament_select(rng, fitness, int(p.tournament_k))
            p1, p2 = pop[i1], pop[i2]

            if rng.random() < float(p.crossover_rate):
                c1, c2 = _blend_crossover(rng, p1, p2, alpha=0.5)
            else:
                c1, c2 = p1.copy(), p2.copy()

            c1 = _mutate_gaussian(rng, c1, sigma=float(p.mutation_sigma), mutation_rate=float(p.mutation_rate))
            c2 = _mutate_gaussian(rng, c2, sigma=float(p.mutation_sigma), mutation_rate=float(p.mutation_rate))
            c1 = _clip_bounds(c1, bounds_arr)
            c2 = _clip_bounds(c2, bounds_arr)

            new_pop.append(c1)
            if len(new_pop) < int(p.pop_size) - elite_n:
                new_pop.append(c2)

        pop = np.vstack([elites, np.asarray(new_pop, dtype=float)]) if elite_n > 0 else np.asarray(new_pop, dtype=float)
        fitness = eval_pop(pop)

        # 更新全局最优
        gen_best_idx = int(np.argmin(fitness))
        gen_best = float(fitness[gen_best_idx])
        if gen_best < f_best:
            f_best = gen_best
            x_best = pop[gen_best_idx].copy()

    # 最后一代记录
    history_best.append(float(np.min(fitness)))
    history_mean.append(float(np.mean(fitness)))

    return {"x_best": x_best, "f_best": f_best, "history_best": np.asarray(history_best), "history_mean": np.asarray(history_mean)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：GA 优化（最小化）。

    Args:
        data: dict，包含：
            - objective: callable
            - bounds: list[(low,high)]
        params: GA 参数（同 GAParams 字段）。

    Returns:
        dict: genetic_algorithm() 的返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "bounds" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 bounds。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    ga_params = GAParams(
        pop_size=int(params.get("pop_size", 50)),
        generations=int(params.get("generations", 200)),
        crossover_rate=float(params.get("crossover_rate", 0.9)),
        mutation_rate=float(params.get("mutation_rate", 0.1)),
        mutation_sigma=float(params.get("mutation_sigma", 0.1)),
        tournament_k=int(params.get("tournament_k", 3)),
        elitism=int(params.get("elitism", 1)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )
    return genetic_algorithm(objective, data["bounds"], params=ga_params)


if __name__ == "__main__":
    # Mock Data：Sphere 函数最小化（最优 0）
    def sphere(x: np.ndarray) -> float:
        return float(np.sum(x**2))

    bounds = [(-5, 5)] * 5
    out = solve({"objective": sphere, "bounds": bounds}, {"pop_size": 60, "generations": 150, "seed": 0})
    print("f_best =", out["f_best"])
    print("x_best =", np.round(out["x_best"], 4))

