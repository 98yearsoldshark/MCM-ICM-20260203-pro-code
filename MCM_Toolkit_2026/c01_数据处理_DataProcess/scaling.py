# -*- coding: utf-8 -*-
# 数据标准化/归一化（Min-Max / Z-score）

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.preprocessing import MinMaxScaler, StandardScaler


def scale_features(
    X: Union[pd.DataFrame, np.ndarray],
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    对特征做标准化/归一化。

    Args:
        X: 特征矩阵（DataFrame 或 ndarray）。
        params: 参数：
            - method: {"standard","minmax"}，默认 "standard"
            - feature_range: tuple(float,float)，minmax 用，默认 (0, 1)

    Returns:
        dict:
            - X_scaled: 与输入同形状的数据（DataFrame 会保留列名）
            - scaler: 拟合后的 scaler 对象
    """
    params = params or {}
    method = params.get("method", "standard")

    is_df = isinstance(X, pd.DataFrame)
    X_values = X.to_numpy() if is_df else np.asarray(X)

    if method == "standard":
        scaler = StandardScaler()
    elif method == "minmax":
        feature_range = params.get("feature_range", (0, 1))
        scaler = MinMaxScaler(feature_range=feature_range)
    else:
        raise ValueError(f"不支持的 method: {method}")

    X_scaled = scaler.fit_transform(X_values)
    if is_df:
        X_scaled = pd.DataFrame(X_scaled, columns=list(X.columns), index=X.index)
    return {"X_scaled": X_scaled, "scaler": scaler}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：对输入特征做缩放。

    Args:
        data: 支持 DataFrame/ndarray，或 dict {'X': ...}。
        params: 见 scale_features。

    Returns:
        dict: 同 scale_features 返回结构。
    """
    if isinstance(data, dict):
        X = data.get("X", data.get("x"))
    else:
        X = data
    return scale_features(X, params=params)


if __name__ == "__main__":
    # Mock Data
    X_demo = pd.DataFrame(
        {
            "a": [50, 60, 40, 80, 90],
            "b": [2, 1, 1, 3, 2],
        }
    )
    out = solve(X_demo, params={"method": "minmax"})
    print(out["X_scaled"])

