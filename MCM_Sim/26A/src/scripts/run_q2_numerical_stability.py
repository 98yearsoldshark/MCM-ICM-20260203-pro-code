#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：数值稳定性检验（dt sweep）。

目的（对齐赛题与 no10 “满分口径”）：
- 证明我们的连续时间机理模型结果不是“步长假象”：
  在更小 dt 下，关键输出（TTE、温升峰值、功率闭合裕量 min_margin）变化应保持在较小范围。

设计选择：
- 为了把“数值误差”与“随机过程方差”分离，本脚本默认把功耗模型中的随机项关掉：
  - Screen Markov 随机亮屏：关
  - 信号抖动 Markov：关
  - 后台 Poisson 唤醒：关
  - 网络 burst Poisson：关
  这样 dt sweep 更像纯 ODE/闭环的数值稳定性测试。
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

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _parse_dt_list(s: str) -> list[float]:
    xs: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    xs = [x for x in xs if x > 0]
    if not xs:
        raise ValueError("dt-list 不能为空，且每个 dt 必须 >0")
    xs = sorted(set(xs), reverse=True)  # 从大到小，方便观察收敛
    return xs


def _make_deterministic(power: PowerParams1Stateful) -> PowerParams1Stateful:
    """关闭功耗模型的随机项，让 dt sweep 更“干净”。"""

    # Screen Markov：OFF/ON 转移率清零（待机段不再随机亮屏）
    sm = power.screen_markov
    screen_markov = replace(
        sm,
        off_to_on_rate_per_s_by_activity={k: 0.0 for k in sm.off_to_on_rate_per_s_by_activity.keys()},
        on_to_off_rate_per_s_by_activity={k: 0.0 for k in sm.on_to_off_rate_per_s_by_activity.keys()},
    )

    # 信号抖动：直接禁用（enabled_radio_modes 置空）
    sig = power.signal_markov
    signal_markov = replace(sig, enabled_radio_modes=tuple(), rates_by_base={})

    # 后台 Poisson：lambda 全部置 0（不再注入随机唤醒）
    bg = power.background_poisson
    background_poisson = replace(bg, lambda_per_s={k: 0.0 for k in bg.lambda_per_s.keys()})

    # 网络 burst：rate/mb 清零（只保留外生吞吐/离散映射的“平稳吞吐”）
    rrc = power.rrc
    burst_rate = {k: 0.0 for k in (rrc.burst_rate_per_s_by_activity or {}).keys()}
    burst_mb = {k: 0.0 for k in (rrc.burst_mb_by_activity or {}).keys()}
    rrc2 = replace(rrc, burst_rate_per_s_by_activity=burst_rate, burst_mb_by_activity=burst_mb)

    return replace(
        power,
        screen_markov=screen_markov,
        signal_markov=signal_markov,
        background_poisson=background_poisson,
        rrc=rrc2,
    )


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _plot_rel_error_box(rows: list[dict[str, object]], *, mode: PlotMode) -> object:
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # 只看“相对参考 dt 的 TTE 误差（%）”
    dt_vals = sorted({float(r["dt_s"]) for r in rows if np.isfinite(float(r.get("rel_tte_pct", float("nan"))))})
    if not dt_vals:
        raise ValueError("没有可用于绘图的 rel_tte_pct")

    data = []
    labels = []
    for dt in dt_vals:
        xs = [float(r["rel_tte_pct"]) for r in rows if float(r["dt_s"]) == float(dt) and np.isfinite(float(r.get("rel_tte_pct", float("nan"))))]
        if xs:
            data.append(xs)
            labels.append(f"{dt:g}s")

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    try:
        ax.boxplot(data, tick_labels=labels, showfliers=False)
    except TypeError:
        ax.boxplot(data, labels=labels, showfliers=False)
    ax.axhline(0.0, color="#999999", lw=1.0, alpha=0.7)
    ax.set_xlabel("积分步长 dt（秒）")
    ax.set_ylabel("相对误差（%）：(TTE(dt)-TTE_ref)/TTE_ref")
    ax.set_title(f"数值稳定性：dt sweep 的 TTE 相对误差分布{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：为分离“数值误差”与“随机过程方差”，本实验关闭功耗模型中的随机项（随机亮屏/信号抖动/后台唤醒/网络突发）。\n"
            "理想情况下，随着 dt 变小，TTE 结果应逐渐收敛；若出现终止机制变化（cutoff↔Δ<0↔SOC_min），需进一步检查边界事件处理与步长设置。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 数值稳定性检验（dt sweep）")
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "numerical_stability"))
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"))
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"))
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（建议使用已校准版本）",
    )
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"))
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（用于稳定性检验）")
    ap.add_argument("--dt-list", default="10,5,2,1", help="逗号分隔的 dt 列表（秒），例如 10,5,2,1")
    ap.add_argument("--include-variants", action="store_true", help="额外加入 cold_outdoor/hot_summer 变体（若存在）")
    args = ap.parse_args()

    dt_list = _parse_dt_list(str(args.dt_list))
    dt_ref = min(dt_list)

    out_reports = ensure_dir(Path(args.out_reports))
    out_plots_root = ensure_dir(Path(args.out_plots))

    raw = load_scenarios_json(args.scenarios)
    power = PowerParams1Stateful.from_json(args.power)
    power_det = _make_deterministic(power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    # 组装 case 列表：基线 +（可选）温度变体
    variant_names = ["-"]
    if bool(args.include_variants):
        variant_names += ["cold_outdoor", "hot_summer"]

    cases: list[tuple[str, str]] = []
    for sid in raw.get("scenarios", {}).keys():
        for v in variant_names:
            spec = raw["scenarios"][sid]
            vmap = spec.get("variants", {}) or {}
            if v != "-" and v not in vmap:
                continue
            cases.append((sid, v))

    # 逐 dt 跑一遍，记录结果
    records: list[dict[str, object]] = []
    ref_map: dict[tuple[str, str], dict[str, object]] = {}
    for dt_s in dt_list:
        for sid, v in cases:
            sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
            pm = StatefulPowerModel1(power_det, seed=0)
            res = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=batt,
                soc0=float(args.soc0),
                dt_s=float(dt_s),
                variant=(None if v == "-" else v),
            )
            row = {
                "scenario_id": sid,
                "variant": v,
                "dt_s": float(dt_s),
                "dt_ref_s": float(dt_ref),
                "status": str(res.status),
                "tte_h": float(res.tte_h) if res.tte_h is not None else float("nan"),
                "soc_end": float(res.soc_end),
                "temp_peak_C": float(res.temp_peak_C),
                "min_headroom_margin": float(res.min_headroom_margin),
            }

            if float(dt_s) == float(dt_ref):
                ref_map[(sid, v)] = dict(row)

            records.append(row)

    # 加上“相对参考 dt 的误差”列
    out_rows: list[dict[str, object]] = []
    for r in records:
        key = (str(r["scenario_id"]), str(r["variant"]))
        ref = ref_map.get(key, {})
        t = float(r.get("tte_h", float("nan")))
        t0 = float(ref.get("tte_h", float("nan")))
        st = str(r.get("status", ""))
        st0 = str(ref.get("status", ""))
        rel = float("nan")
        if np.isfinite(t) and np.isfinite(t0) and t0 > 1e-12:
            rel = float((t - t0) / t0 * 100.0)
        out_rows.append(
            {
                **r,
                "status_ref": st0,
                "status_changed": bool(st != st0),
                "tte_ref_h": t0,
                "rel_tte_pct": rel,
            }
        )

    _write_csv(
        out_reports / "dt_sweep.csv",
        out_rows,
        fieldnames=[
            "scenario_id",
            "variant",
            "dt_s",
            "dt_ref_s",
            "status",
            "status_ref",
            "status_changed",
            "tte_h",
            "tte_ref_h",
            "rel_tte_pct",
            "soc_end",
            "temp_peak_C",
            "min_headroom_margin",
        ],
    )

    # 汇总：每个 dt 的最大 |相对误差| + 终止机制变化次数
    summary: list[dict[str, object]] = []
    for dt_s in dt_list:
        rs = [x for x in out_rows if float(x["dt_s"]) == float(dt_s)]
        rels = [abs(float(x.get("rel_tte_pct", float("nan")))) for x in rs if np.isfinite(float(x.get("rel_tte_pct", float("nan"))))]
        summary.append(
            {
                "dt_s": float(dt_s),
                "n_cases": int(len(rs)),
                "n_status_changed": int(sum(1 for x in rs if bool(x.get("status_changed")))),
                "max_abs_rel_tte_pct": float(max(rels) if rels else float("nan")),
                "p95_abs_rel_tte_pct": float(np.nanpercentile(np.array(rels, dtype=float), 95)) if rels else float("nan"),
            }
        )

    _write_csv(
        out_reports / "dt_sweep_summary.csv",
        summary,
        fieldnames=["dt_s", "n_cases", "n_status_changed", "max_abs_rel_tte_pct", "p95_abs_rel_tte_pct"],
    )

    # 绘图（paper/study 两套）
    modes: list[PlotMode] = ["paper", "study"] if not str(args.mode).strip() else [str(args.mode)]
    for mode in modes:
        out_plots = ensure_dir(out_plots_root / str(mode) / "numerical_stability")
        fig = _plot_rel_error_box(out_rows, mode=mode)
        savefig(fig, out_plots / "01_rel_tte_error_box.png", mode=mode)

    print("Q2 数值稳定性 dt sweep 已生成：")
    print(f"- reports: {out_reports}")
    print(f"- plots  : {out_plots_root}/{{paper|study}}/numerical_stability/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

