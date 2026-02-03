# -*- coding: utf-8 -*-
# 免疫算法（免疫遗传算法 IGA / Immune GA）：带“浓度抑制 + 记忆库”的组合优化
#
# 参考来源（资料目录，Matlab 版本偏“免疫+遗传”融合）：
# - 6、按赛题类别划分的常用算法代码/.../免疫优化算法在物流配送中心选址中的应用代码/*.m
#
# 说明：
# - 这里实现的是“免疫遗传算法”风格：适应度 + 浓度(相似度) -> excellence -> 选择/交叉/变异
# - 支持二进制决策向量；可通过 n_ones 约束实现“从 n 个点里选 k 个点”的选址/选点问题
# - 默认最小化 objective；若要最大化可设置 params['maximize']=True

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


BinaryObjective = Callable[[np.ndarray], float]
BinaryPredicate = Callable[[np.ndarray], bool]
BinaryRepair = Callable[[np.ndarray], np.ndarray]


@dataclass
class ImmuneGAParams:
    pop_size: int = 50
    memory_size: int = 10
    generations: int = 100
    pcross: float = 0.5
    pmutation: float = 0.4
    ps: float = 0.95  # 多样性评价参数：越大越偏向“适应度”，越小越偏向“抑制相似个体”
    similarity_threshold: float = 0.7  # 相似度阈值：>threshold 计入浓度
    elitism: int = 3  # 精英保留：直接按适应度保留的个数
    seed: Optional[int] = 0
    maximize: bool = False


def _repair_n_ones(x: np.ndarray, n_ones: int, rng: np.random.Generator) -> np.ndarray:
    x = x.astype(np.int8, copy=True)
    n_bits = int(x.size)
    k = int(n_ones)
    if k < 0 or k > n_bits:
        raise ValueError("n_ones 必须在 [0, n_bits]。")
    ones = np.flatnonzero(x == 1)
    zeros = np.flatnonzero(x == 0)
    if ones.size > k:
        drop = rng.choice(ones, size=int(ones.size - k), replace=False)
        x[drop] = 0
    elif ones.size < k:
        add = rng.choice(zeros, size=int(k - ones.size), replace=False)
        x[add] = 1
    return x


def _init_population(
    rng: np.random.Generator,
    n: int,
    n_bits: int,
    *,
    n_ones: Optional[int],
    valid: Optional[BinaryPredicate],
    repair: Optional[BinaryRepair],
) -> np.ndarray:
    pop = np.zeros((int(n), int(n_bits)), dtype=np.int8)
    for i in range(int(n)):
        for _ in range(2000):
            if n_ones is None:
                x = (rng.random(n_bits) < 0.5).astype(np.int8)
            else:
                x = np.zeros(n_bits, dtype=np.int8)
                idx = rng.choice(n_bits, size=int(n_ones), replace=False)
                x[idx] = 1
            if repair is not None:
                x = np.asarray(repair(x), dtype=np.int8).reshape(-1)
            if n_ones is not None:
                x = _repair_n_ones(x, int(n_ones), rng=rng)
            if valid is None or bool(valid(x)):
                pop[i] = x
                break
        else:
            # 兜底：直接放一个随机解（即便不满足 valid），避免死循环
            pop[i] = x
    return pop


def _similarity_matrix(pop: np.ndarray, *, n_ones: Optional[int]) -> np.ndarray:
    # pop: (M, n_bits) 0/1
    P = pop.astype(np.int16)
    inter = P @ P.T  # 共享 1 的数量
    if n_ones is not None:
        denom = float(max(1, int(n_ones)))
        return inter.astype(float) / denom
    # Jaccard：|A∩B| / |A∪B|
    ones = np.sum(P, axis=1, keepdims=True).astype(float)
    union = ones + ones.T - inter
    return inter.astype(float) / np.maximum(1.0, union)


def _concentration(sim: np.ndarray, threshold: float) -> np.ndarray:
    # 资料 concentration.m：对每个体统计“与他人相似度 > 阈值”的比例
    M = sim.shape[0]
    cnt = np.sum(sim > float(threshold), axis=1)
    return cnt.astype(float) / float(max(1, M))


def _fitness_to_score(fitness: np.ndarray, *, maximize: bool) -> np.ndarray:
    f = np.asarray(fitness, dtype=float).reshape(-1)
    fmin = float(np.min(f))
    fmax = float(np.max(f))
    denom = fmax - fmin
    eps = 1e-12
    if denom <= 0:
        return np.ones_like(f) * (1.0 / f.size)
    if maximize:
        score = (f - fmin) / (denom + eps)
    else:
        score = (fmax - f) / (denom + eps)
    return score + eps


def _excellence(fitness: np.ndarray, concentration: np.ndarray, *, ps: float, maximize: bool) -> np.ndarray:
    # 参考 excellence.m：fit 部分越大越好；浓度越大越差；ps 控制权重
    fit_score = _fitness_to_score(fitness, maximize=maximize)
    fit_score = fit_score / float(np.sum(fit_score))

    con = np.asarray(concentration, dtype=float).reshape(-1)
    con_sum = float(np.sum(con))
    if con_sum <= 0:
        con_score = np.zeros_like(con)
    else:
        con_score = con / con_sum

    ps = float(ps)
    return ps * fit_score - (1.0 - ps) * con_score


def _best_select(
    pop: np.ndarray,
    fitness: np.ndarray,
    excellence: np.ndarray,
    *,
    n_select: int,
    elitism: int,
    maximize: bool,
) -> np.ndarray:
    n_select = int(n_select)
    elitism = int(max(0, elitism))
    if n_select <= 0:
        raise ValueError("n_select 必须为正整数。")
    if pop.shape[0] < n_select:
        raise ValueError("pop 的个体数量不足。")

    # 精英：按适应度硬保留
    if maximize:
        elite_idx = np.argsort(-fitness)[: min(elitism, n_select)]
    else:
        elite_idx = np.argsort(fitness)[: min(elitism, n_select)]

    chosen = list(map(int, elite_idx.tolist()))
    if len(chosen) == n_select:
        return pop[chosen].copy()

    # 其余：按 excellence 从高到低选（避免除以 0，直接用排序）
    remaining = [i for i in range(pop.shape[0]) if i not in set(chosen)]
    rem_exc = excellence[remaining]
    rem_sorted = [remaining[i] for i in np.argsort(-rem_exc)]
    need = n_select - len(chosen)
    chosen.extend(rem_sorted[:need])
    return pop[np.asarray(chosen, dtype=int)].copy()


def _roulette_select(rng: np.random.Generator, weights: np.ndarray) -> int:
    w = np.asarray(weights, dtype=float).reshape(-1)
    if w.size == 0:
        raise ValueError("weights 为空。")
    # roulette 要求非负；若存在负值则整体平移
    w = w - float(np.min(w))
    w = w + 1e-12
    s = float(np.sum(w))
    if not np.isfinite(s) or s <= 0:
        return int(rng.integers(0, w.size))
    r = float(rng.random() * s)
    c = 0.0
    for i, wi in enumerate(w):
        c += float(wi)
        if r <= c:
            return int(i)
    return int(w.size - 1)


def _crossover_one_point(
    p1: np.ndarray,
    p2: np.ndarray,
    rng: np.random.Generator,
    *,
    n_ones: Optional[int],
    valid: Optional[BinaryPredicate],
    repair: Optional[BinaryRepair],
) -> Tuple[np.ndarray, np.ndarray]:
    n_bits = int(p1.size)
    if n_bits < 2:
        return p1.copy(), p2.copy()
    cut = int(rng.integers(1, n_bits))  # [1, n_bits-1]
    c1 = np.concatenate([p1[:cut], p2[cut:]]).astype(np.int8, copy=False)
    c2 = np.concatenate([p2[:cut], p1[cut:]]).astype(np.int8, copy=False)

    def fix(x: np.ndarray) -> np.ndarray:
        x = x.astype(np.int8, copy=True)
        if repair is not None:
            x = np.asarray(repair(x), dtype=np.int8).reshape(-1)
        if n_ones is not None:
            x = _repair_n_ones(x, int(n_ones), rng=rng)
        if valid is not None and (not bool(valid(x))):
            # 简单重采样兜底
            for _ in range(50):
                if n_ones is None:
                    x_try = (rng.random(n_bits) < 0.5).astype(np.int8)
                else:
                    x_try = np.zeros(n_bits, dtype=np.int8)
                    idx = rng.choice(n_bits, size=int(n_ones), replace=False)
                    x_try[idx] = 1
                if repair is not None:
                    x_try = np.asarray(repair(x_try), dtype=np.int8).reshape(-1)
                if n_ones is not None:
                    x_try = _repair_n_ones(x_try, int(n_ones), rng=rng)
                if valid is None or bool(valid(x_try)):
                    return x_try
        return x

    return fix(c1), fix(c2)


def _mutate(
    x: np.ndarray,
    rng: np.random.Generator,
    *,
    n_ones: Optional[int],
    valid: Optional[BinaryPredicate],
    repair: Optional[BinaryRepair],
) -> np.ndarray:
    x = x.astype(np.int8, copy=True)
    n_bits = int(x.size)
    if n_bits == 0:
        return x
    if n_ones is not None:
        ones = np.flatnonzero(x == 1)
        zeros = np.flatnonzero(x == 0)
        if ones.size > 0 and zeros.size > 0:
            i1 = int(rng.choice(ones))
            i0 = int(rng.choice(zeros))
            x[i1], x[i0] = 0, 1  # swap，保持 1 的数量不变
    else:
        pos = int(rng.integers(0, n_bits))
        x[pos] = 1 - x[pos]

    if repair is not None:
        x = np.asarray(repair(x), dtype=np.int8).reshape(-1)
    if n_ones is not None:
        x = _repair_n_ones(x, int(n_ones), rng=rng)
    if valid is not None and (not bool(valid(x))):
        # 兜底：直接返回原样（避免死循环）
        return x
    return x


def immune_genetic_algorithm(
    objective: BinaryObjective,
    *,
    n_bits: int,
    n_ones: Optional[int] = None,
    valid: Optional[BinaryPredicate] = None,
    repair: Optional[BinaryRepair] = None,
    params: Optional[ImmuneGAParams] = None,
) -> Dict[str, Any]:
    """
    免疫遗传算法（IGA）。

    Args:
        objective: 目标函数 f(x)->float，其中 x 为 0/1 向量。
        n_bits: 变量维度（bit 数）。
        n_ones: 若提供，则强制每个解恰好有 n_ones 个 1（常用于“从 n 个点选 k 个点”）。
        valid: 可选约束函数 valid(x)->bool。
        repair: 可选修复函数 repair(x)->x。
        params: ImmuneGAParams。

    Returns:
        dict:
            - best_x: (n_bits,)
            - best_fitness: float（objective 的原始返回值）
            - history_best: (generations,) 每代最优
    """
    p = params or ImmuneGAParams()
    n_bits = int(n_bits)
    if n_bits <= 0:
        raise ValueError("n_bits 必须为正整数。")
    if n_ones is not None and (int(n_ones) < 0 or int(n_ones) > n_bits):
        raise ValueError("n_ones 必须在 [0, n_bits]。")

    rng = np.random.default_rng(p.seed)

    sizepop = int(max(2, p.pop_size))
    overbest = int(max(0, p.memory_size))
    M = sizepop + overbest

    pop = _init_population(rng, M, n_bits, n_ones=n_ones, valid=valid, repair=repair)

    history_best = np.zeros(int(p.generations), dtype=float)
    best_x = pop[0].copy()
    best_fit_raw = float(objective(best_x))

    def eval_fitness(pop0: np.ndarray) -> np.ndarray:
        vals = np.array([float(objective(ind)) for ind in pop0], dtype=float)
        return vals

    for gen in range(int(p.generations)):
        fitness = eval_fitness(pop)

        # 更新当前最优
        if p.maximize:
            idx_best = int(np.argmax(fitness))
            if float(fitness[idx_best]) > float(best_fit_raw):
                best_fit_raw = float(fitness[idx_best])
                best_x = pop[idx_best].copy()
        else:
            idx_best = int(np.argmin(fitness))
            if float(fitness[idx_best]) < float(best_fit_raw):
                best_fit_raw = float(fitness[idx_best])
                best_x = pop[idx_best].copy()

        # 多样性：浓度
        sim = _similarity_matrix(pop, n_ones=n_ones)
        con = _concentration(sim, threshold=float(p.similarity_threshold))
        exc = _excellence(fitness, con, ps=float(p.ps), maximize=bool(p.maximize))

        # 更新记忆库 + 形成父代
        memory = _best_select(pop, fitness, exc, n_select=max(1, overbest), elitism=int(p.elitism), maximize=bool(p.maximize)) if overbest > 0 else np.zeros((0, n_bits), dtype=np.int8)
        parents = _best_select(pop, fitness, exc, n_select=sizepop, elitism=int(p.elitism), maximize=bool(p.maximize))

        # 选择概率使用父代的 excellence（对父代重算，避免丢失索引映射）
        parents_fitness = eval_fitness(parents)
        parent_sim = _similarity_matrix(parents, n_ones=n_ones)
        parent_con = _concentration(parent_sim, threshold=float(p.similarity_threshold))
        parent_exc = _excellence(parents_fitness, parent_con, ps=float(p.ps), maximize=bool(p.maximize))

        # 产生子代
        children: list[np.ndarray] = []
        while len(children) < sizepop:
            i1 = _roulette_select(rng, parent_exc)
            i2 = _roulette_select(rng, parent_exc)
            p1 = parents[i1]
            p2 = parents[i2]
            if rng.random() < float(p.pcross):
                c1, c2 = _crossover_one_point(p1, p2, rng, n_ones=n_ones, valid=valid, repair=repair)
            else:
                c1, c2 = p1.copy(), p2.copy()
            if rng.random() < float(p.pmutation):
                c1 = _mutate(c1, rng, n_ones=n_ones, valid=valid, repair=repair)
            if rng.random() < float(p.pmutation):
                c2 = _mutate(c2, rng, n_ones=n_ones, valid=valid, repair=repair)
            children.append(c1)
            if len(children) < sizepop:
                children.append(c2)

        # 合并：新种群 = 子代 + 记忆库
        if overbest > 0:
            pop = np.vstack([np.asarray(children[:sizepop], dtype=np.int8), memory])
        else:
            pop = np.asarray(children[:sizepop], dtype=np.int8)

        history_best[gen] = float(best_fit_raw)

    return {"best_x": best_x, "best_fitness": float(best_fit_raw), "history_best": history_best}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：免疫遗传算法（IGA）。

    Args:
        data: dict，包含：
            - objective: callable，输入 x:(n_bits,) 的 0/1 向量，输出 float
            - n_bits: int
            可选：
            - n_ones: int（固定 1 的数量，用于选址/选点）
            - valid: callable(x)->bool
            - repair: callable(x)->x
        params: ImmuneGAParams 字段：
            - pop_size, memory_size, generations, pcross, pmutation, ps, similarity_threshold, elitism, seed, maximize

    Returns:
        dict: immune_genetic_algorithm() 的返回值
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")
    if "objective" not in data or "n_bits" not in data:
        raise TypeError("data 必须包含 objective 与 n_bits。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    p = ImmuneGAParams(
        pop_size=int(params.get("pop_size", 50)),
        memory_size=int(params.get("memory_size", 10)),
        generations=int(params.get("generations", 100)),
        pcross=float(params.get("pcross", 0.5)),
        pmutation=float(params.get("pmutation", 0.4)),
        ps=float(params.get("ps", 0.95)),
        similarity_threshold=float(params.get("similarity_threshold", 0.7)),
        elitism=int(params.get("elitism", 3)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
        maximize=bool(params.get("maximize", False)),
    )

    return immune_genetic_algorithm(
        objective,
        n_bits=int(data["n_bits"]),
        n_ones=None if data.get("n_ones") is None else int(data.get("n_ones")),
        valid=data.get("valid"),
        repair=data.get("repair"),
        params=p,
    )


if __name__ == "__main__":
    # Mock Data：简化选址问题（从 n 个点选 k 个中心，最小化“需求加权到最近中心距离”）
    rng = np.random.default_rng(0)
    n = 30
    k = 5
    coords = rng.uniform(0, 100, size=(n, 2))
    demand = rng.uniform(1, 10, size=n)
    D = np.sqrt(np.sum((coords[:, None, :] - coords[None, :, :]) ** 2, axis=2))

    def objective(x: np.ndarray) -> float:
        centers = np.flatnonzero(x == 1)
        if centers.size == 0:
            return 1e18
        dist_to_centers = np.min(D[:, centers], axis=1)
        return float(np.sum(demand * dist_to_centers))

    out = solve(
        {"objective": objective, "n_bits": n, "n_ones": k},
        {"pop_size": 50, "memory_size": 10, "generations": 80, "pcross": 0.6, "pmutation": 0.4, "seed": 0},
    )
    print("best_fitness =", round(float(out["best_fitness"]), 6))
    print("selected_centers =", np.flatnonzero(out["best_x"] == 1).tolist())
