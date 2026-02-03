# -*- coding: utf-8 -*-
# 模拟退火（SA）：连续变量全局优化（简化版）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../优化与控制题型参考代码...（多处含 SA/退火相关实现）

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
class SAParams:
    iterations: int = 5000
    T0: float = 1.0
    alpha: float = 0.995  # 降温系数
    step_scale: float = 0.1  # 邻域扰动尺度（相对 bounds 范围）
    seed: Optional[int] = 0


def simulated_annealing(
    objective: Objective,
    bounds: Sequence[Tuple[float, float]],
    *,
    x0: Optional[Sequence[float]] = None,
    params: Optional[SAParams] = None,
) -> Dict[str, Any]:
    """
    模拟退火最小化。

    Args:
        objective: 目标函数 f(x)->float（越小越好）。
        bounds: 变量边界 [(low,high), ...]。
        x0: 初始点（可选）；不提供则随机初始化。
        params: SAParams。

    Returns:
        dict:
            - x_best, f_best
            - history_best: 每次迭代的最优值
    """
    p = params or SAParams()
    bounds_arr = np.asarray(list(bounds), dtype=float)
    if bounds_arr.ndim != 2 or bounds_arr.shape[1] != 2:
        raise ValueError("bounds 必须为 (d×2)。")
    if np.any(bounds_arr[:, 0] >= bounds_arr[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")

    d = bounds_arr.shape[0]
    rng = np.random.default_rng(p.seed)
    low = bounds_arr[:, 0]
    high = bounds_arr[:, 1]
    span = high - low
    step = float(p.step_scale) * span

    if x0 is None:
        x = rng.uniform(low, high, size=d)
    else:
        x = np.asarray(list(x0), dtype=float).reshape(-1)
        if x.shape != (d,):
            raise ValueError("x0 维度必须与 bounds 一致。")
        x = np.clip(x, low, high)

    fx = float(objective(x))
    x_best = x.copy()
    f_best = fx

    T = float(p.T0)
    history_best = []
    for _ in range(int(p.iterations)):
        history_best.append(f_best)

        # 高斯扰动邻域
        x_new = x + rng.normal(0.0, step, size=d)
        x_new = np.clip(x_new, low, high)
        f_new = float(objective(x_new))

        delta = f_new - fx
        if delta <= 0:
            accept = True
        else:
            prob = np.exp(-delta / max(T, 1e-12))
            accept = rng.random() < prob

        if accept:
            x, fx = x_new, f_new
            if fx < f_best:
                x_best = x.copy()
                f_best = fx

        T *= float(p.alpha)

    history_best.append(f_best)
    return {"x_best": x_best, "f_best": f_best, "history_best": np.asarray(history_best)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：模拟退火（最小化）。

    Args:
        data: dict，包含：
            - objective: callable
            - bounds: list[(low,high)]
            - x0: list[float] | None
        params: SA 参数（同 SAParams 字段）。

    Returns:
        dict: simulated_annealing() 的返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "objective" not in data or "bounds" not in data:
        raise TypeError("data 必须为 dict，且包含 objective 与 bounds。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    sa_params = SAParams(
        iterations=int(params.get("iterations", 5000)),
        T0=float(params.get("T0", 1.0)),
        alpha=float(params.get("alpha", 0.995)),
        step_scale=float(params.get("step_scale", 0.1)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )
    return simulated_annealing(objective, data["bounds"], x0=data.get("x0"), params=sa_params)


if __name__ == "__main__":
    # Mock Data：带多个局部最优的 Rastrigin
    def rastrigin(x: np.ndarray) -> float:
        A = 10.0
        return float(A * x.size + np.sum(x**2 - A * np.cos(2 * np.pi * x)))

    bounds = [(-5.12, 5.12)] * 5
    out = solve(
        {"objective": rastrigin, "bounds": bounds},
        {"iterations": 8000, "T0": 5.0, "alpha": 0.999, "step_scale": 0.05, "seed": 0},
    )
    print("f_best =", out["f_best"])
    print("x_best =", np.round(out["x_best"], 4))

