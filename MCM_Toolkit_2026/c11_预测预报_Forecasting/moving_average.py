# -*- coding: utf-8 -*-
# 时间序列：滑动平均/移动平均（简单平滑）
#
# 来源（资料目录，Matlab 版）：
# - 0ys-files/temp/10-数学建模41+30种算法常用代码.../Matlab 41种常用算法代码（免调试）/时间序列-滑动平均代码.txt
# - 0ys-files/temp/10-数学建模41+30种算法常用代码.../Matlab 41种常用算法代码（免调试）/时间序列-移动平均法代码.txt
#
# 说明：
# - “滑动平均”（centered）：以当前点为中心的窗口均值（例如 3 点：y[i-1:i+2]）
# - “移动平均”（trailing）：用过去窗口预测当前（例如 3 点：y[i-3:i]）
# - 与资料版不同：边界处默认填 NaN（而不是 0），更符合数据分析习惯

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def centered_moving_average(y: np.ndarray, window: int) -> np.ndarray:
    """中心滑动平均（odd window）。"""
    y = np.asarray(y, dtype=float).reshape(-1)
    w = int(window)
    if w <= 0 or (w % 2 == 0):
        raise ValueError("window 必须为正奇数（例如 3/5/7）。")
    n = int(y.size)
    half = w // 2
    out = np.full(n, np.nan, dtype=float)
    for i in range(half, n - half):
        out[i] = float(np.mean(y[i - half : i + half + 1]))
    return out


def trailing_moving_average(y: np.ndarray, window: int) -> np.ndarray:
    """向后移动平均（用过去 window 个点的均值；前 window 个点为 NaN）。"""
    y = np.asarray(y, dtype=float).reshape(-1)
    w = int(window)
    if w <= 0:
        raise ValueError("window 必须为正整数。")
    n = int(y.size)
    out = np.full(n, np.nan, dtype=float)
    for i in range(w, n):
        out[i] = float(np.mean(y[i - w : i]))
    return out


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：滑动/移动平均平滑。

    Args:
        data: 1D array-like（时间序列 y）。
        params:
            - windows: list[int]（默认 [3,5]）
            - modes: list[str] in {"centered","trailing"}（默认两者都算）

    Returns:
        dict:
            - centered: dict[window]->ndarray（若开启）
            - trailing: dict[window]->ndarray（若开启）
    """
    params = params or {}
    y = np.asarray(data, dtype=float).reshape(-1)

    windows = params.get("windows", [3, 5])
    windows = [int(w) for w in windows]
    modes = params.get("modes", ["centered", "trailing"])
    modes = [str(m).lower().strip() for m in modes]

    out: Dict[str, Any] = {}
    if "centered" in modes:
        out["centered"] = {int(w): centered_moving_average(y, int(w)) for w in windows if int(w) % 2 == 1}
    if "trailing" in modes:
        out["trailing"] = {int(w): trailing_moving_average(y, int(w)) for w in windows}
    return out


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    y = np.cumsum(rng.normal(size=30)) + 0.2 * np.arange(30)
    out = solve(y, {"windows": [3, 5], "modes": ["centered", "trailing"]})
    print("centered_3 head:", np.round(out["centered"][3][:10], 3).tolist())
    print("trailing_5 head:", np.round(out["trailing"][5][:10], 3).tolist())

