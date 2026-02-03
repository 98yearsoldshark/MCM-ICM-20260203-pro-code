"""Model-1（ECM）可视化：生成一批标准图（paper/study 两种模式）。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcm26a.analysis import default_policy_actions, evaluate_policies_model1
from mcm26a.analysis.model1_policy import PolicyAction1
from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import SimResult0, SimResult1, simulate_model0, simulate_model1_ecm, simulate_model1_ecm_trace
from mcm26a.uq import apply_uq_sample, sample_model0_uq

from .style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class PlotBatchConfig1:
    """绘图批量配置（Model-1）。"""

    scenarios_path: Path
    power_params_path: Path
    phone_ecm_path: Path
    out_dir: Path
    soc0: float = 1.0
    dt_s: float = 2.0
    uq_samples: int = 30
    uq_seed: int = 1


def _glossary_text() -> str:
    return (
        "术语说明：\n"
        "- TTE（Time-to-Empty，耗尽时间）：从当前初始电量（SOC0）开始，在给定使用场景下，电池降至关机阈值前的剩余时间。\n"
        "- variant（变体）：在同一“场景”框架下，仅改变少量条件（如网络模式/信号强弱/是否本地播放）形成的对照版本，用于解释差异与做敏感性对比。\n"
        "- cutoff（截止电压关机）：Model-1 以端电压 V_term 下降到 V_cut 为主要终止条件，比 Model-0 的 SOC 阈值更贴近真实关机逻辑。"
    )


def _scenario_ids(raw: dict[str, Any]) -> list[str]:
    return list(raw.get("scenarios", {}).keys())


def _scenario_title(raw: dict[str, Any], sid: str) -> str:
    return str(raw["scenarios"][sid].get("title_zh", sid))


def _variant_label_zh(variant: str) -> str:
    if variant in ("-", "", None):
        return "基线"
    m = {
        "wifi_poor_signal": "Wi-Fi 弱信号",
        "cellular_good_signal": "蜂窝 好信号",
        "cellular_poor_signal": "蜂窝 弱信号",
        "cellular_stream": "蜂窝 流媒体",
        "local_play": "本地播放",
        "rural_poor_signal": "郊区 弱信号",
        "wifi_navigation": "Wi-Fi 导航",
        "online_game": "在线游戏",
        "high_brightness": "高亮度",
        "cellular_browse": "蜂窝 浏览",
        "poor_signal_standby": "待机 弱信号",
    }
    return m.get(str(variant), str(variant))


def _policy_short_label(action_id: str) -> str:
    m = {
        "brightness_100": "降亮度",
        "disable_gps": "关GPS",
        "force_wifi": "用Wi-Fi",
        "good_signal": "信号好",
        "bg_low": "限后台",
    }
    return m.get(str(action_id), str(action_id))


def _policy_legend_text_long() -> str:
    return (
        "策略短标签对照：\n"
        "- 降亮度：将屏幕点亮段亮度统一设为 100 nits\n"
        "- 关GPS：关闭所有段的 GPS\n"
        "- 用Wi-Fi：强制所有段使用 Wi-Fi（假设可用）\n"
        "- 信号好：把信号状态设为 good（用于对照“弱信号”影响）\n"
        "- 限后台：把后台强度统一设为 low"
    )


def _default_policy_actions_model1() -> list[PolicyAction1]:
    """复用 Model-0 的默认策略集合（因为对 Scenario 的变换是通用的）。"""

    acts0 = default_policy_actions()
    return [
        PolicyAction1(
            action_id=a.action_id,
            title_zh=a.title_zh,
            description_zh=a.description_zh,
            apply=a.apply,
        )
        for a in acts0
    ]


def _load_common(cfg: PlotBatchConfig1) -> tuple[dict[str, Any], PowerParams0, BatteryParams1ECM, BatteryParams0]:
    raw = load_scenarios_json(cfg.scenarios_path)
    power = PowerParams0.from_json(cfg.power_params_path)
    batt1 = BatteryParams1ECM.from_json(cfg.phone_ecm_path)
    batt0 = BatteryParams0.from_json(cfg.phone_ecm_path)
    return raw, power, batt1, batt0


def _baseline_results_model1(
    raw: dict[str, Any], *, power: PowerParams0, batt1: BatteryParams1ECM, soc0: float, dt_s: float
) -> dict[str, SimResult1]:
    out: dict[str, SimResult1] = {}
    for sid in _scenario_ids(raw):
        sc = materialize_scenario(raw, sid)
        out[sid] = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=soc0, dt_s=dt_s)
    return out


def _variant_results_model1(
    raw: dict[str, Any], *, power: PowerParams0, batt1: BatteryParams1ECM, soc0: float, dt_s: float
) -> dict[str, dict[str, SimResult1]]:
    out: dict[str, dict[str, SimResult1]] = {}
    for sid in _scenario_ids(raw):
        variants = raw["scenarios"][sid].get("variants", {})
        vnames = ["-"] + list(variants.keys())
        out[sid] = {}
        for v in vnames:
            sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
            out[sid][v] = simulate_model1_ecm(
                sc, power_params=power, battery_params=batt1, soc0=soc0, dt_s=dt_s, variant=v
            )
    return out


def _baseline_results_model0(
    raw: dict[str, Any], *, power: PowerParams0, batt0: BatteryParams0, soc0: float
) -> dict[str, SimResult0]:
    out: dict[str, SimResult0] = {}
    for sid in _scenario_ids(raw):
        sc = materialize_scenario(raw, sid)
        out[sid] = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=soc0)
    return out


def _fig01_tte_baseline(raw: dict[str, Any], baseline1: dict[str, SimResult1], *, mode: PlotMode, dt_s: float):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    titles = [_scenario_title(raw, sid) for sid in sids]
    ttes = [baseline1[sid].tte_h for sid in sids]

    fig, ax = plt.subplots(figsize=(10, 4.6))
    xs = np.arange(len(sids))
    ys = [0.0 if t is None else float(t) for t in ttes]
    bars = ax.bar(xs, ys, color="#E45756", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(titles, rotation=15, ha="right")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Model-1（ECM）：标准场景续航对比{style.title_suffix}")
    ax.axhline(24.0, color="gray", lw=1.0, ls="--", alpha=0.7)

    if style.annotate:
        for b, t, sid in zip(bars, ttes, sids):
            if t is None:
                continue
            st = baseline1[sid].status
            ax.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 0.25, f"{t:.2f}h", ha="center", fontsize=9)
            ax.text(b.get_x() + b.get_width() / 2.0, 0.15, f"{st}", ha="center", va="bottom", fontsize=8, rotation=90)

        fig.tight_layout(rect=(0.0, 0.16, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            f"说明：Model-1 使用等效电路 ECM，并以截止电压关机（cutoff）作为主要终止条件；dt={dt_s:.2f}s。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig02_tte_variants(raw: dict[str, Any], variants1: dict[str, dict[str, SimResult1]], *, mode: PlotMode):
    style = apply_style(mode)
    sids = _scenario_ids(raw)

    fig, axes = plt.subplots(nrows=len(sids), ncols=1, figsize=(10, 11), sharex=False)
    if len(sids) == 1:
        axes = [axes]

    for ax, sid in zip(axes, sids):
        res_map = variants1[sid]
        vnames = list(res_map.keys())
        xlabels = [_variant_label_zh(v) for v in vnames]
        ys = [0.0 if res_map[v].tte_h is None else float(res_map[v].tte_h) for v in vnames]
        xs = np.arange(len(vnames))
        ax.bar(xs, ys, color="#72B7B2")
        ax.set_xticks(xs)
        ax.set_xticklabels(xlabels, rotation=0)
        ax.set_ylabel("耗尽时间（小时）")
        ax.set_title(_scenario_title(raw, sid))
        if style.annotate:
            for i, v in enumerate(vnames):
                r = res_map[v]
                if r.tte_h is None:
                    continue
                ax.text(i, float(r.tte_h) + 0.2, f"{r.tte_h:.2f}h", ha="center", va="bottom", fontsize=8)

    fig.suptitle(f"Model-1（ECM）：变体（variants）对续航的影响{style.title_suffix}", y=1.02)
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.98))
        fig.text(0.01, 0.02, _glossary_text(), ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout()
    return fig


def _fig03_compare_model0_vs_model1(
    raw: dict[str, Any], b0: dict[str, SimResult0], b1: dict[str, SimResult1], *, mode: PlotMode
):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    titles = [_scenario_title(raw, sid) for sid in sids]

    y0 = [0.0 if b0[sid].tte_h is None else float(b0[sid].tte_h) for sid in sids]
    y1 = [0.0 if b1[sid].tte_h is None else float(b1[sid].tte_h) for sid in sids]

    xs = np.arange(len(sids))
    w = 0.38

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(xs - w / 2, y0, width=w, label="Model-0（SOC阈值）", color="#4C78A8", alpha=0.9)
    ax.bar(xs + w / 2, y1, width=w, label="Model-1（截止电压）", color="#E45756", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(titles, rotation=15, ha="right")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Model-0 vs Model-1：TTE 对比{style.title_suffix}")
    ax.legend(frameon=False)

    if style.annotate:
        # 用差值标注：Model-1 - Model-0
        for i, sid in enumerate(sids):
            d = y1[i] - y0[i]
            ax.text(xs[i], max(y0[i], y1[i]) + 0.25, f"Δ={d:+.2f}h", ha="center", fontsize=9)

        fig.tight_layout(rect=(0.0, 0.14, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：Model-1 因为考虑了端电压与截止电压关机，通常会比 Model-0 更早关机（TTE 更短）。\n"
            "该差异来自“高功率下内阻压降/极化压降使端电压提前到达 V_cut”的机理。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig04_policy_overall(
    raw: dict[str, Any],
    *,
    power: PowerParams0,
    batt1: BatteryParams1ECM,
    soc0: float,
    dt_s: float,
    mode: PlotMode,
):
    style = apply_style(mode)

    actions = _default_policy_actions_model1()
    action_ids = [a.action_id for a in actions]
    action_titles = [_policy_short_label(a.action_id) for a in actions]

    # 把 baseline + 所有 variants 都纳入“案例集”，增强“稳健性/通用性”分析
    cases: list[tuple[str, str]] = []
    for sid in _scenario_ids(raw):
        cases.append((sid, "-"))
        for v in raw["scenarios"][sid].get("variants", {}).keys():
            cases.append((sid, v))

    deltas: dict[str, list[float]] = {aid: [] for aid in action_ids}
    for sid, v in cases:
        sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
        baseline, effects = evaluate_policies_model1(
            sc,
            power_params=power,
            battery_params=batt1,
            soc0=soc0,
            actions=actions,
            dt_s=dt_s,
        )
        if baseline.tte_h is None:
            continue
        effect_map = {e.action_id: e for e in effects}
        for aid in action_ids:
            e = effect_map[aid]
            if e.delta_tte_h is None:
                continue
            deltas[aid].append(float(e.delta_tte_h))

    means = []
    stds = []
    for aid in action_ids:
        xs = deltas[aid]
        if not xs:
            means.append(0.0)
            stds.append(0.0)
        else:
            means.append(float(np.mean(xs)))
            stds.append(float(np.std(xs)))

    # 按平均提升排序
    order = np.argsort(-np.array(means))
    means = [means[i] for i in order]
    stds = [stds[i] for i in order]
    action_titles = [action_titles[i] for i in order]

    fig, ax = plt.subplots(figsize=(10, 4.9))
    xs = np.arange(len(means))
    ax.bar(xs, means, yerr=stds, capsize=3, color="#F58518", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(action_titles, rotation=15, ha="right")
    ax.set_ylabel("平均续航提升 ΔTTE（小时）")
    ax.set_title(f"Model-1（ECM）：策略平均收益（跨场景+变体）{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            f"说明：对每个“案例”（场景+变体）计算 ΔTTE，再在所有案例上取平均；误差棒为标准差（反映不同场景下收益差异）。\n"
            f"该图用于回答“哪些建议最稳健”：只在少数场景有效的策略会被自然降权。dt={dt_s:.2f}s。\n\n"
            + _glossary_text()
            + "\n\n"
            + _policy_legend_text_long(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig05_policy_cases(
    raw: dict[str, Any],
    *,
    power: PowerParams0,
    batt1: BatteryParams1ECM,
    soc0: float,
    dt_s: float,
    mode: PlotMode,
):
    style = apply_style(mode)
    actions = _default_policy_actions_model1()

    # 代表性“高耗电/高波动”案例
    wanted = [
        ("S2_navigation", "rural_poor_signal"),
        ("S1_video", "cellular_poor_signal"),
        ("S4_mixed_day", "poor_signal_standby"),
    ]
    cases: list[tuple[str, str]] = []
    for sid, v in wanted:
        if sid not in raw.get("scenarios", {}):
            continue
        variants = raw["scenarios"][sid].get("variants", {})
        if v not in variants:
            cases.append((sid, "-"))
        else:
            cases.append((sid, v))

    n = len(cases)
    fig, axes = plt.subplots(nrows=1, ncols=n, figsize=(5.2 * n, 4.2), sharey=True)
    if n == 1:
        axes = [axes]

    for ax, (sid, v) in zip(axes, cases):
        sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
        baseline, effects = evaluate_policies_model1(
            sc,
            power_params=power,
            battery_params=batt1,
            soc0=soc0,
            actions=actions,
            dt_s=dt_s,
        )
        xs = np.arange(len(effects))
        ds = [0.0 if e.delta_tte_h is None else float(e.delta_tte_h) for e in effects]
        ax.bar(xs, ds, color="#54A24B")
        ax.set_xticks(xs)
        ax.set_xticklabels([_policy_short_label(e.action_id) for e in effects], rotation=0, ha="center")
        ax.set_ylabel("续航提升 ΔTTE（小时）")
        title = f"{_scenario_title(raw, sid)} | {_variant_label_zh(v)}"
        if style.annotate and baseline.tte_h is not None:
            title += f"\n基线TTE={baseline.tte_h:.2f}h"
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)

    fig.suptitle(f"Model-1（ECM）：典型案例的策略收益对比{style.title_suffix}", y=1.02)
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            f"说明：柱子越高表示该策略越有效；若接近 0，表示该案例下该策略影响很小。dt={dt_s:.2f}s。\n\n"
            + _glossary_text()
            + "\n\n"
            + _policy_legend_text_long(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig04_ocv_curve(batt1: BatteryParams1ECM, *, mode: PlotMode):
    style = apply_style(mode)
    soc = np.linspace(0, 1, 200)
    ocv = np.array([batt1.ocv.ocv_v(float(s)) for s in soc])

    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    ax.plot(soc, ocv, color="#4C78A8", lw=2.2, label="OCV(SOC)")
    ax.axhline(float(batt1.v_cut_V), color="#E45756", ls="--", lw=1.4, label=f"V_cut={batt1.v_cut_V:.2f}V")
    ax.set_xlabel("荷电状态 SOC（0~1）")
    ax.set_ylabel("开路电压 OCV（V）")
    ax.set_title(f"Model-1：OCV-SOC 曲线（名义）{style.title_suffix}")
    ax.legend(frameon=False)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：OCV-SOC 曲线用于把 SOC 映射为开路电压；端电压 = OCV - I*R0 - v1。\n"
            "当端电压下降到 V_cut 时视为关机（cutoff）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig05_soc_at_cutoff(raw: dict[str, Any], baseline1: dict[str, SimResult1], *, mode: PlotMode, soc_min: float):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    titles = [_scenario_title(raw, sid) for sid in sids]
    soc_end = [float(baseline1[sid].soc_end) for sid in sids]

    fig, ax = plt.subplots(figsize=(10, 4.6))
    xs = np.arange(len(sids))
    ax.bar(xs, soc_end, color="#72B7B2", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(titles, rotation=15, ha="right")
    ax.set_ylabel("关机时 SOC（比例）")
    ax.set_title(f"Model-1：截止电压关机时的 SOC（基线）{style.title_suffix}")
    ax.axhline(float(soc_min), color="gray", lw=1.0, ls="--", alpha=0.7, label=f"soc_min={soc_min:.2f}")
    ax.legend(frameon=False)

    if style.annotate:
        for i, sid in enumerate(sids):
            st = baseline1[sid].status
            ax.text(xs[i], soc_end[i] + 0.01, f"{soc_end[i]:.3f}", ha="center", fontsize=9)
            ax.text(xs[i], 0.01, st, ha="center", va="bottom", fontsize=8, rotation=90)

        fig.tight_layout(rect=(0.0, 0.14, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图展示 Model-1 在“截止电压关机”时的 SOC_end。\n"
            "若 SOC_end 显著大于 soc_min，说明端电压提前触发关机（通常由高功率导致的压降造成）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig06_trace_example(
    raw: dict[str, Any], *, power: PowerParams0, batt1: BatteryParams1ECM, soc0: float, dt_s: float, mode: PlotMode
):
    style = apply_style(mode)

    # 选一个“短且典型”的场景做示例轨迹
    sid = "S3_gaming" if "S3_gaming" in raw.get("scenarios", {}) else _scenario_ids(raw)[0]
    sc = materialize_scenario(raw, sid)
    tr = simulate_model1_ecm_trace(sc, power_params=power, battery_params=batt1, soc0=soc0, dt_s=dt_s)

    t_h = np.array(tr.t_s) / 3600.0
    soc_pct = np.array(tr.soc) * 100.0
    v1 = np.array(tr.v1_V)
    v = np.array(tr.v_term_V)
    p = np.array(tr.p_W)
    p_max = np.array(tr.p_max_W)

    nrows = 4 if style.annotate else 3
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10.0, 7.6 if style.annotate else 6.8), sharex=True)
    if nrows == 3:
        ax1, ax2, ax3 = axes
        ax4 = None
    else:
        ax1, ax2, ax3, ax4 = axes

    ax1.plot(t_h, soc_pct, color="#4C78A8", lw=2.0)
    ax1.set_ylabel("SOC（%）")
    ax1.set_title(f"Model-1 轨迹示例：{_scenario_title(raw, sid)}{style.title_suffix}")

    ax2.plot(t_h, v, color="#E45756", lw=2.0)
    ax2.axhline(float(batt1.v_cut_V), color="gray", ls="--", lw=1.0, alpha=0.7)
    ax2.set_ylabel("端电压 V_term（V）")

    ax3.plot(t_h, p, color="#54A24B", lw=2.0)
    ax3.plot(t_h, p_max, color="gray", lw=1.6, ls="--", alpha=0.9, label="P_max（可行上限）")
    ax3.set_ylabel("功率（W）")
    if ax4 is None:
        ax3.set_xlabel("时间（小时）")
    ax3.legend(frameon=False, loc="upper right")

    if ax4 is not None:
        ax4.plot(t_h, v1, color="#B279A2", lw=2.0)
        ax4.set_ylabel("极化电压 v1（V）")
        ax4.set_xlabel("时间（小时）")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            f"说明：示例轨迹展示 SOC、端电压与功率随时间的变化；当 V_term 降至 V_cut={batt1.v_cut_V:.2f}V 时触发 cutoff（关机）。\n"
            "灰色虚线为可行功率上限 P_max(t)（由判别式 Δ=(OCV−v1)^2−4R0P 推出），用于刻画“雪崩/不可满足功率需求”边界。\n"
            f"轨迹状态={tr.status}，dt={dt_s:.2f}s。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _uq_boxplot_compare_model0_vs_model1(
    raw: dict[str, Any],
    *,
    power: PowerParams0,
    batt0: BatteryParams0,
    batt1: BatteryParams1ECM,
    soc0: float,
    dt_s: float,
    n: int,
    seed: int,
    mode: PlotMode,
    cache_dir: Path | None = None,
):
    """对“功耗参数不确定性”做传播：比较 Model-0 与 Model-1 的 TTE 分布。

    说明：为了不引入额外 ECM 参数不确定性，这里复用 Model-0 的功耗采样（radio/screen/cpu...）。
    """

    style = apply_style(mode)
    rng = random.Random(int(seed))

    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]

    # 优先尝试从缓存读取：避免 paper/study 两套图重复做昂贵采样
    cache_path: Path | None = None
    data0: dict[str, list[float]] = {}
    data1: dict[str, list[float]] = {}
    if cache_dir is not None:
        cache_dir = ensure_dir(cache_dir)
        soc_tag = f"{float(soc0):.3f}".replace(".", "p")
        dt_tag = f"{float(dt_s):.2f}".replace(".", "p")
        cache_path = cache_dir / f"uq_m0_m1_tte_soc{soc_tag}_dt{dt_tag}_n{int(n)}_seed{int(seed)}.npz"
        if cache_path.exists():
            try:
                z = np.load(cache_path, allow_pickle=False)
                sids_cached = [str(x) for x in z["sids"].tolist()]
                if sids_cached == sids:
                    data0 = {sid: z[f"m0_{sid}"].astype(float).tolist() for sid in sids}
                    data1 = {sid: z[f"m1_{sid}"].astype(float).tolist() for sid in sids}
            except Exception:
                data0 = {}
                data1 = {}

    # 若缓存缺失/无效，则重新采样并写入缓存
    if not data0 or not data1:
        data0 = {sid: [] for sid in sids}
        data1 = {sid: [] for sid in sids}

        # 预构建场景对象，避免在采样循环中反复 materialize
        sc_map = {sid: materialize_scenario(raw, sid) for sid in sids}

        for _ in range(int(n)):
            s = sample_model0_uq(rng)
            p, b0 = apply_uq_sample(power, batt0, s)
            # model1 也只替换 power，不改电池 ECM 参数（保持对比公平且实现简单）
            for sid in sids:
                sc = sc_map[sid]
                r0 = simulate_model0(sc, power_params=p, battery_params=b0, soc0=soc0)
                r1 = simulate_model1_ecm(sc, power_params=p, battery_params=batt1, soc0=soc0, dt_s=dt_s)
                if r0.tte_h is not None:
                    data0[sid].append(float(r0.tte_h))
                if r1.tte_h is not None:
                    data1[sid].append(float(r1.tte_h))

        if cache_path is not None:
            try:
                np.savez_compressed(
                    cache_path,
                    sids=np.array(sids, dtype=object),
                    **{f"m0_{sid}": np.array(data0[sid], dtype=float) for sid in sids},
                    **{f"m1_{sid}": np.array(data1[sid], dtype=float) for sid in sids},
                )
            except Exception:
                # 缓存写入失败不影响出图
                pass

    # 组装箱线图：每个场景画两组 box（model0/model1）
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    positions = []
    box_data = []
    xticks = []
    for i, sid in enumerate(sids):
        positions.extend([2 * i + 1, 2 * i + 2])
        box_data.extend([data0[sid], data1[sid]])
        xticks.append(2 * i + 1.5)

    bp = ax.boxplot(box_data, positions=positions, widths=0.55, patch_artist=True, showfliers=False)
    # 配色：交替
    for j, patch in enumerate(bp["boxes"]):
        patch.set_facecolor("#4C78A8" if j % 2 == 0 else "#E45756")
        patch.set_alpha(0.8)
        patch.set_edgecolor("#333333")

    ax.set_xticks(xticks)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"功耗不确定性传播：Model-0 vs Model-1（箱线图）{style.title_suffix}")

    # 图例
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(facecolor="#4C78A8", edgecolor="#333333", label="Model-0（SOC阈值）"),
            Patch(facecolor="#E45756", edgecolor="#333333", label="Model-1（截止电压）"),
        ],
        loc="upper right",
        frameon=False,
    )

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            f"说明：对功耗参数做先验采样（n={n}），把不确定性传播到 TTE；每个场景两组箱线图分别对应 Model-0 与 Model-1。\n"
            "该图用于展示“结论的稳健性”：若两组分布始终存在系统性差异，说明电池电学机制确实会改变 TTE。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def make_model1_plot_batch(cfg: PlotBatchConfig1, *, mode: PlotMode) -> list[Path]:
    """生成 Model-1 的一批图并保存，返回生成的文件路径列表。"""

    raw, power, batt1, batt0 = _load_common(cfg)
    out_dir = ensure_dir(cfg.out_dir / "model1" / mode)

    b1 = _baseline_results_model1(raw, power=power, batt1=batt1, soc0=float(cfg.soc0), dt_s=float(cfg.dt_s))
    v1 = _variant_results_model1(raw, power=power, batt1=batt1, soc0=float(cfg.soc0), dt_s=float(cfg.dt_s))
    b0 = _baseline_results_model0(raw, power=power, batt0=batt0, soc0=float(cfg.soc0))

    figs: list[tuple[str, str, Any]] = [
        ("tte", "01_tte_baseline.png", _fig01_tte_baseline(raw, b1, mode=mode, dt_s=float(cfg.dt_s))),
        ("tte", "02_tte_variants.png", _fig02_tte_variants(raw, v1, mode=mode)),
        (
            "policy",
            "03_policy_overall.png",
            _fig04_policy_overall(
                raw,
                power=power,
                batt1=batt1,
                soc0=float(cfg.soc0),
                dt_s=float(cfg.dt_s),
                mode=mode,
            ),
        ),
        (
            "policy",
            "04_policy_cases.png",
            _fig05_policy_cases(
                raw,
                power=power,
                batt1=batt1,
                soc0=float(cfg.soc0),
                dt_s=float(cfg.dt_s),
                mode=mode,
            ),
        ),
        ("compare", "05_tte_model0_vs_model1.png", _fig03_compare_model0_vs_model1(raw, b0, b1, mode=mode)),
        ("battery", "06_ocv_curve.png", _fig04_ocv_curve(batt1, mode=mode)),
        ("battery", "07_soc_at_cutoff.png", _fig05_soc_at_cutoff(raw, b1, mode=mode, soc_min=float(batt0.soc_min))),
        (
            "trace",
            "08_trace_example.png",
            _fig06_trace_example(
                raw,
                power=power,
                batt1=batt1,
                soc0=float(cfg.soc0),
                dt_s=float(cfg.dt_s),
                mode=mode,
            ),
        ),
        (
            "uq",
            "09_uq_boxplot_model0_vs_model1.png",
            _uq_boxplot_compare_model0_vs_model1(
                raw,
                power=power,
                batt0=batt0,
                batt1=batt1,
                soc0=float(cfg.soc0),
                dt_s=float(cfg.dt_s),
                n=int(cfg.uq_samples),
                seed=int(cfg.uq_seed),
                mode=mode,
                cache_dir=cfg.out_dir / "model1" / "_cache",
            ),
        ),
    ]

    paths: list[Path] = []
    for category, name, fig in figs:
        path = out_dir / category / name
        savefig(fig, path, mode=mode)
        plt.close(fig)
        paths.append(path)

    return paths
