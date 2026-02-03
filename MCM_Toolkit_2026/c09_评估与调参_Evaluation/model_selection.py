# -*- coding: utf-8 -*-
# 模型选择：交叉验证 / GridSearchCV（网格搜索）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：交叉验证或网格搜索。

    注意：该模块更偏“工具”，因此需要你在 params 中传入 sklearn 的 estimator 对象。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - mode: {"cross_val","grid_search"}（默认 cross_val）
            - estimator: sklearn estimator（必填）
            - scoring: str | None（默认 None）
            - cv: int（默认 5）
            - param_grid: dict（grid_search 模式必填）
            - test_size: float（grid_search 可选，用于拆分留出集评估；默认 0.2）
            - random_state: int（默认 42）

    Returns:
        dict:
            - mode="cross_val": {'scores','mean','std'}
            - mode="grid_search": {'best_params','best_score','best_estimator','test_score'(可选)}
    """
    params = params or {}
    mode = str(get_param(params, "mode", "cross_val")).lower()
    estimator = params.get("estimator")
    if estimator is None:
        raise ValueError("params.estimator 必填（sklearn 的模型对象）。")

    xy = split_xy(data, target_col=params.get("target_col"))
    X = to_numpy_2d(xy.X)
    y = to_numpy_1d(xy.y)

    scoring = params.get("scoring")
    cv = int(get_param(params, "cv", 5))

    if mode == "cross_val":
        scores = cross_val_score(estimator, X, y, scoring=scoring, cv=cv)
        return {"scores": scores, "mean": float(np.mean(scores)), "std": float(np.std(scores))}

    if mode == "grid_search":
        param_grid = params.get("param_grid")
        if not isinstance(param_grid, dict):
            raise ValueError("grid_search 模式下 params.param_grid 必须为 dict。")

        test_size = float(get_param(params, "test_size", 0.2))
        random_state = int(get_param(params, "random_state", 42))
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y if np.unique(y).size > 1 else None
        )

        gs = GridSearchCV(estimator, param_grid, scoring=scoring, cv=cv, refit=True)
        gs.fit(X_train, y_train)

        out: Dict[str, Any] = {
            "best_params": gs.best_params_,
            "best_score": float(gs.best_score_),
            "best_estimator": gs.best_estimator_,
        }
        try:
            out["test_score"] = float(gs.best_estimator_.score(X_test, y_test))
        except Exception:
            pass
        return out

    raise ValueError(f"不支持的 mode: {mode}")


if __name__ == "__main__":
    # Mock Data：用决策树做网格搜索
    from sklearn.tree import DecisionTreeClassifier

    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 4))
    y = (X[:, 0] + 0.8 * X[:, 1] > 0).astype(int)

    out = solve(
        (X, y),
        params={
            "mode": "grid_search",
            "estimator": DecisionTreeClassifier(random_state=0),
            "param_grid": {"max_depth": [2, 3, 4, 5]},
            "scoring": "roc_auc",
            "cv": 5,
        },
    )
    print(out["best_params"], out.get("test_score"))
