#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：生成“标准化条件开关（OAT）”的 TTE 统计表（用于修正图 02 的 x 轴语义）。

动机（对齐 no12 的写法，避免评委误读）：
- 赛题 Q2 问的是“哪些条件/活动会显著缩短续航？哪些影响 surprisingly little？”
- 若直接用 scenarios_v0.json 里“各场景自带的 variants 名称”拼成一条长 x 轴，
  会出现：
  1) 很多列只对一个场景有效（其余全是 N/A）→ 读者困惑；
  2) variant 名称混杂“蜂窝浏览/流媒体/待机弱信号/休止段弱信号”等场景化措辞→ 不像一个干净的“条件开关”实验。

因此这里按 no12 的建议实现 OAT（One-at-a-time）条件切换：
- 只改一个条件，其余保持 baseline 不变；
- 用统一的条件集合（所有场景共用同一 x 轴）。

输出（同源 CSV）：
- out_reports/q2/conditions_oat_stats.csv

后续：
- make_q2_plots.py 会优先读取该 CSV 生成图 02（矩阵热力图），
  从而保证 figure.png 与 other/data.csv 同源、且 x 轴可解释。
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
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.scenarios.transforms import force_radio_mode, map_segments, set_brightness_for_screen_on, set_signal_quality
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.q2_plots import _scenario_title, _variant_label_zh


def _quantile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    return float(np.quantile(np.array(xs, dtype=float), q))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("conditions_oat_stats 为空：请检查 scenarios_v0.json 是否包含场景")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 OAT 条件统计表（统一 x 轴）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q2"), help="输出目录（默认 out_reports/q2）")
    ap.add_argument("--out-name", default="conditions_oat_stats.csv", help="输出 CSV 文件名")
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
    ap.add_argument("--dt", type=float, default=10.0, help="仿真积分步长（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0（默认 1.0）")
    ap.add_argument("--seeds", type=int, default=50, help="每个（场景,条件）重复的随机种子数（越大越稳）")
    ap.add_argument("--seed0", type=int, default=2000, help="随机种子起点（可复现）")
    # no12 建议：Q2 基准采用室温常值；温度仅做少量对照展示方向性
    ap.add_argument("--baseline-ambient-c", type=float, default=20.0, help="baseline 环境温度（°C），Q2 主结果用常值")
    ap.add_argument("--cold-c", type=float, default=-15.0, help="低温对照（°C）")
    ap.add_argument("--hot-c", type=float, default=38.0, help="高温对照（°C）")
    ap.add_argument("--brightness-high-nits", type=float, default=500.0, help="高亮度条件：screen_on 段亮度（nits）")
    ap.add_argument("--cellular-mode", default="lte", help="蜂窝模式：lte 或 5g（用于 network type 切换）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_csv = out_dir / str(args.out_name)

    raw = load_scenarios_json(Path(args.scenarios))
    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    baseline_amb = float(args.baseline_ambient_c)
    cold_c = float(args.cold_c)
    hot_c = float(args.hot_c)

    def _set_ambient(sc, temp_c: float):
        return map_segments(sc, lambda _i, seg: seg if float(seg.ambient_temp_c) == float(temp_c) else replace(seg, ambient_temp_c=float(temp_c)))

    # 统一 x 轴：条件开关（OAT）
    # 说明：variant 名称会写入 CSV，并由 q2_plots._variant_label_zh 映射为中文坐标
    conditions: list[tuple[str, callable]] = [
        ("-", lambda sc: _set_ambient(sc, baseline_amb)),  # baseline：统一室温口径
        ("cond_brightness_high", lambda sc: set_brightness_for_screen_on(_set_ambient(sc, baseline_amb), brightness_nits=float(args.brightness_high_nits))),
        ("cond_signal_poor", lambda sc: set_signal_quality(_set_ambient(sc, baseline_amb), signal_quality="poor")),
        ("cond_radio_cellular", lambda sc: force_radio_mode(_set_ambient(sc, baseline_amb), radio_mode=str(args.cellular_mode))),
        ("cond_temp_cold", lambda sc: _set_ambient(sc, cold_c)),
        ("cond_temp_hot", lambda sc: _set_ambient(sc, hot_c)),
    ]

    sids = list(raw.get("scenarios", {}).keys())
    rows: list[dict[str, object]] = []
    for sid_idx, sid in enumerate(sids):
        base_sc = materialize_scenario(raw, sid)
        for c_idx, (c_id, c_fn) in enumerate(conditions):
            sc = c_fn(base_sc)
            ambient = float(sc.schedule[0].ambient_temp_c)

            ttes: list[float] = []
            statuses: list[str] = []
            soc_end: list[float] = []
            avgp: list[float] = []
            for k in range(int(args.seeds)):
                seed = int(args.seed0) + sid_idx * 100_000 + c_idx * 1000 + k
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
                "variant": str(c_id),
                "variant_label_zh": _variant_label_zh(str(c_id)),
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

    # baseline 放前（同一场景内）
    rows.sort(key=lambda r: (str(r["scenario_id"]), 0 if str(r.get("variant", "")) == "-" else 1, str(r.get("variant", ""))))

    _write_csv(out_csv, rows)
    print(f"已生成：{out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
