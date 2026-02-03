# -*- coding: utf-8 -*-
# K 近邻：分类 / 回归（支持可选标准化）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：KNN 分类/回归训练与评估。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - task: {"classification","regression"}（默认 classification）
            - n_neighbors: int（默认 5）
            - weights: {"uniform","distance"}（默认 uniform）
            - standardize: bool（默认 True；KNN 对尺度敏感，建议 True）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）

    Returns:
        dict:
            - model: 训练好的 Pipeline/模型
            - metrics: dict
            - y_pred: 测试集预测
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X_arr = to_numpy_2d(xy.X)
    y_arr = to_numpy_1d(xy.y)

    task = str(get_param(params, "task", "classification")).lower()
    n_neighbors = int(get_param(params, "n_neighbors", 5))
    weights = str(get_param(params, "weights", "uniform"))
    standardize = bool(get_param(params, "standardize", True))

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state, stratify=y_arr if task == "classification" else None
    )

    if task == "classification":
        estimator = KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights)
    elif task == "regression":
        estimator = KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights)
    else:
        raise ValueError(f"不支持的 task: {task}")

    if standardize:
        model = Pipeline([("scaler", StandardScaler()), ("knn", estimator)])
    else:
        model = estimator

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics: Dict[str, Any]
    if task == "classification":
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            "classification_report": classification_report(y_test, y_pred, zero_division=0),
        }
    else:
        metrics = {
            "r2": float(r2_score(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        }

    return {"model": model, "metrics": metrics, "y_pred": y_pred}


if __name__ == "__main__":
    # Mock Data：分类
    rng = np.random.default_rng(0)
    X0 = rng.normal(loc=-1.0, scale=1.0, size=(120, 2))
    X1 = rng.normal(loc=1.0, scale=1.0, size=(120, 2))
    X = np.vstack([X0, X1])
    y = np.array([0] * 120 + [1] * 120)
    out = solve((X, y), params={"task": "classification", "n_neighbors": 5})
    print(out["metrics"])
