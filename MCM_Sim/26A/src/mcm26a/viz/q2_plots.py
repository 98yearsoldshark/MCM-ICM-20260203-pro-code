"""Q2 可视化：TTE 预测 + 不确定性 + drivers（paper/study 两种模式）。"""

from __future__ import annotations

import csv
import random
from datetime import datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from mcm26a.analysis import default_policy_actions
from mcm26a.analysis.q3_sensitivity import q3_param_names
from mcm26a.analysis.q2_drivers import (
    component_driver_specs,
    mechanism_driver_specs,
    power_component_variant,
    power_mechanism_variant,
)
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.uq import apply_q2_uq_sample, sample_q2_uq

from .style import PlotMode, apply_style, ensure_dir, get_cmap_tte, savefig


@dataclass(frozen=True)
class PlotBatchConfigQ2:
    """绘图批量配置（Q2）。"""

    scenarios_path: Path
    power_params_stateful_path: Path
    phone_aging_path: Path
    out_dir: Path
    reports_dir: Path | None = None
    dt_s: float = 5.0
    soc0_list: tuple[float, ...] = (1.0, 0.75, 0.5, 0.25)
    uq_samples: int = 40
    uq_seed: int = 1
    driver_seeds: int = 25
    driver_soc0: float = 1.0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _glossary_text() -> str:
    return (
        "术语说明：\n"
        "- TTE（Time-to-Empty，耗尽时间）：从当前初始电量（SOC0）开始，在给定场景下电池到达关机阈值前的剩余时间。\n"
        "- variant（变体）：在同一“场景”框架下，仅改变少量条件（如网络制式/信号强弱/亮度）形成的对照版本。\n"
        "- RRC 尾态（TAIL）：网络传输结束后，基带仍维持一段高功耗状态；频繁小流量会反复触发尾态，从而导致“协同放大”。\n"
        "- 热节流/限频（thermal throttling）：温度过高时系统压低 CPU/GPU 等的瞬时功耗。\n"
        "  本模型采用保守近似：仅缩放功耗，不建模“同一任务变慢导致持续更久”的闭环。\n"
        "- drivers（驱动因素）：导致续航变化最大的因素（屏幕/网络/后台/温度等），用能耗占比与 ΔTTE 反事实共同刻画。\n"
        "- 欠压截止：当端电压 V_term 下降到 V_cut（或出现不可供电边界）即关机；常见于高负载、低温、老化或弱信号放大功耗时。"
    )

def _glossary_text_fig05_oat() -> str:
    """图 02（条件对照矩阵）学习版专用的精简术语说明。

    说明：全局 _glossary_text() 过长，容易与坐标轴标注挤在一起，影响读图体验。
    这里仅保留对本图最关键的几个概念：TTE/variant/OAT/读图方式。
    """

    return (
        "术语说明（本图）：\n"
        "- TTE（Time-to-Empty，耗尽时间）：从初始电量 SOC0 开始，到首次触达关机阈值前的剩余时间。\n"
        "- variant（条件对照）：在同一场景脚本下，仅切换 1 个条件（例如高亮度/弱信号/蜂窝网络/温度）。\n"
        "- OAT（One-at-a-time，单因素扰动）：只改一个条件，其余条件保持 baseline（基准工况）不变。\n"
        "- 读图：每格为 ΔTTE/TTE_baseline（%），红色=续航缩短，绿色=续航变长。"
    )


def _scenario_ids(raw: dict[str, Any]) -> list[str]:
    return list(raw.get("scenarios", {}).keys())


def _scenario_title(raw: dict[str, Any], sid: str) -> str:
    return str(raw["scenarios"][sid].get("title_zh", sid))

def _variant_label_zh(variant: str) -> str:
    if variant in ("-", "", None):
        return "基线"
    m = {
        # 标准化 OAT 条件（no12 口径）：统一 x 轴
        "cond_brightness_high": "高亮度",
        "cond_signal_poor": "弱信号",
        "cond_radio_cellular": "网络切换：蜂窝",
        "cond_temp_cold": "低温（-15°C）",
        "cond_temp_hot": "高温（38°C）",
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
        "poor_signal_rest": "休止段 弱信号",
        "cold_outdoor": "低温户外",
        "hot_summer": "炎热夏季",
    }
    return m.get(str(variant), str(variant))


def _stats_dict_from_long_csv(
    raw: dict[str, Any],
    *,
    rows: list[dict[str, str]],
    soc0: float,
) -> dict[str, dict[str, dict[str, float]]]:
    """把 long-form CSV（scenario_id, variant, mean_h, ...）转为 {sid:{variant:{stats}}}。"""

    sids = _scenario_ids(raw)
    sid_set = set(str(x) for x in sids)
    out: dict[str, dict[str, dict[str, float]]] = {sid: {} for sid in sids}
    for r in rows:
        sid = str(r.get("scenario_id", ""))
        if sid not in sid_set:
            continue
        try:
            if float(r.get("soc0", "nan")) != float(soc0):
                continue
        except Exception:
            continue
        v = str(r.get("variant", "-"))
        out[sid][v] = {
            "n": float(r.get("n", "nan")),
            "mean_h": float(r.get("mean_h", "nan")),
            "p05_h": float(r.get("p05_h", "nan")),
            "p50_h": float(r.get("p50_h", "nan")),
            "p95_h": float(r.get("p95_h", "nan")),
            "p_cutoff": float(r.get("p_cutoff", "nan")),
            "p_soc_min": float(r.get("p_soc_min", "nan")),
            "p_insufficient_power": float(r.get("p_insufficient_power", "nan")),
        }
    return out


def _oat_condition_stats_from_report(
    raw: dict[str, Any],
    *,
    reports_dir: Path,
    soc0: float,
) -> dict[str, dict[str, dict[str, float]]]:
    """读取 OAT 条件统计表（conditions_oat_stats.csv），用于“统一 x 轴”的图 02。"""

    p = Path(reports_dir) / "conditions_oat_stats.csv"
    if not p.exists():
        raise FileNotFoundError(str(p))
    rows = _read_csv(p)
    out = _stats_dict_from_long_csv(raw, rows=rows, soc0=float(soc0))

    # 基本 sanity：每个场景应至少含 baseline（variant='-'）
    for sid in _scenario_ids(raw):
        if "-" not in (out.get(sid, {}) or {}):
            raise ValueError("conditions_oat_stats.csv 缺少 baseline 行（variant='-'）")
    return out

def _variant_stats_from_report(
    raw: dict[str, Any],
    *,
    reports_dir: Path,
    soc0: float,
) -> dict[str, dict[str, dict[str, float]]]:
    """从 run_q2_report.py 输出恢复“baseline+variants”统计。

    目的：
    - 与报表同源，避免 make_q2_plots.py 与 run_q2_report.py 各自仿真导致数值不一致；
    - 让 figure.png 与 other/data.csv 可追溯到同一批 CSV。

    依赖：
    - out_reports/q2/tte_summary.csv（必须；需包含 variants 才能替代即时仿真）
    - out_reports/q2/termination_stats.csv（可选；用于补充终止概率）
    """

    reports_dir = Path(reports_dir)
    sids = _scenario_ids(raw)
    sid_set = set(str(x) for x in sids)

    # 0) 优先读 variants_stats.csv（更轻：不要求 UQ 大样本，且明确包含 variants；用于保证图 02 同源）
    vstats_csv = reports_dir / "variants_stats.csv"
    if vstats_csv.exists():
        rows = _read_csv(vstats_csv)
        out: dict[str, dict[str, dict[str, float]]] = {sid: {} for sid in sids}
        for r in rows:
            sid = str(r.get("scenario_id", ""))
            if sid not in sid_set:
                continue
            try:
                if float(r.get("soc0", "nan")) != float(soc0):
                    continue
            except Exception:
                continue
            v = str(r.get("variant", "-"))
            out[sid][v] = {
                "n": float(r.get("n", "nan")),
                "mean_h": float(r.get("mean_h", "nan")),
                "p05_h": float(r.get("p05_h", "nan")),
                "p50_h": float(r.get("p50_h", "nan")),
                "p95_h": float(r.get("p95_h", "nan")),
                "p_cutoff": float(r.get("p_cutoff", "nan")),
                "p_soc_min": float(r.get("p_soc_min", "nan")),
                "p_insufficient_power": float(r.get("p_insufficient_power", "nan")),
            }

        any_variant = any(v != "-" for sid in sids for v in out.get(sid, {}).keys())
        if not any_variant:
            raise ValueError("variants_stats.csv 不包含 variants 行：请检查 run_q2_variants_stats.py 的输出")

        # 完整性检查：若新增了场景但 variants_stats.csv 尚未更新，可能导致某些 sid 缺 baseline（-）。
        # 此时宁可回退到 tte_summary.csv（UQ 报表，通常更全），也不要让下游图表直接 KeyError。
        missing_baseline = [sid for sid in sids if "-" not in (out.get(sid, {}) or {})]
        if missing_baseline:
            raise ValueError(f"variants_stats.csv 不完整（缺 baseline）：{missing_baseline}")

        return out

    # 1) 退化：从 UQ 报表 tte_summary.csv 中恢复（要求 run_q2_report.py --include-variants）
    summ = reports_dir / "tte_summary.csv"
    if not summ.exists():
        raise FileNotFoundError(f"缺少报表：{summ}")

    rows = _read_csv(summ)
    out = {sid: {} for sid in sids}
    for r in rows:
        sid = str(r.get("scenario_id", ""))
        if sid not in sid_set:
            continue
        try:
            if float(r.get("soc0", "nan")) != float(soc0):
                continue
        except Exception:
            continue
        v = str(r.get("variant", "-"))
        out[sid][v] = {
            "n": float(r.get("n", "nan")),
            "mean_h": float(r.get("mean_h", "nan")),
            "p05_h": float(r.get("p05_h", "nan")),
            "p50_h": float(r.get("p50_h", "nan")),
            "p95_h": float(r.get("p95_h", "nan")),
        }

    any_variant = any(v != "-" for sid in sids for v in out.get(sid, {}).keys())
    if not any_variant:
        raise ValueError("tte_summary.csv 不包含 variants：请用 run_q2_report.py --include-variants 或 run_q2_variants_stats.py 生成")

    # 补充终止概率（可选）
    term = reports_dir / "termination_stats.csv"
    if term.exists():
        try:
            trows = _read_csv(term)
            key: dict[tuple[str, str], dict[str, str]] = {}
            for rr in trows:
                try:
                    if float(rr.get("soc0", "nan")) != float(soc0):
                        continue
                except Exception:
                    continue
                sid = str(rr.get("scenario_id", ""))
                if sid not in sid_set:
                    continue
                v = str(rr.get("variant", "-"))
                key[(sid, v)] = rr

            for sid in sids:
                for vname in list(out.get(sid, {}).keys()):
                    rr = key.get((sid, vname))
                    if rr is None:
                        out[sid][vname].update({"p_cutoff": float("nan"), "p_soc_min": float("nan"), "p_insufficient_power": float("nan")})
                        continue
                    out[sid][vname].update(
                        {
                            "p_cutoff": float(rr.get("p_cutoff", "nan")),
                            "p_soc_min": float(rr.get("p_soc_min", "nan")),
                            "p_insufficient_power": float(rr.get("p_insufficient_power", "nan")),
                        }
                    )
        except Exception:
            pass

    return out


def _fig11_prcc_heatmap_from_report(
    raw: dict[str, Any],
    *,
    sens_rows: list[dict[str, str]],
    soc0: float,
    mode: PlotMode,
):
    """从 run_q2_report.py 的 CSV 输出绘制 PRCC 热力图（更快，不重复仿真）。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    ylabels = [_scenario_title(raw, sid) for sid in sids]

    # 只看基线 variant（避免把“条件变体”混进参数不确定性）
    rows = [r for r in sens_rows if str(r.get("variant", "-")) == "-" and float(r.get("soc0", "nan")) == float(soc0)]
    if not rows:
        raise ValueError("param_sensitivity.csv 中缺少所需行：请先运行 scripts/run_q2_report.py 生成 out_reports/q2/param_sensitivity.csv")

    params = q3_param_names()
    pzh = {str(r.get("param", "")): str(r.get("param_zh", r.get("param", ""))) for r in rows}
    xlabels = [pzh.get(p, p) for p in params]

    key = {(str(r["scenario_id"]), str(r["param"])): float(r["prcc"]) for r in rows if "scenario_id" in r and "param" in r and "prcc" in r}
    mat = np.full((len(sids), len(params)), np.nan, dtype=float)
    for i, sid in enumerate(sids):
        for j, p in enumerate(params):
            mat[i, j] = float(key.get((sid, p), float("nan")))

    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    im = ax.imshow(mat, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_yticks(np.arange(len(sids)))
    ax.set_yticklabels(ylabels)
    ax.set_xticks(np.arange(len(params)))
    ax.set_xticklabels(xlabels, rotation=20, ha="right")
    ax.set_title(f"Q2：参数级敏感性 PRCC（输出：TTE，SOC0={int(round(100*soc0))}%）{style.title_suffix}")

    cbar = fig.colorbar(im, ax=ax, shrink=0.95)
    cbar.set_label("PRCC（-1~1）")

    if style.annotate:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                if np.isnan(v):
                    continue
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8, color="black")

        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：PRCC（Partial Rank Correlation Coefficient）衡量“控制其它参数后”，某参数对 TTE 的单调影响强弱。\n"
            "- |PRCC| 越大：该参数越可能主导 TTE 的不确定性；正号表示参数↑使 TTE↑（更省电/更耐用），负号相反。\n"
            "- 本图来自 UQ 抽样样本表（out_reports/q2/param_sensitivity.csv），不重复仿真。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig13_spearman_heatmap_from_report(
    raw: dict[str, Any],
    *,
    sens_rows: list[dict[str, str]],
    soc0: float,
    mode: PlotMode,
):
    """从 run_q2_report.py 的 CSV 输出绘制 Spearman 热力图（与 PRCC 互为验证）。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    ylabels = [_scenario_title(raw, sid) for sid in sids]

    rows = [r for r in sens_rows if str(r.get("variant", "-")) == "-" and float(r.get("soc0", "nan")) == float(soc0)]
    if not rows:
        raise ValueError("param_sensitivity.csv 中缺少所需行：请先运行 scripts/run_q2_report.py")

    params = q3_param_names()
    pzh = {str(r.get("param", "")): str(r.get("param_zh", r.get("param", ""))) for r in rows}
    xlabels = [pzh.get(p, p) for p in params]

    key = {
        (str(r["scenario_id"]), str(r["param"])): float(r["spearman"])
        for r in rows
        if "scenario_id" in r and "param" in r and "spearman" in r
    }
    mat = np.full((len(sids), len(params)), np.nan, dtype=float)
    for i, sid in enumerate(sids):
        for j, p in enumerate(params):
            mat[i, j] = float(key.get((sid, p), float("nan")))

    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    im = ax.imshow(mat, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_yticks(np.arange(len(sids)))
    ax.set_yticklabels(ylabels)
    ax.set_xticks(np.arange(len(params)))
    ax.set_xticklabels(xlabels, rotation=20, ha="right")
    ax.set_title(f"Q2：参数级敏感性 Spearman（输出：TTE，SOC0={int(round(100*soc0))}%）{style.title_suffix}")

    cbar = fig.colorbar(im, ax=ax, shrink=0.95)
    cbar.set_label("Spearman（-1~1）")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：Spearman 衡量“单调相关性”，不控制其它参数；PRCC 则控制其它参数，通常更适合用于回答“谁主导不确定性”。\n"
            "我们同时给出两者，用于交叉验证：若两者符号一致且绝对值都大，结论更稳健。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig12_prcc_rank_overall_from_report(
    *,
    overall_rows: list[dict[str, str]],
    soc0: float,
    mode: PlotMode,
    top_k: int = 10,
):
    """从 overall.csv 输出绘制“平均 |PRCC| 排名”（回答哪些参数最导致 TTE 波动）。"""

    style = apply_style(mode)

    rows = [r for r in overall_rows if float(r.get("soc0", "nan")) == float(soc0)]
    items: list[tuple[str, float]] = []
    for r in rows:
        try:
            v = float(r.get("mean_abs_prcc", "nan"))
        except Exception:
            v = float("nan")
        if not np.isfinite(v):
            continue
        items.append((str(r.get("param_zh", r.get("param", "?"))), float(v)))
    items.sort(key=lambda kv: kv[1], reverse=True)
    items = items[: int(top_k)]
    if not items:
        raise ValueError("param_sensitivity_overall.csv 中没有可用的 mean_abs_prcc 行")

    labels = [k for (k, _) in items][::-1]
    vals = [v for (_, v) in items][::-1]

    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    ax.barh(np.arange(len(vals)), vals, color="#4C78A8", alpha=0.9)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("按场景平均 |PRCC|")
    ax.set_xlim(0.0, 1.0)
    ax.set_title(f"Q2：哪些参数最导致 TTE 波动（SOC0={int(round(100*soc0))}%）{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：对每个场景分别计算 PRCC，再对 |PRCC| 取平均得到“总体敏感度排名”。\n"
            "这回答的是“参数不确定性驱动”，而不是“用户策略动作驱动”。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _load_common(cfg: PlotBatchConfigQ2) -> tuple[dict[str, Any], PowerParams1Stateful, BatteryParams3Aging, PowerParams0]:
    raw = load_scenarios_json(cfg.scenarios_path)
    power1 = PowerParams1Stateful.from_json(cfg.power_params_stateful_path)
    batt = BatteryParams3Aging.from_json(cfg.phone_aging_path)

    # simulate_model3_aging 的签名里保留了 power_params（用于旧功耗模型）；
    # 当传入 power_model 时它会被忽略。这里读取一个 v0 作为占位符，避免修改大量旧接口。
    cfg_dir = Path(cfg.scenarios_path).resolve().parent
    power0_dummy = PowerParams0.from_json(cfg_dir / "power_params_v0.json")
    return raw, power1, batt, power0_dummy


def _quantiles(xs: list[float], qs: tuple[float, ...] = (0.05, 0.5, 0.95)) -> list[float]:
    if not xs:
        return [float("nan")] * len(qs)
    arr = np.array(xs, dtype=float)
    return [float(np.quantile(arr, q)) for q in qs]


def _tte_samples_uq(
    raw: dict[str, Any],
    *,
    base_power1: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0_list: tuple[float, ...],
    n: int,
    seed: int,
    cache_dir: Path,
) -> dict[tuple[str, float], list[float]]:
    """对参数做采样 + 后台随机过程：输出每 (scenario_id, soc0) 的 TTE 样本列表（小时）。"""

    cache_dir = ensure_dir(cache_dir)
    cache_ver = "v5"  # 变更功耗参数/抽样维度/功耗行为时请递增，避免读到旧缓存（no7 升级：APL/大核小核/连续尾态/backlog）
    soc_tag = "_".join(f"{x:.3f}".replace(".", "p") for x in soc0_list)
    cache_path = cache_dir / f"q2_tte_uq_{cache_ver}_dt{dt_s:.2f}_soc{soc_tag}_n{int(n)}_seed{int(seed)}.npz"

    if cache_path.exists():
        try:
            z = np.load(cache_path, allow_pickle=False)
            sids = [str(x) for x in z["sids"].tolist()]
            socs = [float(x) for x in z["socs"].tolist()]
            out: dict[tuple[str, float], list[float]] = {}
            for sid in sids:
                for soc0 in socs:
                    out[(sid, float(soc0))] = z[f"tte_{sid}_soc{soc0:.3f}"].astype(float).tolist()
            return out
        except Exception:
            pass

    sids = _scenario_ids(raw)
    out: dict[tuple[str, float], list[float]] = {(sid, float(soc0)): [] for sid in sids for soc0 in soc0_list}

    for i in range(int(n)):
        rng = random.Random(int(seed) + i)
        s = sample_q2_uq(rng)
        p_i, b_i = apply_q2_uq_sample(base_power1, base_batt, s)

        for sid_idx, sid in enumerate(sids):
            sc = materialize_scenario(raw, sid)
            for soc_idx, soc0 in enumerate(soc0_list):
                # 每次仿真都使用独立 power_model（避免不同场景/不同 SOC 互相影响随机数流）
                sim_seed = int(seed) * 1_000_000 + i * 10_000 + sid_idx * 100 + soc_idx
                pm = StatefulPowerModel1(p_i, seed=sim_seed)
                res = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=b_i,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if res.tte_h is not None:
                    out[(sid, float(soc0))].append(float(res.tte_h))

    try:
        np.savez_compressed(
            cache_path,
            sids=np.array(sids, dtype=object),
            socs=np.array(list(soc0_list), dtype=float),
            **{
                f"tte_{sid}_soc{soc0:.3f}": np.array(out[(sid, float(soc0))], dtype=float)
                for sid in sids
                for soc0 in soc0_list
            },
        )
    except Exception:
        # 缓存写入失败不影响出图
        pass

    return out


def _tte_samples_uq_from_report(
    raw: dict[str, Any],
    *,
    reports_dir: Path,
    soc0_list: tuple[float, ...],
    variant: str = "-",
) -> dict[tuple[str, float], list[float]]:
    """从 out_reports/q2/te_samples.csv 读取样本，构造与 _tte_samples_uq 相同的返回结构。

    目的：
    - 保证“图像”与“报表/数据版本（data.csv）”同源；
    - 避免 make_q2_plots.py 与 run_q2_report.py 各跑一遍导致数值不一致。
    """

    path = Path(reports_dir) / "tte_samples.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少报表：{path}")

    rows = _read_csv(path)
    sids = _scenario_ids(raw)
    sid_set = set(str(x) for x in sids)
    soc_set = set(float(x) for x in soc0_list)

    out: dict[tuple[str, float], list[float]] = {(sid, float(soc0)): [] for sid in sids for soc0 in soc0_list}
    for r in rows:
        if str(r.get("variant", "-")) != str(variant):
            continue
        sid = str(r.get("scenario_id", ""))
        if sid not in sid_set:
            continue
        try:
            soc0 = float(r.get("soc0", "nan"))
            tte = float(r.get("tte_h", "nan"))
        except Exception:
            continue
        if (not np.isfinite(soc0)) or (soc0 not in soc_set):
            continue
        if not np.isfinite(tte):
            continue
        out[(sid, float(soc0))].append(float(tte))

    # 若报表里某些格子缺数据（极少见），就认为报表不完整，交给上层回退到“即时仿真”。
    if any(len(out[(sid, float(soc0))]) == 0 for sid in sids for soc0 in soc0_list):
        raise ValueError("tte_samples.csv 不完整：存在 (scenario_id,soc0) 没有样本")

    return out


def _soc_end_cutoff_from_report(
    raw: dict[str, Any],
    *,
    reports_dir: Path,
    soc0: float,
    variant: str = "-",
) -> dict[str, list[float]]:
    """从 tte_samples.csv 里筛出 status=cutoff 的 soc_end，用于欠压提前关机的分布图。"""

    path = Path(reports_dir) / "tte_samples.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少报表：{path}")

    rows = _read_csv(path)
    sids = _scenario_ids(raw)
    out: dict[str, list[float]] = {sid: [] for sid in sids}
    for r in rows:
        if str(r.get("variant", "-")) != str(variant):
            continue
        try:
            if float(r.get("soc0", "nan")) != float(soc0):
                continue
        except Exception:
            continue
        if str(r.get("status", "")) != "cutoff":
            continue
        sid = str(r.get("scenario_id", ""))
        if sid not in out:
            continue
        try:
            se = float(r.get("soc_end", "nan"))
        except Exception:
            continue
        if np.isfinite(se):
            out[sid].append(float(se))
    return out


def _fig01_tte_matrix(
    raw: dict[str, Any],
    *,
    samples: dict[tuple[str, float], list[float]],
    soc0_list: tuple[float, ...],
    lang: str,
    mode: PlotMode,
):
    style = apply_style(mode)

    sids = _scenario_ids(raw)

    def _fmt_ylabel(sid: str) -> str:
        """热力图 y 轴标签：更紧凑（论文更美观）。

        规则：
        - 中文括号 -> 英文括号；去掉空格
        - 对少数超长标签：把括号内说明移到第二行并简写
        """

        t = _scenario_title(raw, sid)
        t = str(t).replace("（", "(").replace("）", ")")
        t = t.replace(" ", "")
        if sid == "S2_navigation":
            return "导航\n(GPS+地图)"
        if sid == "S1b_browse":
            return "浏览/社交\n(频繁切换)"
        if sid == "S3_gaming":
            return "游戏\n(高CPU/GPU)"
        if sid == "S5_burst_recovery":
            return "高负载→休止\n(恢复效应)"
        return t

    def _fmt_ylabel_en(sid: str) -> str:
        # 英文版：保持紧凑，尽量不占横向空间
        m = {
            "S0_standby": "Standby\n(lightBG)",
            "S1b_browse": "Browse\n(social)",
            "S1_video": "Video\n(stream)",
            "S2_navigation": "Navigation\n(GPS+map)",
            "S3_gaming": "Gaming\n(highCPU/GPU)",
            "S4_mixed_day": "MixedDay\n(typical)",
            "S5_burst_recovery": "Burst→Rest\n(recovery)",
        }
        return m.get(sid, sid)

    if lang not in ("zh", "en"):
        raise ValueError(f"unknown lang: {lang!r}")

    ylabels = [_fmt_ylabel(sid) for sid in sids] if lang == "zh" else [_fmt_ylabel_en(sid) for sid in sids]
    # 说明：为提升可读性，我们把 SOC0 放到 y 轴、场景放到 x 轴（与旧版相反）。
    xlabels = ylabels  # 场景标签（紧凑、多行）
    ylabels_soc = [f"{int(round(100 * soc0))}%" for soc0 in soc0_list]

    mat = np.zeros((len(sids), len(soc0_list)), dtype=float)
    for i, sid in enumerate(sids):
        for j, soc0 in enumerate(soc0_list):
            xs = samples.get((sid, float(soc0)), [])
            mat[i, j] = float(np.mean(xs)) if xs else float("nan")

    # 交换坐标轴：现在矩阵形状为 (SOC0, scenario)
    mat = mat.T

    # 学习版会额外放一段较长的说明文本；把画布做得更高，避免遮挡热力图与坐标轴。
    # y 轴只有 4 个刻度（SOC0），可以把画布做得更“扁”。
    # paper 进一步压缩；study 仍需给底部解释文本留空间。
    fig_h = 3.3 if not style.annotate else 5.4
    fig, ax = plt.subplots(figsize=(10.2, fig_h))
    im = ax.imshow(mat, cmap=get_cmap_tte(), aspect="auto")
    ax.set_xticks(np.arange(len(sids)))
    ax.set_xticklabels(xlabels)
    ax.set_yticks(np.arange(len(soc0_list)))
    ax.set_yticklabels(ylabels_soc)
    if lang == "zh":
        ax.set_xlabel("使用场景")
        ax.set_ylabel("初始电量 SOC0")
        ax.set_title(f"Q2：初始电量 × 不同场景 的平均耗尽时间 TTE(小时){style.title_suffix}")
    else:
        ax.set_xlabel("Scenario")
        ax.set_ylabel("Initial SOC (SOC0)")
        ax.set_title(f"Q2: Mean TTE (h) by initial SOC × scenario{style.title_suffix}")

    cbar = fig.colorbar(im, ax=ax, shrink=0.95)
    cbar.set_label("TTE(小时)" if lang == "zh" else "TTE (h)")

    # 论文读者需要“直接读出数量级”，因此数值标注在 paper/study 两种模式都保留；
    # 学习版仅额外添加底部解释文本。
    vmin = float(np.nanmin(mat)) if np.isfinite(mat).any() else 0.0
    vmax = float(np.nanmax(mat)) if np.isfinite(mat).any() else 1.0
    denom = max(1e-12, vmax - vmin)
    for i in range(mat.shape[0]):  # y: SOC0
        for j in range(mat.shape[1]):  # x: scenario
            v = float(mat[i, j])
            if not np.isfinite(v):
                continue
            # 用背景色亮度自动选择黑/白字，避免换 colormap 后数字看不清。
            t = float((v - vmin) / denom)
            r, g, b, _ = im.cmap(t)
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            color = "#111111" if luminance >= 0.62 else "white"
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", color=color, fontsize=(9 if style.annotate else 8))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.34, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：每个单元格为该场景、该初始 SOC 下的平均 TTE（小时）。\n"
            "我们对关键参数做了先验采样，并在功耗层引入后台 Poisson 唤醒（不可预测性），因此结果应理解为“分布的均值”。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=8,
        )
    else:
        fig.tight_layout()
    return fig


def _fig02_tte_distribution(
    raw: dict[str, Any],
    *,
    samples: dict[tuple[str, float], list[float]],
    soc0: float,
    mode: PlotMode,
):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]
    data = [samples.get((sid, float(soc0)), []) for sid in sids]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    parts = ax.violinplot(data, showmeans=False, showmedians=True, showextrema=False)
    for pc in parts["bodies"]:
        pc.set_facecolor("#4C78A8")
        pc.set_edgecolor("#2F2F2F")
        pc.set_alpha(0.65)
    parts["cmedians"].set_color("#E45756")
    parts["cmedians"].set_linewidth(2.0)

    ax.set_xticks(np.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("耗尽时间 TTE（小时）")
    ax.set_title(f"Q2：TTE 分布（SOC0={soc0:.2f}）{style.title_suffix}")

    if style.annotate:
        # 标注 p05/p50/p95
        for i, sid in enumerate(sids, start=1):
            q05, q50, q95 = _quantiles(samples.get((sid, float(soc0)), []))
            if np.isnan(q50):
                continue
            ax.text(i, q95 + 0.2, f"[{q05:.1f}, {q95:.1f}]h", ha="center", fontsize=8)
            ax.text(i, q50 + 0.1, f"中位 {q50:.1f}h", ha="center", fontsize=8)

        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：小提琴图展示 TTE 的分布（不确定性来源：参数先验 + 后台随机唤醒）。\n"
            "红线为中位数；上方括号为 5%~95% 区间。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _variant_tte_stats(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, dict[str, dict[str, float]]]:
    """对每个场景：baseline + variants 统计 TTE（均值与分位数）。"""

    out: dict[str, dict[str, dict[str, float]]] = {}
    for sid_idx, sid in enumerate(_scenario_ids(raw)):
        spec = raw["scenarios"][sid]
        variants = list(spec.get("variants", {}).keys())
        vnames = ["-"] + [str(v) for v in variants]
        out[sid] = {}

        for vname in vnames:
            sc = materialize_scenario(raw, sid, variant=(None if vname == "-" else vname))
            xs: list[float] = []
            statuses: list[str] = []
            for k in range(int(n_seeds)):
                seed = int(seed0) + sid_idx * 100 + k
                pm = StatefulPowerModel1(base_power, seed=seed)
                r = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm,
                    battery_params=base_batt,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if r.tte_h is not None:
                    xs.append(float(r.tte_h))
                    statuses.append(str(r.status))

            n = len(xs)
            denom = float(n) if n > 0 else float("nan")
            counts = {
                "cutoff": float(sum(1 for s in statuses if s == "cutoff")),
                "soc_min": float(sum(1 for s in statuses if s == "soc_min")),
                "insufficient_power": float(sum(1 for s in statuses if s == "insufficient_power")),
            }
            out[sid][vname] = {
                "n": float(n),
                "mean_h": float(np.mean(xs)) if xs else float("nan"),
                "p05_h": float(np.quantile(np.array(xs, dtype=float), 0.05)) if xs else float("nan"),
                "p50_h": float(np.quantile(np.array(xs, dtype=float), 0.50)) if xs else float("nan"),
                "p95_h": float(np.quantile(np.array(xs, dtype=float), 0.95)) if xs else float("nan"),
                "p_cutoff": float(counts["cutoff"] / denom) if np.isfinite(denom) else float("nan"),
                "p_soc_min": float(counts["soc_min"] / denom) if np.isfinite(denom) else float("nan"),
                "p_insufficient_power": float(counts["insufficient_power"] / denom) if np.isfinite(denom) else float("nan"),
            }

    return out


def _fig05_variants_compare(
    raw: dict[str, Any],
    *,
    stats: dict[str, dict[str, dict[str, float]]],
    soc0: float,
    mode: PlotMode,
):
    style = apply_style(mode)

    # 论文版：希望“一张图看全”，因此改为矩阵热力图（场景×variant），直接呈现“相对缩短多少%”
    # 备注：绝对 TTE 已由图 01（矩阵）覆盖；这里用相对变化更贴合赛题问法（reductions in battery life）。
    from matplotlib.colors import TwoSlopeNorm

    sids = _scenario_ids(raw)

    # 变体列：取所有场景的 variants 并做一个更稳定的排序（可复现）
    all_variants: set[str] = set()
    for sid in sids:
        for v in list(stats.get(sid, {}).keys()):
            if v != "-":
                all_variants.add(str(v))

    # 先放“常见条件”，未知的放最后（字典序）
    preferred = [
        # OAT 条件（统一 x 轴）
        "cond_brightness_high",
        "cond_signal_poor",
        "cond_radio_cellular",
        "cond_temp_cold",
        "cond_temp_hot",
        "high_brightness",
        "wifi_poor_signal",
        "cellular_good_signal",
        "cellular_poor_signal",
        "cellular_stream",
        "cellular_browse",
        "wifi_navigation",
        "online_game",
        "rural_poor_signal",
        "poor_signal_standby",
        "poor_signal_rest",
        "local_play",
        "cold_outdoor",
        "hot_summer",
    ]
    preferred_idx = {k: i for i, k in enumerate(preferred)}

    def _vkey(v: str) -> tuple[int, str]:
        return (preferred_idx.get(v, 10_000), str(v))

    vlist = sorted(list(all_variants), key=_vkey)

    # 构造矩阵：ΔTTE / TTE_base（%）
    mat = np.full((len(sids), len(vlist)), np.nan, dtype=float)
    ann = [["" for _ in vlist] for _ in sids]
    # True 表示“该场景没有定义该变体”（N/A）；False 表示“有定义但数值缺失/异常”
    na_mask = np.zeros((len(sids), len(vlist)), dtype=bool)
    ylabels: list[str] = []
    for i, sid in enumerate(sids):
        base = float(stats.get(sid, {}).get("-", {}).get("mean_h", float("nan")))
        title = _scenario_title(raw, sid)
        # 不把基线小时数写进坐标轴（避免与图 01 的基线 TTE 因 dt/样本口径不同而造成读者困惑）
        ylabels.append(str(title))
        for j, v in enumerate(vlist):
            if str(v) not in (stats.get(sid, {}) or {}):
                na_mask[i, j] = True
                continue
            m = float(stats.get(sid, {}).get(v, {}).get("mean_h", float("nan")))
            if not (np.isfinite(base) and base > 1e-9 and np.isfinite(m)):
                continue
            dpct = (m - base) / base * 100.0
            mat[i, j] = float(dpct)
            if style.annotate:
                dh = m - base
                ann[i][j] = f"{dpct:+.0f}%\n({dh:+.1f}h)"
            else:
                ann[i][j] = f"{dpct:+.0f}%"

    # 颜色：负值（续航缩短）更红，正值更绿
    # 范围：为了论文可比性，采用固定范围并截断（过极端的值在 data.csv 中仍可见）
    vmin, vmax = -80.0, 20.0
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
    cmap = plt.cm.get_cmap("RdYlGn").copy()
    cmap.set_bad("#F0F0F0")

    fig_h = 4.6 + 0.16 * max(0, len(sids) - 6)
    if style.annotate:
        # 学习版底部有解释文本，需要额外高度避免与坐标轴挤在一起。
        fig_h += 1.8
    fig, ax = plt.subplots(figsize=(11.6, fig_h))
    im = ax.imshow(np.ma.masked_invalid(mat), cmap=cmap, norm=norm, aspect="auto")

    ax.set_yticks(np.arange(len(sids)))
    ax.set_yticklabels(ylabels)
    ax.set_xticks(np.arange(len(vlist)))
    ax.set_xticklabels([_variant_label_zh(v) for v in vlist], rotation=15, ha="right")
    ax.set_title(f"Q2：条件变体对续航的相对影响（SOC0={int(round(100*soc0))}%）{style.title_suffix}")

    # 网格线：增强读图（但不抢眼）
    ax.set_xticks(np.arange(-0.5, len(vlist), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(sids), 1), minor=True)
    ax.grid(which="minor", color="#000000", alpha=0.08, linestyle="-", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    # 标注：格内数字（paper 也保留，但更简洁；study 给两行）
    for i in range(len(sids)):
        for j in range(len(vlist)):
            # N/A：该场景没有定义该变体（在图上明确给一个“—”，避免误解为缺失/bug）
            if np.isnan(mat[i, j]) and na_mask[i, j]:
                ax.text(
                    j,
                    i,
                    "—",
                    ha="center",
                    va="center",
                    fontsize=10 if style.annotate else 9,
                    color="#777777",
                    alpha=0.85 if style.annotate else 0.55,
                )
                continue
            if not ann[i][j]:
                continue
            val = mat[i, j]
            # 深色背景用白字
            color = "white" if np.isfinite(val) and abs(float(val)) > 35 else "#111111"
            ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=8, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.92)
    cbar.set_label("相对变化：ΔTTE / TTE_baseline（%）")

    if style.annotate:
        # 预留更大的底部区域放置解释文本（中文行高更大；且学习版含两行格内标注）。
        fig.tight_layout(rect=(0.0, 0.30, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：每个格子表示“在同一场景下，仅改变某个条件（variant）”时，TTE 相对 baseline 的变化百分比。\n"
            "若出现灰色空格/“—”，表示该场景对该条件不适用（或该变体未定义）。\n"
            "红色越深表示续航缩短越严重；绿色表示续航变长（例如高温降低内阻带来少量延长）。\n\n"
            + _glossary_text_fig05_oat(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    return fig


def _fig14_termination_probs_temperature(
    raw: dict[str, Any],
    *,
    stats: dict[str, dict[str, dict[str, float]]],
    soc0: float,
    mode: PlotMode,
):
    """终止原因概率对比：baseline vs 温度 variants（cold/hot）。

说明：
- 该图用于回答题面 Q2 的 “where model performs well or poorly”（边界条件）：
  在低温/高负载等情况下，欠压 cutoff 或 discriminant 失败（insufficient_power）概率会更高。
- 这里使用的是“多随机种子重复”（功耗层随机过程）带来的概率，不等同于参数不确定性 UQ。
"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    nrows = len(sids)
    fig_h = 2.0 * nrows + (1.2 if style.annotate else 0.2)
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10.6, fig_h), sharex=False)
    if nrows == 1:
        axes = [axes]

    temp_variants = ["cold_outdoor", "hot_summer"]
    colors = {"cutoff": "#4C78A8", "soc_min": "#54A24B", "insufficient_power": "#E45756"}

    for ax, sid in zip(axes, sids):
        vnames_all = list(stats.get(sid, {}).keys())
        vnames = ["-"] + [v for v in temp_variants if v in vnames_all]

        p_cut = [float(stats[sid][v].get("p_cutoff", float("nan"))) for v in vnames]
        p_soc = [float(stats[sid][v].get("p_soc_min", float("nan"))) for v in vnames]
        p_ins = [float(stats[sid][v].get("p_insufficient_power", float("nan"))) for v in vnames]

        xs = np.arange(len(vnames))
        ax.bar(xs, p_cut, color=colors["cutoff"], alpha=0.85, label="欠压截止 cutoff")
        ax.bar(xs, p_soc, bottom=p_cut, color=colors["soc_min"], alpha=0.85, label="SOC 下限 soc_min")
        ax.bar(xs, p_ins, bottom=(np.array(p_cut) + np.array(p_soc)), color=colors["insufficient_power"], alpha=0.85, label="不可供电 insufficient_power")

        ax.set_ylim(0.0, 1.0)
        ax.set_xticks(xs)
        ax.set_xticklabels([_variant_label_zh(v) for v in vnames], rotation=12, ha="right")
        ax.set_ylabel("概率")
        ax.set_title(f"{_scenario_title(raw, sid)}：终止原因概率（SOC0={soc0:.2f}）{style.title_suffix}")

        if style.annotate:
            for i, (a, b, c) in enumerate(zip(p_cut, p_soc, p_ins)):
                if np.isfinite(a):
                    ax.text(i, min(0.98, a + 0.02), f"{a:.2f}", ha="center", va="bottom", fontsize=8, color="black")
                if np.isfinite(b) and b > 1e-6:
                    ax.text(i, min(0.98, a + b + 0.02), f"{b:.2f}", ha="center", va="bottom", fontsize=8, color="black")
                if np.isfinite(c) and c > 1e-6:
                    ax.text(i, min(0.98, a + b + c + 0.02), f"{c:.2f}", ha="center", va="bottom", fontsize=8, color="black")

    # 只放一个 legend（避免重复）
    axes[0].legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：每个子图展示同一场景下，baseline 与温度 variants 的终止原因概率分解。\n"
            "- cutoff：端电压降到 V_cut（常见于高负载、低温、老化/弱信号放大功耗）。\n"
            "- insufficient_power：判别式失败（电池无法提供该瞬时功率），属于模型边界/强约束失败信号。\n"
            "- soc_min：SOC 先到下限（更像“容量耗尽”）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig15_temperature_tte(
    raw: dict[str, Any],
    *,
    stats: dict[str, dict[str, dict[str, float]]],
    soc0: float,
    mode: PlotMode,
):
    """温度对 TTE 的影响：baseline vs 冷/热（均值 + 5%~95%）。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    nrows = len(sids)
    fig_h = 2.0 * nrows + (1.2 if style.annotate else 0.2)
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10.6, fig_h), sharex=False)
    if nrows == 1:
        axes = [axes]

    temp_variants = ["cold_outdoor", "hot_summer"]

    for ax, sid in zip(axes, sids):
        vnames_all = list(stats.get(sid, {}).keys())
        vnames = ["-"] + [v for v in temp_variants if v in vnames_all]

        means = [float(stats[sid][v].get("mean_h", float("nan"))) for v in vnames]
        p05 = [float(stats[sid][v].get("p05_h", float("nan"))) for v in vnames]
        p95 = [float(stats[sid][v].get("p95_h", float("nan"))) for v in vnames]
        errs = [max(0.0, m - lo) for m, lo in zip(means, p05)], [max(0.0, hi - m) for m, hi in zip(means, p95)]

        xs = np.arange(len(vnames))
        colors = ["#4C78A8" if v == "-" else "#E45756" for v in vnames]
        ax.bar(xs, means, yerr=errs, color=colors, alpha=0.85, capsize=3)
        ax.set_xticks(xs)
        ax.set_xticklabels([_variant_label_zh(v) for v in vnames], rotation=12, ha="right")
        ax.set_ylabel("TTE（小时）")
        ax.set_title(f"{_scenario_title(raw, sid)}：温度对 TTE 的影响（SOC0={soc0:.2f}）{style.title_suffix}")

        if style.annotate:
            for i, m in enumerate(means):
                if not np.isnan(m):
                    ax.text(i, m + 0.15, f"{m:.2f}h", ha="center", fontsize=8)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：对每个场景，仅改变环境温度（ambient_temp_c），其余使用模式不变。\n"
            "低温会通过“内阻上升 + 有效容量下降”缩短 TTE，并提高欠压提前关机的概率（见终止概率图）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _soc_end_samples(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, list[float]]:
    """每个场景采样关机时 SOC_end（用于欠压提前关机的可视化）。"""

    out: dict[str, list[float]] = {}
    for sid_idx, sid in enumerate(_scenario_ids(raw)):
        sc = materialize_scenario(raw, sid)
        xs: list[float] = []
        for k in range(int(n_seeds)):
            seed = int(seed0) + sid_idx * 100 + k
            pm = StatefulPowerModel1(base_power, seed=seed)
            r = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=base_batt,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            if r.status == "cutoff":
                xs.append(float(r.soc_end))
        out[sid] = xs
    return out


def _fig06_soc_end_boxplot(
    raw: dict[str, Any],
    *,
    soc_end: dict[str, list[float]],
    mode: PlotMode,
):
    style = apply_style(mode)
    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]
    data = [soc_end.get(sid, []) for sid in sids]

    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    bp = ax.boxplot(data, patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#72B7B2")
        patch.set_edgecolor("#333333")
        patch.set_alpha(0.75)
    for k in ("medians", "whiskers", "caps"):
        for line in bp[k]:
            line.set_color("#333333")

    ax.set_xticks(np.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("关机时 SOC_end（-）")
    ax.set_title(f"Q2：欠压提前关机的“剩余电量”分布（仅 cutoff 样本）{style.title_suffix}")
    ax.grid(axis="y", alpha=0.25)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：只统计 status=cutoff 的样本，展示关机瞬间的 SOC_end。\n"
            "若 SOC_end 显著高于 soc_min，说明并非“电量用尽”，而是高功率/高内阻/弱信号等导致端电压跌破 V_cut（欠压提前关机）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _uq_spread_metrics(xs: list[float]) -> dict[str, float]:
    """返回不确定性统计：均值/标准差/CV/分位数/宽度。"""

    if not xs:
        return {
            "n": 0.0,
            "mean": float("nan"),
            "std": float("nan"),
            "cv": float("nan"),
            "p05": float("nan"),
            "p50": float("nan"),
            "p95": float("nan"),
            "width90": float("nan"),
        }
    arr = np.array(xs, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    p05 = float(np.quantile(arr, 0.05))
    p50 = float(np.quantile(arr, 0.50))
    p95 = float(np.quantile(arr, 0.95))
    width = float(p95 - p05)
    cv = float("nan") if abs(mean) <= 1e-12 else float(std / mean)
    return {"n": float(len(xs)), "mean": mean, "std": std, "cv": cv, "p05": p05, "p50": p50, "p95": p95, "width90": width}


def _fig07_uq_spread_ranking(
    raw: dict[str, Any],
    *,
    samples: dict[tuple[str, float], list[float]],
    soc0: float,
    mode: PlotMode,
):
    """用 (p95-p05) 宽度对“不可预测性/不确定性”做排序。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)

    rows = []
    for sid in sids:
        xs = samples.get((sid, float(soc0)), [])
        m = _uq_spread_metrics(xs)
        rows.append((sid, m))

    rows.sort(key=lambda x: float(x[1]["width90"]) if not np.isnan(float(x[1]["width90"])) else -1e18, reverse=True)

    labels = [_scenario_title(raw, sid) for sid, _ in rows]
    widths = [float(m["width90"]) for _, m in rows]
    means = [float(m["mean"]) for _, m in rows]
    cvs = [float(m["cv"]) for _, m in rows]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    y = np.arange(len(labels))
    ax.barh(y, widths, color="#E45756", alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("不确定性宽度（p95 - p05，小时）")
    ax.set_title(f"Q2：不确定性宽度排名（SOC0={soc0:.2f}）{style.title_suffix}")

    if style.annotate:
        for i, (w, mu, cv) in enumerate(zip(widths, means, cvs)):
            if np.isnan(w) or np.isnan(mu):
                continue
            ax.text(w + 0.03, i, f"均值{mu:.2f}h  CV={cv:.2f}", va="center", fontsize=9)
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图用 TTE 的 5%~95% 区间宽度（p95-p05）刻画“不确定性/不可预测性”。\n"
            "宽度越大，说明同一场景在参数先验与行为波动下的 TTE 波动越大；这些场景通常也是模型更容易偏差的边界（突发/弱信号/强耦合）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _mechanism_driver_effects(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, float]:
    """机制化 drivers：逐项“去掉某机制”并计算平均 ΔTTE（小时）。"""

    mechs = mechanism_driver_specs()

    sids = _scenario_ids(raw)
    deltas: dict[str, list[float]] = {mid: [] for mid, _ in mechs}
    for k in range(int(n_seeds)):
        seed = int(seed0) + k
        for sid_idx, sid in enumerate(sids):
            sc = materialize_scenario(raw, sid)
            base_seed = seed * 10_000 + sid_idx

            pm0 = StatefulPowerModel1(base_power, seed=base_seed)
            r0 = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=base_batt,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            if r0.tte_h is None:
                continue

            for mid, _ in mechs:
                p2 = power_mechanism_variant(base_power, mech_id=mid)
                pm1 = StatefulPowerModel1(p2, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=base_batt,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if r1.tte_h is None:
                    continue
                deltas[mid].append(float(r1.tte_h) - float(r0.tte_h))

    return {mid: (float(np.mean(xs)) if xs else 0.0) for mid, xs in deltas.items()}


def _fig08_mechanism_drivers_tornado(
    raw: dict[str, Any],
    *,
    delta_h: dict[str, float],
    mode: PlotMode,
):
    style = apply_style(mode)
    name_zh = {mid: title for mid, title in mechanism_driver_specs()}

    items = [(k, float(v)) for k, v in delta_h.items()]
    items.sort(key=lambda x: abs(x[1]), reverse=True)
    labels = [name_zh.get(k, k) for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    y = np.arange(len(labels))
    colors = ["#54A24B" if v >= 0 else "#E45756" for v in vals]
    ax.barh(y, vals, color=colors, alpha=0.85)
    ax.axvline(0.0, color="#333333", lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("ΔTTE（小时）")
    ax.set_title(f"Q2：drivers（机制消融）对续航的平均影响{style.title_suffix}")

    if style.annotate:
        for i, v in enumerate(vals):
            dx = 0.05 if v >= 0 else -0.05
            ax.text(v + dx, i, f"{v:+.2f}h", va="center", ha="left" if v >= 0 else "right", fontsize=9)
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：与“策略动作”不同，该图直接对模型机制做消融（去掉尾态/弱信号惩罚/后台唤醒/交互项等），再观察 ΔTTE。\n"
            "ΔTTE 越大，说明该机制越可能是“快速掉电”的根因；ΔTTE 接近 0 则可作为“surprisingly little”的证据。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _component_driver_matrix(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[tuple[str, str], float]:
    """组件级 drivers：对每个场景输出“移除组件”带来的平均 ΔTTE（小时）。"""

    comps = component_driver_specs()
    sids = _scenario_ids(raw)

    # 收集每个 (scenario_id, comp_id) 的 ΔTTE 样本
    deltas: dict[tuple[str, str], list[float]] = {(sid, cid): [] for sid in sids for cid, _ in comps}

    for k in range(int(n_seeds)):
        seed = int(seed0) + k
        for sid_idx, sid in enumerate(sids):
            sc = materialize_scenario(raw, sid)
            base_seed = seed * 10_000 + sid_idx

            pm0 = StatefulPowerModel1(base_power, seed=base_seed)
            r0 = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=base_batt,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            if r0.tte_h is None:
                continue

            for cid, _ in comps:
                p2 = power_component_variant(base_power, comp_id=cid)
                pm1 = StatefulPowerModel1(p2, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=base_batt,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if r1.tte_h is None:
                    continue
                deltas[(sid, cid)].append(float(r1.tte_h) - float(r0.tte_h))

    return {(sid, cid): (float(np.mean(xs)) if xs else 0.0) for (sid, cid), xs in deltas.items()}


def _fig09_component_drivers_tornado(
    raw: dict[str, Any],
    *,
    delta_h: dict[str, float],
    mode: PlotMode,
):
    """组件级 drivers（整体平均）tornado：回答题面“哪些因素影响最大/最小”。"""

    style = apply_style(mode)
    name_zh = {cid: title for cid, title in component_driver_specs()}

    items = [(k, float(v)) for k, v in delta_h.items()]
    items.sort(key=lambda x: abs(x[1]), reverse=True)
    labels = [name_zh.get(k, k) for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    y = np.arange(len(labels))
    colors = ["#54A24B" if v >= 0 else "#E45756" for v in vals]
    ax.barh(y, vals, color=colors, alpha=0.85)
    ax.axvline(0.0, color="#333333", lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("ΔTTE（小时）")
    ax.set_title(f"Q2：drivers（组件级反事实）对续航的平均影响{style.title_suffix}")

    if style.annotate:
        for i, v in enumerate(vals):
            dx = 0.05 if v >= 0 else -0.05
            ax.text(v + dx, i, f"{v:+.2f}h", va="center", ha="left" if v >= 0 else "right", fontsize=9)
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图将某个组件的功耗贡献“置零”（理想化反事实），并观察平均 ΔTTE。\n"
            "ΔTTE 越大表示该组件越可能是快速掉电的主因；ΔTTE 接近 0 则可作为“surprisingly little”的证据。\n"
            "注意：该图用于归因/敏感性，不等同于真实手机可实现策略；真实可执行建议见策略动作 drivers 图。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig10_component_driver_matrix(
    raw: dict[str, Any],
    *,
    matrix: dict[tuple[str, str], float],
    mode: PlotMode,
):
    """按场景展示 drivers：直接对齐题面“in each case”。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    comps = component_driver_specs()

    ylabels = [_scenario_title(raw, sid) for sid in sids]
    xlabels = [title for _, title in comps]

    mat = np.zeros((len(sids), len(comps)), dtype=float)
    for i, sid in enumerate(sids):
        for j, (cid, _) in enumerate(comps):
            mat[i, j] = float(matrix.get((sid, cid), 0.0))

    vmax = float(np.nanmax(np.abs(mat))) if mat.size else 1.0
    vmax = max(0.5, vmax)  # 避免色条过于敏感

    # 学习版需要放更多解释文本；增加高度/下边距避免遮挡 x 轴标签。
    fig_h = 4.6 if not style.annotate else 6.9
    fig, ax = plt.subplots(figsize=(11.0, fig_h))
    im = ax.imshow(mat, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(np.arange(len(xlabels)))
    ax.set_xticklabels(xlabels, rotation=20, ha="right")
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels)
    ax.set_xlabel("drivers（组件级反事实）")
    ax.set_title(f"Q2：不同场景的 drivers 强度（平均 ΔTTE）{style.title_suffix}")

    cbar = fig.colorbar(im, ax=ax, shrink=0.95)
    cbar.set_label("ΔTTE（小时）")

    # drivers 矩阵也需要“格子里直接读数”；paper/study 两种模式都显示数值。
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = float(mat[i, j])
            # RdYlGn：中间浅黄，极端深绿/深红；极端用白字更清晰
            t = float(im.norm(v)) if im.norm is not None else 0.5
            color = "white" if (t <= 0.18 or t >= 0.82) else "#111111"
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", color=color, fontsize=(8 if style.annotate else 7))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.40, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图用于回答题面“每种情形下，哪些 drivers 导致快速掉电？”\n"
            "- 行表示不同使用场景；列表示移除某组件功耗后的续航增量（ΔTTE）。\n"
            "- 同一列在某些行接近 0，说明该 driver 在那些情形下影响 surprisingly little。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=8,
        )
    else:
        fig.tight_layout()
    return fig


def _driver_effects(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, float]:
    """粗粒度 drivers：用默认策略动作作为“单因子反事实”，估计平均 ΔTTE（小时）。"""

    actions = default_policy_actions()
    deltas: dict[str, list[float]] = {a.action_id: [] for a in actions}

    sids = _scenario_ids(raw)
    for s in range(int(n_seeds)):
        seed = int(seed0) + s
        for sid_idx, sid in enumerate(sids):
            sc0 = materialize_scenario(raw, sid)

            # 共同随机数（CRN）：baseline 与每个 action 使用同一个 seed（并从同一起点 RNG 状态开始）
            base_seed = seed * 10_000 + sid_idx
            pm0 = StatefulPowerModel1(base_power, seed=base_seed)
            r0 = simulate_model3_aging(
                sc0,
                power_params=power0_dummy,
                power_model=pm0,
                battery_params=base_batt,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            if r0.tte_h is None:
                continue

            for a in actions:
                sc1 = a.apply(sc0)
                pm1 = StatefulPowerModel1(base_power, seed=base_seed)
                r1 = simulate_model3_aging(
                    sc1,
                    power_params=power0_dummy,
                    power_model=pm1,
                    battery_params=base_batt,
                    soc0=float(soc0),
                    dt_s=float(dt_s),
                )
                if r1.tte_h is None:
                    continue
                deltas[a.action_id].append(float(r1.tte_h) - float(r0.tte_h))

    return {k: (float(np.mean(v)) if v else 0.0) for k, v in deltas.items()}


def _fig03_drivers_tornado(
    raw: dict[str, Any],
    *,
    driver_delta_h: dict[str, float],
    mode: PlotMode,
):
    style = apply_style(mode)

    name_zh = {
        "brightness_100": "降亮度（到100nits）",
        "disable_gps": "关闭 GPS",
        "force_wifi": "强制 Wi-Fi",
        "good_signal": "改善信号（poor->good）",
        "bg_low": "限制后台（统一low）",
    }

    items = [(k, float(v)) for k, v in driver_delta_h.items()]
    items.sort(key=lambda x: abs(x[1]), reverse=True)

    labels = [name_zh.get(k, k) for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    y = np.arange(len(labels))
    colors = ["#54A24B" if v >= 0 else "#E45756" for v in vals]
    ax.barh(y, vals, color=colors, alpha=0.85)
    ax.axvline(0.0, color="#333333", lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("ΔTTE（小时）")
    ax.set_title(f"Q2：drivers（单因子反事实）对续航的平均影响{style.title_suffix}")

    if style.annotate:
        for i, v in enumerate(vals):
            dx = 0.05 if v >= 0 else -0.05
            ax.text(v + dx, i, f"{v:+.2f}h", va="center", ha="left" if v >= 0 else "right", fontsize=9)

        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：横轴为策略相对基线的续航变化 ΔTTE（小时）。\n"
            "该图是 drivers 识别的一种实现：把每个因素单独调整，其它保持不变，观察边际影响。\n"
            "ΔTTE 绝对值越大，说明该因素对续航越关键；接近 0 的因素可被描述为“surprisingly little”。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _energy_share_mean(
    raw: dict[str, Any],
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, dict[str, float]]:
    """每个场景的平均能耗占比（%）。"""

    sids = _scenario_ids(raw)
    comps = [
        "base_Wh",
        "screen_Wh",
        "cpu_Wh",
        "gpu_Wh",
        "radio_Wh",
        "gps_Wh",
        "background_Wh",
        "interaction_Wh",
    ]

    out: dict[str, dict[str, float]] = {sid: {c: 0.0 for c in comps} for sid in sids}
    for sid_idx, sid in enumerate(sids):
        acc = {c: [] for c in comps}
        sc = materialize_scenario(raw, sid)
        for k in range(int(n_seeds)):
            seed = int(seed0) + k
            pm = StatefulPowerModel1(base_power, seed=seed * 10_000 + sid_idx)
            r = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=base_batt,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            total = float(r.energy_used_Wh) if r.energy_used_Wh else 0.0
            if total <= 0.0:
                continue
            for c in comps:
                v = float(r.energy_components_Wh.get(c, 0.0))
                acc[c].append(v / total * 100.0)

        for c in comps:
            out[sid][c] = float(np.mean(acc[c])) if acc[c] else 0.0
    return out


def _fig04_energy_share(
    raw: dict[str, Any],
    *,
    share_pct: dict[str, dict[str, float]],
    mode: PlotMode,
):
    style = apply_style(mode)

    sids = _scenario_ids(raw)
    labels = [_scenario_title(raw, sid) for sid in sids]

    comps = [
        "base_Wh",
        "screen_Wh",
        "cpu_Wh",
        "gpu_Wh",
        "radio_Wh",
        "gps_Wh",
        "background_Wh",
        "interaction_Wh",
    ]
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

    data = np.array([[float(share_pct[sid].get(c, 0.0)) for c in comps] for sid in sids], dtype=float)

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    bottom = np.zeros(len(sids))
    for j, c in enumerate(comps):
        ax.bar(labels, data[:, j], bottom=bottom, label=comp_zh.get(c, c), color=colors[j], alpha=0.95)
        bottom += data[:, j]

    ax.set_ylabel("能耗占比（%）")
    ax.set_ylim(0, 100)
    ax.set_title(f"Q2：不同场景的能耗构成（平均占比）{style.title_suffix}")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.18), frameon=False)
    ax.grid(axis="y", alpha=0.25)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：该图展示从 SOC0 放电到关机阈值为止，各组件累积能耗占比（每根柱子总和≈100%）。\n"
            "占比高的组件是主要耗电驱动；“交互”项用于刻画协同作用（例如屏幕+网络/网络+高CPU）。\n\n"
            + _glossary_text(),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig16_termination_probs_from_report(
    raw: dict[str, Any],
    *,
    term_rows: list[dict[str, str]],
    soc0: float,
    mode: PlotMode,
):
    """从 run_q2_report.py 输出绘制“终止原因概率”（UQ 传播后的统计）。"""

    style = apply_style(mode)
    sids = _scenario_ids(raw)
    ylabels = [_scenario_title(raw, sid) for sid in sids]

    # 只看基线（variant='-'），与论文主表一致
    rows = [r for r in term_rows if str(r.get("variant", "-")) == "-" and float(r.get("soc0", "nan")) == float(soc0)]
    if not rows:
        raise ValueError("termination_stats.csv 中缺少所需行：请先运行 scripts/run_q2_report.py")

    key = {str(r["scenario_id"]): r for r in rows if "scenario_id" in r}
    p_cut = [float(key.get(sid, {}).get("p_cutoff", "nan")) for sid in sids]
    p_soc = [float(key.get(sid, {}).get("p_soc_min", "nan")) for sid in sids]
    p_ins = [float(key.get(sid, {}).get("p_insufficient_power", "nan")) for sid in sids]

    x = np.arange(len(sids))
    fig, ax = plt.subplots(figsize=(11.0, 4.6))
    ax.bar(x, p_cut, color="#4C78A8", alpha=0.85, label="欠压截止 cutoff")
    ax.bar(x, p_soc, bottom=p_cut, color="#54A24B", alpha=0.85, label="SOC 下限 soc_min")
    ax.bar(x, p_ins, bottom=(np.array(p_cut) + np.array(p_soc)), color="#E45756", alpha=0.85, label="不可供电 insufficient_power")
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(ylabels, rotation=12, ha="right")
    ax.set_ylabel("概率")
    ax.set_title(f"Q2：终止原因概率（UQ 传播后统计，SOC0={int(round(100*soc0))}%）{style.title_suffix}")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.18))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：该概率来自 UQ 抽样后的大量仿真样本（out_reports/q2/termination_stats.csv），同时包含参数不确定与功耗层随机过程。\n"
            "它用于回答题面 Q2 的“模型在哪里表现好/差”：若某场景 p_insufficient_power 较高，说明处于模型边界（电池无法提供该瞬时功率）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def make_q2_plot_batch(cfg: PlotBatchConfigQ2, *, mode: PlotMode) -> list[Path]:
    """生成 Q2 图表并保存，返回生成的文件路径列表。"""

    raw, power1, batt, power0_dummy = _load_common(cfg)
    out_dir = ensure_dir(cfg.out_dir / "q2" / mode)
    cache_dir = ensure_dir(cfg.out_dir / "q2" / "_cache")

    # --------------------------------
    # 1) TTE 样本：优先使用 run_q2_report.py 输出（同源），缺失时再回退到“即时仿真”
    # --------------------------------
    samples: dict[tuple[str, float], list[float]] | None = None
    if cfg.reports_dir is not None:
        try:
            samples = _tte_samples_uq_from_report(
                raw,
                reports_dir=Path(cfg.reports_dir),
                soc0_list=tuple(float(x) for x in cfg.soc0_list),
                variant="-",
            )
        except Exception:
            samples = None

    if samples is None:
        samples = _tte_samples_uq(
            raw,
            base_power1=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0_list=tuple(float(x) for x in cfg.soc0_list),
            n=int(cfg.uq_samples),
            seed=int(cfg.uq_seed),
            cache_dir=cache_dir,
        )

    figs: list[tuple[str, str, Any]] = [
        ("tte", "01_tte_matrix.png", _fig01_tte_matrix(raw, samples=samples, soc0_list=cfg.soc0_list, lang="zh", mode=mode)),
        ("tte", "01_tte_matrix_en.png", _fig01_tte_matrix(raw, samples=samples, soc0_list=cfg.soc0_list, lang="en", mode=mode)),
        ("uq", "02_tte_distribution_soc1.png", _fig02_tte_distribution(raw, samples=samples, soc0=float(cfg.driver_soc0), mode=mode)),
    ]

    figs.append(("uq", "07_uq_spread_ranking.png", _fig07_uq_spread_ranking(raw, samples=samples, soc0=float(cfg.driver_soc0), mode=mode)))

    # --------------------------------
    # 2) 图 02：条件对比（统一 x 轴，OAT）；以及温度对照（使用场景自带 variants）
    # --------------------------------
    vstats_variants: dict[str, dict[str, dict[str, float]]] | None = None
    if cfg.reports_dir is not None:
        try:
            vstats_variants = _variant_stats_from_report(raw, reports_dir=Path(cfg.reports_dir), soc0=float(cfg.driver_soc0))
        except Exception:
            vstats_variants = None

    if vstats_variants is None:
        vstats_variants = _variant_tte_stats(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 1000,
        )

    # 图 02：优先用“统一 x 轴”的 OAT 条件统计表；若缺失则回退到旧版场景 variants
    cstats: dict[str, dict[str, dict[str, float]]] | None = None
    if cfg.reports_dir is not None:
        try:
            cstats = _oat_condition_stats_from_report(raw, reports_dir=Path(cfg.reports_dir), soc0=float(cfg.driver_soc0))
        except Exception:
            cstats = None
    if cstats is None:
        cstats = vstats_variants

    figs.append(("variants", "05_variants_compare.png", _fig05_variants_compare(raw, stats=cstats, soc0=float(cfg.driver_soc0), mode=mode)))
    figs.append(
        (
            "temperature",
            "15_temperature_tte_compare.png",
            _fig15_temperature_tte(raw, stats=vstats_variants, soc0=float(cfg.driver_soc0), mode=mode),
        )
    )
    figs.append(
        (
            "temperature",
            "14_termination_probs_temperature.png",
            _fig14_termination_probs_temperature(raw, stats=vstats_variants, soc0=float(cfg.driver_soc0), mode=mode),
        )
    )

    soc_end: dict[str, list[float]] | None = None
    if cfg.reports_dir is not None:
        try:
            soc_end = _soc_end_cutoff_from_report(raw, reports_dir=Path(cfg.reports_dir), soc0=float(cfg.driver_soc0), variant="-")
        except Exception:
            soc_end = None
    if soc_end is None:
        soc_end = _soc_end_samples(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 2000,
        )
    figs.append(("uq", "06_soc_end_boxplot.png", _fig06_soc_end_boxplot(raw, soc_end=soc_end, mode=mode)))

    driver_delta_h: dict[str, float] | None = None
    if cfg.reports_dir is not None:
        p = Path(cfg.reports_dir) / "drivers_delta.csv"
        if p.exists():
            try:
                rows = _read_csv(p)
                driver_delta_h = {str(r.get("action_id", "")): float(r.get("mean_delta_h", "nan")) for r in rows if r.get("action_id")}
            except Exception:
                driver_delta_h = None
    if driver_delta_h is None:
        driver_delta_h = _driver_effects(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 100,
        )
    figs.append(("drivers", "03_drivers_tornado.png", _fig03_drivers_tornado(raw, driver_delta_h=driver_delta_h, mode=mode)))

    mech_delta_h: dict[str, float] | None = None
    if cfg.reports_dir is not None:
        p = Path(cfg.reports_dir) / "mechanism_drivers_delta.csv"
        if p.exists():
            try:
                rows = _read_csv(p)
                mech_delta_h = {str(r.get("mech_id", "")): float(r.get("mean_delta_h", "nan")) for r in rows if r.get("mech_id")}
            except Exception:
                mech_delta_h = None
    if mech_delta_h is None:
        mech_delta_h = _mechanism_driver_effects(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 5000,
        )
    figs.append(("drivers", "08_mechanism_drivers_tornado.png", _fig08_mechanism_drivers_tornado(raw, delta_h=mech_delta_h, mode=mode)))

    comp_matrix: dict[tuple[str, str], float] | None = None
    if cfg.reports_dir is not None:
        p = Path(cfg.reports_dir) / "component_drivers_matrix.csv"
        if p.exists():
            try:
                rows = _read_csv(p)
                comp_matrix = {}
                for r in rows:
                    sid = str(r.get("scenario_id", ""))
                    cid = str(r.get("component_id", ""))
                    if not sid or not cid:
                        continue
                    try:
                        d = float(r.get("mean_delta_h", "nan"))
                    except Exception:
                        continue
                    if np.isfinite(d):
                        comp_matrix[(sid, cid)] = float(d)
            except Exception:
                comp_matrix = None
    if comp_matrix is None:
        comp_matrix = _component_driver_matrix(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 7000,
        )

    comp_delta_h: dict[str, float] | None = None
    if cfg.reports_dir is not None:
        p = Path(cfg.reports_dir) / "component_drivers_delta.csv"
        if p.exists():
            try:
                rows = _read_csv(p)
                comp_delta_h = {str(r.get("component_id", "")): float(r.get("mean_delta_h", "nan")) for r in rows if r.get("component_id")}
            except Exception:
                comp_delta_h = None

    if comp_delta_h is None:
        sids = _scenario_ids(raw)
        comp_delta_h = {cid: float(np.mean([comp_matrix.get((sid, cid), 0.0) for sid in sids])) for cid, _ in component_driver_specs()}
    figs.append(("drivers", "09_component_drivers_tornado.png", _fig09_component_drivers_tornado(raw, delta_h=comp_delta_h, mode=mode)))
    figs.append(("drivers", "10_component_driver_matrix.png", _fig10_component_driver_matrix(raw, matrix=comp_matrix, mode=mode)))

    share_pct: dict[str, dict[str, float]] | None = None
    if cfg.reports_dir is not None:
        p = Path(cfg.reports_dir) / "energy_share.csv"
        if p.exists():
            try:
                rows = _read_csv(p)
                share_pct = {sid: {} for sid in _scenario_ids(raw)}
                for r in rows:
                    sid = str(r.get("scenario_id", ""))
                    comp = str(r.get("component", ""))
                    if sid not in share_pct:
                        continue
                    try:
                        v = float(r.get("mean_share_pct", "nan"))
                    except Exception:
                        continue
                    if np.isfinite(v):
                        share_pct[sid][comp] = float(v)
            except Exception:
                share_pct = None
    if share_pct is None:
        share_pct = _energy_share_mean(
            raw,
            base_power=power1,
            base_batt=batt,
            power0_dummy=power0_dummy,
            dt_s=float(cfg.dt_s),
            soc0=float(cfg.driver_soc0),
            n_seeds=int(cfg.driver_seeds),
            seed0=int(cfg.uq_seed) * 100,
        )
    figs.append(("energy", "04_energy_share.png", _fig04_energy_share(raw, share_pct=share_pct, mode=mode)))

    # --------------------------------
    # 4) 参数级敏感性（从报表 CSV 读入，避免重复仿真）
    # --------------------------------
    if cfg.reports_dir is not None:
        reports_dir = Path(cfg.reports_dir)
        sens_csv = reports_dir / "param_sensitivity.csv"
        overall_csv = reports_dir / "param_sensitivity_overall.csv"
        term_csv = reports_dir / "termination_stats.csv"
        if sens_csv.exists():
            try:
                rows = _read_csv(sens_csv)
                figs.append(
                    (
                        "sensitivity",
                        "11_prcc_heatmap_tte.png",
                        _fig11_prcc_heatmap_from_report(raw, sens_rows=rows, soc0=float(cfg.driver_soc0), mode=mode),
                    )
                )
                figs.append(
                    (
                        "sensitivity",
                        "13_spearman_heatmap_tte.png",
                        _fig13_spearman_heatmap_from_report(raw, sens_rows=rows, soc0=float(cfg.driver_soc0), mode=mode),
                    )
                )
            except Exception:
                # 报表缺失/格式不对时，不影响其它图
                pass
        if overall_csv.exists():
            try:
                rows2 = _read_csv(overall_csv)
                figs.append(
                    (
                        "sensitivity",
                        "12_prcc_rank_overall.png",
                        _fig12_prcc_rank_overall_from_report(overall_rows=rows2, soc0=float(cfg.driver_soc0), mode=mode),
                    )
                )
            except Exception:
                pass
        if term_csv.exists():
            try:
                trows = _read_csv(term_csv)
                figs.append(
                    (
                        "termination",
                        "16_termination_probs_uq.png",
                        _fig16_termination_probs_from_report(raw, term_rows=trows, soc0=float(cfg.driver_soc0), mode=mode),
                    )
                )
            except Exception:
                pass

    paths: list[Path] = []
    for sub, fname, fig in figs:
        p = out_dir / sub / fname
        # 用户要求：不覆盖历史热力图。若即将写入的是 01_tte_matrix*.png，则把旧图移动到同目录 other/ 下备份。
        if fname in ("01_tte_matrix.png", "01_tte_matrix_en.png") and p.exists():
            other = ensure_dir(p.parent / "other")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            bak = other / f"{p.stem}_old_{stamp}{p.suffix}"
            p.replace(bak)
        savefig(fig, p, mode=mode)
        plt.close(fig)
        paths.append(p)
    return paths
