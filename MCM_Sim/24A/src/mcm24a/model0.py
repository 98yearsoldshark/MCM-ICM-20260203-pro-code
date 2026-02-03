# -*- coding: utf-8 -*-
# Model-0：宿主鱼 H + 七鳃鳗 L/J/M/F（带性别比反应范式与“记忆”）
#
# 说明：
# - 这是仿真代码的最小可用生态系统：性别比通过繁殖项影响种群，并反馈到宿主。
# - 性别比 p_m 由幼体人均资源 x（或其平滑历史 x_bar）驱动，锚定赛题 0.78/0.56。
# - 记忆长度 w 用一阶低通滤波近似“窗口平均”，避免直接实现 DDE（延迟微分方程）。

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Model0Params:
    # 宿主鱼动力学（默认把 H 归一化到 K_H，因此 K_H 常取 1）
    r_H: float = 1.0
    K_H: float = 1.0
    a: float = 0.8  # 寄生期 J 对宿主的伤害强度
    alpha_HJ: float = 0.0  # 宿主受害项对 J 的饱和系数；0 表示线性

    # 七鳃鳗阶段结构参数
    # b 是“有效补充系数”的合并项（fecundity * early survival）。
    # 这里选一个能在平均资源下产生非平凡共存稳态的基线值，方便做策略对照。
    b: float = 10.0
    mu_L_max: float = 0.8  # 幼体 L -> 寄生期 J 的最大转化率（随资源增加而接近）
    mu_J: float = 1.0  # 寄生期 J -> 成体（M/F）的基准转化率
    d_L: float = 0.2
    d_J: float = 0.3
    d_M: float = 1.2
    d_F: float = 1.2

    # 繁殖受精/配对限制
    h: float = 1.0  # phi(M,F)=M/(M+hF) 中的限制强度

    # 资源归一化
    K_u: float = 1.0
    eps_L: float = 1e-9

    # 可选增强：让宿主反过来影响 J->成体的转化（形成 H↔J 双向耦合）
    K_HJ: float = 0.3  # mu_J_eff(H)=mu_J*H/(H+K_HJ) 的半饱和常数；<=0 表示总是饱和

    # 可选扩展：人类捕捞/控制（对成体额外移除率）
    # - u_A_const：恒定捕捞强度（用于“某地区一直吃/一直不吃”的对照）
    # - u_A_max/u_A_th/u_A_k：随成体数量门控的捕捞（避免在极低密度时继续高强度捕捞）
    u_A_const: float = 0.0
    u_A_max: float = 0.0
    u_A_th: float = 0.3
    u_A_k: float = 10.0


def phi_mating(M: float, F: float, h: float, eps: float = 1e-12) -> float:
    """受精/配对成功率 phi(M,F)=M/(M+hF)（数值稳定版）。"""
    denom = M + h * F
    if denom <= eps:
        return 0.0
    return M / denom


def x_from_resource(R: float, L: float, K_u: float, eps_L: float) -> float:
    """幼体人均资源 u=R/(L+eps) 映射到 x=u/(u+K_u)∈(0,1)。"""
    u = R / (L + eps_L)
    x = u / (u + K_u)
    # 数值安全：截断到 [0,1]
    return float(np.clip(x, 0.0, 1.0))


def male_fraction(x_eff: float, gamma: float) -> float:
    """雄性比例反应范式（锚定：低资源 0.78，高资源 0.56）。"""
    x_eff = float(np.clip(x_eff, 0.0, 1.0))
    pm = 0.56 + 0.22 * (1.0 - x_eff**gamma)
    return float(np.clip(pm, 0.56, 0.78))


def host_damage_term(J: float, a: float, alpha_HJ: float) -> float:
    """宿主损伤项：线性或对 J 饱和。"""
    if alpha_HJ <= 0:
        return a * J
    return a * (J / (1.0 + alpha_HJ * J))


def maturation_multiplier(H: float, K_HJ: float) -> float:
    """宿主对七鳃鳗成熟率的饱和影响（形成双向耦合）。

    若 K_HJ <= 0：视为总是饱和（乘子=1）。
    """
    if K_HJ <= 0:
        return 1.0
    return float(np.clip(H / (H + K_HJ), 0.0, 1.0))


def harvest_rate(A: float, *, u_const: float, u_max: float, u_th: float, u_k: float) -> float:
    """对成体的额外移除率（年^-1）。

    u(A) = u_const + u_max / (1 + exp(-u_k*(A - u_th)))
    """
    A = max(float(A), 0.0)
    u = float(u_const)
    if u_max > 0:
        u += float(u_max) / (1.0 + float(np.exp(-float(u_k) * (A - float(u_th)))))
    return float(max(u, 0.0))


def rhs_model0(
    t: float,
    y: np.ndarray,
    *,
    R: float,
    params: Model0Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
) -> np.ndarray:
    """Model-0 的微分方程右端项（含可选记忆状态 x_bar）。

    状态向量（len=6）：
      y = [H, L, J, M, F, x_bar]

    记忆参数 w：
      - w <= 0：使用瞬时 x（忽略 x_bar；dx_bar/dt=0）
      - w > 0：使用 x_bar，且 dx_bar/dt = (x - x_bar)/w（低通滤波近似窗口平均）

    固定性别比对照：
      - 传入 p_m_override（常数），即可得到 S_56/S_78/S_50 等策略。
    """
    H, L, J, M, F, x_bar = y

    # 为避免数值误差导致的负数，计算导数时先裁剪到非负
    H = max(H, 0.0)
    L = max(L, 0.0)
    J = max(J, 0.0)
    M = max(M, 0.0)
    F = max(F, 0.0)

    x = x_from_resource(R=R, L=L, K_u=params.K_u, eps_L=params.eps_L)

    if w > 0:
        x_eff = float(np.clip(x_bar, 0.0, 1.0))
        dx_bar = (x - x_eff) / w
    else:
        x_eff = x
        dx_bar = 0.0

    if p_m_override is None:
        pm = male_fraction(x_eff=x_eff, gamma=gamma)
    else:
        pm = float(np.clip(float(p_m_override), 0.0, 1.0))
    ph = phi_mating(M=M, F=F, h=params.h)

    # 宿主动力学：逻辑斯蒂增长 - 寄生损伤
    damage = host_damage_term(J=J, a=params.a, alpha_HJ=params.alpha_HJ)
    dH = params.r_H * H * (1.0 - H / params.K_H) - damage * H

    # 七鳃鳗动力学：L->J 随资源；J->成体受宿主丰度饱和调制
    mu_L = params.mu_L_max * x
    muJ_mult = maturation_multiplier(H=H, K_HJ=params.K_HJ)
    mu_J_eff = params.mu_J * muJ_mult

    dL = params.b * F * ph - mu_L * L - params.d_L * L
    dJ = mu_L * L - mu_J_eff * J - params.d_J * J
    uA = harvest_rate(
        A=M + F,
        u_const=params.u_A_const,
        u_max=params.u_A_max,
        u_th=params.u_A_th,
        u_k=params.u_A_k,
    )
    dM = pm * mu_J_eff * J - params.d_M * M - uA * M
    dF = (1.0 - pm) * mu_J_eff * J - params.d_F * F - uA * F

    return np.array([dH, dL, dJ, dM, dF, dx_bar], dtype=float)
