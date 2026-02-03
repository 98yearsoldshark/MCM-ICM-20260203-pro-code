# -*- coding: utf-8 -*-
# 表格数据预处理：数值/类别列的缺失值处理、缩放与 One-Hot 编码（sklearn ColumnTransformer）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param  # noqa: E402


def infer_column_types(
    df: pd.DataFrame,
    *,
    target_col: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """
    根据 dtype 推断数值列与类别列。

    Args:
        df: 输入数据表。
        target_col: 目标列名（若提供则从特征列中排除）。

    Returns:
        (numeric_cols, categorical_cols)
    """
    cols = [c for c in df.columns if c != target_col]
    num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in cols if c not in num]
    return num, cat


def build_preprocessor(
    df: pd.DataFrame,
    *,
    target_col: Optional[str] = None,
    numeric_cols: Optional[Sequence[str]] = None,
    categorical_cols: Optional[Sequence[str]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    构建 sklearn ColumnTransformer 预处理器。

    Args:
        df: 输入 DataFrame（仅用于推断列类型/顺序）。
        target_col: 目标列名（可选）。
        numeric_cols: 显式指定数值列（可选）。
        categorical_cols: 显式指定类别列（可选）。
        params: 配置参数，常用键：
            - numeric_imputer: {"mean","median","most_frequent","constant"}（默认 "median"）
            - categorical_imputer: {"most_frequent","constant"}（默认 "most_frequent"）
            - categorical_fill_value: str（categorical_imputer="constant" 时使用，默认 "missing"）
            - scale_numeric: bool（默认 True）
            - onehot: bool（默认 True）
            - onehot_drop: {"first"} | None（默认 None）
            - onehot_handle_unknown: str（默认 "ignore"）

    Returns:
        dict:
            - preprocessor: ColumnTransformer
            - numeric_cols: list[str]
            - categorical_cols: list[str]
    """
    params = params or {}

    if numeric_cols is None or categorical_cols is None:
        inferred_num, inferred_cat = infer_column_types(df, target_col=target_col)
        numeric_cols = list(numeric_cols) if numeric_cols is not None else inferred_num
        categorical_cols = list(categorical_cols) if categorical_cols is not None else inferred_cat
    else:
        numeric_cols = list(numeric_cols)
        categorical_cols = list(categorical_cols)

    num_steps = [
        ("imputer", SimpleImputer(strategy=str(get_param(params, "numeric_imputer", "median")))),
    ]
    if bool(get_param(params, "scale_numeric", True)):
        num_steps.append(("scaler", StandardScaler()))
    numeric_pipe = Pipeline(num_steps)

    cat_steps = [
        (
            "imputer",
            SimpleImputer(
                strategy=str(get_param(params, "categorical_imputer", "most_frequent")),
                fill_value=get_param(params, "categorical_fill_value", "missing"),
            ),
        ),
    ]
    if bool(get_param(params, "onehot", True)):
        cat_steps.append(
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown=str(get_param(params, "onehot_handle_unknown", "ignore")),
                    drop=get_param(params, "onehot_drop", None),
                ),
            )
        )
    categorical_pipe = Pipeline(cat_steps)

    transformers = []
    if numeric_cols:
        transformers.append(("num", numeric_pipe, numeric_cols))
    if categorical_cols:
        transformers.append(("cat", categorical_pipe, categorical_cols))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    return {"preprocessor": preprocessor, "numeric_cols": numeric_cols, "categorical_cols": categorical_cols}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：拟合预处理器并输出转换后的特征矩阵。

    Args:
        data: DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - target_col: str | None（若提供，则会输出 y 并从 X 中移除）
            - numeric_cols/categorical_cols: list[str] | None（可选）
            - 其余参数见 build_preprocessor

    Returns:
        dict:
            - X: 预处理后的特征矩阵（numpy.ndarray 或 scipy.sparse）
            - y: 目标变量（若提供 target_col）
            - preprocessor: ColumnTransformer
            - numeric_cols/categorical_cols: 列清单
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    target_col = params.get("target_col")
    numeric_cols = params.get("numeric_cols")
    categorical_cols = params.get("categorical_cols")

    built = build_preprocessor(
        df,
        target_col=target_col,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        params=params,
    )
    pre = built["preprocessor"]

    if target_col and target_col in df.columns:
        X_df = df.drop(columns=[target_col])
        y = df[target_col]
    else:
        X_df = df
        y = None

    X = pre.fit_transform(X_df)
    return {
        "X": X,
        "y": y,
        "preprocessor": pre,
        "numeric_cols": built["numeric_cols"],
        "categorical_cols": built["categorical_cols"],
    }


if __name__ == "__main__":
    # Mock Data：数值+类别
    demo = pd.DataFrame(
        {
            "age": [22, 25, None, 35, 32],
            "income": [3000, 4000, 2000, None, 5000],
            "gender": ["M", "F", "M", None, "F"],
            "y": [1, 0, 0, 1, 0],
        }
    )
    out = solve(demo, params={"target_col": "y"})
    print("numeric_cols:", out["numeric_cols"])
    print("categorical_cols:", out["categorical_cols"])
    print("X shape:", out["X"].shape)

