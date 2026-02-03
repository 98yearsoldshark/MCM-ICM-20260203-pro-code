# -*- coding: utf-8 -*-
# Model-1：Model-0 + B_L（七鳃鳗相关寄生虫/病原体）
#
# 设计思路：
# - B_L 的增长依赖七鳃鳗寄生期 J（传播链随宿主丰度增强，采用饱和函数 f_J）
# - B_L 反过来增加 J 的死亡（或等效降低成功变态/成熟），形成“受益-反噬”闭环
# - B_L 使用 logistic 自限项避免无界指数增长导致数值不稳定

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .beneficiary import BLParams, f_J, g_B
from .model0 import (
    Model0Params,
    harvest_rate,
    host_damage_term,
    male_fraction,
    maturation_multiplier,
    phi_mating,
    x_from_resource,
)


@dataclass(frozen=True)
class Model1Params:
    base: Model0Params = field(default_factory=Model0Params)
    bl: BLParams = field(default_factory=BLParams)


def rhs_model1(
    t: float,
    y: np.ndarray,
    *,
    R: float,
    params: Model1Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
) -> np.ndarray:
    """Model-1 的微分方程右端项（含可选记忆状态 x_bar）。

    状态向量（len=7）：
      y = [H, L, J, M, F, x_bar, B_L]
    """
    H, L, J, M, F, x_bar, B = y

    # 数值稳定：导数计算时先裁剪到非负
    H = max(H, 0.0)
    L = max(L, 0.0)
    J = max(J, 0.0)
    M = max(M, 0.0)
    F = max(F, 0.0)
    B = max(B, 0.0)

    base = params.base
    bl = params.bl

    x = x_from_resource(R=R, L=L, K_u=base.K_u, eps_L=base.eps_L)

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

    ph = phi_mating(M=M, F=F, h=base.h)

    # 宿主动力学：逻辑斯蒂增长 - 七鳃鳗寄生损伤
    damage = host_damage_term(J=J, a=base.a, alpha_HJ=base.alpha_HJ)
    dH = base.r_H * H * (1.0 - H / base.K_H) - damage * H

    # 七鳃鳗动力学：L->J 随资源；J->成体受宿主丰度饱和调制
    mu_L = base.mu_L_max * x
    muJ_mult = maturation_multiplier(H=H, K_HJ=base.K_HJ)
    mu_J_eff = base.mu_J * muJ_mult

    # B_L 对 J 的额外死亡（饱和）
    extra_J = bl.delta_J * g_B(B, bl.K_BJ)

    dL = base.b * F * ph - mu_L * L - base.d_L * L
    dJ = mu_L * L - mu_J_eff * J - base.d_J * J - extra_J * J
    uA = harvest_rate(A=M + F, u_const=base.u_A_const, u_max=base.u_A_max, u_th=base.u_A_th, u_k=base.u_A_k)
    dM = pm * mu_J_eff * J - base.d_M * M - uA * M
    dF = (1.0 - pm) * mu_J_eff * J - base.d_F * F - uA * F

    # B_L 动力学：依赖寄生期 J 的增殖（饱和）+ 自然衰亡；带自限避免无界增长
    rB = bl.beta * f_J(J, bl.K_J)
    if bl.K_cap > 0:
        dB = rB * B * (1.0 - B / bl.K_cap) - bl.d * B
    else:
        dB = rB * B - bl.d * B

    return np.array([dH, dL, dJ, dM, dF, dx_bar, dB], dtype=float)
