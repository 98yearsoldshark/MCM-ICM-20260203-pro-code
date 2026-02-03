#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 观测对照（长时间/TTE 层面）：用 user_behavior_dataset.csv 做“日耗电→TTE”的粗对齐。

输出：
- out_reports/q2/validation_user_behavior/
  - users.csv：逐用户的日耗电与等效 TTE（小时，含 daily 与 active 两种口径）
  - summary_by_class.csv：按 User Behavior Class 的分位数统计
  - scenario_tte_pred.csv：模型在若干代表性场景下的预测 TTE（小时）
- out_plots/q2/{paper|study}/observed_user_behavior/
  - 01_tte_hist_overlay.png：观测 TTE 分布（active 口径） + 模型场景 TTE 叠加
  - 03_tte_hist_overlay_daily.png：观测 TTE 分布（daily 口径） + 模型场景 TTE 叠加（辅助理解，不建议放正文）
  - 02_tte_by_class_box.png：按行为类别的观测 TTE 箱线图

说明：
- user_behavior_dataset 是“按天汇总”的用户级统计，不含连续时间轨迹；
  因此这里只做“续航量级与范围”的对照，作为赛题允许的公开证据补充。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _tight_text(s: str) -> str:
    """用于图中文字：中文括号->英文括号，并去掉空格，节省版面。"""

    s = str(s)
    # 中文括号 -> 英文括号
    s = s.replace("（", "(").replace("）", ")")
    # 常见连接符周围的空格（最后统一去空格，但保留这里便于扩展）
    s = s.replace(" vs ", "vs")
    # 去空格（中文论文图通常不需要空格）
    s = s.replace(" ", "")
    return s


def _scenario_title_local(scenario_id: str, title_zh: str, *, lang: str) -> str:
    """局部英文翻译：仅覆盖本图会出现的少量场景，避免引入大规模翻译依赖。"""

    if lang != "en":
        return title_zh

    mapping = {
        "S0_standby": "Standby/lightBG",
        "S4_mixed_day": "Mixedday(standard)",
        "S1_video": "Video(stream)",
        "S2_navigation": "Navigation(GPS+map)",
        "S3_gaming": "Gaming(highCPU/GPU)",
    }
    return mapping.get(str(scenario_id), title_zh)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _q(arr: list[float], q: float) -> float:
    if not arr:
        return float("nan")
    return float(np.quantile(np.array(arr, dtype=float), q))


def _predict_tte_for_scenarios(
    raw: dict,
    *,
    scenario_ids: list[str],
    power: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    dt_s: float,
    soc0: float,
    seeds: int,
    seed0: int,
) -> list[dict[str, object]]:
    """对少量代表性场景做“平均 TTE（小时）”预测，用于叠加对照。"""

    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")
    out: list[dict[str, object]] = []
    for sid in scenario_ids:
        sc = materialize_scenario(raw, sid)
        ttes: list[float] = []
        for k in range(int(seeds)):
            pm = StatefulPowerModel1(power, seed=int(seed0) + k)
            res = simulate_model3_aging(sc, power_params=power0_dummy, power_model=pm, battery_params=batt, soc0=float(soc0), dt_s=float(dt_s))
            if res.tte_h is not None:
                ttes.append(float(res.tte_h))
        out.append(
            {
                "scenario_id": sid,
                "title_zh": str(raw.get("scenarios", {}).get(sid, {}).get("title_zh", sid)),
                "n": int(len(ttes)),
                "tte_mean_h": float(np.mean(np.array(ttes, dtype=float))) if ttes else float("nan"),
                "tte_p05_h": _q(ttes, 0.05),
                "tte_p50_h": _q(ttes, 0.50),
                "tte_p95_h": _q(ttes, 0.95),
            }
        )
    return out


def _plot_hist_overlay(
    obs_tte_h: list[float],
    *,
    scenario_rows: list[dict[str, object]],
    obs_label: str,
    title_zh: str,
    explain_text: str,
    mode: PlotMode,
    lang: str,
):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    obs_label = _tight_text(obs_label)
    title_zh = _tight_text(title_zh)

    arr = np.array(obs_tte_h, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size <= 0:
        raise ValueError("观测 TTE 为空，无法绘图（请检查 user_behavior_dataset.csv 解析是否成功）")
    # 观测统计：均值/中位数（注意：daily 口径通常重尾，均值会被长尾拉大；学习版会显示数值）。
    obs_mean = float(np.mean(arr))
    obs_med = float(np.median(arr))
    arr_sorted = np.sort(arr)

    def _pct(x: float) -> float:
        """返回 x 在观测分布中的经验分位（0~1）。"""
        if not np.isfinite(x) or arr_sorted.size <= 0:
            return float("nan")
        # 用 <= 的经验累计分布（ECDF），更符合“落在分布的哪一侧”直觉。
        return float(np.mean(arr_sorted <= float(x)))

    def _fmt_pct(pct: float) -> str:
        """把经验分位（0~1）格式化成更直观的百分比字符串。"""
        if not np.isfinite(pct):
            return ""
        if pct < 0.01:
            return "<1%"
        if pct > 0.99:
            return ">99%"
        return f"{pct*100:.0f}%"

    # 双面板：左侧展示全范围分布；右侧放大左端区间，避免“模型场景线挤在一起看不清”。（更适合论文排版）
    # 左右交换：把 zoom 放左侧，把 full 放右侧（用户要求）
    # 缩短竖直方向：调小高度，让 y 轴刻度之间的像素间距更紧凑（用户要求）。
    fig_h = 3.2 if mode == "paper" else 3.8
    fig, (ax_zoom, ax_full) = plt.subplots(
        ncols=2,
        figsize=(11.2, fig_h),
        gridspec_kw={"width_ratios": [1.2, 2.2]},
        sharey=True,
    )

    bins = np.histogram_bin_edges(arr, bins=40)
    hist_kws = dict(bins=bins, color="#4C78A8", alpha=0.70, density=True)
    ax_full.hist(arr, **hist_kws, label=str(obs_label))
    ax_zoom.hist(arr, **hist_kws)

    for ax in (ax_full, ax_zoom):
        if lang == "en":
            ax.set_xlabel(_tight_text("EquivalentTTE(h)"))
            ax.set_ylabel(_tight_text("Density"))
        else:
            ax.set_xlabel(_tight_text("等效耗尽时间TTE(小时)"))
            ax.set_ylabel("概率密度")

    ax_full.set_title(f"{title_zh}{style.title_suffix}")
    ax_full.set_xlim(0.0, float(np.max(arr)) * 1.02)

    # 顶部辅轴：把“小时”映射到“观测分位（0~100%）”，方便读者快速判断落点属于分布的哪一段。
    # 注：这是经验分位（ECDF），不是线性刻度。
    n_arr = int(arr_sorted.size)

    def _x_to_pct_axis(x):
        x = np.asarray(x, dtype=float)
        return 100.0 * np.searchsorted(arr_sorted, x, side="right") / float(max(1, n_arr))

    def _pct_to_x_axis(p):
        p = np.asarray(p, dtype=float)
        p = np.clip(p, 0.0, 100.0) / 100.0
        return np.quantile(arr_sorted, p)

    try:
        sec = ax_full.secondary_xaxis("top", functions=(_x_to_pct_axis, _pct_to_x_axis))
        sec.set_xlabel(_tight_text("ObservedPercentile(%)") if lang == "en" else "观测分位(%)")
        # 非线性分位轴：0/25/50 往往挤在左侧，为避免重叠，这里仅保留 0/50/100
        sec.set_xticks([0, 50, 100])
        sec.set_xticklabels(["0%", "50%", "100%"])
    except Exception:
        # 兼容旧 matplotlib：没有 secondary_xaxis 时忽略（不影响主图生成）
        pass

    # 右侧放大范围：覆盖“模型场景预测落点”+ 一部分观测左侧（便于视觉对照）
    max_scn = max([float(r.get("tte_p95_h", float("nan"))) for r in scenario_rows] + [0.0])
    # 放大图用于“看清模型竖线落点”，不要把横轴拉太长导致直方图被压扁。
    # 经验上 2×max_scn 足以覆盖均值线与（学习版）90% 区间带。
    zoom_max = max(10.0, max_scn * 2.0)
    ax_zoom.set_xlim(0.0, zoom_max)
    ax_zoom.set_title(_tight_text("Zoom:LowTTE(ScenarioAnchors)") if lang == "en" else "放大:低TTE区间(模型场景落点)")

    # 在全范围图左上角放一个简短口径说明（active vs daily），避免读者误解
    ax_full.text(
        0.02,
        0.96,
        str(obs_label),
        transform=ax_full.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
    )

    # 叠加“观测摘要线”：均值/中位数（用于把“人群分布”与“代表性场景”放在同一量级上对照）
    # 说明：daily 口径一般是重尾分布，均值不一定代表“最典型”的用户；因此同时给出中位数。
    for ax in (ax_full, ax_zoom):
        ax.axvline(obs_med, color="#222222", lw=1.3, alpha=0.85)
        ax.axvline(obs_mean, color="#222222", lw=1.1, alpha=0.65, ls="--")

    # 叠加模型场景：用“均值线 +（学习版）90% 区间带”替代直立文字，避免遮挡与拥挤。
    palette = ["#E45756", "#F58518", "#54A24B", "#72B7B2", "#B279A2", "#FF9DA6"]
    handles = []
    labels = []

    # 观测摘要线也放进图例（放在第一个，便于读者快速识别）
    handles.append(plt.Line2D([0], [0], color="#222222", lw=2.0))
    if style.annotate:
        labels.append(_tight_text(f"ObsMedian({obs_med:.1f}h)") if lang == "en" else _tight_text(f"观测中位数({obs_med:.1f}h)"))
    else:
        labels.append(_tight_text("ObsMedian") if lang == "en" else _tight_text("观测中位数"))

    handles.append(plt.Line2D([0], [0], color="#222222", lw=1.8, ls="--"))
    if style.annotate:
        labels.append(_tight_text(f"ObsMean({obs_mean:.1f}h)") if lang == "en" else _tight_text(f"观测均值({obs_mean:.1f}h)"))
    else:
        labels.append(_tight_text("ObsMean") if lang == "en" else _tight_text("观测均值"))

    for i, r in enumerate(scenario_rows):
        t = float(r.get("tte_mean_h", float("nan")))
        if not np.isfinite(t):
            continue
        pct = _pct(t)
        lo = float(r.get("tte_p05_h", float("nan")))
        hi = float(r.get("tte_p95_h", float("nan")))
        name_zh = str(r.get("title_zh", r.get("scenario_id", "?")))
        name = _tight_text(_scenario_title_local(str(r.get("scenario_id", "")), name_zh, lang=lang))
        c = palette[i % len(palette)]

        if style.annotate and np.isfinite(lo) and np.isfinite(hi) and hi >= lo:
            ax_zoom.axvspan(lo, hi, color=c, alpha=0.10, lw=0)
        ax_zoom.axvline(t, color=c, lw=1.8, alpha=0.95)
        # 全范围图也画一条细线，让读者知道“模型落在分布左侧”（不抢视觉注意力）
        ax_full.axvline(t, color=c, lw=0.9, alpha=0.45)

        handles.append(plt.Line2D([0], [0], color=c, lw=2.2))
        if style.annotate:
            if np.isfinite(pct):
                labels.append(_tight_text(f"{name}(均值{t:.1f}h,{_fmt_pct(pct)})"))
            else:
                labels.append(_tight_text(f"{name}(均值{t:.1f}h)"))
        else:
            if np.isfinite(pct):
                labels.append(_tight_text(f"{name}({_fmt_pct(pct)})"))
            else:
                labels.append(_tight_text(name))

    if handles:
        # 右上角图例位置不变：放到右侧子图（full 面板）右上角
        ax_full.legend(handles, labels, frameon=False, loc="upper right", fontsize=9)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98), pad=0.35)
        fig.text(
            0.02,
            0.02,
            str(explain_text),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(pad=0.35)
    return fig


def _plot_drain_hist_overlay(
    drain_mAh_day: list[float],
    *,
    scenario_rows: list[dict[str, object]],
    cap_mAh: float,
    title_zh: str,
    explain_text: str,
    mode: PlotMode,
    lang: str,
):
    """对照“日耗电量”的分布：更物理、也更便于解释 daily TTE 的来源。"""

    import matplotlib.pyplot as plt

    style = apply_style(mode)

    title_zh = _tight_text(title_zh)

    arr = np.array(drain_mAh_day, dtype=float)
    arr = arr[np.isfinite(arr)]
    arr = arr[arr > 0]
    if arr.size <= 0:
        raise ValueError("日耗电（mAh/day）为空，无法绘图")

    obs_mean = float(np.mean(arr))
    obs_med = float(np.median(arr))
    arr_sorted = np.sort(arr)

    def _pct(x: float) -> float:
        if not np.isfinite(x) or arr_sorted.size <= 0:
            return float("nan")
        return float(np.mean(arr_sorted <= float(x)))

    def _fmt_pct(pct: float) -> str:
        if not np.isfinite(pct):
            return ""
        if pct < 0.01:
            return "<1%"
        if pct > 0.99:
            return ">99%"
        return f"{pct*100:.0f}%"

    # 左右交换：zoom 左，full 右
    fig_h = 3.2 if mode == "paper" else 3.8
    fig, (ax_zoom, ax_full) = plt.subplots(
        ncols=2,
        figsize=(11.2, fig_h),
        gridspec_kw={"width_ratios": [1.2, 2.2]},
        sharey=True,
    )

    bins = np.histogram_bin_edges(arr, bins=40)
    hist_kws = dict(bins=bins, color="#4C78A8", alpha=0.70, density=True)
    ax_full.hist(arr, **hist_kws, label=_tight_text("Obs:DailyDrain(mAh/day)") if lang == "en" else _tight_text("观测:日耗电分布(mAh/day)"))
    ax_zoom.hist(arr, **hist_kws)

    for ax in (ax_full, ax_zoom):
        if lang == "en":
            ax.set_xlabel(_tight_text("DailyDrain(mAh/day)"))
            ax.set_ylabel(_tight_text("Density"))
        else:
            ax.set_xlabel(_tight_text("日耗电量(mAh/day)"))
            ax.set_ylabel("概率密度")
        ax.axvline(obs_med, color="#222222", lw=1.3, alpha=0.85)
        ax.axvline(obs_mean, color="#222222", lw=1.1, alpha=0.65, ls="--")

    ax_full.set_title(f"{title_zh}{style.title_suffix}")
    ax_full.set_xlim(0.0, float(np.max(arr)) * 1.02)

    # 顶部辅轴：把“日耗电(mAh/day)”映射到“观测分位（0~100%）”
    n_arr = int(arr_sorted.size)

    def _x_to_pct_axis(x):
        x = np.asarray(x, dtype=float)
        return 100.0 * np.searchsorted(arr_sorted, x, side="right") / float(max(1, n_arr))

    def _pct_to_x_axis(p):
        p = np.asarray(p, dtype=float)
        p = np.clip(p, 0.0, 100.0) / 100.0
        return np.quantile(arr_sorted, p)

    try:
        sec = ax_full.secondary_xaxis("top", functions=(_x_to_pct_axis, _pct_to_x_axis))
        sec.set_xlabel(_tight_text("ObservedPercentile(%)") if lang == "en" else "观测分位(%)")
        sec.set_xticks([0, 50, 100])
        sec.set_xticklabels(["0%", "50%", "100%"])
    except Exception:
        pass

    # 放大：优先覆盖场景落点附近（便于读者一眼看到“我们在哪个强度分位”）
    # 经验：把 zoom_max 设为 max(观测 P95, 场景最大隐含耗电) 的 1.1 倍。
    scen_drains = []
    for r in scenario_rows:
        tte_h = float(r.get("tte_mean_h", float("nan")))
        if np.isfinite(tte_h) and tte_h > 1e-9:
            scen_drains.append(float(cap_mAh * 24.0 / tte_h))
    zoom_max = float(max(np.quantile(arr, 0.95), max(scen_drains) if scen_drains else 0.0) * 1.10)
    ax_zoom.set_xlim(0.0, max(1000.0, zoom_max))
    ax_zoom.set_title(_tight_text("Zoom:MainDensity(ScenarioAnchors)") if lang == "en" else _tight_text("放大:主密度区间(场景落点)"))

    palette = ["#E45756", "#F58518", "#54A24B", "#72B7B2", "#B279A2", "#FF9DA6"]
    handles = [
        plt.Line2D([0], [0], color="#222222", lw=2.0),
        plt.Line2D([0], [0], color="#222222", lw=1.8, ls="--"),
    ]
    if style.annotate:
        labels = [
            _tight_text(f"ObsMedian({obs_med:.0f})") if lang == "en" else _tight_text(f"观测中位数({obs_med:.0f})"),
            _tight_text(f"ObsMean({obs_mean:.0f})") if lang == "en" else _tight_text(f"观测均值({obs_mean:.0f})"),
        ]
    else:
        labels = [_tight_text("ObsMedian") if lang == "en" else _tight_text("观测中位数"), _tight_text("ObsMean") if lang == "en" else _tight_text("观测均值")]

    for i, r in enumerate(scenario_rows):
        tte_h = float(r.get("tte_mean_h", float("nan")))
        if not np.isfinite(tte_h) or tte_h <= 1e-9:
            continue
        drain = float(cap_mAh * 24.0 / tte_h)
        pct = _pct(drain)
        name_zh = str(r.get("title_zh", r.get("scenario_id", "?")))
        name = _tight_text(_scenario_title_local(str(r.get("scenario_id", "")), name_zh, lang=lang))
        c = palette[i % len(palette)]
        ax_zoom.axvline(drain, color=c, lw=1.9, alpha=0.95)
        ax_full.axvline(drain, color=c, lw=0.9, alpha=0.45)

        handles.append(plt.Line2D([0], [0], color=c, lw=2.2))
        if style.annotate:
            if np.isfinite(pct):
                labels.append(_tight_text(f"{name}(隐含{drain:.0f},{_fmt_pct(pct)})"))
            else:
                labels.append(_tight_text(f"{name}(隐含{drain:.0f})"))
        else:
            if np.isfinite(pct):
                labels.append(_tight_text(f"{name}({_fmt_pct(pct)})"))
            else:
                labels.append(_tight_text(name))

    ax_zoom.legend(handles, labels, frameon=False, loc="upper right", fontsize=9)
    # 右上角图例不变：放到右侧子图（full 面板）右上角
    try:
        ax_zoom.get_legend().remove()
    except Exception:
        pass
    ax_full.legend(handles, labels, frameon=False, loc="upper right", fontsize=9)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98), pad=0.35)
        fig.text(0.02, 0.02, str(explain_text), ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout(pad=0.35)
    return fig


def _plot_box_by_class(
    rows: list[dict[str, object]],
    *,
    mode: PlotMode,
):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    by_class: dict[int, list[float]] = {}
    for r in rows:
        try:
            c = int(float(r.get("class", "nan")))
        except Exception:
            continue
        try:
            # 兼容旧字段：tte_est_h（历史版本） / tte_est_daily_h（当前版本）
            t = float(r.get("tte_est_daily_h", r.get("tte_est_h", "nan")))
        except Exception:
            continue
        if not np.isfinite(t):
            continue
        by_class.setdefault(c, []).append(float(t))

    classes = sorted(by_class.keys())
    data = [by_class[c] for c in classes]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    # matplotlib>=3.9: labels->tick_labels；为兼容旧版本做 try/except
    try:
        ax.boxplot(data, tick_labels=[str(c) for c in classes], showfliers=False)
    except TypeError:
        ax.boxplot(data, labels=[str(c) for c in classes], showfliers=False)
    ax.set_xlabel("User Behavior Class（观测标签）")
    ax.set_ylabel("等效耗尽时间 TTE（小时）")
    ax.set_title(f"观测：按用户行为类别的等效 TTE 分布{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：类别数字来自数据集（并非本模型输出）。\n"
            "可把该分布用于定义“轻/中/重度用户”的续航范围，从而构造更贴近现实的 Q2 场景集。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 长时间/TTE 观测对照（user_behavior_dataset）")
    ap.add_argument(
        "--data",
        default=str(SRC_DIR.parent / "data" / "SmartphoneMeasurements" / "user_behavior_dataset.csv"),
        help="user_behavior_dataset.csv 路径",
    )
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON 路径",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON 路径（no7 升级 + AndroWatts 多目标校准版）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（用于容量换算）",
    )
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "validation_user_behavior"))
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"))
    ap.add_argument("--dt", type=float, default=60.0, help="仿真积分步长（秒），长时间对照建议 30~120")
    ap.add_argument("--soc0", type=float, default=1.0, help="预测场景使用的初始 SOC（默认 1）")
    ap.add_argument("--seeds", type=int, default=10, help="每个场景重复的随机种子数（越大越稳）")
    ap.add_argument("--mode", default="paper", help="paper 或 study")
    ap.add_argument("--tag", default="", help="输出文件名后缀（例如 v2），用于生成新图而不覆盖旧图")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"], help="图中文字语言：zh 或 en")
    args = ap.parse_args()

    mode: PlotMode = str(args.mode)
    out_reports = ensure_dir(Path(args.out_reports))
    out_plots = ensure_dir(Path(args.out_plots) / str(mode) / "observed_user_behavior")
    tag = str(args.tag).strip()
    suffix = "" if not tag else f"_{tag}"
    lang = str(args.lang).strip().lower() or "zh"

    rows0 = _read_csv_rows(Path(args.data))
    batt = BatteryParams3Aging.from_json(Path(args.phone))
    cap_mAh = float(batt.capacity_Ah_ref) * 1000.0

    # 逐用户：日耗电 -> 等效 TTE
    users: list[dict[str, object]] = []
    obs_drain_mAh_day: list[float] = []
    obs_tte_daily_h: list[float] = []
    obs_tte_active_h: list[float] = []
    for r in rows0:
        try:
            drain = float(r.get("Battery Drain (mAh/day)", "nan"))
        except Exception:
            drain = float("nan")

        try:
            screen_on_h = float(r.get("Screen On Time (hours/day)", "nan"))
        except Exception:
            screen_on_h = float("nan")

        try:
            data_mb_day = float(r.get("Data Usage (MB/day)", "nan"))
        except Exception:
            data_mb_day = float("nan")

        # daily：用“日均消耗持续不变”换算，偏向 long-horizon（包含大量 idle 时间）
        tte_daily = float("nan") if (not np.isfinite(drain) or drain <= 0) else float(cap_mAh / drain * 24.0)
        # active：用“活跃强度”换算（只按亮屏时间归一），更接近“连续使用直到耗尽”的口径
        tte_active = float("nan")
        if np.isfinite(drain) and drain > 0 and np.isfinite(screen_on_h) and screen_on_h > 1e-9:
            tte_active = float(cap_mAh * screen_on_h / drain)

        obs_tte_daily_h.append(float(tte_daily))
        obs_tte_active_h.append(float(tte_active))
        obs_drain_mAh_day.append(float(drain))
        users.append(
            {
                "user_id": int(float(r.get("User ID", "nan"))) if r.get("User ID") else "",
                "class": r.get("User Behavior Class", ""),
                "screen_on_h_day": float(screen_on_h) if np.isfinite(screen_on_h) else "",
                "data_mb_day": float(data_mb_day) if np.isfinite(data_mb_day) else "",
                "drain_mAh_day": drain,
                "tte_est_daily_h": float(tte_daily) if np.isfinite(tte_daily) else "",
                "tte_est_active_h": float(tte_active) if np.isfinite(tte_active) else "",
            }
        )

    _write_csv(
        out_reports / "users.csv",
        users,
        fieldnames=["user_id", "class", "screen_on_h_day", "data_mb_day", "drain_mAh_day", "tte_est_daily_h", "tte_est_active_h"],
    )

    # 按 class 汇总（分位数）
    by_class: dict[str, list[float]] = {}
    for u in users:
        c = str(u.get("class", "")).strip()
        t = float(u.get("tte_est_daily_h", float("nan")))
        if not c:
            continue
        if not np.isfinite(t):
            continue
        by_class.setdefault(c, []).append(float(t))
    summary = []
    for c in sorted(by_class.keys(), key=lambda x: float(x) if x.replace(".", "", 1).isdigit() else x):
        xs = by_class[c]
        summary.append(
            {
                "class": c,
                "n": int(len(xs)),
                "p05_h": _q(xs, 0.05),
                "p50_h": _q(xs, 0.50),
                "p95_h": _q(xs, 0.95),
                "mean_h": float(np.mean(np.array(xs, dtype=float))) if xs else float("nan"),
            }
        )
    _write_csv(out_reports / "summary_by_class.csv", summary, fieldnames=["class", "n", "p05_h", "p50_h", "p95_h", "mean_h"])

    # 预测：选少量“代表性场景”叠加在图上
    raw = load_scenarios_json(Path(args.scenarios))
    power = PowerParams1Stateful.from_json(Path(args.power))

    # active 口径（连续活跃强度）更适合与“连续使用型场景”对照：视频/导航/游戏
    scenario_ids_active = ["S1_video", "S2_navigation", "S3_gaming"]
    pred_rows_active = _predict_tte_for_scenarios(
        raw,
        scenario_ids=scenario_ids_active,
        power=power,
        batt=batt,
        dt_s=float(args.dt),
        soc0=float(args.soc0),
        seeds=int(args.seeds),
        seed0=12345,
    )
    _write_csv(
        out_reports / "scenario_tte_pred.csv",
        pred_rows_active,
        fieldnames=["scenario_id", "title_zh", "n", "tte_mean_h", "tte_p05_h", "tte_p50_h", "tte_p95_h"],
    )

    # daily 口径更适合与“包含大量 idle 的日常场景”对照：待机/混合一天
    scenario_ids_daily = ["S0_standby", "S4_mixed_day"]
    pred_rows_daily = _predict_tte_for_scenarios(
        raw,
        scenario_ids=scenario_ids_daily,
        power=power,
        batt=batt,
        dt_s=float(args.dt),
        soc0=float(args.soc0),
        seeds=int(args.seeds),
        seed0=23456,
    )
    _write_csv(
        out_reports / "scenario_tte_pred_daily.csv",
        pred_rows_daily,
        fieldnames=["scenario_id", "title_zh", "n", "tte_mean_h", "tte_p05_h", "tte_p50_h", "tte_p95_h"],
    )

    # 画图
    fig1 = _plot_hist_overlay(
        obs_tte_active_h,
        scenario_rows=pred_rows_active,
        obs_label=("Obs(active):screen-onnormalized->equivTTE" if lang == "en" else "观测分布（active 口径：按亮屏时间归一→等效 TTE）"),
        title_zh=("Long-horizon/TTE(active):UserDistributionvsContinuousScenarios" if lang == "en" else "长时间/TTE 对照（active 口径）：用户级观测分布 vs 连续使用型场景"),
        explain_text=(
            "说明：user_behavior_dataset.csv 是“按天汇总”的用户级统计。\n"
            "为更接近赛题 Q2 的‘连续使用直到耗尽’口径，我们构造 active 等效续航：\n"
            "  TTE_active_equiv = 容量(mAh) × ScreenOn(h/day) / 日耗电(mAh/day)。\n"
            "它刻画的是‘用户活跃使用强度’而非‘一天的平均强度’，因此能与本题的场景化连续使用 TTE 更可比。\n"
            "图右侧放大的是低 TTE 区间，便于对照模型场景落点。\n"
            "该对照用于校验续航量级与范围，并不替代连续时间 SOC(t) 轨迹的观测验证。"
        ),
        mode=mode,
        lang=lang,
    )
    if suffix:
        # 有 tag 时：只生成新文件名，避免覆盖旧图（便于人工对比）
        savefig(fig1, out_plots / f"01_tte_hist_overlay{suffix}.png", mode=mode)
    else:
        savefig(fig1, out_plots / "01_tte_hist_overlay.png", mode=mode)
    import matplotlib.pyplot as plt

    plt.close(fig1)

    # 额外输出：daily 口径（用于解释为何“日均等效 TTE”可能远大于连续使用场景）
    fig1b = _plot_hist_overlay(
        obs_tte_daily_h,
        scenario_rows=pred_rows_daily,
        obs_label=("Obs(daily):dailyconsumption->equivTTE" if lang == "en" else "观测分布（daily 口径：日均耗电→等效 TTE）"),
        title_zh=("Long-horizon/TTE(daily):UserDistributionvsDailyScenarios(standby/mixed)" if lang == "en" else "长时间/TTE 对照（daily 口径）：用户级观测分布 vs 日常场景（待机/混合）"),
        explain_text=(
            "说明：daily 等效续航把‘日均耗电持续不变’当作假设：\n"
            "  TTE_daily_equiv = 容量(mAh) / 日耗电(mAh/day) × 24h。\n"
            "由于一天中包含大量 idle/熄屏时间，TTE_daily_equiv 往往显著大于‘连续高强度使用直到耗尽’。\n"
            "因此该图更适合作为 long-horizon plausible behavior 的辅助证据，不建议与连续场景 TTE 做严格数值对齐。",
        ),
        mode=mode,
        lang=lang,
    )
    if suffix:
        savefig(fig1b, out_plots / f"03_tte_hist_overlay_daily{suffix}.png", mode=mode)
    else:
        savefig(fig1b, out_plots / "03_tte_hist_overlay_daily.png", mode=mode)
    plt.close(fig1b)

    fig2 = _plot_box_by_class(users, mode=mode)
    if suffix:
        savefig(fig2, out_plots / f"02_tte_by_class_box{suffix}.png", mode=mode)
    else:
        savefig(fig2, out_plots / "02_tte_by_class_box.png", mode=mode)
    plt.close(fig2)

    # 额外：把 daily 口径在“日耗电量”域里再对照一次（更物理、更好解释）
    fig3 = _plot_drain_hist_overlay(
        obs_drain_mAh_day,
        scenario_rows=pred_rows_daily,
        cap_mAh=cap_mAh,
        title_zh=("ObsCompare(daily):DrainDistributionvsScenarioImpliedDrain" if lang == "en" else "观测对照（daily）：日耗电分布 vs 场景隐含日耗电"),
        explain_text=(
            "说明：daily 等效续航 TTE_daily_equiv = 容量/日耗电×24，本质上是“日耗电”的单调变换。\n"
            "因此把对照搬到日耗电域，可以更直接检验功耗量级是否合理：\n"
            "  drain_scn(mAh/day) = 容量(mAh)×24 / TTE_scn(h)。\n"
            "图中同时标出观测中位数/均值，以及场景落点在真实分布中的分位（Px）。",
        ),
        mode=mode,
        lang=lang,
    )
    if suffix:
        savefig(fig3, out_plots / f"04_drain_hist_overlay_daily{suffix}.png", mode=mode)
    else:
        # 不影响旧流程：只有在未指定 tag 时，才生成一个“默认文件名”的新图。
        savefig(fig3, out_plots / "04_drain_hist_overlay_daily.png", mode=mode)
    plt.close(fig3)

    print("Q2 user_behavior 对照已生成：")
    print(f"- reports: {out_reports}")
    print(f"- plots:   {out_plots}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
