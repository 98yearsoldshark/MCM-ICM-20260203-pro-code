#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3 实验：在“均值功耗固定”的前提下，做可控的“波动强度 sweep（α）”，检验 ΔTTE 随波动增强如何变化。

该实验是对 `run_q3_smartphone_measurements_experiment.py` 的补强（更偏“机理+因果对照”）：
- 先从 Monsoon 实测功耗轨迹 P(t) 得到均值 P̄；
- 构造一族等均值轨迹：P_α(t) = P̄ + α·(P(t)-P̄)，其中 α∈[0,1]；
  - α=0 对应“均值常功耗”（完全无波动）；
  - α=1 对应“真实波动强度”；
- 对每条轨迹、每个电池老化档位（new/eol），分别仿真得到 TTE_α，并计算
  ΔTTE(%) = (TTE_α - TTE_α=0) / TTE_α=0 × 100%。

对齐赛题 Q3（Sensitivity and Assumptions）：
- fluctuations in usage patterns：在同一平均功耗下，仅改变时间结构/波动强度，续航预测如何变化？
- 建模假设：把波动简化为均值功耗（α=0）在机理模型里会造成多大系统性偏差？

工程约定：
- 时间单位统一秒（s）；图中可转换为小时/百分比。
- 默认只做 α∈[0,1]，避免出现负功耗并保持均值严格不变（数学上方差随 α^2 缩放）。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.mcm2026_battery_state import apply_battery_state_to_model3, load_battery_state_table
from mcm26a.power.model0 import PowerBreakdown, PowerParams0
from mcm26a.scenarios import Scenario, Segment
from mcm26a.sim import simulate_model3_aging


@dataclass
class _Trace:
    """读取 traces/*.csv 后的统一格式。"""

    name: str
    duration_s: float
    dt_s: float
    p_w: np.ndarray

    @property
    def mean_w(self) -> float:
        return float(np.mean(self.p_w))

    @property
    def std_w(self) -> float:
        return float(np.std(self.p_w))

    @property
    def cv(self) -> float:
        mu = float(self.mean_w)
        return float(self.std_w / mu) if mu > 1e-12 else float("nan")


def _sanitize(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\\-]+", "_", str(s)).strip("_")


def _read_trace_csv(path: Path) -> _Trace:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        rows = [dict(row) for row in r]

    if not rows:
        raise ValueError(f"空轨迹文件：{path}")

    ts = np.array([float(r.get("t_s", "nan")) for r in rows], dtype=float)
    ps = np.array([float(r.get("p_w", "nan")) for r in rows], dtype=float)
    m = np.isfinite(ts) & np.isfinite(ps)
    ts = ts[m]
    ps = ps[m]
    if ts.size < 5:
        raise ValueError(f"轨迹过短：{path} (n={ts.size})")

    # 从时间戳估计 dt（允许少量误差）
    dts = np.diff(ts)
    dt = float(np.median(dts[np.isfinite(dts)]))
    if not np.isfinite(dt) or dt <= 0:
        dt = 1.0

    # 轨迹长度：t 最后一个点一般是 duration-dt；因此 +dt 近似得到一个周期。
    duration = float(ts[-1] + dt)
    # 防御：避免 0 或极小 duration 导致后续 repeat 模式死循环。
    duration = max(duration, float(dt))

    name = path.stem
    return _Trace(name=str(name), duration_s=float(duration), dt_s=float(dt), p_w=ps.astype(float))


class _PowerTraceModel:
    """循环功耗轨迹驱动：每步输出 other_w=P(t)。"""

    def __init__(self, p_w: np.ndarray):
        self._p = np.asarray(p_w, dtype=float)
        self._idx = 0

    def reset(self) -> None:
        self._idx = 0

    def step(self, seg: Segment, *, dt_s: float, battery_temp_C: float | None = None) -> PowerBreakdown:  # noqa: ARG002
        if self._idx >= self._p.size:
            self._idx = 0
        p = float(self._p[self._idx])
        self._idx += 1
        return PowerBreakdown(
            base_w=0.0,
            screen_w=0.0,
            cpu_w=0.0,
            gpu_w=0.0,
            radio_w=0.0,
            gps_w=0.0,
            background_w=0.0,
            interaction_w=0.0,
            other_w=float(p),
        )


class _ConstantPowerModel:
    """恒定功率模型：每步输出 other_w=const。"""

    def __init__(self, p_w: float):
        self._p = float(p_w)

    def reset(self) -> None:
        return None

    def step(self, seg: Segment, *, dt_s: float, battery_temp_C: float | None = None) -> PowerBreakdown:  # noqa: ARG002
        return PowerBreakdown(
            base_w=0.0,
            screen_w=0.0,
            cpu_w=0.0,
            gpu_w=0.0,
            radio_w=0.0,
            gps_w=0.0,
            background_w=0.0,
            interaction_w=0.0,
            other_w=float(self._p),
        )


def _scenario_for_trace(name: str, *, duration_s: float, ambient_temp_c: float = 25.0) -> Scenario:
    """把轨迹长度作为一个 segment，循环重复直到耗尽。"""

    seg = Segment(
        duration_s=float(duration_s),
        ambient_temp_c=float(ambient_temp_c),
        screen_on=True,
        brightness_nits=200.0,
        activity="measured_trace",
        cpu_load=0.5,
        gpu_load=0.2,
        radio_mode="wifi",
        signal_quality="good",
        net_activity="browse",
        gps_on=False,
        background_level="medium",
        screen_apl=float("nan"),
    )
    return Scenario(
        scenario_id=f"SM_SWEEP_{_sanitize(name)}",
        title_zh=f"SmartphoneMeasurements：{name}",
        description_zh="用 Monsoon 实测功耗轨迹做可控波动强度 sweep（α），检验 ΔTTE 随波动变化。",
        repeat=True,
        cycle_s=float(duration_s),
        schedule=(seg,),
    )


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


def _parse_float_list(s: str) -> list[float]:
    xs: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    if not xs:
        raise ValueError("列表不能为空")
    return xs


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 SmartphoneMeasurements 波动强度 sweep（α）")
    ap.add_argument(
        "--reports-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_smartphone_measurements"),
        help="输入/输出目录（默认 out_reports/q3/observed_smartphone_measurements）",
    )
    ap.add_argument("--trace-dir", default="", help="轨迹目录（默认 reports-dir/traces）")
    ap.add_argument(
        "--alphas",
        default="0,0.2,0.4,0.6,0.8,1.0",
        help="波动强度系数 α 列表（逗号分隔，建议 0~1；默认 0,0.2,...,1.0）",
    )
    ap.add_argument("--max-traces", type=int, default=0, help="最多使用多少条 trace（0 表示全部）")

    ap.add_argument(
        "--battery-state-table",
        default=str(SRC_DIR.parent / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"),
        help="电池老化状态表路径",
    )
    ap.add_argument("--battery-dataset", type=int, default=3, help="使用的 battery_dataset（默认 3）")
    ap.add_argument("--battery-cell", default="Cell01", help="使用的 battery_cell（默认 Cell01）")
    ap.add_argument("--state-labels", default="new,eol", help="用于对照的老化档位（逗号分隔）")
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC")
    ap.add_argument("--r-growth-k", type=float, default=1.0, help="SOH→内阻增长映射强度系数")
    ap.add_argument(
        "--capacity-mode",
        default="cap_loss_from_soh",
        choices=["cap_loss_from_soh", "scale_capacity_ref"],
        help="SOH→容量衰减映射方式",
    )
    ap.add_argument("--dt", type=float, default=1.0, help="积分步长（秒），应与 traces/*.csv 的步长一致或为其倍数")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    trace_dir = Path(args.trace_dir) if str(args.trace_dir).strip() else (reports_dir / "traces")
    if not trace_dir.exists():
        raise FileNotFoundError(f"找不到 trace_dir：{trace_dir}（请先运行 run_q3_smartphone_measurements_experiment.py）")

    alphas = _parse_float_list(args.alphas)
    for a in alphas:
        if a < 0.0 or a > 1.0 + 1e-12:
            raise ValueError("为保证均值严格不变且不出现负功耗，本实验建议 alpha 在 [0,1] 内")

    # 读取轨迹（按文件名稳定排序，避免引入随机选择）
    trace_paths = sorted(p for p in trace_dir.glob("*.csv") if p.is_file())
    if not trace_paths:
        raise FileNotFoundError(f"trace_dir 下没有任何 csv：{trace_dir}")
    if int(args.max_traces) > 0:
        trace_paths = trace_paths[: int(args.max_traces)]

    traces = [_read_trace_csv(p) for p in trace_paths]

    # 电池参数与状态
    batt_base = BatteryParams3Aging.from_json(args.phone)
    states_all = load_battery_state_table(args.battery_state_table)
    labels = [s.strip() for s in str(args.state_labels).split(",") if s.strip()]

    # 选出每个 label 对应的一个代表 state（同脚本 run_q3_smartphone_measurements_experiment.py 的策略：SOH 接近该 label 的均值）
    states_all = [s for s in states_all if int(s.battery_dataset) == int(args.battery_dataset) and str(s.battery_cell) == str(args.battery_cell)]
    pick_states = []
    for lab in labels:
        group = [s for s in states_all if str(s.battery_state_label) == str(lab)]
        if not group:
            continue
        target = float(np.mean([float(s.SOH) for s in group]))
        pick = min(group, key=lambda s: abs(float(s.SOH) - target))
        pick_states.append(pick)
    if not pick_states:
        raise ValueError("未选出任何电池状态（请检查 --battery-dataset/--battery-cell/--state-labels）")

    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    dt_s = float(args.dt)
    rows: list[dict[str, object]] = []

    for tr in traces:
        if not np.isfinite(tr.mean_w) or tr.mean_w <= 1e-12:
            continue
        if abs(float(tr.dt_s) - dt_s) > 1e-6:
            # 支持 dt 为倍数：用简单分组均值下采样（避免引入插值噪声）
            ratio = float(dt_s / float(tr.dt_s))
            if abs(ratio - round(ratio)) > 1e-6 or ratio < 1.0:
                raise ValueError(f"dt={dt_s} 不是轨迹 dt={tr.dt_s} 的整数倍，无法稳健下采样：{tr.name}")
            k = int(round(ratio))
            n = int(tr.p_w.size // k)
            p = tr.p_w[: n * k].reshape(n, k).mean(axis=1)
            p = p.astype(float)
            dt_tag = dt_s
            duration_s = float(n * dt_s)
            p_raw = p
        else:
            dt_tag = float(tr.dt_s)
            duration_s = float(tr.duration_s)
            p_raw = tr.p_w.astype(float)

        mu = float(np.mean(p_raw))
        cv0 = float(np.std(p_raw) / mu) if mu > 1e-12 else float("nan")

        sc = _scenario_for_trace(tr.name, duration_s=float(duration_s))

        # baseline：alpha=0 对应均值常功耗（只需算一次）
        pm_mean = _ConstantPowerModel(mu)

        for st in pick_states:
            batt, cap_loss0, r0g0, r1g0 = apply_battery_state_to_model3(
                batt_base,
                st,
                capacity_mode=str(args.capacity_mode),  # type: ignore[arg-type]
                r_growth_k=float(args.r_growth_k),
            )

            res0 = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm_mean,
                battery_params=batt,
                soc0=float(args.soc0),
                cap_loss0_frac=float(cap_loss0),
                r0_growth0_frac=float(r0g0),
                r1_growth0_frac=float(r1g0),
                dt_s=float(dt_s),
            )
            t0_h = float(res0.tte_h) if res0.tte_h is not None else float("nan")

            for a in alphas:
                a = float(a)
                if a <= 0.0 + 1e-12:
                    # 与 baseline 一致
                    t_h = float(t0_h)
                    status = str(res0.status)
                    margin = float(res0.min_headroom_margin)
                    cv = 0.0
                else:
                    p_a = mu + a * (p_raw - mu)
                    # 理论上 alpha∈[0,1] 且 p_raw>=0 时不会出现负值；仍做数值防御。
                    p_a = np.clip(p_a, 0.0, float(np.max(p_raw)))
                    cv = float(np.std(p_a) / mu) if mu > 1e-12 else float("nan")
                    pm = _PowerTraceModel(p_a)
                    res = simulate_model3_aging(
                        sc,
                        power_params=power0_dummy,
                        power_model=pm,
                        battery_params=batt,
                        soc0=float(args.soc0),
                        cap_loss0_frac=float(cap_loss0),
                        r0_growth0_frac=float(r0g0),
                        r1_growth0_frac=float(r1g0),
                        dt_s=float(dt_s),
                    )
                    t_h = float(res.tte_h) if res.tte_h is not None else float("nan")
                    status = str(res.status)
                    margin = float(res.min_headroom_margin)

                d_h = float(t_h - t0_h) if (np.isfinite(t_h) and np.isfinite(t0_h)) else float("nan")
                d_pct = float(100.0 * d_h / t0_h) if (np.isfinite(d_h) and np.isfinite(t0_h) and abs(t0_h) > 1e-12) else float("nan")

                rows.append(
                    {
                        "trace": str(tr.name),
                        "duration_s": float(duration_s),
                        "dt_s": float(dt_s),
                        "alpha": float(a),
                        "mean_W": float(mu),
                        "cv0": float(cv0),
                        "cv_alpha": float(cv),
                        "battery_state_id": str(st.battery_state_id),
                        "battery_state_label": str(st.battery_state_label),
                        "SOH": float(st.SOH),
                        "cap_loss0_frac": float(cap_loss0),
                        "r0_growth0_frac": float(r0g0),
                        "tte_alpha_h": float(t_h),
                        "status_alpha": str(status),
                        "min_margin_alpha": float(margin),
                        "tte_alpha0_h": float(t0_h),
                        "status_alpha0": str(res0.status),
                        "min_margin_alpha0": float(res0.min_headroom_margin),
                        "delta_tte_h": float(d_h),
                        "delta_tte_pct": float(d_pct),
                    }
                )

    out_path = reports_dir / "fluctuation_sweep.csv"
    _write_csv(out_path, rows)
    print(f"written -> {out_path} (rows={len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
