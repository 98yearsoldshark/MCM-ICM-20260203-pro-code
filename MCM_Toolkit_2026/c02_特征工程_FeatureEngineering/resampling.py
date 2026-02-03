# -*- coding: utf-8 -*-
# 样本不平衡处理：过采样/欠采样（可选依赖 imbalanced-learn）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import split_xy, to_numpy_1d, to_numpy_2d  # noqa: E402
from MCM_Toolkit_2026.utils.optional_deps import require_package  # noqa: E402


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：不平衡采样（RandomOverSampler/SMOTE/RandomUnderSampler）。

    说明：该模块依赖 `imbalanced-learn`（import 名为 imblearn），未安装时会给出安装提示。

    Args:
        data: DataFrame（含目标列）/ (X,y) / {'X','y'}。
        params: 参数：
            - target_col: str | None（DataFrame 时必填）
            - method: {"random_over","smote","random_under"}（默认 "random_over"）
            - random_state: int（默认 42）
            - sampler_params: dict（传给 sampler）
            - return_df: bool（默认 True；当 X 为 DataFrame 时返回 DataFrame/Series）

    Returns:
        dict:
            - X_resampled, y_resampled
            - sampler: 采样器对象
    """
    params = params or {}

    imblearn_over = require_package("imblearn.over_sampling", pip_name="imbalanced-learn")
    imblearn_under = require_package("imblearn.under_sampling", pip_name="imbalanced-learn")

    xy = split_xy(data, target_col=params.get("target_col"))
    X_raw, y_raw = xy.X, xy.y

    X = to_numpy_2d(X_raw)
    y = to_numpy_1d(y_raw)

    method = str(params.get("method", "random_over")).lower()
    random_state = int(params.get("random_state", 42))
    sampler_params = dict(params.get("sampler_params", {}) or {})

    if method == "random_over":
        Sampler = getattr(imblearn_over, "RandomOverSampler")
        sampler = Sampler(random_state=random_state, **sampler_params)
    elif method == "smote":
        Sampler = getattr(imblearn_over, "SMOTE")
        sampler = Sampler(random_state=random_state, **sampler_params)
    elif method == "random_under":
        Sampler = getattr(imblearn_under, "RandomUnderSampler")
        sampler = Sampler(random_state=random_state, **sampler_params)
    else:
        raise ValueError("params.method 必须为 random_over/smote/random_under 之一。")

    X_res, y_res = sampler.fit_resample(X, y)

    return_df = bool(params.get("return_df", True))
    if return_df and isinstance(X_raw, pd.DataFrame):
        X_res = pd.DataFrame(X_res, columns=list(X_raw.columns))
    if return_df and isinstance(y_raw, pd.Series):
        y_res = pd.Series(y_res, name=y_raw.name)

    return {"X_resampled": X_res, "y_resampled": y_res, "sampler": sampler}


if __name__ == "__main__":
    # Mock Data：二分类不平衡
    import numpy as np

    rng = np.random.default_rng(0)
    X_major = rng.normal(size=(200, 2))
    y_major = np.zeros(200, dtype=int)
    X_minor = rng.normal(loc=2.0, size=(20, 2))
    y_minor = np.ones(20, dtype=int)
    X = np.vstack([X_major, X_minor])
    y = np.hstack([y_major, y_minor])

    try:
        out = solve((X, y), params={"method": "smote"})
        print("before:", (y == 1).sum(), "/", len(y))
        y2 = out["y_resampled"]
        print("after:", (y2 == 1).sum(), "/", len(y2))
    except ImportError as e:
        print(e)

