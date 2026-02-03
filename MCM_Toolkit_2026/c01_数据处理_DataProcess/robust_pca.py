# -*- coding: utf-8 -*-
# Robust PCA（RPCA / PCP）：将矩阵分解为低秩 L + 稀疏 S
#
# 典型用途：
# - 异常值检测：S 代表“异常/离群/突变”部分
# - 背景建模：L 代表“主要结构/趋势/背景”
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../基于RPCA异常值检测代码
#
# 算法：Inexact Augmented Lagrange Multiplier (IALM)
# - 目标：min ||L||_* + lambda*||S||_1  s.t. M = L + S
# - 核范数通过奇异值阈值化（SVT）实现

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _svt(X: np.ndarray, tau: float) -> np.ndarray:
    """奇异值阈值化（SVT）：对奇异值做 soft-threshold。"""
    U, s, Vt = np.linalg.svd(X, full_matrices=False)
    s_thr = np.maximum(s - float(tau), 0.0)
    return (U * s_thr) @ Vt


def _soft_threshold(X: np.ndarray, tau: float) -> np.ndarray:
    """逐元素 soft-threshold。"""
    tau = float(tau)
    return np.sign(X) * np.maximum(np.abs(X) - tau, 0.0)


def robust_pca(
    M: Union[np.ndarray, list],
    *,
    lam: Optional[float] = None,
    mu: Optional[float] = None,
    max_iter: int = 1000,
    tol: float = 1e-7,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Robust PCA（PCP）分解：M = L + S。

    Args:
        M: 输入矩阵（m×n）。
        lam: 稀疏项权重 λ；若为 None，常用默认 1/sqrt(max(m,n))。
        mu: 增广拉格朗日参数 μ；若为 None，使用经验初始化。
        max_iter: 最大迭代次数。
        tol: 收敛阈值（相对误差）。
        verbose: 是否打印迭代信息。

    Returns:
        dict:
            - L: 低秩矩阵
            - S: 稀疏矩阵（异常部分）
            - n_iter: 实际迭代次数
            - rel_err: 最后相对误差 ||M-L-S||_F / ||M||_F
    """
    A = np.asarray(M, dtype=float)
    if A.ndim != 2:
        raise ValueError("M 必须为二维矩阵。")
    m, n = A.shape
    norm_M = np.linalg.norm(A, ord="fro")
    if norm_M == 0:
        return {"L": np.zeros_like(A), "S": np.zeros_like(A), "n_iter": 0, "rel_err": 0.0}

    lam = float(lam) if lam is not None else 1.0 / np.sqrt(max(m, n))

    # μ 的经验初始化（来自常见实现）
    mu = float(mu) if mu is not None else (m * n) / (4.0 * np.sum(np.abs(A)) + 1e-12)

    L = np.zeros_like(A)
    S = np.zeros_like(A)
    Y = A / max(np.linalg.norm(A, 2), np.linalg.norm(A.ravel(), np.inf) / lam)

    for it in range(1, int(max_iter) + 1):
        # 1) 更新 L：SVT
        L = _svt(A - S + (1.0 / mu) * Y, 1.0 / mu)

        # 2) 更新 S：soft threshold
        S = _soft_threshold(A - L + (1.0 / mu) * Y, lam / mu)

        # 3) 更新乘子
        R = A - L - S
        Y = Y + mu * R

        rel_err = float(np.linalg.norm(R, ord="fro") / norm_M)
        if verbose and (it == 1 or it % 50 == 0):
            print(f"[RPCA] iter={it} rel_err={rel_err:.3e}")
        if rel_err < float(tol):
            return {"L": L, "S": S, "n_iter": it, "rel_err": rel_err, "lambda": lam, "mu": mu}

    rel_err = float(np.linalg.norm(A - L - S, ord="fro") / norm_M)
    return {"L": L, "S": S, "n_iter": int(max_iter), "rel_err": rel_err, "lambda": lam, "mu": mu}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：RPCA 分解。

    Args:
        data: 矩阵或 dict：
            - 直接传入 M
            - dict: {'M': M}
        params: 参数：
            - lam: float | None
            - mu: float | None
            - max_iter: int
            - tol: float
            - verbose: bool

    Returns:
        dict: 见 robust_pca() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        M = data.get("M")
    else:
        M = data
    if M is None:
        raise ValueError("data 需要提供矩阵 M。")
    return robust_pca(
        M,
        lam=params.get("lam"),
        mu=params.get("mu"),
        max_iter=int(params.get("max_iter", 1000)),
        tol=float(params.get("tol", 1e-7)),
        verbose=bool(params.get("verbose", False)),
    )


if __name__ == "__main__":
    # Mock Data：低秩 + 稀疏异常
    rng = np.random.default_rng(0)
    U = rng.normal(0, 1, size=(50, 3))
    V = rng.normal(0, 1, size=(3, 40))
    L_true = U @ V
    S_true = np.zeros_like(L_true)
    idx = rng.choice(L_true.size, size=200, replace=False)
    S_true.ravel()[idx] = rng.normal(0, 10, size=idx.size)
    M = L_true + S_true

    out = solve(M, {"max_iter": 1000, "tol": 1e-6})
    print("rel_err =", out["rel_err"], "n_iter =", out["n_iter"])
    print("||S_true||_0 =", int(np.count_nonzero(S_true)), "||S_hat||_0 =", int(np.count_nonzero(np.abs(out["S"]) > 1e-6)))

