# -*- coding: utf-8 -*-
# 数据分箱：pd.cut / 分箱统计

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import pandas as pd


def cut_bins(
    s: pd.Series,
    *,
    bins: int = 3,
    labels: Optional[list] = None,
    include_lowest: bool = True,
) -> pd.Series:
    """
    连续变量等宽分箱（pd.cut 的轻量封装）。

    Args:
        s: 输入序列（建议为数值型）。
        bins: 分箱数。
        labels: 分箱标签（可选）。
        include_lowest: 是否包含最小值边界。

    Returns:
        pd.Series: 分箱结果（Categorical）。
    """
    return pd.cut(s, bins=bins, labels=labels, include_lowest=include_lowest)


def bin_stats(
    df: pd.DataFrame,
    *,
    feature: str,
    target: Optional[str] = None,
    bins: int = 3,
) -> pd.DataFrame:
    """
    计算分箱后的基础统计：样本数、（可选）目标均值/和。

    Args:
        df: 数据表。
        feature: 需要分箱的特征列名。
        target: 目标列名（可选）。若提供，将统计 target 的均值与和。
        bins: 分箱数。

    Returns:
        pd.DataFrame: 每个箱的统计表。
    """
    if feature not in df.columns:
        raise ValueError(f"feature 不存在：{feature}")
    if target is not None and target not in df.columns:
        raise ValueError(f"target 不存在：{target}")

    b = cut_bins(df[feature], bins=bins)
    out = pd.DataFrame({"count": df.groupby(b)[feature].count()})
    if target is not None:
        out["target_sum"] = df.groupby(b)[target].sum()
        out["target_mean"] = df.groupby(b)[target].mean()
    return out


def solve(data: Union[pd.DataFrame, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：分箱并输出统计表。

    Args:
        data: DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - feature: str（必填）
            - target: str | None
            - bins: int

    Returns:
        dict: {'stats': DataFrame}
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    feature = params.get("feature")
    if not feature:
        raise ValueError("params.feature 必填。")
    target = params.get("target")
    bins = int(params.get("bins", 3))
    return {"stats": bin_stats(df, feature=feature, target=target, bins=bins)}


if __name__ == "__main__":
    # Mock Data
    demo = pd.DataFrame(
        {
            "age": [22, 25, 20, 35, 32, 38, 50, 46],
            "default": [1, 1, 0, 0, 1, 0, 0, 1],
        }
    )
    out = solve(demo, params={"feature": "age", "target": "default", "bins": 3})
    print(out["stats"])

