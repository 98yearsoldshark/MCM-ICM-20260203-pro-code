# -*- coding: utf-8 -*-
# 二分类常用图：ROC/PR/KS/校准曲线/混淆矩阵

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt

from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.data_utils import to_numpy_1d  # noqa: E402


def plot_roc(y_true: Any, y_score: Any, *, ax: Optional[plt.Axes] = None, title: str = "ROC") -> Tuple[plt.Figure, plt.Axes]:
    """绘制 ROC 曲线（并显示 AUC）。"""
    y_true_arr = to_numpy_1d(y_true).astype(int)
    y_score_arr = to_numpy_1d(y_score).astype(float)
    fpr, tpr, _ = roc_curve(y_true_arr, y_score_arr)
    auc = float(roc_auc_score(y_true_arr, y_score_arr))

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig = ax.figure
    ax.plot(fpr, tpr, label=f"AUC={auc:.4f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_xlabel("FPR")
    ax.set_ylabel("TPR")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_pr(y_true: Any, y_score: Any, *, ax: Optional[plt.Axes] = None, title: str = "PR Curve") -> Tuple[plt.Figure, plt.Axes]:
    """绘制 Precision-Recall 曲线（并显示 AP）。"""
    y_true_arr = to_numpy_1d(y_true).astype(int)
    y_score_arr = to_numpy_1d(y_score).astype(float)
    precision, recall, _ = precision_recall_curve(y_true_arr, y_score_arr)
    ap = float(average_precision_score(y_true_arr, y_score_arr))

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig = ax.figure
    ax.plot(recall, precision, label=f"AP={ap:.4f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_ks(y_true: Any, y_score: Any, *, ax: Optional[plt.Axes] = None, title: str = "KS Curve") -> Tuple[plt.Figure, plt.Axes]:
    """绘制 KS 曲线（TPR/FPR 及其差值随阈值变化）。"""
    y_true_arr = to_numpy_1d(y_true).astype(int)
    y_score_arr = to_numpy_1d(y_score).astype(float)
    fpr, tpr, thresholds = roc_curve(y_true_arr, y_score_arr)
    ks = float(np.max(tpr - fpr))

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig = ax.figure
    ax.plot(thresholds[1:], tpr[1:], label="TPR")
    ax.plot(thresholds[1:], fpr[1:], label="FPR")
    ax.plot(thresholds[1:], (tpr - fpr)[1:], label=f"TPR-FPR (KS={ks:.4f})")
    ax.set_xlabel("Threshold")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    # 阈值通常从 1->0，反转更直观
    ax.invert_xaxis()
    return fig, ax


def plot_calibration(
    y_true: Any,
    y_score: Any,
    *,
    n_bins: int = 10,
    ax: Optional[plt.Axes] = None,
    title: str = "Calibration Curve",
) -> Tuple[plt.Figure, plt.Axes]:
    """绘制概率校准曲线。"""
    y_true_arr = to_numpy_1d(y_true).astype(int)
    y_score_arr = to_numpy_1d(y_score).astype(float)

    frac_pos, mean_pred = calibration_curve(y_true_arr, y_score_arr, n_bins=int(n_bins), strategy="uniform")

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    else:
        fig = ax.figure
    ax.plot(mean_pred, frac_pos, marker="o", label="model")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1, label="perfect")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_confusion(
    y_true: Any,
    y_pred: Any,
    *,
    labels: Optional[list] = None,
    ax: Optional[plt.Axes] = None,
    title: str = "Confusion Matrix",
) -> Tuple[plt.Figure, plt.Axes]:
    """绘制混淆矩阵。"""
    y_true_arr = to_numpy_1d(y_true)
    y_pred_arr = to_numpy_1d(y_pred)
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=labels)

    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 4))
    else:
        fig = ax.figure

    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(title)
    return fig, ax


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：生成并（可选）保存图片。

    Args:
        data: dict，包含：
            - y_true: 真实标签（0/1）
            - y_score: 预测概率/分数（可选；绘 ROC/PR/KS/校准时需要）
            - y_pred: 预测标签（可选；绘混淆矩阵时需要）
        params: 参数：
            - kind: {"roc","pr","ks","calibration","confusion"}（必填）
            - save_path: str | None（默认 None；若提供则保存图片）
            - n_bins: int（calibration 用，默认 10）
            - title: str（可选）

    Returns:
        dict: {'fig','ax'}
    """
    params = params or {}
    if not isinstance(data, dict) or "y_true" not in data:
        raise TypeError("data 必须为 dict，并包含 y_true。")

    kind = str(params.get("kind", "")).lower()
    title = str(params.get("title", kind.upper())) if params.get("title") else kind.upper()

    fig_ax: Tuple[plt.Figure, plt.Axes]
    if kind in {"roc", "pr", "ks", "calibration"}:
        if "y_score" not in data:
            raise ValueError(f"kind={kind} 需要 data.y_score。")
        if kind == "roc":
            fig_ax = plot_roc(data["y_true"], data["y_score"], title=title)
        elif kind == "pr":
            fig_ax = plot_pr(data["y_true"], data["y_score"], title=title)
        elif kind == "ks":
            fig_ax = plot_ks(data["y_true"], data["y_score"], title=title)
        else:
            fig_ax = plot_calibration(
                data["y_true"], data["y_score"], n_bins=int(params.get("n_bins", 10)), title=title
            )
    elif kind == "confusion":
        if "y_pred" not in data:
            raise ValueError("kind=confusion 需要 data.y_pred。")
        fig_ax = plot_confusion(data["y_true"], data["y_pred"], title=title)
    else:
        raise ValueError("params.kind 必须为 roc/pr/ks/calibration/confusion 之一。")

    fig, ax = fig_ax
    save_path = params.get("save_path")
    if save_path:
        fig.savefig(str(save_path), bbox_inches="tight", dpi=150)
    return {"fig": fig, "ax": ax}


if __name__ == "__main__":
    # Mock Data：概率比较“好”的模型
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=300)
    y_score = y_true * 0.75 + rng.random(size=300) * 0.25
    out = solve(
        {"y_true": y_true, "y_score": y_score},
        params={"kind": "roc", "title": "ROC Demo", "save_path": "roc_demo.png"},
    )
    plt.close(out["fig"])
    print("saved: roc_demo.png")
