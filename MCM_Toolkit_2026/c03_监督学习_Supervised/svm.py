# -*- coding: utf-8 -*-
# 支持向量机（SVM）：分类（SVC）/ 回归（SVR），基于 scikit-learn
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../分类与判别类题型参考代码.../基于SVM神经网络... 等

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC, LinearSVR, SVC, SVR

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：SVM 训练与评估（分类/回归）。

    Args:
        data: 支持 DataFrame（含目标列）、(X,y)、{'X','y'}。
        params: 参数：
            - task: {'classification','regression'}（默认 'classification'）
            - target_col: str | None（DataFrame 时必填）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True；分类时建议 True）
            - model_type: {'svc','linear_svc','svr','linear_svr'}（可选；不填则按 task 自动）
            - model_params: dict（传给对应模型）
            - probability: bool（仅 SVC；默认 False。若 True 可输出 predict_proba）
            - decision_threshold: float | None（仅二分类且有概率时可用）

    Returns:
        dict:
            - model: 训练好的模型
            - metrics: dict（分类：accuracy/confusion_matrix/report/roc_auc；回归：rmse/mae/r2）
            - y_pred: 测试集预测
            - y_pred_proba: 分类概率（若可得）
            - fpr/tpr/thresholds: ROC 曲线（若可得且二分类）
    """
    params = params or {}
    task = str(get_param(params, "task", "classification")).lower()
    if task not in {"classification", "regression"}:
        raise ValueError("params.task 必须为 classification 或 regression。")

    xy = split_xy(data, target_col=params.get("target_col"))
    X_arr = to_numpy_2d(xy.X)
    y_arr = to_numpy_1d(xy.y)

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))
    stratify = bool(get_param(params, "stratify", True))

    stratify_y = y_arr if (task == "classification" and stratify and np.unique(y_arr).size > 1) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    model_type = params.get("model_type")
    if model_type is None:
        model_type = "svc" if task == "classification" else "svr"
    model_type = str(model_type).lower()

    model_params = dict(params.get("model_params", {}) or {})

    if task == "classification":
        probability = bool(get_param(params, "probability", False))
        if model_type == "svc":
            model = SVC(probability=probability, **model_params)
        elif model_type == "linear_svc":
            model = LinearSVC(**model_params)
        else:
            raise ValueError("分类任务 model_type 必须为 svc 或 linear_svc。")
    else:
        if model_type == "svr":
            model = SVR(**model_params)
        elif model_type == "linear_svr":
            model = LinearSVR(**model_params)
        else:
            raise ValueError("回归任务 model_type 必须为 svr 或 linear_svr。")

    model.fit(X_train, y_train)

    y_pred_proba = None
    if task == "classification" and hasattr(model, "predict_proba"):
        try:
            y_pred_proba = model.predict_proba(X_test)
        except Exception:
            y_pred_proba = None

    decision_threshold = params.get("decision_threshold")
    if task == "classification" and decision_threshold is not None and y_pred_proba is not None and y_pred_proba.shape[1] == 2:
        thr = float(decision_threshold)
        y_pred = (y_pred_proba[:, 1] >= thr).astype(int)
    else:
        y_pred = model.predict(X_test)

    metrics: Dict[str, Any] = {}
    fpr = tpr = thresholds = None

    if task == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
        metrics["classification_report"] = classification_report(y_test, y_pred, zero_division=0)

        if y_pred_proba is not None and y_pred_proba.shape[1] == 2:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y_test, y_pred_proba[:, 1]))
                fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba[:, 1])
            except Exception:
                pass
    else:
        y_true = y_test.astype(float)
        y_hat = y_pred.astype(float)
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_hat)))
        metrics["mae"] = float(mean_absolute_error(y_true, y_hat))
        metrics["r2"] = float(r2_score(y_true, y_hat))

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
    rng = np.random.default_rng(0)

    # Demo 1：二分类
    n = 300
    X0 = rng.normal(loc=-1.0, scale=1.0, size=(n // 2, 2))
    X1 = rng.normal(loc=1.0, scale=1.0, size=(n // 2, 2))
    X = np.vstack([X0, X1])
    y = np.array([0] * (n // 2) + [1] * (n // 2))
    out = solve((X, y), {"task": "classification", "model_type": "svc", "probability": True, "model_params": {"kernel": "rbf"}})
    print("SVM classification metrics:", out["metrics"])

    # Demo 2：回归（y = sin(x) + noise）
    Xr = rng.uniform(-3, 3, size=(300, 1))
    yr = np.sin(Xr[:, 0]) + rng.normal(0, 0.1, size=300)
    out2 = solve((Xr, yr), {"task": "regression", "model_type": "svr", "model_params": {"kernel": "rbf", "C": 10.0}})
    print("SVM regression metrics:", out2["metrics"])

