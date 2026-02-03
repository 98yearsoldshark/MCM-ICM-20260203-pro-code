# -*- coding: utf-8 -*-
# 第三方受益者（B）模块：B_L（七鳃鳗相关寄生虫/病原）与 B_H（宿主鱼机会性寄生虫/病原）
#
# 用途：
# - 为 Model-1/2/3 提供可复用的参数与辅助函数（饱和函数、易感性函数等）
# - 提供“入侵指数/阈值”计算：只需在 B≈0 的线性区间用 Model-0 轨迹即可判断能否入侵
#
# 说明：
# - 这里默认把 B 建模为“感染压力/寄生者丰度”的无量纲量（建议范围 ~[0,1]），
#   用 logistic 自限项避免无界增长导致数值不稳定。

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _sat(x: float, K: float, eps: float = 1e-12) -> float:
    """通用饱和函数：x/(x+K)。

    - K>0：标准饱和，取值∈[0,1)
    - K<=0：退化为“阶跃式饱和”：x>0 则近似 1，否则 0
    """
    x = max(float(x), 0.0)
    K = float(K)
    if K <= 0:
        return 1.0 if x > 0 else 0.0
    return float(np.clip(x / (x + K + eps), 0.0, 1.0))


@dataclass(frozen=True)
class BLParams:
    """B_L：依赖七鳃鳗寄生期 J 的寄生虫/病原体参数。"""

    beta: float = 2.0  # 传播/增殖强度系数（乘在 f_J(J) 上）
    d: float = 0.7  # 自然衰亡率
    K_J: float = 0.1  # f_J(J)=J/(J+K_J) 的半饱和常数

    # B_L 对七鳃鳗的反作用：额外死亡（或等效降低转化）
    delta_J: float = 0.4  # 对 J 的额外死亡强度系数
    K_BJ: float = 0.3  # g(B)=B/(B+K_BJ) 的半饱和常数

    # 数值稳定：B_L 的自限（logistic）携带量；<=0 表示不启用自限
    K_cap: float = 1.0


@dataclass(frozen=True)
class BHParams:
    """B_H：依赖“宿主受损/易感性” W(H,J) 的机会性寄生虫/病原体参数。"""

    beta: float = 1.5  # 增殖强度系数（乘在 W(H,J) 上）
    d: float = 0.7  # 自然衰亡率
    K_W: float = 0.05  # W(H,J) 的半饱和常数（用在 H*J 上）

    # B_H 对宿主的反作用：额外死亡
    delta_H: float = 0.3  # 对 H 的额外死亡强度系数
    K_BH: float = 0.3  # q(B)=B/(B+K_BH) 的半饱和常数

    # 数值稳定：B_H 的自限（logistic）携带量；<=0 表示不启用自限
    K_cap: float = 1.0


def f_J(J: float, K_J: float) -> float:
    """传播链函数：七鳃鳗寄生期越多，B_L 的增长越快（饱和）。"""
    return _sat(J, K_J)


def g_B(B: float, K_B: float) -> float:
    """B 对宿主/七鳃鳗的影响强度（饱和）。"""
    return _sat(B, K_B)


def W_HJ(H: float, J: float, K_W: float) -> float:
    """宿主易感性/受损指标 W(H,J)∈[0,1]（随接触强度 H*J 饱和）。"""
    return _sat(max(float(H), 0.0) * max(float(J), 0.0), K_W)


def invasion_exponent_BL(
    t: np.ndarray,
    y: np.ndarray,
    *,
    params: BLParams,
    burn_in_years: int = 0,
) -> float:
    """入侵指数（Lyapunov 指数近似）：B_L 很稀少时的平均指数增长率 λ。

    在线性区间（B≈0）：
      dB/dt ≈ (beta * f_J(J(t)) - d) * B
    因此：
      λ ≈ (1/T) ∫ (beta * f_J(J(t)) - d) dt

    返回：
      λ（单位：1/年）。λ>0 表示可入侵；λ<0 表示不可入侵。
    """
    if y.ndim != 2 or y.shape[1] < 3:
        raise ValueError("y 需要是 (n_points, n_states>=3)，且包含 J 在第 3 列（index=2）。")

    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or len(t) != y.shape[0]:
        raise ValueError("t 与 y 的长度不一致。")
    if len(t) < 2:
        return float("nan")

    if burn_in_years > 0:
        mask = t >= float(burn_in_years)
        t = t[mask]
        y = y[mask]
        if len(t) < 2:
            return float("nan")

    J = y[:, 2]
    g = params.beta * np.array([f_J(float(j), params.K_J) for j in J], dtype=float) - params.d

    # 时间加权平均（梯形积分 / 总时长）
    dt = np.diff(t)
    g_mid = 0.5 * (g[:-1] + g[1:])
    T = float(np.sum(dt))
    if T <= 0:
        return float("nan")
    return float(np.sum(g_mid * dt) / T)


def invasion_exponent_BH(
    t: np.ndarray,
    y: np.ndarray,
    *,
    params: BHParams,
    burn_in_years: int = 0,
) -> float:
    """入侵指数：B_H 很稀少时的平均指数增长率 λ（同 invasion_exponent_BL）。"""
    if y.ndim != 2 or y.shape[1] < 3:
        raise ValueError("y 需要是 (n_points, n_states>=3)，且包含 H/J 在第 1/3 列（index=0/2）。")

    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or len(t) != y.shape[0]:
        raise ValueError("t 与 y 的长度不一致。")
    if len(t) < 2:
        return float("nan")

    if burn_in_years > 0:
        mask = t >= float(burn_in_years)
        t = t[mask]
        y = y[mask]
        if len(t) < 2:
            return float("nan")

    H = y[:, 0]
    J = y[:, 2]
    W = np.array([W_HJ(float(h), float(j), params.K_W) for h, j in zip(H, J)], dtype=float)
    g = params.beta * W - params.d

    dt = np.diff(t)
    g_mid = 0.5 * (g[:-1] + g[1:])
    T = float(np.sum(dt))
    if T <= 0:
        return float("nan")
    return float(np.sum(g_mid * dt) / T)


def R0_BL_from_equilibrium(J_star: float, *, params: BLParams) -> float:
    """常值情景下的“入侵阈值口径”（类似 R0）：R0>1 则可入侵。"""
    if params.d <= 0:
        return float("inf")
    return float((params.beta * f_J(float(J_star), params.K_J)) / params.d)


def R0_BH_from_equilibrium(H_star: float, J_star: float, *, params: BHParams) -> float:
    """常值情景下的“入侵阈值口径”（类似 R0）：R0>1 则可入侵。"""
    if params.d <= 0:
        return float("inf")
    return float((params.beta * W_HJ(float(H_star), float(J_star), params.K_W)) / params.d)

