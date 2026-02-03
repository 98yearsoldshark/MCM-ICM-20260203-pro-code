# -*- coding: utf-8 -*-
# 插值模板：1D（线性/样条/拉格朗日）与 2D（griddata）
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../三次样条插值/拉格朗日插值/二维内插值...

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.interpolate import BarycentricInterpolator, CubicSpline, PchipInterpolator, griddata

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def interpolate_1d(
    x: Union[np.ndarray, Sequence[float]],
    y: Union[np.ndarray, Sequence[float]],
    x_new: Union[np.ndarray, Sequence[float]],
    *,
    method: str = "linear",
    extrapolate: bool = True,
) -> np.ndarray:
    """
    一维插值。

    Args:
        x: 原始自变量（n,），需严格递增（建议先排序）。
        y: 原始因变量（n,）。
        x_new: 新自变量点（m,）。
        method: {'linear','cubic_spline','pchip','lagrange'}。
        extrapolate: 是否允许外推（对样条/lagrange 生效；线性用 np.interp 会自动截断到端点）。

    Returns:
        ndarray (m,)：插值结果。
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    x_new = np.asarray(x_new, dtype=float).reshape(-1)
    if x.size != y.size:
        raise ValueError("x 与 y 长度必须一致。")
    if x.size < 2:
        raise ValueError("至少需要 2 个点才能插值。")

    order = np.argsort(x)
    x = x[order]
    y = y[order]

    method = str(method).lower()
    if method == "linear":
        # np.interp 对区间外会截断到端点值（不外推）
        return np.interp(x_new, x, y)
    if method in {"cubic_spline", "spline", "cubic"}:
        cs = CubicSpline(x, y, extrapolate=bool(extrapolate))
        return cs(x_new)
    if method == "pchip":
        pchip = PchipInterpolator(x, y, extrapolate=bool(extrapolate))
        return pchip(x_new)
    if method == "lagrange":
        # Barycentric Lagrange（数值更稳定一些，但高阶仍可能振荡）
        itp = BarycentricInterpolator(x, y)
        y_new = itp(x_new)
        if not extrapolate:
            mask = (x_new < x[0]) | (x_new > x[-1])
            y_new = np.asarray(y_new, dtype=float)
            y_new[mask] = np.nan
        return np.asarray(y_new, dtype=float)
    raise ValueError("method 必须为 linear/cubic_spline/pchip/lagrange 之一。")


def interpolate_2d(
    points: Union[np.ndarray, Sequence[Sequence[float]]],
    values: Union[np.ndarray, Sequence[float]],
    xi: Union[np.ndarray, Sequence[Sequence[float]]],
    *,
    method: str = "linear",
    fill_value: float = np.nan,
) -> np.ndarray:
    """
    二维散点插值（griddata）。

    Args:
        points: (n×2) 已知点坐标。
        values: (n,) 已知点取值。
        xi: (m×2) 待插值点坐标。
        method: {'linear','nearest','cubic'}。
        fill_value: 凸包外的填充值。

    Returns:
        ndarray (m,)：插值结果。
    """
    pts = np.asarray(points, dtype=float)
    vals = np.asarray(values, dtype=float).reshape(-1)
    xi = np.asarray(xi, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points 必须为 (n×2)。")
    if xi.ndim != 2 or xi.shape[1] != 2:
        raise ValueError("xi 必须为 (m×2)。")
    if pts.shape[0] != vals.size:
        raise ValueError("points 行数必须等于 values 长度。")
    return griddata(pts, vals, xi, method=str(method), fill_value=float(fill_value))


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：插值。

    Args:
        data: dict，二选一：
            - 1D：{'x','y','x_new'}
            - 2D：{'points','values','xi'}
        params: 参数：
            - kind: {'1d','2d'}（可选；若不填则自动判断）
            - method: 插值方法
            - extrapolate/fill_value

    Returns:
        dict: {'y_new': ndarray}
    """
    params = params or {}
    if not isinstance(data, dict):
        raise TypeError("data 必须为 dict。")

    kind = params.get("kind")
    if kind is None:
        kind = "1d" if {"x", "y", "x_new"}.issubset(data.keys()) else "2d"
    kind = str(kind).lower()

    if kind == "1d":
        y_new = interpolate_1d(
            data["x"],
            data["y"],
            data["x_new"],
            method=str(params.get("method", "linear")),
            extrapolate=bool(params.get("extrapolate", True)),
        )
    elif kind == "2d":
        y_new = interpolate_2d(
            data["points"],
            data["values"],
            data["xi"],
            method=str(params.get("method", "linear")),
            fill_value=float(params.get("fill_value", np.nan)),
        )
    else:
        raise ValueError("kind 必须为 '1d' 或 '2d'。")

    return {"y_new": np.asarray(y_new, dtype=float)}


if __name__ == "__main__":
    # Mock Data：1D 线性插值
    x = [0, 1, 2, 3]
    y = [0, 1, 4, 9]
    x_new = np.linspace(0, 3, 7)
    out = solve({"x": x, "y": y, "x_new": x_new}, {"kind": "1d", "method": "cubic_spline"})
    print("x_new =", x_new)
    print("y_new =", np.round(out["y_new"], 3))

