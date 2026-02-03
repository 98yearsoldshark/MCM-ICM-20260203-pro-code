# -*- coding: utf-8 -*-
# 灰色预测 GM(1,1)：适用于“小样本、贫信息”的单变量短期预测
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../预测与预报类题型参考代码.../离散灰色预测模型.../改进灰色马尔科夫模型...

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def gm11_fit(x0: Union[np.ndarray, list], *, alpha: float = 0.5) -> Dict[str, Any]:
    """
    拟合 GM(1,1) 模型参数。

    模型形式（经典）：
        x0(k) + a*z1(k) = b,  k=2..n
        z1(k) = alpha*x1(k) + (1-alpha)*x1(k-1)
        x1(k) = Σ_{i=1..k} x0(i)

    Args:
        x0: 原始序列（n,），要求 n>=4，且通常为正序列（非严格）。
        alpha: 背景值系数，常用 0.5。

    Returns:
        dict:
            - a, b: 模型参数
            - x0: 原序列
            - x1: 1-AGO 序列
            - z1: 背景序列（n-1,）
    """
    x0_arr = np.asarray(x0, dtype=float).reshape(-1)
    if x0_arr.size < 4:
        raise ValueError("GM(1,1) 建议 n>=4。")
    if not (0.0 < float(alpha) < 1.0):
        raise ValueError("alpha 必须在 (0,1) 内。")

    x1 = np.cumsum(x0_arr)
    z1 = alpha * x1[1:] + (1.0 - alpha) * x1[:-1]

    # 最小二乘估计 [a,b]
    B = np.column_stack([-z1, np.ones_like(z1)])
    Y = x0_arr[1:]
    # 用 lstsq 避免显式求逆
    theta, *_ = np.linalg.lstsq(B, Y, rcond=None)
    a = float(theta[0])
    b = float(theta[1])

    return {"a": a, "b": b, "x0": x0_arr, "x1": x1, "z1": z1, "alpha": float(alpha)}


def gm11_predict(fit: Dict[str, Any], *, horizon: int = 0) -> Dict[str, Any]:
    """
    使用拟合结果进行预测（含样本内拟合 + horizon 步外推）。

    Args:
        fit: gm11_fit() 的返回值。
        horizon: 预测步数（>=0）。

    Returns:
        dict:
            - x0_hat: 对原序列的拟合/预测（n+h,）
            - x1_hat: 对累加序列的拟合/预测（n+h,）
            - residual: 样本内残差（n,），第 1 个点残差设为 0（因为模型从 k=2 开始）
            - rel_error: 相对误差（n,）
            - metrics: dict（C,P 等简单精度指标）
    """
    a = float(fit["a"])
    b = float(fit["b"])
    x0 = np.asarray(fit["x0"], dtype=float).reshape(-1)
    n = x0.size

    h = int(horizon)
    if h < 0:
        raise ValueError("horizon 必须 >= 0。")

    # time response of x1
    k = np.arange(1, n + h + 1, dtype=float)  # 1..n+h
    if abs(a) < 1e-12:
        # a≈0 时退化为近似线性：x1_hat(k)=x0(1)+b*(k-1)
        x1_hat = x0[0] + b * (k - 1.0)
    else:
        c = x0[0] - b / a
        x1_hat = c * np.exp(-a * (k - 1.0)) + b / a

    # inverse AGO
    x0_hat = np.empty_like(x1_hat)
    x0_hat[0] = x0[0]
    x0_hat[1:] = np.diff(x1_hat)

    residual = np.zeros(n, dtype=float)
    residual[1:] = x0[1:] - x0_hat[1:n]
    rel_error = np.zeros(n, dtype=float)
    denom = np.where(np.abs(x0) < 1e-12, 1.0, x0)
    rel_error[1:] = residual[1:] / denom[1:]

    # 经典 GM(1,1) 后验差检验：C、P
    # C = S2 / S1, 其中 S1=原序列标准差，S2=残差标准差
    x0_std = float(np.std(x0, ddof=1)) if n > 1 else 0.0
    res_std = float(np.std(residual[1:], ddof=1)) if n > 2 else 0.0
    C = res_std / x0_std if x0_std > 0 else np.nan

    # 小误差概率：|e(k) - mean(e)| < 0.6745*S1 的比例
    e = residual[1:]
    e_mean = float(np.mean(e)) if e.size else 0.0
    threshold = 0.6745 * x0_std
    P = float(np.mean(np.abs(e - e_mean) < threshold)) if e.size and x0_std > 0 else np.nan

    return {
        "x0_hat": x0_hat,
        "x1_hat": x1_hat,
        "residual": residual,
        "rel_error": rel_error,
        "metrics": {"C": C, "P": P, "x0_std": x0_std, "residual_std": res_std},
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：GM(1,1) 拟合 + 预测。

    Args:
        data: 序列（list/ndarray）或 dict：
            - 直接传入 x0
            - dict: {'x0': x0}
        params: 参数：
            - alpha: 背景值系数（默认 0.5）
            - horizon: 预测步数（默认 0）

    Returns:
        dict:
            - a,b,alpha
            - x0_hat/x1_hat/residual/rel_error/metrics
    """
    params = params or {}
    if isinstance(data, dict):
        x0 = data.get("x0")
    else:
        x0 = data
    if x0 is None:
        raise ValueError("data 需要提供序列 x0。")

    fit = gm11_fit(x0, alpha=float(params.get("alpha", 0.5)))
    pred = gm11_predict(fit, horizon=int(params.get("horizon", 0)))
    return {**fit, **pred}


if __name__ == "__main__":
    # Mock Data：某指标 6 年数据，预测未来 3 年
    x0 = [120, 132, 145, 160, 178, 195]
    out = solve(x0, {"alpha": 0.5, "horizon": 3})
    print("a =", out["a"], "b =", out["b"])
    print("x0_hat =", np.round(out["x0_hat"], 3))
    print("C =", out["metrics"]["C"], "P =", out["metrics"]["P"])

