#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 Model-3（热-电耦合 + 老化）对策略做扫描（同时输出续航/温升/老化差异）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import PolicyAction3, evaluate_policies_model3
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0
from mcm26a.scenarios import (
    disable_gps,
    force_radio_mode,
    load_scenarios_json,
    materialize_scenario,
    set_background_level,
    set_brightness_for_screen_on,
    set_signal_quality,
)


def _actions() -> list[PolicyAction3]:
    return [
        PolicyAction3(
            action_id="brightness_100",
            title_zh="降低亮度至 100 nits（仅屏幕点亮段）",
            description_zh="评估亮度下降带来的续航提升/降温/延寿效果。",
            apply=lambda sc: set_brightness_for_screen_on(sc, brightness_nits=100.0),
        ),
        PolicyAction3(
            action_id="disable_gps",
            title_zh="关闭 GPS",
            description_zh="评估 GPS 的边际耗电/温升/老化影响。",
            apply=disable_gps,
        ),
        PolicyAction3(
            action_id="force_wifi",
            title_zh="强制使用 Wi-Fi（假设可用）",
            description_zh="对比 Wi-Fi 与蜂窝网络的能耗差异。",
            apply=lambda sc: force_radio_mode(sc, radio_mode="wifi"),
        ),
        PolicyAction3(
            action_id="good_signal",
            title_zh="改善信号（poor -> good）",
            description_zh="用于解释“信号差导致异常耗电/温升/老化”的机理影响。",
            apply=lambda sc: set_signal_quality(sc, signal_quality="good"),
        ),
        PolicyAction3(
            action_id="bg_low",
            title_zh="限制后台（统一设为 low）",
            description_zh="评估后台活动的边际耗电。",
            apply=lambda sc: set_background_level(sc, level="low"),
        ),
    ]


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-3 策略扫描（续航-温升-老化）")
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
        help="电池参数 JSON 路径（含老化参数）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--temp0", type=float, default=float("nan"), help="初始温度（°C）；不填则用配置中的 T0_C")
    ap.add_argument("--cap-loss0", type=float, default=0.0, help="初始容量损失比例 cap_loss0（0~1）")
    ap.add_argument("--r0-grow0", type=float, default=0.0, help="初始 R0 增长比例 r0_growth0（>=0）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒），建议 0.5~5")
    ap.add_argument("--scenario-id", default="", help="只跑指定场景（例如 S2_navigation）")
    ap.add_argument("--variant", default="", help="使用指定 variant（例如 rural_poor_signal）")
    ap.add_argument("--include-variants", action="store_true", help="同时跑该场景的所有 variants")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    power_params = PowerParams0.from_json(args.power)
    battery_params = BatteryParams3Aging.from_json(args.phone)
    actions = _actions()

    temp0 = None if str(args.temp0) == "nan" else float(args.temp0)

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if args.scenario_id:
        scenario_ids = [args.scenario_id]

    print("Model-3 策略/反事实扫描（续航-温升-老化）")
    print(
        f"- 老化系数: cap/Ah={battery_params.cap_fade_per_Ah:.2e}, R0/Ah={battery_params.r0_growth_per_Ah:.2e}, "
        f"cap/day={battery_params.cap_fade_per_day:.2e}, R0/day={battery_params.r0_growth_per_day:.2e}"
    )
    print(f"- 初始：SOC0={float(args.soc0):.3f}, cap_loss0={float(args.cap_loss0):.4f}, r0_growth0={float(args.r0_grow0):.4f}, dt={float(args.dt):.2f}s")
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
            baseline, effects = evaluate_policies_model3(
                sc,
                power_params=power_params,
                battery_params=battery_params,
                soc0=float(args.soc0),
                temp0_C=temp0,
                cap_loss0_frac=float(args.cap_loss0),
                r0_growth0_frac=float(args.r0_grow0),
                r1_growth0_frac=float(args.r0_grow0),
                actions=actions,
                dt_s=float(args.dt),
            )

            print(f"[{sid} | variant={vname}] {sc.title_zh}")
            print(
                f"baseline: TTE(h)={_fmt(baseline.tte_h)}  T_peak={_fmt(baseline.temp_peak_C, digits=1)}°C  "
                f"cap_loss={_fmt(baseline.cap_loss_end_frac, digits=4)}  r0_grow={_fmt(baseline.r0_growth_end_frac, digits=4)}  status={baseline.status}"
            )
            print(
                f"{'action':<14} {'Δh':>10} {'ΔT_peak':>10} {'Δcap_loss':>10} {'Δr0_grow':>10} {'status':>12}  title"
            )
            print("-" * 100)
            for e in effects:
                print(
                    f"{e.action_id:<14} {_fmt(e.delta_tte_h, width=10)} {_fmt(e.delta_temp_peak_C, width=10, digits=1)} "
                    f"{_fmt(e.delta_cap_loss_frac, width=10, digits=4)} {_fmt(e.delta_r0_growth_frac, width=10, digits=4)} {e.status:>12}  {e.title_zh}"
                )
            print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

