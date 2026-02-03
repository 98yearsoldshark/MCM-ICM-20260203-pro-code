#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3 数据集实验：用 AndroWatts（open_data/aggregated.csv）构造“真实使用状态”样本，评估 TTE 分布与波动来源。

对齐赛题 Q3（Sensitivity and Assumptions）：
- fluctuations in usage patterns：用公开测量数据提供“真实状态分布”锚点（亮度/频率/流量/温度等）；
- fluctuations（随机过程）：在同一状态下仅改变随机种子，得到 TTE 波动（seed-only）；
- 输出“来源分解”：在固定参数下，比较
    Var_over_cases(E[TTE|case])（使用状态差异）
  vs E_over_cases(Var[TTE|case])（随机过程）

注意：
- 该实验的目的不是替代连续时间模型，而是用公开数据让 Q3 的“波动/敏感性”更贴近真实量级；
- 为避免把“功耗侧热节流（DVFS）”与电池热模型混在一起，本脚本默认关闭 DVFS（no_thermal_throttle）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q2_drivers import power_mechanism_variant
from mcm26a.analysis.q3_sensitivity import simulate_tte_replicates
from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.andro_watts import build_cases, load_aggregated_csv
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import Scenario


def _scenario_from_segment(case_id: str, seg) -> Scenario:
    """把单个 Segment 包装成“周期重复场景”（近似“稳态使用条件”）。"""

    return Scenario(
        scenario_id=str(case_id),
        title_zh=f"AndroWatts 样本 {case_id}",
        description_zh="由公开测量数据 aggregated.csv 映射得到的“稳态使用状态”（单段循环）。",
        repeat=True,
        cycle_s=float(seg.duration_s),
        schedule=(seg,),
    )


def _pick_cases_by_power_quantile(cases, *, n_cases: int) -> list:
    """按观测总功耗分位点抽样，确保覆盖低/中/高负载。"""

    n = int(n_cases)
    if n <= 0:
        raise ValueError("n_cases must be > 0")
    xs = sorted(cases, key=lambda c: float(c.obs.total_w))
    if n >= len(xs):
        return list(xs)
    idx = np.linspace(0, len(xs) - 1, n, dtype=int)
    return [xs[int(i)] for i in idx.tolist()]


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 数据集实验（AndroWatts）")
    ap.add_argument(
        "--aggregated",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
        help="AndroWatts aggregated.csv 路径",
    )
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q3" / "observed_open_data"), help="输出目录")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（若数据缺失则用该值）")
    ap.add_argument("--n-cases", type=int, default=120, help="抽样 case 数量（默认按功耗分位点覆盖）")
    ap.add_argument("--replicates", type=int, default=40, help="每个 case 的 seed 重复次数")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_aggregated_csv(args.aggregated)
    cases_all = build_cases(df, max_n=None, seed=int(args.seed))
    cases = _pick_cases_by_power_quantile(cases_all, n_cases=int(args.n_cases))

    power = PowerParams1Stateful.from_json(args.power)
    # 默认关闭 DVFS：避免“功耗侧节流”与“电池热模型”混杂（更利于解释 Q3）
    power = power_mechanism_variant(power, mech_id="no_thermal_throttle")

    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    dt_s = float(args.dt)
    soc0_default = float(args.soc0)

    rows: list[dict[str, object]] = []
    for j, c in enumerate(cases):
        sc = _scenario_from_segment(f"AW_{int(c.test_id)}", c.segment)
        soc0 = soc0_default if c.soc0 is None else float(c.soc0)

        # 每个 case 内固定 seeds（CRN）：便于跨假设/参数做可比对照
        seeds = [int(args.seed) * 1_000_000 + j * 10_000 + k for k in range(int(args.replicates))]
        st = simulate_tte_replicates(
            sc,
            power=power,
            batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model="model3",
        )

        seg = c.segment
        rows.append(
            {
                "case_id": f"AW_{int(c.test_id)}",
                "obs_total_w": float(c.obs.total_w),
                "obs_screen_w": float(c.obs.screen_w),
                "obs_cpu_w": float(c.obs.cpu_w),
                "obs_gpu_w": float(c.obs.gpu_w),
                "obs_radio_w": float(c.obs.radio_w),
                "obs_gps_w": float(c.obs.gps_w),
                "obs_background_w": float(c.obs.background_w),
                "obs_base_w": float(c.obs.base_w),
                "obs_other_w": float(c.obs.other_w),
                "seg_activity": str(seg.activity),
                "seg_screen_on": bool(seg.screen_on),
                "seg_brightness_nits": float(seg.brightness_nits),
                "seg_cpu_load": float(seg.cpu_load),
                "seg_gpu_load": float(seg.gpu_load),
                "seg_radio_mode": str(seg.radio_mode),
                "seg_net_activity": str(seg.net_activity),
                "seg_gps_on": bool(seg.gps_on),
                "seg_temp_c": float(seg.ambient_temp_c),
                "soc0": float(soc0),
                # TTE 统计
                "replicates": int(args.replicates),
                "tte_mean_h": float(st["tte_mean_h"]),
                "tte_std_h": float(st["tte_std_h"]),
                "tte_cv": float(st["tte_cv"]),
                "tte_p05_h": float(st["tte_p05_h"]),
                "tte_p50_h": float(st["tte_p50_h"]),
                "tte_p95_h": float(st["tte_p95_h"]),
                # 风险指标
                "p_cutoff": float(st["p_cutoff"]),
                "p_soc_min": float(st["p_soc_min"]),
                "p_insufficient_power": float(st["p_insufficient_power"]),
                "min_headroom_margin_mean": float(st["min_headroom_margin_mean"]),
            }
        )

    # 写 per-case 表
    out_cases = out_dir / "cases_tte.csv"
    with out_cases.open("w", encoding="utf-8", newline="") as f:
        # 动态汇总列名（避免后续加列时漏列）
        keys: list[str] = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    # 方差分解（跨 case 的 usage patterns vs case 内随机过程）
    tte_mu = np.array([float(r.get("tte_mean_h", float("nan"))) for r in rows], dtype=float)
    tte_std = np.array([float(r.get("tte_std_h", float("nan"))) for r in rows], dtype=float)
    m = np.isfinite(tte_mu) & np.isfinite(tte_std)
    tte_mu = tte_mu[m]
    tte_std = tte_std[m]
    var_between = float(np.var(tte_mu, ddof=1)) if tte_mu.size >= 2 else float("nan")
    var_within = float(np.mean(tte_std * tte_std)) if tte_std.size >= 1 else float("nan")
    var_total = float(var_between + var_within) if (np.isfinite(var_between) and np.isfinite(var_within)) else float("nan")
    frac_between = float(var_between / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
    frac_within = float(var_within / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")

    out_sum = out_dir / "variance_decomposition_usage.csv"
    with out_sum.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "n_cases",
                "replicates",
                "dt_s",
                "var_between_usage_h2",
                "var_within_seed_h2",
                "var_total_h2",
                "frac_between_usage",
                "frac_within_seed",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "n_cases": int(len(rows)),
                "replicates": int(args.replicates),
                "dt_s": float(dt_s),
                "var_between_usage_h2": float(var_between),
                "var_within_seed_h2": float(var_within),
                "var_total_h2": float(var_total),
                "frac_between_usage": float(frac_between),
                "frac_within_seed": float(frac_within),
            }
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

