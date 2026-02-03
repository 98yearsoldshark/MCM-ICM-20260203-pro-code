# -*- coding: utf-8 -*-
# 异常值检测：Grubbs（单变量）/ 马氏距离（多变量）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../格拉布斯准则判断异常数据代码
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../基于马氏距离剔除异常样本代码

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from scipy.stats import chi2, t

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def grubbs_test(x: Union[np.ndarray, list], *, alpha: float = 0.05) -> Dict[str, Any]:
    """
    Grubbs 检验：检测单个异常值（假设近似正态）。

    Args:
        x: 一维样本。
        alpha: 显著性水平（默认 0.05）。

    Returns:
        dict:
            - G: 统计量
            - G_crit: 临界值
            - outlier_index: 异常点索引（0-based），若无异常则为 None
            - is_outlier: bool
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    n = x.size
    if n < 3:
        raise ValueError("Grubbs 检验要求 n>=3。")
    if not (0.0 < float(alpha) < 1.0):
        raise ValueError("alpha 必须在 (0,1) 内。")

    mu = float(np.mean(x))
    s = float(np.std(x, ddof=1))
    if s <= 0:
        return {"G": 0.0, "G_crit": np.inf, "outlier_index": None, "is_outlier": False}

    dev = np.abs(x - mu)
    idx = int(np.argmax(dev))
    G = float(dev[idx] / s)

    # t 临界值：t_{alpha/(2n), n-2}
    t_crit = float(t.ppf(1.0 - float(alpha) / (2.0 * n), df=n - 2))
    G_crit = ((n - 1) / np.sqrt(n)) * np.sqrt(t_crit**2 / (n - 2 + t_crit**2))

    is_outlier = bool(G > G_crit)
    return {"G": G, "G_crit": float(G_crit), "outlier_index": idx if is_outlier else None, "is_outlier": is_outlier}


def mahalanobis_distance(X: Union[np.ndarray, list]) -> np.ndarray:
    """
    计算每个样本的马氏距离平方 D^2。

    Args:
        X: 数据矩阵 (n×p)。

    Returns:
        ndarray (n,)：每个样本的 D^2（马氏距离平方）。
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("X 必须为二维矩阵 (n×p)。")
    n, p = X.shape
    if n < 2:
        return np.zeros(n, dtype=float)

    mu = np.mean(X, axis=0)
    Xc = X - mu
    cov = np.cov(Xc, rowvar=False)
    # 协方差可能奇异：使用伪逆
    inv_cov = np.linalg.pinv(cov)
    d2 = np.einsum("ij,jk,ik->i", Xc, inv_cov, Xc)
    return np.asarray(d2, dtype=float)


def mahalanobis_outliers(X: Union[np.ndarray, list], *, alpha: float = 0.01) -> Dict[str, Any]:
    """
    用卡方分布阈值检测马氏距离异常点。

    Args:
        X: (n×p)
        alpha: 显著性水平；阈值为 chi2.ppf(1-alpha, df=p)。

    Returns:
        dict:
            - d2: 马氏距离平方
            - threshold: 阈值
            - is_outlier: bool mask
    """
    X_arr = np.asarray(X, dtype=float)
    if X_arr.ndim != 2:
        raise ValueError("X 必须为二维矩阵 (n×p)。")
    p = X_arr.shape[1]
    d2 = mahalanobis_distance(X_arr)
    thr = float(chi2.ppf(1.0 - float(alpha), df=p))
    mask = d2 > thr
    return {"d2": d2, "threshold": thr, "is_outlier": mask}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：异常值检测。

    Args:
        data: dict，包含：
            - kind: {'grubbs','mahalanobis'}
            - x 或 X
        params: 参数：
            - alpha: 显著性水平

    Returns:
        dict: 对应的检测结果。
    """
    params = params or {}
    if not isinstance(data, dict) or "kind" not in data:
        raise TypeError("data 必须为 dict，且包含 kind。")
    kind = str(data["kind"]).lower()
    alpha = float(params.get("alpha", 0.05 if kind == "grubbs" else 0.01))

    if kind == "grubbs":
        return grubbs_test(data.get("x"), alpha=alpha)
    if kind == "mahalanobis":
        return mahalanobis_outliers(data.get("X"), alpha=alpha)
    raise ValueError("kind 必须为 grubbs 或 mahalanobis。")


if __name__ == "__main__":
    x = [10, 11, 12, 10, 9, 200]
    out = solve({"kind": "grubbs", "x": x}, {"alpha": 0.05})
    print("grubbs:", out)

    rng = np.random.default_rng(0)
    X = rng.normal(0, 1, size=(200, 3))
    X[0] = [10, 10, 10]  # 人为异常点
    out2 = solve({"kind": "mahalanobis", "X": X}, {"alpha": 0.01})
    print("mahalanobis outliers:", int(out2["is_outlier"].sum()))

