# -*- coding: utf-8 -*-
# 隐马尔可夫模型（HMM）：给定参数的评分（log-likelihood）与解码（Viterbi）
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../马尔科夫预测模型Python代码/HMM_2.py（原代码依赖 hmmlearn）
#
# 说明：
# - 本实现不依赖 hmmlearn；适用于“已知 HMM 参数”的评分与最可能隐状态序列求解
# - 支持两种观测：
#   1) 离散观测：B[i, o] = P(obs=o | state=i)
#   2) 高斯观测：每个状态对应一个高斯分布 N(mu_i, Sigma_i)

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.special import logsumexp

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _normalize_prob(p: np.ndarray, axis: Optional[int] = None, eps: float = 1e-12) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    s = np.sum(p, axis=axis, keepdims=True)
    s = np.where(s <= 0, 1.0, s)
    out = p / s
    out = np.clip(out, eps, 1.0)
    out = out / np.sum(out, axis=axis, keepdims=True)
    return out


def _log_gaussian_pdf_full(X: np.ndarray, means: np.ndarray, covars: np.ndarray) -> np.ndarray:
    """
    计算 log N(x | mu_i, Sigma_i)。

    Args:
        X: (T×d)
        means: (K×d)
        covars: (K×d×d) full covariance

    Returns:
        logp: (T×K)
    """
    X = np.asarray(X, dtype=float)
    means = np.asarray(means, dtype=float)
    covars = np.asarray(covars, dtype=float)

    T, d = X.shape
    K = means.shape[0]
    if means.shape != (K, d) or covars.shape != (K, d, d):
        raise ValueError("means/covars 维度不匹配。")

    logp = np.zeros((T, K), dtype=float)
    const = -0.5 * d * np.log(2.0 * np.pi)

    for i in range(K):
        mu = means[i]
        Sigma = covars[i]
        # 数值稳健：对角加一点 jitter
        Sigma = Sigma + 1e-9 * np.eye(d)
        sign, logdet = np.linalg.slogdet(Sigma)
        if sign <= 0:
            raise ValueError("协方差矩阵必须为正定（或至少半正定且可数值稳定）。")
        inv = np.linalg.inv(Sigma)
        Xm = X - mu[None, :]
        quad = np.einsum("ij,jk,ik->i", Xm, inv, Xm)
        logp[:, i] = const - 0.5 * (logdet + quad)
    return logp


def _log_gaussian_pdf_diag(X: np.ndarray, means: np.ndarray, covars: np.ndarray) -> np.ndarray:
    """
    对角协方差：Sigma_i = diag(var_i)。

    covars: (K×d) 或 (K×d×d) 但只取对角
    """
    X = np.asarray(X, dtype=float)
    means = np.asarray(means, dtype=float)
    covars = np.asarray(covars, dtype=float)
    T, d = X.shape
    K = means.shape[0]
    if means.shape != (K, d):
        raise ValueError("means 维度不匹配。")
    if covars.ndim == 3:
        if covars.shape != (K, d, d):
            raise ValueError("covars 维度不匹配。")
        var = np.diagonal(covars, axis1=1, axis2=2)
    else:
        if covars.shape != (K, d):
            raise ValueError("covars 维度不匹配。")
        var = covars
    var = np.maximum(var, 1e-9)

    const = -0.5 * d * np.log(2.0 * np.pi)
    # log N = const -0.5 * [sum log var + sum ((x-mu)^2/var)]
    diff = X[:, None, :] - means[None, :, :]  # T×K×d
    quad = np.sum((diff**2) / var[None, :, :], axis=2)  # T×K
    logdet = np.sum(np.log(var), axis=1)  # K
    return const - 0.5 * (logdet[None, :] + quad)


def hmm_log_likelihood(
    observations: Union[Sequence[int], np.ndarray],
    *,
    startprob: Union[np.ndarray, Sequence[float]],
    transmat: Union[np.ndarray, Sequence[Sequence[float]]],
    emission: Dict[str, Any],
) -> Dict[str, Any]:
    """
    计算 HMM 的对数似然（log-likelihood），并返回前向变量（log-alpha）。

    Args:
        observations: 观测序列：
            - 离散：list[int]，取值 0..M-1
            - 高斯：ndarray shape=(T,d)
        startprob: 初始状态分布 π（K,）。
        transmat: 转移矩阵 A（K×K），A[i,j]=P(z_t=j | z_{t-1}=i)。
        emission: 发射/观测模型配置：
            - {'type':'discrete','B': (K×M) 发射概率矩阵}
            - {'type':'gaussian','means':(K×d),'covars':(K×d×d 或 K×d),'covariance_type':'full'|'diag'}

    Returns:
        dict:
            - log_likelihood: float
            - log_alpha: (T×K)
            - log_B: (T×K) 每步每状态的观测 log 概率
    """
    pi = _normalize_prob(np.asarray(startprob, dtype=float).reshape(-1), axis=None)
    A = _normalize_prob(np.asarray(transmat, dtype=float), axis=1)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("transmat 必须为方阵 (K×K)。")
    K = A.shape[0]
    if pi.shape != (K,):
        raise ValueError("startprob 维度必须为 (K,)。")

    etype = str(emission.get("type", "")).lower()
    if etype == "discrete":
        obs = np.asarray(observations, dtype=int).reshape(-1)
        B = _normalize_prob(np.asarray(emission["B"], dtype=float), axis=1)
        if B.shape[0] != K:
            raise ValueError("B 的行数必须等于状态数 K。")
        if obs.size == 0:
            return {"log_likelihood": 0.0, "log_alpha": np.empty((0, K)), "log_B": np.empty((0, K))}
        if np.any(obs < 0) or np.any(obs >= B.shape[1]):
            raise ValueError("离散观测值超出 B 的列范围。")
        log_B = np.log(B[:, obs].T + 1e-12)  # (T×K)
    elif etype == "gaussian":
        X = np.asarray(observations, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError("高斯观测 observations 必须为 (T×d)。")
        means = np.asarray(emission["means"], dtype=float)
        covars = np.asarray(emission["covars"], dtype=float)
        cov_type = str(emission.get("covariance_type", "full")).lower()
        if cov_type == "diag":
            log_B = _log_gaussian_pdf_diag(X, means, covars)
        elif cov_type == "full":
            log_B = _log_gaussian_pdf_full(X, means, covars if covars.ndim == 3 else np.diagflat(covars))
        else:
            raise ValueError("covariance_type 必须为 'full' 或 'diag'。")
    else:
        raise ValueError("emission.type 必须为 'discrete' 或 'gaussian'。")

    T = log_B.shape[0]
    log_pi = np.log(pi + 1e-12)
    log_A = np.log(A + 1e-12)

    log_alpha = np.zeros((T, K), dtype=float)
    log_alpha[0, :] = log_pi + log_B[0, :]
    for t in range(1, T):
        # log_alpha[t,i] = log_B[t,i] + logsumexp_j(log_alpha[t-1,j] + log_A[j,i])
        log_alpha[t, :] = log_B[t, :] + logsumexp(log_alpha[t - 1, :][:, None] + log_A, axis=0)

    ll = float(logsumexp(log_alpha[T - 1, :]))
    return {"log_likelihood": ll, "log_alpha": log_alpha, "log_B": log_B}


def hmm_viterbi(
    observations: Union[Sequence[int], np.ndarray],
    *,
    startprob: Union[np.ndarray, Sequence[float]],
    transmat: Union[np.ndarray, Sequence[Sequence[float]]],
    emission: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Viterbi 解码：求最可能的隐状态序列。

    Returns:
        dict:
            - states: (T,) 最优隐状态序列（0..K-1）
            - log_prob: 最优路径的对数概率
    """
    # 复用 log_B 计算
    out = hmm_log_likelihood(observations, startprob=startprob, transmat=transmat, emission=emission)
    log_B = out["log_B"]
    T, K = log_B.shape

    pi = _normalize_prob(np.asarray(startprob, dtype=float).reshape(-1), axis=None)
    A = _normalize_prob(np.asarray(transmat, dtype=float), axis=1)
    log_pi = np.log(pi + 1e-12)
    log_A = np.log(A + 1e-12)

    delta = np.zeros((T, K), dtype=float)
    psi = np.zeros((T, K), dtype=int)

    delta[0, :] = log_pi + log_B[0, :]
    psi[0, :] = 0
    for t in range(1, T):
        scores = delta[t - 1, :][:, None] + log_A  # (K×K)
        psi[t, :] = np.argmax(scores, axis=0)
        delta[t, :] = log_B[t, :] + np.max(scores, axis=0)

    states = np.zeros(T, dtype=int)
    states[T - 1] = int(np.argmax(delta[T - 1, :]))
    for t in range(T - 2, -1, -1):
        states[t] = int(psi[t + 1, states[t + 1]])

    log_prob = float(np.max(delta[T - 1, :]))
    return {"states": states, "log_prob": log_prob}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：HMM 评分 +（可选）Viterbi 解码。

    Args:
        data: dict，包含：
            - observations: list[int] 或 ndarray(T×d)
            - startprob: (K,)
            - transmat: (K×K)
            - emission: dict（见 hmm_log_likelihood）
        params: 参数：
            - do_viterbi: bool（默认 True）

    Returns:
        dict:
            - log_likelihood
            - (可选) states/log_prob
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")
    for k in ("observations", "startprob", "transmat", "emission"):
        if k not in data:
            raise ValueError(f"data 缺少必要字段：{k}")

    ll = hmm_log_likelihood(
        data["observations"],
        startprob=data["startprob"],
        transmat=data["transmat"],
        emission=data["emission"],
    )

    out = {"log_likelihood": ll["log_likelihood"]}
    if bool(params.get("do_viterbi", True)):
        vit = hmm_viterbi(
            data["observations"],
            startprob=data["startprob"],
            transmat=data["transmat"],
            emission=data["emission"],
        )
        out.update(vit)
    return out


if __name__ == "__main__":
    # Demo 1：离散 HMM
    # 两个隐状态，三个观测符号
    startprob = [0.6, 0.4]
    transmat = [[0.7, 0.3], [0.4, 0.6]]
    B = [[0.5, 0.4, 0.1], [0.1, 0.3, 0.6]]
    obs = [0, 1, 1, 2, 1, 0]
    out = solve(
        {"observations": obs, "startprob": startprob, "transmat": transmat, "emission": {"type": "discrete", "B": B}},
        {"do_viterbi": True},
    )
    print("[Discrete] log_likelihood =", out["log_likelihood"])
    print("[Discrete] states =", out["states"])

    # Demo 2：高斯 HMM（给定参数，做 Viterbi）
    rng = np.random.default_rng(0)
    means = np.array([[0.0, 0.0], [3.0, 3.0]])
    covs = np.array([np.eye(2) * 0.5, np.eye(2) * 0.8])
    obs2 = np.vstack([rng.normal(means[0], 0.5, size=(5, 2)), rng.normal(means[1], 0.7, size=(5, 2))])
    out2 = solve(
        {
            "observations": obs2,
            "startprob": [0.5, 0.5],
            "transmat": [[0.9, 0.1], [0.1, 0.9]],
            "emission": {"type": "gaussian", "means": means, "covars": covs, "covariance_type": "full"},
        },
        {"do_viterbi": True},
    )
    print("[Gaussian] log_likelihood =", out2["log_likelihood"])
    print("[Gaussian] states =", out2["states"])

