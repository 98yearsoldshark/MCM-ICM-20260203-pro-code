# -*- coding: utf-8 -*-
"""数据格式与拆分的通用工具。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


ArrayLike = Union[np.ndarray, Sequence[Sequence[float]]]


@dataclass(frozen=True)
class XYData:
    """统一表示监督学习中的 X/y。"""

    X: Union[pd.DataFrame, np.ndarray]
    y: Union[pd.Series, np.ndarray]
    feature_names: Optional[Sequence[str]] = None


def split_xy(
    data: Any,
    *,
    target_col: Optional[str] = None,
) -> XYData:
    """
    从多种输入格式中抽取 X/y。

    支持的 data 形式：
    - pandas.DataFrame：需要提供 target_col
    - (X, y) 二元组
    - dict：包含键 {'X','y'}（大小写不敏感）

    Args:
        data: 输入数据。
        target_col: 当 data 为 DataFrame 时，用于指定目标列名。

    Returns:
        XYData: 标准化后的 X/y 与可选特征名。
    """
    if isinstance(data, pd.DataFrame):
        if not target_col:
            raise ValueError("data 为 DataFrame 时必须提供 target_col。")
        if target_col not in data.columns:
            raise ValueError(f"target_col 不存在于 DataFrame 中：{target_col}")
        X = data.drop(columns=[target_col])
        y = data[target_col]
        return XYData(X=X, y=y, feature_names=list(X.columns))

    if isinstance(data, (tuple, list)) and len(data) == 2:
        X, y = data
        feature_names = list(X.columns) if isinstance(X, pd.DataFrame) else None
        return XYData(X=X, y=y, feature_names=feature_names)

    if isinstance(data, dict):
        # 兼容大小写
        keys = {str(k).lower(): k for k in data.keys()}
        if "x" not in keys or "y" not in keys:
            raise ValueError("data 为 dict 时必须包含键 'X' 和 'y'。")
        X = data[keys["x"]]
        y = data[keys["y"]]
        feature_names = list(X.columns) if isinstance(X, pd.DataFrame) else None
        return XYData(X=X, y=y, feature_names=feature_names)

    raise TypeError("不支持的 data 类型：请使用 DataFrame、(X,y) 或 {'X','y'}。")


def to_numpy_2d(X: Any) -> Any:
    """
    将输入 X 转为二维 numpy.ndarray。

    Args:
        X: DataFrame/ndarray/二维 list 等。

    Returns:
        Any: 形状为 (n_samples, n_features) 的二维数据；可能为 numpy.ndarray 或 scipy.sparse 矩阵。
    """
    # scipy.sparse 矩阵在 sklearn 中很常见（One-Hot 默认输出 sparse），这里保持原样返回。
    try:
        import scipy.sparse as sp  # type: ignore

        if sp.issparse(X):
            arr = X  # type: ignore[assignment]
        else:
            arr = X.to_numpy() if isinstance(X, pd.DataFrame) else np.asarray(X)
    except Exception:
        arr = X.to_numpy() if isinstance(X, pd.DataFrame) else np.asarray(X)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"X 必须为二维数据，当前维度为 {arr.ndim}")
    return arr


def to_numpy_1d(y: Any) -> np.ndarray:
    """将输入 y 转为一维 numpy.ndarray。"""
    if isinstance(y, pd.Series):
        arr = y.to_numpy()
    else:
        arr = np.asarray(y)
    return arr.reshape(-1)


def get_param(params: Optional[Dict[str, Any]], key: str, default: Any) -> Any:
    """从 params 中读取参数（params 为 None 时返回默认值）。"""
    if params is None:
        return default
    return params.get(key, default)
