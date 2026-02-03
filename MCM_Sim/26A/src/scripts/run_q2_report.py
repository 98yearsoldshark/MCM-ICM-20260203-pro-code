#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q2 数值报表（TTE 分布/区间、drivers、能耗占比），输出到 out_reports/q2/。

说明：
- 本脚本面向“写论文/做表格”，输出 CSV 便于直接引用；
- 图像请用 scripts/make_q2_plots.py 生成（paper/study 两套）。
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import asdict, fields
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import default_policy_actions
from mcm26a.analysis.q3_sensitivity import q3_param_label_zh
from mcm26a.analysis.sensitivity import prcc, spearman_corr
from mcm26a.analysis.q2_drivers import (
    component_driver_specs,
    mechanism_driver_specs,
    power_component_variant,
    power_mechanism_variant,
)
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.uq import Q2UQSample, apply_q2_uq_sample, sample_q2_uq


def _parse_soc_list(s: str) -> list[float]:
    xs: list[float] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    if not xs:
        raise ValueError("soc0-list 不能为空")
    return xs


def _quantile(arr: list[float], q: float) -> float:
    if not arr:
        return float("nan")
    return float(np.quantile(np.array(arr, dtype=float), q))

def _uq_spread_row(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"mean_h": float("nan"), "std_h": float("nan"), "cv": float("nan"), "p05_h": float("nan"), "p50_h": float("nan"), "p95_h": float("nan"), "width90_h": float("nan"), "width90_pct": float("nan")}
    arr = np.array(xs, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    p05 = float(np.quantile(arr, 0.05))
    p50 = float(np.quantile(arr, 0.50))
    p95 = float(np.quantile(arr, 0.95))
    w90 = float(p95 - p05)
    cv = float("nan") if abs(mean) <= 1e-12 else float(std / mean)
    w90pct = float("nan") if abs(mean) <= 1e-12 else float(w90 / mean * 100.0)
    return {"mean_h": mean, "std_h": std, "cv": cv, "p05_h": p05, "p50_h": p50, "p95_h": p95, "width90_h": w90, "width90_pct": w90pct}


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 数值报表（UQ + drivers + 能耗占比）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q2"), help="输出目录（默认 out_reports/q2）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON 路径（no7 升级 + AndroWatts 多目标校准版：更贴近公开测量的总功耗量级，且兼顾主要组件分解）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（Model-3：热-电-老化）",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="积分步长（秒），建议 1~10")
    ap.add_argument("--soc0-list", default="1.0,0.75,0.5,0.25", help="初始 SOC 列表，用逗号分隔")
    ap.add_argument("--uq-samples", type=int, default=80, help="UQ 采样次数（建议 80~5000）")
    ap.add_argument("--uq-seed", type=int, default=1, help="UQ 随机种子（可复现）")
    ap.add_argument("--driver-seeds", type=int, default=50, help="drivers 估计使用的随机种子数量（越大越稳）")
    ap.add_argument("--driver-soc0", type=float, default=1.0, help="drivers/能耗占比使用的 SOC0（默认 1.0）")
    ap.add_argument("--include-variants", action="store_true", help="同时输出每个场景的 variants")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    power1 = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    # 占位：simulate_model3_aging 在传入 power_model 时不会使用 power_params
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    soc0_list = _parse_soc_list(str(args.soc0_list))
    dt_s = float(args.dt)

    # --------------------------------
    # 1) UQ：输出样本级 TTE + 汇总区间
    # --------------------------------
    sample_rows: list[dict[str, object]] = []
    uq_rows: list[dict[str, object]] = []
    tte_map: dict[tuple[str, str, float], list[float]] = {}
    uq_fields = [f.name for f in fields(Q2UQSample)]

    # 组装要跑的“案例列表”：(scenario_id, variant_name, Scenario)
    cases: list[tuple[str, str, object]] = []
    for sid in raw.get("scenarios", {}).keys():
        cases.append((sid, "-", materialize_scenario(raw, sid)))
        if args.include_variants:
            for v in raw["scenarios"][sid].get("variants", {}).keys():
                cases.append((sid, str(v), materialize_scenario(raw, sid, variant=str(v))))

    for i in range(int(args.uq_samples)):
        rng = random.Random(int(args.uq_seed) + i)
        s = sample_q2_uq(rng)
        s_row = asdict(s)
        uq_rows.append({"sample_idx": int(i), **{k: float(s_row[k]) for k in uq_fields}})
        p_i, b_i = apply_q2_uq_sample(power1, batt, s)

        for case_idx, (sid, vname, sc) in enumerate(cases):
            for soc_idx, soc0 in enumerate(soc0_list):
                sim_seed = int(args.uq_seed) * 1_000_000 + i * 10_000 + case_idx * 100 + soc_idx
                pm = StatefulPowerModel1(p_i, seed=sim_seed)
                r = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=b_i,
                    soc0=float(soc0),
                    dt_s=dt_s,
                )
                if r.tte_h is None:
                    continue
                row = {
                    "sample_idx": int(i),
                    "scenario_id": sid,
                    "variant": vname,
                    "soc0": float(soc0),
                    "tte_h": float(r.tte_h),
                    "status": str(r.status),
                    "soc_end": float(r.soc_end),
                    "temp_peak_C": float(r.temp_peak_C),
                }
                row.update({k: float(s_row[k]) for k in uq_fields})
                sample_rows.append(row)
                tte_map.setdefault((sid, vname, float(soc0)), []).append(float(r.tte_h))

    uq_csv = out_dir / "uq_samples.csv"
    with uq_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["sample_idx", *uq_fields],
        )
        w.writeheader()
        w.writerows(uq_rows)

    sample_csv = out_dir / "tte_samples.csv"
    with sample_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "sample_idx",
                "scenario_id",
                "variant",
                "soc0",
                "tte_h",
                "status",
                "soc_end",
                "temp_peak_C",
                *uq_fields,
            ],
        )
        w.writeheader()
        w.writerows(sample_rows)

    summary_rows: list[dict[str, object]] = []
    for (sid, vname, soc0), xs in sorted(tte_map.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        xs = list(xs)
        summary_rows.append(
            {
                "scenario_id": sid,
                "variant": vname,
                "soc0": float(soc0),
                "n": len(xs),
                "mean_h": float(np.mean(xs)) if xs else float("nan"),
                "p05_h": _quantile(xs, 0.05),
                "p50_h": _quantile(xs, 0.50),
                "p95_h": _quantile(xs, 0.95),
            }
        )

    summary_csv = out_dir / "tte_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "variant", "soc0", "n", "mean_h", "p05_h", "p50_h", "p95_h"])
        w.writeheader()
        w.writerows(summary_rows)

    # 额外输出：终止原因概率 + 关机时 SOC 分布（Q2 常见评分点）
    term_counts: dict[tuple[str, str, float], dict[str, int]] = {}
    soc_end_cutoff: dict[tuple[str, str, float], list[float]] = {}
    for r in sample_rows:
        key = (str(r["scenario_id"]), str(r["variant"]), float(r["soc0"]))
        st = str(r["status"])
        term_counts.setdefault(key, {})
        term_counts[key][st] = int(term_counts[key].get(st, 0)) + 1
        if st == "cutoff":
            soc_end_cutoff.setdefault(key, []).append(float(r["soc_end"]))

    term_rows: list[dict[str, object]] = []
    for (sid, vname, soc0), counts in sorted(term_counts.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        n = sum(int(v) for v in counts.values())
        if n <= 0:
            continue
        term_rows.append(
            {
                "scenario_id": sid,
                "variant": vname,
                "soc0": float(soc0),
                "n": int(n),
                "p_cutoff": float(counts.get("cutoff", 0)) / n,
                "p_soc_min": float(counts.get("soc_min", 0)) / n,
                "p_insufficient_power": float(counts.get("insufficient_power", 0)) / n,
            }
        )

    term_csv = out_dir / "termination_stats.csv"
    with term_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["scenario_id", "variant", "soc0", "n", "p_cutoff", "p_soc_min", "p_insufficient_power"],
        )
        w.writeheader()
        w.writerows(term_rows)

    soc_rows: list[dict[str, object]] = []
    for (sid, vname, soc0), xs in sorted(soc_end_cutoff.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        xs = list(xs)
        soc_rows.append(
            {
                "scenario_id": sid,
                "variant": vname,
                "soc0": float(soc0),
                "n_cutoff": len(xs),
                "mean_soc_end": float(np.mean(xs)) if xs else float("nan"),
                "p05_soc_end": _quantile(xs, 0.05),
                "p50_soc_end": _quantile(xs, 0.50),
                "p95_soc_end": _quantile(xs, 0.95),
            }
        )

    soc_csv = out_dir / "soc_end_at_cutoff.csv"
    with soc_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "variant",
                "soc0",
                "n_cutoff",
                "mean_soc_end",
                "p05_soc_end",
                "p50_soc_end",
                "p95_soc_end",
            ],
        )
        w.writeheader()
        w.writerows(soc_rows)

    # --------------------------------
    # 1.5) UQ spread：用宽度/变异系数刻画“哪里更不可预测”
    # --------------------------------
    spread_rows: list[dict[str, object]] = []
    for (sid, vname, soc0), xs in sorted(tte_map.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        m = _uq_spread_row(list(xs))
        spread_rows.append(
            {
                "scenario_id": sid,
                "variant": vname,
                "soc0": float(soc0),
                "n": len(xs),
                **m,
            }
        )

    spread_csv = out_dir / "uq_spread.csv"
    with spread_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "variant",
                "soc0",
                "n",
                "mean_h",
                "std_h",
                "cv",
                "p05_h",
                "p50_h",
                "p95_h",
                "width90_h",
                "width90_pct",
            ],
        )
        w.writeheader()
        w.writerows(spread_rows)

    # --------------------------------
    # 1.6) 参数级敏感性：Spearman / PRCC（TTE）
    # --------------------------------
    def _spearman_safe(xs: list[float], ys: list[float]) -> float:
        ax = np.array(xs, dtype=float)
        ay = np.array(ys, dtype=float)
        m = np.isfinite(ax) & np.isfinite(ay)
        if int(np.sum(m)) < 3:
            return float("nan")
        try:
            return float(spearman_corr(ax[m].tolist(), ay[m].tolist()))
        except Exception:
            return float("nan")

    sens_rows: list[dict[str, object]] = []
    grouped: dict[tuple[str, str, float], list[dict[str, object]]] = {}
    for r in sample_rows:
        key = (str(r["scenario_id"]), str(r["variant"]), float(r["soc0"]))
        grouped.setdefault(key, []).append(r)

    for (sid, vname, soc0), rows in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        y = [float(rr["tte_h"]) for rr in rows]
        x_cols = {p: [float(rr[p]) for rr in rows] for p in uq_fields}
        pr = prcc(x_cols, y)
        for p in uq_fields:
            sens_rows.append(
                {
                    "scenario_id": sid,
                    "variant": vname,
                    "soc0": float(soc0),
                    "n": int(len(rows)),
                    "param": str(p),
                    "param_zh": q3_param_label_zh(str(p)),
                    "spearman": float(_spearman_safe(x_cols[p], y)),
                    "prcc": float(pr.get(str(p), float("nan"))),
                }
            )

    sens_csv = out_dir / "param_sensitivity.csv"
    with sens_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["scenario_id", "variant", "soc0", "n", "param", "param_zh", "spearman", "prcc"],
        )
        w.writeheader()
        w.writerows(sens_rows)

    # 汇总：对同一 soc0，按场景平均 |PRCC|，回答“哪些参数最导致 TTE 波动”
    overall_rows: list[dict[str, object]] = []
    for soc0 in soc0_list:
        for p in uq_fields:
            xs_prcc = [
                abs(float(r["prcc"]))
                for r in sens_rows
                if float(r["soc0"]) == float(soc0)
                and str(r["variant"]) == "-"
                and str(r["param"]) == str(p)
                and np.isfinite(float(r["prcc"]))
            ]
            xs_spear = [
                abs(float(r["spearman"]))
                for r in sens_rows
                if float(r["soc0"]) == float(soc0)
                and str(r["variant"]) == "-"
                and str(r["param"]) == str(p)
                and np.isfinite(float(r["spearman"]))
            ]
            overall_rows.append(
                {
                    "soc0": float(soc0),
                    "param": str(p),
                    "param_zh": q3_param_label_zh(str(p)),
                    "mean_abs_prcc": float(np.mean(xs_prcc)) if xs_prcc else float("nan"),
                    "mean_abs_spearman": float(np.mean(xs_spear)) if xs_spear else float("nan"),
                    "n_scenarios": int(len(xs_prcc)),
                }
            )

    overall_csv = out_dir / "param_sensitivity_overall.csv"
    with overall_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["soc0", "param", "param_zh", "mean_abs_prcc", "mean_abs_spearman", "n_scenarios"],
        )
        w.writeheader()
        w.writerows(overall_rows)

    # --------------------------------
    # 1.7) 温度 variants：baseline vs 冷/热（固定输出，直接对齐题面“temperature complicates matters”）
    # --------------------------------
    temp_rows: list[dict[str, object]] = []
    temp_variant_names = ["-", "cold_outdoor", "hot_summer"]
    sids = list(raw.get("scenarios", {}).keys())
    for sid_idx, sid in enumerate(sids):
        spec = raw["scenarios"][sid]
        vmap = spec.get("variants", {}) or {}
        for vname in temp_variant_names:
            if vname != "-" and vname not in vmap:
                continue

            sc = materialize_scenario(raw, sid, variant=(None if vname == "-" else vname))
            ambient = float(sc.schedule[0].ambient_temp_c)

            xs: list[float] = []
            statuses: list[str] = []
            soc_end: list[float] = []
            for k in range(int(args.driver_seeds)):
                seed = int(args.uq_seed) * 9000 + sid_idx * 100 + k
                pm = StatefulPowerModel1(power1, seed=seed)
                r = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=batt,
                    soc0=float(args.driver_soc0),
                    dt_s=dt_s,
                )
                if r.tte_h is None:
                    continue
                xs.append(float(r.tte_h))
                statuses.append(str(r.status))
                soc_end.append(float(r.soc_end))

            n = len(xs)
            denom = float(n) if n > 0 else float("nan")
            temp_rows.append(
                {
                    "scenario_id": sid,
                    "variant": vname,
                    "ambient_temp_c": ambient,
                    "n": int(n),
                    "tte_mean_h": float(np.mean(xs)) if xs else float("nan"),
                    "tte_p05_h": _quantile(xs, 0.05),
                    "tte_p50_h": _quantile(xs, 0.50),
                    "tte_p95_h": _quantile(xs, 0.95),
                    "p_cutoff": float(sum(1 for s in statuses if s == "cutoff")) / denom if np.isfinite(denom) else float("nan"),
                    "p_soc_min": float(sum(1 for s in statuses if s == "soc_min")) / denom if np.isfinite(denom) else float("nan"),
                    "p_insufficient_power": float(sum(1 for s in statuses if s == "insufficient_power")) / denom if np.isfinite(denom) else float("nan"),
                    "soc_end_mean": float(np.mean(np.array(soc_end, dtype=float))) if soc_end else float("nan"),
                }
            )

    temp_csv = out_dir / "temperature_variants_stats.csv"
    with temp_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "variant",
                "ambient_temp_c",
                "n",
                "tte_mean_h",
                "tte_p05_h",
                "tte_p50_h",
                "tte_p95_h",
                "p_cutoff",
                "p_soc_min",
                "p_insufficient_power",
                "soc_end_mean",
            ],
        )
        w.writeheader()
        w.writerows(temp_rows)

    # --------------------------------
    # 2) drivers：单因子反事实（平均 ΔTTE）
    # --------------------------------
    actions = default_policy_actions()
    driver_rows: list[dict[str, object]] = []
    driver_matrix_rows: list[dict[str, object]] = []

    # baseline 缓存：避免在每个 action 里重复跑 baseline
    baseline_tte_action: dict[tuple[int, int], float] = {}
    for seed_idx in range(int(args.driver_seeds)):
        seed = int(args.uq_seed) * 100 + seed_idx
        for case_idx, (sid, vname, sc0) in enumerate(cases):
            if vname != "-":
                continue
            base_seed = seed * 10_000 + case_idx
            pm0 = StatefulPowerModel1(power1, seed=base_seed)
            r0 = simulate_model3_aging(
                sc0,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=batt,
                soc0=float(args.driver_soc0),
                dt_s=dt_s,
            )
            if r0.tte_h is None:
                continue
            baseline_tte_action[(seed_idx, case_idx)] = float(r0.tte_h)

    for a in actions:
        deltas: list[float] = []
        deltas_by_sid: dict[str, list[float]] = {}
        for seed_idx in range(int(args.driver_seeds)):
            seed = int(args.uq_seed) * 100 + seed_idx
            for case_idx, (sid, vname, sc0) in enumerate(cases):
                if vname != "-":
                    # drivers 报表默认只看基线场景（变体可在图中解释）
                    continue
                t0 = baseline_tte_action.get((seed_idx, case_idx))
                if t0 is None:
                    continue
                sc1 = a.apply(sc0)
                base_seed = seed * 10_000 + case_idx
                pm1 = StatefulPowerModel1(power1, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc1,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=batt,
                    soc0=float(args.driver_soc0),
                    dt_s=dt_s,
                )
                if r1.tte_h is None:
                    continue
                d = float(r1.tte_h) - float(t0)
                deltas.append(d)
                deltas_by_sid.setdefault(str(sid), []).append(d)

        driver_rows.append(
            {
                "action_id": a.action_id,
                "title_zh": a.title_zh,
                "mean_delta_h": float(np.mean(deltas)) if deltas else 0.0,
                "n": len(deltas),
            }
        )
        for sid, xs in sorted(deltas_by_sid.items(), key=lambda x: x[0]):
            driver_matrix_rows.append(
                {
                    "scenario_id": str(sid),
                    "action_id": a.action_id,
                    "title_zh": a.title_zh,
                    "mean_delta_h": float(np.mean(xs)) if xs else 0.0,
                    "n": len(xs),
                }
            )

    drivers_csv = out_dir / "drivers_delta.csv"
    with drivers_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["action_id", "title_zh", "mean_delta_h", "n"])
        w.writeheader()
        w.writerows(driver_rows)

    drivers_mat_csv = out_dir / "drivers_matrix.csv"
    with drivers_mat_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "action_id", "title_zh", "mean_delta_h", "n"])
        w.writeheader()
        w.writerows(driver_matrix_rows)

    # --------------------------------
    # 2.5) drivers（机制消融）：tail / 弱信号惩罚 / 后台唤醒 / 交互项
    # --------------------------------
    mechs = mechanism_driver_specs()
    mech_rows: list[dict[str, object]] = []

    # baseline 缓存：避免在每个机制里重复跑 baseline
    baseline_tte_mech: dict[tuple[int, int], float] = {}
    for seed_idx in range(int(args.driver_seeds)):
        seed = int(args.uq_seed) * 5000 + seed_idx
        for case_idx, (sid, vname, sc0) in enumerate(cases):
            if vname != "-":
                continue
            base_seed = seed * 10_000 + case_idx
            pm0 = StatefulPowerModel1(power1, seed=base_seed)
            r0 = simulate_model3_aging(
                sc0,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=batt,
                soc0=float(args.driver_soc0),
                dt_s=dt_s,
            )
            if r0.tte_h is None:
                continue
            baseline_tte_mech[(seed_idx, case_idx)] = float(r0.tte_h)

    for mid, title in mechs:
        deltas: list[float] = []
        p2 = power_mechanism_variant(power1, mech_id=mid)
        for seed_idx in range(int(args.driver_seeds)):
            seed = int(args.uq_seed) * 5000 + seed_idx
            for case_idx, (sid, vname, sc0) in enumerate(cases):
                if vname != "-":
                    continue
                t0 = baseline_tte_mech.get((seed_idx, case_idx))
                if t0 is None:
                    continue
                base_seed = seed * 10_000 + case_idx
                pm1 = StatefulPowerModel1(p2, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc0,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=batt,
                    soc0=float(args.driver_soc0),
                    dt_s=dt_s,
                )
                if r1.tte_h is None:
                    continue
                deltas.append(float(r1.tte_h) - float(t0))

        mech_rows.append(
            {
                "mech_id": mid,
                "title_zh": title,
                "mean_delta_h": float(np.mean(deltas)) if deltas else 0.0,
                "n": len(deltas),
            }
        )

    mech_csv = out_dir / "mechanism_drivers_delta.csv"
    with mech_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mech_id", "title_zh", "mean_delta_h", "n"])
        w.writeheader()
        w.writerows(mech_rows)

    # --------------------------------
    # 2.6) drivers（组件级反事实）：屏幕/CPU/无线/后台等（更贴近题面 activities/conditions 的归因）
    # --------------------------------
    comps = component_driver_specs()
    comp_rows2: list[dict[str, object]] = []
    comp_matrix_rows: list[dict[str, object]] = []

    # baseline 缓存：避免在每个组件里重复跑 baseline
    baseline_tte_comp: dict[tuple[int, int], float] = {}
    for seed_idx in range(int(args.driver_seeds)):
        seed = int(args.uq_seed) * 7000 + seed_idx
        for case_idx, (sid, vname, sc0) in enumerate(cases):
            if vname != "-":
                continue
            base_seed = seed * 10_000 + case_idx
            pm0 = StatefulPowerModel1(power1, seed=base_seed)
            r0 = simulate_model3_aging(
                sc0,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=batt,
                soc0=float(args.driver_soc0),
                dt_s=dt_s,
            )
            if r0.tte_h is None:
                continue
            baseline_tte_comp[(seed_idx, case_idx)] = float(r0.tte_h)

    # 先做“按场景”的矩阵输出，再汇总为整体平均（方便论文中回答 in each case）
    for cid, title in comps:
        deltas_all: list[float] = []
        p2 = power_component_variant(power1, comp_id=cid)
        for case_idx, (sid, vname, sc0) in enumerate(cases):
            if vname != "-":
                continue
            deltas_sid: list[float] = []
            for seed_idx in range(int(args.driver_seeds)):
                seed = int(args.uq_seed) * 7000 + seed_idx
                base_seed = seed * 10_000 + case_idx

                t0 = baseline_tte_comp.get((seed_idx, case_idx))
                if t0 is None:
                    continue
                pm1 = StatefulPowerModel1(p2, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc0,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=batt,
                    soc0=float(args.driver_soc0),
                    dt_s=dt_s,
                )
                if r1.tte_h is None:
                    continue
                d = float(r1.tte_h) - float(t0)
                deltas_sid.append(d)
                deltas_all.append(d)

            comp_matrix_rows.append(
                {
                    "scenario_id": sid,
                    "component_id": cid,
                    "title_zh": title,
                    "mean_delta_h": float(np.mean(deltas_sid)) if deltas_sid else 0.0,
                    "n": len(deltas_sid),
                }
            )

        comp_rows2.append(
            {
                "component_id": cid,
                "title_zh": title,
                "mean_delta_h": float(np.mean(deltas_all)) if deltas_all else 0.0,
                "n": len(deltas_all),
            }
        )

    comp_csv = out_dir / "component_drivers_delta.csv"
    with comp_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["component_id", "title_zh", "mean_delta_h", "n"])
        w.writeheader()
        w.writerows(comp_rows2)

    comp_mat_csv = out_dir / "component_drivers_matrix.csv"
    with comp_mat_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "component_id", "title_zh", "mean_delta_h", "n"])
        w.writeheader()
        w.writerows(comp_matrix_rows)

    # --------------------------------
    # 3) 能耗占比：基线参数，多随机种子平均
    # --------------------------------
    comp_rows: list[dict[str, object]] = []
    comps = [
        "base_Wh",
        "screen_Wh",
        "cpu_Wh",
        "gpu_Wh",
        "radio_Wh",
        "gps_Wh",
        "background_Wh",
        "interaction_Wh",
    ]
    for case_idx, (sid, vname, sc) in enumerate(cases):
        if vname != "-":
            continue
        acc = {c: [] for c in comps}
        for seed_idx in range(int(args.driver_seeds)):
            seed = int(args.uq_seed) * 100 + seed_idx
            pm = StatefulPowerModel1(power1, seed=seed * 10_000 + case_idx)
            r = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=batt,
                soc0=float(args.driver_soc0),
                dt_s=dt_s,
            )
            total = float(r.energy_used_Wh) if r.energy_used_Wh else 0.0
            if total <= 0.0:
                continue
            for c in comps:
                acc[c].append(float(r.energy_components_Wh.get(c, 0.0)) / total * 100.0)

        for c in comps:
            comp_rows.append(
                {
                    "scenario_id": sid,
                    "component": c,
                    "mean_share_pct": float(np.mean(acc[c])) if acc[c] else 0.0,
                    "n": len(acc[c]),
                }
            )

    share_csv = out_dir / "energy_share.csv"
    with share_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "component", "mean_share_pct", "n"])
        w.writeheader()
        w.writerows(comp_rows)

    print("Q2 报表已生成：")
    print(f"- {sample_csv}")
    print(f"- {uq_csv}")
    print(f"- {summary_csv}")
    print(f"- {term_csv}")
    print(f"- {soc_csv}")
    print(f"- {spread_csv}")
    print(f"- {sens_csv}")
    print(f"- {overall_csv}")
    print(f"- {temp_csv}")
    print(f"- {drivers_csv}")
    print(f"- {drivers_mat_csv}")
    print(f"- {mech_csv}")
    print(f"- {comp_csv}")
    print(f"- {comp_mat_csv}")
    print(f"- {share_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
