# -*- coding: utf-8 -*-
# 指标统计：把轨迹 y(t) 压缩成论文可用的风险/水平指标
#
# 目前输出（Model-0）：
# - mean/min/CV：宿主 H 与七鳃鳗总量 N
# - hit_H_safe / hit_N_q：是否跌破阈值（用于统计 P_host / P_ext）
#
# 补充（对应赛题 Q3“稳定性/韧性”）：
# - 恢复时间 T_rec：从一次“最坏低谷”回升到目标水平所需时间（可选 hold 期避免瞬时越界）

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Metrics:
    mean_H: float
    min_H: float
    cv_H: float
    mean_N: float
    min_N: float
    cv_N: float
    hit_H_safe: int
    hit_N_q: int


def _cv(x: np.ndarray) -> float:
    m = float(np.mean(x))
    if m == 0.0:
        return 0.0
    return float(np.std(x) / abs(m))


def geometric_mean_timeweighted(
    t: np.ndarray,
    s: np.ndarray,
    *,
    burn_in_years: int = 0,
    eps: float = 1e-12,
) -> float:
    """时间加权的几何平均（exp( time-average(log(s)) )）。

    说明：
    - 在随机环境/乘法过程语境下，几何平均比算术平均更能反映长期“典型水平”（bet-hedging 的核心）。
    - 为避免 s=0 导致 log 发散，使用一个极小 eps 做数值保护。
    - 默认在 burn-in 之后统计，避免初值对长期水平的影响。
    """
    t = np.asarray(t, dtype=float)
    s = np.asarray(s, dtype=float)
    if t.ndim != 1 or s.ndim != 1 or t.shape != s.shape:
        raise ValueError("t 与 s 需要是一维且等长。")
    if t.size < 2:
        return float("nan")

    if burn_in_years > 0:
        mask = t >= float(burn_in_years)
        if np.any(mask):
            t = t[mask]
            s = s[mask]

    if t.size < 2:
        return float("nan")

    s_safe = np.maximum(s, 0.0) + float(eps)
    log_s = np.log(s_safe)

    dt = np.diff(t)
    log_mid = 0.5 * (log_s[:-1] + log_s[1:])
    T = float(np.sum(dt))
    if T <= 0.0:
        return float("nan")
    return float(np.exp(np.sum(log_mid * dt) / T))


def recovery_time_from_min(
    t: np.ndarray,
    s: np.ndarray,
    *,
    target: float,
    burn_in_years: int = 0,
    hold_years: float = 1.0,
) -> float:
    """从“最低谷”恢复到目标水平的时间（年）。

    定义：
    - 在 burn-in 之后，取 s(t) 的最小值发生时刻 t_min
    - 计算最早的 t>=t_min，使得在 [t, t+hold_years] 内 s 都 >= target
    - 恢复时间 T_rec = t - t_min；若到仿真结束仍未满足，返回 +inf

    说明：
    - 这是“经验韧性指标”，适合在随机环境下做策略对照（配对对照时噪声较小）。
    - hold_years 用于避免“刚越过阈值马上又跌回去”的伪恢复（默认 1 年）。
    """
    t = np.asarray(t, dtype=float)
    s = np.asarray(s, dtype=float)
    if t.ndim != 1 or s.ndim != 1 or t.shape != s.shape:
        raise ValueError("t 与 s 需要是一维且等长。")
    if t.size < 2:
        return float("inf")

    # burn-in 截断（若 burn-in 太大，退化为全程）
    if burn_in_years > 0:
        mask = t >= float(burn_in_years)
        if np.any(mask):
            t = t[mask]
            s = s[mask]

    if t.size < 2:
        return float("inf")

    target = float(target)
    hold_years = float(hold_years)
    if hold_years < 0:
        raise ValueError("hold_years 不能为负。")

    i0 = int(np.nanargmin(s))
    t0 = float(t[i0])

    above = s >= target
    if hold_years == 0.0:
        # 只需第一次超过即可
        idx = np.where(above[i0:])[0]
        return float("inf") if idx.size == 0 else float(t[i0 + int(idx[0])] - t0)

    # 逐点扫描：找到第一个“连续 hold_years 都在 target 之上”的起点
    for i in range(i0, t.size):
        if not bool(above[i]):
            continue
        t_need = t[i] + hold_years
        # j 为第一个 t[j] >= t_need 的索引（若不存在则无法满足 hold）
        j = int(np.searchsorted(t, t_need, side="left"))
        if j >= t.size:
            break
        if bool(np.all(above[i : j + 1])):
            return float(t[i] - t0)

    return float("inf")


def compute_metrics(
    t: np.ndarray,
    y: np.ndarray,
    *,
    H_safe: float,
    N_q: float,
    burn_in_years: int = 0,
) -> Metrics:
    """从一条轨迹计算汇总指标。

    参数：
      burn_in_years>0 时：
        - mean/CV 只在 burn-in 之后统计（避免初值影响）
        - min 与阈值命中仍使用全时间范围（风险指标应“看全程”）
    """
    if y.ndim != 2 or y.shape[1] < 5:
        raise ValueError("y must be (n_points, n_states>=5)")

    H = y[:, 0]
    N = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]

    min_H = float(np.min(H))
    min_N = float(np.min(N))

    hit_H = int(min_H < H_safe)
    hit_N = int(min_N < N_q)

    if burn_in_years > 0:
        # 时间轴按“年”计，直接用 t>=burn_in_years 截断即可
        t_cut = float(burn_in_years)
        mask = t >= t_cut
        H_stat = H[mask]
        N_stat = N[mask]
    else:
        H_stat = H
        N_stat = N

    return Metrics(
        mean_H=float(np.mean(H_stat)),
        min_H=min_H,
        cv_H=_cv(H_stat),
        mean_N=float(np.mean(N_stat)),
        min_N=min_N,
        cv_N=_cv(N_stat),
        hit_H_safe=hit_H,
        hit_N_q=hit_N,
    )
