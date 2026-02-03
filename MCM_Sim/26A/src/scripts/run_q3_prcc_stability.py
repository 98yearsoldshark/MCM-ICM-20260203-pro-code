#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：全局敏感性（PRCC）稳定性复现实验（N / K 扩容对照）。

赛题 Q3 要求我们讨论“参数取值变化”带来的预测变化。PRCC 是常用全局敏感性工具，但评委常问：
- “你换个随机种子/多采样一点，排名会不会变？”

本脚本用“嵌套设计”做稳定性检验：
- 一次性用最大样本数 N_max 与最大每样本 seed 重复数 K_max 跑完；
- 然后从同一批原始样本中切片，得到不同 (N, K) 组合的 PRCC；
- 这样差异主要来自“样本量/重复数”本身，而不是换了一套随机数导致不可比。

输出（默认）：
- out_reports/q3/sanity_prcc_stability/
  - seed_runs_long.csv：逐 (scenario, sample, seed_idx) 的 TTE/风险裕量（可追溯）
  - prcc_top5.csv：不同 (N,K) 的 top5 参数列表（TTE 均值 / 欠压裕量）
  - stability_summary.csv：与基线 (N0,K0) 的相似性（Jaccard@Top5）
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q3_sensitivity import q3_param_names, sample_q3_uq, sample_to_row, simulate_tte_replicates
from mcm26a.analysis.sensitivity import prcc
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.uq.q2_uq import apply_q2_uq_sample


def _logu(rng: np.random.Generator, lo: float, hi: float) -> float:
    lo = float(lo)
    hi = float(hi)
    if lo <= 0.0 or hi <= 0.0 or hi < lo:
        raise ValueError("log-uniform 需要 0 < lo <= hi")
    u = float(rng.random())
    return lo * ((hi / lo) ** u)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"rows 为空，无法写入 {path}")
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


def _mean_ignore_invalid(xs: Iterable[float | None]) -> float:
    vals = []
    for x in xs:
        if x is None:
            continue
        x = float(x)
        if np.isfinite(x):
            vals.append(x)
    return float(np.mean(vals)) if vals else float("nan")


def _topk_from_prcc(pr: dict[str, float], *, k: int = 5) -> list[tuple[str, float]]:
    xs = [(name, float(v)) for name, v in pr.items() if np.isfinite(float(v))]
    xs.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return xs[: int(k)]


def _jaccard(a: list[str], b: list[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    return float(len(sa & sb)) / float(len(sa | sb))


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 PRCC 稳定性复现实验（N/K 扩容）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q3" / "sanity_prcc_stability"))
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"))
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"))
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--soc0", type=float, default=1.0)
    ap.add_argument("--scenario-ids", default="S4_mixed_day,S3_gaming", help="逗号分隔，要做稳定性检验的场景")
    ap.add_argument("--n-max", type=int, default=600, help="最大样本数 N_max（一次跑完再切片）")
    ap.add_argument("--k-max", type=int, default=8, help="最大 seeds_per_sample K_max（一次跑完再切片）")
    ap.add_argument("--n-list", default="240,600", help="要比较的 N 列表（逗号分隔）")
    ap.add_argument("--k-list", default="4,8", help="要比较的 K 列表（逗号分隔）")
    ap.add_argument("--seed", type=int, default=1007, help="抽样种子（建议与 run_q3_report 的 seed 对齐：1007）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    base_power = PowerParams1Stateful.from_json(args.power)
    base_batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    scenario_ids = [s.strip() for s in str(args.scenario_ids).split(",") if s.strip()]
    if not scenario_ids:
        raise ValueError("scenario_ids 不能为空")

    n_max = int(args.n_max)
    k_max = int(args.k_max)
    if n_max <= 0 or k_max <= 0:
        raise ValueError("n_max/k_max 必须为正")

    n_list = [int(x.strip()) for x in str(args.n_list).split(",") if x.strip()]
    k_list = [int(x.strip()) for x in str(args.k_list).split(",") if x.strip()]
    if any(n <= 0 or n > n_max for n in n_list):
        raise ValueError("n_list 中存在非法值（必须 1<=N<=n_max）")
    if any(k <= 0 or k > k_max for k in k_list):
        raise ValueError("k_list 中存在非法值（必须 1<=K<=k_max）")

    # 用 numpy RNG 做老化抽样（与 random.Random 解耦也没问题；关键是可复现+嵌套）
    rng_uq = np.random.default_rng(int(args.seed))
    rng_aging = np.random.default_rng(int(args.seed) + 99991)

    seed_run_rows: list[dict[str, object]] = []
    prcc_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)

        # 预分配：每个样本的 K_max 个 seed 输出
        tte = np.full((n_max, k_max), np.nan, dtype=float)
        margin = np.full((n_max, k_max), np.nan, dtype=float)

        # 参数表（用于 PRCC）
        x_cols: dict[str, list[float]] = {k: [] for k in q3_param_names()}

        for i in range(n_max):
            # 1) 参数先验（Q3：default 先验）
            # 这里直接复用项目采样器，保证与主流程一致。
            # 注意：sample_q3_uq 使用 random.Random；我们用 numpy 生成一个 seed 再喂进去，确保嵌套可复现。
            import random

            s = sample_q3_uq(random.Random(int(rng_uq.integers(0, 2**31 - 1))), prior_mode="default")
            p_i, b_i = apply_q2_uq_sample(base_power, base_batt, s)

            # 2) 老化/健康状态（与 compute_global_sensitivity 的 default 逻辑对齐）
            soh = float(rng_aging.uniform(0.7, 1.0))
            alpha_r = float(_logu(rng_aging, 0.1, 3.0))
            cap_loss0 = float(max(0.0, 1.0 - soh))
            r0_growth0 = float(max(0.0, alpha_r) * (1.0 - soh))

            row = sample_to_row(s, soh=soh, alpha_r=alpha_r)
            for k in q3_param_names():
                x_cols[k].append(float(row[k]))

            # 3) 每样本内 seeds（嵌套设计：K=4 是 K=8 的前缀）
            seeds = [int(args.seed) * 1_000_000 + i * 10_000 + j for j in range(k_max)]
            stats = simulate_tte_replicates(
                sc,
                power=p_i,
                batt=b_i,
                power0_dummy=power0_dummy,
                dt_s=float(args.dt),
                soc0=float(args.soc0),
                seeds=seeds,
                battery_model="model3",
                cap_loss0_frac=cap_loss0,
                r0_growth0_frac=r0_growth0,
                r1_growth0_frac=0.0,
            )

            runs = stats["runs"]  # type: ignore[index]
            # runs 按 seeds 顺序生成；我们用 seed_idx 保证可切片
            for j, run in enumerate(runs):
                t = run.get("tte_h", None)
                tte[i, j] = float(t) if (t is not None and np.isfinite(float(t))) else np.nan
                margin[i, j] = float(run.get("min_headroom_margin", float("nan")))
                seed_run_rows.append(
                    {
                        "scenario_id": str(sid),
                        "sample_idx": int(i),
                        "seed_idx": int(j),
                        "seed": int(run.get("seed", seeds[j])),
                        "tte_h": float(tte[i, j]) if np.isfinite(tte[i, j]) else float("nan"),
                        "min_headroom_margin": float(margin[i, j]),
                        "status": str(run.get("status", "")),
                    }
                )

        # ------------------------
        # 计算不同 (N,K) 的 PRCC，并做稳定性对照
        # ------------------------
        # 基线：取 n_list[0], k_list[0]（默认 240,4）
        n0 = int(n_list[0])
        k0 = int(k_list[0])

        def _y_tte_mean(n: int, k: int) -> list[float]:
            out = []
            for i in range(n):
                out.append(_mean_ignore_invalid(tte[i, :k].tolist()))
            return out

        def _y_margin_mean(n: int, k: int) -> list[float]:
            out = []
            for i in range(n):
                out.append(_mean_ignore_invalid(margin[i, :k].tolist()))
            return out

        # 基线 top5
        pr0_tte = prcc({k: v[:n0] for k, v in x_cols.items()}, _y_tte_mean(n0, k0))
        pr0_mar = prcc({k: v[:n0] for k, v in x_cols.items()}, _y_margin_mean(n0, k0))
        top0_tte = [p for p, _ in _topk_from_prcc(pr0_tte, k=5)]
        top0_mar = [p for p, _ in _topk_from_prcc(pr0_mar, k=5)]

        for n in n_list:
            for k in k_list:
                pr_tte = prcc({kk: vv[:n] for kk, vv in x_cols.items()}, _y_tte_mean(n, k))
                pr_mar = prcc({kk: vv[:n] for kk, vv in x_cols.items()}, _y_margin_mean(n, k))

                top_tte = _topk_from_prcc(pr_tte, k=5)
                top_mar = _topk_from_prcc(pr_mar, k=5)

                prcc_rows.append(
                    {
                        "scenario_id": str(sid),
                        "output": "tte_mean_h",
                        "n": int(n),
                        "k": int(k),
                        "top5_params": ",".join([p for p, _ in top_tte]),
                        "top5_prcc": ",".join([f"{v:+.3f}" for _, v in top_tte]),
                    }
                )
                prcc_rows.append(
                    {
                        "scenario_id": str(sid),
                        "output": "min_headroom_margin",
                        "n": int(n),
                        "k": int(k),
                        "top5_params": ",".join([p for p, _ in top_mar]),
                        "top5_prcc": ",".join([f"{v:+.3f}" for _, v in top_mar]),
                    }
                )

                # 稳定性（相对基线 top5 集合）
                summary_rows.append(
                    {
                        "scenario_id": str(sid),
                        "output": "tte_mean_h",
                        "baseline_n": int(n0),
                        "baseline_k": int(k0),
                        "n": int(n),
                        "k": int(k),
                        "jaccard_top5_vs_baseline": float(_jaccard(top0_tte, [p for p, _ in top_tte])),
                    }
                )
                summary_rows.append(
                    {
                        "scenario_id": str(sid),
                        "output": "min_headroom_margin",
                        "baseline_n": int(n0),
                        "baseline_k": int(k0),
                        "n": int(n),
                        "k": int(k),
                        "jaccard_top5_vs_baseline": float(_jaccard(top0_mar, [p for p, _ in top_mar])),
                    }
                )

        print(f"[{sid}] done (N_max={n_max}, K_max={k_max})")

    _write_csv(out_dir / "seed_runs_long.csv", seed_run_rows)
    _write_csv(out_dir / "prcc_top5.csv", prcc_rows)
    _write_csv(out_dir / "stability_summary.csv", summary_rows)
    print(f"wrote -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
