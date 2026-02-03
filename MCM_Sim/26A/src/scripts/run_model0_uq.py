#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：对 Model-0 做不确定性传播（输出 TTE 分位数与粗略敏感性）。"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis import pearson_corr, quantile
from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0
from mcm26a.uq import apply_uq_sample, sample_model0_uq


def _fmt(x: float | None, *, width: int = 8, digits: int = 2) -> str:
    if x is None:
        return "-".rjust(width)
    return f"{x:{width}.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Model-0 不确定性传播（UQ）")
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
    ap.add_argument("--samples", type=int, default=500, help="采样次数（建议 200~5000）")
    ap.add_argument("--seed", type=int, default=0, help="随机种子（可复现）")
    ap.add_argument("--include-variants", action="store_true", help="同时跑所有 variants")
    ap.add_argument("--scenario-id", default="", help="只跑指定场景（例如 S2_navigation）")
    ap.add_argument("--variant", default="", help="只跑指定 variant（例如 rural_poor_signal）")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    base_power = PowerParams0.from_json(args.power)
    base_battery = BatteryParams0.from_json(args.phone)

    rng = random.Random(int(args.seed))

    scenario_ids = list(raw.get("scenarios", {}).keys())
    if args.scenario_id:
        scenario_ids = [args.scenario_id]

    print("Model-0 不确定性传播（TTE 单位：小时）")
    print(f"- 样本数: {int(args.samples)}  seed={int(args.seed)}")
    print(f"- 基准电池能量: {base_battery.energy_Wh:.2f} Wh (soc_min={base_battery.soc_min:.3f})")
    print(f"- 初始 SOC: {float(args.soc0):.3f}")
    print("")

    header = f"{'scenario':<14} {'variant':<18} {'P05':>8} {'P50':>8} {'P95':>8} {'mean':>8}  title"
    print(header)
    print("-" * len(header))

    for sid in scenario_ids:
        variants = {"-": None}
        if args.include_variants:
            variants = {"-": None}
            variants.update({k: k for k in raw["scenarios"][sid].get("variants", {}).keys()})
        if args.variant:
            variants = {args.variant: args.variant}

        for vname, v in variants.items():
            sc = materialize_scenario(raw, sid, variant=v)

            ttes: list[float] = []
            # 记录采样值用于粗略敏感性（相关性）
            xs = {
                "battery_energy_scale": [],
                "base_scale": [],
                "screen_scale": [],
                "cpu_scale": [],
                "gpu_scale": [],
                "gps_scale": [],
                "background_scale": [],
                "radio_scale": [],
                "poor_signal_multiplier": [],
            }

            for _ in range(int(args.samples)):
                s = sample_model0_uq(rng)
                p, b = apply_uq_sample(base_power, base_battery, s)
                res = simulate_model0(sc, power_params=p, battery_params=b, soc0=float(args.soc0))
                if res.tte_h is None:
                    continue
                ttes.append(float(res.tte_h))
                xs["battery_energy_scale"].append(float(s.battery_energy_scale))
                xs["base_scale"].append(float(s.base_scale))
                xs["screen_scale"].append(float(s.screen_scale))
                xs["cpu_scale"].append(float(s.cpu_scale))
                xs["gpu_scale"].append(float(s.gpu_scale))
                xs["gps_scale"].append(float(s.gps_scale))
                xs["background_scale"].append(float(s.background_scale))
                xs["radio_scale"].append(float(s.radio_scale))
                xs["poor_signal_multiplier"].append(float(s.poor_signal_multiplier))

            if not ttes:
                print(f"{sid:<14} {vname:<18} {'-':>8} {'-':>8} {'-':>8} {'-':>8}  {sc.title_zh}")
                continue

            p05 = quantile(ttes, 0.05)
            p50 = quantile(ttes, 0.50)
            p95 = quantile(ttes, 0.95)
            mean = sum(ttes) / len(ttes)
            print(f"{sid:<14} {vname:<18} {_fmt(p05)} {_fmt(p50)} {_fmt(p95)} {_fmt(mean)}  {sc.title_zh}")

            # 粗略敏感性：与 TTE 的相关系数（按绝对值排序取前 3）
            corrs = []
            for k, vals in xs.items():
                if len(vals) < 2:
                    continue
                corrs.append((k, pearson_corr(vals, ttes)))
            corrs.sort(key=lambda kv: -abs(kv[1]))
            top = corrs[:3]
            if top:
                top_str = ", ".join([f"{k}:{v:+.2f}" for k, v in top])
                print(f"{'':<34}  top corr => {top_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

