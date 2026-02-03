# -*- coding: utf-8 -*-
# 数据清洗：重复值、缺失值、异常值（简单版）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np
import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param


def clean_tabular_data(df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    对表格数据做常见清洗（可按需开启）。

    Args:
        df: 输入数据表。
        params: 清洗参数。常用键：
            - drop_duplicates: bool，是否去重（默认 False）
            - drop_duplicates_subset: list[str] | None，按哪些列判断重复（默认 None）
            - fillna: dict | None，缺失值填充配置（默认 None）。支持：
                - strategy: {"mean","median","mode","ffill","bfill","constant"}
                - value: 常数填充值（strategy="constant" 时使用）
                - columns: list[str] | None（默认 None 表示全部列）
            - outlier_zscore: dict | None，基于 z-score 的异常值处理（默认 None）。支持：
                - threshold: float（默认 3.0）
                - columns: list[str] | None（默认数值列）
                - clip: bool（默认 False；True 表示把异常值裁剪到阈值边界，而不是标记）

    Returns:
        pd.DataFrame: 清洗后的新 DataFrame（不修改原 df）。
    """
    params = params or {}
    out = df.copy()

    if get_param(params, "drop_duplicates", False):
        subset = get_param(params, "drop_duplicates_subset", None)
        out = out.drop_duplicates(subset=subset)

    fillna_cfg = get_param(params, "fillna", None)
    if isinstance(fillna_cfg, dict):
        strategy = fillna_cfg.get("strategy", "mean")
        columns = fillna_cfg.get("columns", None)
        value = fillna_cfg.get("value", 0)

        if columns is None:
            columns = list(out.columns)

        if strategy in {"mean", "median"}:
            # 仅对数值列做聚合填充
            num_cols = [c for c in columns if pd.api.types.is_numeric_dtype(out[c])]
            if strategy == "mean":
                fill_values = out[num_cols].mean()
            else:
                fill_values = out[num_cols].median()
            out[num_cols] = out[num_cols].fillna(fill_values)
        elif strategy == "mode":
            for c in columns:
                if out[c].isna().any():
                    mode = out[c].mode(dropna=True)
                    if not mode.empty:
                        out[c] = out[c].fillna(mode.iloc[0])
        elif strategy in {"ffill", "bfill"}:
            method = "ffill" if strategy == "ffill" else "bfill"
            out[columns] = out[columns].fillna(method=method)
        elif strategy == "constant":
            out[columns] = out[columns].fillna(value)
        else:
            raise ValueError(f"不支持的 fillna.strategy: {strategy}")

    outlier_cfg = get_param(params, "outlier_zscore", None)
    if isinstance(outlier_cfg, dict):
        threshold = float(outlier_cfg.get("threshold", 3.0))
        columns = outlier_cfg.get("columns", None)
        clip = bool(outlier_cfg.get("clip", False))

        if columns is None:
            columns = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]

        for c in columns:
            s = out[c]
            if not pd.api.types.is_numeric_dtype(s):
                continue
            mu = s.mean()
            sigma = s.std(ddof=0)
            if sigma == 0 or np.isnan(sigma):
                continue
            z = (s - mu) / sigma
            mask = z.abs() > threshold
            if clip:
                out.loc[mask, c] = mu + np.sign(z[mask]) * threshold * sigma
            else:
                # 标记为缺失，让 fillna 决定如何处理
                out.loc[mask, c] = np.nan

    return out


def solve(data: Union[pd.DataFrame, Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：对数据进行清洗并返回结果。

    Args:
        data: 输入数据，支持：
            - pd.DataFrame
            - dict: {'df': DataFrame}（或键名 'data'）
        params: 见 clean_tabular_data。

    Returns:
        dict: {'data': 清洗后的 DataFrame}
    """
    if isinstance(data, pd.DataFrame):
        df = data
    elif isinstance(data, dict):
        df = data.get("df", data.get("data"))
        if not isinstance(df, pd.DataFrame):
            raise TypeError("data 为 dict 时必须提供 DataFrame（键 'df' 或 'data'）。")
    else:
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    cleaned = clean_tabular_data(df, params=params)
    return {"data": cleaned}


if __name__ == "__main__":
    # Mock Data：包含重复、缺失与异常值
    demo = pd.DataFrame(
        {
            "x1": [1, 1, 2, np.nan, 100],
            "x2": [10, 10, np.nan, 12, 11],
            "cat": ["A", "A", "B", None, "C"],
        }
    )
    result = solve(
        demo,
        params={
            "drop_duplicates": True,
            "fillna": {"strategy": "mean"},
            "outlier_zscore": {"threshold": 2.0, "clip": False},
        },
    )
    print(result["data"])
