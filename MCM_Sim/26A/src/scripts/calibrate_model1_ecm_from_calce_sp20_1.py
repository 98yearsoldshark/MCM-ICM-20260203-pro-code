#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：只用一份 CALCE SP20-1 低电流 OCV 测试数据，校准 Model-1 的电池 ECM 参数（R0/R1/C1/OCV）。

工作流（可循环执行）：
1) 从数据提取 (t, I, V)；
2) 先固定 OCV，拟合 R0/R1/tau；
3) 用拟合后的 v1 与 IR 修正反推 OCV，再拟合分段线性 OCV；
4) 重复 2~3 次直到误差稳定；
5) 输出一个“校准版电池配置 JSON”，可直接给 Model-1/2/3 使用。

约束：
- 本脚本严格只读取一个 xlsx 数据文件，不会访问其它数据集。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams1ECM, PiecewiseLinearOCV
from mcm26a.calibration import CalceTimeSeries, extract_time_series, iterative_calibrate_ocv_and_resistance, load_calce_df
from mcm26a.calibration.ecm_current import simulate_ecm_current_control


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


def _default_seed_cfg() -> Path:
    return SRC_DIR / "configs" / "battery_calce_sp20_1.json"


def _compute_capacity_from_discharge(ts: CalceTimeSeries, *, discharge_step: int = 3, i_min_A: float = 0.02) -> float:
    m = (ts.step.astype(int) == int(discharge_step)) & (ts.i_A > float(i_min_A))
    if m.sum() < 100:
        raise ValueError("放电段有效点太少，无法计算容量")
    cap_ah = float(np.sum(ts.i_A[m] * ts.dt_s[m] / 3600.0))
    if cap_ah <= 0:
        raise ValueError("容量计算失败（结果非正）")
    return cap_ah


def _find_step_start(ts: CalceTimeSeries, *, step_id: int) -> int:
    idx = np.where(ts.step.astype(int) == int(step_id))[0]
    if len(idx) == 0:
        raise ValueError(f"找不到 step={step_id}")
    return int(idx[0])


def _make_fit_window_mask(ts: CalceTimeSeries, *, center_idx: int, pre_s: float, post_s: float) -> np.ndarray:
    t0 = float(ts.t_s[center_idx])
    lo = t0 - float(pre_s)
    hi = t0 + float(post_s)
    return (ts.t_s >= lo) & (ts.t_s <= hi)


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

    # 按 step 粗分
    for sid in sorted(set(int(x) for x in ts.step.tolist())):
        m = ts.step.astype(int) == sid
        rr = r[m]
        print(f"  - step={sid}: n={m.sum():6d}  RMSE={_rmse(rr)*1000:7.1f} mV  MAE={_mae(rr)*1000:7.1f} mV")

    # 按电压区间（与手机 cutoff=3.3V 对齐）
    bands = [(4.2, 3.8), (3.8, 3.3), (3.3, 0.0)]
    for hi, lo in bands:
        m = (ts.v_V <= hi) & (ts.v_V > lo)
        rr = r[m]
        if m.sum() == 0:
            continue
        print(f"  - V∈({lo:.1f},{hi:.1f}]V: n={m.sum():6d}  RMSE={_rmse(rr)*1000:7.1f} mV")


def main() -> int:
    ap = argparse.ArgumentParser(description="只用 CALCE SP20-1 低电流数据校准 ECM（R0/R1/C1/OCV）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（只用这一份数据）")
    ap.add_argument(
        "--seed-phone",
        default=str(_default_seed_cfg()),
        help="初始电池配置（含 OCV 初值）。默认使用上一步生成的 battery_calce_sp20_1.json",
    )
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit.json"),
        help="输出校准后的电池配置 JSON 路径",
    )
    ap.add_argument("--steps", default="2,3,4", help="使用哪些 Pgm step（逗号分隔）。默认 2,3,4")
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在 step（默认 3）")
    ap.add_argument("--soc0", type=float, default=1.0, help="校准仿真起始 SOC（默认 1.0）")
    ap.add_argument("--fit-pre", type=float, default=600.0, help="拟合窗口：放电开始前（秒）")
    ap.add_argument("--fit-post", type=float, default=3600.0, help="拟合窗口：放电开始后（秒）")
    ap.add_argument("--fit-end-pre", type=float, default=600.0, help="拟合窗口：放电结束/休止开始前（秒）")
    ap.add_argument("--fit-end-post", type=float, default=7200.0, help="拟合窗口：放电结束/休止开始后（秒）")
    ap.add_argument("--max-iter", type=int, default=3, help="OCV/电阻迭代次数（建议 2~5）")
    ap.add_argument("--n-ocv-points", type=int, default=21, help="OCV 分段线性点数")
    ap.add_argument("--i-min-A", type=float, default=0.02, help="用于识别放电段/容量计算的最小电流阈值（A）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    # 只读取这一份数据
    df = load_calce_df(xlsx)
    steps = tuple(int(s.strip()) for s in str(args.steps).split(",") if s.strip())
    ts = extract_time_series(df, steps=steps)

    # 初始电池配置（提供 OCV 初值与 cutoff 等字段）
    seed_phone = Path(args.seed_phone).expanduser().resolve()
    batt_seed = BatteryParams1ECM.from_json(seed_phone)

    cap_ah = _compute_capacity_from_discharge(ts, discharge_step=int(args.discharge_step), i_min_A=float(args.i_min_A))
    print("[数据] xlsx:", xlsx)
    print(f"[数据] steps={steps}  samples={len(ts.t_s)}  capacity≈{cap_ah:.4f}Ah（由放电段积分得到）")
    print("")

    # 初始 OCV：来自 seed 配置
    ocv0 = batt_seed.ocv

    # 构造拟合窗口（并集）：
    # - 放电开始附近：识别瞬态压降（与手机典型工作区间更接近）
    # - 放电结束后的长休止段：识别极化松弛时间常数 tau（否则在低电流下 tau 很难辨识）
    idx_discharge0 = _find_step_start(ts, step_id=int(args.discharge_step))
    mask_fit_start = _make_fit_window_mask(
        ts,
        center_idx=idx_discharge0,
        pre_s=float(args.fit_pre),
        post_s=float(args.fit_post),
    )
    # 同时加入“放电结束后的长休止段”，用于识别 tau（否则 tau 在低电流下几乎不可辨识）
    idx_rest0 = _find_step_start(ts, step_id=4)
    mask_fit_end = _make_fit_window_mask(
        ts,
        center_idx=idx_rest0,
        pre_s=float(args.fit_end_pre),
        post_s=float(args.fit_end_post),
    )
    mask_fit = mask_fit_start | mask_fit_end
    if mask_fit.sum() < 200:
        raise SystemExit("[ERROR] 拟合窗口太短或数据缺失，导致有效点过少。")

    # 先评估 seed 参数的误差（用 seed 的 R0/R1/C1，tau=R1*C1）
    tau0 = float(batt_seed.r1_ohm) * float(batt_seed.c1_F)
    soc_seed, v1_seed, v_pred_seed = simulate_ecm_current_control(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=ocv0,
        r0_ohm=float(batt_seed.r0_ohm),
        r1_ohm=float(batt_seed.r1_ohm),
        tau_s=float(tau0),
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    _report_error(ts, v_pred_seed, title="seed 参数（未校准）")
    print(
        "[拟合] 使用窗口（并集）:\n"
        f"- 放电开始窗口: t∈[{ts.t_s[idx_discharge0]-float(args.fit_pre):.0f}, {ts.t_s[idx_discharge0]+float(args.fit_post):.0f}]s  n={mask_fit_start.sum()}\n"
        f"- 放电结束窗口: t∈[{ts.t_s[idx_rest0]-float(args.fit_end_pre):.0f}, {ts.t_s[idx_rest0]+float(args.fit_end_post):.0f}]s  n={mask_fit_end.sum()}\n"
        f"- 合并后总计: n={mask_fit.sum()}"
    )
    print("")

    def _progress(it: int, fit) -> None:
        print(
            f"[迭代 {it}] R0={fit.r0_ohm:.4f}Ω  R1={fit.r1_ohm:.4f}Ω  tau={fit.tau_s:.2f}s  C1={fit.c1_F:.1f}F  RMSE={fit.rmse_V*1000:.1f}mV  (n={fit.n})"
        )

    ocv_fit, fit = iterative_calibrate_ocv_and_resistance(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv0=ocv0,
        dt_s=ts.dt_s,
        i_A=ts.i_A,
        v_meas_V=ts.v_V,
        mask_fit=mask_fit,
        n_ocv_points=int(args.n_ocv_points),
        max_iter=int(args.max_iter),
        progress=_progress,
    )
    print("")

    # 用最终参数评估全段误差
    soc_hist, v1_hist, v_pred = simulate_ecm_current_control(
        soc0=float(args.soc0),
        v1_0_V=0.0,
        capacity_Ah=cap_ah,
        ocv=ocv_fit,
        r0_ohm=float(fit.r0_ohm),
        r1_ohm=float(fit.r1_ohm),
        tau_s=float(fit.tau_s),
        dt_s=ts.dt_s,
        i_A=ts.i_A,
    )
    _report_error(ts, v_pred, title="校准后（全段复算）")
    print("")

    # 误差原因（基于本数据能观察到的）
    r = v_pred - ts.v_V
    m_low = ts.v_V < 3.3
    if m_low.sum() > 100:
        print("[诊断] 低电压区（<3.3V）误差通常更大：这往往意味着 R0/R1 随 SOC 增大，而当前模型用常数电阻。")
        print(f"- <3.3V: RMSE={_rmse(r[m_low])*1000:.1f} mV  vs  >=3.3V: RMSE={_rmse(r[~m_low])*1000:.1f} mV")
    print("")

    # 写出配置：保持 schema 与其它 phone_default_* 一致，便于直接替换 --phone
    out_path = Path(args.out).expanduser().resolve()
    out_cfg = json.loads(seed_phone.read_text(encoding="utf-8"))
    batt = out_cfg.get("battery", out_cfg)
    batt["capacity_mAh"] = int(round(cap_ah * 1000.0))
    batt["soc_min"] = float(getattr(batt_seed, "soc_min", 0.02))
    ecm = batt.get("ecm", {})
    ecm["R0_ohm"] = float(fit.r0_ohm)
    ecm["R1_ohm"] = float(fit.r1_ohm)
    ecm["C1_F"] = float(fit.c1_F)
    ecm_curve = ecm.get("ocv_curve", {})
    ecm_curve["type"] = "piecewise_linear"
    ecm_curve["points"] = [[float(s), float(v)] for s, v in ocv_fit.points]
    ecm["ocv_curve"] = ecm_curve
    batt["ecm"] = ecm
    out_cfg["battery"] = batt

    meta = out_cfg.get("meta", {})
    meta["calibration"] = {
        "dataset": str(xlsx),
        "steps_used": list(steps),
        "method": "iterative least-squares (current-controlled ECM) + OCV re-fit",
        "fit_window": {"pre_s": float(args.fit_pre), "post_s": float(args.fit_post)},
        "notes_zh": "只使用这一份 CALCE xlsx 完成；电阻为常数，低 SOC 区间可能仍有系统误差（需扩展为 R(soc) 或引入更多数据）。",
    }
    out_cfg["meta"] = meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[输出] 校准配置已保存：", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
