#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：输出 Model-0 的功耗/能耗贡献分解（按组件拆分）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import component_energies
from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-0 能耗贡献分解")
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
    ap.add_argument("--scenario-id", required=True, help="要分解的场景（例如 S1_video）")
    ap.add_argument("--variant", default="", help="可选 variant（例如 cellular_poor_signal）")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams0.from_json(args.phone)

    sc = materialize_scenario(raw, args.scenario_id, variant=(args.variant or None))
    res = simulate_model0(sc, power_params=power_params, battery_params=battery_params, soc0=float(args.soc0))

    print("Model-0 能耗贡献分解（单位：Wh / %）")
    print(f"- 场景: {args.scenario_id}  variant={args.variant or '-'}  {sc.title_zh}")
    print(f"- TTE(h): {_fmt(res.tte_h)}   AvgP(W): {_fmt(res.avg_power_W, width=8, digits=2)}")
    print(f"- 总耗能(Wh): {_fmt(res.energy_used_Wh, width=8, digits=2)} / 电池(Wh): {_fmt(res.energy_capacity_Wh, width=8, digits=2)}")
    print("")
    print(f"{'component':<14} {'Wh':>10} {'share%':>10}")
    print("-" * 38)
    for ce in component_energies(res):
        print(f"{ce.name:<14} {_fmt(ce.energy_Wh, width=10, digits=2)} {_fmt(ce.share_pct, width=10, digits=2)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

