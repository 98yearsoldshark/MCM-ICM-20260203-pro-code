# -*- coding: utf-8 -*-
# 环境过程：两态马尔可夫链（丰/歉年）
#
# 用途：
# - 生成资源序列 R(t)（低资源 R_L / 高资源 R_H）
# - 用 p_LH/p_HL 控制环境自相关（平均连续歉年≈1/p_LH，连续丰年≈1/p_HL）

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MarkovEnv:
    """两态马尔可夫环境（资源丰/歉年）。

    状态编码：
    - 0：低资源（R_L）
    - 1：高资源（R_H）
    """

    R_L: float
    R_H: float
    p_LH: float  # P(H | L)
    p_HL: float  # P(L | H)

    def stationary_pi_H(self) -> float:
        denom = self.p_LH + self.p_HL
        if denom <= 0:
            # 退化情形：避免除 0，视为 0.5
            return 0.5
        return self.p_LH / denom

    def R_bar(self) -> float:
        pi_H = self.stationary_pi_H()
        return (1.0 - pi_H) * self.R_L + pi_H * self.R_H

    def sample_states(self, T: int, rng: np.random.Generator, *, init_state: int | None = None) -> np.ndarray:
        """采样长度为 T 的状态序列（元素∈{0,1}）。"""
        if T <= 0:
            return np.zeros((0,), dtype=np.int8)

        states = np.empty((T,), dtype=np.int8)

        if init_state is None:
            # 从平稳分布初始化，减少 burn-in 影响
            pi_H = self.stationary_pi_H()
            init_state = int(rng.random() < pi_H)
        else:
            init_state = 1 if init_state else 0

        states[0] = init_state
        for t in range(1, T):
            if states[t - 1] == 0:
                states[t] = 1 if rng.random() < self.p_LH else 0
            else:
                states[t] = 0 if rng.random() < self.p_HL else 1
        return states

    def states_to_R(self, states: np.ndarray) -> np.ndarray:
        """把状态序列映射为资源值序列 R_t。"""
        states = np.asarray(states, dtype=np.int8)
        R = np.where(states == 0, self.R_L, self.R_H).astype(float)
        return R

    def sample_R_series(self, T: int, rng: np.random.Generator, *, init_state: int | None = None) -> np.ndarray:
        """便捷函数：先采样状态，再映射为 R 序列。"""
        return self.states_to_R(self.sample_states(T=T, rng=rng, init_state=init_state))
