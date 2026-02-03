#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出论文阶段 Q1材料的“图片对应数据版本”（CSV）。

动机：
- AI/程序对图片理解不如对结构化数据读取稳定；
- 因此为论文阶段每张主图补充一个 data.csv（放入各子目录的 other/ 下），
  便于后续核对、再绘图或做进一步分析。

目录约定（与论文目录规范对齐）：
- 每个 Q1 子目录根目录仅保留：figure.png + paper_fragment_zh.md + other/
- other/ 内收纳：about.md、context_full.md、paper_fragment_en.md、以及 data.csv 等。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A
PAPER_Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv_rows(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _write_csv_iter(path: Path, header: list[str], row_iter) -> None:
    """避免一次性在内存里堆积大表（用于 CALCE 轨迹）。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in row_iter:
            w.writerow(row)


def _export_ocv_curve(*, out_csv: Path) -> None:
    """对应 Q1-01：OCV(SOC) 曲线数据。"""

    from mcm26a.battery import BatteryParams1ECM

    phone_cfg = SRC_DIR / "configs" / "phone_default_v1_ecm.json"
    batt = BatteryParams1ECM.from_json(phone_cfg)
    soc = np.linspace(0.0, 1.0, 200)
    ocv = np.array([batt.ocv.ocv_v(float(s)) for s in soc], dtype=float)

    header = ["soc", "ocv_V", "v_cut_V"]
    rows = [[float(s), float(v), float(batt.v_cut_V)] for s, v in zip(soc.tolist(), ocv.tolist())]
    _write_csv_rows(out_csv, header, rows)


def _constant_curve(v: float):
    from mcm26a.utils import PiecewiseLinearCurve

    return PiecewiseLinearCurve(points=((0.0, float(v)), (1.0, float(v))))


def _simulate_calce_2rc(*, report_json: Path) -> dict[str, np.ndarray]:
    """复现实验验证脚本（2RC ECM + 可选 diff/hyst 状态）的核心仿真并返回数组。"""

    from mcm26a.battery import BatteryParams1ECM2RC
    from mcm26a.battery.model1_ecm2rc import simulate_ecm2rc_current_control
    from mcm26a.calibration import extract_channel_time_series, load_calce_channel_xlsx

    payload = _read_json(report_json)
    xlsx = Path(payload["dataset"]).expanduser().resolve()
    phone_cfg = Path(payload["phone_config"]).expanduser().resolve()
    soc0 = float(payload.get("soc0_used", 1.0))
    mode = payload.get("mode", {}) or {}
    diff_v_gate = str(mode.get("diff_v_gate", "measured")).strip().lower()

    batt = BatteryParams1ECM2RC.from_json(phone_cfg)
    ts = extract_channel_time_series(load_calce_channel_xlsx(xlsx))

    t = np.asarray(ts.t_s, dtype=float)
    t_rel = t - float(t[0])
    dt_s = np.asarray(ts.dt_s, dtype=float)
    i_A = np.asarray(ts.i_A, dtype=float)
    v_meas = np.asarray(ts.v_V, dtype=float)
    steps = np.asarray(ts.step, dtype=int)

    # R1/R2 曲线兜底：若配置没有给曲线，则用常数曲线。
    r1_curve = batt.r1_curve if batt.r1_curve is not None else _constant_curve(float(batt.r1_ohm))
    r2_curve = batt.r2_curve if batt.r2_curve is not None else _constant_curve(float(batt.r2_ohm))

    use_measured_gate = diff_v_gate in ("measured", "meas", "obs", "observed")

    soc, v1, v2, h, z, v_pred = simulate_ecm2rc_current_control(
        soc0=float(soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        h0=0.0,
        z0=0.0,
        capacity_Ah=float(batt.capacity_Ah),
        ocv=batt.ocv,
        r0_ohm=float(batt.r0_ohm),
        r0_curve=batt.r0_curve,
        c1_F=float(batt.c1_F),
        c2_F=float(batt.c2_F),
        r1_curve=r1_curve,
        r2_curve=r2_curve,
        rate_capacity_k_per_A=float(getattr(batt, "rate_capacity_k_per_A", 0.0)),
        # 迟滞（h）
        hyst_M_V=float(getattr(batt, "hyst_M_V", 0.0)),
        hyst_gamma=float(getattr(batt, "hyst_gamma", 0.0)),
        hyst_i_thresh_A=float(getattr(batt, "hyst_i_thresh_A", 0.05)),
        hyst_M_curve=getattr(batt, "hyst_M_curve", None),
        hyst_relax_tau_s=float(getattr(batt, "hyst_relax_tau_s", 0.0)),
        return_h=True,
        # diff_z（z）
        diff_M_V=float(getattr(batt, "diff_M_V", 0.0)),
        diff_gamma=float(getattr(batt, "diff_gamma", 0.0)),
        diff_i_thresh_A=float(getattr(batt, "diff_i_thresh_A", 0.5)),
        diff_soc_thresh=float(getattr(batt, "diff_soc_thresh", 0.1)),
        diff_v_thresh_V=float(getattr(batt, "diff_v_thresh_V", 0.0)),
        diff_gate_soc_sigma=float(getattr(batt, "diff_gate_soc_sigma", 0.0)),
        diff_gate_v_sigma_V=float(getattr(batt, "diff_gate_v_sigma_V", 0.0)),
        diff_gate_i_sigma_A=float(getattr(batt, "diff_gate_i_sigma_A", 0.0)),
        diff_relax_tau_s=float(getattr(batt, "diff_relax_tau_s", 0.0)),
        diff_relax_tau_init_s=float(getattr(batt, "diff_relax_tau_init_s", 0.0)),
        diff_relax_z_thresh=float(getattr(batt, "diff_relax_z_thresh", 0.0)),
        diff_relax_tau_mid_s=float(getattr(batt, "diff_relax_tau_mid_s", 0.0)),
        diff_relax_z_thresh_mid=float(getattr(batt, "diff_relax_z_thresh_mid", 0.0)),
        diff_relax_tau_fast_s=float(getattr(batt, "diff_relax_tau_fast_s", 0.0)),
        diff_relax_v_thresh_V=float(getattr(batt, "diff_relax_v_thresh_V", 0.0)),
        diff_M_curve=getattr(batt, "diff_M_curve", None),
        diff_R_ohm=float(getattr(batt, "diff_R_ohm", 0.0)),
        diff_R_curve=getattr(batt, "diff_R_curve", None),
        diff_v_gate_V=(v_meas if use_measured_gate else None),
        return_z=True,
        dt_s=dt_s,
        i_A=i_A,
    )

    return {
        "t_rel_s": np.asarray(t_rel, dtype=float),
        "step": np.asarray(steps, dtype=int),
        "i_A": np.asarray(i_A, dtype=float),
        "v_meas_V": np.asarray(v_meas, dtype=float),
        "soc": np.asarray(soc, dtype=float),
        "v1_V": np.asarray(v1, dtype=float),
        "v2_V": np.asarray(v2, dtype=float),
        "h": np.asarray(h, dtype=float),
        "z": np.asarray(z, dtype=float),
        "v_pred_V": np.asarray(v_pred, dtype=float),
        "v_cut_V": float(batt.v_cut_V),
    }


def _export_calce_voltage_trace(*, report_json: Path, out_csv: Path) -> None:
    """对应 Q1-02/Q1-03/Q1-08：预测 vs 观测电压轨迹。"""

    arr = _simulate_calce_2rc(report_json=report_json)
    t = arr["t_rel_s"]
    header = [
        "t_s",
        "t_h",
        "step_index",
        "i_A",
        "v_meas_V",
        "v_pred_V",
        "soc",
        "v1_V",
        "v2_V",
        "h",
        "z",
        "v_cut_V",
    ]

    def _rows():
        for k in range(int(len(t))):
            yield [
                float(arr["t_rel_s"][k]),
                float(arr["t_rel_s"][k] / 3600.0),
                int(arr["step"][k]),
                float(arr["i_A"][k]),
                float(arr["v_meas_V"][k]),
                float(arr["v_pred_V"][k]),
                float(arr["soc"][k]),
                float(arr["v1_V"][k]),
                float(arr["v2_V"][k]),
                float(arr["h"][k]),
                float(arr["z"][k]),
                float(arr["v_cut_V"]),
            ]

    _write_csv_iter(out_csv, header, _rows())


def _export_calce_polarization_states(*, report_json: Path, out_csv: Path) -> None:
    """对应 Q1-04：极化状态分解（v1/v2 及其和）。"""

    arr = _simulate_calce_2rc(report_json=report_json)
    t = arr["t_rel_s"]
    v_sum = arr["v1_V"] + arr["v2_V"]

    header = ["t_s", "t_h", "step_index", "i_A", "v1_V", "v2_V", "v1_plus_v2_V"]

    def _rows():
        for k in range(int(len(t))):
            yield [
                float(arr["t_rel_s"][k]),
                float(arr["t_rel_s"][k] / 3600.0),
                int(arr["step"][k]),
                float(arr["i_A"][k]),
                float(arr["v1_V"][k]),
                float(arr["v2_V"][k]),
                float(v_sum[k]),
            ]

    _write_csv_iter(out_csv, header, _rows())


def _export_trace_example(*, out_csv: Path) -> None:
    """对应 Q1-05：游戏场景轨迹示例（SOC/V_term/P/P_max）。"""

    from mcm26a.battery import BatteryParams1ECM
    from mcm26a.power import PowerParams0
    from mcm26a.scenarios import load_scenarios_json, materialize_scenario
    from mcm26a.sim import simulate_model1_ecm_trace

    raw = load_scenarios_json(SRC_DIR / "configs" / "scenarios_v0.json")
    power = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    batt1 = BatteryParams1ECM.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")

    sid = "S3_gaming" if "S3_gaming" in raw.get("scenarios", {}) else list(raw.get("scenarios", {}).keys())[0]
    sc = materialize_scenario(raw, sid)
    tr = simulate_model1_ecm_trace(sc, power_params=power, battery_params=batt1, soc0=1.0, dt_s=2.0)

    header = [
        "t_s",
        "t_h",
        "soc",
        "ocv_V",
        "v1_V",
        "i_A",
        "v_term_V",
        "p_W",
        "p_max_W",
        "discriminant",
        "scenario_id",
        "status",
    ]

    def _rows():
        for k in range(len(tr.t_s)):
            yield [
                float(tr.t_s[k]),
                float(tr.t_s[k] / 3600.0),
                float(tr.soc[k]),
                float(tr.ocv_V[k]),
                float(tr.v1_V[k]),
                float(tr.i_A[k]),
                float(tr.v_term_V[k]),
                float(tr.p_W[k]),
                float(tr.p_max_W[k]),
                float(tr.discriminant[k]),
                str(tr.scenario_id),
                str(tr.status),
            ]

    _write_csv_iter(out_csv, header, _rows())


def _export_tte_compare_model0_vs_model1(*, out_csv: Path) -> None:
    """对应 Q1-06：Model-0 vs Model-1 的 TTE 对比数据。"""

    from mcm26a.battery import BatteryParams0, BatteryParams1ECM
    from mcm26a.power import PowerParams0
    from mcm26a.scenarios import load_scenarios_json, materialize_scenario
    from mcm26a.sim import simulate_model0, simulate_model1_ecm

    raw = load_scenarios_json(SRC_DIR / "configs" / "scenarios_v0.json")
    power = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    batt1 = BatteryParams1ECM.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")
    batt0 = BatteryParams0.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")

    header = ["scenario_id", "title_zh", "tte_model0_h", "tte_model1_h", "delta_h", "status_model0", "status_model1"]
    rows: list[list[Any]] = []
    for sid, sc_raw in raw.get("scenarios", {}).items():
        sc = materialize_scenario(raw, sid)
        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=1.0)
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=1.0, dt_s=2.0)

        t0 = None if r0.tte_h is None else float(r0.tte_h)
        t1 = None if r1.tte_h is None else float(r1.tte_h)
        rows.append(
            [
                str(sid),
                str(sc_raw.get("title_zh", sid)),
                t0,
                t1,
                (None if (t0 is None or t1 is None) else float(t1 - t0)),
                str(r0.status),
                str(r1.status),
            ]
        )

    _write_csv_rows(out_csv, header, rows)


def _export_q1_scenario_table(*, out_csv: Path) -> None:
    """对应 Q1-06（新版）：五类典型使用场景口径表（用于论文统一表述）。"""

    header = ["场景", "典型行为"]
    rows = [
        ["S1 待机/轻度", "低亮或熄屏，低吞吐，后台少"],
        ["S2 浏览/社交", "频繁切换加载，后台开启应用较多"],
        ["S3 视频/直播", "负载较稳但使用时间长，缓存大"],
        ["S4 游戏", "CPU/GPU 使用度高，温度高"],
        ["S5 导航/通话", "蜂窝多，GPS 常开，弱信号惩罚明显"],
    ]
    _write_csv_rows(out_csv, header, rows)


def _export_q1_tte_radar_5cases(*, out_csv: Path) -> None:
    """对应 Q1-06（当前版本）：五类场景下 Model-0 vs Model-1 的 TTE 对比（用于雷达图）。"""

    from mcm26a.battery import BatteryParams0, BatteryParams1ECM
    from mcm26a.power import PowerParams0
    from mcm26a.scenarios import load_scenarios_json, materialize_scenario
    from mcm26a.sim import simulate_model0, simulate_model1_ecm

    raw = load_scenarios_json(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json")
    power = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    batt1 = BatteryParams1ECM.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")
    batt0 = BatteryParams0.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")

    order = [
        "S1_standby_light",
        "S2_browse_social",
        "S3_video_streaming",
        "S4_gaming",
        "S5_nav_call",
    ]

    header = ["scenario_id", "title_zh", "tte_model0_h", "tte_model1_h", "delta_h_model1_minus_model0"]
    rows: list[list[Any]] = []
    for sid in order:
        sc_raw = raw["scenarios"][sid]
        sc = materialize_scenario(raw, sid)
        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=1.0)
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=1.0, dt_s=2.0)

        t0 = None if r0.tte_h is None else float(r0.tte_h)
        t1 = None if r1.tte_h is None else float(r1.tte_h)
        rows.append(
            [
                str(sid),
                str(sc_raw.get("title_zh", sid)),
                t0,
                t1,
                (None if (t0 is None or t1 is None) else float(t1 - t0)),
            ]
        )

    _write_csv_rows(out_csv, header, rows)


def _export_soc_at_cutoff(*, out_csv: Path) -> None:
    """对应 Q1-07：截止电压触发关机时的 SOC_end（按场景）。"""

    from mcm26a.battery import BatteryParams1ECM
    from mcm26a.power import PowerParams0
    from mcm26a.scenarios import load_scenarios_json, materialize_scenario
    from mcm26a.sim import simulate_model1_ecm

    raw = load_scenarios_json(SRC_DIR / "configs" / "scenarios_v0.json")
    power = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    batt1 = BatteryParams1ECM.from_json(SRC_DIR / "configs" / "phone_default_v1_ecm.json")

    header = ["scenario_id", "title_zh", "soc_end", "soc_min", "status", "v_cut_V", "tte_h"]
    rows: list[list[Any]] = []
    for sid, sc_raw in raw.get("scenarios", {}).items():
        sc = materialize_scenario(raw, sid)
        r = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=1.0, dt_s=2.0)
        rows.append(
            [
                str(sid),
                str(sc_raw.get("title_zh", sid)),
                float(r.soc_end),
                float(batt1.soc_min),
                str(r.status),
                float(r.v_cut_V),
                (None if r.tte_h is None else float(r.tte_h)),
            ]
        )

    _write_csv_rows(out_csv, header, rows)


def main() -> int:
    # Q1-01: OCV curve
    _export_ocv_curve(out_csv=PAPER_Q1_DIR / "01-电池OCV曲线与截止电压" / "other" / "data.csv")

    # Q1-02: 12_09 voltage trace（best_show）
    _export_calce_voltage_trace(
        report_json=SRC_DIR
        / "out_reports"
        / "validation"
        / "12_09_2015_incremental_ocv_test_sp20_1"
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_rdrop_vgate_relax2stage_12_09tuned_v2.json",
        out_csv=PAPER_Q1_DIR / "02-模型1验证_12_09预测vs观测" / "other" / "data.csv",
    )

    # Q1-03: 12_2 voltage trace（best_show）
    _export_calce_voltage_trace(
        report_json=SRC_DIR
        / "out_reports"
        / "validation"
        / "12_2_2015_incremental_ocv_test_sp20_1"
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_rdrop_vgate_relax2stage_12_2tuned_v1.json",
        out_csv=PAPER_Q1_DIR / "03-模型1验证_12_2预测vs观测" / "other" / "data.csv",
    )

    # Q1-04: polarization states（复用 12_09 tuned）
    _export_calce_polarization_states(
        report_json=SRC_DIR
        / "out_reports"
        / "validation"
        / "12_09_2015_incremental_ocv_test_sp20_1"
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_rdrop_vgate_relax2stage_12_09tuned_v2.json",
        out_csv=PAPER_Q1_DIR / "04-极化分解_快慢支路v1v2" / "other" / "data.csv",
    )

    # Q1-05: trace example
    _export_trace_example(out_csv=PAPER_Q1_DIR / "05-轨迹示例_游戏高负载" / "other" / "data.csv")

    # Q1-06: model0 vs model1 TTE compare
    # 当前版本：figure.png 为“5 场景的 TTE 雷达图”，data.csv 对应雷达图数据。
    _export_q1_tte_radar_5cases(out_csv=PAPER_Q1_DIR / "06-模型0vs模型1_TTE对比" / "other" / "data.csv")
    # 旧版（scenarios_v0.json 的 6 场景柱状图）数据仍保留在 other/ 下备用，便于追溯。
    _export_tte_compare_model0_vs_model1(
        out_csv=PAPER_Q1_DIR / "06-模型0vs模型1_TTE对比" / "other" / "data_old_tte_model0_vs_model1.csv"
    )

    # Q1-07: SOC at cutoff
    _export_soc_at_cutoff(out_csv=PAPER_Q1_DIR / "07-欠压提前关机_SOC剩余" / "other" / "data.csv")

    # Q1-08: 10_16 extreme spike（best_show）
    _export_calce_voltage_trace(
        report_json=SRC_DIR
        / "out_reports"
        / "validation"
        / "10_16_2015_initial_capacity_sp20_1"
        / "battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth.json",
        out_csv=PAPER_Q1_DIR / "08-额外测试_极端尖峰10_16" / "other" / "data.csv",
    )

    print("[OK] 已导出 Q1材料 主图数据版本：")
    for d in sorted([p for p in PAPER_Q1_DIR.iterdir() if p.is_dir()]):
        p = d / "other" / "data.csv"
        if p.exists():
            print("-", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
