#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3 数据集实验：SmartphoneMeasurements（Monsoon 电源采样）用来检验“负载波动 vs 平均功耗”的建模假设。

对齐赛题 Q3（Sensitivity and Assumptions）：
- fluctuations in usage patterns：同一平均功耗下，负载的时间结构（突发/尾态/空闲）不同，是否会改变 TTE 预测？
- modeling assumptions：把真实功耗轨迹简化为“均值常功率”会带来多大误差？误差方向是否受老化影响？

实验设计（核心）：
1) 从 SmartphoneMeasurements.zip 读取 Monsoon 的功耗时间序列 P(t)；
2) 构造两个“等均值”场景：
   - Trace：循环重复真实 P(t)
   - Mean ：循环重复常值 mean(P)
3) 在同一电池参数下分别仿真得到 TTE，计算 ΔTTE = TTE_trace - TTE_mean

说明：
- 本实验用外部实测功耗轨迹驱动电池 ODE，用于验证“波动结构”的影响；不用于校准功耗模型本身。
- 为减少跨数据集口径差异，默认从电池老化状态表选取同一电芯体系（dataset+cell）的 new~eol 档位。
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
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
class _PowerTrace:
    phone: str
    test: str
    duration_s: float
    t_s: np.ndarray
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

    @property
    def p95_w(self) -> float:
        return float(np.percentile(self.p_w, 95))

    @property
    def p05_w(self) -> float:
        return float(np.percentile(self.p_w, 5))


def _sanitize(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\\-]+", "_", str(s)).strip("_")


def _iter_monsoon_csv_infos(z: zipfile.ZipFile):
    """遍历 zip 中的 Monsoon csv 文件，返回 (phone, test, inner_path, size_bytes)。"""

    for info in z.infolist():
        name = str(info.filename)
        if name.endswith("/") or info.file_size <= 0:
            continue
        if "/Monsoon/" not in name or not name.lower().endswith(".csv"):
            continue
        # SmartphoneMeasurements-main/Monsoon/<Phone>/<file>.csv
        parts = name.split("/")
        if len(parts) < 4:
            continue
        phone = str(parts[-2]).strip()
        test = str(parts[-1])[: -len(".csv")]
        yield phone, test, name, int(info.file_size)


def _load_monsoon_power_trace(z: zipfile.ZipFile, inner_path: str, *, phone: str, test: str, dt_s: float) -> _PowerTrace:
    """读取 Monsoon csv 并重采样到统一步长 dt_s（用线性插值）。"""

    with z.open(str(inner_path), "r") as bf:
        tf = io.TextIOWrapper(bf, encoding="utf-8", newline="")
        r = csv.reader(tf)
        try:
            header = next(r)
        except StopIteration:
            raise ValueError(f"empty csv: {inner_path}")

        try:
            t_idx = header.index("Time (s)")
        except ValueError:
            t_idx = 0
        try:
            p_idx = header.index("Main Avg Power (W)")
        except ValueError:
            p_idx = 2

        ts: list[float] = []
        ps: list[float] = []
        for row in r:
            if not row:
                continue
            if len(row) <= max(t_idx, p_idx):
                continue
            try:
                t = float(row[t_idx])
                p = float(row[p_idx])
            except Exception:
                continue
            if not np.isfinite(t) or not np.isfinite(p):
                continue
            ts.append(float(t))
            ps.append(float(p))

    if len(ts) < 5:
        raise ValueError(f"trace too short: {phone}/{test} (n={len(ts)})")

    t_raw = np.asarray(ts, dtype=float)
    p_raw = np.asarray(ps, dtype=float)
    # 单调性容错：若有重复时间戳，保持最后一个
    order = np.argsort(t_raw)
    t_raw = t_raw[order]
    p_raw = p_raw[order]

    dur = float(t_raw[-1])
    if dur <= 0:
        raise ValueError("invalid duration")

    # 统一重采样网格：包含 t=0，不包含终点（便于循环）
    n = int(max(2, np.floor(dur / float(dt_s))))
    t = np.arange(n, dtype=float) * float(dt_s)
    p = np.interp(t, t_raw, p_raw)
    p = np.clip(p, 0.0, float(np.nanmax(p_raw) if np.isfinite(np.nanmax(p_raw)) else 1.0))

    return _PowerTrace(phone=str(phone), test=str(test), duration_s=float(t[-1] + dt_s), t_s=t, p_w=p)


class _PowerTraceModel:
    """用循环功耗轨迹驱动仿真：每步输出 other_w=P(t)。"""

    def __init__(self, trace: _PowerTrace):
        self._trace = trace
        self._idx = 0

    def reset(self) -> None:
        self._idx = 0

    def step(self, seg: Segment, *, dt_s: float, battery_temp_C: float | None = None) -> PowerBreakdown:  # noqa: ARG002
        if self._idx >= self._trace.p_w.size:
            self._idx = 0
        p = float(self._trace.p_w[self._idx])
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


def _scenario_for_trace(trace: _PowerTrace, *, ambient_temp_c: float = 25.0) -> Scenario:
    """把轨迹长度作为一个 segment，循环重复直到耗尽。"""

    seg = Segment(
        duration_s=float(trace.duration_s),
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
        scenario_id=f"SM_{_sanitize(trace.phone)}_{_sanitize(trace.test)}",
        title_zh=f"SmartphoneMeasurements：{trace.phone}/{trace.test}",
        description_zh="用 Monsoon 实测功耗轨迹循环驱动电池模型，检验“波动 vs 均值”假设。",
        repeat=True,
        cycle_s=float(trace.duration_s),
        schedule=(seg,),
    )


def _pick_states(states_all, *, dataset: int, cell: str, labels: list[str]) -> list:
    states_all = [s for s in states_all if int(s.battery_dataset) == int(dataset) and str(s.battery_cell) == str(cell)]
    out = []
    for lab in labels:
        group = [s for s in states_all if str(s.battery_state_label) == str(lab)]
        if not group:
            continue
        target = float(np.mean([float(s.SOH) for s in group]))
        pick = min(group, key=lambda s: abs(float(s.SOH) - target))
        out.append(pick)
    if not out:
        raise ValueError("未选出任何电池状态（请检查 --battery-dataset/--battery-cell/--state-labels）")
    return out


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


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 SmartphoneMeasurements 波动假设检验")
    ap.add_argument(
        "--zip",
        default=str(SRC_DIR.parent / "data" / "SmartphoneMeasurements" / "SmartphoneMeasurements.zip"),
        help="SmartphoneMeasurements.zip 路径",
    )
    ap.add_argument(
        "--out-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_smartphone_measurements"),
        help="输出目录",
    )
    ap.add_argument("--dt", type=float, default=1.0, help="重采样与积分步长（秒），默认 1s")
    ap.add_argument(
        "--cases",
        default="all",
        help="选择的 Monsoon trace：\n"
        "- 显式列表：phone:test,phone:test\n"
        "- all：自动选择 zip 中全部 Monsoon 测试（可用 --include-phones/--include-tests/--exclude-large-csv-bytes 过滤）",
    )
    ap.add_argument("--include-phones", default="", help="仅使用指定手机（逗号分隔；留空表示全部）")
    ap.add_argument("--include-tests", default="", help="仅使用指定测试名（逗号分隔；留空表示全部）")
    ap.add_argument(
        "--exclude-large-csv-bytes",
        type=int,
        default=1_000_000,
        help="排除过大的 Monsoon csv（默认 >1,000,000 bytes；用于避开个别超大文件）",
    )
    ap.add_argument("--max-cases", type=int, default=0, help="最多使用多少条 trace（0 表示不限制）")
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
    ap.add_argument("--seed", type=int, default=0, help="占位参数：该实验本身是确定性的（不依赖随机种子）")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = out_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    # 1) 读取 trace（支持 all 自动选择）
    zpath = Path(args.zip)
    if not zpath.exists():
        raise FileNotFoundError(str(zpath))

    include_phones = {s.strip() for s in str(args.include_phones).split(",") if s.strip()}
    include_tests = {s.strip() for s in str(args.include_tests).split(",") if s.strip()}

    with zipfile.ZipFile(str(zpath), "r") as z:
        # phone,test -> inner_path
        index: dict[tuple[str, str], tuple[str, int]] = {}
        for phone, test, inner, size in _iter_monsoon_csv_infos(z):
            index[(phone, test)] = (inner, int(size))

        cases: list[tuple[str, str]] = []
        if str(args.cases).strip().lower() == "all":
            for (phone, test), (_inner, size) in sorted(index.items()):
                if include_phones and phone not in include_phones:
                    continue
                if include_tests and test not in include_tests:
                    continue
                if int(args.exclude_large_csv_bytes) > 0 and int(size) > int(args.exclude_large_csv_bytes):
                    continue
                cases.append((phone, test))
        else:
            for part in str(args.cases).split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" not in part:
                    raise ValueError("cases 格式应为 phone:test 或 all")
                phone, test = part.split(":", 1)
                phone = phone.strip()
                test = test.strip()
                if (phone, test) not in index:
                    raise FileNotFoundError(f"zip 中找不到 Monsoon/{phone}/{test}.csv")
                cases.append((phone, test))

        if not cases:
            raise ValueError("cases 为空：请检查 --cases/--include-phones/--include-tests/--exclude-large-csv-bytes")

        if int(args.max_cases) > 0 and len(cases) > int(args.max_cases):
            # 复现友好：按字典序截断（不引入随机）
            cases = cases[: int(args.max_cases)]

        traces: list[_PowerTrace] = []
        for phone, test in cases:
            inner, _size = index[(phone, test)]
            tr = _load_monsoon_power_trace(z, inner, phone=phone, test=test, dt_s=float(args.dt))
            traces.append(tr)

            # 写出重采样后的轨迹，便于后续画图/复现（避免依赖 zip 内部结构）
            trace_path = trace_dir / f"{_sanitize(phone)}__{_sanitize(test)}_dt{int(float(args.dt))}s.csv"
            with trace_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t_s", "p_w"])
                for t, p in zip(tr.t_s.tolist(), tr.p_w.tolist()):
                    w.writerow([float(t), float(p)])

    # 2) 读取电池状态（new/eol）
    batt_base = BatteryParams3Aging.from_json(args.phone)
    states_all = load_battery_state_table(args.battery_state_table)
    labels = [s.strip() for s in str(args.state_labels).split(",") if s.strip()]
    states = _pick_states(states_all, dataset=int(args.battery_dataset), cell=str(args.battery_cell), labels=labels)

    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    # 3) 仿真：Trace vs Mean（同一 battery_state）
    rows: list[dict[str, object]] = []
    for tr in traces:
        sc = _scenario_for_trace(tr)
        pm_trace = _PowerTraceModel(tr)
        pm_mean = _ConstantPowerModel(tr.mean_w)

        for st in states:
            batt, cap_loss0, r0g0, r1g0 = apply_battery_state_to_model3(
                batt_base,
                st,
                capacity_mode=str(args.capacity_mode),  # type: ignore[arg-type]
                r_growth_k=float(args.r_growth_k),
            )

            res_trace = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm_trace,
                battery_params=batt,
                soc0=float(args.soc0),
                cap_loss0_frac=float(cap_loss0),
                r0_growth0_frac=float(r0g0),
                r1_growth0_frac=float(r1g0),
                dt_s=float(args.dt),
            )

            res_mean = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm_mean,
                battery_params=batt,
                soc0=float(args.soc0),
                cap_loss0_frac=float(cap_loss0),
                r0_growth0_frac=float(r0g0),
                r1_growth0_frac=float(r1g0),
                dt_s=float(args.dt),
            )

            t_trace = float(res_trace.tte_h) if res_trace.tte_h is not None else float("nan")
            t_mean = float(res_mean.tte_h) if res_mean.tte_h is not None else float("nan")
            delta = float(t_trace - t_mean) if (np.isfinite(t_trace) and np.isfinite(t_mean)) else float("nan")
            rel = float(delta / t_mean) if (np.isfinite(delta) and np.isfinite(t_mean) and abs(t_mean) > 1e-12) else float("nan")

            rows.append(
                {
                    "phone": str(tr.phone),
                    "test": str(tr.test),
                    "duration_s": float(tr.duration_s),
                    "dt_s": float(args.dt),
                    "trace_mean_W": float(tr.mean_w),
                    "trace_std_W": float(tr.std_w),
                    "trace_cv": float(tr.cv),
                    "trace_p95_W": float(tr.p95_w),
                    "trace_p05_W": float(tr.p05_w),
                    "battery_state_id": str(st.battery_state_id),
                    "battery_state_label": str(st.battery_state_label),
                    "SOH": float(st.SOH),
                    "cap_loss0_frac": float(cap_loss0),
                    "r0_growth0_frac": float(r0g0),
                    "tte_trace_h": float(t_trace),
                    "status_trace": str(res_trace.status),
                    "min_margin_trace": float(res_trace.min_headroom_margin),
                    "tte_mean_h": float(t_mean),
                    "status_mean": str(res_mean.status),
                    "min_margin_mean": float(res_mean.min_headroom_margin),
                    "delta_tte_h": float(delta),
                    "delta_tte_frac": float(rel),
                }
            )

    _write_csv(out_dir / "trace_vs_mean.csv", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
