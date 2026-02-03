# -*- coding: utf-8 -*-
# Model-3：Model-0 + B_L + B_H（双受益者并存）
#
# 设计思路：
# - B_L：依赖寄生期 J（七鳃鳗多 → 传播链完整 → B_L 更易维持），并反噬 J
# - B_H：依赖宿主受损 W(H,J)（寄生越强 → 易感性越高 → B_H 越易暴发），并伤害 H
# - 两者通过 H↔J 闭环产生间接相互作用：B_L 抑制 J 可能缓解 H，从而压制 B_H；反之亦然

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .beneficiary import BHParams, BLParams, W_HJ, f_J, g_B
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
class Model3Params:
    base: Model0Params = field(default_factory=Model0Params)
    bl: BLParams = field(default_factory=BLParams)
    bh: BHParams = field(default_factory=BHParams)


def rhs_model3(
    t: float,
    y: np.ndarray,
    *,
    R: float,
    params: Model3Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
) -> np.ndarray:
    """Model-3 的微分方程右端项（含可选记忆状态 x_bar）。

    状态向量（len=8）：
      y = [H, L, J, M, F, x_bar, B_L, B_H]
    """
    H, L, J, M, F, x_bar, BL, BH = y

    H = max(H, 0.0)
    L = max(L, 0.0)
    J = max(J, 0.0)
    M = max(M, 0.0)
    F = max(F, 0.0)
    BL = max(BL, 0.0)
    BH = max(BH, 0.0)

    base = params.base
    bl = params.bl
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

    # 宿主：七鳃鳗寄生损伤 + B_H 额外死亡
    damage = host_damage_term(J=J, a=base.a, alpha_HJ=base.alpha_HJ)
    extra_H = bh.delta_H * g_B(BH, bh.K_BH)
    dH = base.r_H * H * (1.0 - H / base.K_H) - damage * H - extra_H * H

    # 七鳃鳗：J->成体受宿主丰度饱和调制；B_L 额外死亡
    mu_L = base.mu_L_max * x
    muJ_mult = maturation_multiplier(H=H, K_HJ=base.K_HJ)
    mu_J_eff = base.mu_J * muJ_mult

    extra_J = bl.delta_J * g_B(BL, bl.K_BJ)

    dL = base.b * F * ph - mu_L * L - base.d_L * L
    dJ = mu_L * L - mu_J_eff * J - base.d_J * J - extra_J * J
    uA = harvest_rate(A=M + F, u_const=base.u_A_const, u_max=base.u_A_max, u_th=base.u_A_th, u_k=base.u_A_k)
    dM = pm * mu_J_eff * J - base.d_M * M - uA * M
    dF = (1.0 - pm) * mu_J_eff * J - base.d_F * F - uA * F

    # B_L：依赖 J；带自限
    rBL = bl.beta * f_J(J, bl.K_J)
    if bl.K_cap > 0:
        dBL = rBL * BL * (1.0 - BL / bl.K_cap) - bl.d * BL
    else:
        dBL = rBL * BL - bl.d * BL

    # B_H：依赖 W(H,J)；带自限
    W = W_HJ(H, J, bh.K_W)
    rBH = bh.beta * W
    if bh.K_cap > 0:
        dBH = rBH * BH * (1.0 - BH / bh.K_cap) - bh.d * BH
    else:
        dBH = rBH * BH - bh.d * BH

    return np.array([dH, dL, dJ, dM, dF, dx_bar, dBL, dBH], dtype=float)
