# -*- coding: utf-8 -*-
# 量子遗传算法（QGA）：基于量子比特编码的全局优化（资料 Matlab 版复刻）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/.../量子遗传算法代码/*.m
#
# 说明：
# - 该实现复刻了资料中的 Qgate/InitPop/collapse/bin2decFun 逻辑
# - 默认“最大化”目标函数；若要最小化，可设置 params['maximize']=False（内部转为最大化 -f）

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


Objective = Callable[[np.ndarray], float]


@dataclass
class QGAParams:
    pop_size: int = 40
    generations: int = 200
    delta: float = 0.01 * math.pi  # 量子旋转门角度增量
    seed: Optional[int] = 0
    maximize: bool = True


def _ensure_bounds(bounds: Sequence[Tuple[float, float]], n_var: int) -> np.ndarray:
    b = np.asarray(list(bounds), dtype=float)
    if b.shape != (n_var, 2):
        raise ValueError("bounds 必须为 (n_var,2)。")
    if np.any(b[:, 0] >= b[:, 1]):
        raise ValueError("bounds 的 low 必须小于 high。")
    return b


def _init_quantum_pop(rng: np.random.Generator, pop_size: int, n_bits: int) -> Tuple[np.ndarray, np.ndarray]:
    # 资料 InitPop.m：每个量子比特初始化为 [alpha,beta]=[1/sqrt(2),1/sqrt(2)]
    v = 1.0 / math.sqrt(2.0)
    alpha = np.full((pop_size, n_bits), v, dtype=float)
    beta = np.full((pop_size, n_bits), v, dtype=float)
    # 给一个非常小的扰动，避免极端边界导致的“方向判定”退化（不影响整体逻辑）
    eps = 1e-12
    alpha = np.clip(alpha + rng.normal(0.0, eps, size=alpha.shape), -1.0, 1.0)
    beta = np.clip(beta + rng.normal(0.0, eps, size=beta.shape), -1.0, 1.0)
    # 重新归一化
    s = np.sqrt(alpha * alpha + beta * beta)
    alpha /= s
    beta /= s
    return alpha, beta


def _collapse(alpha: np.ndarray, beta: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    # 资料 collapse.m：若 pick > alpha^2 则塌缩为 1，否则 0
    pick = rng.random(size=alpha.shape)
    return (pick > (alpha * alpha)).astype(np.int8)


def _decode_binary_to_real(binary: np.ndarray, bit_lengths: Sequence[int], bounds: np.ndarray) -> np.ndarray:
    bit_lengths = [int(x) for x in bit_lengths]
    if any(L <= 0 for L in bit_lengths):
        raise ValueError("bit_lengths 每个元素必须为正整数。")
    n_var = len(bit_lengths)
    if binary.shape[1] != int(sum(bit_lengths)):
        raise ValueError("binary 的列数必须等于 sum(bit_lengths)。")
    X = np.zeros((binary.shape[0], n_var), dtype=float)
    col = 0
    for i, L in enumerate(bit_lengths):
        bits = binary[:, col : col + L]
        # bits 为 0/1，按高位在前：value = sum(bits * 2^(L-1-k))
        powers = (1 << np.arange(L - 1, -1, -1, dtype=np.int64)).reshape(1, -1)
        val = np.sum(bits.astype(np.int64) * powers, axis=1)
        denom = float((1 << L) - 1)
        lo, hi = float(bounds[i, 0]), float(bounds[i, 1])
        X[:, i] = lo + (val / denom) * (hi - lo)
        col += L
    return X


def _qgate_update(
    alpha: np.ndarray,
    beta: np.ndarray,
    fitness: np.ndarray,
    best_binary: np.ndarray,
    best_fitness: float,
    binary: np.ndarray,
    *,
    delta: float,
    rng: np.random.Generator,
) -> None:
    # 资料 Qgate.m 的逐位更新策略（尽量复刻其 s 的判定逻辑）
    pop_size, n_bits = binary.shape
    for i in range(pop_size):
        for j in range(n_bits):
            A = float(alpha[i, j])
            B = float(beta[i, j])
            x = int(binary[i, j])
            b = int(best_binary[j])

            if (x == 0 and b == 0) or (x == 1 and b == 1):
                e = 0.0
            else:
                # 以下 4 个分支与 Matlab 代码一致
                # x!=b：需要旋转；方向 s 取决于 A*B 以及该个体是否劣于全局最优
                worse = bool(fitness[i] < best_fitness)
                s = 0.0
                prod = A * B
                if x == 0 and b == 1 and worse:
                    if prod > 0:
                        s = 1.0
                    elif prod < 0:
                        s = -1.0
                    elif A == 0:
                        s = 0.0
                    elif B == 0:
                        s = float(np.sign(rng.normal()))
                elif x == 0 and b == 1 and (not worse):
                    if prod > 0:
                        s = -1.0
                    elif prod < 0:
                        s = 1.0
                    elif A == 0:
                        s = float(np.sign(rng.normal()))
                    elif B == 0:
                        s = 0.0
                elif x == 1 and b == 0 and worse:
                    if prod > 0:
                        s = -1.0
                    elif prod < 0:
                        s = 1.0
                    elif A == 0:
                        s = float(np.sign(rng.normal()))
                    elif B == 0:
                        s = 0.0
                elif x == 1 and b == 0 and (not worse):
                    if prod > 0:
                        s = 1.0
                    elif prod < 0:
                        s = -1.0
                    elif A == 0:
                        s = 0.0
                    elif B == 0:
                        s = float(np.sign(rng.normal()))
                e = float(s) * float(delta)

            if e != 0.0:
                ce = math.cos(e)
                se = math.sin(e)
                # y = U @ [A,B]
                A_new = ce * A - se * B
                B_new = se * A + ce * B
                alpha[i, j] = A_new
                beta[i, j] = B_new


def quantum_genetic_algorithm(
    objective: Objective,
    *,
    bit_lengths: Sequence[int],
    bounds: Sequence[Tuple[float, float]],
    params: Optional[QGAParams] = None,
) -> Dict[str, Any]:
    """
    量子遗传算法（QGA），连续变量通过二进制编码映射到实数范围。

    Args:
        objective: 目标函数 f(X)->float（默认最大化）。
        bit_lengths: 每个变量的二进制长度（例如 [20,20]）。
        bounds: 每个变量的 (low,high)。
        params: QGAParams。

    Returns:
        dict:
            - best_x: (n_var,)
            - best_binary: (n_bits,)
            - best_fitness: float（原始目标函数值）
            - trace_best: (generations,)
    """
    p = params or QGAParams()
    bit_lengths = [int(x) for x in bit_lengths]
    n_var = len(bit_lengths)
    n_bits = int(sum(bit_lengths))
    bounds_arr = _ensure_bounds(bounds, n_var=n_var)

    rng = np.random.default_rng(p.seed)
    alpha, beta = _init_quantum_pop(rng, int(p.pop_size), n_bits)

    # internal_fitness：始终做“最大化”
    def eval_pop(binary: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X = _decode_binary_to_real(binary, bit_lengths, bounds_arr)
        raw = np.array([float(objective(x)) for x in X], dtype=float)
        if bool(p.maximize):
            fit = raw
        else:
            fit = -raw
        return fit, X

    binary = _collapse(alpha, beta, rng=rng)
    fit, X = eval_pop(binary)

    best_idx = int(np.argmax(fit))
    best_fit = float(fit[best_idx])
    best_binary = binary[best_idx].copy()
    best_x = X[best_idx].copy()

    trace_best = np.zeros(int(p.generations), dtype=float)
    trace_best[0] = float(best_fit)

    for gen in range(1, int(p.generations)):
        binary = _collapse(alpha, beta, rng=rng)
        fit, X = eval_pop(binary)

        _qgate_update(alpha, beta, fit, best_binary, best_fit, binary, delta=float(p.delta), rng=rng)

        new_best_idx = int(np.argmax(fit))
        new_best_fit = float(fit[new_best_idx])
        if new_best_fit > best_fit:
            best_fit = new_best_fit
            best_binary = binary[new_best_idx].copy()
            best_x = X[new_best_idx].copy()
        trace_best[gen] = best_fit

    best_raw = float(best_fit if p.maximize else -best_fit)
    return {"best_x": best_x, "best_binary": best_binary, "best_fitness": best_raw, "trace_best": trace_best}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：QGA 连续优化。

    Args:
        data: dict，包含：
            - objective: callable，输入 x:(n_var,) -> float
            - bit_lengths: list[int]
            - bounds: list[(low,high)]
        params:
            - pop_size, generations, delta, seed, maximize

    Returns:
        dict: quantum_genetic_algorithm() 的返回值
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")
    if "objective" not in data or "bit_lengths" not in data or "bounds" not in data:
        raise TypeError("data 必须包含 objective/bit_lengths/bounds。")
    objective = data["objective"]
    if not callable(objective):
        raise TypeError("data.objective 必须为可调用函数。")

    p = QGAParams(
        pop_size=int(params.get("pop_size", 40)),
        generations=int(params.get("generations", 200)),
        delta=float(params.get("delta", 0.01 * math.pi)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
        maximize=bool(params.get("maximize", True)),
    )
    return quantum_genetic_algorithm(objective, bit_lengths=data["bit_lengths"], bounds=data["bounds"], params=p)


if __name__ == "__main__":
    # Mock Data：复刻资料 Objfunction.m 的测试函数（最大化）
    def obj(x: np.ndarray) -> float:
        return float(math.sin(4 * math.pi * x[0]) * x[0] + math.sin(20 * math.pi * x[1]) * x[1])

    out = solve(
        {"objective": obj, "bit_lengths": [20, 20], "bounds": [(-3.0, 12.1), (4.1, 5.8)]},
        {"pop_size": 40, "generations": 120, "seed": 0, "maximize": True},
    )
    print("best_x =", np.round(out["best_x"], 6))
    print("best_fitness =", round(float(out["best_fitness"]), 6))

