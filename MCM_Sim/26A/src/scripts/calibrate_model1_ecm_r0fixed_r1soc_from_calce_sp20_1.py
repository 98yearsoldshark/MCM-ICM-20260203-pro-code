#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：用“含电流阶跃/脉冲”的数据估计 R0，然后固定 R0，仅用低电流 OCV 数据拟合 R1(SOC)+C1。

为什么要做这一步（对应“优化变差”问题）：
- 低电流数据可用于拟合 OCV 与 RC 松弛，但对 R0 的辨识能力很弱；
- 若让优化器在低电流数据上自由拟合 R0，R0 往往会被推到极小（触底），
  这会导致在高电流脉冲数据上严重低估压降，验证集 RMSE 反而变差；
- 因此采用“分阶段辨识”：
  1) 用含阶跃/脉冲数据估计一个合理 R0 先验；
  2) 固定 R0，用低电流数据拟合 R1(SOC) 与 C1（解释恢复效应）。
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
    extract_time_series,
    fit_c1_and_r1_curve_given_r0,
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
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _compute_capacity_from_discharge(ts, *, i_min_A: float = 0.02) -> float:
    m = ts.i_A > float(i_min_A)
    if int(np.sum(m)) < 100:
        return float("nan")
    cap_ah = float(np.sum(ts.i_A[m] * ts.dt_s[m] / 3600.0))
    return cap_ah


def main() -> int:
    ap = argparse.ArgumentParser(description="CALCE SP20-1：R0 先验 + R1(SOC) 固定R0拟合")
    ap.add_argument("--low-current-xlsx", default=str(_default_low_current_xlsx()), help="低电流 OCV xlsx（Pgm step 格式）")
    ap.add_argument("--pulse-xlsx", default=str(_default_pulse_xlsx()), help="含阶跃/脉冲的 xlsx（Channel/Sheet1 格式）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 初值的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_r1soc.json"),
        help="输出配置 JSON 路径",
    )

    # R0 估计参数
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--load-i", type=float, default=0.2, help="判定负载段的电流阈值（A）")
    ap.add_argument("--n-rest", type=int, default=20, help="边界前 rest 窗口点数")
    ap.add_argument("--n-load", type=int, default=20, help="边界后 load 窗口点数")
    ap.add_argument("--min-gap", type=int, default=200, help="事件最小间隔（点）")
    ap.add_argument("--r0", type=float, default=-1.0, help="手动指定 R0（欧姆）；<0 表示从 pulse 数据估计")

    # 低电流拟合参数（与旧脚本一致）
    ap.add_argument("--steps", default="2,3,4", help="低电流数据使用哪些 Pgm step（逗号分隔）。默认 2,3,4")
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在 step（默认 3）")
    ap.add_argument("--soc0", type=float, default=1.0, help="低电流数据起始 SOC（默认 1.0）")
    ap.add_argument("--i-min-A", type=float, default=0.02, help="用于识别放电段/容量计算的最小电流阈值（A）")
    ap.add_argument("--w-step4", type=float, default=2.0, help="拟合时 step=4 的残差权重（默认 2.0）")
    ap.add_argument("--w-step4-early", type=float, default=4.0, help="拟合时 step=4 前 early-window-s 的权重（默认 4.0）")
    ap.add_argument("--early-window-s", type=float, default=600.0, help="定义 step=4“早期”的时间窗（秒，默认 600）")
    args = ap.parse_args()

    seed_phone = Path(args.seed_phone).expanduser().resolve()
    batt_seed = BatteryParams1ECM.from_json(seed_phone)

    # 1) R0 估计（来自 pulse 数据）
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

    # 2) 低电流数据：固定 R0 拟合 R1(SOC)+C1
    low_xlsx = Path(args.low_current_xlsx).expanduser().resolve()
    df = load_calce_df(low_xlsx)
    steps = tuple(int(s.strip()) for s in str(args.steps).split(",") if s.strip())
    ts = extract_time_series(df, steps=steps)

    cap_ah = _compute_capacity_from_discharge(ts, i_min_A=float(args.i_min_A))
    if not np.isfinite(cap_ah) or cap_ah <= 0:
        cap_ah = float(batt_seed.capacity_Ah)
    print(f"[容量] capacity≈{cap_ah:.4f}Ah（用于 SOC 积分）")

    mask_fit = (ts.step.astype(int) == int(args.discharge_step)) | (ts.step.astype(int) == 4)

    # 权重：提高 step4（尤其 early）的权重以解释恢复效应
    weights = np.ones_like(ts.v_V, dtype=float)
    m4 = ts.step.astype(int) == 4
    weights[m4] = float(args.w_step4)
    idx4 = np.where(m4)[0]
    if len(idx4) > 0:
        t0 = float(ts.t_s[idx4[0]])
        early = m4 & (ts.t_s < t0 + float(args.early_window_s))
        weights[early] = float(args.w_step4_early)

    fit = fit_c1_and_r1_curve_given_r0(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=batt_seed.ocv,
        r0_ohm=float(r0_ohm),
        dt_s=ts.dt_s,
        i_A=ts.i_A,
        v_meas_V=ts.v_V,
        mask=mask_fit,
        weights=weights,
        soc_knots_desc=(1.0, 0.2, 0.1, 0.05, 0.0),
    )

    print("[拟合] 固定 R0 后的结果：")
    print(f"- R0={fit.r0_ohm:.4f}Ω（fixed）  C1={fit.c1_F:.1f}F  RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")
    print("- R1(SOC) 结点：")
    for s, v in fit.r1_curve.points:
        print(f"  - SOC={s:.2f}: R1={v:.4f}Ω")

    # 3) 写出配置（在 seed 配置基础上覆盖 ECM 参数）
    out_path = Path(args.out).expanduser().resolve()
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(float(cap_ah) * 1000.0))
    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    # 参考值：SOC=1.0 处
    ecm["R1_ohm"] = float(fit.r1_curve.value(1.0))
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration_r0fixed"] = {
        "r0_source_xlsx": str(pulse_xlsx),
        "low_current_xlsx": str(low_xlsx),
        "method": "R0 from rest-load transitions + least-squares (R1(SOC), C1) with fixed R0",
        "r0_ohm_used": float(fit.r0_ohm),
        "notes_zh": "用于修复“低电流拟合导致 R0 触底，从而在脉冲验证集上变差”的问题。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

