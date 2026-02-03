# -*- coding: utf-8 -*-
# 多重共线性：相关系数矩阵 + VIF（方差膨胀因子）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_2d


def compute_vif(X: pd.DataFrame) -> pd.DataFrame:
    """
    计算 VIF（方差膨胀因子）。

    Args:
        X: 特征表（建议已去除常数列/已标准化更稳定）。

    Returns:
        pd.DataFrame: 两列：feature, vif（越大通常共线性越严重）。
    """
    if not isinstance(X, pd.DataFrame):
        raise TypeError("compute_vif 仅接受 pandas.DataFrame。")

    # statsmodels 的 vif 输入需要 numpy array
    X_values = X.to_numpy()
    rows = []
    for i, col in enumerate(X.columns):
        try:
            v = float(variance_inflation_factor(X_values, i))
        except Exception:
            v = float("nan")
        rows.append({"feature": col, "vif": v})
    return pd.DataFrame(rows).sort_values("vif", ascending=False).reset_index(drop=True)


def solve(data: Union[pd.DataFrame, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：计算相关系数矩阵与 VIF。

    Args:
        data: 支持：
            - DataFrame（特征表）
            - dict {'X': DataFrame} 或 (X,y)（若传入监督学习数据，可用 params.target_col 自动剔除目标列）
        params: 参数：
            - target_col: str | None（当 data 为包含目标列的 DataFrame 时使用）

    Returns:
        dict:
            - corr: 相关系数矩阵（DataFrame）
            - vif: VIF 表（DataFrame）
    """
    params = params or {}
    target_col = params.get("target_col")

    if isinstance(data, pd.DataFrame):
        df = data
        X = df.drop(columns=[target_col]) if target_col and target_col in df.columns else df
    else:
        # 兼容 (X,y) 或 {'X','y'}
        xy = split_xy(data, target_col=target_col) if not isinstance(data, dict) else None
        if isinstance(data, dict) and ("X" in data or "x" in data):
            X = data.get("X", data.get("x"))
        else:
            X = xy.X  # type: ignore[union-attr]

    if isinstance(X, np.ndarray):
        X = pd.DataFrame(to_numpy_2d(X))
    if not isinstance(X, pd.DataFrame):
        raise TypeError("X 必须为 DataFrame 或 ndarray。")

    # 仅数值列参与计算
    X_num = X.select_dtypes(include="number")
    corr = X_num.corr()
    vif = compute_vif(X_num)
    return {"corr": corr, "vif": vif}


if __name__ == "__main__":
    # Mock Data：构造强相关特征
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=200)
    x2 = 2.0 * x1 + rng.normal(scale=0.01, size=200)  # 与 x1 高度相关
    x3 = rng.normal(size=200)
    demo = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
    out = solve(demo)
    print(out["corr"])
    print(out["vif"])
