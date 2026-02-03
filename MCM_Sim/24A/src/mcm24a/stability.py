# -*- coding: utf-8 -*-
# 稳定性分析工具：常值资源下的平衡点与局部稳定（Jacobian 特征值）
#
# 用途（对应赛题 Q3“稳定性/韧性”）：
# - 对常值资源 R=R0 的平衡点 y* 数值线性化，计算 Jacobian 的特征值
# - 给出：最大实部（是否稳定）、近似回归时间、主振荡周期（若存在复特征值）
#
# 说明：
# - Model-0 在 w<=0 时包含一个“诊断变量” x_bar（对动力学无反馈），会产生 0 特征值；
#   为避免误判，这里提供 5 维降维线性化（忽略 x_bar）。

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .model0 import (
    Model0Params,
    host_damage_term,
    male_fraction,
    maturation_multiplier,
    phi_mating,
    x_from_resource,
)


@dataclass(frozen=True)
class StabilitySummary:
    max_real: float
    stable: int
    return_time: float  # 约等于 -1/max_real（max_real<0）；否则为 inf
    dominant_imag: float
    dominant_period: float  # 约等于 2π/|imag|（imag!=0）；否则为 inf


def finite_diff_jacobian(
    f: Callable[[np.ndarray], np.ndarray],
    y0: np.ndarray,
    *,
    eps: float = 1e-6,
) -> np.ndarray:
    """用中心差分计算 Jacobian：J_ij = ∂f_i/∂y_j。"""
    y0 = np.asarray(y0, dtype=float)
    f0 = np.asarray(f(y0), dtype=float)
    n = y0.size
    m = f0.size
    J = np.zeros((m, n), dtype=float)

    for j in range(n):
        dy = np.zeros_like(y0)
        step = eps * (1.0 + abs(float(y0[j])))
        dy[j] = step
        fp = np.asarray(f(y0 + dy), dtype=float)
        fm = np.asarray(f(y0 - dy), dtype=float)
        J[:, j] = (fp - fm) / (2.0 * step)
    return J


def _rhs_model0_reduced5(
    z: np.ndarray,
    *,
    R: float,
    params: Model0Params,
    gamma: float,
    p_m_override: float | None,
) -> np.ndarray:
    """Model-0 的 5 维右端项（忽略 x_bar），用于 w<=0 的稳定性分析。"""
    H, L, J, M, F = z
    H = max(float(H), 0.0)
    L = max(float(L), 0.0)
    J = max(float(J), 0.0)
    M = max(float(M), 0.0)
    F = max(float(F), 0.0)

    x = x_from_resource(R=float(R), L=float(L), K_u=params.K_u, eps_L=params.eps_L)
    if p_m_override is None:
        pm = male_fraction(x_eff=x, gamma=gamma)
    else:
        pm = float(np.clip(float(p_m_override), 0.0, 1.0))

    ph = phi_mating(M=M, F=F, h=params.h)
    damage = host_damage_term(J=J, a=params.a, alpha_HJ=params.alpha_HJ)
    dH = params.r_H * H * (1.0 - H / params.K_H) - damage * H

    mu_L = params.mu_L_max * x
    muJ_mult = maturation_multiplier(H=H, K_HJ=params.K_HJ)
    mu_J_eff = params.mu_J * muJ_mult

    # 人类捕捞（若启用）：对成体额外移除
    A = M + F
    uA = params.u_A_const
    if params.u_A_max > 0:
        uA += params.u_A_max / (1.0 + np.exp(-params.u_A_k * (A - params.u_A_th)))
    uA = float(max(uA, 0.0))

    dL = params.b * F * ph - mu_L * L - params.d_L * L
    dJ = mu_L * L - mu_J_eff * J - params.d_J * J
    dM = pm * mu_J_eff * J - params.d_M * M - uA * M
    dF = (1.0 - pm) * mu_J_eff * J - params.d_F * F - uA * F
    return np.array([dH, dL, dJ, dM, dF], dtype=float)


def summarize_eigs(eigs: np.ndarray) -> StabilitySummary:
    eigs = np.asarray(eigs, dtype=complex)
    re = np.real(eigs)
    im = np.imag(eigs)
    max_real = float(np.max(re))
    stable = int(max_real < 0.0)
    return_time = float("inf") if max_real >= 0 else float(-1.0 / max_real)

    # 取“实部最大”的特征值作为主导；若有多个，取虚部绝对值最大的那个
    idxs = np.where(np.isclose(re, np.max(re)))[0]
    if idxs.size == 0:
        idx = int(np.argmax(re))
    else:
        idx = int(idxs[np.argmax(np.abs(im[idxs]))])
    dom_im = float(abs(im[idx]))
    dom_period = float("inf") if dom_im == 0.0 else float(2.0 * np.pi / dom_im)
    return StabilitySummary(
        max_real=max_real,
        stable=stable,
        return_time=return_time,
        dominant_imag=dom_im,
        dominant_period=dom_period,
    )


def stability_model0_constant(
    y_star: np.ndarray,
    *,
    R: float,
    params: Model0Params,
    gamma: float,
    w: float,
    p_m_override: float | None = None,
    eps: float = 1e-6,
) -> tuple[np.ndarray, StabilitySummary]:
    """常值资源下 Model-0 的 Jacobian 与稳定性摘要。"""
    y_star = np.asarray(y_star, dtype=float)

    if w <= 0:
        # 降维：忽略 x_bar，避免出现 0 特征值误导
        if y_star.size < 5:
            raise ValueError("y_star 维度不足。")
        z_star = y_star[:5].copy()

        def f(z: np.ndarray) -> np.ndarray:
            return _rhs_model0_reduced5(z, R=R, params=params, gamma=gamma, p_m_override=p_m_override)

        J = finite_diff_jacobian(f, z_star, eps=eps)
        eigs = np.linalg.eigvals(J)
        return J, summarize_eigs(eigs)

    # w>0：完整 6 维（包含 x_bar 的反馈）
    if y_star.size != 6:
        raise ValueError("w>0 时 y_star 需要是 6 维：[H,L,J,M,F,x_bar]。")

    from .model0 import rhs_model0  # 避免循环引用

    def f(y: np.ndarray) -> np.ndarray:
        return rhs_model0(0.0, y, R=R, params=params, gamma=gamma, w=w, p_m_override=p_m_override)

    J = finite_diff_jacobian(f, y_star, eps=eps)
    eigs = np.linalg.eigvals(J)
    return J, summarize_eigs(eigs)

