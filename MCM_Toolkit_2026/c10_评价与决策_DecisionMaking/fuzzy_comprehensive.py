# -*- coding: utf-8 -*-
# 模糊综合评价（Fuzzy Comprehensive Evaluation）
#
# 常见场景：多指标（权重 W）+ 各指标对“评价等级”的隶属度矩阵 R -> 综合评价向量 B
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../评价与决策类题型参考代码.../模糊综合评价*.rar

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def fuzzy_comprehensive_evaluation(
    weights: Union[np.ndarray, Sequence[float]],
    membership: Union[np.ndarray, Sequence[Sequence[float]]],
    *,
    method: str = "weighted_average",
    grade_scores: Optional[Sequence[float]] = None,
    normalize: bool = True,
) -> Dict[str, Any]:
    """
    模糊综合评价（单层）。

    Args:
        weights: 权重向量 W（n,）。
        membership: 隶属度矩阵 R（n×k），n 个指标，k 个等级；每行通常满足和为 1。
        method: 合成算子：
            - "weighted_average": B = W·R（加权平均）
            - "max_min": B_j = max_i min(W_i, R_ij)（最大最小）
        grade_scores: 等级分值（k,），用于把 B 进一步“清晰化”为一个分数：score = B·grade_scores。
        normalize: 是否对 W、B 进行归一化处理（默认 True）。

    Returns:
        dict:
            - B: 综合评价向量（k,）
            - score: float | None（若提供 grade_scores）
            - best_grade: int（0-based，B 最大的等级索引）
            - weights: 归一化后的权重
    """
    w = np.asarray(weights, dtype=float).reshape(-1)
    R = np.asarray(membership, dtype=float)
    if R.ndim != 2:
        raise ValueError("membership 必须为二维矩阵（n×k）。")
    n, k = R.shape
    if w.shape != (n,):
        raise ValueError("weights 长度必须等于 membership 的行数 n。")
    if np.any(w < 0):
        raise ValueError("weights 不能为负。")
    if np.any(R < 0):
        raise ValueError("membership 中隶属度不能为负。")

    if normalize:
        if w.sum() == 0:
            raise ValueError("weights 之和不能为 0。")
        w = w / w.sum()

    method = str(method).lower()
    if method in {"weighted_average", "weighted", "average"}:
        B = w @ R
    elif method in {"max_min", "maxmin", "max-min"}:
        # 对每个等级 j：max_i min(w_i, r_ij)
        B = np.max(np.minimum(w[:, None], R), axis=0)
    else:
        raise ValueError("method 必须为 'weighted_average' 或 'max_min'。")

    if normalize:
        s = float(B.sum())
        if s > 0:
            B = B / s

    best_grade = int(np.argmax(B))
    score = None
    if grade_scores is not None:
        gs = np.asarray(list(grade_scores), dtype=float).reshape(-1)
        if gs.shape != (k,):
            raise ValueError("grade_scores 的长度必须等于等级数 k。")
        score = float(B @ gs)

    return {"B": B, "score": score, "best_grade": best_grade, "weights": w}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：模糊综合评价。

    Args:
        data: dict，包含：
            - weights: W（n,）
            - membership: R（n×k）
        params: 参数：
            - method: 'weighted_average' | 'max_min'
            - grade_scores: list[float] | None
            - normalize: bool

    Returns:
        dict: 见 fuzzy_comprehensive_evaluation() 返回值。
    """
    params = params or {}
    if not isinstance(data, dict) or "weights" not in data or "membership" not in data:
        raise TypeError("data 必须为 dict，且包含 weights 与 membership。")

    return fuzzy_comprehensive_evaluation(
        data["weights"],
        data["membership"],
        method=str(params.get("method", "weighted_average")),
        grade_scores=params.get("grade_scores"),
        normalize=bool(params.get("normalize", True)),
    )


if __name__ == "__main__":
    # Mock Data：
    # 3 个指标（权重 W）+ 4 个等级（优/良/中/差）隶属度
    W = [0.5, 0.3, 0.2]
    R = [
        [0.7, 0.2, 0.1, 0.0],
        [0.2, 0.6, 0.2, 0.0],
        [0.1, 0.3, 0.5, 0.1],
    ]
    grade_scores = [100, 80, 60, 40]
    out = solve({"weights": W, "membership": R}, {"method": "weighted_average", "grade_scores": grade_scores})
    print("B =", np.round(out["B"], 4))
    print("best_grade =", out["best_grade"])
    print("score =", out["score"])

