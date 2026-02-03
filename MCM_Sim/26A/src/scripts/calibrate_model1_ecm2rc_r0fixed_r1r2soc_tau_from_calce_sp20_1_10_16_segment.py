#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 10_16 Initial capacity 数据的“充满后放电+休止恢复”片段拟合 2RC 的 SOC 相关阻抗。

我们要解决什么问题？
- 在 Incremental OCV 验证集中，电压曲线包含明显的“尖峰 + 快速回弹 + 缓慢恢复（小时级）”结构；
- 常参 2RC 很容易出现折中：高 SOC 拟合不错，但低 SOC 的深放电/恢复段明显偏差；
- 物理解释：低 SOC 下阻抗/扩散极化显著增强，时间尺度与幅值都发生变化；
  => 需要 R1(SOC)/R2(SOC)（单调）来表达“越接近耗尽越难放电”的机理。

本脚本的做法：
1) 固定 R0（来自 rest-load 跳变估计，避免 R0 在低电流/长曲线中不可辨识而触底）；
2) 拟合 R1(SOC)、R2(SOC)（单调分段线性）；
3) 用“参考时间常数 tau_ref（在 SOC=1 处）”约束时间尺度可辨识性：
   - tau1_ref：秒级（快支路）
   - tau2_ref：分钟~小时级（慢支路）
   这样能抑制“tau2 过大吸收 OCV 偏差”的退化解。

输出：
- 生成一份 2RC 电池配置 JSON（供后续验证脚本调用）
  scripts/validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py
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
from mcm26a.calibration import (
    estimate_r0_from_rest_load_transitions,
    extract_channel_time_series,
    fit_r1_r2_curves_and_taus_given_r0,
    load_calce_channel_xlsx,
)


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
    ap = argparse.ArgumentParser(description="CALCE SP20-1：10_16 片段拟合 2RC（R1/R2(SOC)+tau_ref，固定 R0）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="10_16 Initial capacity xlsx（Channel/Sheet1 格式）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 曲线的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_r1r2soc_tau_10_16seg.json"),
        help="输出配置 JSON 路径",
    )

    # 选段：默认使用 step 5~8（充满后休止 -> 1A 放电 -> 休止恢复）
    ap.add_argument("--step-start", type=int, default=5, help="片段起始 Step_Index（默认 5）")
    ap.add_argument("--step-end", type=int, default=8, help="片段结束 Step_Index（默认 8，包含）")

    # R0 估计参数
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--load-i", type=float, default=0.2, help="判定负载段的电流阈值（A）")
    ap.add_argument("--n-rest", type=int, default=20, help="边界前 rest 窗口点数")
    ap.add_argument("--n-load", type=int, default=5, help="边界后 load 窗口点数（越小越接近“瞬时”）")
    ap.add_argument("--min-gap", type=int, default=200, help="事件最小间隔（点）")
    ap.add_argument("--r0", type=float, default=-1.0, help="手动指定 R0（欧姆）；<0 表示从 10_16 全数据估计")

    # 拟合权重与下采样
    ap.add_argument("--w-rest", type=float, default=3.0, help="休止段权重（默认 3）")
    ap.add_argument("--w-rest-early", type=float, default=8.0, help="休止段 early 时间窗权重（默认 8）")
    ap.add_argument("--early-window-s", type=float, default=30.0, help="定义休止段 early 的时间窗（秒，默认 30）")
    ap.add_argument("--stride", type=int, default=3, help="下采样步长（默认 3）")

    # SOC 结点与时间常数范围
    ap.add_argument("--soc-knots", default="1.0,0.5,0.2,0.1,0.05,0.0", help="SOC 结点（高到低，逗号分隔）")
    ap.add_argument("--tau1-lo", type=float, default=0.5, help="快支路 tau1_ref 下界（秒）")
    ap.add_argument("--tau1-hi", type=float, default=20.0, help="快支路 tau1_ref 上界（秒）")
    ap.add_argument("--tau2-lo", type=float, default=30.0, help="慢支路 tau2_ref 下界（秒）")
    ap.add_argument("--tau2-hi", type=float, default=20000.0, help="慢支路 tau2_ref 上界（秒）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    seed_phone = Path(args.seed_phone).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    batt_seed = BatteryParams1ECM.from_json(seed_phone)
    ocv = batt_seed.ocv
    cap_ah_seed = float(batt_seed.capacity_Ah)

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)

    # 容量校正（非常关键，直接影响 SOC 漂移与 TTE 位置）。
    #
    # 说明：
    # - Initial capacity 测试的 Discharge_Capacity(Ah) 往往只到“某个截止电压”，并不一定对应 SOC=0；
    #   因此不应直接把它当作“满电->0 的总容量”，否则会导致 SOC 被拉到过低，拟合反而崩掉。
    # - 更稳健的做法：用“该段放电的库仑量 Ah_dis” 与 “OCV 反推的 SOC 跨度 ΔSOC” 组合估计：
    #     capacity ≈ Ah_dis / ΔSOC
    # - 这里先记录 Discharge_Capacity(Ah) 的极差作为参考，不直接用于拟合容量。
    cap_ah = float(cap_ah_seed)
    cap_source = "seed_config"
    cap_discharge_col_delta = None
    if "Discharge_Capacity(Ah)" in df.columns:
        x = df["Discharge_Capacity(Ah)"].to_numpy(dtype=float)
        x = x[np.isfinite(x)]
        if len(x):
            cap_discharge_col_delta = float(np.max(x) - np.min(x))

    # 1) 估计 R0（全数据）
    r0_ohm = float(args.r0)
    if r0_ohm < 0:
        est = estimate_r0_from_rest_load_transitions(
            ts,
            rest_i_thresh_A=float(args.rest_i),
            load_i_thresh_A=float(args.load_i),
            n_rest=int(args.n_rest),
            n_load=int(args.n_load),
            min_gap=int(args.min_gap),
        )
        s = est.summary()
        if int(s.get("n", 0)) <= 0:
            print("[R0] 未能从 10_16 估计到有效 R0。请调整阈值或改用更脉冲化的数据。", file=sys.stderr)
            return 2
        r0_ohm = float(s["median_ohm"])
        print(f"[R0] 估计：n={s['n']}  median={s['median_ohm']:.4f}Ω  p10={s['p10_ohm']:.4f}Ω  p90={s['p90_ohm']:.4f}Ω")
    else:
        print(f"[R0] 手动指定：R0={r0_ohm:.4f}Ω")

    # 2) 选取片段（step_start~step_end）
    step = np.asarray(ts.step, dtype=int)
    seg = (step >= int(args.step_start)) & (step <= int(args.step_end))
    if not bool(np.any(seg)):
        print("[ERROR] 选段为空：请检查 step-start/step-end。", file=sys.stderr)
        return 2

    idx_seg = np.where(seg)[0]
    a, b = int(idx_seg[0]), int(idx_seg[-1] + 1)
    t_s = np.asarray(ts.t_s[a:b], dtype=float)
    i_A = np.asarray(ts.i_A[a:b], dtype=float)
    v_meas = np.asarray(ts.v_V[a:b], dtype=float)
    step_seg = np.asarray(ts.step[a:b], dtype=int)

    # 3) SOC0：用片段起始休止段电压近似 OCV 反推
    rest_i = float(args.rest_i)
    m0 = (np.abs(i_A) <= rest_i) & (t_s <= float(t_s[0]) + float(args.early_window_s))
    v0 = float(np.median(v_meas[m0])) if int(np.sum(m0)) >= 10 else float(v_meas[0])
    soc0 = float(ocv.soc_from_ocv_v(v0))
    soc0 = min(1.0, max(0.0, soc0))
    print(f"[SOC0] 由起始休止段电压反推：V0≈{v0:.4f}V -> SOC0≈{soc0:.3f}")

    # 3.1) 估计该片段的有效容量（用库仑量 / ΔSOC）。
    # - Ah_dis：片段内放电（I>0）库仑计数
    # - SOC_end：取“最后一个休止段”的末尾电压近似 OCV，反推 SOC
    dt_seg = _infer_dt_s(t_s)
    ah_dis = float(np.sum(np.clip(i_A, 0.0, None) * dt_seg) / 3600.0)
    soc_end = None
    # 找最后一个休止段（|I|<=rest_i）的 [start,end) 区间
    m_rest_seg = np.abs(i_A) <= rest_i
    if bool(np.any(m_rest_seg)):
        rest = m_rest_seg.astype(int)
        starts = np.where((rest[1:] == 1) & (rest[:-1] == 0))[0] + 1
        if rest[0] == 1:
            starts = np.concatenate([[0], starts])
        ends = np.where((rest[1:] == 0) & (rest[:-1] == 1))[0] + 1
        if rest[-1] == 1:
            ends = np.concatenate([ends, [len(rest)]])
        if len(starts) and len(ends) and len(starts) == len(ends):
            s_last = int(starts[-1])
            e_last = int(ends[-1])
            if e_last - s_last >= 10:
                # 用休止段末尾 600s 的中位数电压，尽量逼近准平衡 OCV
                t0 = float(t_s[s_last])
                t1 = float(t_s[e_last - 1])
                w_s = min(600.0, max(30.0, 0.5 * max(0.0, t1 - t0)))
                m_tail = m_rest_seg & (t_s >= (t1 - w_s))
                if int(np.sum(m_tail)) >= 10:
                    v_end = float(np.median(v_meas[m_tail]))
                    soc_end = float(ocv.soc_from_ocv_v(v_end))
                    soc_end = min(1.0, max(0.0, soc_end))

    if soc_end is not None and (soc0 - float(soc_end)) > 0.05 and ah_dis > 0.05:
        cap_est = float(ah_dis / max(1e-12, (soc0 - float(soc_end))))
        if 0.5 <= cap_est <= 10.0:
            cap_ah = float(cap_est)
            cap_source = "from_coulomb_count_and_ocv_soc_span"

    cap_msg = f"[容量] seed={cap_ah_seed:.4f}Ah  used={cap_ah:.4f}Ah  source={cap_source}"
    if cap_discharge_col_delta is not None:
        cap_msg += f"  discharge_col_delta≈{cap_discharge_col_delta:.4f}Ah"
    if soc_end is not None:
        cap_msg += f"  ah_dis≈{ah_dis:.4f}Ah  soc_end≈{float(soc_end):.3f}"
    print(cap_msg)

    dur_h = float((t_s[-1] - t_s[0]) / 3600.0)
    print(f"[片段] idx=[{a},{b})  n={len(t_s)}  duration≈{dur_h:.2f} h  steps={sorted(set(int(x) for x in step_seg.tolist()))}")

    # 4) 权重：提高休止段（尤其 very-early）权重，强化“快/慢恢复”可辨识性
    w = np.ones_like(v_meas, dtype=float)
    m_rest = np.abs(i_A) <= rest_i
    w[m_rest] = float(args.w_rest)
    # 以每个休止段自身起点为参考，取 early-window-s 加权
    if np.any(m_rest):
        # 找每个休止段的起点
        rest = m_rest.astype(int)
        starts = np.where((rest[1:] == 1) & (rest[:-1] == 0))[0] + 1
        if rest[0] == 1:
            starts = np.concatenate([[0], starts])
        for s0 in starts.tolist():
            t0 = float(t_s[int(s0)])
            m_early = m_rest & (t_s >= t0) & (t_s <= t0 + float(args.early_window_s))
            w[m_early] = float(args.w_rest_early)

    # 5) 下采样（重算 dt）
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
    fit = fit_r1_r2_curves_and_taus_given_r0(
        soc0=float(soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        capacity_Ah=float(cap_ah),
        ocv=ocv,
        r0_ohm=float(r0_ohm),
        dt_s=dt_s_ds,
        i_A=i_A_ds,
        v_meas_V=v_meas_ds,
        mask=mask_ds,
        weights=w_ds,
        soc_knots_desc=soc_knots_desc,
        tau1_bounds_s=(float(args.tau1_lo), float(args.tau1_hi)),
        tau2_bounds_s=(float(args.tau2_lo), float(args.tau2_hi)),
    )

    print("[拟合] 2RC（固定 R0 + R1/R2(SOC) + tau_ref）完成：")
    print(f"- R0={fit.r0_ohm:.4f}Ω（fixed）")
    print(f"- tau1_ref≈{fit.tau1_ref_s:.2f}s  tau2_ref≈{fit.tau2_ref_s:.1f}s")
    print(f"- C1={fit.c1_F:.1f}F  C2={fit.c2_F:.1f}F  (C2/C1≈{fit.c2_F/fit.c1_F:.1f})")
    print(f"- RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")
    print("- R1(SOC) 结点：")
    for s, v in fit.r1_curve.points:
        print(f"  - SOC={s:.2f}: R1={v:.4f}Ω")
    print("- R2(SOC) 结点：")
    for s, v in fit.r2_curve.points:
        print(f"  - SOC={s:.2f}: R2={v:.4f}Ω")

    # 6) 写出配置（在 seed 配置基础上覆盖/新增 2RC 参数）
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(float(cap_ah) * 1000.0))

    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    ecm["C2_F"] = float(fit.c2_F)
    ecm["R1_ohm"] = float(fit.r1_curve.value(1.0))
    ecm["R2_ohm"] = float(fit.r2_curve.value(1.0))
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    ecm["R2_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r2_curve.points]}
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration_2rc_r0fixed_r1r2soc_tau_10_16seg"] = {
        "source_xlsx": str(xlsx),
        "segment_steps_inclusive": [int(args.step_start), int(args.step_end)],
        "method": "R0 from rest-load transitions + least-squares (R1(SOC),R2(SOC) monotone + tau1_ref,tau2_ref) on discharge+rest segment",
        "r0_ohm_used": float(fit.r0_ohm),
        "capacity_Ah_seed": float(cap_ah_seed),
        "capacity_Ah_used": float(cap_ah),
        "capacity_source": str(cap_source),
        "capacity_discharge_col_delta_Ah": (None if cap_discharge_col_delta is None else float(cap_discharge_col_delta)),
        "capacity_ah_dis_segment_Ah": float(ah_dis),
        "capacity_soc0_used": float(soc0),
        "capacity_soc_end_est": (None if soc_end is None else float(soc_end)),
        "soc_knots_desc": [float(x) for x in soc_knots_desc],
        "tau_bounds_s": {
            "tau1_ref": [float(args.tau1_lo), float(args.tau1_hi)],
            "tau2_ref": [float(args.tau2_lo), float(args.tau2_hi)],
        },
        "weights": {
            "w_rest": float(args.w_rest),
            "w_rest_early": float(args.w_rest_early),
            "early_window_s": float(args.early_window_s),
        },
        "fit_stride": int(stride),
        "fit_result": {
            "tau1_ref_s": float(fit.tau1_ref_s),
            "tau2_ref_s": float(fit.tau2_ref_s),
            "c1_F": float(fit.c1_F),
            "c2_F": float(fit.c2_F),
            "rmse_mV_weighted": float(fit.rmse_V * 1000.0),
            "mae_mV_weighted": float(fit.mae_V * 1000.0),
        },
        "notes_zh": "本配置用于解释“低 SOC 深放电后仍有较大极化电压、且恢复存在快/慢双时间尺度”的现象。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
