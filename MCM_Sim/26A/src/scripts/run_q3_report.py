#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q3 数值报表（敏感性/假设/消融/老化扫描），输出到 out_reports/q3/。

对应赛题要求：
- Q3 Sensitivity and Assumptions：展示 TTE 等预测对参数与建模假设的敏感性；
- 同时给出“使用波动（随机过程）”导致的不可预测性量化，用于解释题干现象。
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

from mcm26a.analysis.q3_sensitivity import (
    compute_aging_scan,
    compute_battery_model_ablation,
    compute_battery_structure_ablation,
    compute_global_sensitivity,
    compute_local_sensitivity,
    compute_mechanism_ablation,
    q3_param_names,
    simulate_tte_replicates,
)
from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.mcm2026_battery_state import pick_soh_scan_points_from_state_table
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


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


def _pick_variant_groups(raw: dict, scenario_id: str) -> list[tuple[str, str | None]]:
    """为 Q3 选择“场景变体组”（用于回答题干中环境/信号等波动导致的差异）。

返回：
- (group_id, variant_name)

约定：
- group_id 为论文写作友好的“统一类别”，variant_name 为 configs 里的真实名字；
- baseline 的 variant_name 为 None；
- poor_signal 组在不同场景中可能对应不同具体名字（wifi_poor_signal / rural_poor_signal / ...）。
"""

    spec = (raw.get("scenarios", {}) or {}).get(str(scenario_id), {}) or {}
    variants = spec.get("variants", {}) or {}
    vnames = sorted(str(k) for k in variants.keys())

    out: list[tuple[str, str | None]] = [("baseline", None)]

    if "cold_outdoor" in variants:
        out.append(("cold_outdoor", "cold_outdoor"))
    if "hot_summer" in variants:
        out.append(("hot_summer", "hot_summer"))

    # 选一个“信号差/网络差”变体：用包含 poor_signal 的名字做统一匹配（兼容 wifi_poor_signal 等）
    poor = None
    for name in vnames:
        if "poor_signal" in name:
            poor = name
            break
    if poor is not None:
        out.append(("poor_signal", poor))

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 数值报表（敏感性/假设/消融/老化扫描）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q3"), help="输出目录（默认 out_reports/q3）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"),
        help="功耗参数 JSON 路径（stateful：RRC+Poisson后台+交互项）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（Model-3：热-电-老化）",
    )

    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒），建议 1~10；Q3 默认 10 以加速")
    ap.add_argument("--soc0", type=float, default=1.0, help="敏感性/消融默认使用的初始 SOC0")

    # 1) 使用波动（随机过程）重复次数
    # 说明：为了满足 Q3 的“分布/尾部”口径，并让 violin/分位图更稳定，我们默认给到 100。
    ap.add_argument("--replicates", type=int, default=100, help="同一参数下重复仿真的随机种子数量（越大越稳）")
    ap.add_argument(
        "--replicates-fluct",
        type=int,
        default=0,
        help="仅用于“使用波动/变体对照”的重复次数；0 表示沿用 --replicates",
    )
    ap.add_argument(
        "--replicates-local",
        type=int,
        default=0,
        help="仅用于“局部敏感性”的重复次数；0 表示沿用 --replicates",
    )
    ap.add_argument(
        "--replicates-ablation",
        type=int,
        default=0,
        help="仅用于“结构消融”的重复次数；0 表示沿用 --replicates",
    )
    ap.add_argument(
        "--replicates-aging",
        type=int,
        default=0,
        help="仅用于“SOH 扫描”的重复次数；0 表示沿用 --replicates",
    )
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")

    # 2) 全局敏感性（PRCC/Spearman）
    ap.add_argument("--global-samples", type=int, default=200, help="全局敏感性采样数 N（建议 200~1000）")
    ap.add_argument("--global-seeds-per-sample", type=int, default=6, help="每个参数样本的重复次数 K（建议 3~10）")

    # 3) 局部敏感性
    ap.add_argument("--local-eps", type=float, default=0.05, help="局部敏感性乘性扰动比例 eps（默认 0.05）")
    ap.add_argument("--local-vcut-delta", type=float, default=0.05, help="局部敏感性 V_cut 加性扰动（V，默认 0.05）")

    # 4) 老化扫描（SOH）
    ap.add_argument(
        "--soh-list",
        default="1.0,0.9,0.8",
        help="SOH 扫描列表（逗号分隔）；或填 auto 表示从 battery_state_table 的分位点自动选点",
    )
    ap.add_argument(
        "--battery-state-table",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
        help="电池状态表（用于 SOH 扫描点的观测锚定；默认 MCM2026_battery_state_table.csv）",
    )
    ap.add_argument(
        "--soh-quantiles",
        default="0,0.1667,0.3333,0.5,0.6667,0.8333,1",
        help="当 --soh-list=auto 时使用的 SOH 分位点（逗号分隔，范围 0~1）",
    )
    ap.add_argument("--alpha-r", type=float, default=1.5, help="老化增阻强度 alpha_R（R0 增长系数）")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    power = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if not scenario_ids:
        raise ValueError("scenarios 配置为空")

    dt_s = float(args.dt)
    soc0 = float(args.soc0)

    def _rep(v: int) -> int:
        v = int(v)
        return int(args.replicates) if v <= 0 else int(v)

    rep_fluct = _rep(int(args.replicates_fluct))
    rep_local = _rep(int(args.replicates_local))
    rep_ablation = _rep(int(args.replicates_ablation))
    rep_aging = _rep(int(args.replicates_aging))

    # 采用“相同 seed 前缀 + 不同用途偏移”的方式，既可复现又避免不同模块互相污染。
    seed_base = int(args.seed) * 1_000_000
    seeds_fluct = [seed_base + 10_000 + i for i in range(int(rep_fluct))]
    seeds_local = [seed_base + 20_000 + i for i in range(int(rep_local))]
    seeds_ablation = [seed_base + 30_000 + i for i in range(int(rep_ablation))]
    seeds_aging = [seed_base + 40_000 + i for i in range(int(rep_aging))]

    # ------------------------
    # 0) 使用波动（随机过程）统计
    # ------------------------
    seed_run_rows: list[dict[str, object]] = []
    fluct_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        stats = simulate_tte_replicates(
            sc,
            power=power,
            batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_fluct,
            battery_model="model3",
        )
        fluct_rows.append(
            {
                "scenario_id": sid,
                "soc0": soc0,
                "dt_s": dt_s,
                "replicates": int(rep_fluct),
                "tte_mean_h": float(stats["tte_mean_h"]),
                "tte_std_h": float(stats["tte_std_h"]),
                "tte_cv": float(stats["tte_cv"]),
                "tte_p05_h": float(stats["tte_p05_h"]),
                "tte_p50_h": float(stats["tte_p50_h"]),
                "tte_p95_h": float(stats["tte_p95_h"]),
                "min_headroom_margin_mean": float(stats["min_headroom_margin_mean"]),
                "min_headroom_margin_std": float(stats["min_headroom_margin_std"]),
                "min_headroom_margin_p05": float(stats["min_headroom_margin_p05"]),
                "min_headroom_margin_p50": float(stats["min_headroom_margin_p50"]),
                "min_headroom_margin_p95": float(stats["min_headroom_margin_p95"]),
                "p_cutoff": float(stats["p_cutoff"]),
                "p_soc_min": float(stats["p_soc_min"]),
                "p_insufficient_power": float(stats["p_insufficient_power"]),
            }
        )
        for run in stats["runs"]:  # type: ignore[index]
            seed_run_rows.append({"scenario_id": sid, "soc0": soc0, "dt_s": dt_s, **dict(run)})

    with (out_dir / "fluctuation_only.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "soc0",
                "dt_s",
                "replicates",
                "tte_mean_h",
                "tte_std_h",
                "tte_cv",
                "tte_p05_h",
                "tte_p50_h",
                "tte_p95_h",
                "min_headroom_margin_mean",
                "min_headroom_margin_std",
                "min_headroom_margin_p05",
                "min_headroom_margin_p50",
                "min_headroom_margin_p95",
                "p_cutoff",
                "p_soc_min",
                "p_insufficient_power",
            ],
        )
        w.writeheader()
        w.writerows(fluct_rows)

    with (out_dir / "seed_runs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "soc0", "dt_s", "seed", "tte_h", "status", "min_headroom_margin"])
        w.writeheader()
        w.writerows(seed_run_rows)

    # ------------------------
    # 0.5) 场景变体（环境/信号等条件波动）：baseline vs cold/hot/poor_signal
    # ------------------------
    variant_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        for group_id, vname in _pick_variant_groups(raw, sid):
            sc = materialize_scenario(raw, sid, variant=vname)
            st = simulate_tte_replicates(
                sc,
                power=power,
                batt=batt,
                power0_dummy=power0_dummy,
                dt_s=dt_s,
                soc0=soc0,
                seeds=seeds_fluct,
                battery_model="model3",
            )
            variant_rows.append(
                {
                    "scenario_id": sid,
                    "variant_group": str(group_id),
                    "variant_name": "" if vname is None else str(vname),
                    "soc0": soc0,
                    "dt_s": dt_s,
                    "replicates": int(rep_fluct),
                    "tte_mean_h": float(st["tte_mean_h"]),
                    "tte_std_h": float(st["tte_std_h"]),
                    "tte_cv": float(st["tte_cv"]),
                    "min_headroom_margin_mean": float(st["min_headroom_margin_mean"]),
                    "p_cutoff": float(st["p_cutoff"]),
                    "p_soc_min": float(st["p_soc_min"]),
                    "p_insufficient_power": float(st["p_insufficient_power"]),
                }
            )

    with (out_dir / "variant_sweep.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "variant_group",
                "variant_name",
                "soc0",
                "dt_s",
                "replicates",
                "tte_mean_h",
                "tte_std_h",
                "tte_cv",
                "min_headroom_margin_mean",
                "p_cutoff",
                "p_soc_min",
                "p_insufficient_power",
            ],
        )
        w.writeheader()
        w.writerows(variant_rows)

    # ------------------------
    # 1) 局部敏感性（dimensionless）
    # ------------------------
    local_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        rows = compute_local_sensitivity(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_local,
            eps=float(args.local_eps),
            v_cut_delta_V=float(args.local_vcut_delta),
            battery_model="model3",
        )
        for r in rows:
            local_rows.append({"scenario_id": sid, **r})

    with (out_dir / "local_sensitivity.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "scenario_id",
            "param",
            "param_zh",
            "type",
            "theta0",
            "theta_minus",
            "theta_plus",
            "y0_tte_mean_h",
            "y_minus_tte_mean_h",
            "y_plus_tte_mean_h",
            "sens_dimless",
            "eps",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(local_rows)

    # ------------------------
    # 2) 结构消融（机制 + 电池模型复杂度）
    # ------------------------
    ablation_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)

        for r in compute_mechanism_ablation(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_ablation,
        ):
            ablation_rows.append({"scenario_id": sid, **r})

        for r in compute_battery_model_ablation(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_ablation,
        ):
            ablation_rows.append({"scenario_id": sid, **r})

        for r in compute_battery_structure_ablation(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_ablation,
        ):
            ablation_rows.append({"scenario_id": sid, **r})

    # 统一写一个 CSV（不同 ablation_type 的列不完全一致；空值留空）
    # 先汇总 fieldnames：保证 CSV 不丢列
    all_keys: list[str] = ["scenario_id"]
    key_set = set(all_keys)
    for r in ablation_rows:
        for k in r.keys():
            if k not in key_set:
                key_set.add(k)
                all_keys.append(k)

    with (out_dir / "ablation.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_keys)
        w.writeheader()
        w.writerows(ablation_rows)

    # ------------------------
    # 3) 全局敏感性（PRCC/Spearman）
    # ------------------------
    prcc_rows: list[dict[str, object]] = []
    spear_rows: list[dict[str, object]] = []
    param_rows_all: list[dict[str, object]] = []
    global_out_rows: list[dict[str, object]] = []

    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        g = compute_global_sensitivity(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            n_samples=int(args.global_samples),
            seeds_per_sample=int(args.global_seeds_per_sample),
            seed=int(args.seed) + 1000,  # 避免与 fluctuation/local 的 seed 复用
            battery_model="model3",
        )

        # 参数样本表：对每个 scenario 都是同分布，但为了避免“多份重复文件”，只写一次
        if not param_rows_all:
            param_rows_all = list(g["param_rows"])  # type: ignore[assignment]

        for out_name, table in [
            ("tte_mean_h", g["prcc_tte"]),
            ("tte_std_h", g["prcc_tte_std"]),
            ("tte_cv", g["prcc_tte_cv"]),
            ("tte_spread_h", g["prcc_tte_spread_h"]),
            ("p_cutoff", g["prcc_p_cutoff"]),
            ("p_insufficient_power", g["prcc_p_insufficient_power"]),
            ("min_headroom_margin", g["prcc_min_headroom_margin"]),
        ]:
            for k in q3_param_names():
                prcc_rows.append({"scenario_id": sid, "output": out_name, "param": k, "prcc": float(table.get(k, float("nan")))})

        for out_name, table in [
            ("tte_mean_h", g["spearman_tte"]),
            ("tte_std_h", g["spearman_tte_std"]),
            ("tte_cv", g["spearman_tte_cv"]),
            ("tte_spread_h", g["spearman_tte_spread_h"]),
            ("p_cutoff", g["spearman_p_cutoff"]),
            ("p_insufficient_power", g["spearman_p_insufficient_power"]),
            ("min_headroom_margin", g["spearman_min_headroom_margin"]),
        ]:
            for k in q3_param_names():
                spear_rows.append(
                    {"scenario_id": sid, "output": out_name, "param": k, "spearman": float(table.get(k, float("nan")))}
                )

        for r in g["per_sample_rows"]:  # type: ignore[index]
            global_out_rows.append({"scenario_id": sid, **dict(r)})

    with (out_dir / "global_param_samples.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_idx", *q3_param_names()])
        w.writeheader()
        w.writerows(param_rows_all)

    with (out_dir / "global_outputs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "sample_idx",
                "tte_mean_h",
                "tte_std_h",
                "tte_cv",
                "tte_spread_h",
                "p_cutoff",
                "p_insufficient_power",
                "min_headroom_margin",
            ],
        )
        w.writeheader()
        w.writerows(global_out_rows)

    # ------------------------
    # 3.5) 不确定性“来源分解”（更贴赛题 Q3 的 fluctuations 口径）
    # ------------------------
    # 近似使用全局采样结果分解：
    #   Var(TTE) = Var(E[TTE|θ]) + E[Var(TTE|θ)]
    # - Var(E[TTE|θ])：参数/状态不确定性（between-sample）
    # - E[Var(TTE|θ)]：使用波动/随机过程（within-sample）
    decomp_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        mu_list: list[float] = []
        sig2_list: list[float] = []
        for r in global_out_rows:
            if str(r.get("scenario_id")) != str(sid):
                continue
            try:
                mu = float(r.get("tte_mean_h", float("nan")))
            except Exception:
                mu = float("nan")
            try:
                sig = float(r.get("tte_std_h", float("nan")))
            except Exception:
                sig = float("nan")
            if np.isfinite(mu):
                mu_list.append(float(mu))
            if np.isfinite(sig):
                sig2_list.append(float(sig) * float(sig))

        var_between = float(np.var(np.asarray(mu_list, dtype=float), ddof=1)) if len(mu_list) >= 2 else float("nan")
        var_within = float(np.mean(np.asarray(sig2_list, dtype=float))) if sig2_list else float("nan")
        var_total = float(var_between + var_within) if (np.isfinite(var_between) and np.isfinite(var_within)) else float("nan")

        frac_param = float(var_between / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
        frac_usage = float(var_within / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")

        decomp_rows.append(
            {
                "scenario_id": str(sid),
                "n_samples": int(args.global_samples),
                "seeds_per_sample": int(args.global_seeds_per_sample),
                "var_between_param_h2": float(var_between),
                "var_within_usage_h2": float(var_within),
                "var_total_h2": float(var_total),
                "frac_param": float(frac_param),
                "frac_usage": float(frac_usage),
            }
        )

    with (out_dir / "variance_decomposition.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "n_samples",
                "seeds_per_sample",
                "var_between_param_h2",
                "var_within_usage_h2",
                "var_total_h2",
                "frac_param",
                "frac_usage",
            ],
        )
        w.writeheader()
        w.writerows(decomp_rows)

    with (out_dir / "global_prcc.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "output", "param", "prcc"])
        w.writeheader()
        w.writerows(prcc_rows)

    with (out_dir / "global_spearman.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "output", "param", "spearman"])
        w.writeheader()
        w.writerows(spear_rows)

    # 额外输出：Top-K 参数摘要表（写论文时很省事）
    top_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        for out_name in [
            "tte_mean_h",
            "tte_std_h",
            "tte_cv",
            "tte_spread_h",
            "p_cutoff",
            "p_insufficient_power",
            "min_headroom_margin",
        ]:
            xs = []
            for r in prcc_rows:
                if str(r.get("scenario_id")) != sid or str(r.get("output")) != out_name:
                    continue
                try:
                    v = float(r.get("prcc", float("nan")))
                except Exception:
                    v = float("nan")
                if not np.isfinite(v):
                    continue
                xs.append((str(r.get("param")), float(v)))
            xs.sort(key=lambda kv: abs(kv[1]), reverse=True)
            for rank, (param, v) in enumerate(xs[:5], start=1):
                top_rows.append({"scenario_id": sid, "output": out_name, "rank": rank, "param": param, "prcc": float(v)})

    with (out_dir / "global_prcc_top5.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "output", "rank", "param", "prcc"])
        w.writeheader()
        w.writerows(top_rows)

    # ------------------------
    # 4) 老化扫描（SOH）
    # ------------------------
    soh_list_str = str(args.soh_list).strip()
    if soh_list_str.lower() in ("auto", "from_table", "table"):
        qs = _parse_float_list(str(args.soh_quantiles))
        qs = [float(q) for q in qs if 0.0 <= float(q) <= 1.0]
        if not qs:
            raise ValueError("soh-quantiles 不能为空，且必须在 [0,1] 内")
        soh_list = pick_soh_scan_points_from_state_table(
            Path(args.battery_state_table),
            quantiles=tuple(float(q) for q in qs),
        )
    else:
        soh_list = _parse_float_list(soh_list_str)
    aging_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        rows = compute_aging_scan(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds_aging,
            soh_list=soh_list,
            alpha_r=float(args.alpha_r),
        )
        for r in rows:
            aging_rows.append({"scenario_id": sid, **r})

    with (out_dir / "aging_scan.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_id",
                "soh",
                "cap_loss0_frac",
                "r0_growth0_frac",
                "alpha_r",
                "tte_mean_h",
                "tte_p05_h",
                "tte_p50_h",
                "tte_p95_h",
                "min_headroom_margin_mean",
                "p_cutoff",
                "p_insufficient_power",
            ],
        )
        w.writeheader()
        w.writerows(aging_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
