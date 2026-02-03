#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-3 做多次“放电到 cutoff”循环，观察续航随老化的退化。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import simulate_repeated_cycles_model3
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-3（老化）多循环仿真")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON 路径",
    )
    ap.add_argument(
        "--scenario-id",
        default="S4_mixed_day",
        help="选择一个场景做循环（默认 S4_mixed_day）",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数 JSON 路径",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（含老化参数）",
    )
    ap.add_argument("--n-cycles", type=int, default=50, help="循环次数（每次从满电放电到 cutoff）")
    ap.add_argument("--soc0", type=float, default=1.0, help="每个循环起始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒）")
    ap.add_argument("--temp0", type=float, default=float("nan"), help="初始温度（°C）；不填则用配置中的 T0_C")
    ap.add_argument("--cooldown", action="store_true", help="每个循环开始前把温度重置为 temp0（近似冷却）")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    sc = materialize_scenario(raw, str(args.scenario_id))
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams3Aging.from_json(args.phone)

    temp0 = None if str(args.temp0) == "nan" else float(args.temp0)

    _, summaries = simulate_repeated_cycles_model3(
        sc,
        power_params=power_params,
        battery_params=battery_params,
        n_cycles=int(args.n_cycles),
        soc0=float(args.soc0),
        temp0_C=temp0,
        dt_s=float(args.dt),
        cool_to_temp0_each_cycle=bool(args.cooldown),
    )

    print("Model-3 多循环退化摘要（每行=一次放电到 cutoff）")
    print(
        f"- 场景: {sc.scenario_id} | {sc.title_zh}\n"
        f"- 老化系数: cap/Ah={battery_params.cap_fade_per_Ah:.2e}, R0/Ah={battery_params.r0_growth_per_Ah:.2e}, "
        f"cap/day={battery_params.cap_fade_per_day:.2e}, R0/day={battery_params.r0_growth_per_day:.2e}"
    )
    print("")
    print(f"{'cycle':>6} {'TTE(h)':>10} {'T_peak(°C)':>11} {'cap_loss':>10} {'r0_grow':>9} {'status':>12}")
    print("-" * 68)
    for s in summaries:
        print(
            f"{s.cycle_index:6d} {_fmt(s.tte_h, width=10)} {_fmt(s.temp_peak_C, width=11, digits=1)} "
            f"{_fmt(s.cap_loss_frac, width=10, digits=4)} {_fmt(s.r0_growth_frac, width=9, digits=4)} {s.status:>12}"
        )

    if summaries:
        first = summaries[0]
        last = summaries[-1]
        if first.tte_h is not None and last.tte_h is not None and first.tte_h > 0:
            drop_pct = (last.tte_h - first.tte_h) / first.tte_h * 100.0
            print("")
            print(f"从第 1 次到第 {last.cycle_index} 次：TTE 变化 {drop_pct:+.2f}%（负值表示续航下降）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

