#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只生成 Q3 的“电池模型复杂度对照（Model-1/2/3）”报表。

动机：
- Q3 的复杂度对照经常需要反复调整展示指标（TTE/温度/风险）与场景变体（cold/hot）；
- 但完整 run_q3_report.py 会同时重算 PRCC/局部敏感性/消融等，耗时很长；
- 因此提供一个轻量脚本，仅输出 battery_model_ablation.csv，便于快速迭代图 06。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q3_sensitivity import compute_battery_model_ablation
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


def _pick_cold_hot_variants(raw: dict, scenario_id: str) -> list[str]:
    spec = (raw.get("scenarios", {}) or {}).get(str(scenario_id), {}) or {}
    variants = spec.get("variants", {}) or {}
    out: list[str] = []
    if "cold_outdoor" in variants:
        out.append("cold_outdoor")
    if "hot_summer" in variants:
        out.append("hot_summer")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 电池模型复杂度对照报表（仅此一项）")
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
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0")
    ap.add_argument("--replicates", type=int, default=40, help="每个模型的随机种子重复次数（越大越稳）")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    ap.add_argument(
        "--with-cold-hot",
        action="store_true",
        help="额外对每个场景可用的 cold_outdoor / hot_summer 变体也做一次复杂度对照（用于放大热效应）。",
    )
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

    seed_base = int(args.seed) * 1_000_000
    seeds = [seed_base + 30_000 + i for i in range(int(args.replicates))]

    rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        # baseline
        sc = materialize_scenario(raw, sid)
        for r in compute_battery_model_ablation(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(args.dt),
            soc0=float(args.soc0),
            seeds=seeds,
        ):
            rows.append({"scenario_id": sid, **r})

        if bool(args.with_cold_hot):
            for vname in _pick_cold_hot_variants(raw, sid):
                scv = materialize_scenario(raw, sid, variant=vname)
                for r in compute_battery_model_ablation(
                    scv,
                    base_power=power,
                    base_batt=batt,
                    power0_dummy=power0_dummy,
                    dt_s=float(args.dt),
                    soc0=float(args.soc0),
                    seeds=seeds,
                ):
                    # Scenario 本身不保存 variant 字段；为了让报表可追溯，这里手工写入变体名。
                    r2 = dict(r)
                    r2["variant"] = str(vname)
                    rows.append({"scenario_id": sid, **r2})

    # 汇总列名（避免丢列）
    fieldnames: list[str] = ["scenario_id"]
    seen = set(fieldnames)
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    out_csv = out_dir / "battery_model_ablation.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[q3-battery-model] wrote -> {out_csv} (rows={len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
