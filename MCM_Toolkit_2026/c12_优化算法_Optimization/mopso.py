# -*- coding: utf-8 -*-
# 多目标粒子群优化（MOPSO）：外部档案库 + 网格拥挤度引导（Coello 2004）
#
# 参考来源（资料目录，Matlab 版实现较完整）：
# - 6、按赛题类别划分的常用算法代码/.../多目标粒子群优化算法代码/mopso.m + 各辅助函数
#
# 说明：
# - 目标为“最小化”多目标向量（每个维度越小越好）
# - 返回外部档案库（Pareto 近似解集）

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


MultiObjective = Callable[[np.ndarray], Sequence[float]]


@dataclass
class MOPSOParams:
    n_pop: int = 100
    n_rep: int = 100
    max_iter: int = 100

    # 收敛因子（与资料版一致的默认值）
    phi1: float = 2.05
    phi2: float = 2.05
    w: Optional[float] = None
    wdamp: float = 1.0
    c1: Optional[float] = None
    c2: Optional[float] = None

    alpha: float = 0.1  # 网格膨胀
    n_grid: int = 10
    beta: float = 4.0  # leader 选择压力（越大越偏向稀疏网格）
    gamma: float = 2.0  # 删除压力（越大越倾向删拥挤网格）

    vel_max_factor: float = 0.1  # vel_max = (ub-lb)*factor
    seed: Optional[int] = 0


@dataclass
class Particle:
    position: np.ndarray
    velocity: np.ndarray
    cost: np.ndarray
    best_position: np.ndarray
    best_cost: np.ndarray
    dominated: bool = False
    grid_index: int = -1
    grid_subindex: Tuple[int, ...] = ()


def _dominates(a: np.ndarray, b: np.ndarray) -> bool:
    # all(a<=b) && any(a<b)
    return bool(np.all(a <= b) and np.any(a < b))


def _determine_domination(pop: List[Particle]) -> None:
    for p in pop:
        p.dominated = False
    n = len(pop)
    for i in range(n):
        if pop[i].dominated:
            continue
        for j in range(i):
            if pop[j].dominated:
                continue
            if _dominates(pop[i].cost, pop[j].cost):
                pop[j].dominated = True
            elif _dominates(pop[j].cost, pop[i].cost):
                pop[i].dominated = True
                break


def _get_non_dominated(pop: List[Particle]) -> List[Particle]:
    return [p for p in pop if not p.dominated]


def _get_costs(pop: List[Particle]) -> np.ndarray:
    # (n_obj, n_pop)
    costs = np.stack([p.cost for p in pop], axis=0)
    return costs.T


def _create_hypercubes(costs: np.ndarray, n_grid: int, alpha: float) -> List[Dict[str, np.ndarray]]:
    # costs: (n_obj, n_rep)
    n_obj = int(costs.shape[0])
    G: List[Dict[str, np.ndarray]] = []
    for j in range(n_obj):
        cj = costs[j]
        min_c = float(np.min(cj))
        max_c = float(np.max(cj))
        dc = float(alpha) * (max_c - min_c)
        min_c -= dc
        max_c += dc
        # Matlab: linspace(min,max,ngrid-1) -> 生成 ngrid-1 个分割点，对应 ngrid 个区间
        gx = np.linspace(min_c, max_c, int(n_grid) - 1, dtype=float)
        lower = np.concatenate([np.array([-np.inf], dtype=float), gx])
        upper = np.concatenate([gx, np.array([np.inf], dtype=float)])
        G.append({"lower": lower, "upper": upper})
    return G


def _get_grid_index(cost: np.ndarray, G: List[Dict[str, np.ndarray]]) -> Tuple[int, Tuple[int, ...]]:
    n_obj = len(G)
    n_grid = int(G[0]["upper"].size)
    sub: List[int] = []
    for j in range(n_obj):
        U = G[j]["upper"]
        # 找到第一个 cost < U 的区间
        idx = int(np.searchsorted(U, float(cost[j]), side="right"))  # 0..n_grid
        idx = min(idx, n_grid - 1)
        sub.append(idx)
    sub_t = tuple(sub)
    # 用 ravel_multi_index 生成全局编号（行主序即可，一致即可）
    index = int(np.ravel_multi_index(sub_t, dims=(n_grid,) * n_obj, mode="clip"))
    return index, sub_t


def _get_occupied_cells(rep: List[Particle]) -> Tuple[np.ndarray, np.ndarray]:
    grid = np.array([p.grid_index for p in rep], dtype=int)
    uniq, counts = np.unique(grid, return_counts=True)
    return uniq, counts.astype(int)


def _roulette_wheel(rng: np.random.Generator, p: np.ndarray) -> int:
    p = np.asarray(p, dtype=float).reshape(-1)
    p = np.clip(p, 0.0, np.inf)
    s = float(np.sum(p))
    if s <= 0 or not np.isfinite(s):
        return int(rng.integers(0, p.size))
    r = float(rng.random() * s)
    c = 0.0
    for i, pi in enumerate(p):
        c += float(pi)
        if r <= c:
            return int(i)
    return int(p.size - 1)


def _select_leader(rng: np.random.Generator, rep: List[Particle], beta: float) -> Particle:
    occ_idx, occ_cnt = _get_occupied_cells(rep)
    p = occ_cnt.astype(float) ** (-float(beta))
    p = p / float(np.sum(p))
    cell = int(occ_idx[_roulette_wheel(rng, p)])
    members = [i for i, r in enumerate(rep) if r.grid_index == cell]
    pick = int(rng.choice(members))
    return rep[pick]


def _delete_from_rep(rng: np.random.Generator, rep: List[Particle], extra: int, gamma: float) -> List[Particle]:
    rep0 = rep[:]
    for _ in range(int(extra)):
        occ_idx, occ_cnt = _get_occupied_cells(rep0)
        p = occ_cnt.astype(float) ** float(gamma)
        p = p / float(np.sum(p))
        cell = int(occ_idx[_roulette_wheel(rng, p)])
        members = [i for i, r in enumerate(rep0) if r.grid_index == cell]
        j = int(rng.choice(members))
        rep0.pop(j)
    return rep0


def mopso(
    objective: MultiObjective,
    bounds: Sequence[Tuple[float, float]],
    *,
    params: Optional[MOPSOParams] = None,
) -> Dict[str, Any]:
    """
    多目标粒子群优化（最小化）。

    Args:
        objective: 目标函数 f(x)->(f1,f2,...)，越小越好。
        bounds: 变量边界 [(low,high), ...]
        params: MOPSOParams

    Returns:
        dict:
            - rep_positions: (n_rep, n_var)
            - rep_costs: (n_rep, n_obj)
            - history_rep_size: (max_iter,) 每代 archive 大小
    """
    p = params or MOPSOParams()
    bounds_arr = np.asarray(list(bounds), dtype=float)
    if bounds_arr.ndim != 2 or bounds_arr.shape[1] != 2:
        raise ValueError("bounds 必须为 (n_var,2)。")
    if np.any(bounds_arr[:, 0] >= bounds_arr[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")
    n_var = int(bounds_arr.shape[0])

    rng = np.random.default_rng(p.seed)

    # 默认参数与资料版一致：使用收敛因子 chi
    phi1 = float(p.phi1)
    phi2 = float(p.phi2)
    phi = phi1 + phi2
    chi = 2.0 / (phi - 2.0 + math.sqrt(phi * phi - 4.0 * phi))
    w = float(chi if p.w is None else p.w)
    c1 = float(chi * phi1 if p.c1 is None else p.c1)
    c2 = float(chi * phi2 if p.c2 is None else p.c2)

    vel_max = (bounds_arr[:, 1] - bounds_arr[:, 0]) * float(p.vel_max_factor)

    def eval_cost(x: np.ndarray) -> np.ndarray:
        c = np.asarray(objective(np.asarray(x, dtype=float).reshape(-1)), dtype=float).reshape(-1)
        if c.size == 0:
            raise ValueError("objective 必须返回非空的多目标向量。")
        return c

    # 初始化
    pop: List[Particle] = []
    for _ in range(int(p.n_pop)):
        pos = rng.uniform(bounds_arr[:, 0], bounds_arr[:, 1], size=n_var)
        vel = np.zeros(n_var, dtype=float)
        cost = eval_cost(pos)
        pop.append(Particle(position=pos, velocity=vel, cost=cost, best_position=pos.copy(), best_cost=cost.copy()))

    _determine_domination(pop)
    rep = _get_non_dominated(pop)

    # 建网格并标注 rep 的 GridIndex
    rep_costs = _get_costs(rep)
    G = _create_hypercubes(rep_costs, n_grid=int(p.n_grid), alpha=float(p.alpha))
    for r in rep:
        r.grid_index, r.grid_subindex = _get_grid_index(r.cost, G)

    history_rep_size = np.zeros(int(p.max_iter), dtype=int)

    for it in range(int(p.max_iter)):
        for i in range(int(p.n_pop)):
            leader = _select_leader(rng, rep, beta=float(p.beta))

            r1 = rng.random(n_var)
            r2 = rng.random(n_var)
            v = (
                w * pop[i].velocity
                + c1 * r1 * (pop[i].best_position - pop[i].position)
                + c2 * r2 * (leader.position - pop[i].position)
            )
            v = np.clip(v, -vel_max, vel_max)
            x = pop[i].position + v

            # 边界处理：越界则反弹（与资料版一致）
            low = bounds_arr[:, 0]
            high = bounds_arr[:, 1]
            flag = (x < low) | (x > high)
            v[flag] = -v[flag]
            x = np.clip(x, low, high)

            cost = eval_cost(x)

            pop[i].position = x
            pop[i].velocity = v
            pop[i].cost = cost

            # 更新个体最优
            if _dominates(cost, pop[i].best_cost):
                pop[i].best_position = x.copy()
                pop[i].best_cost = cost.copy()
            elif not _dominates(pop[i].best_cost, cost):
                if rng.random() < 0.5:
                    pop[i].best_position = x.copy()
                    pop[i].best_cost = cost.copy()

        _determine_domination(pop)
        nd_pop = _get_non_dominated(pop)

        rep = rep + nd_pop
        _determine_domination(rep)
        rep = _get_non_dominated(rep)

        # 更新网格
        rep_costs = _get_costs(rep)
        G = _create_hypercubes(rep_costs, n_grid=int(p.n_grid), alpha=float(p.alpha))
        for r in rep:
            r.grid_index, r.grid_subindex = _get_grid_index(r.cost, G)

        # 限制 archive 大小
        if len(rep) > int(p.n_rep):
            extra = len(rep) - int(p.n_rep)
            rep = _delete_from_rep(rng, rep, extra=extra, gamma=float(p.gamma))

        history_rep_size[it] = len(rep)
        w *= float(p.wdamp)

    rep_positions = np.stack([r.position for r in rep], axis=0) if rep else np.zeros((0, n_var), dtype=float)
    rep_costs_out = np.stack([r.cost for r in rep], axis=0) if rep else np.zeros((0, 0), dtype=float)
    return {"rep_positions": rep_positions, "rep_costs": rep_costs_out, "history_rep_size": history_rep_size}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：MOPSO 多目标优化（最小化）。

    Args:
        data: dict，包含：
            - objective: callable，x->(f1,f2,...)
            - bounds: list[(low,high)]
        params: MOPSOParams 字段（可选）：
            - n_pop, n_rep, max_iter, phi1, phi2, w, wdamp, c1, c2, alpha, n_grid, beta, gamma, vel_max_factor, seed

    Returns:
        dict: mopso() 的返回值
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "bounds" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 bounds。")
    if not callable(data["objective"]):
        raise TypeError("data.objective 必须为可调用函数。")

    p = MOPSOParams(
        n_pop=int(params.get("n_pop", 100)),
        n_rep=int(params.get("n_rep", 100)),
        max_iter=int(params.get("max_iter", 100)),
        phi1=float(params.get("phi1", 2.05)),
        phi2=float(params.get("phi2", 2.05)),
        w=None if params.get("w") is None else float(params.get("w")),
        wdamp=float(params.get("wdamp", 1.0)),
        c1=None if params.get("c1") is None else float(params.get("c1")),
        c2=None if params.get("c2") is None else float(params.get("c2")),
        alpha=float(params.get("alpha", 0.1)),
        n_grid=int(params.get("n_grid", 10)),
        beta=float(params.get("beta", 4.0)),
        gamma=float(params.get("gamma", 2.0)),
        vel_max_factor=float(params.get("vel_max_factor", 0.1)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )
    return mopso(data["objective"], data["bounds"], params=p)


if __name__ == "__main__":
    # Mock Data：ZDT1（经典 2 目标测试问题，最小化）
    def zdt1(x: np.ndarray) -> Tuple[float, float]:
        x = np.asarray(x, dtype=float).reshape(-1)
        f1 = float(x[0])
        g = 1.0 + 9.0 * float(np.mean(x[1:]))
        f2 = float(g * (1.0 - math.sqrt(f1 / g)))
        return f1, f2

    out = solve(
        {"objective": zdt1, "bounds": [(0.0, 1.0)] * 5},
        {"n_pop": 60, "n_rep": 80, "max_iter": 60, "seed": 0},
    )
    print("rep_size =", out["rep_positions"].shape[0])
    if out["rep_costs"].shape[0] > 0:
        print("rep_costs_head =", np.round(out["rep_costs"][:5], 4))

