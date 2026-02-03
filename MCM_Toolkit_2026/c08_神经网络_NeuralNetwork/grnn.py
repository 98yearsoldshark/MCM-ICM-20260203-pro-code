# -*- coding: utf-8 -*-
# GRNN（General Regression Neural Network，广义回归神经网络）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/.../基于广义回归神经网络货运量预测代码/chapter8.1.m
#
# 核心思想：
# - GRNN 本质是“高斯核回归/Parzen 窗”：
#   y(x) = sum_i y_i * exp(-||x-x_i||^2 / (2*sigma^2)) / sum_i exp(...)
# - 训练几乎不需要迭代：主要就是选择平滑参数 sigma（Matlab 里叫 spread）

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
from sklearn.model_selection import KFold, train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d


@dataclass
class GRNNModel:
    X_train: np.ndarray  # (n,d)
    y_train: np.ndarray  # (n,1) or (n,m)
    sigma: float


def _as_2d_y(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        return y.reshape(-1, 1)
    if y.ndim == 2:
        return y
    raise ValueError("y 必须为 1D 或 2D。")


def fit_grnn(X_train: np.ndarray, y_train: np.ndarray, *, sigma: float) -> GRNNModel:
    sigma = float(sigma)
    if sigma <= 0:
        raise ValueError("sigma 必须为正数。")
    X_train = np.asarray(X_train, dtype=float)
    if X_train.ndim != 2:
        raise ValueError("X_train 必须为二维数组 (n,d)。")
    y2 = _as_2d_y(y_train)
    if y2.shape[0] != X_train.shape[0]:
        raise ValueError("X_train 与 y_train 的样本数不一致。")
    return GRNNModel(X_train=X_train, y_train=y2, sigma=sigma)


def predict_grnn(model: GRNNModel, X: np.ndarray) -> np.ndarray:
    Xq = np.asarray(X, dtype=float)
    if Xq.ndim == 1:
        Xq = Xq.reshape(1, -1)
    if Xq.ndim != 2:
        raise ValueError("X 必须为 1D 或 2D。")
    Xt = model.X_train
    yt = model.y_train
    sigma2 = float(model.sigma) ** 2
    # 计算 (m,n) 的平方距离矩阵
    diff = Xq[:, None, :] - Xt[None, :, :]
    d2 = np.sum(diff * diff, axis=2)
    w = np.exp(-d2 / (2.0 * sigma2))
    wsum = np.sum(w, axis=1, keepdims=True)
    w = w / np.maximum(wsum, 1e-12)
    y_pred = w @ yt
    return y_pred


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


def _select_sigma_cv(
    X: np.ndarray,
    y: np.ndarray,
    sigma_candidates: Sequence[float],
    *,
    folds: int,
    random_state: int,
) -> Tuple[float, Dict[str, Any]]:
    sigmas = [float(s) for s in sigma_candidates]
    sigmas = [s for s in sigmas if s > 0]
    if not sigmas:
        raise ValueError("sigma_candidates 必须包含正数。")

    y2 = _as_2d_y(y)
    kf = KFold(n_splits=int(folds), shuffle=True, random_state=int(random_state))
    mean_mse = []
    for s in sigmas:
        mses = []
        for train_idx, val_idx in kf.split(X):
            m = fit_grnn(X[train_idx], y2[train_idx], sigma=s)
            pred = predict_grnn(m, X[val_idx])
            mses.append(_mse(y2[val_idx], pred))
        mean_mse.append(float(np.mean(mses)))
    best_idx = int(np.argmin(mean_mse))
    return float(sigmas[best_idx]), {"sigma_candidates": sigmas, "cv_mean_mse": mean_mse}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：GRNN 回归。

    Args:
        data: (X,y) / {'X','y'} / DataFrame（+ target_col）
        params:
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - sigma: float（默认 None；若不提供可用 sigma_candidates 做 CV）
            - sigma_candidates: list[float]（例如 np.arange(0.1,2.1,0.1)）
            - cv_folds: int（默认 4）

    Returns:
        dict:
            - model: GRNNModel
            - metrics: dict（mse/r2）
            - y_test_pred: ndarray
            - sigma_cv: dict（若使用 CV）
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y) if np.asarray(xy.y).ndim == 1 else np.asarray(xy.y)
    y2 = _as_2d_y(y)

    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))

    X_train, X_test, y_train, y_test = train_test_split(X, y2, test_size=test_size, random_state=random_state)

    sigma = params.get("sigma")
    sigma_cv = None
    if sigma is None and params.get("sigma_candidates") is not None:
        sigma, sigma_cv = _select_sigma_cv(
            X_train,
            y_train,
            sigma_candidates=params["sigma_candidates"],
            folds=int(params.get("cv_folds", 4)),
            random_state=random_state,
        )
    if sigma is None:
        sigma = 1.0

    model = fit_grnn(X_train, y_train, sigma=float(sigma))
    y_pred = predict_grnn(model, X_test)
    metrics = {"mse": _mse(y_test, y_pred), "r2": _r2(y_test, y_pred), "sigma": float(model.sigma)}

    out = {"model": model, "metrics": metrics, "y_test_pred": y_pred}
    if sigma_cv is not None:
        out["sigma_cv"] = sigma_cv
    return out


if __name__ == "__main__":
    # Mock Data：sin + 噪声回归（可选 CV 选 sigma）
    rng = np.random.default_rng(0)
    X = rng.uniform(-3, 3, size=(200, 1))
    y = np.sin(X[:, 0]) + 0.1 * rng.normal(size=200)

    out = solve((X, y), {"sigma_candidates": [0.2, 0.4, 0.8, 1.2], "cv_folds": 4, "random_state": 0})
    print("sigma =", out["metrics"]["sigma"])
    print("mse   =", round(out["metrics"]["mse"], 6))
    print("r2    =", round(out["metrics"]["r2"], 6))

