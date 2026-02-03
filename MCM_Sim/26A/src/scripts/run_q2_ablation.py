#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：Q2 小型消融实验（ablation）。

目的：
- 验证“RRC 尾态 / 后台 Poisson / 交互项 / 弱信号惩罚”等机制是否按预期影响续航；
- 避免出现“加入机制反而变差但原因不明”的情况（为冲 Z 奖准备证据链）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.power.model1_stateful import InteractionParams1, PoissonBackgroundParams1, RRCParams1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging


def _make_ablation_params(p: PowerParams1Stateful, *, ablation_id: str) -> PowerParams1Stateful:
    """根据 ablation_id 返回改动后的参数。"""

    if ablation_id == "full":
        return p

    if ablation_id == "no_bg_poisson":
        bg = PoissonBackgroundParams1(
            lambda_per_s={k: 0.0 for k in p.background_poisson.lambda_per_s.keys()},
            data_mb_per_wake=0.0,
            cpu_wake_W=float(p.background_poisson.cpu_wake_W),
            cpu_wake_duration_s=float(p.background_poisson.cpu_wake_duration_s),
        )
        return replace(p, background_poisson=bg)

    if ablation_id == "no_interaction":
        inter = InteractionParams1(
            beta_screen_net_W=0.0,
            beta_net_highcpu_W=0.0,
            beta_screen_highcpu_W=0.0,
            cpu_high_threshold=float(p.interaction.cpu_high_threshold),
        )
        return replace(p, interaction=inter)

    if ablation_id == "no_tail":
        # tau_tail=0，且把 TAIL 状态功耗设为 IDLE（近似移除尾态能量）
        tau = {k: 0.0 for k in p.rrc.tau_tail_s.keys()}
        p_state = {}
        for mode, table in p.rrc.p_state_W.items():
            idle = float(table.get("IDLE", 0.0))
            p_state[mode] = dict(table)
            p_state[mode]["TAIL"] = idle
        rrc = RRCParams1(
            tau_tail_s=tau,
            p_state_W=p_state,
            e_per_mb_J=dict(p.rrc.e_per_mb_J),
            signal_psi=dict(p.rrc.signal_psi),
            throughput_MBps_by_activity=dict(p.rrc.throughput_MBps_by_activity),
            burst_rate_per_s_by_activity=dict(p.rrc.burst_rate_per_s_by_activity),
            burst_mb_by_activity=dict(p.rrc.burst_mb_by_activity),
        )
        return replace(p, rrc=rrc)

    if ablation_id == "no_signal_penalty":
        psi = dict(p.rrc.signal_psi)
        psi["poor"] = 1.0
        rrc = RRCParams1(
            tau_tail_s=dict(p.rrc.tau_tail_s),
            p_state_W=dict(p.rrc.p_state_W),
            e_per_mb_J=dict(p.rrc.e_per_mb_J),
            signal_psi=psi,
            throughput_MBps_by_activity=dict(p.rrc.throughput_MBps_by_activity),
            burst_rate_per_s_by_activity=dict(p.rrc.burst_rate_per_s_by_activity),
            burst_mb_by_activity=dict(p.rrc.burst_mb_by_activity),
        )
        return replace(p, rrc=rrc)

    raise ValueError(f"unknown ablation_id: {ablation_id!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 消融实验（Model-3 + stateful 功耗）")
    ap.add_argument("--out", default=str(SRC_DIR / "out_reports" / "q2" / "ablation.csv"), help="输出 CSV 路径")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="no7 升级功耗参数 JSON（AndroWatts 多目标校准版：更贴近公开测量的总功耗量级，且兼顾主要组件分解）",
    )
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"), help="电池参数 JSON（Model-3）")
    ap.add_argument("--dt", type=float, default=5.0, help="积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC")
    ap.add_argument("--seeds", type=int, default=30, help="每个场景平均的随机种子数")
    args = ap.parse_args()

    raw = load_scenarios_json(args.scenarios)
    p_full = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    ablations = [
        ("full", "完整：RRC+Poisson后台+交互+弱信号"),
        ("no_bg_poisson", "去掉后台 Poisson 唤醒"),
        ("no_interaction", "去掉交互项（协同作用）"),
        ("no_tail", "去掉 RRC 尾态能量"),
        ("no_signal_penalty", "去掉弱信号惩罚（poor=1）"),
    ]

    rows: list[dict[str, object]] = []
    for sid_idx, sid in enumerate(raw.get("scenarios", {}).keys()):
        sc = materialize_scenario(raw, sid)
        for ab_id, ab_title in ablations:
            p = _make_ablation_params(p_full, ablation_id=ab_id)
            ttes: list[float] = []
            for k in range(int(args.seeds)):
                seed = 1000 + sid_idx * 100 + k
                pm = StatefulPowerModel1(p, seed=seed)
                r = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=batt,
                    soc0=float(args.soc0),
                    dt_s=float(args.dt),
                )
                if r.tte_h is not None:
                    ttes.append(float(r.tte_h))
            rows.append(
                {
                    "scenario_id": sid,
                    "ablation_id": ab_id,
                    "ablation_zh": ab_title,
                    "n": len(ttes),
                    "mean_tte_h": float(np.mean(ttes)) if ttes else float("nan"),
                    "p05_h": float(np.quantile(np.array(ttes, dtype=float), 0.05)) if ttes else float("nan"),
                    "p50_h": float(np.quantile(np.array(ttes, dtype=float), 0.50)) if ttes else float("nan"),
                    "p95_h": float(np.quantile(np.array(ttes, dtype=float), 0.95)) if ttes else float("nan"),
                }
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["scenario_id", "ablation_id", "ablation_zh", "n", "mean_tte_h", "p05_h", "p50_h", "p95_h"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"已写入：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
