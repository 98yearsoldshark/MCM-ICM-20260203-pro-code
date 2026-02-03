#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例：读取 CALCE Anomaly Detection 的 Dataset2.mat，并绘制容量随循环数的衰减曲线。

已验证（本仓库当前文件）：
- mat 内包含变量 `Lot1`（23 个样本）
- 每个样本为 (N,2) 数组：第 1 列为 cycle index（从 1 开始），第 2 列为归一化容量（约 0.95~1.00）
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat


def _default_mat(root: Path) -> Path:
    return root / "extracted" / "anomaly" / "Dataset2" / "Dataset2.mat"


def _pick_mat_key(mat: dict) -> str:
    # 优先 Lot1，其次第一个非 __ 的 key
    if "Lot1" in mat:
        return "Lot1"
    keys = [k for k in mat.keys() if not k.startswith("__")]
    if not keys:
        raise ValueError("mat 文件中没有可用变量（仅包含 __header__/__version__/__globals__）")
    return keys[0]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="绘制 Anomaly Dataset2 的容量衰减曲线（.mat）")
    parser.add_argument("--mat", type=str, default="", help="指定 Dataset2.mat 路径")
    parser.add_argument("--out", type=str, default="", help="输出图片路径（默认 examples/_outputs/）")
    parser.add_argument("--show", action="store_true", help="显示图像窗口（无 GUI 环境可不启用）")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    mat_path = Path(args.mat) if args.mat else _default_mat(root)
    if not mat_path.is_absolute():
        mat_path = (Path.cwd() / mat_path).resolve()

    if not mat_path.exists():
        raise SystemExit(f"[ERROR] 找不到 mat 文件：{mat_path}")

    mat = loadmat(mat_path)
    key = _pick_mat_key(mat)
    lot = mat[key]

    # 兼容 (n,1) object array / (n,) object array
    lot = np.asarray(lot).reshape(-1)
    curves = []
    for i, elem in enumerate(lot):
        arr = np.asarray(elem)
        if arr.ndim != 2 or arr.shape[1] != 2:
            raise ValueError(f"样本 {i} 形状异常：{arr.shape}（期望 (N,2)）")
        curves.append(arr)

    out_dir = (root / "examples" / "_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else (out_dir / "anomaly_dataset2_capacity_fade.png")
    if not out_path.is_absolute():
        out_path = (Path.cwd() / out_path).resolve()

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    for i, arr in enumerate(curves):
        ax.plot(arr[:, 0], arr[:, 1], alpha=0.5, linewidth=1, label=None)

    # 如果所有曲线 cycle 轴一致，则额外画一条平均曲线
    same_x = all(np.array_equal(curves[0][:, 0], c[:, 0]) for c in curves[1:])
    if same_x:
        x = curves[0][:, 0]
        y_mean = np.mean([c[:, 1] for c in curves], axis=0)
        ax.plot(x, y_mean, color="black", linewidth=2, label="mean")
        ax.legend()

    ax.set_title(f"{mat_path.name} / {key}  (n={len(curves)})")
    ax.set_xlabel("Cycle index")
    ax.set_ylabel("Normalized capacity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)

    # 控制台摘要
    lens = [c.shape[0] for c in curves]
    y_all = np.concatenate([c[:, 1] for c in curves])
    print("[OK] mat:", mat_path)
    print("[OK] key:", key)
    print("[OK] samples:", len(curves), "len(min/median/max)=", (min(lens), int(np.median(lens)), max(lens)))
    print("[OK] capacity range:", float(y_all.min()), "~", float(y_all.max()))
    print("[OK] saved:", out_path)

    if args.show:
        plt.show()
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

