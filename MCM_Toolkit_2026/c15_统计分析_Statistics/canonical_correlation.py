# -*- coding: utf-8 -*-
# 典型相关分析（CCA）：两组变量的相关结构分析（sklearn.cross_decomposition.CCA）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../相关性分析类题型参考代码.../典型相关分析matlab代码.rar

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from sklearn.cross_decomposition import CCA

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def cca_fit_transform(
    X: Union[np.ndarray, list],
    Y: Union[np.ndarray, list],
    *,
    n_components: int = 2,
    scale: bool = True,
    max_iter: int = 500,
    tol: float = 1e-6,
) -> Dict[str, Any]:
    """
    拟合 CCA 并得到典型变量（canonical variates）。

    Args:
        X: 第一组变量矩阵 (n×p)。
        Y: 第二组变量矩阵 (n×q)。
        n_components: 典型维度数。
        scale: 是否标准化（默认 True）。
        max_iter: 最大迭代次数。
        tol: 收敛阈值。

    Returns:
        dict:
            - model: CCA 模型
            - X_c, Y_c: 典型变量 (n×k)
            - x_weights, y_weights: 权重（p×k, q×k）
            - corr: 每个典型维度的相关系数（k,）
    """
    X_arr = np.asarray(X, dtype=float)
    Y_arr = np.asarray(Y, dtype=float)
    if X_arr.ndim != 2 or Y_arr.ndim != 2:
        raise ValueError("X 与 Y 必须为二维矩阵。")
    if X_arr.shape[0] != Y_arr.shape[0]:
        raise ValueError("X 与 Y 的样本数（行数）必须一致。")

    k = int(n_components)
    if k < 1:
        raise ValueError("n_components 必须 >= 1。")

    model = CCA(n_components=k, scale=bool(scale), max_iter=int(max_iter), tol=float(tol))
    X_c, Y_c = model.fit_transform(X_arr, Y_arr)

    corr = []
    for i in range(k):
        a = X_c[:, i]
        b = Y_c[:, i]
        ca = np.corrcoef(a, b)[0, 1]
        corr.append(float(ca))

    return {
        "model": model,
        "X_c": np.asarray(X_c, dtype=float),
        "Y_c": np.asarray(Y_c, dtype=float),
        "x_weights": np.asarray(model.x_weights_, dtype=float),
        "y_weights": np.asarray(model.y_weights_, dtype=float),
        "corr": np.asarray(corr, dtype=float),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：CCA。

    Args:
        data: dict，包含：
            - X: (n×p)
            - Y: (n×q)
        params: 参数：
            - n_components: int
            - scale: bool
            - max_iter: int
            - tol: float

    Returns:
        dict: 见 cca_fit_transform() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "X" not in data or "Y" not in data:
        raise TypeError("data 必须为 dict，且包含 X 与 Y。")
    return cca_fit_transform(
        data["X"],
        data["Y"],
        n_components=int(params.get("n_components", 2)),
        scale=bool(params.get("scale", True)),
        max_iter=int(params.get("max_iter", 500)),
        tol=float(params.get("tol", 1e-6)),
    )


if __name__ == "__main__":
    # Mock Data：构造两组存在相关结构的数据
    rng = np.random.default_rng(0)
    n = 300
    z1 = rng.normal(0, 1, size=n)
    z2 = rng.normal(0, 1, size=n)

    X = np.column_stack(
        [
            z1 + 0.1 * rng.normal(0, 1, size=n),
            0.5 * z1 + 0.2 * rng.normal(0, 1, size=n),
            z2 + 0.1 * rng.normal(0, 1, size=n),
        ]
    )
    Y = np.column_stack(
        [
            0.8 * z1 + 0.2 * rng.normal(0, 1, size=n),
            1.2 * z2 + 0.2 * rng.normal(0, 1, size=n),
        ]
    )

    out = solve({"X": X, "Y": Y}, {"n_components": 2})
    print("corr =", np.round(out["corr"], 4))

