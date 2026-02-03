#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-0 对“省电策略/反事实”做快速扫描。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import default_policy_actions, evaluate_policies_model0
from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-0 策略扫描")
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
    ap.add_argument("--scenario-id", default="", help="只跑指定场景（例如 S2_navigation）")
    ap.add_argument("--variant", default="", help="使用指定 variant（例如 rural_poor_signal）")
    ap.add_argument("--include-variants", action="store_true", help="同时跑该场景的所有 variants")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams0.from_json(args.phone)

    actions = default_policy_actions()

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if args.scenario_id:
        scenario_ids = [args.scenario_id]

    print("Model-0 策略/反事实扫描（单位：小时）")
    print(f"- 电池能量: {battery_params.energy_Wh:.2f} Wh (soc_min={battery_params.soc_min:.3f})")
    print(f"- 初始 SOC: {float(args.soc0):.3f}")
    print("")

    for sid in scenario_ids:
        variants: dict[str, str | None] = {"-": None}
        if args.include_variants:
            variants = {"-": None}
            variants.update({k: k for k in raw["scenarios"][sid].get("variants", {}).keys()})
        if args.variant:
            variants = {args.variant: args.variant}

        for vname, v in variants.items():
            sc = materialize_scenario(raw, sid, variant=v)
            baseline, effects = evaluate_policies_model0(
                sc,
                power_params=power_params,
                battery_params=battery_params,
                soc0=float(args.soc0),
                actions=actions,
            )

            print(f"[{sid} | variant={vname}] {sc.title_zh}")
            print(
                f"baseline TTE(h)={_fmt(baseline.tte_h)}  AvgP(W)={_fmt(baseline.avg_power_W, width=8, digits=2)}"
            )
            print(f"{'action':<14} {'TTE(h)':>10} {'Δh':>10} {'Δ%':>8}  title")
            print("-" * 70)
            for e in effects:
                dp = None if e.delta_tte_pct is None else e.delta_tte_pct
                print(
                    f"{e.action_id:<14} {_fmt(e.tte_h, width=10)} {_fmt(e.delta_tte_h, width=10)} {_fmt(dp, width=8)}  {e.title_zh}"
                )
            print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
