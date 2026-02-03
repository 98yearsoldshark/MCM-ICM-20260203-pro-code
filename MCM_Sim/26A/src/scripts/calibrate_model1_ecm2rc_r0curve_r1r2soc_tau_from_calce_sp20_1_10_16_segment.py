#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 10_16 Initial capacity 数据片段拟合 2RC（R0(SOC)+R1(SOC)+R2(SOC)+tau_ref）。

为什么要做这一步？
- 仅用常数 R0 往往难以解释“低 SOC 下的超深尖峰”（瞬时压降明显变大）；
- 若把这部分压降错误地交给慢支路（v2）去吸收，会导致：
  - 参数不可辨识退化（tau2 过大、快支路不见了）
  - 在 Incremental OCV 验证集上“优化反而变差”

本脚本的做法（更物理、更稳健）：
1) 让 R0 随 SOC 单调上升（这里用 SOC=1 与 SOC=0 两点线性曲线表达）；
2) 拟合 R1(SOC)、R2(SOC)（单调分段线性）；
3) 用 tau1_ref/tau2_ref（在 SOC=1 处）约束时间尺度，抑制退化解。

输出：
- 生成一份电池配置 JSON（供 validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py 调用）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams1ECM
from mcm26a.calibration import extract_channel_time_series, fit_r0_curve_and_r1_r2_curves_and_taus, load_calce_channel_xlsx


def _default_xlsx() -> Path:
    return (
        SRC_DIR.parent
        / "data"
        / "calce-umd"
        / "extracted"
        / "battery-data"
        / "SP"
        / "10_16_2015_Initial capacity_SP20-1.xlsx"
    )


def _seed_cfg() -> Path:
    # 提供 OCV 曲线（来自低电流拟合产物）
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _infer_dt_s(t_s: np.ndarray) -> np.ndarray:
    t = np.asarray(t_s, dtype=float)
    dt = np.diff(t, prepend=t[0])
    med = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 1.0
    dt = np.where(dt > 0, dt, med)
    return dt


def main() -> int:
    ap = argparse.ArgumentParser(description="CALCE SP20-1：10_16 片段拟合 2RC（R0(SOC)+R1/R2(SOC)+tau_ref）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="10_16 Initial capacity xlsx（Channel/Sheet1 格式）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 曲线的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0curve_2rc_r1r2soc_tau_10_16seg.json"),
        help="输出配置 JSON 路径",
    )

    # 选段：默认 step 5~8（充满后休止 -> 1A 放电 -> 休止恢复）
    ap.add_argument("--step-start", type=int, default=5, help="片段起始 Step_Index（默认 5）")
    ap.add_argument("--step-end", type=int, default=8, help="片段结束 Step_Index（默认 8，包含）")

    # 拟合权重与下采样
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--w-rest", type=float, default=3.0, help="休止段权重（默认 3）")
    ap.add_argument("--w-rest-early", type=float, default=10.0, help="休止段 early 时间窗权重（默认 10）")
    ap.add_argument("--early-window-s", type=float, default=60.0, help="定义休止段 early 的时间窗（秒，默认 60）")
    ap.add_argument("--stride", type=int, default=2, help="下采样步长（默认 2）")

    # SOC 结点与时间常数范围
    ap.add_argument("--soc-knots", default="1.0,0.5,0.2,0.1,0.05,0.0", help="SOC 结点（高到低，逗号分隔）")
    ap.add_argument("--tau1-lo", type=float, default=2.0, help="快支路 tau1_ref 下界（秒）")
    ap.add_argument("--tau1-hi", type=float, default=120.0, help="快支路 tau1_ref 上界（秒）")
    ap.add_argument("--tau2-lo", type=float, default=200.0, help="慢支路 tau2_ref 下界（秒）")
    ap.add_argument("--tau2-hi", type=float, default=20000.0, help="慢支路 tau2_ref 上界（秒）")
    ap.add_argument("--r-hi", type=float, default=1.5, help="R1/R2@SOC=1 的上界（欧姆，默认 1.5）")
    ap.add_argument("--dr-hi", type=float, default=1.5, help="ΔR1/ΔR2 的上界（欧姆，默认 1.5）")

    # R0(SOC) 端点约束
    ap.add_argument("--r0-1-lo", type=float, default=1e-4, help="R0@SOC=1 下界（欧姆）")
    ap.add_argument("--r0-1-hi", type=float, default=0.8, help="R0@SOC=1 上界（欧姆）")
    ap.add_argument("--dr0-lo", type=float, default=1e-6, help="ΔR0 下界（欧姆）")
    ap.add_argument("--dr0-hi", type=float, default=2.5, help="ΔR0 上界（欧姆）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    seed_phone = Path(args.seed_phone).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2
    if not seed_phone.exists():
        print(f"[ERROR] 找不到 seed-phone：{seed_phone}", file=sys.stderr)
        return 2

    seed = BatteryParams1ECM.from_json(seed_phone)
    cap_ah = float(seed.capacity_Ah)
    ocv = seed.ocv

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)

    # 1) 选段（Step_Index 连续片段）
    step = np.asarray(ts.step, dtype=int)
    t_all = np.asarray(ts.t_s, dtype=float)
    a = int(np.argmax(step >= int(args.step_start)))
    b = int(len(step) - np.argmax(step[::-1] <= int(args.step_end)))
    if b <= a + 10:
        print("[ERROR] 选段失败：请检查 step-start/step-end 是否存在于数据中", file=sys.stderr)
        return 2

    t_s = t_all[a:b]
    i_A = np.asarray(ts.i_A[a:b], dtype=float)
    v_meas = np.asarray(ts.v_V[a:b], dtype=float)
    step_seg = step[a:b]

    # 2) SOC0：用片段起始休止段电压近似 OCV 反推（只用于仿真起点）
    rest_i = float(args.rest_i)
    m0 = (np.abs(i_A) <= rest_i) & (t_s <= float(t_s[0]) + float(args.early_window_s))
    v0 = float(np.median(v_meas[m0])) if int(np.sum(m0)) >= 10 else float(v_meas[0])
    soc0 = float(ocv.soc_from_ocv_v(v0))
    soc0 = min(1.0, max(0.0, soc0))
    print(f"[SOC0] 由起始休止段电压反推：V0≈{v0:.4f}V -> SOC0≈{soc0:.3f}")

    dur_h = float((t_s[-1] - t_s[0]) / 3600.0)
    print(f"[片段] idx=[{a},{b})  n={len(t_s)}  duration≈{dur_h:.2f} h  steps={sorted(set(int(x) for x in step_seg.tolist()))}")

    # 3) 权重：提高休止段（尤其 very-early）权重，强化“恢复动态”可辨识性
    w = np.ones_like(v_meas, dtype=float)
    m_rest = np.abs(i_A) <= rest_i
    w[m_rest] = float(args.w_rest)
    # 以每个休止段自身起点为参考，取 early-window-s 加权
    if np.any(m_rest):
        rest = m_rest.astype(int)
        starts = np.where((rest[1:] == 1) & (rest[:-1] == 0))[0] + 1
        if rest[0] == 1:
            starts = np.concatenate([[0], starts])
        for s0 in starts.tolist():
            t0 = float(t_s[int(s0)])
            m_early = m_rest & (t_s >= t0) & (t_s <= t0 + float(args.early_window_s))
            w[m_early] = float(args.w_rest_early)

    # 4) 下采样（重算 dt）
    stride = max(1, int(args.stride))
    idx_ds = np.arange(0, len(t_s), stride, dtype=int)
    t_s_ds = t_s[idx_ds]
    dt_s_ds = _infer_dt_s(t_s_ds)
    i_A_ds = i_A[idx_ds]
    v_meas_ds = v_meas[idx_ds]
    w_ds = w[idx_ds]
    mask_ds = np.ones_like(v_meas_ds, dtype=bool)
    print(f"[下采样] stride={stride}  n: {len(t_s)} -> {len(t_s_ds)}")

    soc_knots_desc = tuple(float(s.strip()) for s in str(args.soc_knots).split(",") if s.strip())
    fit = fit_r0_curve_and_r1_r2_curves_and_taus(
        soc0=float(soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        capacity_Ah=float(cap_ah),
        ocv=ocv,
        dt_s=dt_s_ds,
        i_A=i_A_ds,
        v_meas_V=v_meas_ds,
        mask=mask_ds,
        weights=w_ds,
        soc_knots_desc=soc_knots_desc,
        r0_1_bounds_ohm=(float(args.r0_1_lo), float(args.r0_1_hi)),
        dr0_bounds_ohm=(float(args.dr0_lo), float(args.dr0_hi)),
        tau1_bounds_s=(float(args.tau1_lo), float(args.tau1_hi)),
        tau2_bounds_s=(float(args.tau2_lo), float(args.tau2_hi)),
        r_bounds_ohm=(1e-4, float(args.r_hi)),
        dr_bounds_ohm=(1e-6, float(args.dr_hi)),
    )

    print("[拟合] 2RC（R0(SOC)+R1/R2(SOC)+tau_ref）完成：")
    print(f"- R0@SOC=1: {fit.r0_ohm_at1:.4f}Ω")
    print(f"- R0@SOC=0: {fit.r0_ohm_at0:.4f}Ω")
    print(f"- tau1_ref≈{fit.tau1_ref_s:.2f}s  tau2_ref≈{fit.tau2_ref_s:.1f}s")
    print(f"- C1={fit.c1_F:.1f}F  C2={fit.c2_F:.1f}F  (C2/C1≈{fit.c2_F/fit.c1_F:.1f})")
    print(f"- RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")

    # 5) 写出配置（在 seed 配置基础上覆盖/新增 2RC 参数）
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(float(cap_ah) * 1000.0))
    ecm = batt.get("ecm", {})

    ecm["R0_ohm"] = float(fit.r0_ohm_at1)
    ecm["R0_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r0_curve.points]}
    ecm["C1_F"] = float(fit.c1_F)
    ecm["C2_F"] = float(fit.c2_F)
    ecm["R1_ohm"] = float(fit.r1_curve.value(1.0))
    ecm["R2_ohm"] = float(fit.r2_curve.value(1.0))
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    ecm["R2_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r2_curve.points]}

    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration_2rc_r0curve_r1r2soc_tau_10_16seg"] = {
        "source_xlsx": str(xlsx),
        "segment_steps_inclusive": [int(args.step_start), int(args.step_end)],
        "method": "least-squares (R0 linear curve + R1(SOC),R2(SOC) monotone + tau1_ref,tau2_ref) on discharge+rest segment",
        "capacity_Ah_used": float(cap_ah),
        "soc_knots_desc": [float(x) for x in soc_knots_desc],
        "bounds": {
            "r0_soc1_ohm": [float(args.r0_1_lo), float(args.r0_1_hi)],
            "dr0_ohm": [float(args.dr0_lo), float(args.dr0_hi)],
            "tau1_ref_s": [float(args.tau1_lo), float(args.tau1_hi)],
            "tau2_ref_s": [float(args.tau2_lo), float(args.tau2_hi)],
        },
        "weights": {
            "w_rest": float(args.w_rest),
            "w_rest_early": float(args.w_rest_early),
            "early_window_s": float(args.early_window_s),
        },
        "fit_stride": int(stride),
        "fit_result": {
            "r0_ohm_at1": float(fit.r0_ohm_at1),
            "r0_ohm_at0": float(fit.r0_ohm_at0),
            "tau1_ref_s": float(fit.tau1_ref_s),
            "tau2_ref_s": float(fit.tau2_ref_s),
            "c1_F": float(fit.c1_F),
            "c2_F": float(fit.c2_F),
            "rmse_mV_weighted": float(fit.rmse_V) * 1000.0,
            "mae_mV_weighted": float(fit.mae_V) * 1000.0,
        },
    }
    out_cfg["meta"] = meta

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[输出] 已写出：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
