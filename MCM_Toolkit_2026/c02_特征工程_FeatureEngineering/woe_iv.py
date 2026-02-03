# -*- coding: utf-8 -*-
# WOE/IV：常用于二分类任务的特征筛选（信用评分/流失预警等）

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd


def woe_iv_for_feature(
    df: pd.DataFrame,
    *,
    feature: str,
    target: str,
    bins: int = 10,
    binning: str = "cut",
) -> Dict[str, Any]:
    """
    计算单个特征的 WOE/IV（二分类）。

    约定：target 为 0/1（1 表示“坏样本/正类”）。

    Args:
        df: 数据表。
        feature: 特征列名。
        target: 目标列名（0/1）。
        bins: 分箱数。
        binning: {"cut","qcut"}，cut 等宽分箱，qcut 等频分箱。

    Returns:
        dict:
            - detail: 每箱统计表（含 WOE/IV）
            - iv: 该特征的 IV 值（float）
    """
    if feature not in df.columns:
        raise ValueError(f"feature 不存在：{feature}")
    if target not in df.columns:
        raise ValueError(f"target 不存在：{target}")

    x = df[feature]
    y = df[target]
    if binning == "cut":
        b = pd.cut(x, bins=bins, include_lowest=True)
    elif binning == "qcut":
        # duplicates='drop'：当数据重复导致无法精确分箱时自动降级
        b = pd.qcut(x, q=bins, duplicates="drop")
    else:
        raise ValueError(f"不支持的 binning: {binning}")

    total = y.groupby(b).count()
    bad = y.groupby(b).sum()
    good = total - bad

    detail = pd.DataFrame({"total": total, "bad": bad, "good": good})
    # 比率：避免除 0
    bad_rate = detail["bad"] / max(detail["bad"].sum(), 1.0)
    good_rate = detail["good"] / max(detail["good"].sum(), 1.0)
    detail["bad_rate"] = bad_rate
    detail["good_rate"] = good_rate

    with np.errstate(divide="ignore", invalid="ignore"):
        detail["woe"] = np.log(detail["bad_rate"] / detail["good_rate"])
    detail = detail.replace({"woe": {np.inf: 0.0, -np.inf: 0.0}}).fillna({"woe": 0.0})
    detail["iv_bin"] = detail["woe"] * (detail["bad_rate"] - detail["good_rate"])
    iv = float(detail["iv_bin"].sum())
    return {"detail": detail, "iv": iv}


def woe_iv(
    df: pd.DataFrame,
    *,
    target: str,
    features: Optional[Sequence[str]] = None,
    bins: int = 10,
    binning: str = "cut",
) -> pd.DataFrame:
    """
    批量计算多个特征的 IV。

    Args:
        df: 数据表。
        target: 目标列名（0/1）。
        features: 需要计算的特征列名列表；None 表示除 target 外的全部列。
        bins: 分箱数。
        binning: {"cut","qcut"}。

    Returns:
        pd.DataFrame: 两列：feature, iv（按 iv 降序）。
    """
    if features is None:
        features = [c for c in df.columns if c != target]

    rows: List[Dict[str, Any]] = []
    for f in features:
        # 跳过明显非数值列（WOE/IV 常用于连续变量；离散变量可先编码或自行分箱）
        if not pd.api.types.is_numeric_dtype(df[f]):
            continue
        try:
            iv = woe_iv_for_feature(df, feature=f, target=target, bins=bins, binning=binning)["iv"]
        except Exception:
            continue
        rows.append({"feature": f, "iv": iv})

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("iv", ascending=False).reset_index(drop=True)


def solve(data: Union[pd.DataFrame, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：计算 WOE/IV。

    Args:
        data: DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - target: str（必填，0/1）
            - features: list[str] | None
            - bins: int
            - binning: {"cut","qcut"}
            - detail_feature: str | None（若提供，则额外返回该特征的分箱明细）

    Returns:
        dict:
            - iv_table: DataFrame（批量 IV 结果）
            - detail: DataFrame | None（单特征明细）
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    target = params.get("target")
    if not target:
        raise ValueError("params.target 必填。")
    features = params.get("features")
    bins = int(params.get("bins", 10))
    binning = params.get("binning", "cut")

    iv_table = woe_iv(df, target=target, features=features, bins=bins, binning=binning)

    detail_feature = params.get("detail_feature")
    detail = None
    if detail_feature:
        detail = woe_iv_for_feature(df, feature=detail_feature, target=target, bins=bins, binning=binning)[
            "detail"
        ]

    return {"iv_table": iv_table, "detail": detail}


if __name__ == "__main__":
    # Mock Data
    demo = pd.DataFrame(
        {
            "age": [22, 25, 20, 35, 32, 38, 50, 46],
            "income": [3000, 4000, 2000, 8000, 5000, 7000, 12000, 9000],
            "default": [1, 1, 0, 0, 1, 0, 0, 1],  # 1=坏样本
        }
    )
    out = solve(demo, params={"target": "default", "bins": 3, "detail_feature": "age"})
    print(out["iv_table"])
    print(out["detail"])

