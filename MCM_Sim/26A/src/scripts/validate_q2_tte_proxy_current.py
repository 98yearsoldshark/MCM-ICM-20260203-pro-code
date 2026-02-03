#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：构造“更像 TTE 真值”的代理对照链条（基于观测电流 I_obs）。

动机（对应 260131-19:32-Q2任务集.md 的 3.4）：
- 赛题 Q2 要求把 TTE 预测与“观测到的或合理的行为”做对照。
- 公开手机数据往往只有短时聚合（如 AndroWatts ~30s），缺少“整机放电到关机”的完整轨迹。
- 但 AndroWatts 提供了电池放电电流（BATTERY_DISCHARGE_RATE_UAS）与初始 SOC/温度，
  我们可以用它构造一个“电池端更接近真值的代理对照”：

  1) 以观测电流 I_obs 作为外生输入（更接近底层电池观测量）；
  2) 使用公开老化状态表的 OCV(SOC)+SOH（MCM2026_battery_state_table.csv）作为电池状态锚点；
  3) 对比两个 TTE：
     - 代理上界（常流到 SOC=0）：t_empty_cc ≈ soc0 * Q_eff / I_obs
     - 机理模型（含欠压截止）：t_cutoff_model（到 V_cut 或 SOC_min 的首次到达时间）

这样可以用“代理真值/上界”解释：为何会出现“还剩 10% 却突然关机”（提前欠压，SOC_end>0）。

输出：
- out_reports/q2/validation_tte_proxy_current/：
  - tte_proxy_current.csv
- out_plots/q2/{paper|study}/observed_tte_proxy_current/：
  - 01_tte_vs_soh_proxy.png
  - 02_soc_end_vs_soh.png
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import AgingECMState, BatteryParams3Aging, aging_ecm_derivatives
from mcm26a.observed.andro_watts import build_cases, load_aggregated_csv
from mcm26a.observed.mcm2026_battery_state import apply_battery_state_to_model3, load_battery_state_table
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _pick_cases_by_percentiles(cases, percentiles: list[float]) -> list[int]:
    ps = np.array([c.obs.total_w for c in cases], dtype=float)
    ps = np.where(np.isfinite(ps), ps, np.nan)
    out_idx: list[int] = []
    used: set[int] = set()
    for p in percentiles:
        target = float(np.nanpercentile(ps, float(p)))
        dist = np.abs(ps - target)
        order = np.argsort(dist)
        pick = None
        for i in order.tolist():
            if int(i) not in used:
                pick = int(i)
                break
        if pick is None:
            pick = int(order[0]) if order.size else 0
        used.add(int(pick))
        out_idx.append(int(pick))
    return out_idx


def _i_obs_from_row(row: dict[str, object]) -> float:
    # I_obs_A = BATTERY_DISCHARGE_RATE_UAS * 1e-6
    v = row.get("BATTERY_DISCHARGE_RATE_UAS", None)
    try:
        x = float(v) if v is not None else float("nan")
    except Exception:
        x = float("nan")
    if not np.isfinite(x):
        return float("nan")
    return float(max(0.0, x * 1e-6))


def _rk4_step_current(
    state: AgingECMState,
    *,
    dt_s: float,
    i_A: float,
    ambient_temp_C: float,
    params: BatteryParams3Aging,
) -> AgingECMState:
    """对 (SOC, v1, T, cap_loss, r0_growth, r1_growth) 做 RK4（恒流驱动）。"""

    dt = float(dt_s)
    i = float(max(0.0, i_A))

    def p_of(s: AgingECMState) -> float:
        # 恒流下的外部负载功率：P = V_term * I
        ocv = float(params.ocv.ocv_v(s.soc))
        r0 = float(params.effective_r0_ohm(soc=s.soc, temp_C=s.temp_C, r0_growth_frac=s.r0_growth_frac))
        v_term = float(ocv - s.v1_V - i * r0)
        return max(0.0, float(v_term) * i)

    def f(s: AgingECMState) -> tuple[float, float, float, float, float, float]:
        p = p_of(s)
        d_soc, d_v1, d_t, d_cap, d_r0, d_r1, _out = aging_ecm_derivatives(
            s, p_W=p, ambient_temp_C=float(ambient_temp_C), params=params
        )
        return float(d_soc), float(d_v1), float(d_t), float(d_cap), float(d_r0), float(d_r1)

    k1 = f(state)
    s2 = AgingECMState(
        soc=state.soc + 0.5 * dt * k1[0],
        v1_V=state.v1_V + 0.5 * dt * k1[1],
        temp_C=state.temp_C + 0.5 * dt * k1[2],
        cap_loss_frac=state.cap_loss_frac + 0.5 * dt * k1[3],
        r0_growth_frac=state.r0_growth_frac + 0.5 * dt * k1[4],
        r1_growth_frac=state.r1_growth_frac + 0.5 * dt * k1[5],
    )
    k2 = f(s2)
    s3 = AgingECMState(
        soc=state.soc + 0.5 * dt * k2[0],
        v1_V=state.v1_V + 0.5 * dt * k2[1],
        temp_C=state.temp_C + 0.5 * dt * k2[2],
        cap_loss_frac=state.cap_loss_frac + 0.5 * dt * k2[3],
        r0_growth_frac=state.r0_growth_frac + 0.5 * dt * k2[4],
        r1_growth_frac=state.r1_growth_frac + 0.5 * dt * k2[5],
    )
    k3 = f(s3)
    s4 = AgingECMState(
        soc=state.soc + dt * k3[0],
        v1_V=state.v1_V + dt * k3[1],
        temp_C=state.temp_C + dt * k3[2],
        cap_loss_frac=state.cap_loss_frac + dt * k3[3],
        r0_growth_frac=state.r0_growth_frac + dt * k3[4],
        r1_growth_frac=state.r1_growth_frac + dt * k3[5],
    )
    k4 = f(s4)

    new_soc = state.soc + (dt / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
    new_v1 = state.v1_V + (dt / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
    new_t = state.temp_C + (dt / 6.0) * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])
    new_cap = state.cap_loss_frac + (dt / 6.0) * (k1[3] + 2.0 * k2[3] + 2.0 * k3[3] + k4[3])
    new_r0 = state.r0_growth_frac + (dt / 6.0) * (k1[4] + 2.0 * k2[4] + 2.0 * k3[4] + k4[4])
    new_r1 = state.r1_growth_frac + (dt / 6.0) * (k1[5] + 2.0 * k2[5] + 2.0 * k3[5] + k4[5])

    new_soc = min(1.0, max(0.0, float(new_soc)))
    new_t = params.clamp_temp_C(float(new_t))
    new_cap = min(float(params.cap_loss_max_frac), max(0.0, float(new_cap)))
    new_r0 = min(float(params.r_growth_max_frac), max(0.0, float(new_r0)))
    new_r1 = min(float(params.r_growth_max_frac), max(0.0, float(new_r1)))

    return AgingECMState(
        soc=float(new_soc),
        v1_V=float(new_v1),
        temp_C=float(new_t),
        cap_loss_frac=float(new_cap),
        r0_growth_frac=float(new_r0),
        r1_growth_frac=float(new_r1),
    )


def _v_term_from_state(state: AgingECMState, *, i_A: float, params: BatteryParams3Aging) -> float:
    ocv = float(params.ocv.ocv_v(state.soc))
    r0 = float(params.effective_r0_ohm(soc=state.soc, temp_C=state.temp_C, r0_growth_frac=state.r0_growth_frac))
    return float(ocv - state.v1_V - float(i_A) * r0)


def _simulate_tte_current(
    *,
    batt: BatteryParams3Aging,
    soc0: float,
    temp0_C: float,
    cap_loss0: float,
    r0_growth0: float,
    r1_growth0: float,
    i_A: float,
    dt_s: float,
    ambient_temp_C: float,
    max_steps: int = 10_000_000,
) -> tuple[float | None, str, float]:
    """恒流驱动下的 TTE（到 V_cut 或 SOC_min）。返回 (tte_h, status, soc_end)。"""

    state = AgingECMState(
        soc=float(soc0),
        v1_V=0.0,
        temp_C=float(temp0_C),
        cap_loss_frac=float(cap_loss0),
        r0_growth_frac=float(r0_growth0),
        r1_growth_frac=float(r1_growth0),
    )
    t_s = 0.0

    for _ in range(int(max_steps)):
        if state.soc <= float(batt.soc_min):
            return (t_s / 3600.0), "soc_min", float(state.soc)

        v0 = _v_term_from_state(state, i_A=float(i_A), params=batt)
        if v0 <= float(batt.v_cut_V):
            return (t_s / 3600.0), "cutoff", float(state.soc)

        new_state = _rk4_step_current(state, dt_s=float(dt_s), i_A=float(i_A), ambient_temp_C=float(ambient_temp_C), params=batt)
        v1 = _v_term_from_state(new_state, i_A=float(i_A), params=batt)

        if v1 <= float(batt.v_cut_V):
            # 线性插值估计命中时间（dt 较大时可显著提升 TTE 精度）
            denom = float(v0 - v1)
            frac = 0.0 if denom <= 1e-12 else float((v0 - float(batt.v_cut_V)) / denom)
            frac = min(1.0, max(0.0, frac))
            t_s += float(dt_s) * frac
            soc_hit = float(state.soc + (new_state.soc - state.soc) * frac)
            return (t_s / 3600.0), "cutoff", soc_hit

        t_s += float(dt_s)
        state = new_state

    return None, "not_depleted", float(state.soc)


def _plot_tte_vs_soh(rows: list[dict[str, object]], *, mode: PlotMode) -> object:
    import matplotlib.pyplot as plt
    import pandas as pd

    style = apply_style(mode)
    df = pd.DataFrame(rows)
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    df["battery_state_label"] = pd.Categorical(df["battery_state_label"], categories=order, ordered=True)

    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    for k, (load_label, g) in enumerate(df.groupby("load_label", observed=False)):
        g = g.sort_values("battery_state_label")
        x = g["SOH"].to_numpy(dtype=float)
        y_model = g["tte_model_h"].to_numpy(dtype=float)
        y_proxy = g["tte_proxy_cc_h"].to_numpy(dtype=float)
        color = colors[k % len(colors)]
        ax.plot(x, y_model, marker="o", ms=4.0, lw=2.0, color=color, label=f"{load_label}（模型：到欠压/下限）")
        ax.plot(x, y_proxy, lw=1.6, color=color, alpha=0.55, linestyle="--", label=f"{load_label}（代理：常流到 0）")

    ax.set_xlabel("SOH（容量健康度）")
    ax.set_ylabel("TTE（小时）")
    ax.set_title(f"代理对照：恒流 TTE（上界） vs 欠压截止 TTE（模型）{style.title_suffix}")
    ax.set_xlim(0.58, 1.02)
    ax.legend(frameon=False, loc="best", fontsize=9)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：虚线“代理 TTE”是常流近似到 SOC=0 的上界（t≈soc0·Q_eff/I_obs），\n"
            "实线“模型 TTE”考虑欠压截止 V_cut，因此通常更短，并可能出现 SOC_end>0（提前关机证据）。\n"
            "该对照用于弥补公开手机数据缺少完整放电曲线的问题：以 I_obs 作为更底层的观测输入构造可复现的 TTE 代理。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_soc_end(rows: list[dict[str, object]], *, mode: PlotMode) -> object:
    import matplotlib.pyplot as plt
    import pandas as pd

    style = apply_style(mode)
    df = pd.DataFrame(rows)
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    df["battery_state_label"] = pd.Categorical(df["battery_state_label"], categories=order, ordered=True)

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    colors = ["#4C78A8", "#F58518", "#54A24B"]
    for k, (load_label, g) in enumerate(df.groupby("load_label", observed=False)):
        g = g.sort_values("battery_state_label")
        x = g["SOH"].to_numpy(dtype=float)
        y = g["soc_end"].to_numpy(dtype=float)
        color = colors[k % len(colors)]
        ax.plot(x, y, marker="o", ms=4.0, lw=2.0, color=color, label=str(load_label))

    ax.set_xlabel("SOH（容量健康度）")
    ax.set_ylabel("终止时剩余 SOC")
    ax.set_title(f"提前关机证据：恒流驱动下的 SOC_end vs SOH{style.title_suffix}")
    ax.set_xlim(0.58, 1.02)
    ax.set_ylim(-0.02, 0.25)
    ax.legend(frameon=False, loc="best")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：若欠压提前关机，SOC_end 往往显著大于 0（例如 5%~15%）。\n"
            "SOH 越低（更老化），在同一电流负载下越容易提前欠压，因此 SOC_end 往往更高。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 代理 TTE 对照（恒流 I_obs 驱动）")
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "validation_tte_proxy_current"))
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"))
    ap.add_argument(
        "--andro-csv",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
    )
    ap.add_argument(
        "--battery-state-table",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
    )
    ap.add_argument(
        "--battery-datasets",
        default="3",
        help="使用哪些 battery_dataset（逗号分隔，例如 3 或 3,5）。默认只用 3（更接近手机电池容量量级）。",
    )
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"))
    ap.add_argument("--dt", type=float, default=10.0, help="恒流仿真步长（秒）")
    ap.add_argument("--pick-percentiles", default="20,50,80", help="选择 3 条代表性负载的分位点（总功耗）")
    args = ap.parse_args()

    out_reports = ensure_dir(Path(args.out_reports))
    out_plots_root = ensure_dir(Path(args.out_plots))

    # 读取 AndroWatts（用于挑选代表性负载，并提取 I_obs/soc0/temp）
    df = load_aggregated_csv(Path(args.andro_csv))
    cases = build_cases(df, max_n=None, seed=0, max_screen_nits=500.0)
    if not cases:
        raise RuntimeError("AndroWatts cases 为空")

    # ID -> row（用于拿 I_obs）
    rows_by_id: dict[int, dict[str, object]] = {}
    for _, r in df.iterrows():
        try:
            tid = int(float(r.get("ID", 0)))
        except Exception:
            continue
        rows_by_id[tid] = dict(r.to_dict())

    ps = [float(x) for x in str(args.pick_percentiles).split(",") if str(x).strip()]
    pick_idx = _pick_cases_by_percentiles(cases, ps)
    picks = [cases[i] for i in pick_idx]

    # 电池状态表（36 states）
    states_all = load_battery_state_table(Path(args.battery_state_table))
    allow = {int(x) for x in str(args.battery_datasets).split(",") if str(x).strip()}
    states = [s for s in states_all if int(s.battery_dataset) in allow]
    if not states:
        raise RuntimeError("筛选后电池状态为空，请检查 --battery-datasets 参数")

    batt_base = BatteryParams3Aging.from_json(Path(args.phone))
    v_nom = 3.7  # 仅用于“代理上界”的能量换算口径（保持与其它脚本一致）

    out_rows: list[dict[str, object]] = []
    for load_k, c in enumerate(picks):
        load_label = ["轻负载", "中负载", "重负载"][load_k] if load_k < 3 else f"load{load_k+1}"
        test_id = int(c.test_id)
        row = rows_by_id.get(test_id, {})
        i_obs = float(_i_obs_from_row(row))
        soc0 = float(c.soc0) if c.soc0 is not None else float("nan")
        temp0 = float(c.temp_c) if c.temp_c is not None else float(23.0)

        for st in states:
            batt, cap_loss0, r0g0, r1g0 = apply_battery_state_to_model3(batt_base, st, r_growth_k=1.0)
            # 让“代理上界”与“模型仿真”的容量口径一致：把 capacity_Ah_ref 直接缩放到该状态的 Q_full_Ah。
            # （否则会出现：代理用 Q_full_Ah，但模型仍用 phone_default 的容量基准，导致不可比。）
            batt = replace(batt, capacity_Ah_ref=float(st.Q_full_Ah))
            cap_loss0 = 0.0
            # 代理上界：常流到 SOC=0（不考虑欠压/保护）
            q_eff_C = float(st.Q_full_Ah) * 3600.0
            t_proxy = float("nan")
            if np.isfinite(soc0) and np.isfinite(i_obs) and i_obs > 1e-9 and q_eff_C > 0:
                t_proxy = float(soc0 * q_eff_C / i_obs / 3600.0)

            # 机理模型：恒流到欠压/下限
            t_model, status, soc_end = _simulate_tte_current(
                batt=batt,
                soc0=float(max(0.0, min(1.0, soc0))) if np.isfinite(soc0) else 1.0,
                temp0_C=float(temp0),
                cap_loss0=float(cap_loss0),
                r0_growth0=float(r0g0),
                r1_growth0=float(r1g0),
                i_A=float(i_obs if np.isfinite(i_obs) else 0.0),
                dt_s=float(args.dt),
                ambient_temp_C=float(temp0),
            )

            out_rows.append(
                {
                    "load_label": load_label,
                    "phone_test_id": int(test_id),
                    "obs_total_w": float(c.obs.total_w),
                    "I_obs_A": float(i_obs),
                    "soc0": float(soc0),
                    "temp_c": float(temp0),
                    "battery_state_id": str(st.battery_state_id),
                    "battery_state_label": str(st.battery_state_label),
                    "SOH": float(st.SOH),
                    "Q_full_Ah": float(st.Q_full_Ah),
                    "tte_proxy_cc_h": float(t_proxy),
                    "tte_model_h": float(t_model) if t_model is not None else float("nan"),
                    "status": str(status),
                    "soc_end": float(soc_end),
                    "v_cut_V": float(batt.v_cut_V),
                    "soc_min": float(batt.soc_min),
                    "tte_model_over_proxy_pct": float("nan")
                    if (not np.isfinite(t_proxy) or t_proxy <= 1e-12 or t_model is None)
                    else float(t_model / t_proxy * 100.0),
                    "energy_proxy_Wh": float(st.Q_full_Ah) * float(v_nom),
                }
            )

    _write_csv(
        out_reports / "tte_proxy_current.csv",
        out_rows,
        fieldnames=[
            "load_label",
            "phone_test_id",
            "obs_total_w",
            "I_obs_A",
            "soc0",
            "temp_c",
            "battery_state_id",
            "battery_state_label",
            "SOH",
            "Q_full_Ah",
            "energy_proxy_Wh",
            "tte_proxy_cc_h",
            "tte_model_h",
            "tte_model_over_proxy_pct",
            "status",
            "soc_end",
            "v_cut_V",
            "soc_min",
        ],
    )

    # 绘图
    modes: list[PlotMode] = ["paper", "study"] if not str(args.mode).strip() else [str(args.mode)]
    for mode in modes:
        outp = ensure_dir(out_plots_root / str(mode) / "observed_tte_proxy_current")
        fig1 = _plot_tte_vs_soh(out_rows, mode=mode)
        savefig(fig1, outp / "01_tte_vs_soh_proxy.png", mode=mode)
        fig2 = _plot_soc_end(out_rows, mode=mode)
        savefig(fig2, outp / "02_soc_end_vs_soh.png", mode=mode)

    print("Q2 代理 TTE（恒流 I_obs）对照已生成：")
    print(f"- reports: {out_reports}")
    print(f"- plots  : {out_plots_root}/{{paper|study}}/observed_tte_proxy_current/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
