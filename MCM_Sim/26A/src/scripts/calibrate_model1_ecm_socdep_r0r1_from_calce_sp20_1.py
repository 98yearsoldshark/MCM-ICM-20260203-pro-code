#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：只用一份 CALCE SP20-1 数据，校准 R0(SOC)+R1(SOC)+C1 的 ECM（更接近真实末端行为）。

相比“仅 R1(SOC)”版本：
- 引入 R0(SOC) 让放电末端的瞬时压降（I*R0）也能随 SOC 增大；
- 这样可同时兼顾：
  - 放电段（step=3）电压轨迹；
  - 放电结束后的长休止松弛段（step=4）；
  - 并减少把所有误差都塞进 v1（极化电压）导致的结构性偏差。

约束：
- 本脚本严格只读取一个 xlsx 数据文件，不会访问其它数据集。
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
    CalceTimeSeries,
    extract_time_series,
    fit_r0_curve_c1_and_r1_curve,
    load_calce_df,
)
from mcm26a.calibration.ecm_current_socdep import simulate_ecm_current_control_r0_r1_soc


def _default_xlsx() -> Path:
    return (
        SRC_DIR.parent
        / "data"
        / "calce-umd"
        / "extracted"
        / "battery-data"
        / "SP"
        / "11_5_2015_low current OCV test_SP20-1.xlsx"
    )


def _seed_cfg() -> Path:
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _compute_capacity_from_discharge(ts: CalceTimeSeries, *, discharge_step: int = 3, i_min_A: float = 0.02) -> float:
    m = (ts.step.astype(int) == int(discharge_step)) & (ts.i_A > float(i_min_A))
    if m.sum() < 100:
        raise ValueError("放电段有效点太少，无法计算容量")
    cap_ah = float(np.sum(ts.i_A[m] * ts.dt_s[m] / 3600.0))
    if cap_ah <= 0:
        raise ValueError("容量计算失败（结果非正）")
    return cap_ah


def _rmse(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x * x))) if len(x) else float("nan")


def _mae(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.abs(x))) if len(x) else float("nan")


def _report_error(ts: CalceTimeSeries, v_pred: np.ndarray, *, title: str) -> None:
    r = v_pred - ts.v_V
    print(f"[误差] {title}")
    print(f"- 全部点: n={len(r)}  RMSE={_rmse(r)*1000:.1f} mV  MAE={_mae(r)*1000:.1f} mV")

    for sid in sorted(set(int(x) for x in ts.step.tolist())):
        m = ts.step.astype(int) == sid
        rr = r[m]
        print(f"  - step={sid}: n={m.sum():6d}  RMSE={_rmse(rr)*1000:7.1f} mV  MAE={_mae(rr)*1000:7.1f} mV")

    m4 = ts.step.astype(int) == 4
    idx = np.where(m4)[0]
    if len(idx) > 0:
        t0 = float(ts.t_s[idx[0]])
        t1 = float(ts.t_s[idx[-1]])
        early = m4 & (ts.t_s < t0 + 600.0)
        late = m4 & (ts.t_s > t1 - 600.0)
        for name, m in [("step4 早600s", early), ("step4 晚600s", late)]:
            rr = r[m]
            print(f"  - {name}: n={m.sum():6d}  RMSE={_rmse(rr)*1000:7.1f} mV  MAE={_mae(rr)*1000:7.1f} mV")


def main() -> int:
    ap = argparse.ArgumentParser(description="只用 CALCE SP20-1：校准 R0(SOC)+R1(SOC)+C1 的 ECM")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（只用这一份数据）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 初值的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0r1soc.json"),
        help="输出校准后的电池配置 JSON 路径",
    )
    ap.add_argument("--steps", default="2,3,4", help="使用哪些 Pgm step（逗号分隔）。默认 2,3,4")
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在 step（默认 3）")
    ap.add_argument("--soc0", type=float, default=1.0, help="起始 SOC（默认 1.0）")
    ap.add_argument("--i-min-A", type=float, default=0.02, help="用于识别放电段/容量计算的最小电流阈值（A）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    df = load_calce_df(xlsx)
    steps = tuple(int(s.strip()) for s in str(args.steps).split(",") if s.strip())
    ts = extract_time_series(df, steps=steps)

    seed_phone = Path(args.seed_phone).expanduser().resolve()
    batt_seed = BatteryParams1ECM.from_json(seed_phone)

    cap_ah = _compute_capacity_from_discharge(ts, discharge_step=int(args.discharge_step), i_min_A=float(args.i_min_A))
    print("[数据] xlsx:", xlsx)
    print(f"[数据] steps={steps}  samples={len(ts.t_s)}  capacity≈{cap_ah:.4f}Ah（由放电段积分得到）")
    print("")

    mask_fit = (ts.step.astype(int) == int(args.discharge_step)) | (ts.step.astype(int) == 4)
    print(f"[拟合] mask: step={args.discharge_step} 或 step=4，总点数 n={mask_fit.sum()}")
    print("")

    # 权重：比纯 R1(SOC) 更温和（R0(SOC) 已能解释一部分末端现象）
    weights = np.ones_like(ts.v_V, dtype=float)
    m4 = ts.step.astype(int) == 4
    weights[m4] = 2.0
    idx4 = np.where(m4)[0]
    if len(idx4) > 0:
        t0 = float(ts.t_s[idx4[0]])
        early = m4 & (ts.t_s < t0 + 600.0)
        weights[early] = 4.0

    fit = fit_r0_curve_c1_and_r1_curve(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=batt_seed.ocv,
        dt_s=ts.dt_s,
        i_A=ts.i_A,
        v_meas_V=ts.v_V,
        mask=mask_fit,
        weights=weights,
        soc_knots_desc=(1.0, 0.2, 0.1, 0.05, 0.0),
    )

    print("[结果] 拟合完成：")
    print(f"- C1={fit.c1_F:.1f}F  RMSE(w)={fit.rmse_V*1000:.1f}mV  MAE(w)={fit.mae_V*1000:.1f}mV  (n={fit.n})")
    print("- R0(SOC) 结点：")
    for s, v in fit.r0_curve.points:
        print(f"  - SOC={s:.2f}: R0={v:.4f}Ω")
    print("- R1(SOC) 结点：")
    for s, v in fit.r1_curve.points:
        print(f"  - SOC={s:.2f}: R1={v:.4f}Ω")
    print("")

    # 全段复算（不加权）
    soc_hist, v1_hist, v_pred = simulate_ecm_current_control_r0_r1_soc(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=batt_seed.ocv,
        r0_curve=fit.r0_curve,
        c1_F=float(fit.c1_F),
        r1_curve=fit.r1_curve,
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    _report_error(ts, v_pred, title="校准后（全段复算，R0/R1 随 SOC）")
    print("")

    out_path = Path(args.out).expanduser().resolve()
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(cap_ah * 1000.0))
    batt["soc_min"] = float(getattr(batt_seed, "soc_min", 0.02))
    ecm = batt.get("ecm", {})
    ecm["C1_F"] = float(fit.c1_F)
    # 参考值：SOC=1.0 处
    ecm["R0_ohm"] = float(fit.r0_curve.value(1.0))
    ecm["R1_ohm"] = float(fit.r1_curve.value(1.0))
    ecm["R0_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r0_curve.points]}
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration"] = {
        "dataset": str(xlsx),
        "steps_used": list(steps),
        "method": "least-squares (current-controlled ECM, R0(SOC)+R1(SOC)+C1; OCV fixed)",
        "notes_zh": "只使用这一份 CALCE xlsx 完成；R0/R1 采用分段线性并保证 SOC 越低电阻不减。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 校准配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

