#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 机理演示图：把“低 SOC 内阻上升 + I^2R0 损耗”与“极化电压 v1 的短时响应”画出来。

用途：
- 这不是用来替代 5.2.1 的主图（SOC0/温度单因素对照），而是给论文叙事提供“机理证据图”。
- 目标是让评委看到：我们的曲线不是纯拟合，而是由电-热-极化机理自然推出。

图中想支持的三类论断（可按需取用）：
1) 极低 SOC “加速掉电/提前欠压关机”：
   - 低 SOC 下 OCV 下降 + R0(SOC) 上升 -> 为满足同一功率需求，电流 I 增大；
   - 内部损耗 I^2 R0 增大，等价于“更多化学能变成热”，从而缩短可用续航。
2) “加速/拐点与 SOC(0) 的位置关系”：
   - 在同一负载下，曲线拐点对应的 SOC 区间相对固定；
   - SOC(0) 越低，越早进入该区间（因此拐点在时间轴上更早出现）。
3) 放电初期的非线性波动：
   - 由极化支路状态 v1 的建立/松弛引起；在恒定功率闭合下会反馈到 I(t)，进而影响 SOC(t) 的局部斜率。

说明：
- 这里不修改仿真核心返回结构（避免影响 Q1/Q3）；我们通过已输出的 (SOC, T, V_term, P) 反推 I 与 v1：
  I(t) = P(t) / V_term(t)
  v1(t) = OCV(SOC) - I(t) * R0_eff(SOC,T) - V_term(t)

输出：
- src/out_plots/q2/{paper|study}/mechanism_demo/
  - 01_mechanism_low_soc_polarization_<scenario_id>.png
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Scenario, load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging_trace
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt


def _parse_float_list(s: str) -> list[float]:
    out: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    if not out:
        raise ValueError("列表参数不能为空")
    return out


def _override_ambient_temp(sc: Scenario, temp_c: float) -> Scenario:
    schedule = tuple(replace(seg, ambient_temp_c=float(temp_c)) for seg in sc.schedule)
    return replace(sc, schedule=schedule)


def _override_batt_initial_temp(batt: BatteryParams3Aging, temp_c: float) -> BatteryParams3Aging:
    tmin = float(batt.temp_min_C)
    tmax = float(batt.temp_max_C)
    if float(temp_c) < tmin:
        tmin = float(temp_c) - 5.0
    if float(temp_c) > tmax:
        tmax = float(temp_c) + 5.0
    return replace(batt, t0_C=float(temp_c), temp_min_C=float(tmin), temp_max_C=float(tmax))


def _simulate_trace(
    sc: Scenario,
    *,
    soc0: float,
    temp_c: float,
    power1: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    dt_s: float,
    seed: int,
):
    sc_t = _override_ambient_temp(sc, temp_c=float(temp_c))
    batt_t = _override_batt_initial_temp(batt, temp_c=float(temp_c))

    pm = StatefulPowerModel1(power1, seed=int(seed))
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    tr = simulate_model3_aging_trace(
        sc_t,
        power_params=power0_dummy,
        power_model=pm,
        battery_params=batt_t,
        soc0=float(soc0),
        dt_s=float(dt_s),
    )
    return tr, batt_t


def _derive_iv1_r0(
    tr,
    *,
    batt: BatteryParams3Aging,
) -> dict[str, np.ndarray]:
    """从 trace 反推 I(t)、v1(t)、R0_eff(t)、I^2R0(t) 等。"""

    t_s = np.asarray(tr.t_s, dtype=float)
    t_h = t_s / 3600.0
    t_min = t_s / 60.0
    soc = np.asarray(tr.soc, dtype=float)
    soc_pct = soc * 100.0
    temp_c = np.asarray(tr.temp_C, dtype=float)
    v_term = np.asarray(tr.v_term_V, dtype=float)
    p = np.asarray(tr.p_W, dtype=float)
    r0_g = np.asarray(tr.r0_growth_frac, dtype=float)

    ocv = np.asarray([float(batt.ocv.ocv_v(float(s))) for s in soc], dtype=float)
    r0 = np.asarray(
        [float(batt.effective_r0_ohm(soc=float(s), temp_C=float(t), r0_growth_frac=float(g))) for s, t, g in zip(soc, temp_c, r0_g)],
        dtype=float,
    )

    # I = P / V_term（功率闭合）；注意 v_term 可能在终止附近非常接近 0，做数值保护。
    with np.errstate(divide="ignore", invalid="ignore"):
        i = np.where(v_term > 1e-9, p / v_term, np.nan)

    # v1 = OCV - I*R0 - V_term（由端电压方程反推极化状态）
    v1 = ocv - i * r0 - v_term
    p_r0 = i * i * r0
    with np.errstate(divide="ignore", invalid="ignore"):
        loss_ratio = np.where(p > 1e-12, p_r0 / p, np.nan)

    return {
        "t_s": t_s,
        "t_h": t_h,
        "t_min": t_min,
        "soc": soc,
        "soc_pct": soc_pct,
        "temp_C": temp_c,
        "v_term_V": v_term,
        "p_W": p,
        "ocv_V": ocv,
        "r0_ohm": r0,
        "i_A": i,
        "v1_V": v1,
        "p_r0_W": p_r0,
        "loss_ratio": loss_ratio,
    }


def _plot_mechanism(
    *,
    mode: PlotMode,
    out_path: Path,
    sc_id: str,
    temp_c: float,
    soc0_list: list[float],
    sims: dict[float, dict[str, np.ndarray]],
    mech: dict[str, np.ndarray],
):
    style = apply_style(mode)

    # 2x2：左上（SOC 叠加），右上（I vs SOC），左下（R0&loss vs SOC），右下（v1&I 初期）
    fig = plt.figure(figsize=(13.2, 8.4) if mode == "paper" else (13.6, 9.2))
    gs = fig.add_gridspec(2, 2, wspace=0.22, hspace=0.30)
    ax_soc = fig.add_subplot(gs[0, 0])
    ax_i_soc = fig.add_subplot(gs[0, 1])
    ax_r0 = fig.add_subplot(gs[1, 0])
    ax_v1 = fig.add_subplot(gs[1, 1])

    # 配色：与 5.2.1 主图保持一致（四条 SOC0 线）
    colors_soc = ["#099F2D", "#005800", "#33618F", "#86AEE1"]

    scenario_title_en_map = {
        "S0_standby": "Standby / Light Background",
        "S1_video": "Video Playback / Streaming",
        "S2_navigation": "Navigation (GPS + Map Data)",
        "S3_gaming": "Gaming (High CPU/GPU Load)",
        "S4_mixed_day": "Mixed Use (Typical Day)",
        "S5_burst_recovery": "Burst Load → Rest (Recovery Demo)",
    }
    sc_title_en = scenario_title_en_map.get(str(sc_id), str(sc_id))

    # ---------- (a) SOC vs time：不同 SOC0 ----------
    max_t = 0.0
    for soc0, c in zip(soc0_list, colors_soc):
        r = sims[float(soc0)]
        t_h = np.asarray(r["t_h"], dtype=float)
        soc_pct = np.asarray(r["soc_pct"], dtype=float)
        max_t = max(max_t, float(t_h[-1]) if t_h.size else 0.0)
        ax_soc.plot(t_h, soc_pct, color=c, lw=2.4, label=f"SOC0={soc0*100:.0f}%")
        if t_h.size:
            ax_soc.plot([t_h[-1]], [soc_pct[-1]], marker="o", color=c, ms=5.0)

    ax_soc.set_xlim(0.0, max_t * 1.02 if max_t > 0 else 1.0)
    ax_soc.set_ylim(0.0, 105.0)
    ax_soc.set_yticks([0, 25, 50, 75, 100])
    ax_soc.legend(frameon=False, loc="upper right")

    # 标出“进入低 SOC 区间”的参考线（可与 R0(SOC) 的拐点对应）
    ax_soc.axhline(20.0, color="#666666", linestyle="--", linewidth=1.0, alpha=0.45)

    if mode == "paper":
        ax_soc.set_xlabel("Time (h)")
        ax_soc.set_ylabel("SOC (%)")
        ax_soc.set_title(f"(a) SOC vs time ({sc_title_en}, T_amb={temp_c:.0f}°C)")
    else:
        ax_soc.set_xlabel("时间（小时）")
        ax_soc.set_ylabel("SOC（%）")
        ax_soc.set_title(f"(a) SOC–时间：不同初始电量对照（{sc_id}，T_amb={temp_c:.0f}°C）{style.title_suffix}")

    # ---------- (b) I vs SOC：低 SOC 电流抬升（功率闭合下更明显） ----------
    ax_i_soc.plot(
        mech["soc_pct"],
        mech["i_A"],
        color="#845ec2",
        lw=2.4,
        label="I(t)=P/V_term",
    )
    # SOC 随放电下降：把 SOC 轴反向更符合直觉（与(c)一致）。
    ax_i_soc.set_xlim(100.0, 0.0)
    if mode == "paper":
        ax_i_soc.set_xlabel("SOC (%)")
        ax_i_soc.set_ylabel("Current I (A)")
        ax_i_soc.set_title("(b) Current increases at low SOC (power closure)")
    else:
        ax_i_soc.set_xlabel("SOC（%）")
        ax_i_soc.set_ylabel("电流 I（A）")
        ax_i_soc.set_title(f"(b) 低 SOC 电流抬升（功率闭合）{style.title_suffix}")
    ax_i_soc.legend(frameon=False, loc="upper left")

    # ---------- (c) R0_eff 与 I^2R0 损耗比：支持“低 SOC 加速掉电”的机理解释 ----------
    ax_r0.plot(mech["soc_pct"], mech["r0_ohm"], color="#d62728", lw=2.4, label="R0_eff (ohm)")
    ax_r0.set_xlim(100.0, 0.0)  # SOC 从高到低（放电方向）
    if mode == "paper":
        ax_r0.set_xlabel("SOC (%)")
        ax_r0.set_ylabel("R0_eff (ohm)")
        ax_r0.set_title("(c) R0_eff rises at low SOC → higher I and I²R0 loss")
    else:
        ax_r0.set_xlabel("SOC（%）")
        ax_r0.set_ylabel("等效内阻 R0_eff（Ω）")
        ax_r0.set_title(f"(c) 低 SOC 内阻上升与 I²R0 损耗{style.title_suffix}")

    ax_r0b = ax_r0.twinx()
    ax_r0b.plot(mech["soc_pct"], mech["loss_ratio"] * 100.0, color="#4e8397", lw=2.2, alpha=0.95, label="I²R0 / P (%)")
    if mode == "paper":
        ax_r0b.set_ylabel("I²R0 / P (%)")
    else:
        ax_r0b.set_ylabel("内部损耗占比 I²R0 / P（%）")

    # 合并图例（两条轴）
    h1, l1 = ax_r0.get_legend_handles_labels()
    h2, l2 = ax_r0b.get_legend_handles_labels()
    ax_r0.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")

    # ---------- (d) 初期极化：v1 与 I 的短时响应（放电初期非线性） ----------
    t_min = mech["t_min"]
    m = t_min <= 10.0
    ax_v1.plot(t_min[m], mech["v1_V"][m] * 1000.0, color="#2ca02c", lw=2.4, label="v1 (mV)")
    if mode == "paper":
        ax_v1.set_xlabel("Time (min)")
        ax_v1.set_ylabel("Polarization v1 (mV)")
        ax_v1.set_title("(d) Early transient: polarization v1 builds up")
    else:
        ax_v1.set_xlabel("时间（分钟）")
        ax_v1.set_ylabel("极化电压 v1（mV）")
        ax_v1.set_title(f"(d) 放电初期极化建立（导致局部非线性）{style.title_suffix}")

    ax_v1b = ax_v1.twinx()
    ax_v1b.plot(t_min[m], mech["i_A"][m], color="#ff7f0e", lw=2.2, alpha=0.9, label="I (A)")
    if mode == "paper":
        ax_v1b.set_ylabel("Current I (A)")
    else:
        ax_v1b.set_ylabel("电流 I（A）")

    h1, l1 = ax_v1.get_legend_handles_labels()
    h2, l2 = ax_v1b.get_legend_handles_labels()
    ax_v1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")

    if style.annotate:
        fig.subplots_adjust(bottom=0.18)
        fig.text(
            0.01,
            0.02,
            "学习提示：\n"
            "- TTE（Time-to-Empty，耗尽时间）：从当前 SOC0 开始到首次触发欠压/不可供电边界的剩余时间。\n"
            "- variant（变体）：在同一场景框架下，只改少量条件（如信号/亮度/制式）形成对照。\n"
            "- 本图使用恒定使用场景（repeat=true 的单段 schedule），并固定功耗随机种子（CRN），只比较机理差异。\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        # twin axes + tight_layout 经常导致标签被裁剪/挤压；论文图用手动留白更稳定。
        fig.subplots_adjust(left=0.07, right=0.985, top=0.95, bottom=0.10, wspace=0.22, hspace=0.30)

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q2 机理演示：低 SOC 加速 + 极化 v1（paper/study）")
    ap.add_argument("--scenario", default="S1_video", help="场景 ID（建议选恒定使用：S1_video/S2_navigation/S3_gaming）")
    ap.add_argument("--soc0-list", default="1.0,0.75,0.5,0.25", help="SOC0 列表（逗号分隔）")
    ap.add_argument("--soc0-mech", type=float, default=1.0, help="用于机理面板(b/c/d)的 SOC0（默认 100%）")
    ap.add_argument("--temp", type=float, default=20.0, help="统一环境温度（°C，默认 20）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒），默认 2s（用于更平滑的初期瞬态）")
    ap.add_argument("--seed", type=int, default=1, help="功耗随机种子（固定代表性轨迹）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging_r0curve_low_soc_v1.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出根目录（默认 src/out_plots）")
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    raw = load_scenarios_json(Path(args.scenarios))
    sc = materialize_scenario(raw, str(args.scenario))

    soc0_list = _parse_float_list(str(args.soc0_list))
    soc0_mech = float(args.soc0_mech)
    temp_c = float(args.temp)

    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))

    out_root = Path(args.out_dir).expanduser().resolve() / "q2"
    out_sub = "mechanism_demo"

    modes: list[PlotMode] = ["paper", "study"] if not str(args.mode).strip() else [str(args.mode).strip()]  # type: ignore[list-item]
    for mode in modes:
        out_dir = ensure_dir(out_root / str(mode) / out_sub)

        sims: dict[float, dict[str, np.ndarray]] = {}
        for soc0 in soc0_list:
            tr, _batt_t = _simulate_trace(
                sc,
                soc0=float(soc0),
                temp_c=temp_c,
                power1=power1,
                batt=batt,
                dt_s=float(args.dt),
                seed=int(args.seed),
            )
            sims[float(soc0)] = {
                "t_h": np.asarray(tr.t_s, dtype=float) / 3600.0,
                "soc_pct": np.asarray(tr.soc, dtype=float) * 100.0,
            }

        tr_mech, batt_t = _simulate_trace(
            sc,
            soc0=soc0_mech,
            temp_c=temp_c,
            power1=power1,
            batt=batt,
            dt_s=float(args.dt),
            seed=int(args.seed),
        )
        mech = _derive_iv1_r0(tr_mech, batt=batt_t)

        outp = out_dir / f"01_mechanism_low_soc_polarization_{sc.scenario_id}.png"
        _plot_mechanism(
            mode=mode,  # type: ignore[arg-type]
            out_path=outp,
            sc_id=sc.scenario_id,
            temp_c=temp_c,
            soc0_list=soc0_list,
            sims=sims,
            mech=mech,
        )
        print(f"[{mode}] wrote: {outp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
