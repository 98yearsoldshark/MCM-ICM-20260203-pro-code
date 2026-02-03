# -*- coding: utf-8 -*-
# AdaBoost：分类 / 回归

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.ensemble import AdaBoostClassifier, AdaBoostRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：AdaBoost 训练与评估。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - task: {"classification","regression"}（默认 classification）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True；分类建议 True）
            - model_params: dict（传给 AdaBoostClassifier/Regressor）

    Returns:
        dict: {'model','metrics','y_pred'}
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X_arr = to_numpy_2d(xy.X)
    y_arr = to_numpy_1d(xy.y)

    task = str(get_param(params, "task", "classification")).lower()
    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))
    stratify = bool(get_param(params, "stratify", True))
    model_params = dict(get_param(params, "model_params", {}) or {})

    stratify_y = y_arr if (task == "classification" and stratify and np.unique(y_arr).size > 1) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    if task == "classification":
        model = AdaBoostClassifier(random_state=random_state, **model_params)
    elif task == "regression":
        model = AdaBoostRegressor(random_state=random_state, **model_params)
    else:
        raise ValueError(f"不支持的 task: {task}")

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if task == "classification":
        metrics: Dict[str, Any] = {
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
    # Mock Data：回归
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 4))
    y = 3.0 * X[:, 0] - 2.0 * X[:, 1] + rng.normal(scale=0.5, size=400)
    out = solve((X, y), params={"task": "regression", "model_params": {"n_estimators": 200}})
    print(out["metrics"])
