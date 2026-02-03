# -*- coding: utf-8 -*-
# Model-2：Model-0 + B_H（宿主鱼机会性寄生虫/病原体）
#
# 设计思路：
# - 七鳃鳗寄生导致宿主“伤口/应激/易感性”上升，用 W(H,J)∈[0,1] 表示
# - B_H 的增长依赖 W(H,J)（机会性：宿主越受损越容易暴发）
# - B_H 反过来增加宿主死亡，从而间接影响七鳃鳗（通过 mu_J_eff(H) 等闭环）

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .beneficiary import BHParams, W_HJ, g_B
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
class Model2Params:
    base: Model0Params = field(default_factory=Model0Params)
    bh: BHParams = field(default_factory=BHParams)


def rhs_model2(
    t: float,
    y: np.ndarray,
    *,
    R: float,
    params: Model2Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
) -> np.ndarray:
    """Model-2 的微分方程右端项（含可选记忆状态 x_bar）。

    状态向量（len=7）：
      y = [H, L, J, M, F, x_bar, B_H]
    """
    H, L, J, M, F, x_bar, B = y

    H = max(H, 0.0)
    L = max(L, 0.0)
    J = max(J, 0.0)
    M = max(M, 0.0)
    F = max(F, 0.0)
    B = max(B, 0.0)

    base = params.base
    bh = params.bh

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

    # 宿主动力学：逻辑斯蒂增长 - 七鳃鳗寄生损伤 - B_H 额外死亡
    damage = host_damage_term(J=J, a=base.a, alpha_HJ=base.alpha_HJ)
    extra_H = bh.delta_H * g_B(B, bh.K_BH)
    dH = base.r_H * H * (1.0 - H / base.K_H) - damage * H - extra_H * H

    # 七鳃鳗动力学（与 Model-0 相同）：L->J 随资源；J->成体受宿主丰度饱和调制
    mu_L = base.mu_L_max * x
    muJ_mult = maturation_multiplier(H=H, K_HJ=base.K_HJ)
    mu_J_eff = base.mu_J * muJ_mult

    dL = base.b * F * ph - mu_L * L - base.d_L * L
    dJ = mu_L * L - mu_J_eff * J - base.d_J * J
    uA = harvest_rate(A=M + F, u_const=base.u_A_const, u_max=base.u_A_max, u_th=base.u_A_th, u_k=base.u_A_k)
    dM = pm * mu_J_eff * J - base.d_M * M - uA * M
    dF = (1.0 - pm) * mu_J_eff * J - base.d_F * F - uA * F

    # B_H 动力学：机会性感染（依赖 W(H,J)）+ 自限 + 衰亡
    W = W_HJ(H, J, bh.K_W)
    rB = bh.beta * W
    if bh.K_cap > 0:
        dB = rB * B * (1.0 - B / bh.K_cap) - bh.d * B
    else:
        dB = rB * B - bh.d * B

    return np.array([dH, dL, dJ, dM, dF, dx_bar, dB], dtype=float)
