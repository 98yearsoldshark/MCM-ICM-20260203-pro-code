#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：功耗参数多目标校准（AndroWatts + SmartphoneMeasurements 约束）。

背景（对齐赛题 26A 要求）：
- 赛题允许用公开数据做“参数估计与验证”，但不能用黑盒回归替代连续时间机理模型；
- Q2 里 TTE 对功耗量级极敏感：P_total 的系统性偏差会被“积分到 TTE”里放大；
- 仅对 total 做缩放校准会牺牲组件分解的可信度，从而削弱 drivers / Recommendations 的解释力。

本脚本做什么：
1) 在 AndroWatts aggregated.csv 上同时拟合：
   - total（总功耗）
   - screen/cpu/gpu/radio/background/base（主要组件）
2) 额外用 SmartphoneMeasurements（Monsoon+iPerf）给 Wi‑Fi 的单位数据能耗（J/MB）加一个“物理量级约束”，
   避免出现“能拟合 AndroWatts，但网络能耗量级不合理”的情况。

输出：
- out_reports/q2/calibration_multiobjective/
  - scales.json：拟合得到的尺度因子
  - fit_metrics_before.csv / fit_metrics_after.csv：同一批样本上的误差指标
- configs/<out-name>.json：写回到新的功耗参数 JSON（结构不变，只调整系数）

备注：
- 这是“可复现的校准流程”，不是最终唯一答案；后续可替换成更强的多目标优化（如 DE/PSO/贝叶斯）。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.observed.andro_watts import AndroWattsCase, build_cases, load_aggregated_csv
from mcm26a.observed.smartphone_measurements import load_smartphone_measurements_zip
from mcm26a.power import PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Segment


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _mean(arr: list[float]) -> float:
    return float(np.mean(np.array(arr, dtype=float))) if arr else float("nan")


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if not np.any(m):
        return float("nan")
    return float(np.mean(np.abs(a[m] - b[m])))


def _mape_pct(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b) & (np.abs(a) > 1e-12)
    if not np.any(m):
        return float("nan")
    return float(np.mean(np.abs((b[m] - a[m]) / a[m])) * 100.0)


def _pearsonr(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(np.sum(m)) < 3:
        return float("nan")
    aa = a[m] - float(np.mean(a[m]))
    bb = b[m] - float(np.mean(b[m]))
    denom = float(np.sqrt(np.sum(aa * aa) * np.sum(bb * bb)))
    if denom <= 1e-12:
        return float("nan")
    return float(np.sum(aa * bb) / denom)


def _simulate_mean_power(
    case: AndroWattsCase,
    *,
    power: PowerParams1Stateful,
    dt_s: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, float]:
    """对单个 case 多随机种子平均，得到“平均功率分解（W）”。

注意：这里仅在“功耗模型层”做积分平均，用于快速校准/对照，不把短时验证强行耦合到电池端。
"""

    dur = float(case.duration_s)
    if dur <= 0:
        return {k: float("nan") for k in ["base_w", "screen_w", "cpu_w", "gpu_w", "radio_w", "gps_w", "background_w", "interaction_w", "total_w"]}

    avg_by_seed: dict[str, list[float]] = {k: [] for k in ["base_w", "screen_w", "cpu_w", "gpu_w", "radio_w", "gps_w", "background_w", "interaction_w", "total_w"]}
    for k in range(int(n_seeds)):
        pm = StatefulPowerModel1(power, seed=int(seed0) + k)
        pm.reset()
        e = {k: 0.0 for k in avg_by_seed.keys()}
        t = 0.0
        while t < dur - 1e-12:
            dt = min(float(dt_s), dur - t)
            bd = pm.step(case.segment, dt_s=dt, battery_temp_C=None)
            e["base_w"] += float(bd.base_w) * dt
            e["screen_w"] += float(bd.screen_w) * dt
            e["cpu_w"] += float(bd.cpu_w) * dt
            e["gpu_w"] += float(bd.gpu_w) * dt
            e["radio_w"] += float(bd.radio_w) * dt
            e["gps_w"] += float(bd.gps_w) * dt
            e["background_w"] += float(bd.background_w) * dt
            e["interaction_w"] += float(bd.interaction_w) * dt
            e["total_w"] += float(bd.total_w) * dt
            t += dt

        for kk in avg_by_seed.keys():
            avg_by_seed[kk].append(float(e[kk]) / dur)

    return {k: _mean(vs) for k, vs in avg_by_seed.items()}


def _metrics(rows: list[dict[str, float]], *, prefix_obs: str = "obs", prefix_pred: str = "pred") -> list[dict[str, object]]:
    comps = ["total", "screen", "cpu", "gpu", "radio", "gps", "background", "base", "other"]
    out = []
    for c in comps:
        y_true = [float(r.get(f"{prefix_obs}_{c}_w", float("nan"))) for r in rows]
        y_pred = [float(r.get(f"{prefix_pred}_{c}_w", float("nan"))) for r in rows]
        out.append(
            {
                "component": c,
                "pearson_r": _pearsonr(y_true, y_pred),
                "mae_W": _mae(y_true, y_pred),
                "mape_pct": _mape_pct(y_true, y_pred),
                "obs_mean_W": float(np.nanmean(np.array(y_true, dtype=float))),
                "pred_mean_W": float(np.nanmean(np.array(y_pred, dtype=float))),
            }
        )
    return out


@dataclass(frozen=True)
class _Scales:
    base: float
    screen: float
    cpu: float
    gpu: float
    radio_state: float
    radio_data: float
    background: float

    def as_dict(self) -> dict[str, float]:
        return {
            "base": float(self.base),
            "screen": float(self.screen),
            "cpu": float(self.cpu),
            "gpu": float(self.gpu),
            "radio_state": float(self.radio_state),
            "radio_data": float(self.radio_data),
            "background": float(self.background),
        }


def _apply_scales(power: PowerParams1Stateful, s: _Scales) -> PowerParams1Stateful:
    """把尺度因子乘到功耗参数上（结构不变）。"""

    # screen：P0/k/k_apl 同尺度缩放
    scr = power.screen
    screen = replace(
        scr,
        P0_W=float(scr.P0_W) * float(s.screen),
        k_W_per_nit=float(scr.k_W_per_nit) * float(s.screen),
        k_apl_W=float(scr.k_apl_W) * float(s.screen),
    )

    # cpu：big/LITTLE 或单 k_W 均缩放
    cpu0 = power.cpu
    cpu = replace(
        cpu0,
        k_W=float(cpu0.k_W) * float(s.cpu),
        k_lit_W=(None if cpu0.k_lit_W is None else float(cpu0.k_lit_W) * float(s.cpu)),
        k_big_W=(None if cpu0.k_big_W is None else float(cpu0.k_big_W) * float(s.cpu)),
    )

    # gpu
    gpu0 = power.gpu
    gpu = replace(gpu0, k_W=float(gpu0.k_W) * float(s.gpu))

    # radio：拆成 state 与 data 两个尺度，便于同时满足“总功耗”与“J/MB 物理量级”
    rrc0 = power.rrc
    p_state = {
        mode: {st: float(pw) * float(s.radio_state) for st, pw in table.items()}
        for mode, table in rrc0.p_state_W.items()
    }
    e_per_mb = {k: float(v) * float(s.radio_data) for k, v in rrc0.e_per_mb_J.items()}
    rrc = replace(rrc0, p_state_W=p_state, e_per_mb_J=e_per_mb)

    # background：基线 + 唤醒 CPU 能耗同尺度缩放（把“后台强度”视为同一族不确定性）
    bg0 = power.background_poisson
    bg_poisson = replace(bg0, cpu_wake_W=float(bg0.cpu_wake_W) * float(s.background))
    bg_level = {k: float(v) * float(s.background) for k, v in power.background_level_W.items()}

    return replace(
        power,
        base_W=float(power.base_W) * float(s.base),
        screen=screen,
        cpu=cpu,
        gpu=gpu,
        rrc=rrc,
        background_level_W=bg_level,
        background_poisson=bg_poisson,
    )


def _wifi_energy_per_mb_targets(zip_path: Path, *, thr_min_MBps: float = 0.2) -> list[float]:
    """从 SmartphoneMeasurements.zip 提取 Wi‑Fi（Router）的单位数据能耗样本（J/MB）。

设计：
- 不直接用单个中位数作为约束（那会在 least_squares 里只有 1 个残差项，权重很难与 1000+ 的 AndroWatts 残差平衡）。
- 而是把每个可用的 router 测试都作为一个“软约束样本”，自然增加约束项数量与稳健性。
"""

    try:
        monsoon, iperf = load_smartphone_measurements_zip(zip_path)
    except Exception:
        return []

    ip_map = {(i.phone, i.test): i for i in iperf}
    baseline = {m.phone: float(m.mean_power_W) for m in monsoon if m.test == "smartphoneBaseline" and np.isfinite(m.mean_power_W)}

    xs: list[float] = []
    for m in monsoon:
        if "Router" not in str(m.test):
            continue
        base = float(baseline.get(m.phone, float("nan")))
        if not np.isfinite(base):
            continue
        ip = ip_map.get((m.phone, m.test))
        if ip is None or (not np.isfinite(ip.mean_mbps)) or ip.mean_mbps <= 0:
            continue
        thr_MBps = float(ip.mean_mbps) / 8.0
        if not np.isfinite(thr_MBps) or thr_MBps <= float(thr_min_MBps):
            continue
        dp = float(m.mean_power_W - base)
        if not np.isfinite(dp) or dp <= 0 or thr_MBps <= 1e-9:
            continue
        xs.append(float(dp / thr_MBps))

    return xs


def _smartphone_baseline_power_targets(zip_path: Path) -> list[float]:
    """从 SmartphoneMeasurements.zip 提取 baseline mean power（W）样本。

说明：
- SmartphoneMeasurements 的 baseline 是在严格控制条件下的短时平均功耗（约 3 分钟），
  不是“整机放电到关机”。
- 这里只作为“量级锚定”的软约束，避免出现 baseline 明显偏低从而导致 TTE 系统性偏长。
"""

    try:
        monsoon, _iperf = load_smartphone_measurements_zip(zip_path)
    except Exception:
        return []

    return [float(m.mean_power_W) for m in monsoon if str(m.test) == "smartphoneBaseline" and np.isfinite(m.mean_power_W) and float(m.mean_power_W) > 0]


def _simulate_baseline_mean_power(
    *,
    power: PowerParams1Stateful,
    dt_s: float,
    n_seeds: int,
    seed0: int,
    duration_s: float,
    brightness_nits: float,
    screen_apl: float,
    cpu_load: float,
) -> float:
    """用功耗模型模拟“SmartphoneMeasurements baseline 条件”的平均功耗（W）。

注意：这是纯功耗层积分平均，不调用电池模型；用于给校准器提供一个“baseline 量级约束”。
"""

    seg = Segment(
        duration_s=float(duration_s),
        ambient_temp_c=25.0,
        screen_on=True,
        brightness_nits=float(brightness_nits),
        activity="video",
        cpu_load=float(cpu_load),
        gpu_load=0.0,
        radio_mode="wifi",
        signal_quality="good",
        net_activity="idle",
        gps_on=False,
        background_level="low",
        net_throughput_MBps=float("nan"),
        screen_apl=float(screen_apl),
    )

    vals: list[float] = []
    for k in range(int(n_seeds)):
        pm = StatefulPowerModel1(power, seed=int(seed0) + k)
        pm.reset()
        e = 0.0
        t = 0.0
        while t < float(duration_s) - 1e-12:
            dt = min(float(dt_s), float(duration_s) - t)
            bd = pm.step(seg, dt_s=dt, battery_temp_C=None)
            e += float(bd.total_w) * dt
            t += dt
        vals.append(e / float(duration_s))

    return float(np.mean(np.array(vals, dtype=float))) if vals else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 多目标功耗校准（AndroWatts + 网络约束）")
    ap.add_argument("--base-power", default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal.json"), help="起点功耗参数 JSON")
    ap.add_argument("--out-name", default="power_params_v2_no7_awcal_mo.json", help="输出到 configs/ 的文件名")
    ap.add_argument("--max-n", type=int, default=220, help="抽样多少条 AndroWatts 样本用于拟合（0 表示全量）")
    ap.add_argument("--seed", type=int, default=0, help="AndroWatts 抽样随机种子")
    ap.add_argument("--dt", type=float, default=1.0, help="功耗积分步长（秒）")
    ap.add_argument("--seeds-per-case", type=int, default=8, help="每条样本平均多少随机种子（拟合用，越大越稳但越慢）")
    ap.add_argument("--max-nits", type=float, default=500.0, help="Brightness(0~100) 映射到的最大 nits")
    ap.add_argument(
        "--andro-csv",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
        help="AndroWatts aggregated.csv 路径",
    )
    ap.add_argument(
        "--sm-zip",
        default=str(SRC_DIR.parent / "data" / "SmartphoneMeasurements" / "SmartphoneMeasurements.zip"),
        help="SmartphoneMeasurements.zip（用于 Wi‑Fi J/MB 约束，可缺省）",
    )
    ap.add_argument("--wifi-weight", type=float, default=0.35, help="Wi‑Fi J/MB 软约束权重（默认 0.35；可调大以更贴合实测量级）")
    ap.add_argument("--baseline-weight", type=float, default=0.0, help="baseline mean power 软约束权重（默认 0=不启用）")
    ap.add_argument("--baseline-duration-s", type=float, default=180.0, help="baseline 约束使用的平均功耗时长（秒）")
    ap.add_argument("--baseline-brightness-nits", type=float, default=500.0, help="baseline 条件：亮度（nits）")
    ap.add_argument("--baseline-apl", type=float, default=1.0, help="baseline 条件：APL（白底≈1）")
    ap.add_argument("--baseline-cpu-load", type=float, default=0.05, help="baseline 条件：CPU 负载（0~1）")
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "calibration_multiobjective"), help="输出报告目录")
    args = ap.parse_args()

    rng = np.random.default_rng(int(args.seed))
    out_reports = Path(args.out_reports)
    out_reports.mkdir(parents=True, exist_ok=True)

    base_power_path = Path(args.base_power)
    power0 = PowerParams1Stateful.from_json(base_power_path)

    df = load_aggregated_csv(Path(args.andro_csv))
    max_n = None if int(args.max_n) <= 0 else int(args.max_n)
    cases = build_cases(df, max_n=max_n, seed=int(args.seed), max_screen_nits=float(args.max_nits))
    if not cases:
        raise RuntimeError("AndroWatts 案例为空，请检查 aggregated.csv 路径或解析逻辑")

    # 预先计算观测均值（作为残差归一化尺度，避免不同组件量级差异导致优化“只看 CPU”）
    obs_means = {
        "total": float(np.mean([c.obs.total_w for c in cases])),
        "screen": float(np.mean([c.obs.screen_w for c in cases])),
        "cpu": float(np.mean([c.obs.cpu_w for c in cases])),
        "gpu": float(np.mean([c.obs.gpu_w for c in cases])),
        "radio": float(np.mean([c.obs.radio_w for c in cases])),
        "background": float(np.mean([c.obs.background_w for c in cases])),
        "base": float(np.mean([c.obs.base_w for c in cases])),
    }

    # Wi‑Fi J/MB 约束目标（可选）
    sm_zip = Path(args.sm_zip)
    wifi_targets = _wifi_energy_per_mb_targets(sm_zip) if float(args.wifi_weight) > 0 else []
    baseline_targets = _smartphone_baseline_power_targets(sm_zip) if float(args.baseline_weight) > 0 else []

    # 固定一组“评估用样本”，用于输出 before/after 指标（避免“拟合目标漂移”）
    eval_idx = rng.choice(len(cases), size=min(200, len(cases)), replace=False).tolist()
    eval_cases = [cases[i] for i in eval_idx]

    def _eval_rows(p: PowerParams1Stateful) -> list[dict[str, float]]:
        rows: list[dict[str, float]] = []
        for i, c in enumerate(eval_cases):
            pred = _simulate_mean_power(c, power=p, dt_s=float(args.dt), n_seeds=int(args.seeds_per_case), seed0=10_000 + i * 31)
            obs = c.obs.as_dict()
            rows.append(
                {
                    "obs_total_w": float(obs["total_w"]),
                    "obs_screen_w": float(obs["screen_w"]),
                    "obs_cpu_w": float(obs["cpu_w"]),
                    "obs_gpu_w": float(obs["gpu_w"]),
                    "obs_radio_w": float(obs["radio_w"]),
                    "obs_gps_w": float(obs["gps_w"]),
                    "obs_background_w": float(obs["background_w"]),
                    "obs_base_w": float(obs["base_w"]),
                    "obs_other_w": float(obs["other_w"]),
                    "pred_total_w": float(pred["total_w"]),
                    "pred_screen_w": float(pred["screen_w"]),
                    "pred_cpu_w": float(pred["cpu_w"]),
                    "pred_gpu_w": float(pred["gpu_w"]),
                    "pred_radio_w": float(pred["radio_w"]),
                    "pred_gps_w": float(pred["gps_w"]),
                    "pred_background_w": float(pred["background_w"]),
                    "pred_base_w": float(pred["base_w"]),
                    "pred_other_w": float("nan"),
                }
            )
        return rows

    before_rows = _eval_rows(power0)
    _write_csv(out_reports / "fit_metrics_before.csv", _metrics(before_rows), fieldnames=["component", "pearson_r", "mae_W", "mape_pct", "obs_mean_W", "pred_mean_W"])

    # -------------------------
    # 多目标最小二乘（log-scale）
    # -------------------------
    # y = log(scale)，避免负数，并让“尺度不确定性”更接近对数均匀的先验直觉。
    def _unpack(y: np.ndarray) -> _Scales:
        s = np.exp(np.array(y, dtype=float))
        return _Scales(
            base=float(s[0]),
            screen=float(s[1]),
            cpu=float(s[2]),
            gpu=float(s[3]),
            radio_state=float(s[4]),
            radio_data=float(s[5]),
            background=float(s[6]),
        )

    # 残差权重：total 重要性最高（避免“组件更像了，但总功耗跑偏”）；其余组件用于提升 drivers 可信度。
    # 经验上 base/radio 属于“聚合不确定性更大”的组件（rail 映射不是一一对应），因此权重略低。
    w = {"total": 5.0, "screen": 1.0, "cpu": 1.0, "gpu": 1.0, "radio": 0.8, "background": 1.0, "base": 0.35}
    # 残差归一化尺度（避免除 0）
    sc = {k: max(1e-3, float(v)) for k, v in obs_means.items()}

    # 选一批“拟合用”样本（可与 eval 不同，避免过拟合某个固定子集）
    fit_idx = rng.choice(len(cases), size=min(220, len(cases)), replace=False).tolist()
    fit_cases = [cases[i] for i in fit_idx]

    def residuals(y: np.ndarray) -> np.ndarray:
        s = _unpack(y)
        p = _apply_scales(power0, s)
        res: list[float] = []

        for i, c in enumerate(fit_cases):
            pred = _simulate_mean_power(c, power=p, dt_s=float(args.dt), n_seeds=int(args.seeds_per_case), seed0=2_000_000 + i * 17)
            # 组件残差（按全局均值归一化）
            res.append(float(w["total"]) * (float(pred["total_w"]) - float(c.obs.total_w)) / sc["total"])
            res.append(float(w["screen"]) * (float(pred["screen_w"]) - float(c.obs.screen_w)) / sc["screen"])
            res.append(float(w["cpu"]) * (float(pred["cpu_w"]) - float(c.obs.cpu_w)) / sc["cpu"])
            res.append(float(w["gpu"]) * (float(pred["gpu_w"]) - float(c.obs.gpu_w)) / sc["gpu"])
            res.append(float(w["radio"]) * (float(pred["radio_w"]) - float(c.obs.radio_w)) / sc["radio"])
            res.append(float(w["background"]) * (float(pred["background_w"]) - float(c.obs.background_w)) / sc["background"])
            res.append(float(w["base"]) * (float(pred["base_w"]) - float(c.obs.base_w)) / sc["base"])

        # Wi‑Fi J/MB 约束（软约束）：只约束 wifi，不强迫 LTE/5G（因为数据不同源）
        if wifi_targets:
            e_wifi = float(_apply_scales(power0, s).rrc.e_per_mb_J.get("wifi", float("nan")))
            if np.isfinite(e_wifi):
                # SmartphoneMeasurements 与 AndroWatts 并非同机型/同条件，因此仅作为“量级锚定”的软约束。
                w_wifi = float(args.wifi_weight)
                if np.isfinite(w_wifi) and w_wifi > 0:
                    for tgt in wifi_targets:
                        if not (np.isfinite(float(tgt)) and float(tgt) > 1e-9):
                            continue
                        res.append(w_wifi * (e_wifi - float(tgt)) / float(tgt))

        # baseline mean power 约束（可选）：避免 baseline 量级显著偏低 → TTE 系统性偏长
        if baseline_targets:
            w_base = float(args.baseline_weight)
            if np.isfinite(w_base) and w_base > 0:
                p_base = _simulate_baseline_mean_power(
                    power=p,
                    dt_s=float(args.dt),
                    n_seeds=max(1, int(args.seeds_per_case)),
                    seed0=9_000_000,
                    duration_s=float(args.baseline_duration_s),
                    brightness_nits=float(args.baseline_brightness_nits),
                    screen_apl=float(args.baseline_apl),
                    cpu_load=float(args.baseline_cpu_load),
                )
                if np.isfinite(p_base):
                    for tgt in baseline_targets:
                        if not (np.isfinite(float(tgt)) and float(tgt) > 1e-9):
                            continue
                        res.append(w_base * (p_base - float(tgt)) / float(tgt))

        # 轻微正则：避免尺度跑飞（保持“结构合理 + 可解释”）
        for name, val in s.as_dict().items():
            res.append(0.05 * math.log(max(1e-9, float(val))))  # 中心在 1

        return np.array(res, dtype=float)

    # 初值：全 1（即不改）
    y0 = np.zeros(7, dtype=float)
    # log-scale bounds：允许 base 放大更多（解决 base 低估），其余较保守
    lo = np.array([math.log(0.4), math.log(0.6), math.log(0.6), math.log(0.6), math.log(0.5), math.log(0.5), math.log(0.5)], dtype=float)
    hi = np.array([math.log(3.5), math.log(1.8), math.log(1.8), math.log(1.8), math.log(2.5), math.log(2.5), math.log(2.5)], dtype=float)

    sol = least_squares(residuals, y0, bounds=(lo, hi), max_nfev=40, verbose=1)
    best = _unpack(sol.x)

    # 写出 scales.json
    (out_reports / "scales.json").write_text(json.dumps(best.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    power_best = _apply_scales(power0, best)
    after_rows = _eval_rows(power_best)
    _write_csv(out_reports / "fit_metrics_after.csv", _metrics(after_rows), fieldnames=["component", "pearson_r", "mae_W", "mape_pct", "obs_mean_W", "pred_mean_W"])

    # -------------------------
    # 写回新的 configs JSON（保留 meta，追加校准说明）
    # -------------------------
    obj = json.loads(Path(args.base_power).read_text(encoding="utf-8"))
    meta = dict(obj.get("meta", {}) or {})
    notes = str(meta.get("notes_zh", "")).strip()
    meta["notes_zh"] = (
        (notes + "\n\n" if notes else "")
        + "多目标校准（自动生成）：同时拟合 AndroWatts 的 total+主要组件，并用 SmartphoneMeasurements 对 Wi‑Fi 的 J/MB 做软约束。\n"
        + f"scales={best.as_dict()}\n"
    )
    obj["meta"] = meta

    # base
    obj["base_W"] = float(obj.get("base_W", 0.0)) * float(best.base)

    # screen
    if "screen" in obj:
        for k in ["P0_W", "k_W_per_nit", "k_apl_W"]:
            if k in obj["screen"]:
                obj["screen"][k] = float(obj["screen"][k]) * float(best.screen)

    # cpu
    if "cpu" in obj:
        for k in ["k_W", "k_lit_W", "k_big_W"]:
            if k in obj["cpu"] and obj["cpu"][k] is not None:
                obj["cpu"][k] = float(obj["cpu"][k]) * float(best.cpu)

    # gpu
    if "gpu" in obj and "k_W" in obj["gpu"]:
        obj["gpu"]["k_W"] = float(obj["gpu"]["k_W"]) * float(best.gpu)

    # background
    if "background_level_W" in obj:
        obj["background_level_W"] = {k: float(v) * float(best.background) for k, v in (obj["background_level_W"] or {}).items()}
    if "background_poisson" in obj and "cpu_wake_W" in obj["background_poisson"]:
        obj["background_poisson"]["cpu_wake_W"] = float(obj["background_poisson"]["cpu_wake_W"]) * float(best.background)

    # rrc
    if "rrc" in obj:
        rrc = obj["rrc"]
        if "p_state_W" in rrc:
            rrc["p_state_W"] = {
                mode: {st: float(pw) * float(best.radio_state) for st, pw in table.items()} for mode, table in (rrc.get("p_state_W") or {}).items()
            }
        if "e_per_mb_J" in rrc:
            rrc["e_per_mb_J"] = {k: float(v) * float(best.radio_data) for k, v in (rrc.get("e_per_mb_J") or {}).items()}
        obj["rrc"] = rrc

    out_cfg = SRC_DIR / "configs" / str(args.out_name)
    out_cfg.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Q2 多目标功耗校准完成：")
    print(f"- scales: {out_reports / 'scales.json'}")
    print(f"- metrics(before/after): {out_reports / 'fit_metrics_before.csv'} , {out_reports / 'fit_metrics_after.csv'}")
    print(f"- new config: {out_cfg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
