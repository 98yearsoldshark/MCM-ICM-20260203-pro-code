# -*- coding: utf-8 -*-
# 自回归模型 AR(p)：statsmodels.tsa.ar_model.AutoReg
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../预测与预报类题型参考代码.../基于AR预测模型的未来油价预测代码

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def ar_forecast(
    y: Union[Sequence[float], np.ndarray, pd.Series],
    *,
    lags: Union[int, Sequence[int]] = 1,
    horizon: int = 1,
    trend: str = "c",
) -> Dict[str, Any]:
    """
    拟合 AR(p) 并预测未来 horizon 步。

    Args:
        y: 一维时间序列。
        lags: 滞后阶数 p（int）或滞后集合（如 [1,2,7]）。
        horizon: 预测步数（>=1）。
        trend: 趋势项（'n' 无；'c' 常数；'t' 线性；'ct' 常数+线性）。

    Returns:
        dict:
            - model: 拟合结果对象（AutoRegResults）
            - forecast: ndarray (h,)
            - params: 系数
            - resid: 残差
            - aic/bic
    """
    y_ser = pd.Series(np.asarray(y, dtype=float).reshape(-1))
    h = int(horizon)
    if h < 1:
        raise ValueError("horizon 必须 >= 1。")

    model = AutoReg(y_ser, lags=lags, trend=str(trend), old_names=False)
    res = model.fit()
    start = len(y_ser)
    end = start + h - 1
    forecast = np.asarray(res.predict(start=start, end=end, dynamic=False), dtype=float)
    return {
        "model": res,
        "forecast": forecast,
        "params": res.params.to_dict() if hasattr(res.params, "to_dict") else np.asarray(res.params),
        "resid": np.asarray(res.resid, dtype=float),
        "aic": float(res.aic),
        "bic": float(res.bic),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：AR 预测。

    Args:
        data: 序列或 dict：
            - 直接传入 y
            - dict: {'y': y}
        params: 参数：
            - lags: int | list[int]
            - horizon: int
            - trend: str

    Returns:
        dict: 见 ar_forecast() 返回值。
    """
    params = params or {}
    if isinstance(data, dict):
        y = data.get("y")
    else:
        y = data
    if y is None:
        raise ValueError("data 需要提供序列 y。")
    return ar_forecast(
        y,
        lags=params.get("lags", 1),
        horizon=int(params.get("horizon", 1)),
        trend=str(params.get("trend", "c")),
    )


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    t = np.arange(80)
    y = 0.3 * t + 3 * np.sin(t / 5) + rng.normal(0, 1.0, size=len(t))
    out = solve(y, {"lags": 5, "horizon": 5, "trend": "c"})
    print("AIC =", out["aic"], "BIC =", out["bic"])
    print("forecast =", np.round(out["forecast"], 3))

