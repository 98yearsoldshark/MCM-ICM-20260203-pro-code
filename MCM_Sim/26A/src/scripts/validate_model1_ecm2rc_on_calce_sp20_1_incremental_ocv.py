#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：在 CALCE SP20-1 Incremental OCV 数据上验证 Model-1（二阶 Thevenin 2RC ECM）电压预测误差。

定位（对应赛题要求）：
- 赛题强调“连续时间机理模型”并要求用数据做参数估计与验证；
- 这里验证的是电池端：给定电流轨迹 I(t) 时，2RC ECM 能否解释端电压 V(t)（含松弛/恢复）。

与 1RC 的关系（来自 no3 的可用技术点）：
- 2RC 用两个极化支路区分不同时间尺度：v1（更快）与 v2（更慢）；
- 有助于解释“秒级回弹 + 分钟级恢复”并存的现象。

输出：
- JSON 报表：MCM_Sim/26A/src/out_reports/validation/<dataset_id>/<config>.json
- 图像：MCM_Sim/26A/src/out_plots/model1/{paper|study}/validation/<dataset_id>/<config>/...
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

from mcm26a.battery import BatteryParams1ECM2RC
from mcm26a.battery.model1_ecm2rc import simulate_ecm2rc_current_control
from mcm26a.calibration import build_voltage_error_report, extract_channel_time_series, load_calce_channel_xlsx
from mcm26a.utils import PiecewiseLinearCurve
# 注意：必须在导入 matplotlib.pyplot 之前引入 style，
# 以确保 MPLBACKEND/MPLCONFIGDIR 在受限环境下可用（否则可能触发 GUI 后端崩溃或写权限问题）。
from mcm26a.viz.style import apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt


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
    return [
        # 推荐：2RC（R0 先验 + R1/R2(SOC) + C1/C2）
        SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_2rc.json",
    ]


def _slugify(text: str) -> str:
    s = str(text).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "dataset"


def _infer_dataset_id(xlsx: Path) -> str:
    return _slugify(xlsx.stem)


def _constant_curve(v: float) -> PiecewiseLinearCurve:
    return PiecewiseLinearCurve(points=((0.0, float(v)), (1.0, float(v))))


def _estimate_soc0_from_initial_rest(ts, *, batt: BatteryParams1ECM2RC, rest_i_thresh_A: float, window_s: float) -> float:
    """用起始休止段的电压（近似 OCV）反推 SOC0。"""

    t = np.asarray(ts.t_s, dtype=float)
    i = np.asarray(ts.i_A, dtype=float)
    v = np.asarray(ts.v_V, dtype=float)

    m = (np.abs(i) <= float(rest_i_thresh_A)) & (t <= float(t[0]) + float(window_s))
    if int(np.sum(m)) < 30:
        return 1.0
    v0 = float(np.median(v[m]))
    soc0 = float(batt.ocv.soc_from_ocv_v(v0))
    return min(1.0, max(0.0, soc0))


def _simulate_voltage_current_control(
    ts, *, batt: BatteryParams1ECM2RC, soc0: float, diff_v_gate: str = "measured"
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """电流控制下仿真 2RC，返回 (soc, v1, v2, h, z, v_pred)。

    说明：
    - h：状态迟滞/路径记忆（可选）
    - z：低 SOC 扩散极化/慢恢复状态（可选）
    """

    r1_curve = batt.r1_curve if batt.r1_curve is not None else _constant_curve(float(batt.r1_ohm))
    r2_curve = batt.r2_curve if batt.r2_curve is not None else _constant_curve(float(batt.r2_ohm))
    # 是否启用 z：由配置决定（diff_gamma>0 且 diff_relax_tau_s>0 且 M 非零）
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
    if diff_enabled:
        use_measured_gate = str(diff_v_gate).strip().lower() in ("measured", "meas", "obs", "observed")
        soc, v1, v2, h, z, v_pred = simulate_ecm2rc_current_control(
            soc0=float(soc0),
            v1_0_V=0.0,
            v2_0_V=0.0,
            capacity_Ah=float(batt.capacity_Ah),
            ocv=batt.ocv,
            r0_ohm=float(batt.r0_ohm),
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
            # measured：观测辅助/诊断模式；model：纯前向（用模型电压门控）
            diff_v_gate_V=(np.asarray(ts.v_V, dtype=float) if use_measured_gate else None),
            return_h=True,
            return_z=True,
            dt_s=np.asarray(ts.dt_s, dtype=float),
            i_A=np.asarray(ts.i_A, dtype=float),
        )
    else:
        soc, v1, v2, h, v_pred = simulate_ecm2rc_current_control(
        soc0=float(soc0),
        v1_0_V=0.0,
        v2_0_V=0.0,
        capacity_Ah=float(batt.capacity_Ah),
        ocv=batt.ocv,
        r0_ohm=float(batt.r0_ohm),
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
        return_h=True,
        # diff_* 相关参数仅在 diff_enabled=False 时不会被使用；这里留空即可（保持签名一致）。
        dt_s=np.asarray(ts.dt_s, dtype=float),
        i_A=np.asarray(ts.i_A, dtype=float),
    )
        z = np.zeros_like(v_pred, dtype=float)
    return (
        np.asarray(soc, dtype=float),
        np.asarray(v1, dtype=float),
        np.asarray(v2, dtype=float),
        np.asarray(h, dtype=float),
        np.asarray(z, dtype=float),
        np.asarray(v_pred, dtype=float),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="验证：CALCE SP20-1 Incremental OCV（Model-1/ECM 2RC 电压误差）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（Channel_* 格式）")
    ap.add_argument(
        "--phone",
        action="append",
        default=[],
        help="电池配置 JSON（可重复传入多次用于对比）；留空则使用默认配置",
    )
    ap.add_argument("--dataset-id", default="", help="数据集标识（用于输出目录命名）；留空则根据文件名自动推断")
    ap.add_argument(
        "--out-dir",
        default="",
        help="输出报表目录（默认：MCM_Sim/26A/src/out_reports/validation/<dataset_id>/）",
    )
    ap.add_argument(
        "--plots-dir",
        default=str(SRC_DIR / "out_plots"),
        help="图像输出根目录（默认：MCM_Sim/26A/src/out_plots/model1/{paper|study}/validation/...）",
    )
    ap.add_argument("--no-plots", action="store_true", help="不生成图像（只输出 JSON 报表）")
    ap.add_argument("--soc0", type=float, default=-1.0, help="初始 SOC；<0 表示用起始休止段电压自动估计")
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--rest-window", type=float, default=600.0, help="估计 SOC0 的起始时间窗（秒）")
    ap.add_argument(
        "--diff-v-gate",
        default="measured",
        choices=("measured", "model"),
        help=(
            "扩散极化 z(t) 的门控电压来源：\n"
            "- measured：使用观测电压 V_meas(t) 作为门控输入（观测辅助/诊断；曲线通常更贴合）\n"
            "- model：使用模型预测电压 V_pred(t) 作为门控输入（纯前向预测口径；更适合做独立验证）"
        ),
    )
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    dataset_id = str(args.dataset_id).strip() or _infer_dataset_id(xlsx)

    phone_paths = [Path(p).expanduser().resolve() for p in args.phone] if args.phone else _default_phones()
    phone_by_tag = {p.stem: p for p in phone_paths}
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if str(args.out_dir).strip()
        else (SRC_DIR / "out_reports" / "validation" / dataset_id)
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)
    print("[数据] dataset_id:", dataset_id)
    print("[数据] xlsx:", xlsx)
    print(f"[数据] samples={len(ts.t_s)}  duration≈{(float(ts.t_s[-1]-ts.t_s[0])/3600.0):.2f} h  steps={len(set(int(x) for x in ts.step.tolist()))}")

    pred_map: dict[str, dict[str, np.ndarray]] = {}

    for phone in phone_paths:
        batt = BatteryParams1ECM2RC.from_json(phone)
        soc0 = float(args.soc0)
        if soc0 < 0:
            soc0 = _estimate_soc0_from_initial_rest(ts, batt=batt, rest_i_thresh_A=float(args.rest_i), window_s=float(args.rest_window))

        soc, v1, v2, h, z, v_pred = _simulate_voltage_current_control(ts, batt=batt, soc0=soc0, diff_v_gate=str(args.diff_v_gate))
        rep = build_voltage_error_report(
            ts,
            v_pred_V=v_pred,
            rest_i_thresh_A=float(args.rest_i),
            v_cut_V=float(batt.v_cut_V),
        )

        tag = phone.stem
        out_json = out_dir / f"{tag}.json"
        payload = {
            "dataset": str(xlsx),
            "phone_config": str(phone),
            "soc0_used": float(soc0),
            "mode": {
                "diff_v_gate": str(args.diff_v_gate),
                "notes_zh": "diff_v_gate=measured 表示 z(t) 门控使用观测电压（观测辅助/诊断）；model 表示使用模型电压（纯前向验证口径）。",
            },
            "report": rep,
        }
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        pred_map[tag] = {"v_pred": v_pred, "soc": soc, "v1": v1, "v2": v2, "h": h, "z": z}

        o = rep["overall"]
        pd = rep.get("phone_domain", {}) or {}
        r = rep.get("rest_segments", {})
        print("")
        print(f"[结果] {tag}")
        print(f"- soc0={soc0:.3f}")
        print(f"- overall: RMSE={o['rmse_mV']:.1f} mV  MAE={o['mae_mV']:.1f} mV  (n={o['n']})")
        if pd:
            u = pd.get("overall_until_cutoff_above_vcut", pd.get("overall_until_cutoff", {})) or {}
            print(
                f"- phone_domain: RMSE={u.get('rmse_mV', float('nan')):.1f} mV  "
                f"MAE={u.get('mae_mV', float('nan')):.1f} mV  "
                f"(n={u.get('n','?')})  "
                f"TTE误差={pd.get('tte_error_s', float('nan')):.1f} s"
            )
        if r:
            print(
                f"- rest: n_seg={r.get('n_segments','?')}  early_RMSE={r['rest_early']['rmse_mV']:.1f} mV  late_RMSE={r['rest_late']['rmse_mV']:.1f} mV"
            )
        print(f"- report: {out_json}")

    if args.no_plots or not pred_map:
        return 0

    t_h = (np.asarray(ts.t_s, dtype=float) - float(ts.t_s[0])) / 3600.0
    v_meas = np.asarray(ts.v_V, dtype=float)
    i = np.asarray(ts.i_A, dtype=float)
    steps = np.asarray(ts.step, dtype=int)

    def _plot_idx(mode: str) -> np.ndarray:
        """根据数据规模自适应下采样，避免“折线感”与绘图过重两头失衡。

        经验：study 模式更偏向诊断，允许更多点；paper 模式更偏向版面与文件体积。
        """

        target = 20000 if str(mode) == "study" else 12000
        stride = max(1, int(len(t_h) // max(1, int(target))))
        return np.arange(0, len(t_h), stride, dtype=int)

    root = Path(args.plots_dir).expanduser().resolve()

    def _first_cut_time_h(v: np.ndarray, *, v_cut: float, discharge_i_thresh_A: float = 0.1) -> float | None:
        m = (i >= float(discharge_i_thresh_A)) & (np.asarray(v, dtype=float) <= float(v_cut))
        if not bool(np.any(m)):
            return None
        k = int(np.argmax(m))
        return float(t_h[k])

    for tag, arrs in pred_map.items():
        for mode in ("paper", "study"):
            style = apply_style(mode)  # type: ignore[arg-type]
            idx = _plot_idx(mode)
            outp = ensure_dir(root / "model1" / mode / "validation" / dataset_id / tag)
            batt = BatteryParams1ECM2RC.from_json(phone_by_tag.get(tag, phone_paths[0]))
            v_cut = float(batt.v_cut_V)
            tte_meas_h = _first_cut_time_h(v_meas, v_cut=v_cut)
            tte_pred_h = _first_cut_time_h(np.asarray(arrs["v_pred"], dtype=float), v_cut=v_cut)

            def _t(zh: str, en: str) -> str:
                """paper 用英文；study 用中文（用户学习/诊断更友好）。"""

                return en if str(mode) == "paper" else zh

            # 01 电压时序对比
            fig, ax = plt.subplots(figsize=(10.5, 4.2))
            ax.plot(t_h[idx], v_meas[idx], color="#4C78A8", lw=2.0, label=_t("观测 V", "Measured V"))
            ax.plot(
                t_h[idx],
                arrs["v_pred"][idx],
                color="#E45756",
                lw=1.8,
                label=_t("模型 V_pred（2RC）", "Model V_pred (2RC)"),
            )
            # 截止电压与 TTE（Time-to-Empty）
            ax.axhline(
                v_cut,
                color="gray",
                lw=1.0,
                ls="--",
                alpha=0.7,
                label=_t(f"截止电压 {v_cut:.1f}V", f"Cutoff voltage {v_cut:.1f} V"),
            )
            if tte_meas_h is not None:
                ax.axvline(
                    tte_meas_h,
                    color="black",
                    ls=":",
                    lw=1.2,
                    alpha=0.7,
                    label=_t("观测 TTE", "Measured TTE"),
                )
            if tte_pred_h is not None:
                ax.axvline(
                    tte_pred_h,
                    color="#E45756",
                    ls=":",
                    lw=1.2,
                    alpha=0.7,
                    label=_t("预测 TTE", "Predicted TTE"),
                )
            ax.set_xlabel(_t("时间（小时）", "Time (h)"))
            ax.set_ylabel(_t("电压（V）", "Voltage (V)"))
            # 论文版不显示“运行代号/配置文件名”，避免观感杂乱；学习版保留便于溯源。
            title_main = _t("CALCE Incremental OCV：电压对比", "CALCE Incremental OCV: Voltage Comparison")
            if str(mode) == "study":
                ax.set_title(f"{title_main}（{tag}）{style.title_suffix}")
            else:
                ax.set_title(f"{title_main}{style.title_suffix}")
            ax.legend(frameon=False, loc="best", ncol=3)

            if style.annotate:
                fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
                fig.text(
                    0.01,
                    0.02,
                    "学习提示：\n"
                    "1) “尖峰”多来自电流阶跃造成的瞬时欧姆压降 I·R0；\n"
                    "2) 休止段电压回升来自极化电压 v1/v2 的衰减（2RC 用快/慢两条支路分担不同时间尺度）；\n"
                    "3) variants=不同模型/参数配置的对比版本；TTE(Time to Empty)=续航剩余时间，通常由 SOC 或截止电压触发。\n",
                    ha="left",
                    va="bottom",
                    fontsize=9,
                )
            else:
                fig.tight_layout()
            savefig(fig, outp / "01_voltage_trace.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

            # 01b 电压局部放大：对齐最低点（用于诊断“尖峰进入/回弹形态”）
            k_min = int(np.argmin(v_meas))
            t0_s = float(np.asarray(ts.t_s, dtype=float)[k_min])
            t_all_s = np.asarray(ts.t_s, dtype=float)
            # 经验窗口：最低点前 120s、后 240s（足够覆盖“进入尖峰+回弹到平台”）
            m_zoom = (t_all_s >= t0_s - 120.0) & (t_all_s <= t0_s + 240.0)
            if bool(np.any(m_zoom)) and int(np.sum(m_zoom)) >= 10:
                t_rel = t_all_s[m_zoom] - t0_s
                fig, ax = plt.subplots(figsize=(10.5, 3.8))
                ax.plot(t_rel, v_meas[m_zoom], color="#4C78A8", lw=2.2, label=_t("观测 V", "Measured V"))
                ax.plot(
                    t_rel,
                    np.asarray(arrs["v_pred"], dtype=float)[m_zoom],
                    color="#E45756",
                    lw=2.0,
                    label=_t("模型 V_pred（2RC）", "Model V_pred (2RC)"),
                )
                ax.axvline(0.0, color="gray", lw=1.2, ls=":", alpha=0.8, label=_t("最低点对齐", "Aligned at minimum"))
                ax.axhline(v_cut, color="gray", lw=1.0, ls="--", alpha=0.5)
                ax.set_xlabel(_t("时间（秒，相对最低点）", "Time (s, relative to minimum)"))
                ax.set_ylabel(_t("电压（V）", "Voltage (V)"))
                title_zoom = _t("尖峰局部放大（对齐最低点）", "Zoom near deepest dip (aligned at minimum)")
                if str(mode) == "study":
                    ax.set_title(f"{title_zoom}（{tag}）{style.title_suffix}")
                else:
                    ax.set_title(f"{title_zoom}{style.title_suffix}")
                ax.legend(frameon=False, loc="best", ncol=3)
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.28, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "读图要点：\n"
                        "- 进入尖峰（t<0）：形态主要受门控与低 SOC 机制 z 的“建立速度”影响；\n"
                        "- 离开尖峰（t>0）：0~数秒的回弹受 z 的快速恢复与欧姆项决定，几十秒~分钟的缓慢回升受慢恢复决定；\n"
                        "- 若出现不真实的折线/拐点，通常需要把硬阈值门控改成软门控（Sigmoid 平滑）。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, outp / "01b_voltage_trace_zoom_min.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

            # 02 残差直方图
            fig, ax = plt.subplots(figsize=(8.0, 4.0))
            r_mV = (arrs["v_pred"] - v_meas) * 1000.0
            ax.hist(r_mV, bins=80, color="#72B7B2", alpha=0.9)
            ax.set_xlabel("残差 r=V_pred−V_meas（mV）")
            ax.set_ylabel("频数")
            ax.set_title(f"残差分布（{tag}）{style.title_suffix}")
            if style.annotate:
                ax.axvline(float(np.median(r_mV)), color="gray", lw=1.2, ls="--", alpha=0.8)
            fig.tight_layout()
            savefig(fig, outp / "02_residual_hist.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

            # 03 按 step 的 RMSE 条形图
            fig, ax = plt.subplots(figsize=(10.5, 4.0))
            uniq = sorted(set(int(x) for x in steps.tolist()))
            rmses = []
            for s in uniq:
                m = steps == int(s)
                rr = (arrs["v_pred"][m] - v_meas[m]) * 1000.0
                rmses.append(float(np.sqrt(np.mean(rr * rr))) if np.any(m) else float("nan"))
            xs = np.arange(len(uniq))
            ax.bar(xs, rmses, color="#F58518", alpha=0.9)
            ax.set_xticks(xs)
            ax.set_xticklabels([str(s) for s in uniq])
            ax.set_xlabel("Step_Index")
            ax.set_ylabel("RMSE（mV）")
            ax.set_title(f"按 Step 分解的 RMSE（{tag}）{style.title_suffix}")
            fig.tight_layout()
            savefig(fig, outp / "03_rmse_by_step.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

            # 04 极化电压分解（v1/v2）
            # 说明：在某些拟合结果里 v1 与 v2 可能高度重合，导致先画的曲线“被后画的覆盖”，肉眼看起来像消失。
            # 这里用：
            # - 单位换算到 mV（更直观）
            # - 先画 v2，再画 v1（并提高 zorder）
            # - 加一个放大窗（捕捉电流阶跃附近的快/慢差异）
            v1_mV = arrs["v1"] * 1000.0
            v2_mV = arrs["v2"] * 1000.0
            v12_mV = (arrs["v1"] + arrs["v2"]) * 1000.0

            # 配色（论文友好）：三条曲线用固定 3 色调色板（用户指定 Cube Palette）。
            # - v2（慢支路）：#845ec2
            # - v1（快支路）：#4e8397
            # - v1+v2（总极化）：#d5cabd
            c_v2 = "#845ec2"
            c_v1 = "#4e8397"
            c_v12 = "#d5cabd"

            fig, ax = plt.subplots(figsize=(10.8, 4.2))
            ax.plot(t_h[idx], v2_mV[idx], color=c_v2, lw=1.6, alpha=0.90, label="v2（慢支路）", zorder=2)
            ax.plot(t_h[idx], v1_mV[idx], color=c_v1, lw=2.2, alpha=0.95, label="v1（快支路）", zorder=3)
            ax.plot(t_h[idx], v12_mV[idx], color=c_v12, lw=2.4, alpha=1.00, label="v1+v2", zorder=1)
            ax.set_xlabel("时间（小时）")
            ax.set_ylabel("极化电压（mV）")
            ax.set_title(f"2RC 极化电压分解（{tag}）{style.title_suffix}")
            ax.legend(frameon=False, loc="upper left", ncol=3)

            # 放大窗：围绕 |ΔI| 最大的阶跃附近，展示快/慢支路的差异（用全分辨率而非下采样）
            di = np.abs(np.diff(i, prepend=i[0]))
            k0 = int(np.argmax(di))
            t0 = float(t_h[k0])
            w_pre_h = 2.0 / 60.0  # 2 分钟
            w_post_h = 8.0 / 60.0  # 8 分钟
            mz = (t_h >= t0 - w_pre_h) & (t_h <= t0 + w_post_h)
            if int(np.sum(mz)) >= 20:
                axins = ax.inset_axes([0.63, 0.46, 0.35, 0.45])
                axins.plot(t_h[mz], v2_mV[mz], color=c_v2, lw=1.2, alpha=0.90)
                axins.plot(t_h[mz], v1_mV[mz], color=c_v1, lw=1.6, alpha=0.95)
                axins.set_title("阶跃附近放大", fontsize=9)
                axins.grid(True, alpha=0.25)
                axins.tick_params(labelsize=8)
                ax.indicate_inset_zoom(axins, edgecolor="gray", alpha=0.7)

            if style.annotate:
                fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
                v1_max = float(np.max(np.abs(v1_mV)))
                v2_max = float(np.max(np.abs(v2_mV)))
                fig.text(
                    0.01,
                    0.02,
                    "解释：端电压 V=OCV−I·R0−v1−v2。\n"
                    "如果看不到 v1（快支路），常见原因是 v1 与 v2 高度重合或幅值极小（会被后画的曲线覆盖）。\n"
                    f"本数据中 v1|max|≈{v1_max:.3f} mV，v2|max|≈{v2_max:.3f} mV；已在右上角给出“阶跃附近放大图”。\n",
                    ha="left",
                    va="bottom",
                    fontsize=9,
                )
            else:
                fig.tight_layout()
            savefig(fig, outp / "04_polarization_states.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

            # 05 电流轨迹（辅助理解尖峰来源）
            fig, ax = plt.subplots(figsize=(10.5, 3.0))
            ax.plot(t_h[idx], i[idx], color="#4C78A8", lw=1.2)
            ax.axhline(0.0, color="gray", lw=1.0, alpha=0.6)
            ax.set_xlabel("时间（小时）")
            ax.set_ylabel("电流（A，放电为正）")
            ax.set_title(f"电流轨迹 I(t)（{tag}）{style.title_suffix}")
            if style.annotate:
                fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
                fig.text(
                    0.01,
                    0.02,
                    "提示：当 I(t) 发生阶跃时，若 R0 合理，V(t) 也会出现“同步的瞬时跳变”。\n",
                    ha="left",
                    va="bottom",
                    fontsize=9,
                )
            else:
                fig.tight_layout()
            savefig(fig, outp / "05_current_trace.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

            # 06 迟滞/慢恢复状态 h(t)（若启用）
            h = np.asarray(arrs.get("h", np.zeros_like(i)), dtype=float)
            if np.any(np.abs(h) > 1e-9):
                fig, ax = plt.subplots(figsize=(10.5, 3.2))
                ax.plot(t_h[idx], h[idx], color="#54A24B", lw=1.8)
                ax.axhline(0.0, color="gray", lw=1.0, alpha=0.6)
                ax.set_xlabel("时间（小时）")
                ax.set_ylabel("状态 h（-1~1）")
                ax.set_title(f"迟滞/慢恢复状态 h(t)（{tag}）{style.title_suffix}")
                ax.set_ylim(-1.05, 1.05)
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "解释：h(t) 是一个“路径记忆/慢恢复”状态。\n"
                        "- 放电段（I>0）时，h→+1；充电段（I<0）时，h→-1；\n"
                        "- 休止段（I≈0）时，若设置了 hyst_relax_tau_s，则 h 会缓慢回到 0。\n"
                        "端电压额外项：V_term = OCV − I·R0 − v1 − v2 − M(SOC)·h。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, outp / "06_h_state.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

                # 07 M(SOC)*h(t) 对电压的贡献（mV）
                m0 = float(getattr(batt, "hyst_M_V", 0.0))
                mh = np.zeros_like(h, dtype=float)
                if getattr(batt, "hyst_M_curve", None) is not None:
                    mh = np.array([float(batt.hyst_M_curve.value(float(s))) for s in arrs["soc"]], dtype=float) * h
                else:
                    mh = float(m0) * h
                fig, ax = plt.subplots(figsize=(10.5, 3.2))
                ax.plot(t_h[idx], mh[idx] * 1000.0, color="#B279A2", lw=1.8)
                ax.axhline(0.0, color="gray", lw=1.0, alpha=0.6)
                ax.set_xlabel("时间（小时）")
                ax.set_ylabel("电压贡献 M(SOC)·h（mV）")
                ax.set_title(f"迟滞/慢恢复对电压的贡献（{tag}）{style.title_suffix}")
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "读图：该曲线越大，表示“路径记忆/慢恢复”造成的电压偏移越明显。\n"
                        "它常用于解释：深放电后即使进入休止段，电压仍显著偏低且回升很慢。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, outp / "07_h_voltage_contrib.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

            # 08 低 SOC 扩散极化/慢恢复状态 z(t)（若启用）
            z = np.asarray(arrs.get("z", np.zeros_like(i)), dtype=float)
            if np.any(np.abs(z) > 1e-9):
                fig, ax = plt.subplots(figsize=(10.5, 3.2))
                ax.plot(t_h[idx], z[idx], color="#9D755D", lw=1.8)
                ax.axhline(0.0, color="gray", lw=1.0, alpha=0.6)
                ax.set_xlabel("时间（小时）")
                ax.set_ylabel("状态 z（0~1）")
                ax.set_title(f"扩散极化/慢恢复状态 z(t)（{tag}）{style.title_suffix}")
                ax.set_ylim(-0.02, 1.02)
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.25, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "解释：z(t) 表示“低 SOC 下的扩散/浓差极化强度”（0~1）。\n"
                        "- 触发：当 SOC 足够低且放电电流足够大时，z 会逐步上升（更强的非平衡）；\n"
                        "- 休止/充电：z 按时间常数 diff_relax_tau_s 逐步衰减到 0（慢恢复）。\n"
                        "端电压额外项：V_term = OCV − I·R0 − v1 − v2 − M2(SOC)·z。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, outp / "08_diff_state.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

                # 09 M2(SOC)*z(t) 对电压的贡献（mV）
                m20 = float(getattr(batt, "diff_M_V", 0.0))
                mz = np.zeros_like(z, dtype=float)
                if getattr(batt, "diff_M_curve", None) is not None:
                    mz = np.array([float(batt.diff_M_curve.value(float(s))) for s in arrs["soc"]], dtype=float) * z
                else:
                    mz = float(m20) * z
                fig, ax = plt.subplots(figsize=(10.5, 3.2))
                ax.plot(t_h[idx], mz[idx] * 1000.0, color="#E45756", lw=1.8)
                ax.axhline(0.0, color="gray", lw=1.0, alpha=0.6)
                ax.set_xlabel("时间（小时）")
                ax.set_ylabel("电压贡献 M2(SOC)·z（mV）")
                ax.set_title(f"扩散极化/慢恢复对电压的贡献（{tag}）{style.title_suffix}")
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "读图：该曲线越大，表示“低 SOC 扩散极化”造成的额外压降越明显。\n"
                        "它常用于解释：深放电末端出现异常深的电压下探，以及随后小时级的缓慢回升。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, outp / "09_diff_voltage_contrib.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
