"""统计小工具：分位数、相关系数等（避免引入重量依赖）。"""

from __future__ import annotations

import math
from typing import Iterable


def quantile(values: list[float], q: float) -> float:
    """经验分位数（线性插值）。

    - values 会被当作无序样本；函数内部会排序（原列表不会修改）。
    - q 取值范围 [0, 1]。
    """

    if not values:
        raise ValueError("values must be non-empty")
    if q < 0.0 or q > 1.0:
        raise ValueError("q must be within [0, 1]")

    xs = sorted(float(x) for x in values)
    n = len(xs)
    if n == 1:
        return xs[0]

    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def mean(values: Iterable[float]) -> float:
    xs = [float(x) for x in values]
    if not xs:
        raise ValueError("values must be non-empty")
    return sum(xs) / len(xs)


def pearson_corr(xs: list[float], ys: list[float]) -> float:
    """皮尔逊相关系数（Pearson correlation）。"""

    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    n = len(xs)
    if n < 2:
        raise ValueError("need at least 2 samples")

    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = 0.0
    syy = 0.0
    sxy = 0.0
    for x, y in zip(xs, ys):
        dx = x - mx
        dy = y - my
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy

    if sxx <= 0.0 or syy <= 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)

