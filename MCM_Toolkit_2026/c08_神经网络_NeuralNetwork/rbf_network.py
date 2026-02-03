# -*- coding: utf-8 -*-
# RBF 神经网络（Radial Basis Function Network）——回归基线
#
# 参考来源（资料目录，Matlab 版多用于时间序列/混沌预测）：
# - 6、按赛题类别划分的常用算法代码/.../混沌时间序列的RBF神经网络预测代码/Main_RBF*.m
# - 6、按赛题类别划分的常用算法代码/.../GA优化后的RBF神经网络优化分析代码/*.m
#
# 本实现特点：
# - centers：KMeans 选取（也可外部传入）
# - sigma：可手动指定；否则用“中心间距离的中位数”自适应
# - weights：线性最小二乘/岭回归闭式解（比梯度下降更稳定）

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d


@dataclass
class RBFModel:
    centers: np.ndarray  # (m,d)
    sigma: float
    weights: np.ndarray  # (m(+bias), out_dim)
    include_bias: bool = True


def _as_2d_y(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        return y.reshape(-1, 1)
    if y.ndim == 2:
        return y
    raise ValueError("y 必须为 1D 或 2D。")


def _estimate_sigma(centers: np.ndarray) -> float:
    C = np.asarray(centers, dtype=float)
    if C.shape[0] <= 1:
        return 1.0
    diff = C[:, None, :] - C[None, :, :]
    d = np.sqrt(np.sum(diff * diff, axis=2))
    d = d[np.triu_indices(d.shape[0], k=1)]
    d = d[d > 0]
    if d.size == 0:
        return 1.0
    return float(np.median(d))


def _rbf_features(X: np.ndarray, centers: np.ndarray, sigma: float) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    C = np.asarray(centers, dtype=float)
    sigma = float(sigma)
    if sigma <= 0:
        raise ValueError("sigma 必须为正数。")
    diff = X[:, None, :] - C[None, :, :]
    d2 = np.sum(diff * diff, axis=2)
    return np.exp(-d2 / (2.0 * sigma * sigma))


def fit_rbf_network(
    X_train: np.ndarray,
    y_train: np.ndarray,
    *,
    n_centers: int = 20,
    sigma: Optional[float] = None,
    ridge_alpha: float = 1e-6,
    include_bias: bool = True,
    random_state: int = 0,
) -> RBFModel:
    X_train = np.asarray(X_train, dtype=float)
    if X_train.ndim != 2:
        raise ValueError("X_train 必须为二维数组 (n,d)。")
    y2 = _as_2d_y(y_train)
    if y2.shape[0] != X_train.shape[0]:
        raise ValueError("X_train 与 y_train 的样本数不一致。")

    n = int(X_train.shape[0])
    m = int(max(2, min(int(n_centers), n)))

    km = KMeans(n_clusters=m, n_init=10, random_state=int(random_state))
    km.fit(X_train)
    centers = np.asarray(km.cluster_centers_, dtype=float)

    sigma_use = float(_estimate_sigma(centers) if sigma is None else float(sigma))
    Phi = _rbf_features(X_train, centers, sigma=sigma_use)
    if include_bias:
        Phi = np.concatenate([Phi, np.ones((n, 1), dtype=float)], axis=1)

    # Ridge closed-form: (Phi^T Phi + αI) W = Phi^T y
    A = Phi.T @ Phi
    A = A + float(ridge_alpha) * np.eye(A.shape[0], dtype=float)
    B = Phi.T @ y2
    W = np.linalg.solve(A, B)
    return RBFModel(centers=centers, sigma=sigma_use, weights=W, include_bias=bool(include_bias))


def predict_rbf_network(model: RBFModel, X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(1, -1)
    Phi = _rbf_features(X, model.centers, sigma=float(model.sigma))
    if model.include_bias:
        Phi = np.concatenate([Phi, np.ones((Phi.shape[0], 1), dtype=float)], axis=1)
    return Phi @ model.weights


def _mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = _as_2d_y(y_true)
    y_pred = _as_2d_y(y_pred)
    return float(np.mean((y_true - y_pred) ** 2))


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = _as_2d_y(y_true)
    y_pred = _as_2d_y(y_pred)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true, axis=0, keepdims=True)) ** 2))
    return 1.0 - ss_res / (ss_tot + 1e-12)


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：RBF 网络回归。

    Args:
        data: (X,y) / {'X','y'} / DataFrame（+ target_col）
        params:
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - n_centers: int（默认 20）
            - sigma: float（默认 None，自适应）
            - ridge_alpha: float（默认 1e-6）
            - include_bias: bool（默认 True）

    Returns:
        dict:
            - model: RBFModel
            - metrics: dict（mse/r2/sigma）
            - y_test_pred: ndarray
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y) if np.asarray(xy.y).ndim == 1 else np.asarray(xy.y)
    y2 = _as_2d_y(y)

    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))
    X_train, X_test, y_train, y_test = train_test_split(X, y2, test_size=test_size, random_state=random_state)

    model = fit_rbf_network(
        X_train,
        y_train,
        n_centers=int(params.get("n_centers", 20)),
        sigma=None if params.get("sigma") is None else float(params.get("sigma")),
        ridge_alpha=float(params.get("ridge_alpha", 1e-6)),
        include_bias=bool(params.get("include_bias", True)),
        random_state=random_state,
    )
    y_pred = predict_rbf_network(model, X_test)
    metrics = {"mse": _mse(y_test, y_pred), "r2": _r2(y_test, y_pred), "sigma": float(model.sigma)}
    return {"model": model, "metrics": metrics, "y_test_pred": y_pred}


if __name__ == "__main__":
    # Mock Data：二维输入的非线性回归
    rng = np.random.default_rng(0)
    X = rng.uniform(-2, 2, size=(400, 2))
    y = np.sin(X[:, 0]) + 0.5 * np.cos(2 * X[:, 1]) + 0.1 * rng.normal(size=400)
    out = solve((X, y), {"n_centers": 30, "random_state": 0})
    print("sigma =", out["metrics"]["sigma"])
    print("mse   =", round(out["metrics"]["mse"], 6))
    print("r2    =", round(out["metrics"]["r2"], 6))

