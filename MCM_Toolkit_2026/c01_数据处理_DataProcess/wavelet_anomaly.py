# -*- coding: utf-8 -*-
# 小波多尺度异常点检测（基于 CWT）：适合“突变/尖峰/奇异点”位置定位
#
# 参考来源（资料目录）：
# - 6、按赛题类别划分的常用算法代码/42-1 .../数据处理类题型参考代码.../利用多尺度小波分解侦测时间序列中奇异点位置
#
# 思路（简化）：
# 1) 对序列做连续小波变换 CWT（多尺度）
# 2) 将各尺度系数 |coef| 聚合成一个“异常评分曲线”
# 3) 在评分曲线上找峰值（peaks）
#
# 依赖：scipy.signal

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np
from scipy.signal import find_peaks

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def wavelet_anomaly_score(
    y: Union[np.ndarray, Sequence[float]],
    *,
    widths: Optional[Sequence[int]] = None,
    aggregate: str = "sum_abs",
) -> np.ndarray:
    """
    计算多尺度小波异常评分曲线。

    Args:
        y: 一维序列。
        widths: 尺度列表（默认 1..20）。
        aggregate: 聚合方式：
            - 'sum_abs': Σ_s |coef_s(t)|
            - 'max_abs': max_s |coef_s(t)|

    Returns:
        score: ndarray (n,)
    """
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    if y_arr.size < 3:
        return np.zeros_like(y_arr)

    # 默认用较小尺度更适合抓“尖峰/突变”；若想抓更平滑的大尺度变化，可把 widths 扩大
    if widths is None:
        widths = list(range(1, 7))
    widths_arr = np.asarray(list(widths), dtype=int)
    widths_arr = widths_arr[widths_arr > 0]
    if widths_arr.size == 0:
        raise ValueError("widths 必须包含正整数尺度。")

    # SciPy 的 signal.cwt 已在 1.12 标记为 deprecated，避免未来版本移除导致不可用；
    # 这里用“Ricker 小波 + 卷积”的方式手写一个简化版 CWT。
    def ricker_wavelet(points: int, a: float) -> np.ndarray:
        a = float(a)
        if a <= 0:
            raise ValueError("a 必须 > 0。")
        # 参考：Mexican hat / Ricker wavelet 的常用表达式
        x = np.arange(points, dtype=float) - (points - 1) / 2.0
        wsq = a * a
        xsq = x * x
        A = 2.0 / (np.sqrt(3.0 * a) * (np.pi ** 0.25))
        return A * (1.0 - xsq / wsq) * np.exp(-xsq / (2.0 * wsq))

    coefs = []
    n = y_arr.size
    for w in widths_arr:
        # 小波长度通常取 ~10*w；并保证为奇数，便于对齐
        L = int(max(3, 10 * int(w)))
        if L % 2 == 0:
            L += 1
        wav = ricker_wavelet(L, float(w))
        # 卷积得到该尺度系数（取 same 保持长度一致）
        coefs.append(np.convolve(y_arr, wav, mode="same"))
    abs_coef = np.abs(np.vstack(coefs))  # (n_scales×n)

    aggregate = str(aggregate).lower()
    if aggregate == "sum_abs":
        score = np.sum(abs_coef, axis=0)
    elif aggregate == "max_abs":
        score = np.max(abs_coef, axis=0)
    else:
        raise ValueError("aggregate 必须为 sum_abs 或 max_abs。")

    return np.asarray(score, dtype=float)


def detect_wavelet_anomalies(
    y: Union[np.ndarray, Sequence[float]],
    *,
    widths: Optional[Sequence[int]] = None,
    aggregate: str = "sum_abs",
    threshold_method: str = "zscore",
    zscore_thr: float = 3.0,
    quantile_thr: float = 0.99,
    min_distance: int = 1,
) -> Dict[str, Any]:
    """
    检测异常点（峰值）。

    Args:
        y: 一维序列。
        widths: 尺度列表（默认 1..20）。
        aggregate: 评分聚合方式。
        threshold_method: 阈值方式：
            - 'zscore': score > mean + zscore_thr*std
            - 'quantile': score > quantile(score, quantile_thr)
        zscore_thr: z-score 阈值（默认 3）。
        quantile_thr: 分位数阈值（默认 0.99）。
        min_distance: 峰值之间的最小间隔（点数）。

    Returns:
        dict:
            - score: (n,) 异常评分
            - peaks: 异常点索引（0-based）
            - peak_scores: 对应峰值评分
            - threshold: 使用的阈值
    """
    score = wavelet_anomaly_score(y, widths=widths, aggregate=aggregate)
    if score.size == 0:
        return {"score": score, "peaks": np.array([], dtype=int), "peak_scores": np.array([], dtype=float), "threshold": np.nan}

    threshold_method = str(threshold_method).lower()
    if threshold_method == "zscore":
        mu = float(np.mean(score))
        sigma = float(np.std(score, ddof=0))
        thr = mu + float(zscore_thr) * sigma
    elif threshold_method == "quantile":
        thr = float(np.quantile(score, float(quantile_thr)))
    else:
        raise ValueError("threshold_method 必须为 zscore 或 quantile。")

    peaks, props = find_peaks(score, height=thr, distance=int(min_distance))
    peak_scores = props.get("peak_heights", np.array([], dtype=float))
    return {"score": score, "peaks": peaks.astype(int), "peak_scores": np.asarray(peak_scores, dtype=float), "threshold": thr}


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：小波异常检测。

    Args:
        data: 序列或 dict：
            - 直接传入 y
            - dict: {'y': y}
        params: 参数：
            - widths: list[int] | None
            - aggregate: 'sum_abs' | 'max_abs'
            - threshold_method: 'zscore' | 'quantile'
            - zscore_thr: float
            - quantile_thr: float
            - min_distance: int

    Returns:
        dict: 见 detect_wavelet_anomalies()。
    """
    params = params or {}
    if isinstance(data, dict):
        y = data.get("y")
    else:
        y = data
    if y is None:
        raise ValueError("data 需要提供序列 y。")
    return detect_wavelet_anomalies(
        y,
        widths=params.get("widths"),
        aggregate=str(params.get("aggregate", "sum_abs")),
        threshold_method=str(params.get("threshold_method", "zscore")),
        zscore_thr=float(params.get("zscore_thr", 3.0)),
        quantile_thr=float(params.get("quantile_thr", 0.99)),
        min_distance=int(params.get("min_distance", 1)),
    )


if __name__ == "__main__":
    # Mock Data：带两个突变的序列
    rng = np.random.default_rng(0)
    n = 300
    y = np.sin(np.linspace(0, 12 * np.pi, n)) + rng.normal(0, 0.1, size=n)
    y[80] += 3.0
    y[200] -= 2.5

    # 用较小尺度更容易定位尖峰位置
    out = solve(y, {"widths": [1, 2, 3], "threshold_method": "quantile", "quantile_thr": 0.995, "min_distance": 10})
    print("peaks =", out["peaks"])
    print("peak_scores =", np.round(out["peak_scores"], 3))
