#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-01：生成“数据支撑版”OCV 曲线候选图（不覆盖论文材料旧图）。

说明（面向赛题要求）：
- 赛题要求连续时间机理模型（ODE/DAE）为核心；数据仅用于参数估计与验证。
- 在 ECM 中，OCV(SOC) 是电池端电压方程的关键映射；真实工程常用“查表+插值”表示。
- 本脚本从某个电池参数 JSON 中读取 OCV 的分段线性点（通常由公开数据集/文献提取），
  生成更可信的 OCV 图，并同时导出对应的 CSV 数据版本，便于核对。

输出策略：
- 默认将图片/CSV 写到 Q1材料对应目录的 other/ 下（文件名含 candidate，不覆盖 figure.png）。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from mcm26a.battery import BatteryParams1ECM2RC
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig

import matplotlib.pyplot as plt


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A


def _write_csv(path: Path, *, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1-01：生成 OCV 曲线候选图（数据支撑版，不覆盖旧图）")
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_q1fit_2rc_v9_hyst_scale075.json"),
        help="电池参数 JSON（需包含 battery.ecm.ocv_curve.points 与 V_cut_V）",
    )
    ap.add_argument(
        "--out-dir",
        default=str(
            ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "01-电池OCV曲线与截止电压" / "other"
        ),
        help="输出目录（默认写入 Q1材料/01/.../other/，不覆盖 figure.png）",
    )
    ap.add_argument(
        "--mode",
        default="paper",
        choices=("paper", "study", "both"),
        help="输出模式：paper/study/both",
    )
    args = ap.parse_args()

    phone = Path(args.phone).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    batt = BatteryParams1ECM2RC.from_json(phone)
    pts = list(batt.ocv.points)

    soc = np.linspace(0.0, 1.0, 400)
    ocv = np.array([batt.ocv.ocv_v(float(s)) for s in soc], dtype=float)
    v_cut = float(batt.v_cut_V)

    # 数据版本（候选）：采样曲线 + knot 点
    _write_csv(
        out_dir / "data_candidate_ocv_curve.csv",
        header=["soc", "ocv_V", "v_cut_V"],
        rows=[[float(s), float(v), float(v_cut)] for s, v in zip(soc.tolist(), ocv.tolist())],
    )
    _write_csv(
        out_dir / "data_candidate_ocv_knots.csv",
        header=["soc_knot", "ocv_knot_V"],
        rows=[[float(s), float(v)] for s, v in pts],
    )

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for mode in modes:
        style = apply_style(mode)  # sets mpl rcParams

        fig, ax = plt.subplots(figsize=(8.2, 4.6))
        c0 = PALETTE_SKIP_GRADIENT[0]
        ax.plot(soc, ocv, color=c0, lw=2.2, label="OCV(SOC)")
        # knot 点（让读者看到“分段线性”并非随意画线）
        k_soc = [float(x) for x, _ in pts]
        k_v = [float(y) for _, y in pts]
        ax.scatter(k_soc, k_v, s=18, color=c0, alpha=0.95, zorder=3, label="分段点")

        ax.axhline(v_cut, color="gray", ls="--", lw=1.2, alpha=0.8, label=f"V_cut={v_cut:.2f}V")

        ax.set_xlabel("SOC（0~1）")
        ax.set_ylabel("开路电压 OCV（V）")
        ax.set_title(f"OCV-SOC 曲线（数据支撑版）{style.title_suffix}")
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(min(ocv.min(), min(k_v)) - 0.05, max(ocv.max(), max(k_v)) + 0.05)
        ax.legend(frameon=False, loc="lower right")

        if style.annotate:
            fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
            fig.text(
                0.01,
                0.02,
                "说明：本图从电池参数配置文件中读取 OCV 的分段线性点（knot），并对 SOC 做线性插值。\n"
                "在 ECM 中，OCV(SOC) 用于闭合连续时间状态方程；V_cut 用于定义关机/耗尽事件（TTE）。\n"
                f"配置来源：{phone.name}",
                ha="left",
                va="bottom",
                fontsize=9,
            )
        else:
            fig.tight_layout()

        out_png = out_dir / f"figure_candidate_ocv_{phone.stem}_{mode}.png"
        savefig(fig, out_png, mode=mode)  # type: ignore[arg-type]
        plt.close(fig)

    print(f"[OK] OCV 候选图与数据已生成到：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

