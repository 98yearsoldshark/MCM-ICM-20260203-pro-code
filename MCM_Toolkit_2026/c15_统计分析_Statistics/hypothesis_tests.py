# -*- coding: utf-8 -*-
# 常用统计检验与区间估计（scipy.stats / statsmodels）
#
# 参考来源（资料目录）：
# - 4、Python各类算法代码集合/41-2 .../04第4章 概率论与数理统计/...（置信区间、t 检验、卡方检验、K-S 检验、方差分析等）
#
# 说明：
# - 竞赛中“统计推断”常用于：对比差异（t 检验/ANOVA）、拟合优度（卡方/K-S）、置信区间估计等
# - 本文件提供轻量封装，便于统一接口调用

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy import stats

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_1d(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float).reshape(-1)
    if arr.size == 0:
        raise ValueError("样本不能为空。")
    return arr


def confidence_interval_mean(x: Any, *, alpha: float = 0.05) -> Dict[str, Any]:
    """
    均值的 (1-alpha) 置信区间（t 区间）。
    """
    arr = _to_1d(x)
    n = int(arr.size)
    mean = float(np.mean(arr))
    s = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    if n <= 1 or s == 0:
        return {"mean": mean, "n": n, "ci": (mean, mean), "alpha": float(alpha)}

    se = s / np.sqrt(n)
    tcrit = float(stats.t.ppf(1.0 - float(alpha) / 2.0, df=n - 1))
    lo = mean - tcrit * se
    hi = mean + tcrit * se
    return {"mean": mean, "n": n, "std": s, "se": float(se), "tcrit": tcrit, "ci": (float(lo), float(hi)), "alpha": float(alpha)}


def ttest_independent(a: Any, b: Any, *, equal_var: bool = False) -> Dict[str, Any]:
    """
    两独立样本 t 检验（Welch 默认，equal_var=False）。
    """
    a1 = _to_1d(a)
    b1 = _to_1d(b)
    res = stats.ttest_ind(a1, b1, equal_var=bool(equal_var), nan_policy="omit")
    return {
        "statistic": float(res.statistic),
        "pvalue": float(res.pvalue),
        "equal_var": bool(equal_var),
        "mean_a": float(np.nanmean(a1)),
        "mean_b": float(np.nanmean(b1)),
        "n_a": int(np.sum(~np.isnan(a1))),
        "n_b": int(np.sum(~np.isnan(b1))),
    }


def chi_square_gof(observed: Any, expected: Optional[Any] = None) -> Dict[str, Any]:
    """
    卡方拟合优度检验（goodness-of-fit）。
    """
    obs = _to_1d(observed)
    if np.any(obs < 0):
        raise ValueError("observed 频数不能为负。")
    if expected is None:
        exp = np.ones_like(obs) * (float(np.sum(obs)) / obs.size)
    else:
        exp = _to_1d(expected)
        if exp.shape != obs.shape:
            raise ValueError("expected 与 observed 形状必须一致。")
    res = stats.chisquare(f_obs=obs, f_exp=exp)
    return {"statistic": float(res.statistic), "pvalue": float(res.pvalue), "df": int(obs.size - 1)}


def chi_square_independence(table: Any, *, correction: bool = True) -> Dict[str, Any]:
    """
    卡方独立性检验（列联表）。
    """
    tab = np.asarray(table, dtype=float)
    if tab.ndim != 2:
        raise ValueError("table 必须为二维列联表。")
    if np.any(tab < 0):
        raise ValueError("列联表频数不能为负。")
    chi2, p, dof, expected = stats.chi2_contingency(tab, correction=bool(correction))
    return {"chi2": float(chi2), "pvalue": float(p), "dof": int(dof), "expected": expected, "correction": bool(correction)}


def normality_test(x: Any) -> Dict[str, Any]:
    """
    正态性检验（自动选择）。

    - n>=8：使用 D'Agostino K^2（scipy.stats.normaltest）
    - n<8：使用 Shapiro（scipy.stats.shapiro）
    """
    arr = _to_1d(x)
    n = int(arr.size)
    if n >= 8:
        stat, p = stats.normaltest(arr, nan_policy="omit")
        method = "normaltest"
    else:
        stat, p = stats.shapiro(arr)
        method = "shapiro"
    return {"method": method, "statistic": float(stat), "pvalue": float(p), "n": n}


def ks_test_normal(x: Any) -> Dict[str, Any]:
    """
    K-S 检验：检验样本是否来自某个正态分布 N(mu, sigma^2)。

    注意：mu/sigma 由样本估计会影响严格显著性（比赛中可作快速检验/参考）。
    """
    arr = _to_1d(x)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    if sigma == 0:
        return {"statistic": 0.0, "pvalue": 1.0, "mu": mu, "sigma": sigma}
    stat, p = stats.kstest(arr, "norm", args=(mu, sigma))
    return {"statistic": float(stat), "pvalue": float(p), "mu": mu, "sigma": sigma}


def anova_oneway(groups: Sequence[Any]) -> Dict[str, Any]:
    """
    单因素方差分析：多个组的均值是否相同。
    """
    xs = [_to_1d(g) for g in groups]
    if len(xs) < 2:
        raise ValueError("anova_oneway 至少需要 2 组数据。")
    res = stats.f_oneway(*xs)
    return {"statistic": float(res.statistic), "pvalue": float(res.pvalue), "k_groups": int(len(xs))}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：常用统计检验。

    Args:
        data: 根据 test 不同，支持：
            - ttest_ind:
                - (a,b) 或 {'a','b'}
            - chi2_gof:
                - observed 或 {'observed','expected'(可选)}
            - chi2_independence:
                - table 或 {'table'}
            - ci_mean / normality / ks_normal:
                - x 或 {'x'}
            - anova_oneway:
                - {'groups': [g1,g2,...]}
        params:
            - test: str（默认 'ttest_ind'）
            - alpha: float（ci_mean 使用，默认 0.05）
            - equal_var: bool（ttest_ind 使用，默认 False）
            - correction: bool（chi2_independence 使用，默认 True）

    Returns:
        dict: {'test':..., 'result':...}
    """
    params = params or {}
    test = str(params.get("test", "ttest_ind")).lower()

    if test in {"ci_mean", "confidence_interval_mean"}:
        x = data.get("x") if isinstance(data, dict) else data
        return {"test": test, "result": confidence_interval_mean(x, alpha=float(params.get("alpha", 0.05)))}

    if test in {"ttest_ind", "ttest_independent"}:
        if isinstance(data, (tuple, list)) and len(data) == 2:
            a, b = data
        elif isinstance(data, dict) and "a" in data and "b" in data:
            a, b = data["a"], data["b"]
        else:
            raise ValueError("ttest_ind 需要 (a,b) 或 {'a','b'}。")
        return {"test": test, "result": ttest_independent(a, b, equal_var=bool(params.get("equal_var", False)))}

    if test in {"chi2_gof", "chisquare_gof", "chi_square_gof"}:
        if isinstance(data, dict):
            obs = data.get("observed")
            exp = data.get("expected")
        else:
            obs = data
            exp = None
        return {"test": test, "result": chi_square_gof(obs, expected=exp)}

    if test in {"chi2_independence", "chi_square_independence"}:
        tab = data.get("table") if isinstance(data, dict) else data
        return {"test": test, "result": chi_square_independence(tab, correction=bool(params.get("correction", True)))}

    if test in {"normality", "normality_test"}:
        x = data.get("x") if isinstance(data, dict) else data
        return {"test": test, "result": normality_test(x)}

    if test in {"ks_normal", "kstest_normal"}:
        x = data.get("x") if isinstance(data, dict) else data
        return {"test": test, "result": ks_test_normal(x)}

    if test in {"anova_oneway", "anova"}:
        if not isinstance(data, dict) or "groups" not in data:
            raise ValueError("anova_oneway 需要 data={'groups':[...]}。")
        return {"test": test, "result": anova_oneway(data["groups"])}

    raise ValueError(f"不支持的 test: {test}")


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, size=60)
    b = rng.normal(0.3, 1, size=55)
    print(solve((a, b), {"test": "ttest_ind"})["result"])
    print(solve(a, {"test": "ci_mean", "alpha": 0.05})["result"])
    print(solve(a, {"test": "normality"})["result"])

