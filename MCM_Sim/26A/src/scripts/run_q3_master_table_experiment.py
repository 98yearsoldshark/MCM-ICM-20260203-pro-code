#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3 数据集实验：AndroWatts（真实使用状态）× 电池老化状态表（SOH+OCV），量化续航波动来源。

对齐赛题 Q3（Sensitivity and Assumptions）：
- fluctuations in usage patterns：用 AndroWatts 的公开测量状态分布（亮度/频率/流量/温度等）做“现实锚点”；
- history/aging：用电池老化状态表（Mendeley 派生）把 SOH 与 OCV(SOC) 引入模型；
- fluctuations（随机过程）：在同一 (usage, aging) 条件下仅改变随机种子，得到 TTE 的 seed 波动；
- 来源分解：把总方差分解为
    (1) 使用状态差异（phone_test）
    (2) 老化差异（battery_state）
    (3) 二者交互（usage×aging）
    (4) 随机过程（seed-only）

注意：
- 该实验不是用数据替代连续时间机理模型，而是用公开数据“锚定参数/验证量级/解释差异来源”；
- 为避免“功耗侧热节流（DVFS）”与“电池热模型”混杂，本脚本默认关闭功耗侧热节流（no_thermal_throttle）。
"""

from __future__ import annotations

import argparse
import csv
import sys
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
from mcm26a.observed.mcm2026_battery_state import apply_battery_state_to_model3, load_battery_state_table
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import Scenario


def _scenario_from_segment(case_id: str, seg) -> Scenario:
    """把单个 Segment 包装成“周期重复场景”（近似“稳态使用条件”）。"""

    return Scenario(
        scenario_id=str(case_id),
        title_zh=f"AW 样本 {case_id}",
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


def _pick_states_one_per_label(states, *, labels: list[str]) -> list:
    """每个老化档位挑 1 个代表状态（SOH 最接近该档位的均值）。"""

    out = []
    for lab in labels:
        group = [s for s in states if str(s.battery_state_label) == str(lab)]
        if not group:
            continue
        target = float(np.mean([float(s.SOH) for s in group]))
        pick = min(group, key=lambda s: abs(float(s.SOH) - target))
        out.append(pick)
    if not out:
        raise ValueError("未能从 battery_state_table 中选出任何状态（请检查 labels/数据文件）")
    return out


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


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 数据集实验（AndroWatts×老化状态）")
    ap.add_argument(
        "--aggregated",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
        help="AndroWatts aggregated.csv 路径",
    )
    ap.add_argument(
        "--battery-state-table",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
        help="电池老化状态表（36×15）路径",
    )
    ap.add_argument(
        "--battery-dataset",
        type=int,
        default=3,
        help="只使用指定 battery_dataset（默认 3；避免混入不同电芯体系导致 cutoff 口径不一致）",
    )
    ap.add_argument(
        "--battery-cell",
        default="Cell01",
        help="只使用指定 battery_cell（默认 Cell01；与 battery_dataset 共同决定一套完整 new~eol 档位）",
    )
    ap.add_argument(
        "--out-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_master_table"),
        help="输出目录（默认 out_reports/q3/observed_master_table）",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal.json"),
        help="功耗参数 JSON（建议用 AndroWatts 对照校准版）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒）")
    ap.add_argument("--n-phone-tests", type=int, default=24, help="抽样 phone_test 数量（按总功耗分位点覆盖）")
    ap.add_argument(
        "--state-labels",
        default="new,slight,moderate,aged,old,eol",
        help="选择的老化档位（逗号分隔，默认 6 档）",
    )
    ap.add_argument("--replicates", type=int, default=30, help="每个 (usage, aging) 的 seed 重复次数")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    ap.add_argument("--soc0-default", type=float, default=1.0, help="若数据缺失则用该值作为初始 SOC")
    ap.add_argument("--r-growth-k", type=float, default=1.0, help="SOH→内阻增长的映射强度系数（见 apply_battery_state_to_model3）")
    ap.add_argument(
        "--capacity-mode",
        default="cap_loss_from_soh",
        choices=["cap_loss_from_soh", "scale_capacity_ref"],
        help="把 SOH 映射为容量衰减的方式（默认用 cap_loss0=1-SOH，更直观）",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 手机侧：真实状态分布（AndroWatts）
    df = load_aggregated_csv(args.aggregated)
    cases_all = build_cases(df, max_n=None, seed=int(args.seed))
    cases = _pick_cases_by_power_quantile(cases_all, n_cases=int(args.n_phone_tests))

    # 2) 电池侧：老化状态表（SOH + OCV 多项式）
    states_all = load_battery_state_table(args.battery_state_table)
    # 避免把“不同电芯体系/标称电压范围”的状态混在一起（会让 V_cut 的比较口径失真）。
    states_all = [s for s in states_all if int(s.battery_dataset) == int(args.battery_dataset) and str(s.battery_cell) == str(args.battery_cell)]
    labels = [s.strip() for s in str(args.state_labels).split(",") if s.strip()]
    states = _pick_states_one_per_label(states_all, labels=labels)

    # 3) 模型参数
    power = PowerParams1Stateful.from_json(args.power)
    power = power_mechanism_variant(power, mech_id="no_thermal_throttle")
    batt_base = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    dt_s = float(args.dt)
    soc0_default = float(args.soc0_default)

    rows: list[dict[str, object]] = []
    # (I,J) 平衡设计：每个 phone_case×state 都跑一次；同一 phone_case 内用相同 seeds（CRN）以便稳健对比老化效应。
    for i, c in enumerate(cases):
        sc = _scenario_from_segment(f"AW_{int(c.test_id)}", c.segment)
        soc0 = soc0_default if c.soc0 is None else float(c.soc0)
        temp0_C = None if c.temp_c is None else float(c.temp_c)
        # 对该 phone_case 固定 seeds 前缀（跨不同老化状态共享）
        seeds = [int(args.seed) * 1_000_000 + i * 10_000 + k for k in range(int(args.replicates))]

        for st in states:
            batt, cap_loss0, r0g0, r1g0 = apply_battery_state_to_model3(
                batt_base,
                st,
                capacity_mode=str(args.capacity_mode),  # type: ignore[arg-type]
                r_growth_k=float(args.r_growth_k),
            )

            stats = simulate_tte_replicates(
                sc,
                power=power,
                batt=batt,
                power0_dummy=power0_dummy,
                dt_s=dt_s,
                soc0=soc0,
                seeds=seeds,
                battery_model="model3",
                cap_loss0_frac=float(cap_loss0),
                r0_growth0_frac=float(r0g0),
                r1_growth0_frac=float(r1g0),
            )

            seg = c.segment
            rows.append(
                {
                    "phone_test_id": int(c.test_id),
                    "battery_state_id": str(st.battery_state_id),
                    "battery_state_label": str(st.battery_state_label),
                    "SOH": float(st.SOH),
                    "soc0": float(soc0),
                    "temp0_C": float(temp0_C) if temp0_C is not None else float("nan"),
                    "cap_loss0_frac": float(cap_loss0),
                    "r0_growth0_frac": float(r0g0),
                    "r1_growth0_frac": float(r1g0),
                    # 观测功耗（用于“真实状态强度”轴）
                    "obs_total_w": float(c.obs.total_w),
                    "obs_screen_w": float(c.obs.screen_w),
                    "obs_cpu_w": float(c.obs.cpu_w),
                    "obs_gpu_w": float(c.obs.gpu_w),
                    "obs_radio_w": float(c.obs.radio_w),
                    "obs_gps_w": float(c.obs.gps_w),
                    "obs_background_w": float(c.obs.background_w),
                    "obs_base_w": float(c.obs.base_w),
                    "obs_other_w": float(c.obs.other_w),
                    # 映射后的“场景输入”
                    "seg_activity": str(seg.activity),
                    "seg_screen_on": bool(seg.screen_on),
                    "seg_brightness_nits": float(seg.brightness_nits),
                    "seg_cpu_load": float(seg.cpu_load),
                    "seg_gpu_load": float(seg.gpu_load),
                    "seg_radio_mode": str(seg.radio_mode),
                    "seg_net_activity": str(seg.net_activity),
                    "seg_gps_on": bool(seg.gps_on),
                    "seg_temp_c": float(seg.ambient_temp_c),
                    "seg_duration_s": float(seg.duration_s),
                    # TTE 统计
                    "replicates": int(args.replicates),
                    "tte_mean_h": float(stats["tte_mean_h"]),
                    "tte_std_h": float(stats["tte_std_h"]),
                    "tte_cv": float(stats["tte_cv"]),
                    "tte_p05_h": float(stats["tte_p05_h"]),
                    "tte_p50_h": float(stats["tte_p50_h"]),
                    "tte_p95_h": float(stats["tte_p95_h"]),
                    # 风险/终止机制
                    "p_cutoff": float(stats["p_cutoff"]),
                    "p_soc_min": float(stats["p_soc_min"]),
                    "p_insufficient_power": float(stats["p_insufficient_power"]),
                    "min_headroom_margin_mean": float(stats["min_headroom_margin_mean"]),
                }
            )

    _write_csv(out_dir / "cells_tte.csv", rows)

    # ------------------------
    # 方差/ANOVA 分解（usage vs aging vs interaction vs seed）
    # ------------------------
    # 1) 取每个 cell 的 mean/std
    # 2) Var_total ≈ Var(E[T|cell]) + E[Var(T|cell)]
    # 3) 对 Var(E[T|cell]) 再做二因素（phone×state）平方和分解，得到 usage/aging/interaction 三块。
    phone_ids = sorted({int(r["phone_test_id"]) for r in rows})
    state_ids = sorted({str(r["battery_state_id"]) for r in rows})
    I = len(phone_ids)
    J = len(state_ids)
    if I * J != len(rows):
        raise ValueError("当前 rows 不是平衡设计（phone_test×battery_state 未形成完整笛卡尔积）")

    idx_phone = {pid: k for k, pid in enumerate(phone_ids)}
    idx_state = {sid: k for k, sid in enumerate(state_ids)}

    y = np.full((I, J), np.nan, dtype=float)  # cell mean
    s = np.full((I, J), np.nan, dtype=float)  # cell std
    for r in rows:
        i = idx_phone[int(r["phone_test_id"])]
        j = idx_state[str(r["battery_state_id"])]
        y[i, j] = float(r["tte_mean_h"])
        s[i, j] = float(r["tte_std_h"])

    m = np.isfinite(y)
    if not bool(np.all(m)):
        # 若有 NaN，则无法做严格平衡 ANOVA；这里直接报错，提示提高仿真稳定性/筛掉异常 case。
        bad = int(np.size(m) - int(np.sum(m)))
        raise ValueError(f"存在 {bad} 个 cell 的 tte_mean_h 为 NaN，无法做平衡方差分解")

    n_cells = int(I * J)
    # within-seed：E[Var(T|cell)] ≈ mean(std^2)
    var_within = float(np.mean(s * s))

    # between-cell：Var(E[T|cell])
    y_flat = y.reshape(-1)
    var_between = float(np.var(y_flat, ddof=1)) if n_cells >= 2 else float("nan")

    # 二因素平方和分解：SS_total = SS_phone + SS_state + SS_interaction
    grand = float(np.mean(y))
    mean_i = np.mean(y, axis=1)  # phone means
    mean_j = np.mean(y, axis=0)  # state means
    ss_total = float(np.sum((y - grand) ** 2))
    ss_phone = float(J * np.sum((mean_i - grand) ** 2))
    ss_state = float(I * np.sum((mean_j - grand) ** 2))
    ss_inter = float(max(0.0, ss_total - ss_phone - ss_state))

    # 把 SS 转成“方差贡献”（与 var_between 同一尺度）
    denom = float(n_cells - 1) if n_cells >= 2 else float("nan")
    var_phone = float(ss_phone / denom) if np.isfinite(denom) and denom > 0 else float("nan")
    var_state = float(ss_state / denom) if np.isfinite(denom) and denom > 0 else float("nan")
    var_inter = float(ss_inter / denom) if np.isfinite(denom) and denom > 0 else float("nan")

    # 数值容错：保证三者求和≈var_between（浮点误差允许 1e-9）
    if np.isfinite(var_between):
        var_phone = float(max(0.0, var_phone))
        var_state = float(max(0.0, var_state))
        var_inter = float(max(0.0, var_between - var_phone - var_state)) if var_inter < 0 else float(var_inter)

    var_total = float(var_phone + var_state + var_inter + var_within)
    frac_phone = float(var_phone / var_total) if var_total > 0 else float("nan")
    frac_state = float(var_state / var_total) if var_total > 0 else float("nan")
    frac_inter = float(var_inter / var_total) if var_total > 0 else float("nan")
    frac_within = float(var_within / var_total) if var_total > 0 else float("nan")

    decomp = [
        {
            "n_phone_tests": int(I),
            "n_states": int(J),
            "n_cells": int(n_cells),
            "replicates": int(args.replicates),
            "dt_s": float(dt_s),
            "var_usage_phone_h2": float(var_phone),
            "var_aging_state_h2": float(var_state),
            "var_interaction_h2": float(var_inter),
            "var_seed_within_h2": float(var_within),
            "var_total_h2": float(var_total),
            "frac_usage_phone": float(frac_phone),
            "frac_aging_state": float(frac_state),
            "frac_interaction": float(frac_inter),
            "frac_seed_within": float(frac_within),
        }
    ]
    _write_csv(out_dir / "variance_decomposition_usage_aging.csv", decomp)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
