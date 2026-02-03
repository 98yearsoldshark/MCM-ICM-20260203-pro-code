# -*- coding: utf-8 -*-
# 多级/层次模糊综合评价（Hierarchical Fuzzy Comprehensive Evaluation）
#
# 常见场景：
# - 准则层：m 个子系统（或一级指标），权重 Wc
# - 指标层：每个子系统下有若干二级指标，权重 Wi
# - 每个二级指标对应到 k 个等级（优/良/中/差...）的隶属度 -> 关系矩阵 R_i（n_i×k）
# - 先对每个子系统做一次模糊综合评价得到 B_i（1×k），再用 Wc 汇总得到总评价 B（1×k）
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../多目标模糊综合评价模型Python代码.docx

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.fuzzy_comprehensive import fuzzy_comprehensive_evaluation


def frequency_weights(score_matrix: Union[np.ndarray, Sequence[Sequence[float]]], *, n_bins: int = 5) -> np.ndarray:
    """
    频数统计法确定权重（偏启发式，来自资料中的“频数统计法确定权重”示意）。

    用法假设：
    - score_matrix 的每一行对应一个指标；
    - 每一列是不同专家/样本对该指标的打分；
    - 对每行做分箱，取频数最高箱的中点作为“典型得分”，再归一化为权重。
    """
    X = np.asarray(score_matrix, dtype=float)
    if X.ndim != 2:
        raise ValueError("score_matrix 必须为二维矩阵。")
    if X.shape[0] < 1 or X.shape[1] < 1:
        raise ValueError("score_matrix 不能为空。")
    b = int(n_bins)
    if b < 1:
        raise ValueError("n_bins 必须 >= 1。")

    w = np.zeros(X.shape[0], dtype=float)
    for i in range(X.shape[0]):
        row = X[i, :]
        if np.allclose(row, row[0]):
            w[i] = float(row[0])
            continue
        hist, edges = np.histogram(row, bins=b)
        idx = int(np.argmax(hist))
        mid = 0.5 * (edges[idx] + edges[idx + 1])
        w[i] = float(mid)

    s = float(np.sum(w))
    if s <= 0:
        raise ValueError("frequency_weights 计算得到的权重和 <= 0，无法归一化。")
    return (w / s).astype(float)


def hierarchical_fuzzy_evaluation(
    criterion_weights: Union[np.ndarray, Sequence[float]],
    indicator_weights_list: Sequence[Union[np.ndarray, Sequence[float]]],
    membership_matrices: Sequence[Union[np.ndarray, Sequence[Sequence[float]]]],
    *,
    method: str = "max_min",
    grade_scores: Optional[Sequence[float]] = None,
    normalize: bool = True,
) -> Dict[str, Any]:
    """
    两级模糊综合评价。

    Args:
        criterion_weights: 准则层权重 Wc（m,）。
        indicator_weights_list: 指标层权重列表 [W1, W2, ...]，长度 m；Wi 形如 (n_i,)。
        membership_matrices: 隶属度矩阵列表 [R1, R2, ...]，长度 m；Ri 形如 (n_i×k)。
        method: 合成算子（同 fuzzy_comprehensive_evaluation）：
            - "weighted_average"
            - "max_min"（资料示意多用该算子）
        grade_scores: 等级分值（k,），用于输出清晰化分数 score。
        normalize: 是否对权重与 B 归一化。

    Returns:
        dict:
            - B: 总评价向量（k,）
            - score/best_grade
            - B_groups: list[ndarray]（每个子系统的评价向量）
            - R_upper: ndarray（m×k，上层关系矩阵）
    """
    Wc = np.asarray(criterion_weights, dtype=float).reshape(-1)
    m = int(Wc.size)
    if m < 1:
        raise ValueError("criterion_weights 不能为空。")
    if len(indicator_weights_list) != m or len(membership_matrices) != m:
        raise ValueError("indicator_weights_list 与 membership_matrices 的长度必须等于准则层个数 m。")

    B_groups: List[np.ndarray] = []
    for Wi, Ri in zip(indicator_weights_list, membership_matrices):
        out_i = fuzzy_comprehensive_evaluation(Wi, Ri, method=method, normalize=normalize)
        B_groups.append(np.asarray(out_i["B"], dtype=float))

    # 上层关系矩阵：每行就是一个子系统的评价向量
    R_upper = np.vstack(B_groups)
    out = fuzzy_comprehensive_evaluation(Wc, R_upper, method=method, grade_scores=grade_scores, normalize=normalize)
    return {
        "B": np.asarray(out["B"], dtype=float),
        "score": out["score"],
        "best_grade": int(out["best_grade"]),
        "B_groups": B_groups,
        "R_upper": R_upper,
        "criterion_weights": np.asarray(out["weights"], dtype=float),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：多级/层次模糊综合评价（两级）。

    Args:
        data: dict，包含：
            - criterion_weights / group_weights: (m,)
            - indicator_weights_list / sub_weights_list: list[(n_i,)]
            - membership_matrices / relation_matrices: list[(n_i×k)]
        params:
            - method: "weighted_average" | "max_min"
            - grade_scores: list[float] | None
            - normalize: bool

    Returns:
        dict: 见 hierarchical_fuzzy_evaluation()。
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")

    Wc = data.get("criterion_weights", data.get("group_weights"))
    Ws = data.get("indicator_weights_list", data.get("sub_weights_list"))
    Rs = data.get("membership_matrices", data.get("relation_matrices"))
    if Wc is None or Ws is None or Rs is None:
        raise ValueError("data 需要包含 criterion_weights/group_weights、indicator_weights_list/sub_weights_list、membership_matrices/relation_matrices。")

    return hierarchical_fuzzy_evaluation(
        Wc,
        Ws,
        Rs,
        method=str(params.get("method", "max_min")),
        grade_scores=params.get("grade_scores"),
        normalize=bool(params.get("normalize", True)),
    )


if __name__ == "__main__":
    # Mock Data：2 个子系统，每个子系统 3 个指标，4 个等级
    grade_scores = [100, 80, 60, 40]

    Wc = [0.6, 0.4]  # 准则层权重（子系统权重）
    Ws = [
        [0.5, 0.3, 0.2],  # 子系统1：指标权重
        [0.2, 0.5, 0.3],  # 子系统2：指标权重
    ]
    Rs = [
        # 子系统1：3×4 隶属度
        [
            [0.7, 0.2, 0.1, 0.0],
            [0.2, 0.6, 0.2, 0.0],
            [0.1, 0.3, 0.5, 0.1],
        ],
        # 子系统2：3×4 隶属度
        [
            [0.3, 0.5, 0.2, 0.0],
            [0.6, 0.3, 0.1, 0.0],
            [0.2, 0.4, 0.3, 0.1],
        ],
    ]

    out = solve(
        {"criterion_weights": Wc, "indicator_weights_list": Ws, "membership_matrices": Rs},
        {"method": "max_min", "grade_scores": grade_scores},
    )
    print("B =", np.round(out["B"], 4))
    print("score =", out["score"])
    print("best_grade =", out["best_grade"])

