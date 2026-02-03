# -*- coding: utf-8 -*-
# 马尔科夫链：由历史状态序列估计转移矩阵，并进行多步预测
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../预测与预报类题型参考代码.../马尔科夫链法预测股票.rar

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Hashable, List, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def fit_transition_matrix(
    states: Sequence[Hashable],
    *,
    smoothing: float = 0.0,
) -> Dict[str, Any]:
    """
    由观测状态序列估计转移概率矩阵 P。

    Args:
        states: 状态序列（长度 T>=2），元素可为 int/str 等可哈希对象。
        smoothing: 拉普拉斯平滑（>=0），例如 1e-6，可避免 0 概率。

    Returns:
        dict:
            - P: 转移矩阵 (K×K)，P[i,j]=Pr(s_{t+1}=j | s_t=i)
            - state_to_idx / idx_to_state: 映射
            - counts: 转移计数矩阵 (K×K)
    """
    if len(states) < 2:
        raise ValueError("states 长度必须 >= 2。")
    if float(smoothing) < 0:
        raise ValueError("smoothing 必须 >= 0。")

    uniq = list(dict.fromkeys(states))  # 保持出现顺序
    K = len(uniq)
    state_to_idx = {s: i for i, s in enumerate(uniq)}
    idx_to_state = {i: s for s, i in state_to_idx.items()}

    counts = np.zeros((K, K), dtype=float)
    for a, b in zip(states[:-1], states[1:]):
        i = state_to_idx[a]
        j = state_to_idx[b]
        counts[i, j] += 1.0

    counts_sm = counts + float(smoothing)
    row_sum = counts_sm.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    P = counts_sm / row_sum

    return {"P": P, "counts": counts, "state_to_idx": state_to_idx, "idx_to_state": idx_to_state}


def predict_distribution(
    P: np.ndarray,
    *,
    current: Union[int, np.ndarray],
    n_steps: int = 1,
) -> np.ndarray:
    """
    给定转移矩阵，预测 n_steps 之后的状态分布。

    Args:
        P: (K×K) 转移矩阵（行随机）。
        current: 当前状态：
            - int：当前处于某一离散状态 idx
            - ndarray shape=(K,)：当前分布向量（和为 1）
        n_steps: 预测步数（>=1）

    Returns:
        ndarray shape=(K,)：n_steps 之后的分布。
    """
    P = np.asarray(P, dtype=float)
    if P.ndim != 2 or P.shape[0] != P.shape[1]:
        raise ValueError("P 必须为方阵。")
    K = P.shape[0]
    n_steps = int(n_steps)
    if n_steps < 1:
        raise ValueError("n_steps 必须 >= 1。")

    if isinstance(current, (int, np.integer)):
        dist = np.zeros(K, dtype=float)
        dist[int(current)] = 1.0
    else:
        dist = np.asarray(current, dtype=float).reshape(-1)
        if dist.shape != (K,):
            raise ValueError("current 分布向量维度必须为 (K,)。")
        s = dist.sum()
        if s <= 0:
            raise ValueError("current 分布向量之和必须 > 0。")
        dist = dist / s

    # 多步：dist * P^n
    Pn = np.linalg.matrix_power(P, n_steps)
    return dist @ Pn


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：拟合转移矩阵并做多步预测。

    Args:
        data: 状态序列或 dict：
            - 直接传入 states
            - dict: {'states': states}
        params: 参数：
            - smoothing: float（默认 0）
            - n_steps: int（默认 1）

    Returns:
        dict:
            - P, counts, mapping...
            - next_dist: n_steps 后的分布（以“最后一个观测状态”为 current）
            - next_state: 概率最大的预测状态（原始标签）
    """
    params = params or {}
    if isinstance(data, dict):
        states = data.get("states")
    else:
        states = data
    if states is None:
        raise ValueError("data 需要提供状态序列 states。")

    fit = fit_transition_matrix(states, smoothing=float(params.get("smoothing", 0.0)))
    P = fit["P"]

    last = states[-1]
    last_idx = fit["state_to_idx"][last]
    n_steps = int(params.get("n_steps", 1))
    dist = predict_distribution(P, current=last_idx, n_steps=n_steps)
    next_idx = int(np.argmax(dist))
    next_state = fit["idx_to_state"][next_idx]

    return {**fit, "next_dist": dist, "next_state": next_state, "n_steps": n_steps, "current_state": last}


if __name__ == "__main__":
    # Mock Data：简单三状态序列（上涨/震荡/下跌）
    states = ["up", "up", "flat", "down", "down", "flat", "up", "up", "down", "flat", "flat", "up"]
    out = solve(states, {"smoothing": 1e-6, "n_steps": 2})
    print("P =\\n", np.round(out["P"], 3))
    print("current =", out["current_state"])
    print("next_dist (2-step) =", np.round(out["next_dist"], 3))
    print("pred_state =", out["next_state"])

