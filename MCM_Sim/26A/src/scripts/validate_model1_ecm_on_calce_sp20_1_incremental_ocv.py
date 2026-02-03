#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：在 CALCE SP20-1 Incremental OCV 数据上验证 Model-1（ECM）电压预测误差。

定位（对应赛题要求）：
- 赛题要求“连续时间机理模型”，并要求用数据做参数估计与验证；
- 我们把“手机侧功耗模型”与“电池电学模型”解耦；
- 这里验证的是电池端：给定电流轨迹 I(t) 时，ECM 能否解释 V(t)（含松弛/恢复）。

说明：
- 本脚本不做拟合，只做对比与误差报表输出；
- 用于检验：引入 R1(SOC)/R0(SOC) 等结构后，是否能在“独立数据”上更稳健。
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

from mcm26a.battery import BatteryParams1ECM
from mcm26a.calibration import build_voltage_error_report, extract_channel_time_series, load_calce_channel_xlsx
from mcm26a.calibration.ecm_current_socdep import (
    simulate_ecm_current_control_r0_r1_soc,
    simulate_ecm_current_control_r1_soc,
)
from mcm26a.utils import PiecewiseLinearCurve
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig

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
        # baseline：仅 OCV（R0/R1/C1 为名义值）
        SRC_DIR / "configs" / "battery_calce_sp20_1.json",
        # 推荐：先用“含阶跃/脉冲”的数据估计 R0，再固定 R0 拟合 R1(SOC)+C1（修复“优化变差”）
        SRC_DIR / "configs" / "battery_calce_sp20_1_ecmfit_r0fixed_r1soc.json",
    ]


def _slugify(text: str) -> str:
    """把任意字符串转成适合做目录名的 slug（仅保留 a-z0-9 与下划线）。"""

    s = str(text).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "dataset"


def _infer_dataset_id(xlsx: Path) -> str:
    # 默认用文件名（去扩展名）作为 dataset_id，避免多次验证互相覆盖输出。
    return _slugify(xlsx.stem)


def _ensure_out_dir(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _constant_curve(v: float) -> PiecewiseLinearCurve:
    return PiecewiseLinearCurve(points=((0.0, float(v)), (1.0, float(v))))


def _estimate_soc0_from_initial_rest(ts, *, batt: BatteryParams1ECM, rest_i_thresh_A: float, window_s: float) -> float:
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


def _simulate_voltage_current_control(ts, *, batt: BatteryParams1ECM, soc0: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """根据配置选择“电流控制 ECM”仿真分支，返回 (soc, v1, h, v_pred)。"""

    r1_curve = batt.r1_curve if batt.r1_curve is not None else _constant_curve(float(batt.r1_ohm))

    if batt.r0_curve is not None:
        soc, v1, h, v_pred = simulate_ecm_current_control_r0_r1_soc(
            soc0=float(soc0),
            v1_0_V=0.0,
            capacity_Ah=float(batt.capacity_Ah),
            ocv=batt.ocv,
            r0_curve=batt.r0_curve,
            c1_F=float(batt.c1_F),
            r1_curve=r1_curve,
            rate_capacity_k_per_A=float(getattr(batt, "rate_capacity_k_per_A", 0.0)),
            ocv_hysteresis_V=float(getattr(batt, "ocv_hysteresis_V", 0.0)),
            ocv_hysteresis_i_thresh_A=float(getattr(batt, "ocv_hysteresis_i_thresh_A", 0.2)),
            hyst_M_V=float(getattr(batt, "hyst_M_V", 0.0)),
            hyst_gamma=float(getattr(batt, "hyst_gamma", 0.0)),
            hyst_i_thresh_A=float(getattr(batt, "hyst_i_thresh_A", 0.05)),
            hyst_M_curve=getattr(batt, "hyst_M_curve", None),
            hyst_relax_tau_s=float(getattr(batt, "hyst_relax_tau_s", 0.0)),
            return_h=True,
            dt_s=np.asarray(ts.dt_s, dtype=float),
            i_A=np.asarray(ts.i_A, dtype=float),
        )
        return soc, v1, h, v_pred

    soc, v1, h, v_pred = simulate_ecm_current_control_r1_soc(
        soc0=float(soc0),
        v1_0_V=0.0,
        capacity_Ah=float(batt.capacity_Ah),
        ocv=batt.ocv,
        r0_ohm=float(batt.r0_ohm),
        c1_F=float(batt.c1_F),
        r1_curve=r1_curve,
        rate_capacity_k_per_A=float(getattr(batt, "rate_capacity_k_per_A", 0.0)),
        ocv_hysteresis_V=float(getattr(batt, "ocv_hysteresis_V", 0.0)),
        ocv_hysteresis_i_thresh_A=float(getattr(batt, "ocv_hysteresis_i_thresh_A", 0.2)),
        hyst_M_V=float(getattr(batt, "hyst_M_V", 0.0)),
        hyst_gamma=float(getattr(batt, "hyst_gamma", 0.0)),
        hyst_i_thresh_A=float(getattr(batt, "hyst_i_thresh_A", 0.05)),
        hyst_M_curve=getattr(batt, "hyst_M_curve", None),
        hyst_relax_tau_s=float(getattr(batt, "hyst_relax_tau_s", 0.0)),
        return_h=True,
        dt_s=np.asarray(ts.dt_s, dtype=float),
        i_A=np.asarray(ts.i_A, dtype=float),
    )
    return soc, v1, h, v_pred


def main() -> int:
    ap = argparse.ArgumentParser(description="验证：CALCE SP20-1 Incremental OCV（Model-1/ECM 电压误差）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（Channel_* 格式）")
    ap.add_argument(
        "--phone",
        action="append",
        default=[],
        help="电池配置 JSON（可重复传入多次用于对比）；留空则使用默认两份配置",
    )
    ap.add_argument(
        "--dataset-id",
        default="",
        help="数据集标识（用于输出目录命名）；留空则根据 xlsx 文件名自动生成",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="误差报表输出目录；留空则写入 src/out_reports/validation/<dataset-id>/",
    )
    ap.add_argument(
        "--plots-dir",
        default=str(SRC_DIR / "out_plots"),
        help="图像输出根目录（默认写入 src/out_plots/model1/{paper|study}/validation/...）",
    )
    ap.add_argument(
        "--no-plots",
        action="store_true",
        help="不生成图像（只输出 JSON 报表）",
    )
    ap.add_argument("--soc0", type=float, default=-1.0, help="初始 SOC；<0 表示用起始休止段电压自动估计")
    ap.add_argument("--rest-i", type=float, default=0.02, help="判定休止段的电流阈值（A）")
    ap.add_argument("--rest-window", type=float, default=600.0, help="估计 SOC0 的起始时间窗（秒）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    dataset_id = str(args.dataset_id).strip() or _infer_dataset_id(xlsx)

    phone_paths = [Path(p).expanduser().resolve() for p in args.phone] if args.phone else _default_phones()
    out_dir = (
        Path(args.out_dir).expanduser().resolve()
        if str(args.out_dir).strip()
        else (SRC_DIR / "out_reports" / "validation" / dataset_id)
    )
    out_dir = _ensure_out_dir(out_dir)

    df = load_calce_channel_xlsx(xlsx)
    ts = extract_channel_time_series(df)
    print("[数据] dataset_id:", dataset_id)
    print("[数据] xlsx:", xlsx)
    print(f"[数据] samples={len(ts.t_s)}  duration≈{(float(ts.t_s[-1]-ts.t_s[0])/3600.0):.2f} h  steps={len(set(int(x) for x in ts.step.tolist()))}")

    # 存下来用于画图
    pred_map: dict[str, dict[str, np.ndarray]] = {}
    v_cut_global: float | None = None

    for phone in phone_paths:
        batt = BatteryParams1ECM.from_json(phone)
        if v_cut_global is None:
            v_cut_global = float(batt.v_cut_V)
        soc0 = float(args.soc0)
        if soc0 < 0:
            soc0 = _estimate_soc0_from_initial_rest(ts, batt=batt, rest_i_thresh_A=float(args.rest_i), window_s=float(args.rest_window))

        soc, v1, h, v_pred = _simulate_voltage_current_control(ts, batt=batt, soc0=soc0)
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
            "report": rep,
        }
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        pred_map[tag] = {
            "v_pred": np.asarray(v_pred, dtype=float),
            "soc": np.asarray(soc, dtype=float),
            "v1": np.asarray(v1, dtype=float),
            "h": np.asarray(h, dtype=float),
        }

        # 控制台摘要
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

    # 图像输出：每个配置单独出一套（paper/study）
    if not args.no_plots and pred_map:
        t_h = (np.asarray(ts.t_s, dtype=float) - float(ts.t_s[0])) / 3600.0
        v_meas = np.asarray(ts.v_V, dtype=float)
        i = np.asarray(ts.i_A, dtype=float)
        steps = np.asarray(ts.step, dtype=int)

        # 下采样：避免 14 万点画图过重（每 10 点取 1 个，约 1.4 万点）
        stride = 10
        idx = np.arange(0, len(t_h), stride, dtype=int)

        root = Path(args.plots_dir).expanduser().resolve()
        v_cut = float(v_cut_global) if v_cut_global is not None else 3.3

        def _first_cut_time_h(v: np.ndarray) -> float | None:
            m = (i >= 0.1) & (v <= v_cut)
            if not bool(np.any(m)):
                return None
            k = int(np.argmax(m))
            return float(t_h[k])

        tte_meas_h = _first_cut_time_h(v_meas)
        for tag, arrs in pred_map.items():
            for mode in ("paper", "study"):
                style = apply_style(mode)  # type: ignore[arg-type]
                out_dir = ensure_dir(root / "model1" / mode / "validation" / dataset_id / tag)

                # 1) 电压时序对比
                fig, ax = plt.subplots(figsize=(10.5, 4.2))
                ax.plot(t_h[idx], v_meas[idx], color="#4C78A8", lw=1.8, label="观测 V")
                ax.plot(t_h[idx], arrs["v_pred"][idx], color="#E45756", lw=1.6, label="模型 V_pred")
                # 截止电压与 TTE（Time-to-Empty）
                ax.axhline(v_cut, color="gray", ls="--", lw=1.0, alpha=0.7, label=f"截止电压 {v_cut:.1f}V")
                tte_pred_h = _first_cut_time_h(np.asarray(arrs["v_pred"], dtype=float))
                if tte_meas_h is not None:
                    ax.axvline(tte_meas_h, color="black", ls=":", lw=1.2, alpha=0.7, label="观测 TTE")
                if tte_pred_h is not None:
                    ax.axvline(tte_pred_h, color="#E45756", ls=":", lw=1.2, alpha=0.7, label="预测 TTE")
                ax.set_xlabel("时间（小时）")
                ax.set_ylabel("电压（V）")
                ax.set_title(f"CALCE Incremental OCV：电压对比（{tag}）{style.title_suffix}")
                ax.legend(frameon=False, loc="best")
                if style.annotate:
                    fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
                    fig.text(
                        0.01,
                        0.02,
                        "术语：\n"
                        "- variants：同一模型结构下的不同“配置/参数版本”（例如不同 R0 曲线），用于做消融与对比。\n"
                        "- TTE（Time-to-Empty）：到“电池空/关机”的剩余时间；本文用端电压跌破截止电压 V_cut 作为判定。\n\n"
                        "读图要点：\n"
                        "- 负载阶跃/脉冲处的“尖峰/跳变”主要由 R0（欧姆内阻）决定；\n"
                        "- 休止段的缓慢回升由 RC 松弛（R1||C1 等极化支路）决定。\n"
                        "若尖峰误差大：优先检查 R0 或 R0(SOC)；若休止段误差大：优先检查时间常数（R1/C1 或增加 2RC）。\n",
                        ha="left",
                        va="bottom",
                        fontsize=9,
                    )
                else:
                    fig.tight_layout()
                savefig(fig, out_dir / "01_voltage_trace.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

                # 2) 残差直方图
                fig, ax = plt.subplots(figsize=(8.0, 4.0))
                r_mV = (arrs["v_pred"] - v_meas) * 1000.0
                ax.hist(r_mV, bins=80, color="#72B7B2", alpha=0.9)
                ax.set_xlabel("残差 r=V_pred−V_meas（mV）")
                ax.set_ylabel("频数")
                ax.set_title(f"残差分布（{tag}）{style.title_suffix}")
                if style.annotate:
                    ax.axvline(float(np.median(r_mV)), color="gray", lw=1.2, ls="--", alpha=0.8)
                fig.tight_layout()
                savefig(fig, out_dir / "02_residual_hist.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

                # 3) 按 step 的 RMSE 条形图（用于定位误差结构）
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
                savefig(fig, out_dir / "03_rmse_by_step.png", mode=mode)  # type: ignore[arg-type]
                plt.close(fig)

        # 4) 多配置对比图：同一张图叠加所有 variants，便于肉眼判断“谁更贴近观测”
        for mode in ("paper", "study"):
            style = apply_style(mode)  # type: ignore[arg-type]
            out_dir = ensure_dir(root / "model1" / mode / "validation" / dataset_id / "__compare__")
            fig, ax = plt.subplots(figsize=(11.2, 4.4))
            ax.plot(t_h[idx], v_meas[idx], color="#4C78A8", lw=2.0, label="观测 V")
            palette = ["#E45756", "#54A24B", "#F58518", "#B279A2", "#72B7B2", "#EECA3B"]
            for j, (tag, arrs) in enumerate(sorted(pred_map.items(), key=lambda kv: kv[0])):
                c = palette[j % len(palette)]
                v_pred = np.asarray(arrs["v_pred"], dtype=float)
                tte_pred_h = _first_cut_time_h(v_pred)
                if tte_meas_h is not None and tte_pred_h is not None:
                    dt_s = (tte_pred_h - tte_meas_h) * 3600.0
                    label = f"{tag}（TTE误差 {dt_s:+.0f}s）"
                else:
                    label = tag
                ax.plot(t_h[idx], v_pred[idx], color=c, lw=1.4, alpha=0.95, label=label)
            ax.axhline(v_cut, color="gray", ls="--", lw=1.0, alpha=0.7, label=f"截止电压 {v_cut:.1f}V")
            if tte_meas_h is not None:
                ax.axvline(tte_meas_h, color="black", ls=":", lw=1.2, alpha=0.7, label="观测 TTE")
            ax.set_xlabel("时间（小时）")
            ax.set_ylabel("电压（V）")
            ax.set_title(f"多 variants 电压对比{style.title_suffix}")
            ax.legend(frameon=False, loc="best", ncols=1)
            if style.annotate:
                fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
                fig.text(
                    0.01,
                    0.02,
                    "说明：本图用于“横向对比多个配置（variants）”。优先观察：\n"
                    "1) 高电流放电段（I>0）瞬时压降是否匹配（主要由 R0/R0(SOC) 决定）；\n"
                    "2) 接近截止电压时，预测 TTE 是否与观测一致（竖虚线）；\n"
                    "3) 休止段电压回升形态是否一致（主要由 RC 松弛决定）。\n",
                    ha="left",
                    va="bottom",
                    fontsize=9,
                )
            else:
                fig.tight_layout()
            savefig(fig, out_dir / "00_voltage_trace_compare.png", mode=mode)  # type: ignore[arg-type]
            plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
