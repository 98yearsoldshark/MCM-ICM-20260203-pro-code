# -*- coding: utf-8 -*-
# 示例：客户流失/违约等二分类任务（预处理 + 逻辑回归 + ROC/AUC/KS/阈值）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c01_数据处理_DataProcess.preprocessor import build_preprocessor  # noqa: E402
from MCM_Toolkit_2026.c09_评估与调参_Evaluation.classification_metrics import roc_auc_ks  # noqa: E402
from MCM_Toolkit_2026.c09_评估与调参_Evaluation.thresholding import threshold_metrics_table, find_best_threshold  # noqa: E402
from MCM_Toolkit_2026.utils.file_reader import read_table  # noqa: E402


def solve(data: Union[pd.DataFrame, str, Path], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    端到端二分类示例：自动识别数值/类别列 -> 预处理 -> 逻辑回归 -> 评估。

    Args:
        data: DataFrame 或路径（csv/xlsx/xls）。
        params: 参数：
            - target_col: str（默认 'target'）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - model_params: dict（传给 LogisticRegression）
            - preprocess_params: dict（传给 build_preprocessor，比如 onehot_drop/scale_numeric 等）
            - threshold_metric: {"ks","f1","youden_j"}（默认 ks）

    Returns:
        dict:
            - pipeline: sklearn Pipeline(preprocessor+model)
            - metrics: dict（AUC/KS/accuracy 等）
            - best_threshold: float
            - threshold_table: DataFrame
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
    built = build_preprocessor(X_train, target_col=None, params=preprocess_params)
    pre = built["preprocessor"]

    model_params = dict(params.get("model_params", {}) or {})
    model_params.setdefault("max_iter", 1000)
    model = LogisticRegression(**model_params)

    pipe = Pipeline([("pre", pre), ("model", model)])
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    if hasattr(pipe, "predict_proba"):
        y_score = pipe.predict_proba(X_test)[:, 1]
    else:
        # 兜底：用预测标签当作“分数”（不建议）
        y_score = y_pred.astype(float)

    roc = roc_auc_ks(y_test, y_score)
    thr_table = threshold_metrics_table(y_test, y_score)
    best = find_best_threshold(thr_table, metric=str(params.get("threshold_metric", "ks")))

    metrics = {
        "auc": roc["auc"],
        "ks": roc["ks"],
        "best_threshold": best["best_threshold"],
        "best_metric": best["metric"],
    }
    return {"pipeline": pipe, "metrics": metrics, "best_threshold": best["best_threshold"], "threshold_table": thr_table}


if __name__ == "__main__":
    # Mock Data：包含类别特征与数值特征
    rng = np.random.default_rng(0)
    n = 500
    df_demo = pd.DataFrame(
        {
            "account_funds": rng.normal(loc=5000, scale=2000, size=n).clip(0),
            "txn_cnt": rng.poisson(lam=10, size=n),
            "gender": rng.choice(["男", "女"], size=n),
        }
    )
    # 构造一个与 account_funds/txn_cnt 有关的“流失”标签
    score = 0.0003 * (3000 - df_demo["account_funds"]) + 0.05 * (5 - df_demo["txn_cnt"]) + (df_demo["gender"] == "男") * 0.1
    prob = 1 / (1 + np.exp(-score))
    df_demo["target"] = (rng.random(size=n) < prob).astype(int)

    out = solve(df_demo, params={"target_col": "target"})
    print(out["metrics"])
