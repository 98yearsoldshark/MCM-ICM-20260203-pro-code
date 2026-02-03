#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-3（ECM + 热 + 老化）批量计算标准场景的 TTE，并输出老化状态变化。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-3（热-电耦合 + 老化）场景批量仿真")
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
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（含 ECM + thermal + aging 参数）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--temp0", type=float, default=float("nan"), help="初始温度（°C）；不填则用配置中的 T0_C")
    ap.add_argument("--cap-loss0", type=float, default=0.0, help="初始容量损失比例 cap_loss0（0~1）")
    ap.add_argument("--r0-grow0", type=float, default=0.0, help="初始 R0 增长比例 r0_growth0（>=0）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒），建议 0.5~5")
    ap.add_argument("--include-variants", action="store_true", help="同时跑所有 variants")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams3Aging.from_json(args.phone)

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if not scenario_ids:
        print("未找到任何 scenarios。", file=sys.stderr)
        return 2

    temp0 = None if str(args.temp0) == "nan" else float(args.temp0)
    t0_print = battery_params.t0_C if temp0 is None else float(temp0)

    print("Model-3（ECM + 热 + 老化）标准场景汇总")
    print(
        f"- cutoff: {battery_params.v_cut_V:.2f} V,  R0_ref={battery_params.r0_ohm_ref:.3f}Ω@{battery_params.t_ref_C:.1f}°C,  "
        f"Q_ref={battery_params.capacity_Ah_ref:.2f}Ah"
    )
    print(
        f"- 老化系数: cap/Ah={battery_params.cap_fade_per_Ah:.2e}, R0/Ah={battery_params.r0_growth_per_Ah:.2e}, "
        f"cap/day={battery_params.cap_fade_per_day:.2e}, R0/day={battery_params.r0_growth_per_day:.2e}"
    )
    print(
        f"- 初始：SOC0={float(args.soc0):.3f}, T0={t0_print:.1f}°C, cap_loss0={float(args.cap_loss0):.4f}, "
        f"r0_growth0={float(args.r0_grow0):.4f}, dt={float(args.dt):.2f}s"
    )
    print("")
    print(
        f"{'scenario':<14} {'variant':<18} {'TTE(h)':>10} {'T_peak':>9} {'cap_loss':>10} {'r0_grow':>9} {'status':>18}  title"
    )
    print("-" * 108)

    def _run_one(sid: str, vname: str, v: str | None) -> None:
        sc = materialize_scenario(raw, sid, variant=v)
        res = simulate_model3_aging(
            sc,
            power_params=power_params,
            battery_params=battery_params,
            soc0=float(args.soc0),
            temp0_C=temp0,
            cap_loss0_frac=float(args.cap_loss0),
            r0_growth0_frac=float(args.r0_grow0),
            r1_growth0_frac=float(args.r0_grow0),
            variant=vname,
            dt_s=float(args.dt),
        )
        print(
            f"{sid:<14} {vname:<18} {_fmt(res.tte_h, width=10)} {_fmt(res.temp_peak_C, width=9, digits=1)} "
            f"{_fmt(res.cap_loss_end_frac, width=10, digits=4)} {_fmt(res.r0_growth_end_frac, width=9, digits=4)} {res.status:>18}  {sc.title_zh}"
        )

    for sid in scenario_ids:
        _run_one(sid, "-", None)
        if args.include_variants:
            for vname in raw["scenarios"][sid].get("variants", {}).keys():
                _run_one(sid, vname, vname)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

