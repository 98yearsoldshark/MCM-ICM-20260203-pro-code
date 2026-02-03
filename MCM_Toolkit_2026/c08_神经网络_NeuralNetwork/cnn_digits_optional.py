# -*- coding: utf-8 -*-
# CNN 卷积神经网络（可选：需要安装 tensorflow）
#
# 资料目录中的 CNN 示例使用 TensorFlow 1.x + MNIST 下载：
# - 5、30个常用算法Python代码/.../卷积神经网络模型Python代码.txt
#
# 为了避免“网络下载数据集 + 旧版 TF API”，这里改成：
# - 数据：sklearn 自带的 digits（8×8 灰度图），无需联网
# - 框架：tensorflow.keras（若未安装 tensorflow，则提示安装）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d


def _require_tensorflow() -> Any:
    try:
        import tensorflow as tf  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("该脚本需要 tensorflow：可选安装 `pip install tensorflow`。") from e
    return tf


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：训练一个简单 CNN（图像分类）。

    Args:
        data: (X,y) / {'X','y'} / DataFrame（不建议；图像一般用 ndarray）
            - X: (n,h,w) 或 (n,h,w,c)
            - y: (n,)
        params:
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - epochs: int（默认 5）
            - batch_size: int（默认 32）
            - verbose: int（默认 0）

    Returns:
        dict:
            - model: keras.Model
            - history: dict
            - metrics: dict（test_loss/test_accuracy）
    """
    tf = _require_tensorflow()
    params = params or {}

    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y).astype(int)

    # 把 (n, h*w) 还原为方图：仅用于 digits 这类数据；更一般的图像请直接传 (n,h,w[,c])
    if X.ndim == 2 and X.shape[1] > 1:
        side = int(np.sqrt(X.shape[1]))
        if side * side != X.shape[1]:
            raise ValueError("X 为二维时，列数必须是完全平方数（才能还原为方形图像）。")
        X_img = X.reshape(-1, side, side, 1)
    else:
        X_img = np.asarray(X, dtype=float)
        if X_img.ndim == 3:
            X_img = X_img[..., None]
        if X_img.ndim != 4:
            raise ValueError("X 需要是 (n,h,w) 或 (n,h,w,c) 或 (n,h*w)。")

    X_img = X_img.astype("float32")
    # 简单归一化（digits 原始范围约 0~16）
    mx = float(np.max(X_img))
    if mx > 0:
        X_img = X_img / mx

    num_classes = int(np.max(y)) + 1
    n = int(X_img.shape[0])
    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))
    epochs = int(params.get("epochs", 5))
    batch_size = int(params.get("batch_size", 32))
    verbose = int(params.get("verbose", 0))

    # 手写切分，避免额外依赖
    rng = np.random.default_rng(random_state)
    idx = np.arange(n)
    rng.shuffle(idx)
    split = int(round(n * (1.0 - test_size)))
    train_idx, test_idx = idx[:split], idx[split:]
    X_train, y_train = X_img[train_idx], y[train_idx]
    X_test, y_test = X_img[test_idx], y[test_idx]

    keras = tf.keras
    model = keras.Sequential(
        [
            keras.layers.Input(shape=tuple(X_img.shape[1:])),
            keras.layers.Conv2D(16, (3, 3), padding="same", activation="relu"),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(32, (3, 3), padding="same", activation="relu"),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dense(num_classes, activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    hist = model.fit(X_train, y_train, validation_split=0.1, epochs=epochs, batch_size=batch_size, verbose=verbose)
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    return {"model": model, "history": dict(hist.history), "metrics": {"test_loss": float(test_loss), "test_accuracy": float(test_acc)}}


if __name__ == "__main__":
    try:
        from sklearn.datasets import load_digits
    except Exception:
        raise SystemExit("缺少 scikit-learn，无法运行 demo（但本 Toolkit 默认依赖 sklearn）。")

    try:
        _require_tensorflow()
    except ImportError as e:
        print(str(e))
        raise SystemExit(0)

    digits = load_digits()
    # digits.data: (n,64)；digits.images: (n,8,8)
    out = solve((digits.data, digits.target), {"epochs": 5, "verbose": 0})
    print(out["metrics"])

