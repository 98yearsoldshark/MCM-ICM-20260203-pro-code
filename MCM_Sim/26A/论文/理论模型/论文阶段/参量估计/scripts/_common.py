#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参量估计公共工具（中文注释版）。

放置位置：
- 本文件位于论文目录 `.../参量估计/scripts/`，用于把“数据抽取→拟合→出图→写表”的流程标准化。

设计目标：
- 不污染 src/ 主代码结构；
- 但允许复用 `MCM_Sim/26A/src/mcm26a/` 的绘图风格与少量数据适配逻辑；
- 产物统一落在 `.../参量估计/` 下，便于论文引用与复现。
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def find_project_root(start: Path) -> Path:
    """从 start 向上寻找包含 `src/mcm26a` 的 26A 项目根目录。"""

    start = Path(start).resolve()
    for p in [start] + list(start.parents):
        if (p / "src" / "mcm26a").exists():
            return p
    raise FileNotFoundError("未找到包含 src/mcm26a 的项目根目录（26A）")


PROJECT_DIR = find_project_root(Path(__file__).resolve())
SRC_DIR = PROJECT_DIR / "src"

# 允许导入 mcm26a（复用绘图风格/部分数据适配逻辑）
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_repo_path(p: str | Path) -> str:
    """把绝对路径压缩成仓库内相对口径：`MCM_Sim/26A/...`。

用于论文材料，避免在文档里出现本机用户名/磁盘路径。
"""

    s = str(Path(p))
    return s.replace(str(PROJECT_DIR), "MCM_Sim/26A")


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"rows 为空，无法写入：{p}")

    # 保持列顺序稳定：按首次出现顺序收集 key
    keys: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)

    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() < 3:
        return float("nan")
    yt = y_true[mask]
    yp = y_pred[mask]
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - float(np.mean(yt))) ** 2))
    return float("nan") if ss_tot <= 0 else float(1.0 - ss_res / ss_tot)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() < 3:
        return float("nan")
    return float(np.sqrt(np.mean((y_true[mask] - y_pred[mask]) ** 2)))


def linear_fit_with_intercept(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """最小二乘拟合 y = a + b x，返回 (a, b)。"""

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return float("nan"), float("nan")
    X = np.column_stack([np.ones(mask.sum()), x[mask]])
    beta, *_ = np.linalg.lstsq(X, y[mask], rcond=None)
    a = float(beta[0])
    b = float(beta[1])
    return a, b


def linear_fit_through_origin(x: np.ndarray, y: np.ndarray) -> float:
    """最小二乘拟合 y = b x（过原点），返回 b。"""

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return float("nan")
    xx = x[mask]
    yy = y[mask]
    den = float(np.sum(xx * xx))
    if den <= 1e-12:
        return float("nan")
    return float(np.sum(xx * yy) / den)


@dataclass(frozen=True)
class FitSummary:
    n: int
    r2: float
    rmse: float


def summarize_fit(y_true: np.ndarray, y_pred: np.ndarray) -> FitSummary:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    return FitSummary(n=int(mask.sum()), r2=r2_score(y_true, y_pred), rmse=rmse(y_true, y_pred))


def finite_rows(*cols: Iterable[float]) -> np.ndarray:
    """返回所有列都 finite 的 mask。"""

    cols2 = [np.asarray(c, dtype=float) for c in cols]
    mask = np.ones_like(cols2[0], dtype=bool)
    for c in cols2:
        mask &= np.isfinite(c)
    return mask
