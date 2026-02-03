#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：生成“baseline vs variants”的 TTE 统计表（用于图 02 同源化）。

动机（对齐赛题 Requirements 2 的高分口径）：
- Q2 需要回答：哪些“条件/活动”会显著缩短续航（conditions），以及缩短多少（ΔTTE 或比例）。
- 我们的图 02（baseline vs variants）如果每次都“即时仿真”，很容易出现：
  - 图与 data.csv 不同源（难追溯）
  - seeds 数偏小导致排序抖动（不够“硬证据”）

本脚本专门输出一份可复现 CSV：
- out_reports/q2/variants_stats.csv

后续：
- make_q2_plots.py 会优先读取该 CSV 生成图 02（以及温度 variants 图），
  从而保证 figure.png 与 other/data.csv 同源。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.q2_plots import _scenario_title, _variant_label_zh


def _quantile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    return float(np.quantile(np.array(xs, dtype=float), q))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("variants_stats 为空：请检查 scenarios_v0.json 的 variants 定义是否存在")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 variants 统计表（baseline vs variants）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q2"), help="输出目录（默认 out_reports/q2）")
    ap.add_argument("--out-name", default="variants_stats.csv", help="输出 CSV 文件名")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3：热-电-老化）",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="仿真积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0（默认 1.0）")
    ap.add_argument("--seeds", type=int, default=50, help="每个（场景,variant）重复的随机种子数（越大越稳）")
    ap.add_argument("--seed0", type=int, default=1000, help="随机种子起点（可复现）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_csv = out_dir / str(args.out_name)

    raw = load_scenarios_json(Path(args.scenarios))
    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    sids = list(raw.get("scenarios", {}).keys())
    rows: list[dict[str, object]] = []
    for sid_idx, sid in enumerate(sids):
        spec = raw["scenarios"][sid]
        variants = list((spec.get("variants", {}) or {}).keys())
        vnames = ["-"] + [str(v) for v in variants]

        for v_idx, vname in enumerate(vnames):
            sc = materialize_scenario(raw, sid, variant=(None if vname == "-" else str(vname)))
            ambient = float(sc.schedule[0].ambient_temp_c)

            ttes: list[float] = []
            statuses: list[str] = []
            soc_end: list[float] = []
            avgp: list[float] = []
            for k in range(int(args.seeds)):
                seed = int(args.seed0) + sid_idx * 10_000 + v_idx * 100 + k
                pm = StatefulPowerModel1(power1, seed=seed)
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
                statuses.append(str(r.status))
                soc_end.append(float(r.soc_end))
                if r.avg_power_W is not None:
                    avgp.append(float(r.avg_power_W))

            denom = float(max(1, int(args.seeds)))
            row = {
                "scenario_id": str(sid),
                "scenario_title_zh": _scenario_title(raw, str(sid)),
                "variant": str(vname),
                "variant_label_zh": _variant_label_zh(str(vname)),
                "ambient_temp_c": float(ambient),
                "soc0": float(args.soc0),
                "dt_s": float(args.dt),
                "n_seeds": int(args.seeds),
                "n": int(len(ttes)),
                "mean_h": float(np.mean(np.array(ttes, dtype=float))) if ttes else float("nan"),
                "p05_h": _quantile(ttes, 0.05),
                "p50_h": _quantile(ttes, 0.50),
                "p95_h": _quantile(ttes, 0.95),
                "p_cutoff": float(sum(1 for s in statuses if s == "cutoff")) / denom,
                "p_soc_min": float(sum(1 for s in statuses if s == "soc_min")) / denom,
                "p_insufficient_power": float(sum(1 for s in statuses if s == "insufficient_power")) / denom,
                "soc_end_mean": float(np.mean(np.array(soc_end, dtype=float))) if soc_end else float("nan"),
                "avg_power_W_mean": float(np.mean(np.array(avgp, dtype=float))) if avgp else float("nan"),
            }
            rows.append(row)

    # 基线放前（同一场景内）
    rows.sort(key=lambda r: (str(r["scenario_id"]), 0 if str(r.get("variant", "")) == "-" else 1, str(r.get("variant", ""))))

    _write_csv(out_csv, rows)
    print(f"已生成：{out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

