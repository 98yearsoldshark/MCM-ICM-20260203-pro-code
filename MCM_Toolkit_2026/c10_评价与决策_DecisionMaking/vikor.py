# -*- coding: utf-8 -*-
# VIKOR 评价模型：多指标折衷排序（适合“折衷解/妥协解”场景）
#
# 核心输出：
# - S：群体效用（加权距离）
# - R：个体遗憾（最大加权距离）
# - Q：折衷指标（综合 S 与 R）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码（综合评价方法资料中常见 VIKOR）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c10_评价与决策_DecisionMaking.critic_weight import critic_weight  # noqa: E402
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


def vikor(
    decision_matrix: Union[np.ndarray, list],
    *,
    weights: Optional[Sequence[float]] = None,
    is_benefit: Optional[Sequence[bool]] = None,
    v: float = 0.5,
) -> Dict[str, Any]:
    """
    VIKOR 排序（越小越好）。

    Args:
        decision_matrix: X（m×n）。
        weights: 权重（n,），若 None 则等权。
        is_benefit: 指标类型（True=效益型，False=成本型）。
        v: 折衷系数 v∈[0,1]。v 越大越强调群体效用 S；越小越强调个体遗憾 R。

    Returns:
        dict:
            - S/R/Q: (m,)
            - order: Q 从小到大排序索引
            - rank: 名次（从 1 开始；1 最好）
            - weights: 实际使用权重
            - f_star/f_minus: 每个指标的最优/最劣（在效益化后的空间）
    """
    X = _to_2d(decision_matrix)
    X = _benefit_transform(X, is_benefit=is_benefit)
    m, n = X.shape

    if not (0.0 <= float(v) <= 1.0):
        raise ValueError("v 必须在 [0,1]。")

    if weights is None:
        w = np.ones(n, dtype=float) / n
    else:
        w = np.asarray(list(weights), dtype=float).reshape(-1)
        if w.shape != (n,):
            raise ValueError("weights 长度必须等于指标数 n。")
        if np.any(w < 0):
            raise ValueError("weights 不能为负。")
        if w.sum() == 0:
            raise ValueError("weights 之和不能为 0。")
        w = w / w.sum()

    f_star = np.max(X, axis=0)
    f_minus = np.min(X, axis=0)
    denom = f_star - f_minus
    denom[denom == 0] = 1.0  # 避免除零（该指标对所有方案相同 -> 不影响）

    # 距离（越小越好）
    d = (f_star[None, :] - X) / denom[None, :]
    # S：加权距离和；R：最大加权距离
    S = d @ w
    R = np.max(d * w[None, :], axis=1)

    S_star, S_minus = float(np.min(S)), float(np.max(S))
    R_star, R_minus = float(np.min(R)), float(np.max(R))

    if abs(S_minus - S_star) < 1e-12:
        S_norm = np.zeros_like(S)
    else:
        S_norm = (S - S_star) / (S_minus - S_star)

    if abs(R_minus - R_star) < 1e-12:
        R_norm = np.zeros_like(R)
    else:
        R_norm = (R - R_star) / (R_minus - R_star)

    Q = float(v) * S_norm + (1.0 - float(v)) * R_norm

    order = np.argsort(Q)  # 越小越好
    rank = np.empty_like(order)
    rank[order] = np.arange(1, m + 1)

    return {
        "S": S,
        "R": R,
        "Q": Q,
        "order": order,
        "rank": rank,
        "weights": w,
        "f_star": f_star,
        "f_minus": f_minus,
        "distance": d,
        "v": float(v),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：VIKOR 排序。

    Args:
        data: 决策矩阵或 dict：
            - 直接传入 X
            - dict: {'X': X}
        params: 参数：
            - is_benefit: list[bool] | None
            - v: float（默认 0.5）
            - weights: list[float] | None
            - weights_method: {'equal','entropy','critic'}（weights 为空时生效，默认 'equal'）

    Returns:
        dict: 见 vikor() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X")
    else:
        X = data
    if X is None:
        raise ValueError("data 需要提供决策矩阵 X。")

    is_benefit = params.get("is_benefit")
    weights = params.get("weights")
    if weights is None:
        wm = str(params.get("weights_method", "equal")).lower()
        if wm == "entropy":
            w, _ = entropy_weight(X, is_benefit=is_benefit)
            weights = w
        elif wm == "critic":
            w, _ = critic_weight(X, is_benefit=is_benefit)
            weights = w
        elif wm == "equal":
            weights = None
        else:
            raise ValueError("weights_method 必须为 equal/entropy/critic 之一。")

    return vikor(X, weights=weights, is_benefit=is_benefit, v=float(params.get("v", 0.5)))


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
    out = solve(X, {"is_benefit": [True, False, True, True], "weights_method": "critic", "v": 0.5})
    print("weights =", np.round(out["weights"], 4))
    print("Q =", np.round(out["Q"], 4))
    print("rank =", out["rank"])

