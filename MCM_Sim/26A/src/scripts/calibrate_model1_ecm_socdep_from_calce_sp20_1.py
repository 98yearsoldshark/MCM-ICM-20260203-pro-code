#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：只用一份 CALCE SP20-1 低电流 OCV 测试数据，校准“R1 随 SOC 变化”的 ECM（Model-1 扩展）。

动机（对应本项目的“循环校准闭环”）：
- 常参 1RC 在高电压区可以拟合得很好，但在低 SOC 的长休止松弛段误差很大；
- 这通常意味着 R1（极化阻抗）随 SOC 强烈增加；
- 因此我们在不引入过多自由度的前提下，先把 R1 改为 R1(SOC) 分段线性曲线。

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
from mcm26a.calibration import CalceTimeSeries, extract_time_series, fit_r0_c1_and_r1_curve, load_calce_df
from mcm26a.calibration.ecm_current_socdep import simulate_ecm_current_control_r1_soc
from mcm26a.utils import PiecewiseLinearCurve


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
    # 该文件来自“OCV-only 校准”阶段：主要提供 capacity 与 OCV 初值
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

    # 休止段早/晚（用来观察松弛是否被解释）
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

    # 与 cutoff=3.3V 对齐的电压区间
    bands = [(4.2, 3.8), (3.8, 3.3), (3.3, 0.0)]
    for hi, lo in bands:
        m = (ts.v_V <= hi) & (ts.v_V > lo)
        rr = r[m]
        if m.sum() == 0:
            continue
        print(f"  - V∈({lo:.1f},{hi:.1f}]V: n={m.sum():6d}  RMSE={_rmse(rr)*1000:7.1f} mV")


def main() -> int:
    ap = argparse.ArgumentParser(description="只用 CALCE SP20-1：校准 R1(SOC) 的 ECM（R0 常数 + C1 常数）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（只用这一份数据）")
    ap.add_argument("--seed-phone", default=str(_seed_cfg()), help="提供 OCV 初值的电池配置（默认 battery_calce_sp20_1.json）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r1soc.json"),
        help="输出校准后的电池配置 JSON 路径",
    )
    ap.add_argument("--steps", default="2,3,4", help="使用哪些 Pgm step（逗号分隔）。默认 2,3,4")
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在 step（默认 3）")
    ap.add_argument("--soc0", type=float, default=1.0, help="起始 SOC（默认 1.0）")
    ap.add_argument("--i-min-A", type=float, default=0.02, help="用于识别放电段/容量计算的最小电流阈值（A）")
    ap.add_argument("--w-step4", type=float, default=2.0, help="拟合时 step=4 的残差权重（默认 2.0）")
    ap.add_argument("--w-step4-early", type=float, default=4.0, help="拟合时 step=4 前 early-window-s 的权重（默认 4.0）")
    ap.add_argument("--early-window-s", type=float, default=600.0, help="定义 step=4“早期”的时间窗（秒，默认 600）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    # 只读取这一份数据
    df = load_calce_df(xlsx)
    steps = tuple(int(s.strip()) for s in str(args.steps).split(",") if s.strip())
    ts = extract_time_series(df, steps=steps)

    seed_phone = Path(args.seed_phone).expanduser().resolve()
    batt_seed = BatteryParams1ECM.from_json(seed_phone)

    cap_ah = _compute_capacity_from_discharge(ts, discharge_step=int(args.discharge_step), i_min_A=float(args.i_min_A))
    print("[数据] xlsx:", xlsx)
    print(f"[数据] steps={steps}  samples={len(ts.t_s)}  capacity≈{cap_ah:.4f}Ah（由放电段积分得到）")
    print("")

    # 仅拟合 step=3/4（step=2 基本是满电休止，可视为 OCV 锚点；但本脚本中 OCV 固定）
    mask_fit = (ts.step.astype(int) == int(args.discharge_step)) | (ts.step.astype(int) == 4)
    print(f"[拟合] mask: step={args.discharge_step} 或 step=4，总点数 n={mask_fit.sum()}")
    print("")

    # 权重：为了让“放电末端 -> 休止初期”的松弛被优先解释，适当提高 step4（尤其是早期）的权重。
    weights = np.ones_like(ts.v_V, dtype=float)
    m4 = ts.step.astype(int) == 4
    weights[m4] = float(args.w_step4)
    idx4 = np.where(m4)[0]
    if len(idx4) > 0:
        t0 = float(ts.t_s[idx4[0]])
        early = m4 & (ts.t_s < t0 + float(args.early_window_s))
        weights[early] = float(args.w_step4_early)

    # seed 误差（先用 seed 的 R0/R1/C1；如果 seed 没有 R1_curve，则退化为常数曲线）
    r1_seed_curve = (
        batt_seed.r1_curve
        if batt_seed.r1_curve is not None
        else PiecewiseLinearCurve(points=((0.0, float(batt_seed.r1_ohm)), (1.0, float(batt_seed.r1_ohm))))
    )
    soc_seed, v1_seed, v_pred_seed = simulate_ecm_current_control_r1_soc(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=batt_seed.ocv,
        r0_ohm=float(batt_seed.r0_ohm),
        c1_F=float(batt_seed.c1_F),
        r1_curve=r1_seed_curve,
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    _report_error(ts, v_pred_seed, title="seed 参数（常数 R1）")
    print("")

    fit = fit_r0_c1_and_r1_curve(
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
    print(f"- R0={fit.r0_ohm:.4f}Ω  C1={fit.c1_F:.1f}F  RMSE={fit.rmse_V*1000:.1f}mV  MAE={fit.mae_V*1000:.1f}mV  (n={fit.n})")
    print("- R1(SOC) 结点：")
    for s, v in fit.r1_curve.points:
        print(f"  - SOC={s:.2f}: R1={v:.4f}Ω")
    print("")

    # 用拟合结果全段复算误差
    soc_hist, v1_hist, v_pred = simulate_ecm_current_control_r1_soc(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=batt_seed.ocv,
        r0_ohm=float(fit.r0_ohm),
        c1_F=float(fit.c1_F),
        r1_curve=fit.r1_curve,
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    _report_error(ts, v_pred, title="校准后（全段复算，R1 随 SOC）")
    print("")

    # 写出配置（兼容原 schema：保留 R1_ohm 作为参考值，并新增 R1_curve）
    out_path = Path(args.out).expanduser().resolve()
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(cap_ah * 1000.0))
    batt["soc_min"] = float(getattr(batt_seed, "soc_min", 0.02))
    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    # 参考值：SOC=1.0 处
    r1_soc1 = float(fit.r1_curve.value(1.0))
    ecm["R1_ohm"] = r1_soc1
    ecm["R1_curve"] = {"type": "piecewise_linear", "points": [[float(s), float(v)] for s, v in fit.r1_curve.points]}
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration"] = {
        "dataset": str(xlsx),
        "steps_used": list(steps),
        "method": "least-squares (current-controlled ECM, R1(SOC) + constant R0,C1; OCV fixed)",
        "notes_zh": "只使用这一份 CALCE xlsx 完成；该版本主要用于修正低 SOC 长休止松弛误差结构。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 校准配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
