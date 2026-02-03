# -*- coding: utf-8 -*-
# 灰色关联分析（Grey Relational Analysis, GRA）：衡量序列/方案与参考序列的相似程度
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../相关性分析类题型参考代码.../灰色关联分析（matlab）.zip

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_2d(x: Any) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    if a.ndim != 2:
        raise ValueError("data 必须为二维矩阵（m×n）。")
    return a


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
    if method in {"initial", "init"}:
        base = x[:, [0]]
        base[base == 0] = 1.0
        return x / base
    if method in {"none", ""}:
        return x
    raise ValueError("normalize_method 必须为 minmax/zscore/initial/none 之一。")


def grey_relational_analysis(
    data: Union[np.ndarray, list],
    *,
    ref: Optional[Sequence[float]] = None,
    rho: float = 0.5,
    normalize_method: str = "minmax",
) -> Dict[str, Any]:
    """
    灰色关联分析（GRA）。

    Args:
        data: 数据矩阵 X（m×n），m 个方案/序列，n 个指标/时刻。
        ref: 参考序列（n,）。若为 None，则取“理想最优”参考：每列最大值。
        rho: 分辨系数 ρ（0<ρ<=1），常用 0.5。
        normalize_method: 归一化方法（默认 minmax）。

    Returns:
        dict:
            - ref: 参考序列（n,）
            - coeff: 关联系数矩阵 ξ（m×n）
            - grade: 关联度 γ（m,），为每行系数均值
            - order: 降序排序索引（m,）
            - rank: 名次（m,，从 1 开始）
    """
    X = _to_2d(data)
    if not (0 < float(rho) <= 1.0):
        raise ValueError("rho 必须在 (0,1]。")

    Z = _normalize(X, method=normalize_method)
    if ref is None:
        ref_arr = np.max(Z, axis=0)
    else:
        ref_arr = np.asarray(list(ref), dtype=float).reshape(-1)
        if ref_arr.shape != (Z.shape[1],):
            raise ValueError("ref 的长度必须等于列数 n。")

    # 绝对差
    delta = np.abs(Z - ref_arr[None, :])
    dmin = float(np.min(delta))
    dmax = float(np.max(delta))
    denom = delta + float(rho) * dmax
    denom[denom == 0] = 1e-12

    coeff = (dmin + float(rho) * dmax) / denom
    grade = np.mean(coeff, axis=1)

    order = np.argsort(-grade)
    rank = np.empty_like(order)
    rank[order] = np.arange(1, len(grade) + 1)

    return {"ref": ref_arr, "coeff": coeff, "grade": grade, "order": order, "rank": rank, "normalized": Z}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：灰色关联分析。

    Args:
        data: 矩阵（m×n）或 dict：
            - 直接传入 matrix
            - dict: {'X': matrix}
        params: 参数：
            - ref: list[float] | None
            - rho: float（默认 0.5）
            - normalize_method: str（默认 'minmax'）

    Returns:
        dict: 见 grey_relational_analysis()。
    """
    params = params or {}
    if isinstance(data, dict):
        X = data.get("X")
    else:
        X = data
    if X is None:
        raise ValueError("data 需要提供矩阵 X。")
    return grey_relational_analysis(
        X,
        ref=params.get("ref"),
        rho=float(params.get("rho", 0.5)),
        normalize_method=str(params.get("normalize_method", "minmax")),
    )


if __name__ == "__main__":
    # Mock Data：5 个方案、4 个指标
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
    out = solve(X, {"rho": 0.5, "normalize_method": "minmax"})
    print("grade =", np.round(out["grade"], 4))
    print("rank  =", out["rank"])
    print("best idx (0-based) =", int(out["order"][0]))

