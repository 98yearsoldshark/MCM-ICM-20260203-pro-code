# -*- coding: utf-8 -*-
# 指数平滑（Holt / Holt-Winters）：趋势/季节分解型短期预测（statsmodels）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def holt_winters_forecast(
    y: Union[Sequence[float], np.ndarray, pd.Series],
    *,
    horizon: int = 1,
    trend: Optional[str] = "add",
    seasonal: Optional[str] = None,
    seasonal_periods: Optional[int] = None,
    damped_trend: bool = False,
) -> Dict[str, Any]:
    """
    Holt-Winters 指数平滑预测。

    Args:
        y: 一维时间序列。
        horizon: 预测步数（>=1）。
        trend: {'add','mul',None}。
        seasonal: {'add','mul',None}。
        seasonal_periods: 季节周期（如月度数据一年季节=12）。
        damped_trend: 是否阻尼趋势。

    Returns:
        dict:
            - model: 拟合结果对象（statsmodels HoltWintersResults）
            - forecast: ndarray (h,)
            - fitted: 样本内拟合值 ndarray (n,)
            - resid: 残差 ndarray (n,)
    """
    y_ser = pd.Series(np.asarray(y, dtype=float).reshape(-1))
    h = int(horizon)
    if h < 1:
        raise ValueError("horizon 必须 >= 1。")

    model = ExponentialSmoothing(
        y_ser,
        trend=trend,
        damped_trend=bool(damped_trend),
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
    )
    res = model.fit(optimized=True)
    forecast = np.asarray(res.forecast(h), dtype=float)
    fitted = np.asarray(res.fittedvalues, dtype=float)
    resid = np.asarray(y_ser.values - fitted, dtype=float)
    return {"model": res, "forecast": forecast, "fitted": fitted, "resid": resid}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：指数平滑预测。

    Args:
        data: 序列或 dict：
            - 直接传入 y
            - dict: {'y': y}
        params: 参数：
            - horizon: int
            - trend/seasonal/seasonal_periods/damped_trend

    Returns:
        dict: 见 holt_winters_forecast() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        y = data.get("y")
    else:
        y = data
    if y is None:
        raise ValueError("data 需要提供序列 y。")
    return holt_winters_forecast(
        y,
        horizon=int(params.get("horizon", 1)),
        trend=params.get("trend", "add"),
        seasonal=params.get("seasonal"),
        seasonal_periods=params.get("seasonal_periods"),
        damped_trend=bool(params.get("damped_trend", False)),
    )


if __name__ == "__main__":
    # Mock Data：带季节项的序列（周期=12）
    rng = np.random.default_rng(1)
    t = np.arange(60)
    season = 10 * np.sin(2 * np.pi * t / 12)
    y = 0.2 * t + season + rng.normal(0, 2.0, size=len(t))

    out = solve(y, {"horizon": 6, "trend": "add", "seasonal": "add", "seasonal_periods": 12})
    print("forecast =", np.round(out["forecast"], 3))

