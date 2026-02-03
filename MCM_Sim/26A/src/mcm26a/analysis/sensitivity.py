"""Q3 敏感性分析工具：Spearman 与 PRCC（Partial Rank Correlation Coefficient）。

为何需要（对齐赛题 Q3）：
- 赛题要求在改变“建模假设/参数值/使用波动”后，解释 TTE 等预测如何变化；
- 仅给出 UQ 区间还不够，需要回答“哪些参数最敏感/最关键”，并给出量化排名；
- PRCC 是建模比赛中常用的全局敏感性指标：对变量做秩变换后，计算“控制其它变量后的偏相关”。

实现说明：
- 为避免引入重量依赖，这里只使用 numpy（项目已依赖）；
- 采用“秩变换 + 最小二乘残差 + Pearson 相关”实现 PRCC；
- 该实现面向工程可复现与论文可解释，并非为极端规模优化。
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .stats import pearson_corr


def rankdata(values: Iterable[float]) -> np.ndarray:
    """秩变换（Spearman/PRCC 使用）。

规则：
- 返回从 1 到 n 的秩；
- ties（相等值）用“平均秩”（average rank）。
"""

    xs = np.array(list(values), dtype=float)
    n = xs.size
    if n == 0:
        return np.array([], dtype=float)

    order = np.argsort(xs, kind="mergesort")  # mergesort 稳定，便于可复现
    ranks = np.empty(n, dtype=float)

    i = 0
    cur_rank = 1.0
    while i < n:
        j = i
        v = xs[order[i]]
        while j < n and xs[order[j]] == v:
            j += 1
        # positions [i, j) -> ranks [cur_rank, cur_rank + (j-i) - 1]
        lo = cur_rank
        hi = cur_rank + (j - i) - 1.0
        avg = 0.5 * (lo + hi)
        ranks[order[i:j]] = avg
        cur_rank += float(j - i)
        i = j
    return ranks


def spearman_corr(xs: list[float], ys: list[float]) -> float:
    """Spearman 相关系数：对 x/y 做秩变换后计算 Pearson。"""

    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        raise ValueError("need at least 2 samples")
    rx = rankdata(xs).tolist()
    ry = rankdata(ys).tolist()
    return float(pearson_corr(rx, ry))


def prcc(
    x_by_name: dict[str, list[float]],
    y: list[float],
) -> dict[str, float]:
    """计算每个参数的 PRCC（对秩做偏相关）。

输入：
- x_by_name：参数名 -> 样本列表（长度一致）
- y：输出样本列表（与每个参数列表同长度）

输出：
- 参数名 -> PRCC 值（[-1, 1]）

注意：
- 函数会自动剔除含 NaN/Inf 的样本行；
- 若样本数过少（n <= p+2）将返回 NaN。
"""

    if not x_by_name:
        raise ValueError("x_by_name must be non-empty")
    keys = list(x_by_name.keys())
    n0 = len(y)
    if any(len(x_by_name[k]) != n0 for k in keys):
        raise ValueError("all x columns must have same length as y")

    X = np.column_stack([np.array(x_by_name[k], dtype=float) for k in keys])
    yy = np.array(y, dtype=float)

    m = np.isfinite(yy) & np.all(np.isfinite(X), axis=1)
    X = X[m]
    yy = yy[m]

    n, p = X.shape
    if n <= p + 2:
        return {k: float("nan") for k in keys}

    # rank transform
    Xr = np.column_stack([rankdata(X[:, j]) for j in range(p)])
    yr = rankdata(yy)

    out: dict[str, float] = {}
    ones = np.ones((n, 1), dtype=float)
    for j, name in enumerate(keys):
        if p == 1:
            out[name] = float(pearson_corr(Xr[:, 0].tolist(), yr.tolist()))
            continue

        cols = [c for c in range(p) if c != j]
        Z = np.column_stack([ones, Xr[:, cols]])  # intercept + other ranks

        bx, *_ = np.linalg.lstsq(Z, Xr[:, j], rcond=None)
        by, *_ = np.linalg.lstsq(Z, yr, rcond=None)

        rx = Xr[:, j] - Z @ bx
        ry = yr - Z @ by
        out[name] = float(pearson_corr(rx.tolist(), ry.tolist()))

    return out

