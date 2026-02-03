# -*- coding: utf-8 -*-
# 物元分析法（Matter-Element / Extension Evaluation）多指标评价
#
# 参考来源（资料目录，Matlab 版：wuyuanpingjia.m）：
# - 6、按赛题类别划分的常用算法代码/.../评价与决策类题型参考代码.../物元分析法多指标评价模型（matlab）.zip
#
# 说明：
# - 该方法通常用于“把对象按等级/类别进行评价”（例如：优/良/中/差 或 1~m 级）
# - 输入需要给出每个指标在各等级下的“经典域区间” [a(i,j), b(i,j)]
# - 节域（node domain）默认取各等级经典域的整体 min/max
# - 公式尽量复刻资料 Matlab 版（并扩展为可批量评价多个对象）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _as_2d_float(X: Any) -> np.ndarray:
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(1, -1)
    if arr.ndim != 2:
        raise ValueError("X 必须为 1D 或 2D 数组。")
    return arr


def _parse_classical_domains(R0: Any) -> Tuple[np.ndarray, np.ndarray]:
    """
    解析经典域上下限。

    支持两种形状：
    - (n_indicators, 2*m)：[a1,b1,a2,b2,...]
    - (n_indicators, m, 2)：[..., (a,b)]
    """
    R0 = np.asarray(R0, dtype=float)
    if R0.ndim == 2 and (R0.shape[1] % 2 == 0):
        a = R0[:, 0::2]
        b = R0[:, 1::2]
        return a, b
    if R0.ndim == 3 and R0.shape[2] == 2:
        a = R0[:, :, 0]
        b = R0[:, :, 1]
        return a, b
    raise ValueError("classical_domains 的形状必须为 (n,2m) 或 (n,m,2)。")


def _correlation_single_indicator(x: float, a: float, b: float, ap: float, bp: float) -> float:
    """
    单指标-单等级的关联函数（复刻资料版 wuyuanpingjia.m）。

    其中：
    - [a,b]：经典域区间（某等级）
    - [ap,bp]：节域区间（总体范围）
    """
    # 防止节域宽度为 0
    if ap == bp:
        return 0.0

    if a == b:
        if x == a:
            return 0.0
        pp = abs(x - 0.5 * (ap + bp)) - 0.5 * (bp - ap)
        den = pp - abs(x - a)
        if den == 0:
            return float("inf") if abs(x - a) > 0 else 0.0
        return abs(x - a) / den

    # a != b
    p = abs(x - 0.5 * (a + b)) - 0.5 * (b - a)
    if (x >= a) and (x <= b):
        # x 在经典域内：p <= 0，此处 k >= 0
        width = abs(b - a)
        if width == 0:
            return 0.0
        return -p / width

    # x 在经典域外
    pp = abs(x - 0.5 * (ap + bp)) - 0.5 * (bp - ap)
    den = pp - p
    if den == 0:
        return float("inf") if p != 0 else 0.0
    return p / den


def matter_element_evaluate(
    X: Any,
    classical_domains: Any,
    weights: Optional[Sequence[float]] = None,
    *,
    node_domains: Optional[Sequence[Tuple[float, float]]] = None,
    grade_names: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    物元分析法多指标评价（批量）。

    Args:
        X: (n_obj, n_indicators) 待评价对象的指标矩阵。
        classical_domains: 经典域区间：
            - (n_indicators, 2*m) 或 (n_indicators, m, 2)
        weights: 指标权重 w（长度 n_indicators）。若 None 则默认等权。
        node_domains: 节域区间 (n_indicators,2)。若 None 则取各等级经典域的整体 min/max。
        grade_names: 等级名称（长度 m）。若 None 则用 "G1..Gm"。

    Returns:
        dict:
            - k: (n_obj, n_indicators, m) 各指标关于各等级的关联度
            - kp: (n_obj, m) 加权组合关联度（w*k）
            - grade_index: (n_obj,) 0-based 最优等级下标（kp 最大）
            - grade_index_1based: (n_obj,) 1-based 等级编号
            - grade: list[str] 最优等级名称
            - j_star: (n_obj,) 级别变量特征值（资料版 j*）
    """
    X2 = _as_2d_float(X)
    a, b = _parse_classical_domains(classical_domains)
    n_ind, m = a.shape
    if X2.shape[1] != n_ind:
        raise ValueError("X 的列数必须等于指标个数 n_indicators。")

    if weights is None:
        w = np.ones(n_ind, dtype=float) / float(n_ind)
    else:
        w = np.asarray(list(weights), dtype=float).reshape(-1)
        if w.size != n_ind:
            raise ValueError("weights 长度必须等于指标个数。")
        s = float(np.sum(w))
        if s <= 0:
            raise ValueError("weights 之和必须为正。")
        w = w / s

    if node_domains is None:
        ap = np.min(np.stack([a, b], axis=2), axis=(1, 2))
        bp = np.max(np.stack([a, b], axis=2), axis=(1, 2))
    else:
        nd = np.asarray(list(node_domains), dtype=float)
        if nd.shape != (n_ind, 2):
            raise ValueError("node_domains 必须为 (n_indicators,2)。")
        ap = nd[:, 0]
        bp = nd[:, 1]

    grade_names_use: List[str]
    if grade_names is None:
        grade_names_use = [f"G{i+1}" for i in range(m)]
    else:
        grade_names_use = list(grade_names)
        if len(grade_names_use) != m:
            raise ValueError("grade_names 长度必须等于等级数 m。")

    n_obj = int(X2.shape[0])
    k = np.zeros((n_obj, n_ind, m), dtype=float)
    for i in range(n_obj):
        for ii in range(n_ind):
            x = float(X2[i, ii])
            for j in range(m):
                k[i, ii, j] = _correlation_single_indicator(x, float(a[ii, j]), float(b[ii, j]), float(ap[ii]), float(bp[ii]))

    # kp = w * k（对指标维度加权求和）
    kp = np.tensordot(k, w, axes=([1], [0]))  # (n_obj, m)

    grade_index = np.argmax(kp, axis=1).astype(int)
    grade = [grade_names_use[int(j)] for j in grade_index]

    # 级别变量特征值 j*（资料版：对 kp 做线性归一化后加权平均等级编号）
    j_star = np.zeros(n_obj, dtype=float)
    for i in range(n_obj):
        kp_i = kp[i]
        kp_min = float(np.min(kp_i))
        kp_max = float(np.max(kp_i))
        if kp_max == kp_min:
            j_star[i] = float(grade_index[i] + 1)
            continue
        av = (kp_i - kp_min) / (kp_max - kp_min)
        num = float(np.sum((np.arange(1, m + 1, dtype=float)) * av))
        den = float(np.sum(av))
        j_star[i] = num / (den + 1e-12)

    return {
        "k": k,
        "kp": kp,
        "grade_index": grade_index,
        "grade_index_1based": grade_index + 1,
        "grade": grade,
        "j_star": j_star,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：物元分析法多指标评价。

    Args:
        data: dict，包含：
            - X: (n_obj, n_indicators)
            - classical_domains: (n_indicators,2*m) 或 (n_indicators,m,2)
            可选：
            - weights: (n_indicators,)
            - node_domains: (n_indicators,2)
            - grade_names: list[str]
        params: 预留（当前未使用）

    Returns:
        dict: matter_element_evaluate() 的返回值
    """
    _ = params or {}
    if not isinstance(data, dict) or "X" not in data or "classical_domains" not in data:
        raise TypeError("data 必须为 dict，且包含 X 与 classical_domains。")
    return matter_element_evaluate(
        data["X"],
        data["classical_domains"],
        weights=data.get("weights"),
        node_domains=data.get("node_domains"),
        grade_names=data.get("grade_names"),
    )


if __name__ == "__main__":
    # Mock Data：3 个对象，4 个指标，3 个等级（G1~G3）
    # 经典域：每个指标在每个等级的取值区间（假设已统一为“增序/越大越好”的指标方向）
    classical = np.array(
        [
            [[0, 3], [3, 6], [6, 10]],
            [[0, 2], [2, 5], [5, 10]],
            [[0, 4], [4, 7], [7, 10]],
            [[0, 1], [1, 3], [3, 5]],
        ],
        dtype=float,
    )  # (n_ind=4, m=3, 2)
    X = np.array([[2.0, 4.0, 8.0, 0.8], [7.0, 6.0, 6.5, 2.0], [9.0, 9.5, 9.0, 4.2]], dtype=float)
    w = [0.3, 0.2, 0.3, 0.2]
    out = solve({"X": X, "classical_domains": classical, "weights": w, "grade_names": ["差", "中", "好"]})
    print("grade =", out["grade"])
    print("j_star =", np.round(out["j_star"], 4).tolist())

