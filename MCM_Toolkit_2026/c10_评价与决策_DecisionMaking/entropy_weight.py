# -*- coding: utf-8 -*-
# 熵权法：根据指标的信息熵自动确定权重（客观赋权）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../评价与决策类题型参考代码.../熵权法（matlab）.zip

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
        raise ValueError("data 必须是二维决策矩阵（m×n）。")
    return a


def _benefit_transform(x: np.ndarray, is_benefit: Optional[Sequence[bool]]) -> np.ndarray:
    """把“成本型”指标转换为“效益型”指标（越大越好）。"""
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
        # 常用转换：max+min - x（避免 1/x 在 0 附近不稳定）
        out[:, j] = np.max(col) + np.min(col) - col
    return out


def entropy_weight(
    decision_matrix: Union[np.ndarray, list],
    *,
    is_benefit: Optional[Sequence[bool]] = None,
    eps: float = 1e-12,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    熵权法计算权重。

    Args:
        decision_matrix: 决策矩阵 X（m×n），m 个方案，n 个指标。
        is_benefit: 长度为 n 的 bool 序列；True 表示“效益型(越大越好)”，False 表示“成本型(越小越好)”。
            - 若为 None，则默认全部为效益型。
        eps: 数值稳定项，避免 log(0)。

    Returns:
        (weights, details)

        weights:
            shape=(n,) 的权重向量，和为 1。
        details:
            - p: 归一化比例矩阵 p_ij
            - entropy: 每个指标的信息熵 e_j
            - redundancy: 冗余度 d_j = 1 - e_j
    """
    x = _to_2d(decision_matrix)
    x = _benefit_transform(x, is_benefit=is_benefit)

    # 非负化：熵权法常用 p_ij = x_ij / sum_i x_ij，因此要求 x >= 0
    min_val = float(np.min(x))
    if min_val < 0:
        x = x - min_val

    col_sum = np.sum(x, axis=0)
    if np.any(col_sum <= 0):
        raise ValueError("存在全 0 指标列，无法计算熵权。请检查数据或做平移/缩放。")

    p = x / (col_sum + eps)
    m, n = p.shape
    k = 1.0 / np.log(m) if m > 1 else 0.0

    # 约定：0*log(0) = 0
    entropy = -k * np.sum(p * np.log(p + eps), axis=0)
    redundancy = 1.0 - entropy

    if np.allclose(redundancy.sum(), 0.0):
        # 所有指标熵都接近 1（信息量极低），退化为等权
        weights = np.ones(n, dtype=float) / n
    else:
        weights = redundancy / redundancy.sum()

    return weights, {"p": p, "entropy": entropy, "redundancy": redundancy}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：熵权法计算权重。

    Args:
        data: 决策矩阵（m×n）或 dict：
            - 直接传入 matrix
            - dict: {'X': matrix}（或 'decision_matrix'）
        params: 参数：
            - is_benefit: list[bool] | None
            - eps: float

    Returns:
        dict:
            - weights: ndarray shape=(n,)
            - entropy/redundancy/p
    """
    params = params or {}
    if isinstance(data, dict):
        x = data.get("X", data.get("decision_matrix"))
    else:
        x = data
    if x is None:
        raise ValueError("data 需要提供决策矩阵 X。")

    w, details = entropy_weight(
        x,
        is_benefit=params.get("is_benefit"),
        eps=float(params.get("eps", 1e-12)),
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
    print("entropy =", np.round(out["entropy"], 4))

