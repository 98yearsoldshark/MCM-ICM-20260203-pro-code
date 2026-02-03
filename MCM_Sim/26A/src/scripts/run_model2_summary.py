#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-2（ECM + 热模型）批量计算标准场景的 TTE，并输出温升信息。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams2Thermal
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model2_thermal


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-2（热-电耦合 ECM）场景批量仿真")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON 路径",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数 JSON 路径（Model-2 仍复用 Model-0 的功耗分解）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v2_thermal.json"),
        help="电池参数 JSON 路径（含 ECM + thermal 参数）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--temp0", type=float, default=float("nan"), help="初始温度（°C）；不填则用配置中的 T0_C")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒），建议 0.5~5")
    ap.add_argument("--include-variants", action="store_true", help="同时跑所有 variants")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams2Thermal.from_json(args.phone)

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if not scenario_ids:
        print("未找到任何 scenarios。", file=sys.stderr)
        return 2

    temp0 = None if str(args.temp0) == "nan" else float(args.temp0)
    t0_print = battery_params.t0_C if temp0 is None else float(temp0)

    print("Model-2（ECM + 热模型）标准场景汇总")
    print(
        f"- cutoff: {battery_params.v_cut_V:.2f} V,  R0_ref={battery_params.r0_ohm_ref:.3f}Ω@{battery_params.t_ref_C:.1f}°C,  "
        f"Q_ref={battery_params.capacity_Ah_ref:.2f}Ah"
    )
    print(
        f"- 热参数: C_th={battery_params.c_th_J_per_K:.0f} J/K,  R_th={battery_params.r_th_K_per_W:.2f} K/W,  "
        f"eta_heat={battery_params.eta_device_heat:.2f}"
    )
    print(f"- 初始 SOC: {float(args.soc0):.3f}  初始温度: {t0_print:.1f}°C  dt={float(args.dt):.2f}s")
    print("")
    print(f"{'scenario':<14} {'variant':<18} {'TTE(h)':>10} {'T_end(°C)':>10} {'T_peak(°C)':>11} {'status':>18}  title")
    print("-" * 98)

    for sid in scenario_ids:
        base = materialize_scenario(raw, sid)
        res = simulate_model2_thermal(
            base,
            power_params=power_params,
            battery_params=battery_params,
            soc0=float(args.soc0),
            temp0_C=temp0,
            variant=None,
            dt_s=float(args.dt),
        )
        print(
            f"{sid:<14} {'-':<18} {_fmt(res.tte_h, width=10)} {_fmt(res.temp_end_C, width=10, digits=1)} "
            f"{_fmt(res.temp_peak_C, width=11, digits=1)} {res.status:>18}  {base.title_zh}"
        )

        if args.include_variants:
            variants = raw["scenarios"][sid].get("variants", {})
            for vname in variants.keys():
                sc = materialize_scenario(raw, sid, variant=vname)
                res = simulate_model2_thermal(
                    sc,
                    power_params=power_params,
                    battery_params=battery_params,
                    soc0=float(args.soc0),
                    temp0_C=temp0,
                    variant=vname,
                    dt_s=float(args.dt),
                )
                print(
                    f"{sid:<14} {vname:<18} {_fmt(res.tte_h, width=10)} {_fmt(res.temp_end_C, width=10, digits=1)} "
                    f"{_fmt(res.temp_peak_C, width=11, digits=1)} {res.status:>18}  {sc.title_zh}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

