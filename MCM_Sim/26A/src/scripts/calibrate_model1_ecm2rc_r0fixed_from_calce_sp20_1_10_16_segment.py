#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用 10_16 Initial capacity 数据中的“充满后放电+休止恢复”片段拟合常参 2RC。

为什么要做这件事？
- 低电流 OCV 数据对 RC 支路（极化/扩散）的辨识能力很弱，容易把时间常数拟合到“过快”；
- 但 Incremental OCV 验证集包含很长的休止恢复（分钟~小时尺度），需要慢时间常数才能解释；
- 因此先用 10_16（含 1A 放电 + 长休止）拟合 2RC 的两条时间尺度，
  再把结果拿去 Incremental OCV 上做独立验证（避免“用验证集调参”）。
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
from mcm26a.calibration import estimate_r0_from_rest_load_transitions, extract_channel_time_series, fit_2rc_const_given_r0, load_calce_channel_xlsx


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
    # 提供 OCV 初值（来自低电流拟合产物）
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _infer_dt_s(t_s: np.ndarray) -> np.ndarray:
    t = np.asarray(t_s, dtype=float)
    dt = np.diff(t, prepend=t[0])
    med = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 1.0
    dt = np.where(dt > 0, dt, med)
    return dt


def _compute_discharge_capacity_ah(ts, *, discharge_i_min_A: float = 0.2) -> float:
    i = np.asarray(ts.i_A, dtype=float)
    m = i >= float(discharge_i_min_A)
    if int(np.sum(m)) < 200:
        return float("nan")
    cap_ah = float(np.sum(i[m] * np.asarray(ts.dt_s, dtype=float)[m] / 3600.0))
    return cap_ah


def main() -> int:
    ap = argparse.ArgumentParser(description="CALCE SP20-1：用 10_16 片段拟合常参 2RC（固定 R0）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="10_16 Initial capacity xlsx（Channel/Sheet1 格式）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 曲线的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_from_10_16seg.json"),
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

    # 权重：强调放电后休止段（恢复）
    ap.add_argument("--w-rest", type=float, default=3.0, help="休止段权重（默认 3）")
    ap.add_argument("--w-rest-early", type=float, default=6.0, help="休止段前 early-window-s 权重（默认 6）")
    ap.add_argument("--early-window-s", type=float, default=120.0, help="休止段 early 时间窗（秒，默认 120）")
    ap.add_argument("--stride", type=int, default=5, help="下采样步长（默认 5，越大越快但信息更少）")
    ap.add_argument(
        "--capacity-ah",
        type=float,
        default=-1.0,
        help="手动指定容量（Ah）；<0 表示沿用 seed 配置容量（更符合“电压提前触发 cutoff”的机理）",
    )
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    seed_phone = Path(args.seed_phone).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    batt_seed_1rc = BatteryParams1ECM.from_json(seed_phone)
    ocv = batt_seed_1rc.ocv

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)

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
            print("[ERROR] 未能从 10_16 估计到有效 R0（事件太少或阈值不合适）。", file=sys.stderr)
            return 2
        r0_ohm = float(s["median_ohm"])
        print(f"[R0] 估计：n={s['n']}  median={s['median_ohm']:.4f}Ω  p10={s['p10_ohm']:.4f}Ω  p90={s['p90_ohm']:.4f}Ω")
    else:
        print(f"[R0] 手动指定：R0={r0_ohm:.4f}Ω")

    # 2) 截取 step 区间
    steps = np.asarray(ts.step, dtype=int)
    m_seg = (steps >= int(args.step_start)) & (steps <= int(args.step_end))
    idx = np.where(m_seg)[0]
    if len(idx) < 500:
        print("[ERROR] 选定 step 区间内样本太少，请检查 step-start/step-end。", file=sys.stderr)
        return 2
    a, b = int(idx[0]), int(idx[-1]) + 1

    t_s = np.asarray(ts.t_s, dtype=float)[a:b]
    t0 = float(t_s[0])
    t_s = t_s - t0
    dt_s = _infer_dt_s(t_s)
    i_A = np.asarray(ts.i_A, dtype=float)[a:b]
    v_meas = np.asarray(ts.v_V, dtype=float)[a:b]
    step_seg = steps[a:b]

    print(f"[片段] idx=[{a},{b})  n={len(t_s)}  duration≈{float(t_s[-1])/3600.0:.2f} h  steps={sorted(set(int(x) for x in step_seg.tolist()))}")

    # 3) SOC0：用片段起始的休止段电压近似 OCV 反推
    rest_i = float(args.rest_i)
    m0 = (np.abs(i_A) <= rest_i) & (t_s <= float(args.early_window_s))
    v0 = float(np.median(v_meas[m0])) if int(np.sum(m0)) >= 30 else float(v_meas[0])
    soc0 = float(ocv.soc_from_ocv_v(v0))
    soc0 = min(1.0, max(0.0, soc0))
    print(f"[SOC0] 由起始休止段电压反推：V0≈{v0:.4f}V -> SOC0≈{soc0:.3f}")

    # 4) 容量（重要）：用于 SOC->OCV 映射的“电荷尺度”，默认沿用低电流 OCV 校准得到的容量。
    # 说明：高电流下看似“容量变小”更多来自电压压降（R0/RC）提前触发 V_cut，
    # 因此不建议把 1A 放电直到 2.5V 的库仑积分直接当作“容量”（那会把 SOC 标尺压缩，导致 OCV 错位）。
    cap_ah = float(args.capacity_ah)
    if cap_ah <= 0 or not np.isfinite(cap_ah):
        cap_ah = float(batt_seed_1rc.capacity_Ah)
        cap_src = "seed"
    else:
        cap_src = "manual"
    print(f"[容量] capacity≈{cap_ah:.4f}Ah（source={cap_src}）")

    # 5) 拟合权重/掩码：片段全纳入，但提高休止段（尤其 early）权重
    mask = np.ones_like(v_meas, dtype=bool)
    w = np.ones_like(v_meas, dtype=float)
    m_rest = np.abs(i_A) <= rest_i
    w[m_rest] = float(args.w_rest)
    # 找到放电结束后的休止段 early：用 step==step_end 且在该 step 的起始窗口内
    rest_steps = sorted(set(int(s) for s in step_seg[m_rest].tolist()))
    if rest_steps:
        # 取最后一个 rest step 作为“放电后恢复”（默认 step_end 就是）
        s_last = int(rest_steps[-1])
        m_last = (step_seg == s_last) & m_rest
        if np.any(m_last):
            t_last0 = float(np.min(t_s[m_last]))
            m_early = m_last & (t_s <= t_last0 + float(args.early_window_s))
            w[m_early] = float(args.w_rest_early)

    # 6) 下采样以加速拟合（注意：必须用下采样后的时间戳重算 dt）
    stride = max(1, int(args.stride))
    idx_ds = np.arange(0, len(t_s), stride, dtype=int)
    t_s_ds = t_s[idx_ds]
    dt_s_ds = _infer_dt_s(t_s_ds)
    i_A_ds = i_A[idx_ds]
    v_meas_ds = v_meas[idx_ds]
    mask_ds = mask[idx_ds]
    w_ds = w[idx_ds]

    print(f"[下采样] stride={stride}  n: {len(t_s)} -> {len(t_s_ds)}")

    fit = fit_2rc_const_given_r0(
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
    )

    tau1 = float(fit.r1_ohm) * float(fit.c1_F)
    tau2 = float(fit.r2_ohm) * float(fit.c2_F)
    print("[拟合] 常参 2RC（固定 R0）完成：")
    print(f"- R0={fit.r0_ohm:.4f}Ω（fixed）")
    print(f"- R1={fit.r1_ohm:.6f}Ω  C1={fit.c1_F:.1f}F  tau1≈{tau1:.1f}s")
    print(f"- R2={fit.r2_ohm:.6f}Ω  C2={fit.c2_F:.1f}F  tau2≈{tau2:.1f}s")
    print(f"- RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")

    # 7) 写出配置（在 seed 配置基础上覆盖/新增 2RC 参数）
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(float(cap_ah) * 1000.0))

    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["R1_ohm"] = float(fit.r1_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    ecm["R2_ohm"] = float(fit.r2_ohm)
    ecm["C2_F"] = float(fit.c2_F)
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration_2rc_r0fixed_from_10_16seg"] = {
        "source_xlsx": str(xlsx),
        "segment_steps_inclusive": [int(args.step_start), int(args.step_end)],
        "method": "R0 from rest-load transitions + least-squares (2RC const R1,C1,R2,C2) on discharge+rest segment",
        "r0_ohm_used": float(fit.r0_ohm),
        "capacity_Ah_used": float(cap_ah),
        "weights": {
            "w_rest": float(args.w_rest),
            "w_rest_early": float(args.w_rest_early),
            "early_window_s": float(args.early_window_s),
        },
        "fit_result": {
            "r1_ohm": float(fit.r1_ohm),
            "c1_F": float(fit.c1_F),
            "r2_ohm": float(fit.r2_ohm),
            "c2_F": float(fit.c2_F),
            "tau1_s": float(tau1),
            "tau2_s": float(tau2),
            "rmse_mV_weighted": float(fit.rmse_V * 1000.0),
            "mae_mV_weighted": float(fit.mae_V * 1000.0),
        },
        "notes_zh": "该校准仅用于产生“慢时间常数”先验，最终好坏以 Incremental OCV 独立验证集为准。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
