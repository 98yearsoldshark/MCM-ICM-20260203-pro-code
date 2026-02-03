# -*- coding: utf-8 -*-
# Monte Carlo 仿真：用随机采样估计期望/概率/积分（通用模板）

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


Sampler = Callable[[np.random.Generator, int], np.ndarray]
Func = Callable[[np.ndarray], np.ndarray]


@dataclass
class MCParams:
    n_samples: int = 10000
    seed: Optional[int] = 0
    ci_level: float = 0.95


def monte_carlo_expectation(
    sampler: Sampler,
    func: Optional[Func] = None,
    *,
    params: Optional[MCParams] = None,
) -> Dict[str, Any]:
    """
    Monte Carlo 估计 E[f(X)]。

    Args:
        sampler: 采样器 sampler(rng, n)->samples，返回 shape=(n, d) 或 (n,)。
        func: 变换函数 f(samples)->values，返回 shape=(n,) 或 (n,k)。
            - 若为 None，则直接对 samples 求均值（即估计 E[X]）。
        params: MCParams。

    Returns:
        dict:
            - mean: 样本均值
            - std: 样本标准差（ddof=1）
            - ci: 正态近似置信区间（mean ± z*std/sqrt(n)）
            - samples: 原始 samples（可能较大；需要时可关闭返回）
            - values: func 后的 values（同上）
    """
    p = params or MCParams()
    rng = np.random.default_rng(p.seed)
    n = int(p.n_samples)
    if n < 1:
        raise ValueError("n_samples 必须 >= 1。")
    if not (0.0 < float(p.ci_level) < 1.0):
        raise ValueError("ci_level 必须在 (0,1) 内。")

    samples = sampler(rng, n)
    values = samples if func is None else func(samples)
    values = np.asarray(values, dtype=float)

    mean = np.mean(values, axis=0)
    std = np.std(values, axis=0, ddof=1) if n > 1 else np.zeros_like(mean)

    # 正态近似 z 值（常用 95%≈1.96）；用误差函数反解近似
    # 为避免引入额外依赖，这里用常用水平的硬编码；其他水平退化到 1.96。
    level = float(p.ci_level)
    z_map = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_map.get(round(level, 2), 1.96)

    half = z * std / np.sqrt(n) if n > 1 else np.zeros_like(std)
    ci = np.stack([mean - half, mean + half], axis=0)

    return {"mean": mean, "std": std, "ci": ci, "n_samples": n}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：Monte Carlo 期望估计。

    Args:
        data: dict，包含：
            - sampler: callable(rng,n)->samples
            - func: callable(samples)->values（可选）
        params: 参数：
            - n_samples: int
            - seed: int | None
            - ci_level: float（默认 0.95）

    Returns:
        dict: 见 monte_carlo_expectation() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "sampler" not in data:
        raise TypeError("data 必须为 dict，且包含 sampler。")
    sampler = data["sampler"]
    if not callable(sampler):
        raise TypeError("data.sampler 必须为可调用函数。")
    func = data.get("func")
    if func is not None and not callable(func):
        raise TypeError("data.func 必须为可调用函数或 None。")

    mc_params = MCParams(
        n_samples=int(params.get("n_samples", 10000)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
        ci_level=float(params.get("ci_level", 0.95)),
    )
    return monte_carlo_expectation(sampler, func, params=mc_params)


if __name__ == "__main__":
    # Mock Data：估计 π（单位正方形内随机点落在 1/4 圆内的概率 * 4）
    def sampler_xy(rng: np.random.Generator, n: int) -> np.ndarray:
        return rng.uniform(0, 1, size=(n, 2))

    def inside_quarter_circle(xy: np.ndarray) -> np.ndarray:
        x = xy[:, 0]
        y = xy[:, 1]
        return (x * x + y * y <= 1.0).astype(float)

    out = solve({"sampler": sampler_xy, "func": inside_quarter_circle}, {"n_samples": 200000, "seed": 0, "ci_level": 0.95})
    p_hat = float(out["mean"])
    pi_hat = 4.0 * p_hat
    print("pi_hat =", pi_hat)
    print("95% CI for p =", out["ci"][:, 0])

