#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 概念演示图：CPL（恒功率负载）下 SOC(t) 的“向下弯曲”来自功率闭合反馈，而非 SOC 定义本身。

你指出的关键“陷阱点”可以用一张图讲清楚：
1) 物理 SOC 定义是电荷积分；若 I 恒定（恒流），SOC(t) 是严格直线；
2) 智能手机更接近恒功率负载（CPL）：I(t)=P/V(t)；
3) 端电压 V(t) 又由 OCV(SOC)、R0、极化 v1 等决定，因此 I(t) 会随 SOC 下降而上升，
   从而使 SOC(t) 在时间轴上呈现“加速掉电”的非线性（向下弯曲）。

为了避免误导，本脚本还对比：
- 名义 OCV（knot 很少 -> 直线段） vs 数据支撑 OCV（knot 更多 -> 更真实的膝点/平台）
在同一恒功率输入下得到的 SOC(t)/I(t) 曲线差异。

输出（不覆盖旧图）：
- src/out_plots/q2/{paper|study}/mechanism_demo/02_soc_time_cpl_vs_cc_<scenario_id>.png
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
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model1_ecm_trace
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt


def _simulate_cpl(
    *,
    scenario_id: str,
    scenarios_path: Path,
    power_path: Path,
    batt_path: Path,
    soc0: float,
    dt_s: float,
):
    raw = load_scenarios_json(scenarios_path)
    sc = materialize_scenario(raw, scenario_id)
    power = PowerParams0.from_json(power_path)
    batt = BatteryParams1ECM.from_json(batt_path)

    # 关键：power_model=None -> 每段功耗常值；在 repeat=true 且单段 schedule 时就是严格 CPL。
    tr = simulate_model1_ecm_trace(sc, power_params=power, power_model=None, battery_params=batt, soc0=float(soc0), dt_s=float(dt_s))
    return tr, batt


def _plot_demo(
    *,
    mode: PlotMode,
    out_path: Path,
    scenario_id: str,
    tr_nom,
    batt_nom: BatteryParams1ECM,
    tr_dat,
    batt_dat: BatteryParams1ECM,
):
    style = apply_style(mode)

    # 时间轴（小时）
    t_nom_h = np.asarray(tr_nom.t_s, dtype=float) / 3600.0
    t_dat_h = np.asarray(tr_dat.t_s, dtype=float) / 3600.0
    soc_nom = np.asarray(tr_nom.soc, dtype=float) * 100.0
    soc_dat = np.asarray(tr_dat.soc, dtype=float) * 100.0
    i_nom = np.asarray(tr_nom.i_A, dtype=float)
    i_dat = np.asarray(tr_dat.i_A, dtype=float)
    p0 = float(tr_dat.p_W[0]) if tr_dat.p_W else float("nan")

    # 恒流基线：取数据支撑版在 t=0 的电流作为 I0，让两者起点斜率可比
    i0 = float(i_dat[0]) if np.isfinite(float(i_dat[0])) else float(np.nanmean(i_dat[:10]))
    # 用“更长的时间轴”画基线（取两条 trace 的最大终止时间）
    t_end = float(max(t_nom_h[-1] if t_nom_h.size else 0.0, t_dat_h[-1] if t_dat_h.size else 0.0))
    t_cc = np.linspace(0.0, t_end, 400)
    # SOC_cc(t) = SOC0 - I0 * t / (3600 Q_Ah)
    # 注意：该基线只用于形态对照（“线性 vs 非线性”），不用于精确数值对齐/终止判据对齐。
    q_ah = float(batt_dat.capacity_Ah)
    soc0 = float(soc_dat[0] / 100.0)
    soc_cc = 100.0 * (soc0 - (i0 * (t_cc * 3600.0)) / (q_ah * 3600.0))
    soc_cc = np.clip(soc_cc, 0.0, 100.0)

    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(10.8, 7.0), sharex=True)
    ax_soc, ax_i = axes

    # SOC(t)
    ax_soc.plot(t_dat_h, soc_dat, color="#845ec2", lw=2.6, label="CPL + data-supported OCV")
    ax_soc.plot(t_nom_h, soc_nom, color="#4C78A8", lw=2.2, alpha=0.7, label="CPL + nominal OCV")
    ax_soc.plot(t_cc, soc_cc, color="#666666", lw=2.0, ls="--", alpha=0.9, label="CC baseline (linear SOC)")
    ax_soc.set_ylim(0.0, 105.0)
    ax_soc.set_yticks([0, 25, 50, 75, 100])
    ax_soc.legend(frameon=False, ncol=2, fontsize=9)
    ax_soc.grid(axis="y", alpha=0.22)

    # I(t)
    ax_i.plot(t_dat_h, i_dat, color="#845ec2", lw=2.6, label="I(t) under CPL (data OCV)")
    ax_i.plot(t_nom_h, i_nom, color="#4C78A8", lw=2.2, alpha=0.7, label="I(t) under CPL (nominal OCV)")
    ax_i.axhline(i0, color="#666666", lw=1.8, ls="--", alpha=0.9, label="CC baseline I0")
    ax_i.legend(frameon=False, ncol=2, fontsize=9)
    ax_i.grid(axis="y", alpha=0.22)

    if mode == "paper":
        ax_soc.set_ylabel("SOC (%)")
        ax_i.set_ylabel("Current I (A)")
        ax_i.set_xlabel("Time (h)")
        fig.suptitle(f"CPL vs CC: why SOC(t) becomes nonlinear (scenario={scenario_id}, P≈{p0:.2f} W)", y=0.98)
    else:
        ax_soc.set_ylabel("SOC（%）")
        ax_i.set_ylabel("电流 I（A）")
        ax_i.set_xlabel("时间（小时）")
        fig.suptitle(f"CPL vs 恒流：SOC(t) 非线性来自功率闭合反馈（场景={scenario_id}，P≈{p0:.2f} W）{style.title_suffix}", y=0.98)

    if style.annotate:
        fig.subplots_adjust(bottom=0.22, top=0.92)
        fig.text(
            0.01,
            0.02,
            "读图要点：\n"
            "- 恒流（CC）下：I 恒定 -> dSOC/dt 恒定 -> SOC(t) 是严格直线。\n"
            "- 恒功率（CPL）下：I(t)=P/V(t)。当 SOC 降低导致 V_term 下降（OCV 膝点 + I·R0 压降 + 极化）时，I 会被迫增大，SOC(t) 因此向下弯曲（加速掉电）。\n"
            "- OCV 曲线越接近真实（更多分段点），越能把低 SOC 膝点导致的加速表现出来；名义 OCV 过粗会“看起来像直尺”。\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q2：CPL vs CC 的 SOC(t) 非线性演示图（不覆盖旧图）")
    ap.add_argument("--scenario", default="S1_video", help="场景 ID（建议选单段 repeat 场景：S1_video/S2_navigation/S3_gaming）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v0.json"), help="功耗参数 JSON（用于常值功耗）")
    ap.add_argument(
        "--phone-nominal",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="名义版电池参数 JSON（OCV knot 少）",
    )
    ap.add_argument(
        "--phone-data",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm_ocv_data_v1.json"),
        help="数据支撑版电池参数 JSON（OCV knot 多）",
    )
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出根目录（默认 src/out_plots）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式：paper/study/both")
    args = ap.parse_args()

    tr_nom, batt_nom = _simulate_cpl(
        scenario_id=str(args.scenario),
        scenarios_path=Path(args.scenarios),
        power_path=Path(args.power),
        batt_path=Path(args.phone_nominal),
        soc0=float(args.soc0),
        dt_s=float(args.dt),
    )
    tr_dat, batt_dat = _simulate_cpl(
        scenario_id=str(args.scenario),
        scenarios_path=Path(args.scenarios),
        power_path=Path(args.power),
        batt_path=Path(args.phone_data),
        soc0=float(args.soc0),
        dt_s=float(args.dt),
    )

    out_root = Path(args.out_dir).expanduser().resolve() / "q2"
    out_sub = "mechanism_demo"

    modes: tuple[str, ...] = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for mode in modes:
        out_dir = ensure_dir(out_root / mode / out_sub)
        out_path = out_dir / f"02_soc_time_cpl_vs_cc_{str(args.scenario)}.png"
        _plot_demo(
            mode=mode,  # type: ignore[arg-type]
            out_path=out_path,
            scenario_id=str(args.scenario),
            tr_nom=tr_nom,
            batt_nom=batt_nom,
            tr_dat=tr_dat,
            batt_dat=batt_dat,
        )
        print(f"[{mode}] wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
