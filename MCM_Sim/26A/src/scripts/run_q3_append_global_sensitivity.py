#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加/更新单个场景的 Q3「全局敏感性」报表（PRCC/Spearman/global_outputs/variance_decomposition）。

使用场景：
- 我们新增了一个场景（例如 Browsing/Social Media），但不希望重跑整套 run_q3_report.py（耗时很大）；
- 只需要把该场景补齐到全局敏感性相关 CSV 中，从而让 PRCC 图可以包含该场景。

注意：
- 本脚本只更新与“全局敏感性”相关的文件：
  - out_reports/q3/global_prcc.csv
  - out_reports/q3/global_spearman.csv
  - out_reports/q3/global_outputs.csv
  - out_reports/q3/variance_decomposition.csv
  - out_reports/q3/global_prcc_top5.csv
- 不会更新局部敏感性/消融/老化扫描等更昂贵的报表。
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

from mcm26a.analysis.q3_sensitivity import compute_global_sensitivity, q3_param_names
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _write_csv(path: Path, rows: list[dict[str, object]], *, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _float(x: object) -> float:
    try:
        return float(x)  # type: ignore[arg-type]
    except Exception:
        return float("nan")


def _assert_param_samples_match(existing: list[dict[str, str]], new_rows: list[dict[str, float]]) -> None:
    """避免出现“同一 global_outputs/global_prcc 使用了不同参数样本表”的不一致。"""

    if not existing:
        return

    # existing: sample_idx + params
    if len(existing) != len(new_rows):
        raise ValueError(f"global_param_samples.csv 行数不一致：existing={len(existing)} new={len(new_rows)}")

    keys = ["sample_idx", *q3_param_names()]
    for i, (a, b) in enumerate(zip(existing, new_rows)):
        for k in keys:
            va = _float(a.get(k))
            vb = float(b.get(k, float("nan")))
            if not (np.isfinite(va) and np.isfinite(vb)):
                raise ValueError(f"global_param_samples.csv 存在非数值：row={i} key={k}")
            if abs(float(va) - float(vb)) > 1e-12:
                raise ValueError(
                    "global_param_samples.csv 与本次计算的参数样本不一致："
                    f"row={i} key={k} existing={va} new={vb}。\n"
                    "请确认 n_samples/seed/prior_mode 与原始报表一致，或直接重跑 scripts/run_q3_report.py。"
                )


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - 追加单个场景的 Q3 全局敏感性报表")
    ap.add_argument("--scenario-id", required=True, help="要追加/更新的 scenario_id（例如 S1b_browse）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q3"), help="out_reports/q3 目录")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"),
        help="功耗参数 JSON（需与原始 global_prcc 对齐）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（需与原始 global_prcc 对齐）",
    )
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0")
    ap.add_argument("--global-samples", type=int, default=240, help="全局采样数 N（应与现有报表一致）")
    ap.add_argument("--global-seeds-per-sample", type=int, default=4, help="每个样本的 seeds 数 K（应与现有报表一致）")
    ap.add_argument("--seed", type=int, default=7, help="基准随机种子（应与现有报表一致）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    sid = str(args.scenario_id)
    if sid not in (raw.get("scenarios", {}) or {}):
        raise KeyError(f"unknown scenario_id: {sid!r} (not found in {args.scenarios})")

    sc = materialize_scenario(raw, sid)
    power = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    # 与 scripts/run_q3_report.py 保持一致：全局敏感性使用 seed+1000，避免与 fluctuation/local 复用
    seed_global = int(args.seed) + 1000

    g = compute_global_sensitivity(
        sc,
        base_power=power,
        base_batt=batt,
        power0_dummy=power0_dummy,
        dt_s=float(args.dt),
        soc0=float(args.soc0),
        n_samples=int(args.global_samples),
        seeds_per_sample=int(args.global_seeds_per_sample),
        seed=int(seed_global),
        battery_model="model3",
        prior_mode="default",
    )

    # 1) 校验：global_param_samples 必须一致（否则会造成跨场景 PRCC 不可比）
    param_path = out_dir / "global_param_samples.csv"
    existing_param = _read_csv(param_path)
    _assert_param_samples_match(existing_param, g["param_rows"])  # type: ignore[arg-type]
    if not existing_param:
        # 若此前没有（例如首次运行），则写入
        _write_csv(param_path, list(g["param_rows"]), fieldnames=["sample_idx", *q3_param_names()])  # type: ignore[arg-type]

    # 2) global_outputs.csv：追加/替换该场景的 per-sample 输出
    out_path = out_dir / "global_outputs.csv"
    existing_out = _read_csv(out_path)
    existing_out = [r for r in existing_out if str(r.get("scenario_id")) != sid]
    for r in g["per_sample_rows"]:  # type: ignore[index]
        existing_out.append({"scenario_id": sid, **dict(r)})
    _write_csv(
        out_path,
        existing_out,
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

    # 3) variance_decomposition.csv：用全局采样结果做 “参数 vs 使用波动” 分解
    vd_path = out_dir / "variance_decomposition.csv"
    vd_rows = _read_csv(vd_path)
    vd_rows = [r for r in vd_rows if str(r.get("scenario_id")) != sid]

    mu = [float(r.get("tte_mean_h", "nan")) for r in g["per_sample_rows"]]  # type: ignore[index]
    sig2 = [float(r.get("tte_std_h", "nan")) ** 2 for r in g["per_sample_rows"]]  # type: ignore[index]
    mu = [x for x in mu if np.isfinite(x)]
    sig2 = [x for x in sig2 if np.isfinite(x)]
    var_between = float(np.var(np.asarray(mu, dtype=float), ddof=1)) if len(mu) >= 2 else float("nan")
    var_within = float(np.mean(np.asarray(sig2, dtype=float))) if sig2 else float("nan")
    var_total = float(var_between + var_within) if (np.isfinite(var_between) and np.isfinite(var_within)) else float("nan")
    frac_param = float(var_between / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
    frac_usage = float(var_within / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
    vd_rows.append(
        {
            "scenario_id": sid,
            "n_samples": int(args.global_samples),
            "seeds_per_sample": int(args.global_seeds_per_sample),
            "var_between_param_h2": float(var_between),
            "var_within_usage_h2": float(var_within),
            "var_total_h2": float(var_total),
            "frac_param": float(frac_param),
            "frac_usage": float(frac_usage),
        }
    )
    _write_csv(
        vd_path,
        vd_rows,
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

    # 4) global_prcc.csv / global_spearman.csv
    prcc_path = out_dir / "global_prcc.csv"
    prcc_rows = _read_csv(prcc_path)
    prcc_rows = [r for r in prcc_rows if str(r.get("scenario_id")) != sid]
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
    _write_csv(prcc_path, prcc_rows, fieldnames=["scenario_id", "output", "param", "prcc"])

    spear_path = out_dir / "global_spearman.csv"
    spear_rows = _read_csv(spear_path)
    spear_rows = [r for r in spear_rows if str(r.get("scenario_id")) != sid]
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
            spear_rows.append({"scenario_id": sid, "output": out_name, "param": k, "spearman": float(table.get(k, float("nan")))})
    _write_csv(spear_path, spear_rows, fieldnames=["scenario_id", "output", "param", "spearman"])

    # 5) global_prcc_top5.csv：写作辅助（只追加该场景）
    top_path = out_dir / "global_prcc_top5.csv"
    top_rows = _read_csv(top_path)
    top_rows = [r for r in top_rows if str(r.get("scenario_id")) != sid]
    prcc_map = {
        "tte_mean_h": g["prcc_tte"],
        "tte_std_h": g["prcc_tte_std"],
        "tte_cv": g["prcc_tte_cv"],
        "tte_spread_h": g["prcc_tte_spread_h"],
        "p_cutoff": g["prcc_p_cutoff"],
        "p_insufficient_power": g["prcc_p_insufficient_power"],
        "min_headroom_margin": g["prcc_min_headroom_margin"],
    }
    for out_name, table in prcc_map.items():
        xs = [(str(k), float(table.get(k, float("nan")))) for k in q3_param_names()]
        xs = [(k, v) for (k, v) in xs if np.isfinite(v)]
        xs.sort(key=lambda kv: abs(kv[1]), reverse=True)
        for rank, (param, v) in enumerate(xs[:5], start=1):
            top_rows.append({"scenario_id": sid, "output": out_name, "rank": int(rank), "param": str(param), "prcc": float(v)})
    _write_csv(top_path, top_rows, fieldnames=["scenario_id", "output", "rank", "param", "prcc"])

    print(f"[ok] appended global sensitivity for scenario={sid} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

