# -*- coding: utf-8 -*-
# KMeans 聚类（基于 scikit-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, to_numpy_2d


def solve(data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：KMeans 聚类。

    Args:
        data: 特征数据，支持 DataFrame/ndarray，或 dict {'X': ...}。
        params: 参数：
            - n_clusters: int（默认 3）
            - random_state: int（默认 42）
            - standardize: bool（默认 False；True 表示先做 Z-score）
            - model_params: dict（传给 sklearn.cluster.KMeans）

    Returns:
        dict:
            - model: KMeans 模型
            - labels: 聚类标签（ndarray）
            - centers: 聚类中心（ndarray）
            - inertia: SSE（float）
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X", data.get("x"))
    else:
        X = data

    X_arr = to_numpy_2d(X)
    standardize = bool(get_param(params, "standardize", False))
    if standardize:
        X_arr = StandardScaler().fit_transform(X_arr)

    n_clusters = int(get_param(params, "n_clusters", 3))
    random_state = int(get_param(params, "random_state", 42))
    model_params = dict(get_param(params, "model_params", {}) or {})

    model = KMeans(n_clusters=n_clusters, random_state=random_state, **model_params)
    labels = model.fit_predict(X_arr)
    return {
        "model": model,
        "labels": labels,
        "centers": model.cluster_centers_,
        "inertia": float(model.inertia_),
    }


if __name__ == "__main__":
    # Mock Data
    rng = np.random.default_rng(0)
    X = np.vstack(
        [
            rng.normal(loc=(-2, -2), scale=0.5, size=(100, 2)),
            rng.normal(loc=(2, 2), scale=0.5, size=(100, 2)),
            rng.normal(loc=(2, -2), scale=0.5, size=(100, 2)),
        ]
    )
    out = solve(X, params={"n_clusters": 3, "random_state": 0})
    print("inertia:", out["inertia"])
    print("centers:\n", out["centers"])
