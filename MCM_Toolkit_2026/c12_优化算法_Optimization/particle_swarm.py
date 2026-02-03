# -*- coding: utf-8 -*-
# 粒子群优化（PSO）：连续变量全局优化（简化、可直接改）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码.../PSO*.m

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Objective = Callable[[np.ndarray], float]


@dataclass
class PSOParams:
    n_particles: int = 50
    iterations: int = 200
    w: float = 0.729  # 惯性权重
    c1: float = 1.49445  # 个体学习因子
    c2: float = 1.49445  # 社会学习因子
    seed: Optional[int] = 0
    vmax_ratio: Optional[float] = 0.2  # 最大速度 = ratio*(high-low)，None 表示不限制


def particle_swarm_optimization(
    objective: Objective,
    bounds: Sequence[Tuple[float, float]],
    *,
    params: Optional[PSOParams] = None,
) -> Dict[str, Any]:
    """
    PSO 连续优化（最小化）。

    Args:
        objective: 目标函数 f(x)->float（越小越好）。
        bounds: 变量边界 [(low,high), ...]。
        params: PSOParams。

    Returns:
        dict:
            - x_best, f_best
            - history_best: 每次迭代的全局最优值
    """
    p = params or PSOParams()
    bounds_arr = np.asarray(list(bounds), dtype=float)
    if bounds_arr.ndim != 2 or bounds_arr.shape[1] != 2:
        raise ValueError("bounds 必须为 (d×2)。")
    if np.any(bounds_arr[:, 0] >= bounds_arr[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")

    d = bounds_arr.shape[0]
    rng = np.random.default_rng(p.seed)

    low = bounds_arr[:, 0]
    high = bounds_arr[:, 1]
    pos = rng.uniform(low, high, size=(int(p.n_particles), d))
    vel = rng.normal(0.0, 1.0, size=(int(p.n_particles), d))

    if p.vmax_ratio is not None:
        vmax = float(p.vmax_ratio) * (high - low)
    else:
        vmax = None

    pbest_pos = pos.copy()
    pbest_fit = np.array([float(objective(x)) for x in pos], dtype=float)
    gbest_idx = int(np.argmin(pbest_fit))
    gbest_pos = pbest_pos[gbest_idx].copy()
    gbest_fit = float(pbest_fit[gbest_idx])

    history_best = []
    for _ in range(int(p.iterations)):
        history_best.append(gbest_fit)

        r1 = rng.random(size=pos.shape)
        r2 = rng.random(size=pos.shape)
        vel = float(p.w) * vel + float(p.c1) * r1 * (pbest_pos - pos) + float(p.c2) * r2 * (gbest_pos - pos)
        if vmax is not None:
            vel = np.clip(vel, -vmax, vmax)

        pos = pos + vel
        pos = np.clip(pos, low, high)

        fit = np.array([float(objective(x)) for x in pos], dtype=float)
        improved = fit < pbest_fit
        pbest_fit[improved] = fit[improved]
        pbest_pos[improved] = pos[improved]

        gbest_idx = int(np.argmin(pbest_fit))
        if float(pbest_fit[gbest_idx]) < gbest_fit:
            gbest_fit = float(pbest_fit[gbest_idx])
            gbest_pos = pbest_pos[gbest_idx].copy()

    history_best.append(gbest_fit)
    return {"x_best": gbest_pos, "f_best": gbest_fit, "history_best": np.asarray(history_best)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：PSO 优化（最小化）。

    Args:
        data: dict，包含：
            - objective: callable
            - bounds: list[(low,high)]
        params: PSO 参数（同 PSOParams 字段）。

    Returns:
        dict: particle_swarm_optimization() 的返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "bounds" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 bounds。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    pso_params = PSOParams(
        n_particles=int(params.get("n_particles", 50)),
        iterations=int(params.get("iterations", 200)),
        w=float(params.get("w", 0.729)),
        c1=float(params.get("c1", 1.49445)),
        c2=float(params.get("c2", 1.49445)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
        vmax_ratio=None if params.get("vmax_ratio") is None else float(params.get("vmax_ratio", 0.2)),
    )
    return particle_swarm_optimization(objective, data["bounds"], params=pso_params)


if __name__ == "__main__":
    # Mock Data：Rastrigin 函数最小化（多峰，最优 0）
    def rastrigin(x: np.ndarray) -> float:
        A = 10.0
        return float(A * x.size + np.sum(x**2 - A * np.cos(2 * np.pi * x)))

    bounds = [(-5.12, 5.12)] * 5
    out = solve({"objective": rastrigin, "bounds": bounds}, {"n_particles": 60, "iterations": 200, "seed": 0})
    print("f_best =", out["f_best"])
    print("x_best =", np.round(out["x_best"], 4))

