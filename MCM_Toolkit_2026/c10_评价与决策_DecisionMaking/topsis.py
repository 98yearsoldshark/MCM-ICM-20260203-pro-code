# -*- coding: utf-8 -*-
# TOPSIS 评价模型：贴近理想解排序（可配合熵权/AHP 等权重）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../评价与决策类题型参考代码.../TOPSIS评价模型具体步骤及代码.zip

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.entropy_weight import entropy_weight  # noqa: E402


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
    if method == "vector":
        denom = np.sqrt(np.sum(x**2, axis=0))
        denom[denom == 0] = 1.0
        return x / denom
    if method in {"minmax", "min-max"}:
        xmin = np.min(x, axis=0)
        xmax = np.max(x, axis=0)
        denom = xmax - xmin
        denom[denom == 0] = 1.0
        return (x - xmin) / denom
    raise ValueError("normalize_method 必须为 'vector' 或 'minmax'。")


def topsis(
    decision_matrix: Union[np.ndarray, list],
    *,
    weights: Optional[Sequence[float]] = None,
    is_benefit: Optional[Sequence[bool]] = None,
    normalize_method: str = "vector",
) -> Dict[str, Any]:
    """
    TOPSIS 计算贴近度并排序。

    Args:
        decision_matrix: X（m×n）。
        weights: 权重向量（n,）。若为 None，默认等权。
        is_benefit: 指标类型（True=效益型，False=成本型）。
        normalize_method: 归一化方法：'vector'（向量归一化）或 'minmax'。

    Returns:
        dict:
            - score: 贴近度 C（m,），越大越好
            - rank: 排名（m,），从 1 开始（1 为最好）
            - order: 排序索引（m,），score 从大到小
            - ideal_best/ideal_worst: 理想最优/最劣（n,）
            - d_pos/d_neg: 到理想最优/最劣的距离（m,）
    """
    x = _to_2d(decision_matrix)
    x = _benefit_transform(x, is_benefit=is_benefit)
    z = _normalize(x, method=normalize_method)

    m, n = z.shape
    if weights is None:
        w = np.ones(n, dtype=float) / n
    else:
        w = np.asarray(list(weights), dtype=float)
        if w.shape != (n,):
            raise ValueError("weights 的长度必须等于指标数 n。")
        if np.any(w < 0):
            raise ValueError("weights 不能为负。")
        if w.sum() == 0:
            raise ValueError("weights 之和不能为 0。")
        w = w / w.sum()

    v = z * w  # 加权归一化矩阵
    ideal_best = np.max(v, axis=0)
    ideal_worst = np.min(v, axis=0)

    d_pos = np.sqrt(np.sum((v - ideal_best) ** 2, axis=1))
    d_neg = np.sqrt(np.sum((v - ideal_worst) ** 2, axis=1))
    score = d_neg / (d_pos + d_neg + 1e-12)

    order = np.argsort(-score)  # 降序
    rank = np.empty_like(order)
    rank[order] = np.arange(1, m + 1)

    return {
        "score": score,
        "rank": rank,
        "order": order,
        "ideal_best": ideal_best,
        "ideal_worst": ideal_worst,
        "d_pos": d_pos,
        "d_neg": d_neg,
        "weights": w,
        "normalized": z,
        "weighted_normalized": v,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：TOPSIS 排序（可选权重来源）。

    Args:
        data: 决策矩阵（m×n）或 dict：
            - 直接传入 matrix
            - dict: {'X': matrix}（或 'decision_matrix'）
        params: 参数：
            - is_benefit: list[bool] | None
            - normalize_method: 'vector' | 'minmax'
            - weights: list[float] | None（若提供则直接用）
            - weights_method: {'equal','entropy'}（weights 为空时生效，默认 'equal'）

    Returns:
        dict: 见 topsis() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        x = data.get("X", data.get("decision_matrix"))
    else:
        x = data
    if x is None:
        raise ValueError("data 需要提供决策矩阵 X。")

    is_benefit = params.get("is_benefit")
    normalize_method = str(params.get("normalize_method", "vector"))

    weights = params.get("weights")
    if weights is None:
        weights_method = str(params.get("weights_method", "equal")).lower()
        if weights_method == "entropy":
            w, _ = entropy_weight(x, is_benefit=is_benefit)
            weights = w
        elif weights_method == "equal":
            weights = None
        else:
            raise ValueError("weights_method 必须为 'equal' 或 'entropy'。")

    return topsis(
        x,
        weights=weights,
        is_benefit=is_benefit,
        normalize_method=normalize_method,
    )


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

    out = solve(X, {"is_benefit": [True, False, True, True], "weights_method": "entropy"})
    print("weights =", np.round(out["weights"], 4))
    print("score =", np.round(out["score"], 4))
    print("rank  =", out["rank"])
    print("best idx (0-based) =", int(out["order"][0]))

