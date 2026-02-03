# -*- coding: utf-8 -*-
# 示例：员工离职预测（二分类）——预处理 + 决策树 +（可选）网格搜索

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c01_数据处理_DataProcess.preprocessor import build_preprocessor  # noqa: E402
from MCM_Toolkit_2026.utils.file_reader import read_table  # noqa: E402


def solve(data: Union[pd.DataFrame, str, Path], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    端到端二分类示例：预处理（缺失/One-Hot/标准化）+ 决策树 + 评估。

    Args:
        data: DataFrame 或路径（csv/xlsx/xls）。
        params: 参数：
            - target_col: str（默认 'target'）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - tree_params: dict（传给 DecisionTreeClassifier）
            - preprocess_params: dict（传给 build_preprocessor）
            - grid_search: bool（默认 False）
            - param_grid: dict（grid_search=True 时使用）
            - scoring: str（默认 'roc_auc'）
            - cv: int（默认 5）

    Returns:
        dict:
            - model: Pipeline 或 GridSearchCV.best_estimator_
            - metrics: dict（accuracy/roc_auc）
            - best_params: dict | None
    """
    params = params or {}

    if isinstance(data, (str, Path)):
        df = read_table(data)
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或表格文件路径。")

    target_col = str(params.get("target_col", "target"))
    if target_col not in df.columns:
        raise ValueError(f"缺少目标列：{target_col}")

    X_df = df.drop(columns=[target_col])
    y = df[target_col].to_numpy()

    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))

    X_train, X_test, y_train, y_test = train_test_split(
        X_df, y, test_size=test_size, random_state=random_state, stratify=y if len(np.unique(y)) > 1 else None
    )

    preprocess_params = dict(params.get("preprocess_params", {}) or {})
    pre = build_preprocessor(X_train, params=preprocess_params)["preprocessor"]

    tree_params = dict(params.get("tree_params", {}) or {})
    tree_params.setdefault("random_state", random_state)
    base_model = DecisionTreeClassifier(**tree_params)

    pipe = Pipeline([("pre", pre), ("model", base_model)])

    best_params = None
    if bool(params.get("grid_search", False)):
        param_grid = dict(params.get("param_grid", {}) or {})
        if not param_grid:
            param_grid = {
                "model__max_depth": [3, 5, 7, 9],
                "model__min_samples_split": [2, 5, 10],
                "model__criterion": ["gini", "entropy"],
            }
        scoring = str(params.get("scoring", "roc_auc"))
        cv = int(params.get("cv", 5))
        gs = GridSearchCV(pipe, param_grid=param_grid, scoring=scoring, cv=cv, refit=True)
        gs.fit(X_train, y_train)
        model = gs.best_estimator_
        best_params = gs.best_params_
    else:
        pipe.fit(X_train, y_train)
        model = pipe

    y_pred = model.predict(X_test)
    metrics = {"accuracy": float(accuracy_score(y_test, y_pred))}
    # 二分类时给出 AUC（若 predict_proba 可用）
    if hasattr(model, "predict_proba"):
        try:
            y_score = model.predict_proba(X_test)[:, 1]
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_score))
        except Exception:
            pass

    return {"model": model, "metrics": metrics, "best_params": best_params}


if __name__ == "__main__":
    # Mock Data：包含数值+类别（工资）特征
    rng = np.random.default_rng(0)
    n = 600
    df_demo = pd.DataFrame(
        {
            "satisfaction": rng.uniform(0, 1, size=n),
            "work_hours": rng.normal(loc=45, scale=8, size=n).clip(20, 80),
            "salary_level": rng.choice(["低", "中", "高"], p=[0.5, 0.35, 0.15], size=n),
            "tenure_years": rng.integers(0, 11, size=n),
        }
    )
    # 构造离职概率：满意度低、加班多、工资低更容易离职
    score = (
        (0.5 - df_demo["satisfaction"]) * 2.0
        + (df_demo["work_hours"] - 45) * 0.03
        + (df_demo["salary_level"] == "低") * 0.4
        + (df_demo["salary_level"] == "高") * (-0.2)
    )
    prob = 1 / (1 + np.exp(-score))
    df_demo["target"] = (rng.random(size=n) < prob).astype(int)

    out = solve(df_demo, params={"target_col": "target", "grid_search": True})
    print(out["metrics"])
    print("best_params:", out["best_params"])

