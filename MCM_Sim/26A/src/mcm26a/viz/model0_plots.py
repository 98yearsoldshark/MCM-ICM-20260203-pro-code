"""Model-0 可视化：生成一批标准图（paper/study 两种模式）。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcm26a.analysis import default_policy_actions, evaluate_policies_model0
from mcm26a.analysis.stats import pearson_corr, quantile
from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario, set_brightness_for_screen_on
from mcm26a.sim import SimResult0, simulate_model0
from mcm26a.uq import apply_uq_sample, sample_model0_uq

from .style import PlotMode, apply_style, ensure_dir, savefig

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class PlotBatchConfig:
    """绘图批量配置。"""

    scenarios_path: Path
    power_params_path: Path
    phone_params_path: Path
    out_dir: Path
    soc0: float = 1.0
    uq_samples: int = 800
    uq_seed: int = 1


def _glossary_text() -> str:
    return (
        "术语说明：\n"
        "- TTE（Time-to-Empty，耗尽时间）：从当前初始电量（SOC0）开始，在给定使用场景下，电池降至关机阈值前的剩余时间。\n"
        "- variant（变体）：在同一“场景”框架下，仅改变少量条件（如网络模式/信号强弱/是否本地播放）形成的对照版本，用于解释差异与做敏感性对比。"
    )


def _activity_zh(activity: str) -> str:
    m = {
        "standby": "待机",
        "video": "视频",
        "navigation": "导航",
        "gaming": "游戏",
        "browse": "浏览",
        "call": "通话",
    }
    return m.get(str(activity), str(activity))


def _radio_zh(mode: str) -> str:
    m = {
        "wifi": "Wi-Fi",
        "lte": "蜂窝（LTE）",
        "5g": "蜂窝（5G）",
    }
    return m.get(str(mode), str(mode))


def _signal_zh(q: str) -> str:
    m = {"good": "信号好", "poor": "信号差"}
    return m.get(str(q), str(q))


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
    """策略的短标签（用于论文图，避免横轴过长）。"""

    m = {
        "brightness_100": "降亮度",
        "disable_gps": "关GPS",
        "force_wifi": "用Wi-Fi",
        "good_signal": "信号好",
        "bg_low": "限后台",
    }
    return m.get(str(action_id), str(action_id))


def _policy_legend_text_long() -> str:
    """学习版：把短标签映射为完整描述，便于读者理解。"""

    return (
        "策略短标签对照：\n"
        "- 降亮度：将屏幕点亮段亮度统一设为 100 nits\n"
        "- 关GPS：关闭所有段的 GPS\n"
        "- 用Wi-Fi：强制所有段使用 Wi-Fi（假设可用）\n"
        "- 信号好：把信号状态设为 good（用于对照“弱信号”影响）\n"
        "- 限后台：把后台强度统一设为 low"
    )


def _load_common(cfg: PlotBatchConfig) -> tuple[dict[str, Any], PowerParams0, BatteryParams0]:
    raw = load_scenarios_json(cfg.scenarios_path)
    power = PowerParams0.from_json(cfg.power_params_path)
    battery = BatteryParams0.from_json(cfg.phone_params_path)
    return raw, power, battery


def _scenario_ids(raw: dict[str, Any]) -> list[str]:
    return list(raw.get("scenarios", {}).keys())


def _scenario_title(raw: dict[str, Any], sid: str) -> str:
    return str(raw["scenarios"][sid].get("title_zh", sid))


def _baseline_results(
    raw: dict[str, Any], *, power: PowerParams0, battery: BatteryParams0, soc0: float
) -> dict[str, SimResult0]:
    out: dict[str, SimResult0] = {}
    for sid in _scenario_ids(raw):
        sc = materialize_scenario(raw, sid)
        out[sid] = simulate_model0(sc, power_params=power, battery_params=battery, soc0=soc0)
    return out


def _variant_results(
    raw: dict[str, Any], *, power: PowerParams0, battery: BatteryParams0, soc0: float
) -> dict[str, dict[str, SimResult0]]:
    out: dict[str, dict[str, SimResult0]] = {}
    for sid in _scenario_ids(raw):
        variants = raw["scenarios"][sid].get("variants", {})
        vnames = ["-"] + list(variants.keys())
        out[sid] = {}
        for v in vnames:
            sc = materialize_scenario(raw, sid, variant=(None if v == "-" else v))
            out[sid][v] = simulate_model0(sc, power_params=power, battery_params=battery, soc0=soc0, variant=v)
    return out


def _fig01_tte_baseline(raw: dict[str, Any], baseline: dict[str, SimResult0], *, mode: PlotMode):
    style = apply_style(mode)

    sids = _scenario_ids(raw)
    titles = [_scenario_title(raw, sid) for sid in sids]
    ttes = [baseline[sid].tte_h for sid in sids]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    xs = np.arange(len(sids))
    ys = [0.0 if t is None else float(t) for t in ttes]
    bars = ax.bar(xs, ys, color="#4C78A8")
    ax.set_xticks(xs)
    ax.set_xticklabels(titles, rotation=15, ha="right")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Model-0：标准场景续航对比{style.title_suffix}")
    ax.axhline(24.0, color="gray", lw=1.0, ls="--", alpha=0.7)
    ax.text(len(xs) - 0.5, 24.0 + 0.2, "24h", color="gray", ha="right", va="bottom", fontsize=9)

    if style.annotate:
        for b, t in zip(bars, ttes):
            if t is None:
                continue
            ax.text(
                b.get_x() + b.get_width() / 2.0,
                b.get_height() + 0.3,
                f"{t:.2f}h",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        # 学习版把说明放到图外，避免遮挡主体可视化
        fig.tight_layout(rect=(0.0, 0.16, 1.0, 1.0))
        fig.text(
            0.01,
            0.02,
            "说明：Model-0 使用能量守恒（dE/dt=-P_total）计算耗尽时间；条形越高表示续航越长；灰虚线为 24 小时参考线。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig02_tte_variants(raw: dict[str, Any], variant_res: dict[str, dict[str, SimResult0]], *, mode: PlotMode):
    style = apply_style(mode)
    sids = _scenario_ids(raw)

    fig, axes = plt.subplots(nrows=len(sids), ncols=1, figsize=(10, 11), sharex=False)
    if len(sids) == 1:
        axes = [axes]

    for ax, sid in zip(axes, sids):
        res_map = variant_res[sid]
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
                if r.avg_power_W is not None:
                    ax.text(i, 0.2, f"均功率≈{r.avg_power_W:.2f}W", ha="center", va="bottom", fontsize=7, rotation=90)

    fig.suptitle(f"Model-0：变体（variants）对续航的影响{style.title_suffix}", y=1.02)
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig03_component_share(raw: dict[str, Any], baseline: dict[str, SimResult0], *, mode: PlotMode):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]

    # 组件顺序（与 PowerBreakdown 一致）
    comps = ["base_Wh", "screen_Wh", "cpu_Wh", "gpu_Wh", "radio_Wh", "gps_Wh", "background_Wh", "interaction_Wh"]
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2", "#FF9DA6", "#9D755D"]
    comp_zh = {
        "base_Wh": "基础",
        "screen_Wh": "屏幕",
        "cpu_Wh": "CPU",
        "gpu_Wh": "GPU",
        "radio_Wh": "网络",
        "gps_Wh": "GPS",
        "background_Wh": "后台",
        "interaction_Wh": "交互",
    }

    data = []
    for sid in sids:
        res = baseline[sid]
        total = float(res.energy_used_Wh) if res.energy_used_Wh else 0.0
        row = []
        for c in comps:
            v = float(res.energy_components_Wh.get(c, 0.0))
            row.append(0.0 if total <= 0 else (v / total * 100.0))
        data.append(row)
    data = np.array(data)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    bottom = np.zeros(len(sids))
    for j, c in enumerate(comps):
        ax.bar(labels, data[:, j], bottom=bottom, label=comp_zh.get(c, c.replace("_Wh", "")), color=colors[j])
        bottom += data[:, j]

    ax.set_ylabel("能耗占比（%）")
    ax.set_title(f"Model-0：不同场景的能耗构成（占比）{style.title_suffix}")
    ax.set_ylim(0, 100)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.18), frameon=False)
    ax.grid(axis="y", alpha=0.25)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.14, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图展示“耗尽到 soc_min”为止，各组件累积耗能的占比（每根柱子总和=100%）。占比高的组件是主要耗电驱动。\n"
            "可据此生成节能建议（例如降低亮度、改善信号、切换网络等）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig04_policy_overall(raw: dict[str, Any], *, power: PowerParams0, battery: BatteryParams0, soc0: float, mode: PlotMode):
    style = apply_style(mode)

    actions = default_policy_actions()
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
        baseline, effects = evaluate_policies_model0(
            sc, power_params=power, battery_params=battery, soc0=soc0, actions=actions
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

    fig, ax = plt.subplots(figsize=(10, 4.8))
    xs = np.arange(len(means))
    ax.bar(xs, means, yerr=stds, capsize=3, color="#F58518", alpha=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels(action_titles, rotation=15, ha="right")
    ax.set_ylabel("平均续航提升 ΔTTE（小时）")
    ax.set_title(f"Model-0：策略平均收益（跨场景+变体）{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.16, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：对每个“案例”（场景+变体）计算 ΔTTE，再在所有案例上取平均；误差棒为标准差（反映不同场景下收益差异）。\n"
            "这是把“建议”建立在稳健性上的关键一步：只在个别场景有效的策略会被自然降权。\n\n"
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


def _fig05_policy_cases(raw: dict[str, Any], *, power: PowerParams0, battery: BatteryParams0, soc0: float, mode: PlotMode):
    style = apply_style(mode)
    actions = default_policy_actions()

    # 代表性“高耗电/高波动”案例
    wanted = [
        ("S2_navigation", "rural_poor_signal"),
        ("S1_video", "cellular_poor_signal"),
        ("S4_mixed_day", "poor_signal_standby"),
    ]
    cases = []
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
        baseline, effects = evaluate_policies_model0(
            sc, power_params=power, battery_params=battery, soc0=soc0, actions=actions
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

    fig.suptitle(f"Model-0：典型案例的策略收益对比{style.title_suffix}", y=1.02)
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：柱子越高表示该策略越有效；若接近 0，表示该案例下该策略影响很小。\n\n"
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


def _uq_samples_for_scenarios(
    raw: dict[str, Any],
    *,
    base_power: PowerParams0,
    base_battery: BatteryParams0,
    soc0: float,
    n: int,
    seed: int,
) -> tuple[dict[str, list[float]], dict[str, dict[str, float]]]:
    """返回：
    - ttes[sid] = [TTE_h samples...]
    - corrs[sid][factor] = pearson corr
    """

    rng = random.Random(int(seed))

    # 因子名固定，保证热力图列顺序稳定
    factor_keys = [
        "battery_energy_scale",
        "base_scale",
        "screen_scale",
        "cpu_scale",
        "gpu_scale",
        "gps_scale",
        "background_scale",
        "radio_scale",
        "poor_signal_multiplier",
    ]

    ttes: dict[str, list[float]] = {sid: [] for sid in _scenario_ids(raw)}
    samples_x: dict[str, dict[str, list[float]]] = {
        sid: {k: [] for k in factor_keys} for sid in _scenario_ids(raw)
    }

    for _ in range(int(n)):
        s = sample_model0_uq(rng)
        p, b = apply_uq_sample(base_power, base_battery, s)

        for sid in _scenario_ids(raw):
            sc = materialize_scenario(raw, sid)
            res = simulate_model0(sc, power_params=p, battery_params=b, soc0=soc0)
            if res.tte_h is None:
                continue
            ttes[sid].append(float(res.tte_h))
            samples_x[sid]["battery_energy_scale"].append(float(s.battery_energy_scale))
            samples_x[sid]["base_scale"].append(float(s.base_scale))
            samples_x[sid]["screen_scale"].append(float(s.screen_scale))
            samples_x[sid]["cpu_scale"].append(float(s.cpu_scale))
            samples_x[sid]["gpu_scale"].append(float(s.gpu_scale))
            samples_x[sid]["gps_scale"].append(float(s.gps_scale))
            samples_x[sid]["background_scale"].append(float(s.background_scale))
            samples_x[sid]["radio_scale"].append(float(s.radio_scale))
            samples_x[sid]["poor_signal_multiplier"].append(float(s.poor_signal_multiplier))

    corrs: dict[str, dict[str, float]] = {}
    for sid in _scenario_ids(raw):
        corrs[sid] = {}
        ys = ttes[sid]
        for k in factor_keys:
            xs = samples_x[sid][k]
            if len(xs) < 2 or len(xs) != len(ys):
                corrs[sid][k] = 0.0
            else:
                corrs[sid][k] = float(pearson_corr(xs, ys))

    return ttes, corrs


def _fig06_uq_boxplot(raw: dict[str, Any], ttes: dict[str, list[float]], *, mode: PlotMode):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]
    data = [ttes[sid] for sid in sids]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.boxplot(data, labels=labels, showfliers=False)
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Model-0：不确定性下的续航分布（箱线图）{style.title_suffix}")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    if style.annotate:
        lines = []
        for sid in sids:
            xs = ttes[sid]
            if not xs:
                continue
            p05 = quantile(xs, 0.05)
            p50 = quantile(xs, 0.50)
            p95 = quantile(xs, 0.95)
            lines.append(f"{_scenario_title(raw, sid)}: P05={p05:.2f}, P50={p50:.2f}, P95={p95:.2f}")
        ax.text(
            0.01,
            0.98,
            "分位数摘要（同一组随机采样参数）：\n" + "\n".join(lines),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#999999", "alpha": 0.9},
        )

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.06, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig07_uq_corr_heatmap(raw: dict[str, Any], corrs: dict[str, dict[str, float]], *, mode: PlotMode):
    style = apply_style(mode)

    sids = _scenario_ids(raw)
    row_labels = [_scenario_title(raw, sid) for sid in sids]
    col_labels = [
        "电池能量",
        "基础功耗",
        "屏幕",
        "CPU",
        "GPU",
        "GPS",
        "后台",
        "网络",
        "弱信号系数",
    ]
    factor_keys = [
        "battery_energy_scale",
        "base_scale",
        "screen_scale",
        "cpu_scale",
        "gpu_scale",
        "gps_scale",
        "background_scale",
        "radio_scale",
        "poor_signal_multiplier",
    ]

    mat = np.zeros((len(sids), len(factor_keys)))
    for i, sid in enumerate(sids):
        for j, k in enumerate(factor_keys):
            mat[i, j] = float(corrs[sid].get(k, 0.0))

    fig, ax = plt.subplots(figsize=(10, 4.6))
    im = ax.imshow(mat, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=20, ha="right")
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_title(f"Model-0：TTE 对不确定性因子的相关性（热力图）{style.title_suffix}")
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("皮尔逊相关系数")

    if style.annotate:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, f"{mat[i, j]:+.2f}", ha="center", va="center", fontsize=8, color="black")
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：相关系数绝对值越大，表示该不确定性因子对 TTE 的影响越显著（在当前先验采样范围内）。\n"
            "正号表示因子增大 -> TTE 增大；负号表示因子增大 -> TTE 减小。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig08_brightness_sweep(raw: dict[str, Any], *, power: PowerParams0, battery: BatteryParams0, soc0: float, mode: PlotMode):
    style = apply_style(mode)

    # 选取典型“亮度敏感”场景
    targets = ["S1_video", "S2_navigation", "S3_gaming", "S4_mixed_day"]
    targets = [t for t in targets if t in raw.get("scenarios", {})]

    brightness = [50, 100, 200, 400, 600]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    for sid in targets:
        sc0 = materialize_scenario(raw, sid)
        ys = []
        for b in brightness:
            sc = set_brightness_for_screen_on(sc0, brightness_nits=float(b))
            res = simulate_model0(sc, power_params=power, battery_params=battery, soc0=soc0)
            ys.append(float("nan") if res.tte_h is None else float(res.tte_h))
        ax.plot(brightness, ys, marker="o", label=_scenario_title(raw, sid))

    ax.set_xlabel("屏幕亮度（nits）")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Model-0：亮度对续航的影响（反事实扫参）{style.title_suffix}")
    ax.legend()

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.14, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：仅修改“屏幕点亮段”的亮度，其余使用模式不变。\n"
            "曲线斜率越大表示“调暗屏幕”收益越大；不同场景斜率不同，体现策略的场景依赖性。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig09_schedule_timeline_all(raw: dict[str, Any], *, mode: PlotMode):
    style = apply_style(mode)

    sids = _scenario_ids(raw)
    fig, axes = plt.subplots(nrows=len(sids), ncols=1, figsize=(10.5, 9.5), sharex=False)
    if len(sids) == 1:
        axes = [axes]

    # 活动配色（可按需扩展）
    activity_color = {
        "standby": "#9E9E9E",
        "video": "#4C78A8",
        "navigation": "#54A24B",
        "gaming": "#E45756",
        "browse": "#B279A2",
        "call": "#F58518",
    }

    for ax, sid in zip(axes, sids):
        sc = materialize_scenario(raw, sid)
        total_s = float(sc.cycle_s) if float(sc.cycle_s) > 0 else float(sum(seg.duration_s for seg in sc.schedule))
        # 短周期用“分钟”更直观；长周期（如 24h）用“小时”
        if total_s <= 2.0 * 3600.0:
            scale = 1.0 / 60.0
            unit = "分钟"
        else:
            scale = 1.0 / 3600.0
            unit = "小时"

        t = 0.0
        bars = []
        colors = []
        for seg in sc.schedule:
            dur_u = float(seg.duration_s) * scale
            bars.append((t, dur_u))
            c = activity_color.get(seg.activity, "#72B7B2")
            # 屏幕关闭时用更浅颜色，增强可读性
            alpha = 0.35 if not seg.screen_on else 0.95
            colors.append((*plt.matplotlib.colors.to_rgb(c), alpha))
            t += dur_u

        ax.broken_barh(bars, (0, 10), facecolors=colors, edgecolors="white", linewidth=0.8)
        ax.set_ylim(0, 10)
        ax.set_yticks([])
        ax.set_xlabel(f"时间（{unit}，单周期）")
        ax.set_title(_scenario_title(raw, sid))
        ax.grid(False)
        ax.set_xlim(0.0, max(1e-9, t))

        if style.annotate:
            # 总览图的段内标注尽量“短”，避免混合场景的短段文字拥挤。
            # 更详细参数请查看单场景日程图（by_scenario）。
            t_total = max(1e-9, t)
            t0 = 0.0
            for seg in sc.schedule:
                dur_u = float(seg.duration_s) * scale
                mid = t0 + dur_u / 2.0

                act = _activity_zh(seg.activity)
                # 段太短时不标注，防止重叠；中等长度只标活动名；足够长才加亮度。
                if dur_u < 0.05 * t_total:
                    tag = ""
                elif dur_u < 0.12 * t_total:
                    tag = act
                else:
                    tag = act if not seg.screen_on else f"{act}\n{seg.brightness_nits:.0f} nits"

                if tag:
                    ax.text(mid, 5, tag, ha="center", va="center", fontsize=9, color="black")

                t0 += dur_u

    # 加一个全局图例，便于读者理解“颜色=活动类型”
    try:
        from matplotlib.patches import Patch

        used = []
        for sid in sids:
            sc = materialize_scenario(raw, sid)
            used.extend([seg.activity for seg in sc.schedule])
        used = sorted(set(used))
        handles = [Patch(facecolor=activity_color.get(a, "#72B7B2"), label=_activity_zh(a)) for a in used]
        fig.legend(handles=handles, loc="upper center", ncol=min(6, len(handles)), frameon=False, bbox_to_anchor=(0.5, 1.02))
    except Exception:
        pass

    fig.suptitle(
        f"标准场景日程（schedule）可视化（输入侧）{style.title_suffix}",
        y=1.06,
    )
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.90))
        fig.text(
            0.01,
            0.02,
            "说明：该图展示每个场景在一个周期内的“输入过程”（活动类型/屏幕/网络/信号/GPS 等）。\n"
            "短周期场景以“分钟”为横轴，长周期（24h）以“小时”为横轴。\n\n"
            + _glossary_text()
            + "\n\n注：更详细的每段参数（起止时间、网络/信号/GPS 等）请查看单场景日程图。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    return fig


def _fig09_schedule_timeline_single(raw: dict[str, Any], sid: str, *, mode: PlotMode):
    """单场景日程图：study 版在下方给出参数表，避免段内文字拥挤。"""

    style = apply_style(mode)
    sc = materialize_scenario(raw, sid)

    # 活动配色（与总览一致）
    activity_color = {
        "standby": "#9E9E9E",
        "video": "#4C78A8",
        "navigation": "#54A24B",
        "gaming": "#E45756",
        "browse": "#B279A2",
        "call": "#F58518",
    }

    total_s = float(sc.cycle_s) if float(sc.cycle_s) > 0 else float(sum(seg.duration_s for seg in sc.schedule))
    if total_s <= 2.0 * 3600.0:
        scale = 1.0 / 60.0
        unit = "分钟"
    else:
        scale = 1.0 / 3600.0
        unit = "小时"

    if style.annotate:
        fig = plt.figure(figsize=(10.5, 4.6))
        gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[2.2, 1.2], hspace=0.25)
        ax = fig.add_subplot(gs[0, 0])
        ax_tbl = fig.add_subplot(gs[1, 0])
        ax_tbl.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(10.5, 2.4))
        ax_tbl = None

    # timeline
    t = 0.0
    bars = []
    colors = []
    for seg in sc.schedule:
        dur_u = float(seg.duration_s) * scale
        bars.append((t, dur_u))
        c = activity_color.get(seg.activity, "#72B7B2")
        alpha = 0.35 if not seg.screen_on else 0.95
        colors.append((*plt.matplotlib.colors.to_rgb(c), alpha))
        t += dur_u

    ax.broken_barh(bars, (0, 10), facecolors=colors, edgecolors="white", linewidth=1.0)
    ax.set_ylim(0, 10)
    ax.set_yticks([])
    ax.set_xlim(0.0, max(1e-9, t))
    ax.set_xlabel(f"时间（{unit}，单周期）")
    ax.set_title(f"{_scenario_title(raw, sid)}：单场景日程{style.title_suffix}")
    ax.grid(False)

    # 图例（仅展示该场景用到的活动）
    try:
        from matplotlib.patches import Patch

        used = sorted(set(seg.activity for seg in sc.schedule))
        handles = [Patch(facecolor=activity_color.get(a, "#72B7B2"), label=_activity_zh(a)) for a in used]
        ax.legend(handles=handles, loc="upper right", frameon=False)
    except Exception:
        pass

    if style.annotate and ax_tbl is not None:
        # 参数表
        col_labels = ["段", f"起-止({unit})", "活动", "屏幕", "亮度", "网络", "信号", "GPS"]
        cell_text = []
        t0 = 0.0
        for i, seg in enumerate(sc.schedule):
            dur_u = float(seg.duration_s) * scale
            t1 = t0 + dur_u
            cell_text.append(
                [
                    str(i),
                    f"{t0:.1f}-{t1:.1f}",
                    _activity_zh(seg.activity),
                    "开" if seg.screen_on else "关",
                    "-" if not seg.screen_on else f"{seg.brightness_nits:.0f}",
                    _radio_zh(seg.radio_mode),
                    _signal_zh(seg.signal_quality),
                    "开" if seg.gps_on else "关",
                ]
            )
            t0 = t1

        table = ax_tbl.table(cellText=cell_text, colLabels=col_labels, loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.0, 1.15)

        # 额外说明与术语
        fig.text(
            0.01,
            0.01,
            "说明：上图为该场景单周期的输入过程；下表列出每段的关键参数。\n\n" + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )

    # 带 table 的 figure 与 tight_layout 兼容性较差；学习版保持 gridspec 的间距即可。
    if not style.annotate:
        fig.tight_layout()
    return fig


def make_model0_plot_batch(cfg: PlotBatchConfig, *, mode: PlotMode) -> list[Path]:
    """生成 Model-0 的一批图并保存，返回生成的文件路径列表。"""

    raw, power, battery = _load_common(cfg)
    # 输出根目录：out_plots/model0/{paper|study}/
    out_dir = ensure_dir(cfg.out_dir / "model0" / mode)

    baseline = _baseline_results(raw, power=power, battery=battery, soc0=float(cfg.soc0))
    variants = _variant_results(raw, power=power, battery=battery, soc0=float(cfg.soc0))

    # UQ（一次采样结果用于多个图）
    ttes_uq, corrs_uq = _uq_samples_for_scenarios(
        raw,
        base_power=power,
        base_battery=battery,
        soc0=float(cfg.soc0),
        n=int(cfg.uq_samples),
        seed=int(cfg.uq_seed),
    )

    figures: list[tuple[str, str, Any]] = [
        ("tte", "01_tte_baseline.png", _fig01_tte_baseline(raw, baseline, mode=mode)),
        ("tte", "02_tte_variants.png", _fig02_tte_variants(raw, variants, mode=mode)),
        ("energy", "03_component_share.png", _fig03_component_share(raw, baseline, mode=mode)),
        ("policy", "04_policy_overall.png", _fig04_policy_overall(raw, power=power, battery=battery, soc0=float(cfg.soc0), mode=mode)),
        ("policy", "05_policy_cases.png", _fig05_policy_cases(raw, power=power, battery=battery, soc0=float(cfg.soc0), mode=mode)),
        ("uq", "06_uq_tte_boxplot.png", _fig06_uq_boxplot(raw, ttes_uq, mode=mode)),
        ("uq", "07_uq_corr_heatmap.png", _fig07_uq_corr_heatmap(raw, corrs_uq, mode=mode)),
        ("sweep", "08_brightness_sweep.png", _fig08_brightness_sweep(raw, power=power, battery=battery, soc0=float(cfg.soc0), mode=mode)),
        ("scenarios", "09_schedule_timeline_all.png", _fig09_schedule_timeline_all(raw, mode=mode)),
    ]

    # 单场景日程图（更清晰、适合学习版查看）
    for sid in _scenario_ids(raw):
        figures.append(("scenarios/by_scenario", f"schedule_{sid}.png", _fig09_schedule_timeline_single(raw, sid, mode=mode)))

    paths: list[Path] = []
    for category, name, fig in figures:
        path = out_dir / category / name
        savefig(fig, path, mode=mode)
        plt.close(fig)
        paths.append(path)

    return paths
