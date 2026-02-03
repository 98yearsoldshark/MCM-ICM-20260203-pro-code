# -*- coding: utf-8 -*-
# 灰色马尔科夫（Grey-Markov）：GM(1,1) + 马尔科夫状态修正（简化实现）
#
# 思路：
# 1) 先用 GM(1,1) 得到样本内拟合 x_hat
# 2) 用“修正系数” c_k = x(k)/x_hat(k) 构造状态序列（分箱离散化）
# 3) 估计转移矩阵 P，并用 E[c] 对未来灰色预测进行乘法修正
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../预测与预报类题型参考代码.../改进灰色马尔科夫模型...

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.c11_预测预报_Forecasting.grey_gm11 import gm11_fit, gm11_predict  # noqa: E402


def _digitize(values: np.ndarray, bins: np.ndarray) -> np.ndarray:
    # 返回 0..K-1 的状态编号
    idx = np.digitize(values, bins[1:-1], right=False)
    return idx.astype(int)


def grey_markov_forecast(
    x0: Union[np.ndarray, list],
    *,
    horizon: int = 1,
    alpha: float = 0.5,
    n_states: int = 3,
    bins: Optional[Sequence[float]] = None,
    smoothing: float = 1e-6,
) -> Dict[str, Any]:
    """
    灰色马尔科夫预测（简化版）。

    Args:
        x0: 原始序列（n,）。
        horizon: 预测步数。
        alpha: GM(1,1) 背景值系数。
        n_states: 状态数（当 bins=None 时生效）。
        bins: 自定义分箱边界（长度 K+1），包含两端；若提供，则 n_states=K。
            例如 bins=[0.8,0.95,1.05,1.2] 表示 3 个状态。
        smoothing: 转移矩阵平滑项，避免 0 概率。

    Returns:
        dict:
            - gm: GM(1,1) 输出（含 x0_hat）
            - correction_factors: c_k（n,）
            - state_seq: 状态序列（从第 2 个点开始更有意义）
            - P: 转移矩阵（K×K）
            - state_repr: 每个状态的代表修正系数（K,，用该状态样本均值）
            - corrected_forecast: 修正后的未来预测（h,）
            - grey_forecast: 未修正的未来预测（h,）
    """
    x0_arr = np.asarray(x0, dtype=float).reshape(-1)
    n = x0_arr.size
    if n < 4:
        raise ValueError("灰色马尔科夫建议 n>=4。")
    h = int(horizon)
    if h < 1:
        raise ValueError("horizon 必须 >= 1。")

    fit = gm11_fit(x0_arr, alpha=float(alpha))
    gm = {**fit, **gm11_predict(fit, horizon=h)}

    x0_hat = np.asarray(gm["x0_hat"], dtype=float)
    # 样本内修正系数：c_k = x(k) / x_hat(k)
    denom = np.where(np.abs(x0_hat[:n]) < 1e-12, 1.0, x0_hat[:n])
    c = x0_arr / denom

    # 分箱得到状态
    if bins is not None:
        bins_arr = np.asarray(list(bins), dtype=float).reshape(-1)
        if bins_arr.size < 3:
            raise ValueError("bins 至少需要 3 个边界点（>=2 个状态）。")
        if not np.all(np.diff(bins_arr) > 0):
            raise ValueError("bins 必须严格递增。")
    else:
        K = int(n_states)
        if K < 2:
            raise ValueError("n_states 必须 >= 2。")
        # 用分位数构造边界；两端取 min/max
        qs = np.linspace(0, 1, K + 1)
        bins_arr = np.quantile(c[1:], qs)  # 从第 2 个点开始
        bins_arr[0] = float(np.min(c[1:]))
        bins_arr[-1] = float(np.max(c[1:]))
        # 若全相等会导致重复边界
        if not np.all(np.diff(bins_arr) > 0):
            # 退化处理：加一点极小扰动
            bins_arr = bins_arr + np.linspace(0, 1e-6, bins_arr.size)

    state_seq = _digitize(c, bins_arr)
    K = int(np.max(state_seq)) + 1

    # 转移计数（使用 c 的状态序列）
    counts = np.zeros((K, K), dtype=float)
    for a, b in zip(state_seq[:-1], state_seq[1:]):
        counts[int(a), int(b)] += 1.0
    counts_sm = counts + float(smoothing)
    row_sum = counts_sm.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    P = counts_sm / row_sum

    # 状态代表值：该状态样本的 c 的均值
    state_repr = np.zeros(K, dtype=float)
    for s in range(K):
        mask = state_seq[1:] == s  # 仍从第 2 个点开始统计更合理
        if np.any(mask):
            state_repr[s] = float(np.mean(c[1:][mask]))
        else:
            state_repr[s] = 1.0

    # 未来预测修正
    grey_future = x0_hat[n : n + h]
    corrected = np.zeros(h, dtype=float)

    cur_state = int(state_seq[-1])
    for t in range(h):
        dist = P[cur_state, :]
        expected_c = float(dist @ state_repr)
        corrected[t] = float(grey_future[t] * expected_c)
        # 迭代更新状态：取最大概率状态（确定性版本）
        cur_state = int(np.argmax(dist))

    return {
        "gm": gm,
        "correction_factors": c,
        "bins": bins_arr,
        "state_seq": state_seq,
        "P": P,
        "state_repr": state_repr,
        "grey_forecast": grey_future,
        "corrected_forecast": corrected,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：灰色马尔科夫预测。

    Args:
        data: 序列或 dict：
            - 直接传入 x0
            - dict: {'x0': x0}
        params: 参数：
            - horizon: int（默认 1）
            - alpha: float（默认 0.5）
            - n_states: int（默认 3）
            - bins: list[float] | None
            - smoothing: float（默认 1e-6）

    Returns:
        dict: 见 grey_markov_forecast() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        x0 = data.get("x0")
    else:
        x0 = data
    if x0 is None:
        raise ValueError("data 需要提供序列 x0。")

    return grey_markov_forecast(
        x0,
        horizon=int(params.get("horizon", 1)),
        alpha=float(params.get("alpha", 0.5)),
        n_states=int(params.get("n_states", 3)),
        bins=params.get("bins"),
        smoothing=float(params.get("smoothing", 1e-6)),
    )


if __name__ == "__main__":
    x0 = [120, 132, 145, 160, 178, 195]
    out = solve(x0, {"horizon": 3, "n_states": 3})
    print("grey_future =", np.round(out["grey_forecast"], 3))
    print("corrected   =", np.round(out["corrected_forecast"], 3))
    print("P =\\n", np.round(out["P"], 3))

