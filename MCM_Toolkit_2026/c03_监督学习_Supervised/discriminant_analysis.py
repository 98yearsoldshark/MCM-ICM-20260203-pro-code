# -*- coding: utf-8 -*-
# 判别分析：LDA（Fisher 线性判别）/ QDA（二次判别），基于 scikit-learn
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../分类与判别类题型参考代码.../基于Fisher算法的分类程序

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：LDA/QDA 训练与评估。

    Args:
        data: 支持 DataFrame（含目标列）、(X,y)、{'X','y'}。
        params: 参数：
            - model_type: {'lda','qda'}（默认 'lda'）
            - target_col: str | None（DataFrame 时必填）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - stratify: bool（默认 True）
            - model_params: dict（传给 LDA/QDA 的参数）

    Returns:
        dict:
            - model
            - metrics
            - y_pred
            - y_pred_proba（若可得）
            - embedding（LDA 可选：transform 后的低维表示）
    """
    params = params or {}
    model_type = str(get_param(params, "model_type", "lda")).lower()
    if model_type not in {"lda", "qda"}:
        raise ValueError("model_type 必须为 'lda' 或 'qda'。")

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

    model_params = dict(params.get("model_params", {}) or {})
    if model_type == "lda":
        model = LinearDiscriminantAnalysis(**model_params)
    else:
        model = QuadraticDiscriminantAnalysis(**model_params)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    y_pred_proba = None
    if hasattr(model, "predict_proba"):
        try:
            y_pred_proba = model.predict_proba(X_test)
        except Exception:
            y_pred_proba = None

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }

    embedding = None
    if model_type == "lda" and hasattr(model, "transform"):
        try:
            embedding = model.transform(X_arr)
        except Exception:
            embedding = None

    return {"model": model, "metrics": metrics, "y_pred": y_pred, "y_pred_proba": y_pred_proba, "embedding": embedding}


if __name__ == "__main__":
    # Mock Data：三分类高斯簇
    rng = np.random.default_rng(0)
    X1 = rng.normal(0, 1, size=(120, 4))
    X2 = rng.normal(3, 1, size=(120, 4))
    X3 = rng.normal(-2, 1, size=(120, 4))
    X = np.vstack([X1, X2, X3])
    y = np.array([0] * 120 + [1] * 120 + [2] * 120)

    out = solve((X, y), {"model_type": "lda"})
    print("LDA metrics:", out["metrics"])

    out2 = solve((X, y), {"model_type": "qda"})
    print("QDA metrics:", out2["metrics"])

