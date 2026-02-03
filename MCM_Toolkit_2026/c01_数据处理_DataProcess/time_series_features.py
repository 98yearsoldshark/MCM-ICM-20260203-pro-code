# -*- coding: utf-8 -*-
# 时间序列特征工程（适配本地 CSV/Excel）：收益率、滞后项、滚动统计等

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def add_return_features(
    df: pd.DataFrame,
    *,
    price_col: str = "close",
    return_col: str = "ret",
) -> pd.DataFrame:
    """新增收益率列（pct_change）。"""
    out = df.copy()
    out[return_col] = out[price_col].pct_change()
    return out


def add_lag_features(df: pd.DataFrame, *, col: str, lags: Sequence[int]) -> pd.DataFrame:
    """新增滞后特征列。"""
    out = df.copy()
    for k in lags:
        out[f"{col}_lag{k}"] = out[col].shift(int(k))
    return out


def add_rolling_features(
    df: pd.DataFrame,
    *,
    col: str,
    windows: Sequence[int],
) -> pd.DataFrame:
    """新增滚动均值/标准差（波动率）等统计特征。"""
    out = df.copy()
    for w in windows:
        w = int(w)
        out[f"{col}_roll_mean{w}"] = out[col].rolling(w).mean()
        out[f"{col}_roll_std{w}"] = out[col].rolling(w).std(ddof=0)
    return out


def make_supervised(
    df: pd.DataFrame,
    *,
    price_col: str = "close",
    horizon: int = 1,
    target_type: str = "direction",
    lags: Sequence[int] = (1, 2, 3, 5, 10),
    windows: Sequence[int] = (5, 10, 20),
    dropna: bool = True,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    将价格序列构造成监督学习数据集（X,y）。

    Args:
        df: 输入数据表，至少包含 price_col。
        price_col: 价格列名。
        horizon: 预测步长（用 t+horizon 的收益/方向作为标签）。
        target_type: {"direction","return"}：
            - direction：预测未来涨跌（0/1）
            - return：预测未来收益率（连续值）
        lags: 滞后项（基于收益率 ret）。
        windows: 滚动窗口（基于收益率 ret）。
        dropna: 是否丢弃含 NaN 的行。

    Returns:
        (X, y)
    """
    if price_col not in df.columns:
        raise ValueError(f"缺少列：{price_col}")

    tmp = add_return_features(df, price_col=price_col, return_col="ret")
    tmp = add_lag_features(tmp, col="ret", lags=lags)
    tmp = add_rolling_features(tmp, col="ret", windows=windows)

    future_ret = tmp["ret"].shift(-int(horizon))
    if target_type == "direction":
        y = (future_ret > 0).astype(int)
    elif target_type == "return":
        y = future_ret
    else:
        raise ValueError("target_type 必须为 direction 或 return。")

    feature_cols = [c for c in tmp.columns if c not in {price_col} and c != "ret"]
    X = tmp[feature_cols].copy()
    y = y.rename("y")

    if dropna:
        keep = X.notna().all(axis=1) & y.notna()
        X = X.loc[keep].reset_index(drop=True)
        y = y.loc[keep].reset_index(drop=True)

    return X, y


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：时间序列 -> 监督学习特征与标签。

    Args:
        data: DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - price_col: str（默认 'close'）
            - horizon: int（默认 1）
            - target_type: {'direction','return'}（默认 'direction'）
            - lags: list[int]
            - windows: list[int]
            - dropna: bool（默认 True）

    Returns:
        dict: {'X': DataFrame, 'y': Series}
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    X, y = make_supervised(
        df,
        price_col=str(params.get("price_col", "close")),
        horizon=int(params.get("horizon", 1)),
        target_type=str(params.get("target_type", "direction")),
        lags=tuple(params.get("lags", (1, 2, 3, 5, 10))),
        windows=tuple(params.get("windows", (5, 10, 20))),
        dropna=bool(params.get("dropna", True)),
    )
    return {"X": X, "y": y}


if __name__ == "__main__":
    # Mock Data：生成一段随机游走价格序列
    rng = np.random.default_rng(0)
    n = 300
    ret = rng.normal(loc=0.0005, scale=0.01, size=n)
    close = 100 * np.cumprod(1 + ret)
    df_demo = pd.DataFrame({"close": close})

    out = solve(df_demo, params={"horizon": 1, "target_type": "direction"})
    print(out["X"].head())
    print(out["y"].value_counts())

