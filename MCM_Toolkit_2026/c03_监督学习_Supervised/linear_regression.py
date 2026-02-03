# -*- coding: utf-8 -*-
# 线性回归 / 多项式回归（基于 scikit-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import get_param, split_xy, to_numpy_1d, to_numpy_2d


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：线性回归/多项式回归拟合与评估。

    Args:
        data: 支持：
            - DataFrame（包含目标列；需要 params.target_col）
            - (X, y) 二元组
            - dict {'X','y'}
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）
            - degree: int（默认 1；>1 表示多项式回归）
            - include_bias: bool（PolynomialFeatures 参数，默认 False）
            - fit_intercept: bool（LinearRegression 参数，默认 True）
            - statsmodels_summary: bool（默认 False；True 返回 OLS summary 文本）

    Returns:
        dict:
            - model: 训练好的模型
            - poly: PolynomialFeatures 或 None
            - metrics: dict（R2/MAE/MSE/RMSE）
            - y_pred: 测试集预测
            - y_true: 测试集真实值
            - ols_summary: str | None
    """
    params = params or {}
    target_col = params.get("target_col")
    xy = split_xy(data, target_col=target_col)

    X = xy.X
    y = xy.y

    X_arr = to_numpy_2d(X)
    y_arr = to_numpy_1d(y)

    test_size = float(get_param(params, "test_size", 0.2))
    random_state = int(get_param(params, "random_state", 42))

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=test_size, random_state=random_state
    )

    degree = int(get_param(params, "degree", 1))
    include_bias = bool(get_param(params, "include_bias", False))
    fit_intercept = bool(get_param(params, "fit_intercept", True))

    poly = None
    if degree > 1:
        poly = PolynomialFeatures(degree=degree, include_bias=include_bias)
        X_train_fit = poly.fit_transform(X_train)
        X_test_fit = poly.transform(X_test)
    else:
        X_train_fit = X_train
        X_test_fit = X_test

    model = LinearRegression(fit_intercept=fit_intercept)
    model.fit(X_train_fit, y_train)

    y_pred = model.predict(X_test_fit)

    metrics = {
        "r2": float(r2_score(y_test, y_pred)),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "mse": float(mean_squared_error(y_test, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
    }

    ols_summary = None
    if bool(get_param(params, "statsmodels_summary", False)):
        try:
            import statsmodels.api as sm

            X_sm = sm.add_constant(X_train_fit)
            est = sm.OLS(y_train, X_sm).fit()
            ols_summary = str(est.summary())
        except Exception:
            ols_summary = None

    return {
        "model": model,
        "poly": poly,
        "metrics": metrics,
        "y_pred": y_pred,
        "y_true": y_test,
        "ols_summary": ols_summary,
    }


if __name__ == "__main__":
    # Mock Data：一元线性回归（可把 degree=2 试试多项式回归）
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 10, size=200)
    y = 2.0 * x + 1.0 + rng.normal(scale=1.0, size=200)
    df = pd.DataFrame({"x": x, "y": y})

    out = solve(df, params={"target_col": "y", "degree": 1})
    print(out["metrics"])
