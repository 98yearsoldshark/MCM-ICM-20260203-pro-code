# -*- coding: utf-8 -*-
# PCA 主成分分析（基于 scikit-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, to_numpy_2d


def solve(data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：PCA 降维。

    Args:
        data: 特征数据，支持 DataFrame/ndarray，或 dict {'X': ...}。
        params: 参数：
            - n_components: int | float | None（默认 2）
            - standardize: bool（默认 True；PCA 通常建议先标准化）
            - random_state: int | None（默认 42）
            - model_params: dict（传给 sklearn.decomposition.PCA）

    Returns:
        dict:
            - model: PCA 模型
            - X_transformed: 降维后的数据（ndarray）
            - components: 主成分方向（ndarray）
            - explained_variance_ratio: 解释方差比（ndarray）
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X", data.get("x"))
    else:
        X = data

    X_arr = to_numpy_2d(X)
    if bool(get_param(params, "standardize", True)):
        X_arr = StandardScaler().fit_transform(X_arr)

    n_components = params.get("n_components", 2)
    random_state = params.get("random_state", 42)
    model_params = dict(get_param(params, "model_params", {}) or {})

    model = PCA(n_components=n_components, random_state=random_state, **model_params)
    X_transformed = model.fit_transform(X_arr)
    return {
        "model": model,
        "X_transformed": X_transformed,
        "components": model.components_,
        "explained_variance_ratio": model.explained_variance_ratio_,
    }


if __name__ == "__main__":
    # Mock Data：3 维降到 2 维
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    out = solve(X, params={"n_components": 2})
    print(out["explained_variance_ratio"])
