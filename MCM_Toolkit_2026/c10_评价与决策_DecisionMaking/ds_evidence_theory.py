# -*- coding: utf-8 -*-
# Dempster-Shafer 证据理论（DS）：多源信息融合（简化：单元素 + 全集 Θ）
#
# 适用场景：
# - 多个模型/专家给出对若干类别/方案的“支持度”，需要融合成一个更稳健的结论
#
# 这里实现的简化版假设：
# - 仅对单元素集合 {i} 分配质量 m(i)，以及对全集 Θ 分配质量 m(Θ)
# - 不处理一般子集（例如 {A,B}）的质量分配（那会更复杂）
#
# Dempster 组合规则（两条证据 m1,m2）：
# - 冲突系数 K = Σ_{i≠j} m1(i)*m2(j)
# - 组合后：
#   m(i) = [m1(i)m2(i) + m1(i)m2(Θ) + m1(Θ)m2(i)] / (1-K)
#   m(Θ) = [m1(Θ)m2(Θ)] / (1-K)
#
# 同时提供 Pignistic 概率变换（BetP）：
#   BetP(i) = m(i) + m(Θ)/N
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../相关性分析类题型参考代码.../DS理论与灰色关联的结合matlab版.rar

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _normalize_mass(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=float).reshape(-1)
    if np.any(m < 0):
        raise ValueError("质量分配 m 不能为负。")
    s = float(m.sum())
    if s <= 0:
        raise ValueError("质量分配 m 之和必须 > 0。")
    return m / s


def ds_combine_two(m1: Union[np.ndarray, Sequence[float]], m2: Union[np.ndarray, Sequence[float]]) -> Dict[str, Any]:
    """
    组合两条证据（简化：单元素 + Θ）。

    Args:
        m1: (N+1,) 质量向量，最后一项为 m(Θ)。
        m2: (N+1,) 质量向量，最后一项为 m(Θ)。

    Returns:
        dict:
            - m: 组合后的质量向量 (N+1,)
            - conflict: 冲突系数 K
            - norm_factor: 归一化因子 1-K
    """
    a = _normalize_mass(np.asarray(m1, dtype=float))
    b = _normalize_mass(np.asarray(m2, dtype=float))
    if a.shape != b.shape:
        raise ValueError("m1 与 m2 形状必须一致。")
    if a.size < 2:
        raise ValueError("至少需要 1 个单元素 + Θ（长度>=2）。")

    N = a.size - 1
    a_theta = float(a[-1])
    b_theta = float(b[-1])
    a_s = a[:N]
    b_s = b[:N]

    # 冲突：不同单元素之间的乘积之和
    conflict = float(np.sum(a_s) * np.sum(b_s) - float(np.dot(a_s, b_s)))
    norm = 1.0 - conflict
    if norm <= 1e-12:
        # 极端冲突：无法归一化，返回“全不确定”
        m = np.zeros(N + 1, dtype=float)
        m[-1] = 1.0
        return {"m": m, "conflict": conflict, "norm_factor": norm}

    m_s = (a_s * b_s + a_s * b_theta + a_theta * b_s) / norm
    m_theta = (a_theta * b_theta) / norm
    m = np.concatenate([m_s, [m_theta]])
    return {"m": m, "conflict": conflict, "norm_factor": norm}


def ds_combine_many(masses: Union[np.ndarray, Sequence[Sequence[float]]]) -> Dict[str, Any]:
    """
    组合多条证据（逐步两两合并）。

    Args:
        masses: (T×(N+1))，T 条证据。

    Returns:
        dict:
            - m: 最终质量
            - conflicts: 每一步的冲突系数列表
    """
    M = np.asarray(masses, dtype=float)
    if M.ndim != 2:
        raise ValueError("masses 必须为二维数组 (T×(N+1))。")
    if M.shape[0] < 1:
        raise ValueError("至少需要 1 条证据。")

    cur = _normalize_mass(M[0])
    conflicts = []
    for i in range(1, M.shape[0]):
        out = ds_combine_two(cur, M[i])
        cur = out["m"]
        conflicts.append(float(out["conflict"]))
    return {"m": cur, "conflicts": np.asarray(conflicts, dtype=float)}


def pignistic_probability(m: Union[np.ndarray, Sequence[float]]) -> np.ndarray:
    """
    Pignistic 概率变换：BetP(i) = m(i) + m(Θ)/N。
    """
    m = _normalize_mass(np.asarray(m, dtype=float))
    N = m.size - 1
    if N < 1:
        raise ValueError("m 长度必须 >= 2。")
    return m[:N] + m[-1] / float(N)


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：DS 证据融合。

    Args:
        data: 支持两种输入：
            1) masses: (T×(N+1)) 的质量矩阵（最后一列为 Θ）
            2) probs: (T×N) 的“支持度/概率”矩阵，将自动补 Θ=1-sum(probs)
               - 若 probs 每行和>1，会先归一化到和=1，再将 Θ 置 0
        params: 参数：
            - input_type: {'masses','probs'}（可选；不填则自动判断）
            - theta_clip: bool（默认 True；Θ<0 时截断为 0）

    Returns:
        dict:
            - m: 最终质量 (N+1,)
            - betp: Pignistic 概率 (N,)
            - pred: 最大 BetP 的类别索引（0-based）
            - conflicts: 每一步冲突系数（若多条证据）
    """
    params = params or {}
    theta_clip = bool(params.get("theta_clip", True))

    if isinstance(data, dict):
        masses = data.get("masses")
        probs = data.get("probs")
        input_type = params.get("input_type")
        if input_type is None:
            input_type = "masses" if masses is not None else "probs"
    else:
        # 直接传入数组：默认视为 masses
        masses = data
        probs = None
        input_type = "masses"

    input_type = str(input_type).lower()

    if input_type == "masses":
        if masses is None:
            raise ValueError("input_type=masses 时需要提供 masses。")
        out = ds_combine_many(masses)
        m = out["m"]
        conflicts = out["conflicts"]
    elif input_type == "probs":
        if probs is None:
            raise ValueError("input_type=probs 时需要提供 probs。")
        P = np.asarray(probs, dtype=float)
        if P.ndim != 2:
            raise ValueError("probs 必须为二维数组 (T×N)。")
        row_sum = P.sum(axis=1, keepdims=True)
        # 若每行和>1，先归一化到 1
        mask = row_sum > 1.0 + 1e-12
        Pn = P.copy()
        Pn[mask[:, 0], :] = Pn[mask[:, 0], :] / row_sum[mask[:, 0], :]
        theta = 1.0 - Pn.sum(axis=1, keepdims=True)
        if theta_clip:
            theta = np.maximum(theta, 0.0)
        M = np.hstack([Pn, theta])
        out = ds_combine_many(M)
        m = out["m"]
        conflicts = out["conflicts"]
    else:
        raise ValueError("input_type 必须为 masses 或 probs。")

    betp = pignistic_probability(m)
    pred = int(np.argmax(betp))
    return {"m": m, "betp": betp, "pred": pred, "conflicts": conflicts}


if __name__ == "__main__":
    # Mock Data：3 类，2 条证据（每条给出 probs，自动补 Θ）
    probs = np.array(
        [
            [0.7, 0.2, 0.05],  # Θ=0.05
            [0.4, 0.5, 0.05],  # Θ=0.05
        ],
        dtype=float,
    )
    out = solve({"probs": probs}, {"input_type": "probs"})
    print("combined m =", np.round(out["m"], 4))
    print("betp =", np.round(out["betp"], 4), "pred =", out["pred"])

