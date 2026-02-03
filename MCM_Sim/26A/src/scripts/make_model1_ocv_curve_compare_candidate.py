#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Model-1 的 OCV–SOC 曲线“对照候选图”（不覆盖旧图）。

动机（修正你指出的“直线陷阱”）：
- phone_default_v1_ecm.json 只有 4 个分段点，画出来必然像几段直线，这是“名义/占位”版本；
- 在恒功率负载（CPL）下，I=P/V，V 又由 OCV(SOC) 决定，因此 OCV 形状会显著影响 SOC(t) 的非线性；
- 为了论文表述更严谨，我们提供“名义 OCV vs 数据支撑 OCV”的一张对照图，便于说明升级路径。

输出：
- src/out_plots/model1/{paper|study}/battery/06_ocv_curve_compare_candidate.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams1ECM
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt


def _plot_compare(*, mode: PlotMode, out_path: Path, batt_nom: BatteryParams1ECM, batt_data: BatteryParams1ECM) -> None:
    style = apply_style(mode)

    soc = np.linspace(0.0, 1.0, 500)
    ocv_nom = np.array([batt_nom.ocv.ocv_v(float(s)) for s in soc], dtype=float)
    ocv_dat = np.array([batt_data.ocv.ocv_v(float(s)) for s in soc], dtype=float)

    fig, ax = plt.subplots(figsize=(9.2, 4.6))

    # 配色：让“数据支撑版”更显眼；名义版做弱化以强调其“占位/粗糙”属性。
    ax.plot(soc, ocv_dat, color="#845ec2", lw=2.6, label="Data-supported OCV(SOC)")
    ax.plot(soc, ocv_nom, color="#4C78A8", lw=2.2, alpha=0.65, label="Nominal OCV(SOC)")

    # knot 点：让读者知道“分段线性”的节点数量差异
    k_soc_n = [float(x) for x, _ in batt_nom.ocv.points]
    k_v_n = [float(y) for _, y in batt_nom.ocv.points]
    k_soc_d = [float(x) for x, _ in batt_data.ocv.points]
    k_v_d = [float(y) for _, y in batt_data.ocv.points]
    ax.scatter(k_soc_d, k_v_d, s=18, color="#845ec2", alpha=0.95, zorder=3, label="Data knots")
    ax.scatter(k_soc_n, k_v_n, s=18, color="#4C78A8", alpha=0.75, zorder=3, label="Nominal knots")

    v_cut = float(batt_data.v_cut_V)
    ax.axhline(v_cut, color="#666666", ls="--", lw=1.2, alpha=0.8, label=f"V_cut={v_cut:.2f}V")

    if mode == "paper":
        ax.set_xlabel("SOC (0–1)")
        ax.set_ylabel("Open-circuit voltage OCV (V)")
        ax.set_title("OCV–SOC curve: nominal vs data-supported (candidate)")
    else:
        ax.set_xlabel("SOC（0~1）")
        ax.set_ylabel("开路电压 OCV（V）")
        ax.set_title(f"OCV-SOC 曲线对照（候选，修正“直线陷阱”）{style.title_suffix}")

    ax.set_xlim(0.0, 1.0)
    y_min = float(min(ocv_nom.min(), ocv_dat.min(), min(k_v_n), min(k_v_d))) - 0.05
    y_max = float(max(ocv_nom.max(), ocv_dat.max(), max(k_v_n), max(k_v_d))) + 0.05
    ax.set_ylim(y_min, y_max)
    ax.legend(frameon=False, ncol=2, loc="lower right")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "读图要点：\n"
            "- 名义版 knot 很少，因此看起来像几段直线；它适合“跑通框架”，但不适合支撑精细机理叙事。\n"
            "- 数据支撑版包含更多 knot（来源于公开数据校准），能更好刻画低 SOC 膝点与平台。\n"
            "- 在恒功率负载（CPL）下，I=P/V_term，OCV 形状会通过功率闭合反馈影响 SOC(t) 的非线性。\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 Model-1 的 OCV–SOC 曲线对照候选图（不覆盖旧图）")
    ap.add_argument(
        "--phone-nominal",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="名义版电池参数 JSON（OCV 分段点较少）",
    )
    ap.add_argument(
        "--phone-data",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm_ocv_data_v1.json"),
        help="数据支撑版电池参数 JSON（OCV 分段点较多）",
    )
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出根目录（默认 src/out_plots）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式：paper/study/both")
    args = ap.parse_args()

    batt_nom = BatteryParams1ECM.from_json(Path(args.phone_nominal))
    batt_dat = BatteryParams1ECM.from_json(Path(args.phone_data))

    out_root = Path(args.out_dir).expanduser().resolve()

    modes: tuple[str, ...] = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for mode in modes:
        out_dir = ensure_dir(out_root / "model1" / mode / "battery")
        out_path = out_dir / "06_ocv_curve_compare_candidate.png"
        _plot_compare(mode=mode, out_path=out_path, batt_nom=batt_nom, batt_data=batt_dat)  # type: ignore[arg-type]
        print(f"[{mode}] wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

