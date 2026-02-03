# -*- coding: utf-8 -*-
# LightGBM：可选依赖（lightgbm），提供统一 solve 接口

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.metrics import accuracy_score, mean_squared_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d  # noqa: E402
from MCM_Toolkit_2026.utils.optional_deps import require_package  # noqa: E402


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：LightGBM 训练与评估（分类/回归）。

    说明：该模块依赖 `lightgbm`，未安装时会给出安装提示。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - task: {"classification","regression"}（默认 classification）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - model_params: dict（传给 LGBMClassifier/LGBMRegressor）
            - fit_params: dict（传给 model.fit，比如 eval_set/early_stopping_rounds/verbose 等）

    Returns:
        dict:
            - model
            - metrics
            - y_pred
            - y_pred_proba（分类且支持时）
    """
    params = params or {}
    lgb = require_package("lightgbm", pip_name="lightgbm")

    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y)

    task = str(params.get("task", "classification")).lower()
    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))

    stratify = y if (task == "classification" and len(np.unique(y)) > 1) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model_params = dict(params.get("model_params", {}) or {})
    model_params.setdefault("random_state", random_state)
    model_params.setdefault("n_estimators", 500)

    if task == "classification":
        Model = getattr(lgb, "LGBMClassifier")
        model = Model(**model_params)
    elif task == "regression":
        Model = getattr(lgb, "LGBMRegressor")
        model = Model(**model_params)
    else:
        raise ValueError("task 必须为 classification 或 regression。")

    fit_params = dict(params.get("fit_params", {}) or {})
    try:
        model.fit(X_train, y_train, **fit_params)
    except TypeError:
        model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    metrics: Dict[str, Any]
    y_pred_proba = None
    if task == "classification":
        metrics = {"accuracy": float(accuracy_score(y_test, y_pred))}
        if hasattr(model, "predict_proba"):
            try:
                y_pred_proba = model.predict_proba(X_test)
                if y_pred_proba is not None and y_pred_proba.shape[1] == 2:
                    metrics["roc_auc"] = float(roc_auc_score(y_test, y_pred_proba[:, 1]))
            except Exception:
                y_pred_proba = None
    else:
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        metrics = {"r2": float(r2_score(y_test, y_pred)), "rmse": rmse}

    return {"model": model, "metrics": metrics, "y_pred": y_pred, "y_pred_proba": y_pred_proba}


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 6))
    y = (X[:, 0] + 0.5 * X[:, 1] > 0).astype(int)
    try:
        out = solve((X, y), params={"task": "classification"})
        print(out["metrics"])
    except ImportError as e:
        print(e)

