# -*- coding: utf-8 -*-
# 小波神经网络（Wavelet Neural Network, WNN）——Morlet 小波 + 单隐层回归
#
# 参考来源（资料目录，Matlab 版为在线梯度下降）：
# - 6、按赛题类别划分的常用算法代码/.../小波神经网络的时间序列预测代码/chapter32/wavenn.m
# - 6、按赛题类别划分的常用算法代码/.../小波神经网络的时间序列预测代码/chapter32/mymorlet.m
# - 6、按赛题类别划分的常用算法代码/.../小波神经网络的时间序列预测代码/chapter32/d_mymorlet.m
#
# 说明：
# - 该实现保留了与资料版一致的核心参数：W_in/W_out + a(尺度) + b(平移)
# - 为保证可运行与可复用，训练数据默认做简单 MinMax 归一化（可关闭）

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d


@dataclass
class MinMax01:
    """把数据缩放到 [-1, 1]（类似 Matlab mapminmax 的常用用法）。"""

    data_min: np.ndarray
    data_max: np.ndarray

    @classmethod
    def fit(cls, X: np.ndarray) -> "MinMax01":
        X = np.asarray(X, dtype=float)
        return cls(data_min=np.min(X, axis=0), data_max=np.max(X, axis=0))

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        denom = self.data_max - self.data_min
        denom = np.where(denom == 0, 1.0, denom)
        Z = (X - self.data_min) / denom
        return 2.0 * Z - 1.0

    def inverse_transform(self, Z: np.ndarray) -> np.ndarray:
        Z = np.asarray(Z, dtype=float)
        X01 = 0.5 * (Z + 1.0)
        return X01 * (self.data_max - self.data_min) + self.data_min


def _morlet(t: np.ndarray, omega: float = 1.75) -> np.ndarray:
    # mymorlet.m: exp(-(t.^2)/2) * cos(1.75*t)
    return np.exp(-(t * t) / 2.0) * np.cos(float(omega) * t)


def _d_morlet(t: np.ndarray, omega: float = 1.75) -> np.ndarray:
    # d_mymorlet.m: -1.75*sin(1.75*t).*exp(-(t.^2)/2)-t*cos(1.75*t).*exp(-(t.^2)/2)
    w = float(omega)
    return -w * np.sin(w * t) * np.exp(-(t * t) / 2.0) - t * np.cos(w * t) * np.exp(-(t * t) / 2.0)


@dataclass
class WNNModel:
    W_in: np.ndarray  # (n_hidden, n_features)
    W_out: np.ndarray  # (n_outputs, n_hidden)
    bias_out: np.ndarray  # (n_outputs,)
    a: np.ndarray  # (n_hidden,) 尺度
    b: np.ndarray  # (n_hidden,) 平移
    omega: float = 1.75
    x_scaler: Optional[MinMax01] = None
    y_scaler: Optional[MinMax01] = None


def _as_2d_y(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        return y.reshape(-1, 1)
    if y.ndim == 2:
        return y
    raise ValueError("y 必须为 1D 或 2D。")


def _forward(model: WNNModel, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    前向传播。

    Returns:
        y_hat: (n, n_outputs)
        t: (n, n_hidden) 隐层归一化输入
        phi: (n, n_hidden) 小波激活
    """
    X = np.asarray(X, dtype=float)
    Z = X @ model.W_in.T  # (n,h)
    a = np.maximum(np.asarray(model.a, dtype=float), 1e-6)
    t = (Z - model.b.reshape(1, -1)) / a.reshape(1, -1)
    phi = _morlet(t, omega=float(model.omega))
    y_hat = phi @ model.W_out.T + model.bias_out.reshape(1, -1)
    return y_hat, t, phi


def fit_wavelet_nn(
    X_train: np.ndarray,
    y_train: np.ndarray,
    *,
    n_hidden: int = 6,
    lr_w: float = 0.01,
    lr_ab: float = 0.001,
    epochs: int = 100,
    omega: float = 1.75,
    normalize: bool = True,
    seed: int = 0,
) -> Tuple[WNNModel, Dict[str, Any]]:
    """
    训练小波神经网络（在线 SGD）。

    Args:
        X_train: (n,d)
        y_train: (n,) or (n,m)
        n_hidden: 隐层节点数
        lr_w: 权重学习率（W_in/W_out/bias_out）
        lr_ab: a/b 学习率
        epochs: 迭代轮数
        omega: Morlet 频率参数（资料中为 1.75）
        normalize: 是否对 X/y 做 MinMax 缩放到 [-1,1]
        seed: 随机种子

    Returns:
        (model, info)
    """
    rng = np.random.default_rng(int(seed))
    X = np.asarray(X_train, dtype=float)
    if X.ndim != 2:
        raise ValueError("X_train 必须为二维数组 (n,d)。")
    y2 = _as_2d_y(y_train)
    if y2.shape[0] != X.shape[0]:
        raise ValueError("X_train 与 y_train 的样本数不一致。")

    x_scaler = None
    y_scaler = None
    if normalize:
        x_scaler = MinMax01.fit(X)
        X = x_scaler.transform(X)
        y_scaler = MinMax01.fit(y2)
        y2 = y_scaler.transform(y2)

    n, d = X.shape
    out_dim = int(y2.shape[1])
    h = int(max(1, n_hidden))

    # 参数初始化（与资料版一致：随机正态；a/b 也随机，但保证 a 不为 0）
    W_in = rng.normal(0.0, 1.0, size=(h, d))
    W_out = rng.normal(0.0, 1.0, size=(out_dim, h))
    bias_out = np.zeros(out_dim, dtype=float)
    a = np.abs(rng.normal(1.0, 0.5, size=h)) + 0.5
    b = rng.normal(0.0, 0.5, size=h)

    model = WNNModel(W_in=W_in, W_out=W_out, bias_out=bias_out, a=a, b=b, omega=float(omega), x_scaler=x_scaler, y_scaler=y_scaler)

    loss_hist = np.zeros(int(epochs), dtype=float)
    for ep in range(int(epochs)):
        # 打乱顺序（SGD）
        idx = rng.permutation(n)
        total = 0.0
        for ii in idx:
            x = X[ii : ii + 1, :]  # (1,d)
            y = y2[ii : ii + 1, :]  # (1,m)
            y_hat, t, phi = _forward(model, x)
            e = (y_hat - y).reshape(-1)  # (m,)
            total += float(np.mean(e * e))

            # 备份 W_out（用于计算 g）
            W_out_old = model.W_out.copy()

            # 更新输出层
            model.W_out = model.W_out - float(lr_w) * np.outer(e, phi.reshape(-1))
            model.bias_out = model.bias_out - float(lr_w) * e

            # 反传到隐层参数
            g = W_out_old.T @ e  # (h,)
            dphi = _d_morlet(t.reshape(-1), omega=float(model.omega))  # (h,)
            a_safe = np.maximum(model.a, 1e-6)
            common = g * dphi  # (h,)

            # W_in 梯度：common/a * x
            model.W_in = model.W_in - float(lr_w) * np.outer(common / a_safe, x.reshape(-1))
            # b 梯度：-common/a -> 更新时 +lr * common/a
            model.b = model.b + float(lr_ab) * (common / a_safe)
            # a 梯度：-common * t / a -> 更新时 +lr * common * t / a
            model.a = model.a + float(lr_ab) * (common * t.reshape(-1) / a_safe)
            model.a = np.maximum(model.a, 1e-6)

        loss_hist[ep] = total / float(n)

    info = {"loss_history": loss_hist}
    return model, info


def predict_wavelet_nn(model: WNNModel, X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(1, -1)
    if model.x_scaler is not None:
        X = model.x_scaler.transform(X)
    y_hat, _, _ = _forward(model, X)
    if model.y_scaler is not None:
        y_hat = model.y_scaler.inverse_transform(y_hat)
    return y_hat


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
    统一接口：小波神经网络回归。

    Args:
        data: (X,y) / {'X','y'} / DataFrame（+ target_col）
        params:
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - n_hidden: int（默认 6）
            - lr_w: float（默认 0.01）
            - lr_ab: float（默认 0.001）
            - epochs: int（默认 100）
            - omega: float（默认 1.75）
            - normalize: bool（默认 True）

    Returns:
        dict:
            - model: WNNModel
            - metrics: dict（mse/r2）
            - y_test_pred: ndarray
            - train_info: dict
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y) if np.asarray(xy.y).ndim == 1 else np.asarray(xy.y)
    y2 = _as_2d_y(y)

    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))
    X_train, X_test, y_train, y_test = train_test_split(X, y2, test_size=test_size, random_state=random_state)

    model, train_info = fit_wavelet_nn(
        X_train,
        y_train,
        n_hidden=int(params.get("n_hidden", 6)),
        lr_w=float(params.get("lr_w", 0.01)),
        lr_ab=float(params.get("lr_ab", 0.001)),
        epochs=int(params.get("epochs", 100)),
        omega=float(params.get("omega", 1.75)),
        normalize=bool(params.get("normalize", True)),
        seed=random_state,
    )
    y_pred = predict_wavelet_nn(model, X_test)
    metrics = {"mse": _mse(y_test, y_pred), "r2": _r2(y_test, y_pred)}
    return {"model": model, "metrics": metrics, "y_test_pred": y_pred, "train_info": train_info}


if __name__ == "__main__":
    # Mock Data：时间序列（sin）做 1 步预测
    rng = np.random.default_rng(0)
    t = np.linspace(0, 20, 400)
    series = np.sin(t) + 0.05 * rng.normal(size=t.size)

    # 构造监督学习样本：用过去 5 个点预测下一个点
    lag = 5
    X = np.stack([series[i : i + lag] for i in range(series.size - lag - 1)], axis=0)
    y = series[lag + 1 :]

    out = solve((X, y), {"n_hidden": 6, "epochs": 60, "lr_w": 0.01, "lr_ab": 0.001, "random_state": 0, "normalize": True})
    print("mse =", round(out["metrics"]["mse"], 6))
    print("r2  =", round(out["metrics"]["r2"], 6))

