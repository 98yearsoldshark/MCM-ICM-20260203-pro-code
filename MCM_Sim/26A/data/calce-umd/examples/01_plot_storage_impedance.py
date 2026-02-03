#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例：读取 storage/Impedance 的 CSV，并绘制 Nyquist + Bode 图。

说明：
- CALCE 的 Storage/Impedance CSV 通常无表头，为 5 列数值：
  [freq(Hz), Zreal(Ohm), Zimag(Ohm), |Z|(Ohm), phase(deg)]
  （从文件首行数值的典型含义推断，建议以原页面/论文说明为准）
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def _find_default_csv(root: Path) -> Path:
    candidates = sorted((root / "extracted" / "storage").rglob("*.csv"))
    if not candidates:
        raise FileNotFoundError("未找到任何 storage CSV（extracted/storage/**/*.csv）")
    return candidates[0]


def _load_impedance_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None)
    if df.shape[1] != 5:
        raise ValueError(f"期望 5 列，但读到 {df.shape[1]} 列：{path}")
    df.columns = ["freq_hz", "z_real_ohm", "z_imag_ohm", "z_mod_ohm", "z_phase_deg"]
    # 强制转为数值（容错：无法解析则 NaN）
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="绘制 CALCE Storage Impedance CSV 的 Nyquist/Bode 图")
    parser.add_argument("--csv", type=str, default="", help="指定 CSV 路径（默认自动挑选一个）")
    parser.add_argument("--out", type=str, default="", help="输出图片路径（默认 examples/_outputs/*.png）")
    parser.add_argument("--show", action="store_true", help="显示图像窗口（无 GUI 环境可不启用）")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    csv_path = Path(args.csv) if args.csv else _find_default_csv(root)
    if not csv_path.is_absolute():
        csv_path = (Path.cwd() / csv_path).resolve()

    df = _load_impedance_csv(csv_path)
    if df.empty:
        raise SystemExit(f"[ERROR] CSV 无有效数据：{csv_path}")

    out_dir = (root / "examples" / "_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else (out_dir / f"storage_impedance_{csv_path.stem}.png")
    if not out_path.is_absolute():
        out_path = (Path.cwd() / out_path).resolve()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # Nyquist: x=Zreal, y=-Zimag（更常见的画法）
    ax = axes[0]
    ax.plot(df["z_real_ohm"], -df["z_imag_ohm"], marker="o", linewidth=1)
    ax.set_title("Nyquist")
    ax.set_xlabel("Zreal (Ohm)")
    ax.set_ylabel("-Zimag (Ohm)")
    ax.grid(True, alpha=0.3)

    # Bode |Z|
    ax = axes[1]
    ax.semilogx(df["freq_hz"], df["z_mod_ohm"], marker="o", linewidth=1)
    ax.set_title("|Z| vs f")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("|Z| (Ohm)")
    ax.grid(True, which="both", alpha=0.3)

    # Bode phase
    ax = axes[2]
    ax.semilogx(df["freq_hz"], df["z_phase_deg"], marker="o", linewidth=1)
    ax.set_title("Phase vs f")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (deg)")
    ax.grid(True, which="both", alpha=0.3)

    fig.suptitle(csv_path.name, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)

    print("[OK] csv:", csv_path)
    print("[OK] points:", len(df))
    print("[OK] saved:", out_path)

    if args.show:
        plt.show()
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

