#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：使用波动（fluctuations）敏感性——均值固定的“突发性/脉冲化”强度 sweep（α）。

动机（对齐赛题 Q3）：
题面要求我们研究“使用模式波动”变化时，预测结果如何变化。为了避免把“均值变了”与“波动结构变了”
混在一起，本脚本构造一个 **均值近似固定** 的对照：

1) 对 Poisson 类突发（后台唤醒/前台网络 burst）：
   - 每次突发“幅度”按 α 放大：burst_mb *= α，cpu_wake_W *= α，data_mb_per_wake *= α
   - 到达率按 1/α 缩小：lambda_per_s /= α，burst_rate_per_s /= α
   => 这样保持“单位时间的平均工作量/平均数据量”近似不变，但突发更集中（方差更大）。

2) 对 Markov 类随机切换（信号好/差抖动、待机亮屏抖动）：
   - 同时缩放两方向转移率：rate *= α
   => 保持稳态分布（长期均值）不变，只改变“切换频率/时间相关结构”。

输出：
- 报表：
  - `src/out_reports/q3/fluctuation_burstiness_sweep/summary.csv`
  - `src/out_reports/q3/fluctuation_burstiness_sweep/runs.csv`
- 图：
  - `src/out_plots/q3/paper/fluctuation/22_burstiness_sweep.png`
  - `src/out_plots/q3/study/fluctuation/22_burstiness_sweep.png`

说明：
- 时间单位内部统一为秒（SI），图中可用“小时/分钟”作展示。
- 本实验不依赖任何额外外部数据集，属于“模型内可控对照”，用于回答 Q3 的 fluctuation 条目。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q3_sensitivity import simulate_tte_replicates
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, PlotMode, apply_style, savefig


def _parse_float_list(s: str) -> list[float]:
    xs: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    if not xs:
        raise ValueError("列表不能为空")
    return xs


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"rows 为空，无法写入 {path}")
    keys: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def apply_burstiness_alpha(p: PowerParams1Stateful, alpha: float) -> PowerParams1Stateful:
    """把功耗模型中的“随机性结构”按 α 调制，并尽量保持均值不变。"""

    a = float(alpha)
    if not np.isfinite(a) or a <= 0.0:
        raise ValueError("alpha 必须为正且有限")

    # --- Screen Markov：同时缩放两方向转移率，保持稳态概率不变 ---
    sm = p.screen_markov
    sm2 = replace(
        sm,
        off_to_on_rate_per_s_by_activity={k: float(v) * a for k, v in sm.off_to_on_rate_per_s_by_activity.items()},
        on_to_off_rate_per_s_by_activity={k: float(v) * a for k, v in sm.on_to_off_rate_per_s_by_activity.items()},
    )

    # --- Signal Markov：同时缩放 good<->poor 的转移率，保持稳态概率不变 ---
    sig = p.signal_markov
    sig2 = replace(
        sig,
        rates_by_base={
            base: {k: float(v) * a for k, v in rates.items()} for base, rates in (sig.rates_by_base or {}).items()
        },
    )

    # --- Background Poisson：幅度×α，速率/α（保持均值工作量/数据量近似不变） ---
    bg = p.background_poisson
    bg2 = replace(
        bg,
        lambda_per_s={k: float(v) / a for k, v in (bg.lambda_per_s or {}).items()},
        data_mb_per_wake=float(bg.data_mb_per_wake) * a,
        cpu_wake_W=float(bg.cpu_wake_W) * a,
    )

    # --- RRC burst：burst_mb×α，burst_rate/α（保持平均 burst 数据率不变） ---
    rrc = p.rrc
    rrc2 = replace(
        rrc,
        burst_rate_per_s_by_activity={
            k: float(v) / a for k, v in (rrc.burst_rate_per_s_by_activity or {}).items()
        },
        burst_mb_by_activity={k: float(v) * a for k, v in (rrc.burst_mb_by_activity or {}).items()},
    )

    return replace(p, screen_markov=sm2, signal_markov=sig2, background_poisson=bg2, rrc=rrc2)


def _plot_burstiness_sweep(
    rows: list[dict[str, object]],
    *,
    mode: PlotMode,
    out_path: Path,
    alpha_ref: float,
) -> None:
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # scenario_id -> title_zh
    title_by_id: dict[str, str] = {}
    for r in rows:
        sid = str(r.get("scenario_id", ""))
        if sid and sid not in title_by_id:
            title_by_id[sid] = str(r.get("scenario_title_zh", sid))

    alphas = sorted({float(r["alpha"]) for r in rows if r.get("alpha") is not None})
    alphas = [a for a in alphas if np.isfinite(a)]
    scenario_ids = sorted({str(r["scenario_id"]) for r in rows if str(r.get("scenario_id", "")).strip()})

    # (scenario, alpha) -> list[delta]
    data: dict[tuple[str, float], list[float]] = {}
    for r in rows:
        sid = str(r.get("scenario_id", "")).strip()
        if not sid:
            continue
        try:
            a = float(r.get("alpha", "nan"))
            d = float(r.get("delta_tte_pct", "nan"))
        except Exception:
            continue
        if not (np.isfinite(a) and np.isfinite(d)):
            continue
        data.setdefault((sid, float(a)), []).append(float(d))

    # 统计：中位数 + IQR
    series = {}
    for sid in scenario_ids:
        meds = []
        p25 = []
        p75 = []
        ns = []
        for a in alphas:
            xs = data.get((sid, float(a)), [])
            xs = [x for x in xs if np.isfinite(x)]
            if not xs:
                meds.append(float("nan"))
                p25.append(float("nan"))
                p75.append(float("nan"))
                ns.append(0)
                continue
            meds.append(float(np.percentile(xs, 50)))
            p25.append(float(np.percentile(xs, 25)))
            p75.append(float(np.percentile(xs, 75)))
            ns.append(len(xs))
        series[sid] = (np.array(meds, dtype=float), np.array(p25, dtype=float), np.array(p75, dtype=float), ns)

    fig, ax = plt.subplots(figsize=(7.8, 4.6))

    # 最多 4 色：Skip Gradient
    for i, sid in enumerate(scenario_ids):
        col = PALETTE_SKIP_GRADIENT[i % len(PALETTE_SKIP_GRADIENT)]
        med, lo, hi, _ns = series[sid]
        ax.plot(alphas, med, color=col, lw=2.1, marker="o", markersize=5.5, alpha=0.95, label=title_by_id.get(sid, sid))
        ax.fill_between(alphas, lo, hi, color=col, alpha=0.14, linewidth=0.0)

    ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.75)
    ax.set_xlabel("突发性/脉冲化强度 α（均值固定）")
    ax.set_ylabel(f"ΔTTE（%），相对 α={alpha_ref:g}")
    ax.set_title(f"Q3：均值固定的“突发性”波动强度 sweep {style.title_suffix}")
    ax.legend(frameon=False, fontsize=9, loc="lower left")

    # y 轴视野：自动留白
    ys: list[float] = []
    for sid in scenario_ids:
        med, lo, hi, _ns = series[sid]
        for arr in (med, lo, hi):
            xs = arr[np.isfinite(arr)]
            ys.extend(xs.tolist())
    if ys:
        y_min = float(min(ys))
        y_max = float(max(ys))
        ax.set_ylim(min(-1.0, y_min - 0.35), max(0.35, y_max + 0.25))

    if style.annotate:
        fig.text(
            0.02,
            0.02,
            "说明：本 sweep 通过“幅度×α、到达率/α”的方式保持平均工作量近似不变，主要改变波动的集中程度与时间结构。\n"
            "因此 ΔTTE 主要反映电池端非线性（I^2R 压降/极化 + 欠压截止）对突发性的放大效应。",
            ha="left",
            va="bottom",
            fontsize=9,
        )

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3：均值固定的突发性波动强度 sweep（α）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"))
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"))
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--soc0", type=float, default=1.0)
    ap.add_argument("--battery-model", default="model3", choices=["model1", "model1_2rc", "model2", "model3"])
    ap.add_argument("--scenario-ids", default="S4_mixed_day,S3_gaming,S5_burst_recovery")
    ap.add_argument("--alpha-list", default="0.5,1.0,2.0,4.0")
    ap.add_argument("--replicates", type=int, default=120)
    ap.add_argument("--seed", type=int, default=1007)
    ap.add_argument("--out-reports-dir", default=str(SRC_DIR / "out_reports" / "q3" / "fluctuation_burstiness_sweep"))
    ap.add_argument("--out-plots-dir", default=str(SRC_DIR / "out_plots" / "q3"))
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    base_power = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    scenario_ids = [s.strip() for s in str(args.scenario_ids).split(",") if s.strip()]
    if not scenario_ids:
        raise ValueError("scenario_ids 不能为空")

    alphas = sorted(_parse_float_list(str(args.alpha_list)))
    if any(a <= 0 for a in alphas):
        raise ValueError("alpha_list 必须全部为正")
    alpha_ref = float(min(alphas))

    reps = int(args.replicates)
    if reps <= 5:
        raise ValueError("replicates 太小（建议 >= 30）")

    # CRN：同一 scenario 下所有 α 共享同一组 seeds，便于做 per-seed 的 ΔTTE
    seed_base = int(args.seed) * 1_000_000
    base_seeds = [seed_base + i for i in range(reps)]

    summary_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []

    for sid_idx, sid in enumerate(scenario_ids):
        sc = materialize_scenario(raw, sid)
        title_zh = str(sc.title_zh or sid)

        # 先跑 reference（alpha_ref），便于 per-seed delta
        p_ref = apply_burstiness_alpha(base_power, alpha_ref)
        stats_ref = simulate_tte_replicates(
            sc,
            power=p_ref,
            batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(args.dt),
            soc0=float(args.soc0),
            seeds=base_seeds,
            battery_model=str(args.battery_model),
        )
        tte_ref_by_seed = {int(r["seed"]): r.get("tte_h", None) for r in stats_ref["runs"]}  # type: ignore[index]

        for a in alphas:
            p_a = apply_burstiness_alpha(base_power, float(a))
            stats = simulate_tte_replicates(
                sc,
                power=p_a,
                batt=batt,
                power0_dummy=power0_dummy,
                dt_s=float(args.dt),
                soc0=float(args.soc0),
                seeds=base_seeds,
                battery_model=str(args.battery_model),
            )

            # per-run：相对 alpha_ref 的 ΔTTE%
            deltas: list[float] = []
            for r in stats["runs"]:  # type: ignore[index]
                seed = int(r["seed"])
                tte = r.get("tte_h", None)
                tte_ref = tte_ref_by_seed.get(seed, None)
                if tte is None or tte_ref is None:
                    d = float("nan")
                else:
                    t0 = float(tte_ref)
                    t1 = float(tte)
                    d = float("nan") if (not np.isfinite(t0) or abs(t0) <= 1e-12 or not np.isfinite(t1)) else 100.0 * (t1 - t0) / t0
                deltas.append(d)

                run_rows.append(
                    {
                        "scenario_id": str(sid),
                        "scenario_title_zh": title_zh,
                        "alpha": float(a),
                        "alpha_ref": float(alpha_ref),
                        "seed": int(seed),
                        "tte_h": r.get("tte_h", None),
                        "tte_ref_h": tte_ref,
                        "delta_tte_pct": float(d),
                        "status": str(r.get("status", "")),
                        "min_headroom_margin": float(r.get("min_headroom_margin", float("nan"))),
                    }
                )

            # summary（用 mean_tte 对 mean_tte_ref）
            mean_ref = float(stats_ref["tte_mean_h"])
            mean_a = float(stats["tte_mean_h"])
            delta_mean_pct = float("nan") if (not np.isfinite(mean_ref) or abs(mean_ref) <= 1e-12 or not np.isfinite(mean_a)) else 100.0 * (mean_a - mean_ref) / mean_ref

            deltas_valid = [x for x in deltas if np.isfinite(x)]
            summary_rows.append(
                {
                    "scenario_id": str(sid),
                    "scenario_title_zh": title_zh,
                    "alpha": float(a),
                    "alpha_ref": float(alpha_ref),
                    "dt_s": float(args.dt),
                    "soc0": float(args.soc0),
                    "replicates": int(reps),
                    "battery_model": str(args.battery_model),
                    "tte_mean_h": float(stats["tte_mean_h"]),
                    "tte_p05_h": float(stats["tte_p05_h"]),
                    "tte_p50_h": float(stats["tte_p50_h"]),
                    "tte_p95_h": float(stats["tte_p95_h"]),
                    "tte_std_h": float(stats["tte_std_h"]),
                    "min_headroom_margin_mean": float(stats["min_headroom_margin_mean"]),
                    "min_headroom_margin_p05": float(stats["min_headroom_margin_p05"]),
                    "min_headroom_margin_p50": float(stats["min_headroom_margin_p50"]),
                    "min_headroom_margin_p95": float(stats["min_headroom_margin_p95"]),
                    "p_cutoff": float(stats["p_cutoff"]),
                    "p_soc_min": float(stats["p_soc_min"]),
                    "p_insufficient_power": float(stats["p_insufficient_power"]),
                    "delta_mean_tte_pct_vs_ref": float(delta_mean_pct),
                    "delta_tte_pct_median": float(np.percentile(deltas_valid, 50)) if deltas_valid else float("nan"),
                    "delta_tte_pct_p25": float(np.percentile(deltas_valid, 25)) if deltas_valid else float("nan"),
                    "delta_tte_pct_p75": float(np.percentile(deltas_valid, 75)) if deltas_valid else float("nan"),
                    "delta_tte_pct_n": int(len(deltas_valid)),
                }
            )

        print(f"[{sid}] done: alphas={alphas} reps={reps}")

    out_reports = Path(args.out_reports_dir)
    _write_csv(out_reports / "summary.csv", summary_rows)
    _write_csv(out_reports / "runs.csv", run_rows)

    out_plots = Path(args.out_plots_dir)
    for mode in ("paper", "study"):
        out_path = out_plots / mode / "fluctuation" / "22_burstiness_sweep.png"
        _plot_burstiness_sweep(run_rows, mode=mode, out_path=out_path, alpha_ref=alpha_ref)  # type: ignore[arg-type]

    print(f"wrote -> {out_reports}")
    print(f"wrote -> {out_plots / 'paper' / 'fluctuation' / '22_burstiness_sweep.png'}")
    print(f"wrote -> {out_plots / 'study' / 'fluctuation' / '22_burstiness_sweep.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

