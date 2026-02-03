#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：不确定性分解（参数 vs 使用波动）sanity check 实验。

动机（对齐赛题 Q3）：
- 图 09 的“参数 vs 使用波动”占比很容易被质疑：是不是算错了？是不是对先验过于主观？
- 我们用两个方向性实验做 sanity check（不追求替代主结果，而是证明逻辑一致）：
  1) 先验收窄（prior_mode=tight）：参数项应下降、使用波动项相对占比应上升；
  2) 增加每个样本内的 seed 重复 K：使用波动项估计更稳定（方差更平滑）。

输出：
- out_reports/q3/sanity_uncertainty_decomp/summary.csv

说明：
- 本脚本只跑“全局采样 + total variance 分解”这一小块，避免重跑 Q3 其它模块导致耗时过大；
- 默认只挑 2 个代表场景（S4_mixed_day, S3_gaming），你可用 --scenarios-ids 扩展到全部。
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

from mcm26a.analysis.q3_sensitivity import compute_global_sensitivity
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("rows 不能为空")
    keys: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _decompose_from_global_result(g: dict[str, object]) -> tuple[float, float, float, float, float]:
    """从 compute_global_sensitivity 的输出做 Var 分解（TTE）。"""

    y_mu = np.asarray(g["y_tte"], dtype=float)  # type: ignore[arg-type]
    y_sig = np.asarray(g["y_tte_std"], dtype=float)  # type: ignore[arg-type]

    y_mu = y_mu[np.isfinite(y_mu)]
    y_sig = y_sig[np.isfinite(y_sig)]

    var_between = float(np.var(y_mu, ddof=1)) if y_mu.size >= 2 else float("nan")
    var_within = float(np.mean(y_sig * y_sig)) if y_sig.size >= 1 else float("nan")
    var_total = float(var_between + var_within) if (np.isfinite(var_between) and np.isfinite(var_within)) else float("nan")
    frac_param = float(var_between / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
    frac_usage = float(var_within / var_total) if (np.isfinite(var_total) and var_total > 0) else float("nan")
    return var_between, var_within, var_total, frac_param, frac_usage


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 不确定性分解 sanity check（参数 vs 使用波动）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q3" / "sanity_uncertainty_decomp"))
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"))
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"))
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--soc0", type=float, default=1.0)
    ap.add_argument("--n-samples", type=int, default=120, help="全局采样样本数 N（越大越稳）")
    ap.add_argument("--seeds-per-sample", type=int, default=6, help="每个样本内的 seed 重复数 K（越大越稳）")
    ap.add_argument(
        "--prior-modes",
        default="default,tight",
        help="逗号分隔：default,tight（tight=先验收窄，用于 sanity check）",
    )
    ap.add_argument(
        "--scenario-ids",
        default="S4_mixed_day,S3_gaming",
        help="逗号分隔：要测试的场景（默认挑 2 个代表：标准一天+高负载）",
    )
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    power = PowerParams1Stateful.from_json(args.power)
    batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    prior_modes = [m.strip() for m in str(args.prior_modes).split(",") if m.strip()]
    scenario_ids = [s.strip() for s in str(args.scenario_ids).split(",") if s.strip()]
    if not prior_modes:
        raise ValueError("prior_modes 不能为空")
    if not scenario_ids:
        raise ValueError("scenario_ids 不能为空")

    rows: list[dict[str, object]] = []
    for mi, pm in enumerate(prior_modes):
        for si, sid in enumerate(scenario_ids):
            sc = materialize_scenario(raw, sid)
            # 让不同 (mode,scenario) 的抽样彼此独立，但仍可复现
            seed = int(args.seed) + 1000 * mi + 100 * si
            g = compute_global_sensitivity(
                sc,
                base_power=power,
                base_batt=batt,
                power0_dummy=power0_dummy,
                dt_s=float(args.dt),
                soc0=float(args.soc0),
                n_samples=int(args.n_samples),
                seeds_per_sample=int(args.seeds_per_sample),
                seed=int(seed),
                battery_model="model3",
                prior_mode=str(pm),  # type: ignore[arg-type]
            )
            var_between, var_within, var_total, frac_param, frac_usage = _decompose_from_global_result(g)
            rows.append(
                {
                    "scenario_id": str(sid),
                    "prior_mode": str(pm),
                    "dt_s": float(args.dt),
                    "soc0": float(args.soc0),
                    "n_samples": int(args.n_samples),
                    "seeds_per_sample": int(args.seeds_per_sample),
                    "seed": int(seed),
                    "var_between_param_h2": float(var_between),
                    "var_within_usage_h2": float(var_within),
                    "var_total_h2": float(var_total),
                    "frac_param": float(frac_param),
                    "frac_usage": float(frac_usage),
                }
            )

            print(
                f"[{sid} | {pm}] frac_param={frac_param:.4f}, frac_usage={frac_usage:.4f} "
                f"(Var_between={var_between:.3g}, Var_within={var_within:.3g})"
            )

    _write_csv(out_dir / "summary.csv", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

