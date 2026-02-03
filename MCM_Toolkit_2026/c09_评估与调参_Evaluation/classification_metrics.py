# -*- coding: utf-8 -*-
# 分类评估：ROC/AUC/KS（常用于二分类）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from sklearn.metrics import roc_auc_score, roc_curve

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import to_numpy_1d


def roc_auc_ks(y_true: Any, y_score: Any) -> Dict[str, Any]:
    """
    计算 ROC 曲线、AUC 与 KS。

    约定：
    - y_true: 0/1
    - y_score: 预测为 1 的概率/打分（越大越像正类）

    Args:
        y_true: 真实标签（0/1）。
        y_score: 预测分数/概率。

    Returns:
        dict:
            - auc: float
            - ks: float
            - fpr: ndarray
            - tpr: ndarray
            - thresholds: ndarray
            - best_threshold: float（使 tpr-fpr 最大的阈值）
    """
    y_true_arr = to_numpy_1d(y_true)
    y_score_arr = to_numpy_1d(y_score)

    fpr, tpr, thresholds = roc_curve(y_true_arr, y_score_arr)
    auc = float(roc_auc_score(y_true_arr, y_score_arr))

    ks_values = tpr - fpr
    ks = float(np.max(ks_values))
    best_idx = int(np.argmax(ks_values))
    best_threshold = float(thresholds[best_idx])
    return {
        "auc": auc,
        "ks": ks,
        "fpr": fpr,
        "tpr": tpr,
        "thresholds": thresholds,
        "best_threshold": best_threshold,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：ROC/AUC/KS 计算。

    Args:
        data: dict，至少包含：
            - y_true
            - y_score（预测为 1 的概率/分数）
        params: 预留（当前未使用）。

    Returns:
        dict: roc_auc_ks 返回结果（其中 fpr/tpr/thresholds 为 ndarray）。
    """
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict，包含 y_true/y_score。")
    if "y_true" not in data or "y_score" not in data:
        raise ValueError("data 必须包含键 y_true 和 y_score。")
    return roc_auc_ks(data["y_true"], data["y_score"])


if __name__ == "__main__":
    # Mock Data：随机分数
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=200)
    y_score = y_true * 0.7 + rng.random(size=200) * 0.3
    out = solve({"y_true": y_true, "y_score": y_score})
    print({k: out[k] for k in ["auc", "ks", "best_threshold"]})
