# -*- coding: utf-8 -*-
# 二分类阈值选择：KS/Youden/F1 等

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, roc_curve

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import to_numpy_1d  # noqa: E402


def threshold_metrics_table(y_true: Any, y_score: Any) -> pd.DataFrame:
    """
    基于 ROC 曲线的阈值集合，计算每个阈值下的常见指标。

    Args:
        y_true: 真实标签（0/1）。
        y_score: 预测分数/概率（越大越像正类）。

    Returns:
        pd.DataFrame: 每行一个阈值及其指标。
    """
    y_true_arr = to_numpy_1d(y_true).astype(int)
    y_score_arr = to_numpy_1d(y_score).astype(float)

    fpr, tpr, thresholds = roc_curve(y_true_arr, y_score_arr)
    rows = []
    for thr, fpr_i, tpr_i in zip(thresholds, fpr, tpr):
        y_pred = (y_score_arr >= thr).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true_arr, y_pred, average="binary", zero_division=0
        )
        rows.append(
            {
                "threshold": float(thr),
                "tpr": float(tpr_i),
                "fpr": float(fpr_i),
                "youden_j": float(tpr_i - fpr_i),
                "ks": float(tpr_i - fpr_i),  # 在该定义下 KS=TPR-FPR
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
            }
        )
    return pd.DataFrame(rows).sort_values("threshold", ascending=False).reset_index(drop=True)


def find_best_threshold(table: pd.DataFrame, metric: str = "ks") -> Dict[str, Any]:
    """
    在阈值表中选择最优阈值。

    Args:
        table: threshold_metrics_table 的输出。
        metric: {"ks","youden_j","f1","precision","recall"}。

    Returns:
        dict: {'best_threshold','best_row','metric'}
    """
    metric = str(metric).lower()
    if metric not in {"ks", "youden_j", "f1", "precision", "recall"}:
        raise ValueError("metric 必须为 ks/youden_j/f1/precision/recall 之一。")
    idx = int(table[metric].to_numpy().argmax()) if not table.empty else -1
    best_row = table.iloc[idx].to_dict() if idx >= 0 else None
    best_threshold = float(best_row["threshold"]) if best_row else None
    return {"metric": metric, "best_threshold": best_threshold, "best_row": best_row}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：阈值表 + 最优阈值。

    Args:
        data: dict，包含：
            - y_true
            - y_score
        params: 参数：
            - metric: 见 find_best_threshold（默认 "ks"）

    Returns:
        dict:
            - table: DataFrame
            - best: dict
    """
    params = params or {}
    if not isinstance(data, dict) or "y_true" not in data or "y_score" not in data:
        raise TypeError("data 必须为 dict，并包含 y_true/y_score。")
    table = threshold_metrics_table(data["y_true"], data["y_score"])
    best = find_best_threshold(table, metric=str(params.get("metric", "ks")))
    return {"table": table, "best": best}


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=200)
    y_score = y_true * 0.7 + rng.random(size=200) * 0.3
    out = solve({"y_true": y_true, "y_score": y_score}, params={"metric": "f1"})
    print(out["best"])

