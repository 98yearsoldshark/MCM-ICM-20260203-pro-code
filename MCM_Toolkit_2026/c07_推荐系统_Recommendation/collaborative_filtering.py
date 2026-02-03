# -*- coding: utf-8 -*-
# 协同过滤（Item-based）：基于物品评分相关系数的简易推荐

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd


def build_user_item_matrix(
    df: pd.DataFrame,
    *,
    user_col: str,
    item_col: str,
    rating_col: str,
) -> pd.DataFrame:
    """
    将长表评分数据转换为用户-物品矩阵（pivot）。

    Args:
        df: 输入长表，至少包含 user_col/item_col/rating_col。
        user_col: 用户列名。
        item_col: 物品列名。
        rating_col: 评分列名。

    Returns:
        pd.DataFrame: 行=用户，列=物品，值=评分（缺失为 NaN）。
    """
    missing = [c for c in [user_col, item_col, rating_col] if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列：{missing}")
    return df.pivot_table(index=user_col, columns=item_col, values=rating_col)


def item_based_recommend(
    ratings_long: pd.DataFrame,
    *,
    user_col: str,
    item_col: str,
    rating_col: str,
    target_item: str,
    min_count: int = 20,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    基于与 target_item 的相关系数做物品推荐（Item-based CF）。

    计算流程（与原始示例一致）：
    1) 统计每个物品的平均分与评分次数
    2) 构建用户-物品矩阵
    3) 计算所有物品与 target_item 的相关系数
    4) 合并评分次数并按阈值过滤

    Args:
        ratings_long: 长表评分数据。
        user_col: 用户列名。
        item_col: 物品列名。
        rating_col: 评分列名。
        target_item: 目标物品名称（列名需与 item_col 的取值一致）。
        min_count: 最小评分次数阈值（过滤冷门物品）。
        top_n: 返回 Top-N。

    Returns:
        pd.DataFrame: 推荐结果表（相关系数、评分次数、平均分）。
    """
    # 物品统计
    item_stats = ratings_long.groupby(item_col)[rating_col].agg(["mean", "count"]).rename(
        columns={"mean": "rating_mean", "count": "rating_count"}
    )

    user_item = build_user_item_matrix(ratings_long, user_col=user_col, item_col=item_col, rating_col=rating_col)
    if target_item not in user_item.columns:
        raise ValueError(f"target_item 不存在于物品列中：{target_item}")

    target_r = user_item[target_item]
    corr = user_item.corrwith(target_r)
    out = pd.DataFrame({"corr": corr}).dropna()

    out = out.join(item_stats, how="left")
    out = out[out["rating_count"].fillna(0).astype(int) >= int(min_count)]
    out = out.sort_values("corr", ascending=False)
    return out.head(int(top_n))


def solve(data: Union[pd.DataFrame, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：协同过滤推荐。

    Args:
        data: 长表评分数据 DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - user_col: str（默认 'user'）
            - item_col: str（默认 'item'）
            - rating_col: str（默认 'rating'）
            - target_item: str（必填）
            - min_count: int（默认 5）
            - top_n: int（默认 10）

    Returns:
        dict: {'recommendations': DataFrame}
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    user_col = params.get("user_col", "user")
    item_col = params.get("item_col", "item")
    rating_col = params.get("rating_col", "rating")
    target_item = params.get("target_item")
    if not target_item:
        raise ValueError("params.target_item 必填。")
    min_count = int(params.get("min_count", 5))
    top_n = int(params.get("top_n", 10))

    rec = item_based_recommend(
        df,
        user_col=user_col,
        item_col=item_col,
        rating_col=rating_col,
        target_item=str(target_item),
        min_count=min_count,
        top_n=top_n,
    )
    return {"recommendations": rec}


if __name__ == "__main__":
    # Mock Data：随机生成用户-物品评分
    rng = np.random.default_rng(0)
    users = [f"U{i}" for i in range(1, 51)]
    items = ["A", "B", "C", "D", "E", "F"]

    rows = []
    for u in users:
        for it in items:
            if rng.random() < 0.6:  # 稀疏
                rows.append({"user": u, "item": it, "rating": float(rng.integers(1, 6))})
    df_demo = pd.DataFrame(rows)

    out = solve(df_demo, params={"target_item": "A", "min_count": 5, "top_n": 5})
    print(out["recommendations"])

