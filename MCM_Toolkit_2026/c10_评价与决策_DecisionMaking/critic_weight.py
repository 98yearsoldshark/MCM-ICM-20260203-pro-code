# -*- coding: utf-8 -*-
# CRITIC 客观赋权法：综合“对比强度（标准差）”与“冲突性（相关性）”给权重
#
# 常见流程：
# 1) 对决策矩阵做归一化（min-max 或 z-score）
# 2) 计算每个指标的标准差 σ_j（对比强度）
# 3) 计算指标间相关系数 r_jk（冲突性）
# 4) 信息量 C_j = σ_j * Σ_k (1 - r_jk)
# 5) 权重 w_j = C_j / Σ C_j
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码（评价/决策相关资料中常见 CRITIC/综合评价方法）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_2d(x: Any) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    if a.ndim != 2:
        raise ValueError("决策矩阵必须为二维（m×n）。")
    return a


def _benefit_transform(x: np.ndarray, is_benefit: Optional[Sequence[bool]]) -> np.ndarray:
    if is_benefit is None:
        return x
    is_benefit = list(is_benefit)
    if len(is_benefit) != x.shape[1]:
        raise ValueError("is_benefit 的长度必须等于指标数 n。")
    out = x.copy()
    for j, ben in enumerate(is_benefit):
        if ben:
            continue
        col = out[:, j]
        out[:, j] = np.max(col) + np.min(col) - col
    return out


def _normalize(x: np.ndarray, method: str) -> np.ndarray:
    method = str(method).lower()
    if method in {"minmax", "min-max"}:
        xmin = np.min(x, axis=0)
        xmax = np.max(x, axis=0)
        denom = xmax - xmin
        denom[denom == 0] = 1.0
        return (x - xmin) / denom
    if method in {"zscore", "z-score"}:
        mu = np.mean(x, axis=0)
        sigma = np.std(x, axis=0, ddof=0)
        sigma[sigma == 0] = 1.0
        return (x - mu) / sigma
    if method in {"none", ""}:
        return x
    raise ValueError("normalize_method 必须为 minmax/zscore/none 之一。")


def critic_weight(
    decision_matrix: Union[np.ndarray, list],
    *,
    is_benefit: Optional[Sequence[bool]] = None,
    normalize_method: str = "minmax",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    计算 CRITIC 权重。

    Args:
        decision_matrix: X（m×n）。
        is_benefit: 指标类型（True=效益型，False=成本型）。
        normalize_method: 归一化方法（默认 minmax）。

    Returns:
        (weights, details)

        weights:
            shape=(n,) 的权重向量，和为 1。
        details:
            - normalized: 归一化后的矩阵
            - std: σ_j
            - corr: 相关系数矩阵 r_jk
            - conflict: Σ_k (1-r_jk)
            - info: C_j
    """
    X = _to_2d(decision_matrix)
    X = _benefit_transform(X, is_benefit=is_benefit)
    Z = _normalize(X, method=normalize_method)

    # 标准差（对比强度）
    std = np.std(Z, axis=0, ddof=0)

    # 相关矩阵（冲突性）；若某列常数导致 nan，则置 0（表示不相关）
    corr = np.corrcoef(Z, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)

    conflict = np.sum(1.0 - corr, axis=1)
    info = std * conflict

    if np.allclose(info.sum(), 0.0):
        w = np.ones(X.shape[1], dtype=float) / X.shape[1]
    else:
        w = info / info.sum()

    return w, {"normalized": Z, "std": std, "corr": corr, "conflict": conflict, "info": info}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：CRITIC 权重计算。

    Args:
        data: 决策矩阵或 dict：
            - 直接传入 X
            - dict: {'X': X}
        params: 参数：
            - is_benefit: list[bool] | None
            - normalize_method: str（默认 'minmax'）

    Returns:
        dict:
            - weights
            - std/corr/conflict/info/normalized
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X")
    else:
        X = data
    if X is None:
        raise ValueError("data 需要提供决策矩阵 X。")

    w, details = critic_weight(
        X,
        is_benefit=params.get("is_benefit"),
        normalize_method=str(params.get("normalize_method", "minmax")),
    )
    return {"weights": w, **details}


if __name__ == "__main__":
    # Mock Data：5 个方案、4 个指标（第 2 个指标为成本型）
    X = np.array(
        [
            [80, 30, 0.60, 120],
            [90, 50, 0.55, 100],
            [75, 45, 0.70, 110],
            [88, 35, 0.65, 130],
            [92, 40, 0.58, 105],
        ],
        dtype=float,
    )
    out = solve(X, {"is_benefit": [True, False, True, True]})
    print("weights =", np.round(out["weights"], 4))

