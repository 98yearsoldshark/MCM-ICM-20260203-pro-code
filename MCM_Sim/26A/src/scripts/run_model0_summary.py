#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-0 批量计算标准场景的 TTE（耗尽时间）与功耗分解。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0


def _fmt_hours(t_h: float | None) -> str:
    if t_h is None:
        return "-"
    return f"{t_h:8.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-0 场景批量 TTE 计算")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON 路径",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数 JSON 路径",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v0.json"),
        help="电池参数 JSON 路径",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--include-variants", action="store_true", help="同时跑所有 variants")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams0.from_json(args.phone)

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if not scenario_ids:
        print("未找到任何 scenarios。", file=sys.stderr)
        return 2

    print("Model-0 标准场景 TTE 汇总（单位：小时）")
    print(f"- 电池能量: {battery_params.energy_Wh:.2f} Wh  (soc_min={battery_params.soc_min:.3f})")
    print(f"- 初始 SOC: {float(args.soc0):.3f}")
    print("")
    print(f"{'scenario':<14} {'variant':<18} {'TTE(h)':>10} {'AvgP(W)':>10}  title")
    print("-" * 72)

    for sid in scenario_ids:
        base = materialize_scenario(raw, sid)
        res = simulate_model0(
            base,
            power_params=power_params,
            battery_params=battery_params,
            soc0=float(args.soc0),
            variant=None,
        )
        avgp = "-" if res.avg_power_W is None else f"{res.avg_power_W:10.2f}"
        print(f"{sid:<14} {'-':<18} {_fmt_hours(res.tte_h)} {avgp}  {base.title_zh}")

        if args.include_variants:
            variants = raw["scenarios"][sid].get("variants", {})
            for vname in variants.keys():
                sc = materialize_scenario(raw, sid, variant=vname)
                res = simulate_model0(
                    sc,
                    power_params=power_params,
                    battery_params=battery_params,
                    soc0=float(args.soc0),
                    variant=vname,
                )
                avgp = "-" if res.avg_power_W is None else f"{res.avg_power_W:10.2f}"
                print(f"{sid:<14} {vname:<18} {_fmt_hours(res.tte_h)} {avgp}  {sc.title_zh}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

