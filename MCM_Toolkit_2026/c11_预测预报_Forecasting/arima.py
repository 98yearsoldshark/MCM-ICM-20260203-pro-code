# -*- coding: utf-8 -*-
# ARIMA 时间序列预测（statsmodels）
#
# 说明：美赛中常见“短期趋势 + 随机波动”的序列预测，可先做差分/对数等再建模。

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def arima_forecast(
    y: Union[Sequence[float], np.ndarray, pd.Series],
    *,
    order: Tuple[int, int, int] = (1, 0, 0),
    horizon: int = 1,
    trend: Optional[str] = None,
) -> Dict[str, Any]:
    """
    拟合 ARIMA 并预测未来 horizon 步。

    Args:
        y: 一维时间序列。
        order: (p,d,q)。
        horizon: 预测步数（>=1）。
        trend: 趋势项（None/'n'/'c'/'t'/'ct' 等，见 statsmodels 文档）。

    Returns:
        dict:
            - model: 拟合后的结果对象（statsmodels ARIMAResults）
            - forecast: 预测均值（h,）
            - conf_int: 置信区间 DataFrame（h×2）
            - aic/bic: 信息准则
            - resid: 残差（n,）
    """
    y_ser = pd.Series(np.asarray(y, dtype=float).reshape(-1))
    h = int(horizon)
    if h < 1:
        raise ValueError("horizon 必须 >= 1。")

    model = ARIMA(y_ser, order=tuple(order), trend=trend)
    res = model.fit()

    f = res.get_forecast(steps=h)
    forecast = np.asarray(f.predicted_mean, dtype=float)
    conf_int = f.conf_int()
    return {
        "model": res,
        "forecast": forecast,
        "conf_int": conf_int,
        "aic": float(res.aic),
        "bic": float(res.bic),
        "resid": np.asarray(res.resid, dtype=float),
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：ARIMA 预测。

    Args:
        data: 序列或 dict：
            - 直接传入 y
            - dict: {'y': y}
        params: 参数：
            - order: (p,d,q)
            - horizon: int
            - trend: str | None

    Returns:
        dict: 见 arima_forecast() 返回值（其中 model 为 statsmodels 对象）。
    """
    params = params or {}
    if isinstance(data, dict):
        y = data.get("y")
    else:
        y = data
    if y is None:
        raise ValueError("data 需要提供序列 y。")
    return arima_forecast(
        y,
        order=tuple(params.get("order", (1, 0, 0))),
        horizon=int(params.get("horizon", 1)),
        trend=params.get("trend"),
    )


if __name__ == "__main__":
    # Mock Data：构造一个带趋势的序列
    rng = np.random.default_rng(0)
    t = np.arange(60)
    y = 0.5 * t + 5 * np.sin(t / 6) + rng.normal(0, 1.5, size=len(t))

    out = solve(y, {"order": (2, 1, 2), "horizon": 5, "trend": "n"})
    print("AIC =", out["aic"], "BIC =", out["bic"])
    print("forecast =", np.round(out["forecast"], 3))
    print("conf_int =\\n", out["conf_int"].round(3))

