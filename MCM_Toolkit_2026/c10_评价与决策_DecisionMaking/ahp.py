# -*- coding: utf-8 -*-
# 层次分析法（AHP）：由两两比较矩阵求权重，并进行一致性检验
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../评价与决策类题型参考代码.../层次分析法评价.rar

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# Saaty 随机一致性指标 RI（n=1..15 常用）
_RI_TABLE = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.48,
    13: 1.56,
    14: 1.57,
    15: 1.59,
}


def _check_pairwise_matrix(a: np.ndarray, *, atol: float = 1e-8) -> None:
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("两两比较矩阵必须为方阵。")
    if a.shape[0] < 1:
        raise ValueError("矩阵维度必须 >= 1。")
    if np.any(a <= 0):
        raise ValueError("两两比较矩阵必须为正数。")
    # 允许用户不严格满足互反；若满足则可做更强的校验
    diag = np.diag(a)
    if not np.allclose(diag, 1.0, atol=atol):
        raise ValueError("两两比较矩阵对角线应为 1。")


def ahp_weights(
    pairwise_matrix: Union[np.ndarray, list],
    *,
    method: str = "eigen",
    atol: float = 1e-8,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    计算 AHP 权重并给出一致性检验指标。

    Args:
        pairwise_matrix: 两两比较矩阵 A（n×n），通常满足 a_ij = 1/a_ji, a_ii=1。
        method: 权重求解方法：
            - "eigen": 主特征向量法（默认）
            - "gm": 几何平均法（行几何均值归一化）
        atol: 数值校验容差。

    Returns:
        (weights, info)

        weights:
            shape=(n,) 的权重向量，和为 1。
        info:
            包含：
            - lambda_max: 最大特征值
            - ci: 一致性指标 CI
            - ri: 随机一致性指标 RI
            - cr: 一致性比例 CR（CI/RI）
    """
    a = np.asarray(pairwise_matrix, dtype=float)
    _check_pairwise_matrix(a, atol=atol)
    n = a.shape[0]

    method = str(method).lower()
    if method not in {"eigen", "gm"}:
        raise ValueError("method 必须为 'eigen' 或 'gm'。")

    if n == 1:
        w = np.array([1.0], dtype=float)
        return w, {"lambda_max": 1.0, "ci": 0.0, "ri": 0.0, "cr": 0.0}

    if method == "gm":
        # 行几何平均：w_i ∝ (Π_j a_ij)^(1/n)
        geom = np.prod(a, axis=1) ** (1.0 / n)
        w = geom / geom.sum()
        # 用 Aw / w 估计最大特征值（常用近似）
        aw = a @ w
        lambda_max = float(np.mean(aw / w))
    else:
        # 主特征向量（实部）
        vals, vecs = np.linalg.eig(a)
        idx = int(np.argmax(vals.real))
        lambda_max = float(vals.real[idx])
        v = vecs[:, idx].real
        v = np.abs(v)
        w = v / v.sum()

    ci = float((lambda_max - n) / (n - 1))
    ri = float(_RI_TABLE.get(n, 1.59))  # n>15 时用 15 的近似
    cr = float(ci / ri) if ri > 0 else 0.0

    return w, {"lambda_max": lambda_max, "ci": ci, "ri": ri, "cr": cr}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：AHP 求权重 + 一致性检验。

    Args:
        data: np.ndarray | list | dict，支持：
            - 直接传入 n×n 矩阵
            - dict: {'A': matrix}（或 'pairwise_matrix'）
        params: 参数：
            - method: 'eigen' | 'gm'
            - cr_threshold: float，一致性阈值（默认 0.10）

    Returns:
        dict:
            - weights: ndarray shape=(n,)
            - lambda_max/ci/ri/cr
            - is_consistent: bool（cr <= threshold）
    """
    params = params or {}
    if isinstance(data, dict):
        a = data.get("A", data.get("pairwise_matrix"))
    else:
        a = data
    if a is None:
        raise ValueError("data 需要提供两两比较矩阵 A。")

    w, info = ahp_weights(a, method=str(params.get("method", "eigen")))
    thr = float(params.get("cr_threshold", 0.10))
    return {
        "weights": w,
        **info,
        "is_consistent": bool(info["cr"] <= thr),
        "cr_threshold": thr,
    }


if __name__ == "__main__":
    # Mock Data：4 个指标的两两比较矩阵（示例）
    A = np.array(
        [
            [1, 1 / 3, 3, 5],
            [3, 1, 5, 7],
            [1 / 3, 1 / 5, 1, 3],
            [1 / 5, 1 / 7, 1 / 3, 1],
        ],
        dtype=float,
    )

    out = solve(A, {"method": "eigen", "cr_threshold": 0.10})
    print("weights =", np.round(out["weights"], 4))
    print("lambda_max =", out["lambda_max"])
    print("CI =", out["ci"], "RI =", out["ri"], "CR =", out["cr"])
    print("is_consistent =", out["is_consistent"])

