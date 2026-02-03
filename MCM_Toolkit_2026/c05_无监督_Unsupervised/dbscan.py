# -*- coding: utf-8 -*-
# DBSCAN 聚类（基于 scikit-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, to_numpy_2d


def solve(data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：DBSCAN 聚类。

    Args:
        data: 特征数据，支持 DataFrame/ndarray，或 dict {'X': ...}。
        params: 参数：
            - eps: float（默认 0.5）
            - min_samples: int（默认 5）
            - standardize: bool（默认 False；True 表示先做 Z-score）
            - model_params: dict（传给 sklearn.cluster.DBSCAN）

    Returns:
        dict:
            - model: DBSCAN 模型
            - labels: 聚类标签（-1 表示噪声点）
            - n_clusters: 聚类数（不含噪声）
            - n_noise: 噪声点数
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X", data.get("x"))
    else:
        X = data

    X_arr = to_numpy_2d(X)
    if bool(get_param(params, "standardize", False)):
        X_arr = StandardScaler().fit_transform(X_arr)

    eps = float(get_param(params, "eps", 0.5))
    min_samples = int(get_param(params, "min_samples", 5))
    model_params = dict(get_param(params, "model_params", {}) or {})

    model = DBSCAN(eps=eps, min_samples=min_samples, **model_params)
    labels = model.fit_predict(X_arr)
    n_noise = int(np.sum(labels == -1))
    n_clusters = int(len(set(labels)) - (1 if -1 in labels else 0))
    return {"model": model, "labels": labels, "n_clusters": n_clusters, "n_noise": n_noise}


if __name__ == "__main__":
    # Mock Data：三团簇 + 少量噪声
    rng = np.random.default_rng(0)
    X = np.vstack(
        [
            rng.normal(loc=(-2, -2), scale=0.4, size=(120, 2)),
            rng.normal(loc=(2, 2), scale=0.4, size=(120, 2)),
            rng.normal(loc=(2, -2), scale=0.4, size=(120, 2)),
            rng.uniform(low=-5, high=5, size=(10, 2)),
        ]
    )
    out = solve(X, params={"eps": 0.6, "min_samples": 5})
    print(out["n_clusters"], out["n_noise"])
