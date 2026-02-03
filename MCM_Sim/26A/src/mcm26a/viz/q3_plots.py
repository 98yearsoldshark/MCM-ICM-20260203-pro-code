"""Q3 可视化：敏感性（局部/全局）+ 假设消融 + 老化扫描（paper/study 两种模式）。

设计原则：
- paper：尽量“干净”、可直接放论文；
- study：在图下方补充解释文字，帮助理解 PRCC/局部敏感度/消融的含义。
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from mcm26a.analysis.q3_sensitivity import q3_param_label_en, q3_param_label_zh, q3_param_names
from mcm26a.scenarios import load_scenarios_json

from .style import PlotMode, apply_style, ensure_dir, savefig


@dataclass(frozen=True)
class PlotBatchConfigQ3:
    """Q3 绘图批量配置。"""

    scenarios_path: Path
    reports_dir: Path
    out_dir: Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _scenario_ids_and_titles(raw: dict[str, Any]) -> tuple[list[str], list[str]]:
    sids = list(raw.get("scenarios", {}).keys())
    titles = [str(raw["scenarios"][sid].get("title_zh", sid)) for sid in sids]
    return sids, titles


def _wrap_title_zh_two_lines(title: str) -> str:
    """把过长的中文场景名改成两行，减少 y 轴占用的水平空间。

规则（按优先级）：
0) 统一格式（用户偏好）：
   - 中文括号 -> 英文括号；
   - 去掉空格（尤其是汉字与英文之间）；
   - CPU/GPU -> c/gpu；
   - “休止：恢复” -> “休止\\n恢复”（去掉冒号并换行）。
1) 含括号：如 “游戏(高c/gpu负载)” -> “游戏\\n(高c/gpu负载)”
2) 含冒号：如 “高负载→休止：恢复效应演示” -> “高负载→休止：\\n恢复效应演示”
3) 其他：原样返回。
"""

    s = str(title).strip()
    # 1) 规范化：括号/空格/缩写（先做替换，再做换行策略）
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"(?i)cpu/gpu", "c/gpu", s)
    # 删除所有空格：提升紧凑性，避免 y 轴标签过宽
    s = re.sub(r"[ \t\u00A0]+", "", s)

    # 特殊：把“休止：恢复”改为“休止\n恢复”（去掉冒号并换行）
    s = s.replace("休止：恢复", "休止\n恢复").replace("休止:恢复", "休止\n恢复")

    # 若已经包含换行，直接返回（避免二次拆分）
    if "\n" in s:
        return s

    # 2) 括号优先：括号内容通常是解释性补充，独占第二行可显著缩短标签宽度
    if "(" in s and ")" in s:
        a, b = s.split("(", 1)
        return f"{a.strip()}\n({b.strip()}"

    # 3) 其次按冒号拆分（保留冒号）
    if "：" in s:
        a, b = s.split("：", 1)
        return f"{a.strip()}：\n{b.strip()}"
    if ":" in s:
        a, b = s.split(":", 1)
        return f"{a.strip()}:\n{b.strip()}"

    return s


def _wrap_title_en_two_lines(title: str) -> str:
    """英文场景名两行换行（减少 y 轴占用的水平空间）。"""

    s = str(title).strip()
    # 若已经包含换行，直接返回
    if "\n" in s:
        return s

    # 优先把括号内容挪到第二行
    if "(" in s and ")" in s:
        a, b = s.split("(", 1)
        return f"{a.strip()}\n({b.strip()}"

    # 常见分隔：斜杠、箭头
    if " / " in s:
        a, b = s.split(" / ", 1)
        return f"{a.strip()}\n/ {b.strip()}"
    if "->" in s:
        a, b = s.split("->", 1)
        return f"{a.strip()} ->\n{b.strip()}"
    if "→" in s:
        a, b = s.split("→", 1)
        return f"{a.strip()} →\n{b.strip()}"

    return s


def _scenario_titles_en(raw: dict[str, Any], sids: list[str]) -> list[str]:
    """从 scenarios 配置中取英文标题；若缺失则用内置兜底。"""

    fallback = {
        "S0_standby": "Standby\n(light background)",
        "S1b_browse": "Browsing\n(social media)",
        "S1_video": "Video\n(playback/streaming)",
        "S2_navigation": "Navigation\n(GPS + maps)",
        "S3_gaming": "Gaming\n(high CPU/GPU load)",
        "S4_mixed_day": "Mixed usage\n(typical day)",
        "S5_burst_recovery": "Burst load -> rest\n(recovery demo)",
    }
    out: list[str] = []
    for sid in sids:
        sc = raw.get("scenarios", {}).get(str(sid), {})
        t = str(sc.get("title_en", "") or "").strip()
        if not t:
            t = fallback.get(str(sid), str(sid))
        out.append(t)
    return out


def _fig_prcc_heatmap(
    raw: dict[str, Any],
    *,
    prcc_rows: list[dict[str, str]],
    outputs_rows: list[dict[str, str]] | None,
    output_name: str,
    mode: PlotMode,
):
    style = apply_style(mode)
    # 图中文字语言：默认中文；可通过环境变量覆盖。
    # 仅影响图面显示，不影响报表/计算结果。
    lang = str(os.environ.get("MCM26A_PLOT_LANG", "zh")).strip().lower()
    if lang not in ("zh", "en"):
        lang = "zh"

    sids = list(raw.get("scenarios", {}).keys())
    if lang == "en":
        stitles = [_wrap_title_en_two_lines(s) for s in _scenario_titles_en(raw, sids)]
    else:
        stitles = [_wrap_title_zh_two_lines(str(raw["scenarios"][sid].get("title_zh", sid))) for sid in sids]
    # 一些参数在我们的建模口径中被视为“固定/不作为可变假设讨论”，
    # 为避免在 PRCC 图里误导读者（尤其会掩盖可调/可解释的参数），这里从 x 轴剔除。
    # 说明：我们只是在“展示层面”剔除；报表里仍保留原始列，便于复现实验。
    _fixed_params = {
        "v_cut_V",  # 截止电压阈值（安全策略/规格）
        "soc_min",  # 最小 SOC 阈值（安全策略/规格）
        "batt_r1_scale",  # 已通过识别/标定固定
        "eta_pmic",  # 视为硬件常数（不在 Q3 里作为可变假设展开）
        "alpha_r",  # 老化增阻强度系数（在当前口径中固定）
        "background_base_scale",  # 背景基线功耗：当前口径视为固定（不作为可变假设展示）
    }
    params = [p for p in q3_param_names() if p not in _fixed_params]
    xlabels = [q3_param_label_en(p) for p in params] if lang == "en" else [q3_param_label_zh(p) for p in params]

    out_title = (
        {
            "tte_mean_h": "Mean time-to-empty TTE (h)",
            "tte_std_h": "TTE std (h)",
            "tte_cv": "TTE coefficient of variation (CV)",
            "tte_spread_h": "TTE spread (P95-P05, h)",
            "p_cutoff": "Undervoltage cutoff probability",
            "p_insufficient_power": "Insufficient-power probability (Δ<0)",
            "min_headroom_margin": "Headroom margin (dimensionless)",
        }.get(str(output_name), str(output_name))
        if lang == "en"
        else {
            "tte_mean_h": "平均耗尽时间 TTE（小时）",
            "tte_std_h": "TTE 标准差（小时）",
            "tte_cv": "TTE 变异系数 CV（无量纲）",
            "tte_spread_h": "TTE 分位距（P95-P05，小时）",
            "p_cutoff": "欠压截止概率",
            "p_insufficient_power": "不可供电概率（Δ<0）",
            "min_headroom_margin": "功率闭合裕量（无量纲）",
        }.get(str(output_name), str(output_name))
    )

    mat = np.full((len(sids), len(params)), np.nan, dtype=float)
    key = {(r["scenario_id"], r["param"]): float(r["prcc"]) for r in prcc_rows if r.get("output") == output_name}
    for i, sid in enumerate(sids):
        for j, p in enumerate(params):
            mat[i, j] = float(key.get((sid, p), float("nan")))

    fig, ax = plt.subplots(figsize=(11.8, 4.6))
    all_nan = bool(np.all(np.isnan(mat)))
    # 若样本数不足导致 PRCC 全为 NaN，则用 0 占位画出网格，并在图内提示。
    mat_show = np.zeros_like(mat) if all_nan else mat
    im = ax.imshow(mat_show, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_yticks(np.arange(len(sids)))
    ax.set_yticklabels(stitles)
    ax.set_xticks(np.arange(len(params)))
    ax.set_xticklabels(xlabels, rotation=20, ha="right")
    # 论文图面尽量不写 “Q3”，由图题/图注统一编号（更干净）。
    if lang == "en":
        ax.set_title(f"Global Sensitivity PRCC (Output: {out_title}){style.title_suffix}")
    else:
        ax.set_title(f"全局敏感性 PRCC（输出：{out_title}）{style.title_suffix}")

    # 若输出在采样范围内几乎恒定，则 PRCC 退化为“全接近 0”。
    # 仅在 study 模式提示，避免污染 paper 图面。
    output_is_const = False
    if outputs_rows is not None:
        def _is_const(sid: str) -> bool:
            xs = []
            for r in outputs_rows:
                if str(r.get("scenario_id")) != sid:
                    continue
                try:
                    v = float(r.get(output_name, "nan"))
                except Exception:
                    v = float("nan")
                if np.isfinite(v):
                    xs.append(float(v))
            if len(xs) < 2:
                return True
            return float(np.max(xs) - np.min(xs)) <= 1e-12

        output_is_const = bool(sids and all(_is_const(sid) for sid in sids))

    # 分组分隔线：让读者更快看懂“电池端/阈值/负载/无线/随机机制”的位置
    # 采用参数名定位，避免未来调参时硬编码索引出错。
    def _sep_after(name: str) -> None:
        if name not in params:
            return
        j = params.index(name)
        ax.axvline(j + 0.5, color="#666666", linewidth=1.2, alpha=0.35)

    _sep_after("alpha_r")
    _sep_after("eta_pmic")
    # 若背景基线被视为固定并从 x 轴剔除，则用 GPS 作为“负载参数/无线机制”分隔点。
    _sep_after("gps_scale")
    _sep_after("poor_signal_psi_scale")

    # pad 越小 colorbar 越靠近主图（视觉上“向左移动一点”）。
    cbar = fig.colorbar(im, ax=ax, shrink=0.95, pad=0.015)
    cbar.set_label("PRCC (-1 to 1)" if lang == "en" else "PRCC（-1~1）")

    # 论文版也需要在格子里写数值（读者可快速定位/比较），因此不再只限于 study。
    # 为避免视觉负担，字体保持较小并根据底色自动切换黑/白。
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            rgba = im.cmap(im.norm(float(v)))
            # perceived luminance
            lum = 0.299 * float(rgba[0]) + 0.587 * float(rgba[1]) + 0.114 * float(rgba[2])
            txt_color = "black" if lum > 0.6 else "white"
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8, color=txt_color)

    if style.annotate:
        extra = ""
        if str(output_name) == "min_headroom_margin":
            extra = (
                "\n补充：min_headroom_margin 定义为 min_t[disc/(V_eq^2)] = min_t[1 - P/Pmax]（无量纲）。"
                "越接近 0 表示越接近“电压崩塌/不可供电（Δ<0）”边界。"
            )
        if all_nan:
            ax.text(
                0.5,
                0.5,
                "PRCC 结果全为 NaN：\n请增大 Q3 全局采样数（global-samples）\n确保 n > 参数数 + 2",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=12,
                color="#333333",
                bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#999999"},
            )
        if output_is_const and not all_nan:
            ax.text(
                0.99,
                0.02,
                "提示：该输出在当前采样范围内几乎恒定（PRCC 退化）",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=9,
                color="#555555",
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "#DDDDDD"},
            )
        # 预留更大的底部空间给说明文本，避免 tight_layout 报警告并造成重叠。
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：PRCC（Partial Rank Correlation Coefficient）衡量“控制其它参数后”，某参数对输出的单调影响强弱。\n"
            "- 绝对值越大：越敏感；正号：参数↑使输出↑；负号：参数↑使输出↓。\n"
            "- 我们对每个参数样本做多随机种子重复并取平均，以降低随机过程噪声。" + extra,
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_local_tornado(
    raw: dict[str, Any],
    *,
    local_rows: list[dict[str, str]],
    scenario_id: str,
    mode: PlotMode,
    top_k: int = 10,
):
    style = apply_style(mode)
    scen_cfg = raw.get("scenarios", {}).get(scenario_id, {})
    title_zh = str(scen_cfg.get("title_zh", scenario_id))

    rows = [r for r in local_rows if r.get("scenario_id") == scenario_id]
    if not rows:
        raise ValueError(f"local_sensitivity.csv 中没有 scenario_id={scenario_id!r} 的行")

    # 排序：按 |sens| 降序
    items = []
    for r in rows:
        try:
            s = float(r.get("sens_dimless", "nan"))
        except Exception:
            s = float("nan")
        items.append((str(r.get("param_zh", r.get("param", "?"))), s))
    items = [(k, v) for (k, v) in items if np.isfinite(v)]
    items.sort(key=lambda kv: abs(kv[1]), reverse=True)
    items = items[: int(top_k)]
    if not items:
        raise ValueError(f"scenario_id={scenario_id!r} 的局部敏感性全为 NaN，无法出图")

    labels = [k for (k, _) in items][::-1]
    vals = [v for (_, v) in items][::-1]
    colors = ["#4C78A8" if v < 0 else "#E45756" for v in vals]

    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    ax.barh(np.arange(len(vals)), vals, color=colors, alpha=0.9)
    ax.axvline(0.0, color="#333333", linewidth=1.0)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("局部敏感度（无量纲）")
    ax.set_title(f"Q3：局部敏感性（{title_zh}）{style.title_suffix}")

    if style.annotate:
        # 为底部说明文字预留更大空间，避免元素拥挤/被裁剪。
        fig.tight_layout(rect=(0.0, 0.26, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：局部敏感度 S≈(θ/y)·(Δy/Δθ)，在基准点附近对单个参数做 ± 扰动计算。\n"
            "- |S| 越大：该参数越关键；S>0 表示参数↑会延长续航；S<0 表示参数↑会缩短续航。\n"
            "- 本图仅反映“局部”效应；全局非线性/交互效应用 PRCC 热力图补充。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_seed_variation(
    raw: dict[str, Any],
    *,
    seed_rows: list[dict[str, str]],
    mode: PlotMode,
):
    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    # 说明：
    # - 若直接画 TTE（小时），不同场景的均值差异（3~25h）会淹没随机波动（通常只有秒~分钟级）。
    # - 为更直观地回答题干“同样使用却有时掉电更快”的随机性来源，这里画相对均值的 ΔTTE(%) 分布。
    data: list[list[float]] = []
    means_h: list[float] = []
    p05: list[float] = []
    p50: list[float] = []
    p95: list[float] = []
    sids_plot: list[str] = []
    stitles_plot: list[str] = []
    for sid, title in zip(sids, stitles):
        xs_h: list[float] = []
        for r in seed_rows:
            if r.get("scenario_id") != sid:
                continue
            try:
                v = float(r.get("tte_h", "nan"))
            except Exception:
                v = float("nan")
            if np.isfinite(v):
                xs_h.append(float(v))

        # 若该场景没有 seed_runs 数据（例如新增场景但未重跑报表），则跳过，
        # 避免生成“假的 0 分布”误导读者。
        if not xs_h:
            continue

        mu = float(np.nanmean(xs_h))
        means_h.append(mu)
        if not np.isfinite(mu) or abs(mu) <= 1e-12:
            ds = [0.0 for _ in xs_h]
        else:
            ds = [100.0 * (x - mu) / mu for x in xs_h if np.isfinite(x)]
            if not ds:
                ds = [0.0]
        data.append(ds)
        p05.append(float(np.percentile(ds, 5)))
        p50.append(float(np.percentile(ds, 50)))
        p95.append(float(np.percentile(ds, 95)))
        sids_plot.append(str(sid))
        stitles_plot.append(str(title))

    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    if not data:
        raise ValueError("seed_runs.csv 中没有任何可用的 tte_h 数据，无法生成使用波动分布图")
    parts = ax.violinplot(data, showmeans=False, showmedians=False, showextrema=False)
    from .style import PALETTE_SKIP_GRADIENT

    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(PALETTE_SKIP_GRADIENT[i % len(PALETTE_SKIP_GRADIENT)])
        pc.set_edgecolor("#2F2F2F")
        pc.set_alpha(0.68)

    xs = np.arange(1, len(stitles_plot) + 1, dtype=float)
    # 5~95% 区间 + 中位数：比“红色横线”更不易被误读为“线性拟合线”。
    for x, lo, mid, hi in zip(xs, p05, p50, p95):
        ax.vlines(x, lo, hi, color="#333333", linewidth=1.4, alpha=0.85, zorder=3)
        ax.scatter([x], [mid], s=28, color="#333333", zorder=4)

    ax.axhline(0.0, color="#666666", linewidth=1.0, alpha=0.35, zorder=2)

    ax.set_xticks(xs)
    ax.set_xticklabels(stitles_plot, rotation=15, ha="right")
    ax.set_ylabel("ΔTTE（%）")
    ax.set_title(f"Q3：仅由“使用波动/随机过程”导致的续航波动（ΔTTE%）{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：TTE（Time-to-Empty）指电量耗尽时间。\n"
            "- 固定同一组参数，仅改变随机种子（后台唤醒、信号抖动、待机偶发亮屏等），得到“随机过程”导致的续航波动。\n"
            "- 纵轴为相对均值的百分比偏差：ΔTTE(%)=(TTE-均值)/均值×100%。黑点为中位数，竖线为 5%~95% 区间。\n"
            "- 若分布很窄，表示在该场景下随机过程对续航的边际影响较小（更主要由使用强度/参数差异决定）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_variance_decomposition(
    raw: dict[str, Any],
    *,
    decomp_rows: list[dict[str, str]],
    mode: PlotMode,
):
    """把 TTE 的不确定性拆分为：参数/状态不确定性 vs 使用波动（随机过程）。

依据：
  Var(TTE) = Var(E[TTE|θ]) + E[Var(TTE|θ)]
其中 θ 表示参数/慢变量（SOH、R0/R1、功耗尺度等）。
"""

    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    by_sid = {str(r.get("scenario_id", "")): r for r in decomp_rows}
    frac_param: list[float] = []
    frac_usage: list[float] = []
    var_between: list[float] = []
    var_within: list[float] = []
    for sid in sids:
        r = by_sid.get(str(sid), {})
        try:
            fp = float(r.get("frac_param", "nan"))
        except Exception:
            fp = float("nan")
        try:
            fu = float(r.get("frac_usage", "nan"))
        except Exception:
            fu = float("nan")
        try:
            vt = float(r.get("var_total_h2", "nan"))
        except Exception:
            vt = float("nan")
        try:
            vb = float(r.get("var_between_param_h2", "nan"))
        except Exception:
            vb = float("nan")
        try:
            vw = float(r.get("var_within_usage_h2", "nan"))
        except Exception:
            vw = float("nan")

        if not np.isfinite(fp) or not np.isfinite(fu):
            fp, fu = float("nan"), float("nan")
        frac_param.append(fp)
        frac_usage.append(fu)
        var_between.append(vb)
        var_within.append(vw)

    x = np.arange(len(sids))
    fp = np.asarray(frac_param, dtype=float)
    fu = np.asarray(frac_usage, dtype=float)

    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    ax.bar(x, fp, color="#4C78A8", alpha=0.92, label="参数/状态不确定性 Var(E[T|θ])")
    ax.bar(x, fu, bottom=fp, color="#F58518", alpha=0.90, label="使用波动 E[Var(T|θ)]")
    ax.set_xticks(x)
    ax.set_xticklabels(stitles, rotation=15, ha="right")
    ax.set_ylim(0.0, 1.02)
    ax.set_ylabel("方差占比（0~1）")
    ax.set_title(f"Q3：TTE 不确定性来源分解（参数 vs 使用波动）{style.title_suffix}")
    ax.legend(frameon=False, fontsize=9, ncol=1, loc="upper right")

    # 由于在“宽先验”下，使用波动占比可能非常小（例如 <0.1%），肉眼几乎不可见。
    # 为避免误读为“全是 1/没有橙色”，这里在每根柱顶标注占比（百分数）。
    for i, (a, b) in enumerate(zip(fp, fu)):
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        ax.text(
            float(i),
            1.005,
            f"{a*100:.2f}% / {b*100:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#333333",
        )

    # study 模式额外在柱底标注绝对方差量级（h^2），帮助读者理解“不是 0，只是很小”。
    if style.annotate:
        for i, (vb, vw) in enumerate(zip(var_between, var_within)):
            if not (np.isfinite(vb) and np.isfinite(vw)):
                continue
            ax.text(
                float(i),
                0.02,
                f"Var_param={vb:.3g}\nVar_usage={vw:.3g}",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333333",
            )

    if style.annotate:
        fig.subplots_adjust(bottom=0.26, top=0.92, left=0.06, right=0.99)
        fig.text(
            0.01,
            0.02,
            "说明：该图用“全局采样（参数不确定性）+ 每个样本内多 seed 重复（使用波动）”近似分解 TTE 的总体波动。\n"
            "- 若橙色占比高：即使参数确定，随机使用过程也会导致显著续航波动（题干现象）；\n"
            "- 若蓝色占比高：硬件/环境/老化等慢变量差异更主导续航差异，建议优先做参数校准或区分机型/SOH。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_aging_scan(
    raw: dict[str, Any],
    *,
    aging_rows: list[dict[str, str]],
    mode: PlotMode,
):
    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    # 每个场景：soh -> (tte_mean, tte_p05, tte_p95)
    # 说明：老化扫描点数若较少，评委容易把它当成“示意图”。因此这里把 5%~95% 不确定带画出来，
    # 让读者看到：同一 SOH 下“随机过程波动”与“SOH 主效应”的量级差异。
    series: dict[str, list[tuple[float, float, float, float]]] = {sid: [] for sid in sids}
    for r in aging_rows:
        sid = str(r.get("scenario_id", ""))
        if sid not in series:
            continue
        try:
            soh = float(r.get("soh", "nan"))
            mu = float(r.get("tte_mean_h", "nan"))
            p05 = float(r.get("tte_p05_h", "nan"))
            p95 = float(r.get("tte_p95_h", "nan"))
        except Exception:
            continue
        if not (np.isfinite(soh) and np.isfinite(mu)):
            continue
        # 若 p05/p95 不存在（旧报表），则退化为均值线不画阴影。
        p05 = float(p05) if np.isfinite(p05) else float("nan")
        p95 = float(p95) if np.isfinite(p95) else float("nan")
        series[sid].append((float(soh), float(mu), float(p05), float(p95)))
    for sid in sids:
        series[sid].sort(key=lambda x: x[0])

    fig, ax = plt.subplots(figsize=(10.6, 4.8))
    colors = plt.cm.tab10(np.linspace(0.0, 1.0, max(3, len(sids))))
    all_xs: list[float] = []
    for i, sid in enumerate(sids):
        pts = series.get(sid, [])
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        lo = [p[2] for p in pts]
        hi = [p[3] for p in pts]
        all_xs.extend(xs)
        ax.plot(xs, ys, marker="o", linewidth=2.0, color=colors[i % len(colors)], label=stitles[i])
        if any(np.isfinite(v) for v in lo) and any(np.isfinite(v) for v in hi):
            ax.fill_between(xs, lo, hi, color=colors[i % len(colors)], alpha=0.12, linewidth=0.0)

    ax.set_xlabel("电池健康度 SOH")
    ax.set_ylabel("平均耗尽时间 TTE（小时）")
    ax.set_title(f"Q3：老化敏感性（SOH 扫描）{style.title_suffix}")
    if all_xs:
        x0 = float(min(all_xs))
        x1 = float(max(all_xs))
        ax.set_xlim(max(0.0, x0 - 0.02), min(1.02, x1 + 0.02))
    else:
        ax.set_xlim(0.65, 1.02)
    ax.legend(ncol=2, frameon=False, fontsize=9)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：SOH 同时通过“容量衰减（可用电量减少）+ 内阻增长（更易欠压关机）”影响续航。\n"
            "该扫描用于回答：哪些场景对老化更敏感（曲线更陡），以及老化是否显著提高提前关机风险。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_mechanism_ablation_heatmap(
    raw: dict[str, Any],
    *,
    ablation_rows: list[dict[str, str]],
    mode: PlotMode,
    top_k: int = 8,
):
    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    rows = [r for r in ablation_rows if r.get("ablation_type") == "mechanism"]
    if not rows:
        raise ValueError("ablation.csv 中未找到 ablation_type=mechanism 的行")

    # 选出影响最大的 top_k 个机制（按跨场景平均 |ΔTTE|）
    mech_ids = sorted({str(r.get("ablation_id", "")) for r in rows if r.get("ablation_id")})
    mech_label = {str(r.get("ablation_id")): str(r.get("ablation_label_zh", r.get("ablation_id"))) for r in rows}

    score = {}
    for mid in mech_ids:
        xs = []
        for r in rows:
            if str(r.get("ablation_id")) != mid:
                continue
            try:
                xs.append(abs(float(r.get("delta_tte_h", "nan"))))
            except Exception:
                pass
        xs = [x for x in xs if np.isfinite(x)]
        score[mid] = float(np.mean(xs)) if xs else 0.0
    mech_ids.sort(key=lambda m: score.get(m, 0.0), reverse=True)
    mech_ids = mech_ids[: int(top_k)]

    mat_tte = np.full((len(mech_ids), len(sids)), np.nan, dtype=float)
    mat_margin = np.full((len(mech_ids), len(sids)), np.nan, dtype=float)
    lookup = {(str(r.get("ablation_id")), str(r.get("scenario_id"))): r for r in rows}
    for i, mid in enumerate(mech_ids):
        for j, sid in enumerate(sids):
            r = lookup.get((mid, sid))
            if not r:
                continue
            try:
                mat_tte[i, j] = float(r.get("delta_tte_h", "nan"))
            except Exception:
                mat_tte[i, j] = float("nan")
            # 风险维度：功率闭合裕量（越接近 0 越危险）。本处用 Δmargin = (variant - base)。
            try:
                m_base = float(r.get("min_headroom_margin_base", "nan"))
            except Exception:
                m_base = float("nan")
            try:
                m_var = float(r.get("min_headroom_margin_variant", "nan"))
            except Exception:
                m_var = float("nan")
            if np.isfinite(m_base) and np.isfinite(m_var):
                mat_margin[i, j] = float(m_var - m_base)
            else:
                mat_margin[i, j] = float("nan")

    ylabels = [mech_label.get(mid, mid) for mid in mech_ids]

    # 双面板：左侧 ΔTTE，右侧 Δmargin（风险/欠压边界距离）
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(14.8, 4.8), sharey=True)

    abs_tte = np.abs(mat_tte)
    lim_tte = float(np.nanmax(abs_tte)) if np.any(np.isfinite(abs_tte)) else 1.0
    lim_tte = max(0.2, float(lim_tte))
    im0 = ax0.imshow(mat_tte, cmap="coolwarm", vmin=-lim_tte, vmax=lim_tte, aspect="auto")

    abs_m = np.abs(mat_margin)
    lim_m = float(np.nanmax(abs_m)) if np.any(np.isfinite(abs_m)) else 0.01
    lim_m = max(0.002, float(lim_m))
    im1 = ax1.imshow(mat_margin, cmap="coolwarm", vmin=-lim_m, vmax=lim_m, aspect="auto")

    # y 轴仅在左侧显示，避免拥挤
    ax0.set_yticks(np.arange(len(ylabels)))
    ax0.set_yticklabels(ylabels)
    ax1.set_yticks(np.arange(len(ylabels)))
    ax1.set_yticklabels([])

    for ax in (ax0, ax1):
        ax.set_xticks(np.arange(len(stitles)))
        ax.set_xticklabels(stitles, rotation=15, ha="right")

    ax0.set_title("机制消融：续航影响 ΔTTE（小时）")
    ax1.set_title("机制消融：风险影响 Δmargin（无量纲）")
    fig.suptitle(f"Q3：机制消融（续航 vs 风险）{style.title_suffix}", y=0.98)

    cbar0 = fig.colorbar(im0, ax=ax0, shrink=0.95)
    cbar0.set_label("ΔTTE（小时）")
    cbar1 = fig.colorbar(im1, ax=ax1, shrink=0.95)
    cbar1.set_label("Δmargin（无量纲）")

    if style.annotate:
        for i in range(mat_tte.shape[0]):
            for j in range(mat_tte.shape[1]):
                v = mat_tte[i, j]
                if np.isnan(v):
                    continue
                ax0.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8, color="black")
        for i in range(mat_margin.shape[0]):
            for j in range(mat_margin.shape[1]):
                v = mat_margin[i, j]
                if np.isnan(v):
                    continue
                ax1.text(j, i, f"{v:+.3f}", ha="center", va="center", fontsize=8, color="black")

        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.93))
        fig.text(
            0.01,
            0.02,
            "说明：同一场景下，我们一次只移除一个功耗侧机制（one-at-a-time ablation），并用相同随机种子对照（CRN）降低噪声。\n"
            "- 左图：ΔTTE =（移除机制后的 TTE）-（基线 TTE）。ΔTTE>0 表示该机制会缩短续航；ΔTTE≈0 可作为“surprisingly little”的证据。\n"
            "- 右图：Δmargin =（移除机制后的 min_headroom_margin）-（基线 min_headroom_margin）。margin 越大越“安全”，越接近 0 越逼近电压崩塌边界。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    return fig


def _fig_battery_model_ablation_bars(
    raw: dict[str, Any],
    *,
    ablation_rows: list[dict[str, str]],
    mode: PlotMode,
):
    """电池/耦合复杂度假设：Model-1 vs Model-2 vs Model-3 的多指标对照（同一功耗随机过程）。

    说明（对齐赛题）：
    - 只比 TTE 容易出现“差异很小”从而缺乏说服力；
    - 但热耦合/老化往往更直接体现在温度峰值与欠压风险（margin）上；
    - 因此这里同时展示：TTE、温度峰值、功率闭合裕量（margin）。
    """

    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    rows = [r for r in ablation_rows if r.get("ablation_type") == "battery_model"]
    if not rows:
        raise ValueError("ablation.csv 中未找到 ablation_type=battery_model 的行")

    # baseline only（variant 为空）：避免把 cold/hot 变体与 baseline 混在一张主图里
    rows = [r for r in rows if str(r.get("variant", "") or "").strip() == ""]

    # (scenario_id, model) -> metrics
    key: dict[tuple[str, str], dict[str, float]] = {}
    for r in rows:
        sid = str(r.get("scenario_id", ""))
        mid = str(r.get("ablation_id", ""))

        def _f(k: str) -> float:
            try:
                return float(r.get(k, "nan"))
            except Exception:
                return float("nan")

        key[(sid, mid)] = {
            "tte_h": _f("tte_h"),
            "temp_peak_C": _f("temp_peak_C"),
            "min_headroom_margin": _f("min_headroom_margin"),
            "p_cutoff": _f("p_cutoff"),
        }

    from .style import PALETTE_SKIP_GRADIENT

    models = ["model1", "model2", "model3"]
    labels = {"model1": "Model-1", "model2": "Model-2", "model3": "Model-3"}
    colors = {"model1": PALETTE_SKIP_GRADIENT[0], "model2": PALETTE_SKIP_GRADIENT[2], "model3": PALETTE_SKIP_GRADIENT[3]}

    x = np.arange(len(sids))
    w = 0.23

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(11.2, 9.0), sharex=True)
    ax_tte, ax_temp, ax_margin = axes

    for i, m in enumerate(models):
        xs = x + (i - 1) * w
        y_tte = [float(key.get((sid, m), {}).get("tte_h", float("nan"))) for sid in sids]
        y_temp = [float(key.get((sid, m), {}).get("temp_peak_C", float("nan"))) for sid in sids]
        y_m = [float(key.get((sid, m), {}).get("min_headroom_margin", float("nan"))) for sid in sids]

        ax_tte.bar(xs, y_tte, width=w, label=labels[m], color=colors[m], alpha=0.92)
        ax_temp.bar(xs, y_temp, width=w, label=labels[m], color=colors[m], alpha=0.92)
        ax_margin.bar(xs, y_m, width=w, label=labels[m], color=colors[m], alpha=0.92)

    ax_tte.set_ylabel("TTE（小时）")
    ax_temp.set_ylabel("温度峰值（°C）")
    ax_margin.set_ylabel("min margin（无量纲）")
    ax_margin.set_ylim(0.0, 1.05)

    ax_tte.set_title(f"Q3：建模假设对照（电池模型复杂度，多指标）{style.title_suffix}")
    ax_tte.legend(ncol=3, frameon=False, fontsize=9, loc="upper right")

    ax_margin.set_xticks(x)
    ax_margin.set_xticklabels(stitles, rotation=15, ha="right")

    # paper 模式保持干净；study 模式补充解释
    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.16, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：Model-1（纯电）忽略温度/老化；Model-2 加入热-电耦合；Model-3 在此基础上加入老化状态。\n"
            "- 仅比 TTE 往往差异较小，但温度峰值与欠压风险裕量（min margin）更能体现热耦合/老化的物理影响；\n"
            "- min margin 越接近 0 表示越逼近电压崩塌边界，更可能“突然掉电/提前关机”。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_battery_structure_ablation_bars(
    raw: dict[str, Any],
    *,
    ablation_rows: list[dict[str, str]],
    mode: PlotMode,
):
    """电池端结构假设：1RC vs 2RC 的预测差异（ΔTTE）。"""

    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    rows = [r for r in ablation_rows if r.get("ablation_type") == "battery_structure"]
    if not rows:
        raise ValueError("ablation.csv 中未找到 ablation_type=battery_structure 的行")

    # scenario_id -> delta_tte_h / delta_tte_pct
    delta_h: dict[str, float] = {}
    delta_pct: dict[str, float] = {}
    for r in rows:
        sid = str(r.get("scenario_id", ""))
        try:
            dh = float(r.get("delta_tte_h", "nan"))
        except Exception:
            dh = float("nan")
        try:
            dp = float(r.get("delta_tte_pct", "nan"))
        except Exception:
            dp = float("nan")
        delta_h[sid] = float(dh)
        delta_pct[sid] = float(dp)

    xs = np.arange(len(sids))
    ys = [float(delta_h.get(sid, float("nan"))) for sid in sids]
    cols = ["#2CA02C" if (np.isfinite(y) and y >= 0) else "#D62728" for y in ys]

    # 留出更高的画布，避免在 study 模式下文字过多导致布局拥挤。
    fig, ax = plt.subplots(figsize=(10.6, 5.3))
    ax.bar(xs, ys, color=cols, alpha=0.88)
    ax.axhline(0.0, color="#666666", linewidth=1.0, alpha=0.6)
    ax.set_xticks(xs)
    ax.set_xticklabels(stitles, rotation=12, ha="right")
    ax.set_ylabel("ΔTTE（小时，2RC - 1RC）")
    ax.set_title(f"Q3：结构假设对照（电池 1RC vs 2RC）{style.title_suffix}")

    if style.annotate:
        # 在柱子上标注百分比差异（便于快速感知量级）
        for x, y, sid in zip(xs, ys, sids):
            dp = delta_pct.get(sid, float("nan"))
            if not np.isfinite(y):
                continue
            text = f"{y:+.2f}h"
            if np.isfinite(dp):
                text += f" ({dp:+.1f}%)"
            ax.text(
                x,
                y + (0.02 if y >= 0 else -0.02),
                text,
                ha="center",
                va="bottom" if y >= 0 else "top",
                fontsize=9,
            )

        # 说明文字较长时 tight_layout 容易失败；这里改用手动边距更稳定。
        fig.subplots_adjust(bottom=0.34, top=0.92, left=0.06, right=0.99)
        fig.text(
            0.01,
            0.02,
            "说明：本图检验‘1RC 单时间常数极化’这一简化。\n"
            "- 2RC 允许快/慢两条极化支路，能更真实刻画突发负载后的回弹与较慢恢复；\n"
            "- 我们固定关闭功耗侧热节流（DVFS），仅比较电池端结构差异；\n"
            "- 若 ΔTTE≈0，说明对 TTE 预测可用 1RC 近似；若差异显著，建议在正文采用 2RC 或在不确定性中说明。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_battery_model_cold_hot_heatmaps(
    raw: dict[str, Any],
    *,
    battery_model_rows: list[dict[str, str]],
    mode: PlotMode,
):
    """用 cold/hot 变体放大热效应：展示 Model-2 相对 Model-1 的差异随环境变化的敏感性。

    目的（对齐赛题 Q3）：
    - 评委可能会质疑“Model-1/2/3 复杂度差异不大”；但热耦合的影响往往在
      环境温度变化（cold/hot）下更显著；
    - 因此这里固定功耗输入，比较 Model-2 与 Model-1 的差异，并把差异在 baseline/cold/hot 三种
      环境变体下并列展示。
    """

    import matplotlib.pyplot as plt

    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    # 只用 battery_model_ablation.csv（若不存在则传入的是 ablation.csv 的子集，可能缺少变体）。
    rows = [r for r in battery_model_rows if r.get("ablation_type") == "battery_model"]
    if not rows:
        raise ValueError("缺少 battery_model_ablation 行：请先生成 battery_model_ablation.csv 或 ablation.csv")

    # variant 列为空表示 baseline；其余为 cold_outdoor/hot_summer
    variants = ["", "cold_outdoor", "hot_summer"]
    v_zh = {"": "基线", "cold_outdoor": "低温", "hot_summer": "高温"}

    # (scenario, variant, model) -> metrics
    key: dict[tuple[str, str, str], dict[str, float]] = {}

    def _f(row: dict[str, str], k: str) -> float:
        try:
            return float(row.get(k, "nan"))
        except Exception:
            return float("nan")

    for r in rows:
        sid = str(r.get("scenario_id", ""))
        var = str(r.get("variant", "") or "")
        mid = str(r.get("ablation_id", ""))
        key[(sid, var, mid)] = {
            "tte_h": _f(r, "tte_h"),
            "min_margin": _f(r, "min_headroom_margin"),
            "temp_end_C": _f(r, "temp_end_C"),
        }

    def _delta(sid: str, var: str, metric: str) -> float:
        a = key.get((sid, var, "model1"))
        b = key.get((sid, var, "model2"))
        if not a or not b:
            return float("nan")
        va = float(a.get(metric, float("nan")))
        vb = float(b.get(metric, float("nan")))
        if not (np.isfinite(va) and np.isfinite(vb)):
            return float("nan")
        return float(vb - va)

    mat_tte = np.full((len(sids), len(variants)), np.nan, dtype=float)
    mat_margin = np.full((len(sids), len(variants)), np.nan, dtype=float)
    mat_temp = np.full((len(sids), len(variants)), np.nan, dtype=float)
    for i, sid in enumerate(sids):
        for j, var in enumerate(variants):
            mat_tte[i, j] = _delta(sid, var, "tte_h")
            mat_margin[i, j] = _delta(sid, var, "min_margin")
            mat_temp[i, j] = _delta(sid, var, "temp_end_C")

    def _lim(mat: np.ndarray, floor: float) -> float:
        xs = np.abs(mat[np.isfinite(mat)])
        if xs.size <= 0:
            return float(floor)
        return max(float(floor), float(np.max(xs)))

    lim_tte = _lim(mat_tte, 0.05)
    lim_m = _lim(mat_margin, 0.005)
    lim_t = _lim(mat_temp, 0.5)

    fig, axes = plt.subplots(1, 3, figsize=(15.4, 4.6), sharey=True)
    ax0, ax1, ax2 = axes

    im0 = ax0.imshow(mat_tte, cmap="coolwarm", vmin=-lim_tte, vmax=lim_tte, aspect="auto")
    im1 = ax1.imshow(mat_margin, cmap="coolwarm", vmin=-lim_m, vmax=lim_m, aspect="auto")
    im2 = ax2.imshow(mat_temp, cmap="coolwarm", vmin=-lim_t, vmax=lim_t, aspect="auto")

    for ax in axes:
        ax.set_xticks(np.arange(len(variants)))
        ax.set_xticklabels([v_zh.get(v, v) for v in variants])

    ax0.set_yticks(np.arange(len(stitles)))
    ax0.set_yticklabels(stitles)
    ax1.set_yticks(np.arange(len(stitles)))
    ax1.set_yticklabels([])
    ax2.set_yticks(np.arange(len(stitles)))
    ax2.set_yticklabels([])

    ax0.set_title("ΔTTE（h）\nModel-2 − Model-1")
    ax1.set_title("Δmargin（无量纲）\nModel-2 − Model-1")
    ax2.set_title("ΔT_end（°C）\nModel-2 − Model-1")
    fig.suptitle(f"Q3：cold/hot 变体下的热耦合影响（放大效应检验）{style.title_suffix}", y=0.98)

    fig.colorbar(im0, ax=ax0, shrink=0.92)
    fig.colorbar(im1, ax=ax1, shrink=0.92)
    fig.colorbar(im2, ax=ax2, shrink=0.92)

    if style.annotate:
        # 学习版：格内写数字，便于团队快速读结论
        for i in range(mat_tte.shape[0]):
            for j in range(mat_tte.shape[1]):
                v = mat_tte[i, j]
                if np.isfinite(v):
                    ax0.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8, color="black")
                v = mat_margin[i, j]
                if np.isfinite(v):
                    ax1.text(j, i, f"{v:+.3f}", ha="center", va="center", fontsize=8, color="black")
                v = mat_temp[i, j]
                if np.isfinite(v):
                    ax2.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8, color="black")

        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.93))
        fig.text(
            0.01,
            0.02,
            "说明：本图用于回答“在环境温度变化时，忽略热耦合会带来多大误差”。\n"
            "- ΔTTE>0：热模型预测更长续航；ΔTTE<0：热模型预测更短续航（常见于低温增阻/容量折减）。\n"
            "- Δmargin<0：更接近欠压边界（风险更高）；ΔT_end<0：环境使电池更冷。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))

    return fig


def _fig_variant_sweep_heatmap(
    raw: dict[str, Any],
    *,
    variant_rows: list[dict[str, str]],
    mode: PlotMode,
    value_col: str = "delta_tte_h",
):
    """Q3：场景变体（cold/hot/poor_signal）对输出的影响热力图。

默认画 ΔTTE（小时）：variant - baseline。
"""

    style = apply_style(mode)
    sids, stitles = _scenario_ids_and_titles(raw)

    # group -> 论文友好中文名
    group_order = ["cold_outdoor", "hot_summer", "poor_signal"]
    group_zh = {"cold_outdoor": "低温", "hot_summer": "高温", "poor_signal": "弱信号"}

    # (scenario_id, group) -> stats
    base = {}
    other = {}
    for r in variant_rows:
        sid = str(r.get("scenario_id", ""))
        g = str(r.get("variant_group", ""))
        try:
            tte = float(r.get("tte_mean_h", "nan"))
            margin = float(r.get("min_headroom_margin_mean", "nan"))
        except Exception:
            continue
        if g == "baseline":
            base[sid] = {"tte_mean_h": tte, "min_headroom_margin_mean": margin}
        else:
            other[(sid, g)] = {"tte_mean_h": tte, "min_headroom_margin_mean": margin}

    # build matrix
    mat = np.full((len(sids), len(group_order)), np.nan, dtype=float)
    for i, sid in enumerate(sids):
        b = base.get(sid)
        if not b:
            continue
        for j, g in enumerate(group_order):
            o = other.get((sid, g))
            if not o:
                continue
            if value_col == "delta_tte_h":
                mat[i, j] = float(o["tte_mean_h"] - b["tte_mean_h"])
            elif value_col == "delta_min_headroom_margin":
                mat[i, j] = float(o["min_headroom_margin_mean"] - b["min_headroom_margin_mean"])
            else:
                raise ValueError(f"unknown value_col: {value_col!r}")

    if value_col == "delta_tte_h":
        title = "Q3：场景变体对续航的影响 ΔTTE（小时）"
        cbar_label = "ΔTTE（小时）"
    else:
        title = "Q3：场景变体对电压崩塌裕量的影响 Δmargin（无量纲）"
        cbar_label = "Δmargin（无量纲）"

    xlabels = [group_zh.get(g, g) for g in group_order]

    fig, ax = plt.subplots(figsize=(9.6, 4.3))
    abs_mat = np.abs(mat)
    lim = float(np.nanmax(abs_mat)) if np.any(np.isfinite(abs_mat)) else 1.0
    lim = max(0.02, float(lim))
    im = ax.imshow(mat, cmap="coolwarm", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_yticks(np.arange(len(stitles)))
    ax.set_yticklabels(stitles)
    ax.set_xticks(np.arange(len(xlabels)))
    ax.set_xticklabels(xlabels)
    ax.set_title(f"{title}{style.title_suffix}")

    cbar = fig.colorbar(im, ax=ax, shrink=0.95)
    cbar.set_label(cbar_label)

    if style.annotate:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                if np.isnan(v):
                    continue
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=9, color="black")
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：Δ 表示（变体 - baseline）。变体用于回答题面中环境/信号等外部条件变化带来的续航差异。\n"
            "- 低温：内阻上升/有效容量下降（更易提前关机）；\n"
            "- 弱信号：无线能耗放大 + RRC 尾态协同；\n"
            "- 高温：本模型主要体现温升与热耦合对电池端的影响（若功耗侧节流启用，还会改变负载）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def make_q3_plot_batch(cfg: PlotBatchConfigQ3, *, mode: PlotMode) -> list[Path]:
    """批量生成 Q3 图像。"""

    mode = str(mode)  # type: ignore[assignment]
    style = apply_style(mode)  # noqa: F841  # 保持与其它 plot_batch 一致：先设置全局风格

    raw = load_scenarios_json(cfg.scenarios_path)

    reports_dir = Path(cfg.reports_dir)
    need = [
        "global_prcc.csv",
        "local_sensitivity.csv",
        "seed_runs.csv",
        "aging_scan.csv",
        "ablation.csv",
        "variant_sweep.csv",
        "variance_decomposition.csv",
    ]
    missing = [p for p in need if not (reports_dir / p).exists()]
    if missing:
        raise FileNotFoundError(
            "缺少 Q3 报表文件："
            + ", ".join(missing)
            + "。请先运行 scripts/run_q3_report.py 生成 out_reports/q3/*.csv"
        )

    prcc_rows = _read_csv(reports_dir / "global_prcc.csv")
    outputs_rows = _read_csv(reports_dir / "global_outputs.csv") if (reports_dir / "global_outputs.csv").exists() else None
    local_rows = _read_csv(reports_dir / "local_sensitivity.csv")
    seed_rows = _read_csv(reports_dir / "seed_runs.csv")
    decomp_rows = _read_csv(reports_dir / "variance_decomposition.csv")
    aging_rows = _read_csv(reports_dir / "aging_scan.csv")
    ablation_rows = _read_csv(reports_dir / "ablation.csv")
    # 若存在“只算电池模型复杂度”的轻量报表，则优先使用（包含温度峰值等额外列）。
    battery_model_rows = (
        _read_csv(reports_dir / "battery_model_ablation.csv")
        if (reports_dir / "battery_model_ablation.csv").exists()
        else ablation_rows
    )
    variant_rows = _read_csv(reports_dir / "variant_sweep.csv")

    out_dir = ensure_dir(Path(cfg.out_dir) / "q3" / mode)

    paths: list[Path] = []

    # 1) 全局敏感性热力图
    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="tte_mean_h", mode=mode)
    p = out_dir / "sensitivity" / "01_prcc_tte_mean_h.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="p_cutoff", mode=mode)
    p = out_dir / "sensitivity" / "02_prcc_p_cutoff.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="p_insufficient_power", mode=mode)
    p = out_dir / "sensitivity" / "03_prcc_p_insufficient_power.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="min_headroom_margin", mode=mode)
    p = out_dir / "sensitivity" / "04_prcc_min_headroom_margin.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="tte_cv", mode=mode)
    p = out_dir / "sensitivity" / "05_prcc_tte_cv.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_prcc_heatmap(raw, prcc_rows=prcc_rows, outputs_rows=outputs_rows, output_name="tte_spread_h", mode=mode)
    p = out_dir / "sensitivity" / "06_prcc_tte_spread_h.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    # 2) 局部敏感性：每个场景一张 tornado
    # 说明：本项目允许在 scenarios_v0.json 中追加新场景，但不一定同步重跑所有报表。
    # 因此这里仅对 local_sensitivity.csv 中存在的 scenario_id 出 tornado 图，避免因为“缺报表”而中断整套出图。
    sid_order = {str(sid): i for i, sid in enumerate(raw.get("scenarios", {}).keys())}
    local_sids = sorted({str(r.get("scenario_id")) for r in local_rows if r.get("scenario_id")}, key=lambda s: sid_order.get(s, 10**9))
    for sid in local_sids:
        try:
            fig = _fig_local_tornado(raw, local_rows=local_rows, scenario_id=str(sid), mode=mode)
        except Exception:
            # 若该场景局部敏感性缺失/全为 NaN，则跳过（不影响其它图）
            continue
        p = out_dir / "sensitivity" / f"10_local_tornado_{sid}.png"
        savefig(fig, p, mode=mode)
        plt.close(fig)
        paths.append(p)

    # 3) 使用波动（随机过程）导致的分布
    fig = _fig_seed_variation(raw, seed_rows=seed_rows, mode=mode)
    p = out_dir / "fluctuation" / "20_seed_variation_violin.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_variance_decomposition(raw, decomp_rows=decomp_rows, mode=mode)
    p = out_dir / "fluctuation" / "21_variance_decomposition.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    # 4) 老化扫描
    fig = _fig_aging_scan(raw, aging_rows=aging_rows, mode=mode)
    p = out_dir / "aging" / "30_aging_soh_scan.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    # 5) 机制消融
    fig = _fig_mechanism_ablation_heatmap(raw, ablation_rows=ablation_rows, mode=mode)
    p = out_dir / "ablation" / "40_mechanism_ablation_heatmap.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_battery_model_ablation_bars(raw, ablation_rows=battery_model_rows, mode=mode)
    p = out_dir / "ablation" / "41_battery_model_ablation.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    # 5.1) cold/hot 变体：放大热效应（需要 battery_model_ablation.csv 才能区分变体）
    if any(str(r.get("variant", "") or "").strip() for r in battery_model_rows):
        fig = _fig_battery_model_cold_hot_heatmaps(raw, battery_model_rows=battery_model_rows, mode=mode)
        p = out_dir / "ablation" / "43_battery_model_cold_hot_effects.png"
        savefig(fig, p, mode=mode)
        plt.close(fig)
        paths.append(p)

    fig = _fig_battery_structure_ablation_bars(raw, ablation_rows=ablation_rows, mode=mode)
    p = out_dir / "ablation" / "42_battery_structure_ablation.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    # 6) 变体对照（环境/信号波动）
    fig = _fig_variant_sweep_heatmap(raw, variant_rows=variant_rows, mode=mode, value_col="delta_tte_h")
    p = out_dir / "variants" / "50_variant_delta_tte_heatmap.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    fig = _fig_variant_sweep_heatmap(raw, variant_rows=variant_rows, mode=mode, value_col="delta_min_headroom_margin")
    p = out_dir / "variants" / "51_variant_delta_margin_heatmap.png"
    savefig(fig, p, mode=mode)
    plt.close(fig)
    paths.append(p)

    return paths
