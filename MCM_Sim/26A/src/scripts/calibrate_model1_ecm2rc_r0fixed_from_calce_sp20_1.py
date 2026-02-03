#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用“R0 先验 + 低电流数据”校准二阶 Thevenin 2RC ECM（Model-1 扩展）。

设计动机（来自 no3 的可用技术点）：
- 1RC 常能拟合“单一时间尺度”的恢复，但对“秒级 + 分钟级”并存的松弛现象往往不够；
- 2RC（双极化）用两个时间常数解释“快速回弹 + 慢速恢复”，更贴近真实；
- 同时延续我们已验证有效的分阶段辨识：
  - 用含阶跃/脉冲数据估计 R0（瞬时欧姆压降）
  - 固定 R0，用低电流数据拟合极化支路（R1||C1 与 R2||C2）

注意：
- 本脚本只负责生成“2RC 电池配置 JSON”（供后续验证脚本调用）。
- 本版本拟合：C1/C2（常数）+ R1(SOC)/R2(SOC)（单调分段线性），以避免“常参 2RC 难以同时解释高/低 SOC”的问题。
- 验证（独立数据）请用：scripts/validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py
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
from mcm26a.battery.ocv import PiecewiseLinearOCV
from mcm26a.calibration import (
    fit_c1_c2_and_r1_r2_curves_given_r0,
    estimate_r0_from_rest_load_transitions,
    extract_channel_time_series,
    extract_time_series,
    load_calce_channel_xlsx,
    load_calce_df,
)


def _default_low_current_xlsx() -> Path:
    return (
        SRC_DIR.parent
        / "data"
        / "calce-umd"
        / "extracted"
        / "battery-data"
        / "SP"
        / "11_5_2015_low current OCV test_SP20-1.xlsx"
    )


def _default_pulse_xlsx() -> Path:
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
    # 提供 OCV 初值（来自低电流拟合）
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _compute_capacity_from_discharge(ts, *, discharge_step: int = 3, i_min_A: float = 0.02) -> float:
    m = (ts.step.astype(int) == int(discharge_step)) & (ts.i_A > float(i_min_A))
    if int(np.sum(m)) < 100:
        return float("nan")
    cap_ah = float(np.sum(ts.i_A[m] * ts.dt_s[m] / 3600.0))
    return cap_ah


def main() -> int:
    ap = argparse.ArgumentParser(description="CALCE SP20-1：R0 先验 + 2RC（双极化）拟合")
    ap.add_argument("--low-current-xlsx", default=str(_default_low_current_xlsx()), help="低电流 OCV xlsx（Pgm step 格式）")
    ap.add_argument("--pulse-xlsx", default=str(_default_pulse_xlsx()), help="含阶跃/脉冲的 xlsx（Channel/Sheet1 格式）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 初值的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_2rc.json"),
        help="输出配置 JSON 路径",
    )

    # R0 估计参数
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--load-i", type=float, default=0.2, help="判定负载段的电流阈值（A）")
    ap.add_argument("--n-rest", type=int, default=20, help="边界前 rest 窗口点数")
    ap.add_argument("--n-load", type=int, default=20, help="边界后 load 窗口点数")
    ap.add_argument("--min-gap", type=int, default=200, help="事件最小间隔（点）")
    ap.add_argument("--r0", type=float, default=-1.0, help="手动指定 R0（欧姆）；<0 表示从 pulse 数据估计")

    # 2RC 拟合窗口与权重（沿用我们当前“先解释恢复效应”的策略）
    # 低电流 OCV 文件里 step=2 可能是小电流充电/预处理段；为了避免引入未知初始极化状态，
    # 这里默认只取 discharge+rest（3,4）做拟合更稳健。
    ap.add_argument("--steps", default="3,4", help="低电流数据使用哪些 Pgm step（逗号分隔）。默认 3,4")
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在 step（默认 3）")
    ap.add_argument("--soc0", type=float, default=1.0, help="低电流数据起始 SOC（默认 1.0）")
    ap.add_argument("--i-min-A", type=float, default=0.02, help="用于识别放电段/容量计算的最小电流阈值（A）")
    ap.add_argument("--w-step4", type=float, default=2.0, help="拟合时 step=4 的残差权重（默认 2.0）")
    ap.add_argument("--w-step4-early", type=float, default=4.0, help="拟合时 step=4 前 early-window-s 的权重（默认 4.0）")
    ap.add_argument("--early-window-s", type=float, default=600.0, help="定义 step=4“早期”的时间窗（秒，默认 600）")
    ap.add_argument("--soc-knots", default="1.0,0.2,0.1,0.05,0.0", help="R1/R2(SOC) 结点（按 SOC 从高到低，逗号分隔）")
    ap.add_argument("--stride", type=int, default=5, help="拟合时下采样步长（每 stride 点取 1 点，默认 5）")

    args = ap.parse_args()

    # 0) 读取 seed（提供 OCV 初值）
    seed_phone = Path(args.seed_phone).expanduser().resolve()
    batt_seed_1rc = BatteryParams1ECM.from_json(seed_phone)
    ocv0: PiecewiseLinearOCV = batt_seed_1rc.ocv

    # 1) 估计 R0（来自 pulse 数据）
    r0_ohm = float(args.r0)
    pulse_xlsx = Path(args.pulse_xlsx).expanduser().resolve()
    if r0_ohm < 0:
        df_pulse = load_calce_channel_xlsx(pulse_xlsx)
        ts_pulse = extract_channel_time_series(df_pulse)
        est = estimate_r0_from_rest_load_transitions(
            ts_pulse,
            rest_i_thresh_A=float(args.rest_i),
            load_i_thresh_A=float(args.load_i),
            n_rest=int(args.n_rest),
            n_load=int(args.n_load),
            min_gap=int(args.min_gap),
        )
        s = est.summary()
        if int(s.get("n", 0)) <= 0:
            print("[R0] 未能从 pulse 数据估计到有效 R0（事件太少或阈值不合适）。", file=sys.stderr)
            return 2
        r0_ohm = float(s["median_ohm"])
        print(f"[R0] 由 pulse 数据估计：n={s['n']}  median={s['median_ohm']:.4f}Ω  p10={s['p10_ohm']:.4f}Ω  p90={s['p90_ohm']:.4f}Ω")
    else:
        print(f"[R0] 手动指定：R0={r0_ohm:.4f}Ω")

    # 2) 低电流数据：固定 R0 拟合 2RC（R1/R2(SOC) + C1/C2）
    low_xlsx = Path(args.low_current_xlsx).expanduser().resolve()
    df = load_calce_df(low_xlsx)
    steps = tuple(int(s.strip()) for s in str(args.steps).split(",") if s.strip())
    ts = extract_time_series(df, steps=steps)

    cap_ah = _compute_capacity_from_discharge(ts, discharge_step=int(args.discharge_step), i_min_A=float(args.i_min_A))
    if not np.isfinite(cap_ah) or cap_ah <= 0:
        cap_ah = float(batt_seed_1rc.capacity_Ah)
    print(f"[容量] capacity≈{cap_ah:.4f}Ah（用于 SOC 积分）")

    # 拟合 mask：step=放电 或 step=4（休止）
    mask_fit = (ts.step.astype(int) == int(args.discharge_step)) | (ts.step.astype(int) == 4)

    # 权重：提高休止段（尤其 early）的权重以优先解释“恢复效应”
    weights = np.ones_like(ts.v_V, dtype=float)
    m4 = ts.step.astype(int) == 4
    weights[m4] = float(args.w_step4)
    idx4 = np.where(m4)[0]
    if len(idx4) > 0:
        t0 = float(ts.t_s[idx4[0]])
        early = m4 & (ts.t_s < t0 + float(args.early_window_s))
        weights[early] = float(args.w_step4_early)

    # 下采样：加速拟合
    stride = max(1, int(args.stride))
    idx = np.arange(0, len(ts.t_s), stride, dtype=int)
    # 注意：抽样后 dt 不能直接取 ts.dt_s[idx]（那是原始相邻采样点的 dt，会把时间“缩短”stride 倍）。
    # 正确做法：用抽样后的时间戳重新计算 dt。
    t_s_ds = ts.t_s[idx].astype(float)
    dt_s = np.diff(t_s_ds, prepend=t_s_ds[0])
    med = float(np.median(dt_s[dt_s > 0])) if np.any(dt_s > 0) else 1.0
    dt_s = np.where(dt_s > 0, dt_s, med)

    i_A = ts.i_A[idx]
    v_meas = ts.v_V[idx]
    w = weights[idx]
    mask = mask_fit[idx]

    if int(np.sum(mask)) < 200:
        print("[ERROR] 拟合点太少（下采样过大或数据不完整）。", file=sys.stderr)
        return 2

    soc_knots_desc = tuple(float(s.strip()) for s in str(args.soc_knots).split(",") if s.strip())
    fit = fit_c1_c2_and_r1_r2_curves_given_r0(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        capacity_Ah=float(cap_ah),
        ocv=ocv0,
        r0_ohm=float(r0_ohm),
        dt_s=dt_s,
        i_A=i_A,
        v_meas_V=v_meas,
        mask=mask,
        weights=w,
        soc_knots_desc=soc_knots_desc,
    )

    print("[拟合] 2RC（固定 R0 + R1/R2(SOC)）完成：")
    print(f"- R0={fit.r0_ohm:.4f}Ω（fixed）")
    print(f"- C1={fit.c1_F:.1f}F  C2={fit.c2_F:.1f}F  (C2/C1≈{fit.c2_F/fit.c1_F:.1f})")
    print(f"- RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")
    print("- R1(SOC) 结点：")
    for s, v in fit.r1_curve.points:
        print(f"  - SOC={s:.2f}: R1={v:.4f}Ω")
    print("- R2(SOC) 结点：")
    for s, v in fit.r2_curve.points:
        print(f"  - SOC={s:.2f}: R2={v:.4f}Ω")

    # 用全分辨率（不下采样）复算一次误差（仅作自检，最终好坏以“独立验证集”衡量）
    from mcm26a.battery.model1_ecm2rc import simulate_ecm2rc_current_control

    _, _, _, v_pred_full = simulate_ecm2rc_current_control(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        capacity_Ah=float(cap_ah),
        ocv=ocv0,
        r0_ohm=float(fit.r0_ohm),
        r0_curve=None,
        c1_F=float(fit.c1_F),
        c2_F=float(fit.c2_F),
        r1_curve=fit.r1_curve,
        r2_curve=fit.r2_curve,
        rate_capacity_k_per_A=float(getattr(batt_seed_1rc, "rate_capacity_k_per_A", 0.0)),
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    err = np.asarray(v_pred_full, dtype=float) - np.asarray(ts.v_V, dtype=float)
    rmse_full = float(np.sqrt(np.mean(err * err)))
    mae_full = float(np.mean(np.abs(err)))
    print(f"[复算] 全分辨率误差：RMSE={rmse_full*1000:.1f}mV  MAE={mae_full*1000:.1f}mV  (n={len(err)})")

    # 3) 写出配置（在 seed 配置基础上覆盖/新增 2RC 参数）
    out_path = Path(args.out).expanduser().resolve()
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(float(cap_ah) * 1000.0))

    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    ecm["C2_F"] = float(fit.c2_F)
    # 参考值：SOC=1.0 处
    ecm["R1_ohm"] = float(fit.r1_curve.value(1.0))
    ecm["R2_ohm"] = float(fit.r2_curve.value(1.0))
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    ecm["R2_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r2_curve.points]}
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration_2rc_r0fixed"] = {
        "r0_source_xlsx": str(pulse_xlsx),
        "low_current_xlsx": str(low_xlsx),
        "method": "R0 from rest-load transitions + least-squares (2RC: C1,C2 + R1(SOC),R2(SOC) monotone piecewise-linear) with fixed R0",
        "r0_ohm_used": float(fit.r0_ohm),
        "soc_knots_desc": [float(x) for x in soc_knots_desc],
        "fit_stride": int(stride),
        "notes_zh": "2RC 用两个时间尺度解释“快速回弹 + 慢速恢复”。为覆盖高/低 SOC 的阻抗差异，这里用 R1(SOC)/R2(SOC) 单调曲线。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
