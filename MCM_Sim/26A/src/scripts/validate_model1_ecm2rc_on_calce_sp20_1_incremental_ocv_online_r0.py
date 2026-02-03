#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：CALCE Incremental OCV（2RC ECM + 在线估计 R0，Q1 增强版）。

本脚本服务赛题 Q1 的“参数估计与验证”叙事：
- 仍然使用连续时间机理模型（2RC 等效电路 / ODE）做前向仿真；
- 不引入黑箱回归；仅在使用早期通过“休止->负载”的电压跳变估计一次 R0；
- 用估计到的 R0 固定下来，对整段轨迹前向预测并输出误差指标与对比图。

输出：
- JSON：src/out_reports/validation/<dataset_id>/<tag>__{open_loop|online_r0fit}.json
- 图：  src/out_plots/model1/{paper|study}/validation/<dataset_id>/<tag>__{open_loop|online_r0fit}/01_voltage_trace.png
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import matplotlib.pyplot as plt

from mcm26a.battery import BatteryParams1ECM2RC
from mcm26a.battery.model1_ecm2rc import simulate_ecm2rc_current_control
from mcm26a.calibration import build_voltage_error_report, extract_channel_time_series, load_calce_channel_xlsx
from mcm26a.calibration.calce_channel import CalceChannelTimeSeries
from mcm26a.calibration.r0_estimator import estimate_r0_from_rest_load_transitions
from mcm26a.utils import PiecewiseLinearCurve
from mcm26a.viz.style import apply_style, ensure_dir, savefig


def _default_xlsx() -> Path:
    return (
        SRC_DIR.parent
        / "data"
        / "calce-umd"
        / "extracted"
        / "battery-data"
        / "SP"
        / "12_2_2015_Incremental OCV test_SP20-1.xlsx"
    )


def _default_phones() -> list[Path]:
    return [SRC_DIR / "configs" / "battery_calce_sp20_1_q1fit_2rc_v1.json"]


def _slugify(text: str) -> str:
    s = str(text).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "dataset"


def _infer_dataset_id(xlsx: Path) -> str:
    return _slugify(xlsx.stem)


def _constant_curve(v: float) -> PiecewiseLinearCurve:
    return PiecewiseLinearCurve(points=((0.0, float(v)), (1.0, float(v))))


def _estimate_soc0_from_initial_rest(
    ts: CalceChannelTimeSeries,
    *,
    batt: BatteryParams1ECM2RC,
    rest_i_thresh_A: float,
    window_s: float,
) -> float:
    """用起始休止段的端电压（近似 OCV）反推 SOC0（非常弱假设，论文里可解释）。"""

    t = np.asarray(ts.t_s, dtype=float)
    i = np.asarray(ts.i_A, dtype=float)
    v = np.asarray(ts.v_V, dtype=float)

    t0 = float(t[0])
    m = (np.abs(i) <= float(rest_i_thresh_A)) & (t <= t0 + float(window_s))
    if int(np.sum(m)) < 30:
        return 1.0
    v0 = float(np.median(v[m]))
    soc0 = float(batt.ocv.soc_from_ocv_v(v0))
    return float(np.clip(soc0, 0.0, 1.0))


def _simulate_voltage_current_control(
    ts: CalceChannelTimeSeries,
    *,
    batt: BatteryParams1ECM2RC,
    soc0: float,
    r0_override_ohm: float | None,
    diff_v_gate: str,
) -> np.ndarray:
    """电流控制下仿真 2RC，返回 v_pred(t)（纯前向）。"""

    r1_curve = batt.r1_curve if batt.r1_curve is not None else _constant_curve(float(batt.r1_ohm))
    r2_curve = batt.r2_curve if batt.r2_curve is not None else _constant_curve(float(batt.r2_ohm))

    r0 = float(batt.r0_ohm) if r0_override_ohm is None else float(r0_override_ohm)

    # diff_z（扩散极化）是否启用：通过参数存在性判定；不改变模型对外接口。
    diff_enabled = (
        float(getattr(batt, "diff_gamma", 0.0)) > 0.0
        and float(getattr(batt, "diff_relax_tau_s", 0.0)) > 0.0
        and (
            float(getattr(batt, "diff_M_V", 0.0)) > 0.0
            or getattr(batt, "diff_M_curve", None) is not None
            or float(getattr(batt, "diff_R_ohm", 0.0)) > 0.0
            or getattr(batt, "diff_R_curve", None) is not None
        )
    )
    use_measured_gate = str(diff_v_gate).strip().lower() in ("measured", "meas", "obs", "observed")

    if diff_enabled:
        _, _, _, _, _, v_pred = simulate_ecm2rc_current_control(
            soc0=float(soc0),
            v1_0_V=0.0,
            v2_0_V=0.0,
            capacity_Ah=float(batt.capacity_Ah),
            ocv=batt.ocv,
            r0_ohm=float(r0),
            r0_curve=batt.r0_curve,
            c1_F=float(batt.c1_F),
            c2_F=float(batt.c2_F),
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            rate_capacity_k_per_A=float(getattr(batt, "rate_capacity_k_per_A", 0.0)),
            hyst_M_V=float(getattr(batt, "hyst_M_V", 0.0)),
            hyst_gamma=float(getattr(batt, "hyst_gamma", 0.0)),
            hyst_i_thresh_A=float(getattr(batt, "hyst_i_thresh_A", 0.05)),
            hyst_M_curve=getattr(batt, "hyst_M_curve", None),
            hyst_relax_tau_s=float(getattr(batt, "hyst_relax_tau_s", 0.0)),
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
            diff_v_gate_V=(np.asarray(ts.v_V, dtype=float) if use_measured_gate else None),
            return_h=True,
            return_z=True,
            dt_s=np.asarray(ts.dt_s, dtype=float),
            i_A=np.asarray(ts.i_A, dtype=float),
        )
    else:
        _, _, _, v_pred = simulate_ecm2rc_current_control(
            soc0=float(soc0),
            v1_0_V=0.0,
            v2_0_V=0.0,
            capacity_Ah=float(batt.capacity_Ah),
            ocv=batt.ocv,
            r0_ohm=float(r0),
            r0_curve=batt.r0_curve,
            c1_F=float(batt.c1_F),
            c2_F=float(batt.c2_F),
            r1_curve=r1_curve,
            r2_curve=r2_curve,
            rate_capacity_k_per_A=float(getattr(batt, "rate_capacity_k_per_A", 0.0)),
            hyst_M_V=float(getattr(batt, "hyst_M_V", 0.0)),
            hyst_gamma=float(getattr(batt, "hyst_gamma", 0.0)),
            hyst_i_thresh_A=float(getattr(batt, "hyst_i_thresh_A", 0.05)),
            hyst_M_curve=getattr(batt, "hyst_M_curve", None),
            hyst_relax_tau_s=float(getattr(batt, "hyst_relax_tau_s", 0.0)),
            return_h=False,
            dt_s=np.asarray(ts.dt_s, dtype=float),
            i_A=np.asarray(ts.i_A, dtype=float),
        )

    return np.asarray(v_pred, dtype=float)


def _subset_by_time(ts: CalceChannelTimeSeries, *, window_s: float) -> CalceChannelTimeSeries:
    t_rel = np.asarray(ts.t_s, dtype=float) - float(ts.t_s[0])
    m = t_rel <= float(window_s)
    return CalceChannelTimeSeries(
        t_s=np.asarray(ts.t_s, dtype=float)[m],
        dt_s=np.asarray(ts.dt_s, dtype=float)[m],
        step=np.asarray(ts.step, dtype=int)[m],
        i_A=np.asarray(ts.i_A, dtype=float)[m],
        v_V=np.asarray(ts.v_V, dtype=float)[m],
        temp_C=None,
        r_internal_ohm=None,
    )


def _fit_r0_online(
    ts: CalceChannelTimeSeries,
    *,
    window_s: float,
    rest_i_thresh_A: float,
    load_i_thresh_A: float,
    n_rest: int,
    n_load: int,
    min_gap: int,
) -> dict:
    """在给定时间窗内估计 R0（在线辨识）。"""

    ts_sub = _subset_by_time(ts, window_s=window_s)
    est = estimate_r0_from_rest_load_transitions(
        ts_sub,
        rest_i_thresh_A=float(rest_i_thresh_A),
        load_i_thresh_A=float(load_i_thresh_A),
        n_rest=int(n_rest),
        n_load=int(n_load),
        min_gap=int(min_gap),
    )
    return {
        "window_s": float(window_s),
        "params": {"n_rest": int(n_rest), "n_load": int(n_load), "min_gap": int(min_gap)},
        "summary": est.summary(),
    }


def _plot_voltage_trace(
    *,
    mode: str,
    tag: str,
    out_dir: Path,
    ts: CalceChannelTimeSeries,
    v_pred: np.ndarray,
    v_cut_V: float,
    note_zh: str,
) -> None:
    """画电压对比图：paper（简洁）/study（带讲解）。"""

    style = apply_style(mode)  # type: ignore[arg-type]

    t_h = (np.asarray(ts.t_s, dtype=float) - float(ts.t_s[0])) / 3600.0
    v_meas = np.asarray(ts.v_V, dtype=float)

    target = 20000 if str(mode) == "study" else 12000
    stride = max(1, int(len(t_h) // max(1, int(target))))
    idx = np.arange(0, len(t_h), stride, dtype=int)

    # 配色：Cube Palette（三色时更清爽）；本图为“观测 vs 模型”，两色即可。
    c_meas = "#4e8397"  # blue-green
    c_pred = "#845ec2"  # purple

    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.plot(t_h[idx], v_meas[idx], color=c_meas, lw=2.0, label="观测 V")
    ax.plot(t_h[idx], v_pred[idx], color=c_pred, lw=1.8, label="模型 V_pred（2RC）")
    ax.axhline(float(v_cut_V), color="gray", lw=1.0, ls="--", alpha=0.7, label=f"截止电压 {float(v_cut_V):.1f}V")
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("电压（V）")
    ax.set_title(f"电压对比（{tag}）{style.title_suffix}")
    ax.legend(frameon=False, loc="best", ncol=3)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "学习提示：\n"
            "- 该数据包含“电流脉冲 + 休止恢复”，尖峰主要来自 I·R0 的瞬时压降；平台/回弹由 OCV(SOC) 与极化状态共同决定。\n"
            "- TTE（Time-To-Empty）：电压首次跌破截止电压 V_cut 的时间（本项目单位：秒）。\n"
            "- variants：同一数据/同一模型下，不同参数配置/机制开关的曲线对比。\n"
            f"- {note_zh}\n",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_dir / "01_voltage_trace.png", mode=mode)  # type: ignore[arg-type]
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="验证：CALCE Incremental OCV（2RC + 在线 R0 估计）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（Channel_* 格式）")
    ap.add_argument("--phone", action="append", default=[], help="电池配置 JSON（可重复传入多次用于对比）；留空则使用默认配置")
    ap.add_argument("--dataset-id", default="", help="数据集标识（用于输出目录命名）；留空则根据文件名自动推断")
    ap.add_argument("--out-dir", default="", help="输出报表目录（默认：src/out_reports/validation/<dataset_id>/）")
    ap.add_argument("--plots-dir", default=str(SRC_DIR / "out_plots"), help="图像输出根目录（默认：src/out_plots/model1/...）")
    ap.add_argument("--no-plots", action="store_true", help="不生成图像（只输出 JSON 报表）")
    ap.add_argument("--soc0", type=float, default=-1.0, help="初始 SOC；<0 表示用起始休止段电压自动估计")
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--rest-window", type=float, default=600.0, help="估计 SOC0 的起始时间窗（秒）")
    ap.add_argument(
        "--diff-v-gate",
        default="model",
        choices=("model", "measured"),
        help="扩散极化 z(t) 门控电压来源：model=纯前向口径；measured=观测辅助/诊断。",
    )

    # 在线 R0 估计参数（谨慎可解释：只识别一次“有效 R0”）
    ap.add_argument("--r0-fit-window", type=float, default=12 * 3600.0, help="用于在线估计 R0 的时间窗长度（秒）")
    ap.add_argument("--r0-fit-load-i", type=float, default=0.2, help="判定负载段的电流阈值（A）")
    ap.add_argument("--r0-fit-n-rest", type=int, default=20, help="边界前 rest 窗口点数")
    ap.add_argument("--r0-fit-n-load", type=int, default=1, help="边界后 load 窗口点数（越小越接近“瞬时”）")
    ap.add_argument("--r0-fit-min-gap", type=int, default=50, help="事件最小间隔（点）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    dataset_id = str(args.dataset_id).strip() or _infer_dataset_id(xlsx)
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if str(args.out_dir).strip()
        else (SRC_DIR / "out_reports" / "validation" / dataset_id)
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    phone_paths = [Path(p).expanduser().resolve() for p in args.phone] if args.phone else _default_phones()

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)
    print("[数据] dataset_id:", dataset_id)
    print("[数据] xlsx:", xlsx)
    print(f"[数据] samples={len(ts.t_s)}  duration≈{(float(ts.t_s[-1]) - float(ts.t_s[0]))/3600.0:.2f}h")

    for phone in phone_paths:
        if not phone.exists():
            print(f"[WARN] 找不到 phone 配置，跳过：{phone}")
            continue

        batt = BatteryParams1ECM2RC.from_json(phone)

        soc0 = float(args.soc0)
        if soc0 < 0:
            soc0 = _estimate_soc0_from_initial_rest(ts, batt=batt, rest_i_thresh_A=float(args.rest_i), window_s=float(args.rest_window))

        # 1) open-loop（R0 用配置值）
        v_pred_open = _simulate_voltage_current_control(
            ts, batt=batt, soc0=soc0, r0_override_ohm=None, diff_v_gate=str(args.diff_v_gate)
        )
        rep_open = build_voltage_error_report(ts, v_pred_V=v_pred_open, rest_i_thresh_A=float(args.rest_i), v_cut_V=float(batt.v_cut_V))

        # 2) online R0 fit（早期估计一次，然后固定）
        r0_fit = _fit_r0_online(
            ts,
            window_s=float(args.r0_fit_window),
            rest_i_thresh_A=float(args.rest_i),
            load_i_thresh_A=float(args.r0_fit_load_i),
            n_rest=int(args.r0_fit_n_rest),
            n_load=int(args.r0_fit_n_load),
            min_gap=int(args.r0_fit_min_gap),
        )
        s = (r0_fit.get("summary", {}) or {}) if isinstance(r0_fit, dict) else {}
        r0_eff = None
        if int(s.get("n", 0)) > 0 and s.get("median_ohm", None) is not None:
            r0_eff = float(s["median_ohm"])

        v_pred_online = _simulate_voltage_current_control(
            ts, batt=batt, soc0=soc0, r0_override_ohm=r0_eff, diff_v_gate=str(args.diff_v_gate)
        )
        rep_online = build_voltage_error_report(
            ts, v_pred_V=v_pred_online, rest_i_thresh_A=float(args.rest_i), v_cut_V=float(batt.v_cut_V)
        )

        tag = phone.stem
        out_open = out_dir / f"{tag}__open_loop.json"
        out_online = out_dir / f"{tag}__online_r0fit.json"
        out_open.write_text(
            json.dumps(
                {
                    "dataset": str(xlsx),
                    "phone_config": str(phone),
                    "soc0_used": float(soc0),
                    "mode": {"kind": "open_loop", "diff_v_gate": str(args.diff_v_gate)},
                    "report": rep_open,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        out_online.write_text(
            json.dumps(
                {
                    "dataset": str(xlsx),
                    "phone_config": str(phone),
                    "soc0_used": float(soc0),
                    "mode": {
                        "kind": "online_r0fit",
                        "diff_v_gate": str(args.diff_v_gate),
                        "r0_fit": r0_fit,
                        "r0_base_ohm": float(batt.r0_ohm),
                        "r0_effective_ohm": (None if r0_eff is None else float(r0_eff)),
                    },
                    "report": rep_online,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        def _brief(rep: dict) -> str:
            pd = rep.get("phone_domain", {}) or {}
            u = pd.get("overall_until_cutoff_above_vcut", pd.get("overall_until_cutoff", {})) or {}
            return f"RMSE_phone_domain={float(u.get('rmse_mV', float('nan'))):.2f}mV  TTE误差={float(pd.get('tte_error_s', float('nan'))):.1f}s"

        print("")
        print(f"[结果] {tag}")
        print(f"- open_loop:   {_brief(rep_open)}")
        if r0_eff is None:
            print(f"- online_r0fit: 未估计到有效 R0（n={int(s.get('n',0))}），已退回 open_loop")
        else:
            print(f"- online_r0fit: R0_base={float(batt.r0_ohm):.4f}Ω -> R0_eff={float(r0_eff):.4f}Ω  (n={int(s.get('n',0))})")
            print(f"               {_brief(rep_online)}")
        print(f"- report(open):   {out_open}")
        print(f"- report(online): {out_online}")

        if args.no_plots:
            continue

        root = Path(args.plots_dir).expanduser().resolve()
        for mode in ("paper", "study"):
            outp_open = ensure_dir(root / "model1" / mode / "validation" / dataset_id / f"{tag}__open_loop")
            outp_online = ensure_dir(root / "model1" / mode / "validation" / dataset_id / f"{tag}__online_r0fit")
            _plot_voltage_trace(
                mode=mode,
                tag=f"{tag}（open_loop）",
                out_dir=outp_open,
                ts=ts,
                v_pred=v_pred_open,
                v_cut_V=float(batt.v_cut_V),
                note_zh=f"R0 固定为配置值：{float(batt.r0_ohm):.4f}Ω",
            )
            if r0_eff is None:
                note = f"在线 R0 估计失败（n={int(s.get('n',0))}），退回：{float(batt.r0_ohm):.4f}Ω"
            else:
                note = (
                    f"在线估计：R0_base={float(batt.r0_ohm):.4f}Ω -> R0_eff={float(r0_eff):.4f}Ω；"
                    f"窗口={float(args.r0_fit_window)/3600.0:.1f}h，事件数 n={int(s.get('n',0))}"
                )
            _plot_voltage_trace(
                mode=mode,
                tag=f"{tag}（online_r0fit）",
                out_dir=outp_online,
                ts=ts,
                v_pred=v_pred_online,
                v_cut_V=float(batt.v_cut_V),
                note_zh=note,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
