# -*- coding: utf-8 -*-
# 朴素贝叶斯（Gaussian/Multinomial/Bernoulli）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import BernoulliNB, GaussianNB, MultinomialNB

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：朴素贝叶斯分类模型训练与评估。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - model: {"gaussian","multinomial","bernoulli"}（默认 gaussian）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True）
            - model_params: dict（传给具体 NB 模型）

    Returns:
        dict:
            - model: 训练好的模型
            - metrics: dict（accuracy/confusion_matrix/classification_report）
            - y_pred: 测试集预测标签
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X_arr = to_numpy_2d(xy.X)
    y_arr = to_numpy_1d(xy.y)

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))
    stratify = bool(get_param(params, "stratify", True))
    stratify_y = y_arr if (stratify and np.unique(y_arr).size > 1) else None

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    kind = str(get_param(params, "model", "gaussian")).lower()
    model_params = dict(get_param(params, "model_params", {}) or {})
    if kind == "gaussian":
        model = GaussianNB(**model_params)
    elif kind == "multinomial":
        model = MultinomialNB(**model_params)
    elif kind == "bernoulli":
        model = BernoulliNB(**model_params)
    else:
        raise ValueError(f"不支持的 model: {kind}")

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }
    return {"model": model, "metrics": metrics, "y_pred": y_pred}


if __name__ == "__main__":
    # Mock Data：二分类
    rng = np.random.default_rng(0)
    X0 = rng.normal(loc=-1.0, scale=1.0, size=(150, 2))
    X1 = rng.normal(loc=1.0, scale=1.0, size=(150, 2))
    X = np.vstack([X0, X1])
    y = np.array([0] * 150 + [1] * 150)
    out = solve((X, y), params={"model": "gaussian"})
    print(out["metrics"])
