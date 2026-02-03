#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只生成 Q3 的老化扫描报表（aging_scan.csv）。

动机：
- Q3 的“老化敏感性（SOH 扫描）”经常需要反复调整扫描点/样本量/展示口径；
- 但完整的 run_q3_report.py 会同时重算 PRCC、局部敏感性、消融等，耗时较长；
- 因此提供一个“只跑 SOH 扫描”的轻量脚本，便于快速迭代图 03。
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

from mcm26a.analysis.q3_sensitivity import compute_aging_scan
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


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 老化扫描（SOH）报表（仅此一项）")
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
    ap.add_argument("--replicates-aging", type=int, default=40, help="每个 SOH 点的随机种子重复次数")
    ap.add_argument("--seed", type=int, default=7, help="随机种子（可复现）")
    ap.add_argument(
        "--soh-list",
        default="auto",
        help="SOH 扫描列表（逗号分隔）；或填 auto 表示从 battery_state_table 的分位点自动选点",
    )
    ap.add_argument(
        "--battery-state-table",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
        help="电池状态表（用于 SOH 扫描点观测锚定；默认 MCM2026_battery_state_table.csv）",
    )
    ap.add_argument(
        "--soh-quantiles",
        default="0,0.1667,0.3333,0.5,0.6667,0.8333,1",
        help="当 --soh-list=auto 时使用的 SOH 分位点（逗号分隔，范围 0~1）",
    )
    ap.add_argument("--alpha-r", type=float, default=1.5, help="老化增阻强度 alpha_R（R0 增长系数）")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if not scenario_ids:
        raise ValueError("scenarios 配置为空")

    # 采用与 run_q3_report.py 一致的“用途偏移”种子规则，避免不同模块互相污染。
    seed_base = int(args.seed) * 1_000_000
    seeds_aging = [seed_base + 40_000 + i for i in range(int(args.replicates_aging))]

    soh_list_str = str(args.soh_list).strip()
    if soh_list_str.lower() in ("auto", "from_table", "table"):
        qs = _parse_float_list(str(args.soh_quantiles))
        qs = [float(q) for q in qs if 0.0 <= float(q) <= 1.0]
        if not qs:
            raise ValueError("soh-quantiles 不能为空，且必须在 [0,1] 内")
        soh_list = pick_soh_scan_points_from_state_table(Path(args.battery_state_table), quantiles=tuple(qs))
    else:
        soh_list = _parse_float_list(soh_list_str)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    aging_rows: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        rows = compute_aging_scan(
            sc,
            base_power=power,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(args.dt),
            soc0=float(args.soc0),
            seeds=seeds_aging,
            soh_list=soh_list,
            alpha_r=float(args.alpha_r),
        )
        for r in rows:
            aging_rows.append({"scenario_id": sid, **r})

    out_csv = out_dir / "aging_scan.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
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

    print(f"[q3-aging] soh_list={soh_list}")
    print(f"[q3-aging] wrote -> {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

