# -*- coding: utf-8 -*-
# 感知机（Perceptron）：线性分类基线（sklearn）
#
# 参考来源（资料目录）：
# - 4、Python各类算法代码集合/41-1 .../神经网络分类.py（原代码自写 Perceptron 并联网读取 iris）
#
# 说明：
# - 这里用 sklearn.linear_model.Perceptron 封装，避免手写 bug，同时保持离线可运行

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.linear_model import Perceptron
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：感知机分类训练与评估。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params:
            - target_col: str | None（DataFrame 时必填）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True）
            - model_params: dict（传给 sklearn Perceptron 的参数）

    Returns:
        dict: {'model','metrics','y_pred'}
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y)

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))
    stratify = bool(get_param(params, "stratify", True))
    model_params = dict(get_param(params, "model_params", {}) or {})

    stratify_y = y if (stratify and np.unique(y).size > 1) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    model = Perceptron(random_state=random_state, **model_params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }
    return {"model": model, "metrics": metrics, "y_pred": y_pred}


if __name__ == "__main__":
    # Mock Data：使用 sklearn 自带 iris，构造一个二分类任务（setosa vs versicolor）
    from sklearn.datasets import load_iris

    iris = load_iris()
    X_all = iris.data
    y_all = iris.target

    # 只取前两类，避免多分类对初学者产生“感知机不收敛”的困惑
    mask = y_all < 2
    X = X_all[mask][:, [0, 2]]  # 取两列特征，和资料示意类似
    y = y_all[mask]

    out = solve((X, y), params={"model_params": {"max_iter": 1000, "eta0": 1.0, "tol": 1e-3}})
    print(out["metrics"])

