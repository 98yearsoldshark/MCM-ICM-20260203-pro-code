# -*- coding: utf-8 -*-
# 类别特征编码：One-Hot / Label / Target Encoding（轻量实现）

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


def one_hot_encode(
    df: pd.DataFrame,
    *,
    columns: Sequence[str],
    drop_first: bool = False,
    dummy_na: bool = False,
) -> pd.DataFrame:
    """
    One-Hot 编码（pandas.get_dummies 封装）。

    Args:
        df: 输入数据表。
        columns: 需要编码的列名列表。
        drop_first: 是否丢弃每个类别的第一列（避免虚拟变量陷阱）。
        dummy_na: 是否将 NaN 视为一个类别。

    Returns:
        pd.DataFrame: 编码后的新表。
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列：{missing}")
    return pd.get_dummies(df, columns=list(columns), drop_first=drop_first, dummy_na=dummy_na)


def label_encode(df: pd.DataFrame, *, columns: Sequence[str]) -> Tuple[pd.DataFrame, Dict[str, Dict[Any, int]]]:
    """
    Label Encoding：把类别映射为整数（每列独立编码）。

    Args:
        df: 输入数据表。
        columns: 需要编码的列名列表。

    Returns:
        (df_encoded, mapping)
        - df_encoded: 编码后的新表
        - mapping: dict[col][category] = code
    """
    out = df.copy()
    mapping: Dict[str, Dict[Any, int]] = {}
    for c in columns:
        if c not in out.columns:
            raise ValueError(f"缺少列：{c}")
        cat = out[c].astype("category")
        out[c] = cat.cat.codes.replace({-1: np.nan})  # NaN 保持 NaN
        mapping[c] = {k: int(v) for v, k in enumerate(cat.cat.categories)}
    return out, mapping


def target_encode(
    df: pd.DataFrame,
    *,
    feature: str,
    target: str,
    smoothing: float = 10.0,
    min_samples_leaf: int = 1,
    noise: float = 0.0,
    random_state: int = 42,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Target Encoding（均值编码，带平滑项）。

    适用：二分类/回归等 target 为数值型的场景；对高基数类别特征很常用。
    注意：严格做法应在训练集上拟合映射，并在测试集上 transform；这里提供基础实现。

    Args:
        df: 数据表。
        feature: 类别特征列。
        target: 目标列（数值）。
        smoothing: 平滑强度（越大越靠近全局均值）。
        min_samples_leaf: 最小样本数阈值（低频类别会更靠近全局均值）。
        noise: 是否添加少量噪声（可缓解过拟合；默认 0 表示不加）。
        random_state: 噪声随机种子。

    Returns:
        (encoded, mapping_table)
        - encoded: 与 df 行对齐的编码值（Series）
        - mapping_table: 每个类别的统计与编码值（DataFrame）
    """
    if feature not in df.columns:
        raise ValueError(f"feature 不存在：{feature}")
    if target not in df.columns:
        raise ValueError(f"target 不存在：{target}")

    g = df.groupby(feature)[target].agg(["mean", "count"]).rename(columns={"mean": "target_mean", "count": "count"})
    global_mean = float(df[target].mean())

    # 平滑：count 越大越信任该类别均值
    smoothing_factor = 1.0 / (1.0 + np.exp(-(g["count"] - min_samples_leaf) / max(smoothing, 1e-9)))
    g["encoded"] = global_mean * (1.0 - smoothing_factor) + g["target_mean"] * smoothing_factor

    encoded = df[feature].map(g["encoded"]).astype(float)

    if noise and noise > 0:
        rng = np.random.default_rng(int(random_state))
        encoded = encoded * (1.0 + rng.normal(loc=0.0, scale=float(noise), size=len(encoded)))

    g = g.reset_index()
    g["global_mean"] = global_mean
    return encoded, g


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：编码工具。

    Args:
        data: DataFrame 或 dict {'df': DataFrame}。
        params: 参数：
            - mode: {"onehot","label","target"}（必填）
            - onehot: columns, drop_first, dummy_na
            - label: columns
            - target: feature, target, smoothing, min_samples_leaf, noise, random_state

    Returns:
        dict: 根据 mode 返回不同字段。
    """
    params = params or {}
    if isinstance(data, dict):
        df = data.get("df", data.get("data"))
    else:
        df = data
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data 必须为 DataFrame 或包含 DataFrame 的 dict。")

    mode = str(params.get("mode", "")).lower()
    if mode == "onehot":
        cols = params.get("columns")
        if not cols:
            raise ValueError("onehot 模式下 params.columns 必填。")
        out = one_hot_encode(df, columns=cols, drop_first=bool(params.get("drop_first", False)), dummy_na=bool(params.get("dummy_na", False)))
        return {"data": out}
    if mode == "label":
        cols = params.get("columns")
        if not cols:
            raise ValueError("label 模式下 params.columns 必填。")
        out, mapping = label_encode(df, columns=cols)
        return {"data": out, "mapping": mapping}
    if mode == "target":
        feature = params.get("feature")
        target = params.get("target")
        if not feature or not target:
            raise ValueError("target 模式下 params.feature/params.target 必填。")
        encoded, mapping_table = target_encode(
            df,
            feature=str(feature),
            target=str(target),
            smoothing=float(params.get("smoothing", 10.0)),
            min_samples_leaf=int(params.get("min_samples_leaf", 1)),
            noise=float(params.get("noise", 0.0)),
            random_state=int(params.get("random_state", 42)),
        )
        return {"encoded": encoded, "mapping_table": mapping_table}
    raise ValueError("params.mode 必须为 onehot/label/target 之一。")


if __name__ == "__main__":
    demo = pd.DataFrame(
        {
            "city": ["北京", "上海", "广州", "深圳", "北京", None],
            "y": [1, 0, 1, 0, 1, 0],
        }
    )
    out = solve(demo, params={"mode": "onehot", "columns": ["city"], "dummy_na": True})
    print(out["data"])

