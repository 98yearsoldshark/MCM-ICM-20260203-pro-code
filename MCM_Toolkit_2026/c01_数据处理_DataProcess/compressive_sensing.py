# -*- coding: utf-8 -*-
# 压缩感知（Compressed Sensing）：从欠定观测 y = A x 重建稀疏信号 x
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../基于压缩感知算法的数据压缩与复原代码
#
# 说明：
# - 这里给出两个常用重建方法（基于 sklearn）：
#   1) OMP（Orthogonal Matching Pursuit）：指定稀疏度 k
#   2) LASSO：L1 正则回归（alpha 控制稀疏性）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from sklearn.linear_model import Lasso, OrthogonalMatchingPursuit

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def reconstruct_sparse_signal(
    A: Union[np.ndarray, list],
    y: Union[np.ndarray, list],
    *,
    method: str = "omp",
    n_nonzero_coefs: Optional[int] = None,
    alpha: float = 0.01,
    fit_intercept: bool = False,
    max_iter: int = 5000,
) -> Dict[str, Any]:
    """
    稀疏信号重建：求解 y ≈ A x。

    Args:
        A: 观测矩阵 (m×n)。
        y: 观测向量 (m,) 或矩阵 (m×k)。
        method: {'omp','lasso'}。
        n_nonzero_coefs: OMP 稀疏度（非零系数个数），建议给定；若 None 则由 OMP 自行停止（不一定最优）。
        alpha: LASSO 正则强度（越大越稀疏）。
        fit_intercept: 是否拟合截距（通常压缩感知不需要）。
        max_iter: LASSO 最大迭代次数。

    Returns:
        dict:
            - x_hat: 重建信号 (n,) 或 (n×k)
            - coef_: 同 x_hat（兼容 sklearn 命名）
    """
    A = np.asarray(A, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if A.ndim != 2:
        raise ValueError("A 必须为二维矩阵 (m×n)。")
    m, n = A.shape
    if y_arr.ndim == 1:
        if y_arr.shape[0] != m:
            raise ValueError("y 长度必须等于 A 的行数 m。")
    elif y_arr.ndim == 2:
        if y_arr.shape[0] != m:
            raise ValueError("y 行数必须等于 A 的行数 m。")
    else:
        raise ValueError("y 必须为 (m,) 或 (m×k)。")

    method = str(method).lower()
    if method == "omp":
        model = OrthogonalMatchingPursuit(n_nonzero_coefs=n_nonzero_coefs, fit_intercept=bool(fit_intercept))
    elif method == "lasso":
        model = Lasso(alpha=float(alpha), fit_intercept=bool(fit_intercept), max_iter=int(max_iter))
    else:
        raise ValueError("method 必须为 'omp' 或 'lasso'。")

    model.fit(A, y_arr)

    coef = model.coef_
    # sklearn 在多输出时 coef_ 形状可能为 (k×n)，这里统一成 (n×k)
    if coef.ndim == 2:
        x_hat = coef.T
    else:
        x_hat = coef.reshape(-1)
    return {"x_hat": np.asarray(x_hat, dtype=float), "coef_": np.asarray(x_hat, dtype=float)}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：压缩感知重建。

    Args:
        data: dict，包含：
            - A: (m×n)
            - y: (m,) 或 (m×k)
        params: 参数：
            - method: 'omp' | 'lasso'
            - n_nonzero_coefs: int | None
            - alpha: float（lasso）
            - fit_intercept: bool
            - max_iter: int（lasso）

    Returns:
        dict: {'x_hat': ...}
    """
    params = params or {}
    if not isinstance(data, dict) or "A" not in data or "y" not in data:
        raise TypeError("data 必须为 dict，且包含 A 与 y。")
    return reconstruct_sparse_signal(
        data["A"],
        data["y"],
        method=str(params.get("method", "omp")),
        n_nonzero_coefs=params.get("n_nonzero_coefs"),
        alpha=float(params.get("alpha", 0.01)),
        fit_intercept=bool(params.get("fit_intercept", False)),
        max_iter=int(params.get("max_iter", 5000)),
    )


if __name__ == "__main__":
    # Mock Data：生成稀疏向量 x（n=200, k=10），观测 m=80
    rng = np.random.default_rng(0)
    n = 200
    m = 80
    k = 10
    A = rng.normal(0, 1, size=(m, n))
    x_true = np.zeros(n, dtype=float)
    idx = rng.choice(n, size=k, replace=False)
    x_true[idx] = rng.normal(0, 1, size=k)
    y = A @ x_true + rng.normal(0, 0.01, size=m)

    out = solve({"A": A, "y": y}, {"method": "omp", "n_nonzero_coefs": k})
    x_hat = out["x_hat"]
    err = np.linalg.norm(x_hat - x_true) / (np.linalg.norm(x_true) + 1e-12)
    print("relative_error =", err)
    print("support_true =", sorted(idx.tolist())[:10], "...")
    print("support_hat  =", sorted(np.where(np.abs(x_hat) > 1e-3)[0].tolist())[:10], "...")

