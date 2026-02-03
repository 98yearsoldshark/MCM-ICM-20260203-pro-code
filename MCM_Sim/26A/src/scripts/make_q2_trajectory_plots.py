#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：生成场景轨迹图包（SOC/V/T/P 随时间变化），用于解释“为什么不同场景 TTE 差这么多”。

输出：
- out_plots/q2/{paper|study}/trajectories/{scenario_id}/trace_socXX.png

说明：
- 使用 Model-3 的连续时间仿真轨迹（simulate_model3_aging_trace）。
- 每张图 2x2 面板：SOC(t)、V_term(t)、T(t)、P_total(t)，并标注终止原因与 TTE。
- 学习版（study）会额外解释：虚线/阴影含义、终止机制等。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Scenario, load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging_trace
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _parse_soc_list(s: str) -> list[float]:
    out: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    if not out:
        raise ValueError("soc0-list 不能为空")
    return out


def _segment_spans(sc: Scenario) -> list[tuple[float, float, object]]:
    t = 0.0
    spans: list[tuple[float, float, object]] = []
    for seg in sc.schedule:
        t2 = t + float(seg.duration_s)
        spans.append((t, t2, seg))
        t = t2
    return spans


def _shade_inputs(ax, sc: Scenario) -> None:
    """用浅色阴影标记关键外生输入段（不改变主曲线可读性）。"""

    for t0, t1, seg in _segment_spans(sc):
        # 亮屏段：浅灰
        if bool(getattr(seg, "screen_on", False)):
            ax.axvspan(t0 / 3600.0, t1 / 3600.0, color="#000000", alpha=0.045, lw=0)
        # 弱信号段：浅红叠加（如果存在）
        if str(getattr(seg, "signal_quality", "good")) == "poor":
            ax.axvspan(t0 / 3600.0, t1 / 3600.0, color="#E45756", alpha=0.055, lw=0)


def _plot_one(
    sc: Scenario,
    *,
    soc0: float,
    power1: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    dt_s: float,
    seed: int,
    mode: PlotMode,
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    pm = StatefulPowerModel1(power1, seed=int(seed))

    tr = simulate_model3_aging_trace(
        sc,
        power_params=power0_dummy,
        power_model=pm,
        battery_params=batt,
        soc0=float(soc0),
        dt_s=float(dt_s),
    )

    t_h = np.array(tr.t_s, dtype=float) / 3600.0
    soc_pct = np.array(tr.soc, dtype=float) * 100.0
    v = np.array(tr.v_term_V, dtype=float)
    temp = np.array(tr.temp_C, dtype=float)
    p = np.array(tr.p_W, dtype=float)

    # ---- 派生量：用于解释“为什么 SOC 看起来近似线性 / 极化在图里体现在哪里” ----
    soc = np.array(tr.soc, dtype=float)
    ocv = np.array([float(batt.ocv.ocv_v(float(s))) for s in soc.tolist()], dtype=float)

    # 平滑功率：论文版更“赏心悦目”，学习版保留原始抖动（更能看出随机过程/尾态等机制）
    def _moving_average(x: np.ndarray, win: int) -> np.ndarray:
        if win <= 1 or x.size < 3:
            return x
        w = np.ones(int(win), dtype=float) / float(win)
        return np.convolve(x, w, mode="same")

    # 5 分钟滑动平均（窗口会随 dt 自动变化）
    win = int(max(1, round(300.0 / max(1e-9, float(dt_s)))))
    p_smooth = _moving_average(p, win=win)

    tte_h = float(t_h[-1]) if t_h.size else float("nan")
    status = str(tr.status)

    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(11.8, 7.0))
    ax_soc, ax_v = axes[0]
    ax_t, ax_p = axes[1]

    for ax in (ax_soc, ax_v, ax_t, ax_p):
        _shade_inputs(ax, sc)
        # 段边界：轻微竖线（不抢眼）
        for t0, t1, _seg in _segment_spans(sc):
            ax.axvline(t0 / 3600.0, color="#000000", alpha=0.04, lw=0.8)

    ax_soc.plot(t_h, soc_pct, color="#4C78A8", lw=2.0, label="SOC（库仑计数）")
    # 线性参考线：等效“恒流”下 SOC 应该是严格线性的；CPL 下真实 SOC 会偏离该直线
    if t_h.size >= 2:
        soc_lin = np.linspace(float(soc_pct[0]), float(soc_pct[-1]), int(t_h.size))
        ax_soc.plot(t_h, soc_lin, color="#999999", lw=1.6, linestyle="--", alpha=0.9, label="线性参考（等效恒流）")
    # 学习版额外画“剩余能量百分比”（SoE），用于解释“为何手机电量/体感不是线性”的直觉
    if style.annotate:
        # SoE(soc) ∝ ∫_0^soc OCV(u) du（以 OCV 曲线近似电池可用能量密度）
        pts = list(batt.ocv.points)
        def _ocv_int(s: float) -> float:
            s = float(max(0.0, min(1.0, s)))
            acc = 0.0
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                if s <= x0:
                    break
                a = x0
                b = min(x1, s)
                if b <= a:
                    continue
                # 线性插值下的梯形积分
                # y(x)=y0 + (y1-y0)*(x-x0)/(x1-x0)
                ya = y0 + (y1 - y0) * (a - x0) / (x1 - x0) if x1 != x0 else y0
                yb = y0 + (y1 - y0) * (b - x0) / (x1 - x0) if x1 != x0 else y0
                acc += 0.5 * (ya + yb) * (b - a)
            return float(acc)

        e1 = _ocv_int(1.0)
        soe_pct = np.array([(_ocv_int(float(s)) / e1 * 100.0) if e1 > 1e-12 else float("nan") for s in soc.tolist()], dtype=float)
        ax_soc.plot(t_h, soe_pct, color="#333333", lw=1.6, linestyle=":", alpha=0.85, label="SoE（剩余能量%）")
    ax_soc.set_xlabel("时间（小时）")
    ax_soc.set_ylabel("SOC（%）")
    ax_soc.set_title("SOC(t)")
    if style.annotate:
        ax_soc.legend(frameon=False, fontsize=9, loc="upper right")

    ax_v.plot(t_h, v, color="#E45756", lw=2.0, label="V_term（端电压）")
    # OCV 线：帮助理解“极化/内阻压降”= OCV - V_term
    ax_v.plot(t_h, ocv, color="#555555", lw=1.4, linestyle="--", alpha=0.65, label="OCV（开路电压）")
    ax_v.axhline(float(batt.v_cut_V), color="#333333", lw=1.2, linestyle="--", alpha=0.7)
    ax_v.set_xlabel("时间（小时）")
    ax_v.set_ylabel("端电压 V_term（V）")
    ax_v.set_title("V_term(t)")
    if style.annotate:
        ax_v.legend(frameon=False, fontsize=9, loc="upper right")

    ax_t.plot(t_h, temp, color="#54A24B", lw=2.0)
    ax_t.set_xlabel("时间（小时）")
    ax_t.set_ylabel("温度（°C）")
    ax_t.set_title("T(t)")

    if style.annotate:
        ax_p.plot(t_h, p, color="#845EC2", lw=1.0, alpha=0.30, label="P_total 原始")
        ax_p.plot(t_h, p_smooth, color="#845EC2", lw=2.2, alpha=0.95, label=f"P_total 平滑（≈{int(round(win*dt_s))}s窗）")
        ax_p.legend(frameon=False, fontsize=9, loc="upper right")
    else:
        # 论文版：只画平滑曲线（更清爽/更美观），但本质仍是同一次仿真的轨迹
        ax_p.plot(t_h, p_smooth, color="#845EC2", lw=2.2, alpha=0.95)
    ax_p.set_xlabel("时间（小时）")
    ax_p.set_ylabel("总功耗 P_total（W）")
    ax_p.set_title("P_total(t)")

    # TTE 竖线（命中点）
    for ax in (ax_soc, ax_v, ax_t, ax_p):
        ax.axvline(tte_h, color="#111111", lw=1.2, alpha=0.55)

    title = f"{sc.title_zh} | soc0={soc0:.2f} | TTE={tte_h:.2f}h | status={status}{style.title_suffix}"
    fig.suptitle(title, y=0.995, fontsize=12)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.95))
        fig.text(
            0.02,
            0.02,
            "标注说明：\n"
            "- 黑色竖线：TTE（首次终止时刻）。\n"
            "- V_term 子图黑色虚线：截止电压 V_cut（触发欠压关机）。\n"
            "- V_term 子图灰色虚线：OCV（开路电压）；OCV 与 V_term 的差值对应内阻压降 + 极化压降。\n"
            "- SOC 子图灰色虚线：等效恒流（线性 SOC）参考线；用于对比 CPL 下 SOC 的非线性。\n"
            "- 灰色阴影：亮屏段；红色浅阴影：弱信号段（若场景中存在）。\n"
            "- 终止原因 status：cutoff=欠压；soc_min=电量下限；insufficient_power=功率不可行（Δ<0）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.95))

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 轨迹图包（paper/study）")
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"), help="输出图像根目录（默认 out_plots/q2）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（Model-3）",
    )
    ap.add_argument("--dt", type=float, default=5.0, help="积分步长（秒），默认 5s（更平滑；终稿建议 2~5s）")
    ap.add_argument("--soc0-list", default="1.0,0.75,0.5,0.25", help="SOC0 列表（逗号分隔）")
    ap.add_argument("--seed", type=int, default=1, help="功耗随机种子（固定代表性轨迹）")
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    out_root = Path(args.out_plots)
    raw = load_scenarios_json(args.scenarios)

    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))

    soc0_list = _parse_soc_list(str(args.soc0_list))
    dt_s = float(args.dt)

    scenario_ids = list(raw.get("scenarios", {}).keys())
    scenario_ids.sort()

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for mode in modes:
        out_dir = ensure_dir(out_root / str(mode) / "trajectories")
        for sid in scenario_ids:
            sc = materialize_scenario(raw, sid)
            for soc0 in soc0_list:
                tag = f"soc{int(round(float(soc0) * 100)):03d}"
                out_path = out_dir / str(sid) / f"trace_{tag}.png"
                _plot_one(
                    sc,
                    soc0=float(soc0),
                    power1=power1,
                    batt=batt,
                    dt_s=dt_s,
                    seed=int(args.seed),
                    mode=mode,  # type: ignore[arg-type]
                    out_path=out_path,
                )
        print(f"[{mode}] trajectories -> {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
