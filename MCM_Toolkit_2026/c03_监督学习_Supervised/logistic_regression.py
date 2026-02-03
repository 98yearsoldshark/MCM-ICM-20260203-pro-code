# -*- coding: utf-8 -*-
# 逻辑回归（二分类/多分类，基于 scikit-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：逻辑回归模型训练与评估。

    Args:
        data: 支持 DataFrame（含目标列）、(X,y)、{'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True；二分类时建议 True）
            - model_params: dict（传给 LogisticRegression 的参数）
            - decision_threshold: float | None（默认 None，使用 model.predict；若给定则按概率阈值输出 0/1）

    Returns:
        dict:
            - model: 训练好的模型
            - metrics: dict（accuracy/confusion_matrix/classification_report/roc_auc 等）
            - y_pred: 测试集预测标签
            - y_pred_proba: 测试集预测概率（若模型支持）
            - fpr/tpr/thresholds: ROC 曲线数据（仅二分类且可得概率时）
    """
    params = params or {}
    xy = split_xy(data, target_col=params.get("target_col"))
    X_arr = to_numpy_2d(xy.X)
    y_arr = to_numpy_1d(xy.y)

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))
    stratify = bool(get_param(params, "stratify", True))

    y_unique = np.unique(y_arr)
    stratify_y = y_arr if (stratify and y_unique.size > 1) else None

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    model_params = dict(params.get("model_params", {}) or {})
    model = LogisticRegression(**model_params)
    model.fit(X_train, y_train)

    y_pred_proba = None
    if hasattr(model, "predict_proba"):
        try:
            y_pred_proba = model.predict_proba(X_test)
        except Exception:
            y_pred_proba = None

    decision_threshold = params.get("decision_threshold")
    if decision_threshold is not None and y_pred_proba is not None and y_pred_proba.shape[1] == 2:
        thr = float(decision_threshold)
        y_pred = (y_pred_proba[:, 1] >= thr).astype(int)
    else:
        y_pred = model.predict(X_test)

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }

    fpr = tpr = thresholds = None
    if y_pred_proba is not None and y_pred_proba.shape[1] == 2:
        # 二分类：计算 ROC/AUC
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_pred_proba[:, 1]))
            fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba[:, 1])
        except Exception:
            pass

    return {
        "model": model,
        "metrics": metrics,
        "y_pred": y_pred,
        "y_pred_proba": y_pred_proba,
        "fpr": fpr,
        "tpr": tpr,
        "thresholds": thresholds,
    }


if __name__ == "__main__":
    # Mock Data：生成一个可分的二分类数据
    rng = np.random.default_rng(0)
    n = 300
    X0 = rng.normal(loc=-1.0, scale=1.0, size=(n // 2, 2))
    X1 = rng.normal(loc=1.0, scale=1.0, size=(n // 2, 2))
    X = np.vstack([X0, X1])
    y = np.array([0] * (n // 2) + [1] * (n // 2))

    out = solve((X, y), params={"model_params": {"max_iter": 200}})
    print(out["metrics"])
