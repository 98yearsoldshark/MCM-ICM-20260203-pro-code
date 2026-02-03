# -*- coding: utf-8 -*-
# 曲线拟合（数学建模拟合常用模板）
#
# 覆盖两类常见需求：
# 1) 多项式拟合：np.polyfit / np.poly1d
# 2) 非线性拟合：scipy.optimize.curve_fit（需要你提供“函数形式”）
#
# 参考来源（资料目录）：
# - 5、30个常用算法Python代码/.../数学建模拟合模型Python代码.txt

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _to_1d_float(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float).reshape(-1)
    if arr.size == 0:
        raise ValueError("x 不能为空。")
    return arr


def _parse_xy(data: Any, params: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """
    从多种输入格式中抽取 (x,y)。

    支持：
    - (x, y)
    - dict: {'x','y'}
    - DataFrame：默认取两列；或通过 params['x_col'], params['y_col'] 指定
    """
    if isinstance(data, (tuple, list)) and len(data) == 2:
        x, y = data
        return _to_1d_float(x), _to_1d_float(y)

    if isinstance(data, dict):
        if "x" not in data or "y" not in data:
            raise ValueError("data 为 dict 时必须包含键 'x' 与 'y'。")
        return _to_1d_float(data["x"]), _to_1d_float(data["y"])

    if isinstance(data, pd.DataFrame):
        x_col = params.get("x_col")
        y_col = params.get("y_col")
        if not x_col or not y_col:
            if data.shape[1] != 2:
                raise ValueError("data 为 DataFrame 且未指定 x_col/y_col 时，必须只有两列。")
            x_col, y_col = data.columns[0], data.columns[1]
        if x_col not in data.columns or y_col not in data.columns:
            raise ValueError(f"x_col/y_col 不存在于 DataFrame：{x_col}, {y_col}")
        return _to_1d_float(data[x_col]), _to_1d_float(data[y_col])

    raise TypeError("不支持的 data 类型：请使用 (x,y)、{'x','y'} 或 DataFrame。")


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = _to_1d_float(y_true)
    y_pred = _to_1d_float(y_pred)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = _to_1d_float(y_true)
    y_pred = _to_1d_float(y_pred)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = _to_1d_float(y_true)
    y_pred = _to_1d_float(y_pred)
    return float(np.mean(np.abs(y_true - y_pred)))


def _model_exponential_base(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """y = b * a^x + c（与资料中的示例一致）。"""
    return b * np.power(a, x) + c


def _model_exponential(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """y = a * exp(b*x) + c。"""
    return a * np.exp(b * x) + c


def _model_power(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """y = a * x^b + c（要求 x>0）。"""
    x = np.asarray(x, dtype=float)
    if np.any(x <= 0):
        raise ValueError("power 拟合要求 x > 0。")
    return a * np.power(x, b) + c


def _model_logistic(x: np.ndarray, L: float, k: float, x0: float, b: float) -> np.ndarray:
    """y = L / (1 + exp(-k*(x-x0))) + b。"""
    x = np.asarray(x, dtype=float)
    return L / (1.0 + np.exp(-k * (x - x0))) + b


_BUILTIN_MODELS: Dict[str, Callable[..., np.ndarray]] = {
    "exp_base": _model_exponential_base,
    "exponential_base": _model_exponential_base,
    "exp": _model_exponential,
    "exponential": _model_exponential,
    "power": _model_power,
    "logistic": _model_logistic,
}


def polynomial_fit(x: np.ndarray, y: np.ndarray, *, degree: int = 3) -> Dict[str, Any]:
    """
    多项式拟合：y ≈ p(x)。

    Returns:
        dict:
            - coeffs: ndarray，长度 degree+1（从高次到低次）
            - poly: np.poly1d，可直接调用 poly(x_new)
            - y_pred: 预测值
            - metrics: r2/rmse/mae
    """
    x = _to_1d_float(x)
    y = _to_1d_float(y)
    if x.shape != y.shape:
        raise ValueError("x 与 y 长度必须一致。")
    deg = int(degree)
    if deg < 0:
        raise ValueError("degree 必须 >= 0。")

    coeffs = np.polyfit(x, y, deg)
    poly = np.poly1d(coeffs)
    y_pred = poly(x)
    return {
        "coeffs": np.asarray(coeffs, dtype=float),
        "poly": poly,
        "y_pred": np.asarray(y_pred, dtype=float),
        "metrics": {"r2": _r2(y, y_pred), "rmse": _rmse(y, y_pred), "mae": _mae(y, y_pred)},
    }


def nonlinear_fit(
    x: np.ndarray,
    y: np.ndarray,
    *,
    func: Callable[..., np.ndarray],
    p0: Optional[Sequence[float]] = None,
    bounds: Union[Tuple[float, float], Tuple[Sequence[float], Sequence[float]]] = (-np.inf, np.inf),
    maxfev: int = 20000,
) -> Dict[str, Any]:
    """
    非线性最小二乘拟合：y ≈ func(x, *params)。
    """
    x = _to_1d_float(x)
    y = _to_1d_float(y)
    if x.shape != y.shape:
        raise ValueError("x 与 y 长度必须一致。")

    popt, pcov = curve_fit(func, x, y, p0=p0, bounds=bounds, maxfev=int(maxfev))
    y_pred = func(x, *popt)
    return {
        "params": np.asarray(popt, dtype=float),
        "cov": np.asarray(pcov, dtype=float),
        "y_pred": np.asarray(y_pred, dtype=float),
        "metrics": {"r2": _r2(y, y_pred), "rmse": _rmse(y, y_pred), "mae": _mae(y, y_pred)},
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：曲线拟合（多项式/非线性）。

    Args:
        data: (x,y) / {'x','y'} / DataFrame
        params:
            - model: str（默认 "polynomial"）
                - "polynomial"：多项式拟合
                - "exp_base"/"exp"/"power"/"logistic"：内置非线性模型
            - degree: int（polynomial 时使用，默认 3）
            - func: callable（非线性自定义函数，形如 func(x, *theta)）
            - p0: list[float] | None（curve_fit 初值）
            - bounds: curve_fit bounds（默认 (-inf, inf)）
            - maxfev: int（默认 20000）
            - x_col/y_col: DataFrame 时使用

    Returns:
        dict:
            - model: str
            - y_pred: ndarray
            - metrics: dict
            - (poly/coeffs) 或 (func/params/cov)
    """
    params = params or {}
    x, y = _parse_xy(data, params)
    if x.shape != y.shape:
        raise ValueError("x 与 y 长度必须一致。")

    model = str(params.get("model", "polynomial")).lower()
    if model in {"poly", "polynomial"}:
        out = polynomial_fit(x, y, degree=int(params.get("degree", 3)))
        return {"model": "polynomial", **out}

    func = params.get("func")
    if func is None:
        if model not in _BUILTIN_MODELS:
            raise ValueError(f"未知 model={model}，请使用 'polynomial' 或提供 params['func']。")
        func = _BUILTIN_MODELS[model]

    out = nonlinear_fit(
        x,
        y,
        func=func,
        p0=params.get("p0"),
        bounds=params.get("bounds", (-np.inf, np.inf)),
        maxfev=int(params.get("maxfev", 20000)),
    )
    return {"model": model, "func": func, **out}


if __name__ == "__main__":
    # Mock Data：资料中的示例（增长趋势）
    x = np.arange(1, 31, 1, dtype=float)
    y = np.array(
        [
            20,
            23,
            26,
            29,
            32,
            35,
            38,
            45,
            53,
            62,
            73,
            86,
            101,
            118,
            138,
            161,
            188,
            220,
            257,
            300,
            350,
            409,
            478,
            558,
            651,
            760,
            887,
            1035,
            1208,
            1410,
        ],
        dtype=float,
    )

    poly_out = solve((x, y), {"model": "polynomial", "degree": 3})
    exp_out = solve((x, y), {"model": "exp_base", "p0": [1.1, 1.0, 0.0]})

    print("[polynomial] degree=3 metrics =", poly_out["metrics"])
    print("[exp_base] params(a,b,c) =", np.round(exp_out["params"], 6))
    print("[exp_base] metrics =", exp_out["metrics"])

