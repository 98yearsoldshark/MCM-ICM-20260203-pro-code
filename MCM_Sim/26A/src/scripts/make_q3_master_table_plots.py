#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q3 数据集实验（AndroWatts×老化状态）图像，paper/study 两套。

读取：
- out_reports/q3/observed_master_table/cells_tte.csv
- out_reports/q3/observed_master_table/variance_decomposition_usage_aging.csv

输出：
- out_plots/q3/{paper|study}/observed_master_table/
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

from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, PlotMode, apply_style, ensure_dir, savefig


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _build_cell_grids(rows: list[dict[str, str]]):
    """把 cells_tte.csv 转成矩阵形式，便于做二因素分解/分组分析。"""

    phone_ids = sorted({int(r["phone_test_id"]) for r in rows})
    state_ids = sorted({str(r["battery_state_id"]) for r in rows})
    I = len(phone_ids)
    J = len(state_ids)
    if I <= 0 or J <= 0:
        raise ValueError("cells_tte.csv 为空或缺少 phone/state 维度")

    idx_phone = {pid: i for i, pid in enumerate(phone_ids)}
    idx_state = {sid: j for j, sid in enumerate(state_ids)}

    y = np.full((I, J), np.nan, dtype=float)  # cell mean
    s = np.full((I, J), np.nan, dtype=float)  # cell std（seed 波动）
    p = np.full((I,), np.nan, dtype=float)  # 每个 phone_test 的观测总功耗（W）

    for r in rows:
        try:
            pid = int(r["phone_test_id"])
            sid = str(r["battery_state_id"])
            i = idx_phone[pid]
            j = idx_state[sid]

            y[i, j] = float(r.get("tte_mean_h", "nan"))
            s[i, j] = float(r.get("tte_std_h", "nan"))

            pw = float(r.get("obs_total_w", "nan"))
            if np.isfinite(pw):
                if not np.isfinite(p[i]):
                    p[i] = float(pw)
                else:
                    # 观测功耗在同一 phone_test 下应当不随 battery_state 改变（否则说明数据拼接有误）。
                    if abs(float(p[i]) - float(pw)) > 1e-6:
                        raise ValueError(f"phone_test_id={pid} 的 obs_total_w 在不同老化档位下不一致")
        except KeyError as e:
            raise KeyError(f"cells_tte.csv 缺少字段：{e}") from e

    if not np.isfinite(p).all():
        bad = int(np.size(p) - int(np.sum(np.isfinite(p))))
        raise ValueError(f"cells_tte.csv 中有 {bad} 个 phone_test 的 obs_total_w 缺失/非数值")
    if not np.isfinite(y).all():
        bad = int(np.size(y) - int(np.sum(np.isfinite(y))))
        raise ValueError(f"cells_tte.csv 中有 {bad} 个 cell 的 tte_mean_h 缺失/非数值")
    if not np.isfinite(s).all():
        bad = int(np.size(s) - int(np.sum(np.isfinite(s))))
        raise ValueError(f"cells_tte.csv 中有 {bad} 个 cell 的 tte_std_h 缺失/非数值")

    return phone_ids, state_ids, p, y, s


def _variance_decomposition_from_grid(
    y: np.ndarray,
    s: np.ndarray,
    *,
    phone_sel: np.ndarray,
):
    """对 (phone_sel×all_states) 子样本做使用×老化×交互×随机 的方差分解。"""

    if phone_sel.dtype != bool or phone_sel.ndim != 1:
        raise ValueError("phone_sel 必须是一维 bool mask")
    if y.ndim != 2 or s.ndim != 2:
        raise ValueError("y/s 必须是二维矩阵")
    if y.shape != s.shape:
        raise ValueError("y 与 s 的形状不一致")
    I, J = y.shape
    if phone_sel.shape[0] != I:
        raise ValueError("phone_sel 长度与 y 行数不一致")

    idx = np.where(phone_sel)[0]
    if idx.size <= 0:
        raise ValueError("phone_sel 选择结果为空")

    y2 = y[idx, :]
    s2 = s[idx, :]
    I2, J2 = y2.shape
    n_cells = int(I2 * J2)
    if n_cells < 2:
        raise ValueError("子样本 cell 数过少，无法分解")

    # within-seed：E[Var(T|cell)] ≈ mean(std^2)
    var_within = float(np.mean(s2 * s2))

    # between-cell：Var(E[T|cell])
    y_flat = y2.reshape(-1)
    var_between = float(np.var(y_flat, ddof=1))

    # 二因素平方和分解：SS_total = SS_phone + SS_state + SS_interaction
    grand = float(np.mean(y2))
    mean_i = np.mean(y2, axis=1)  # phone means
    mean_j = np.mean(y2, axis=0)  # state means
    ss_total = float(np.sum((y2 - grand) ** 2))
    ss_phone = float(J2 * np.sum((mean_i - grand) ** 2))
    ss_state = float(I2 * np.sum((mean_j - grand) ** 2))
    denom = float(n_cells - 1)
    var_phone = float(ss_phone / denom)
    var_state = float(ss_state / denom)
    var_inter = float(max(0.0, var_between - var_phone - var_state))

    var_total = float(var_phone + var_state + var_inter + var_within)
    frac_phone = float(var_phone / var_total) if var_total > 0 else float("nan")
    frac_state = float(var_state / var_total) if var_total > 0 else float("nan")
    frac_inter = float(var_inter / var_total) if var_total > 0 else float("nan")
    frac_within = float(var_within / var_total) if var_total > 0 else float("nan")
    return {
        "I": int(I2),
        "J": int(J2),
        "n_cells": int(n_cells),
        "var_usage_phone_h2": float(var_phone),
        "var_aging_state_h2": float(var_state),
        "var_interaction_h2": float(var_inter),
        "var_seed_within_h2": float(var_within),
        "var_total_h2": float(var_total),
        "frac_usage_phone": float(frac_phone),
        "frac_aging_state": float(frac_state),
        "frac_interaction": float(frac_inter),
        "frac_seed_within": float(frac_within),
    }


def _fmt_pct_zh(x: float) -> str:
    """百分比字符串（避免显示为 0.0% 造成误读）。"""

    if not np.isfinite(x):
        return "?"
    v = float(x) * 100.0
    if v < 0.05:
        return "<0.1%"
    return f"{v:.1f}%"


def _fig_decomposition_power_bins(rows: list[dict[str, str]], *, mode: PlotMode, n_bins: int = 3):
    """把 11 的“单条分解”升级为：总体 + 按观测功耗分位分组（低/中/高）三条分解。"""

    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    style = apply_style(mode)
    phone_ids, _state_ids, p_obs, y, s = _build_cell_grids(rows)
    I = len(phone_ids)

    # 1) 按观测功耗排序并切成 n_bins 组（尽量均分）
    order = np.argsort(p_obs)
    groups = np.array_split(order, int(n_bins))
    if len(groups) < 2:
        raise ValueError("n_bins 太小，无法分组")

    # 2) 计算总体 + 分组分解
    bars = []
    mask_all = np.ones((I,), dtype=bool)
    d_all = _variance_decomposition_from_grid(y, s, phone_sel=mask_all)
    bars.append(("总体", mask_all, d_all, (float(np.min(p_obs)), float(np.max(p_obs)))))

    labels = ["低功耗", "中功耗", "高功耗"]
    # 若 n_bins!=3，则用 “第k组” 兜底
    for k, idx in enumerate(groups):
        m = np.zeros((I,), dtype=bool)
        m[idx] = True
        d = _variance_decomposition_from_grid(y, s, phone_sel=m)
        lo = float(np.min(p_obs[idx]))
        hi = float(np.max(p_obs[idx]))
        name = labels[k] if k < len(labels) else f"第{k+1}组"
        bars.append((name, m, d, (lo, hi)))

    # 3) 绘图：多条 100% 堆叠条
    c_usage = PALETTE_SKIP_GRADIENT[0]  # 使用：紫
    c_inter = PALETTE_SKIP_GRADIENT[1]  # 交互：亮青
    c_aging = PALETTE_SKIP_GRADIENT[2]  # 老化：青绿
    c_seed = PALETTE_SKIP_GRADIENT[3]  # 随机：深绿
    segs = [
        ("使用", "frac_usage_phone", c_usage),
        ("老化", "frac_aging_state", c_aging),
        ("交互", "frac_interaction", c_inter),
        ("随机", "frac_seed_within", c_seed),
    ]

    fig, ax = plt.subplots(figsize=(9.6, 3.8))
    y_pos = np.arange(len(bars))

    def _luminance(hex_color: str) -> float:
        hc = hex_color.lstrip("#")
        r = int(hc[0:2], 16) / 255.0
        g = int(hc[2:4], 16) / 255.0
        b = int(hc[4:6], 16) / 255.0
        return 0.299 * r + 0.587 * g + 0.114 * b

    # y 轴标签：paper 保持简洁；study 补充功耗范围方便解释
    y_labels = []
    for name, _m, _d, (lo, hi) in bars:
        if style.annotate:
            y_labels.append(f"{name}\n({lo:.2f}~{hi:.2f}W)")
        else:
            y_labels.append(name)

    for yi, (name, _m, d, _rng) in enumerate(bars):
        left = 0.0
        for lab, key, col in segs:
            frac = float(d.get(key, float("nan")))
            ax.barh([yi], [frac], left=[left], color=col, alpha=0.95, height=0.56, edgecolor="white", linewidth=1.2)
            # 在块内写百分比：使图“信息密度”更高，避免只看到一大块紫色
            # 1% 左右的交互项也很关键，因此阈值设得更低一些（避免被误读为“没有交互”）。
            if np.isfinite(frac) and frac > 0.008:
                txt = _fmt_pct_zh(frac)
                ax.text(
                    left + frac / 2.0,
                    yi,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=("black" if _luminance(col) > 0.62 else "white"),
                )
            left += float(frac)

        # 总体那条在右侧额外标注 power 范围（paper 版也给一个弱提示，不占太多空间）
        if (not style.annotate) and name == "总体":
            lo, hi = float(np.min(p_obs)), float(np.max(p_obs))
            ax.text(1.01, yi, f"{lo:.2f}~{hi:.2f}W", ha="left", va="center", fontsize=9, color="#444444")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels)
    ax.invert_yaxis()  # “总体”在最上方
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("方差占比（0~1）")
    ax.grid(axis="x", alpha=0.22)
    ax.grid(axis="y", visible=False)

    d0 = bars[0][2]
    title_sub = (
        f"使用 {_fmt_pct_zh(float(d0['frac_usage_phone']))} | 老化 {_fmt_pct_zh(float(d0['frac_aging_state']))} | "
        f"交互 {_fmt_pct_zh(float(d0['frac_interaction']))} | 随机 {_fmt_pct_zh(float(d0['frac_seed_within']))}"
    )
    ax.set_title(f"Q3：TTE 波动来源分解（按观测功耗分位分组）{style.title_suffix}\n{title_sub}")

    handles = [Patch(facecolor=col, label=lab) for lab, _k, col in segs]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=10, title="来源")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.26, 0.86, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：在观测锚定实验中，我们把 phone_test 按观测总功耗分位点分成低/中/高三档。\n"
            "分解显示：高功耗条件下“老化”占比上升（增阻+欠压更敏感），从而形成 usage×aging 的交互效应。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.08, 0.86, 0.98))

    return fig


def _fig_decomposition_bootstrap_ci(rows: list[dict[str, str]], *, mode: PlotMode, n_boot: int = 2000, seed: int = 0):
    """对 11 的分解结果做 Bootstrap：展示抽样不确定性（95% CI），防止“换样本就变”质疑。"""

    import matplotlib.pyplot as plt

    style = apply_style(mode)
    phone_ids, _state_ids, _p_obs, y, s = _build_cell_grids(rows)
    I = len(phone_ids)

    rng = np.random.default_rng(int(seed))

    def _decomp_weighted(weights: np.ndarray) -> np.ndarray:
        """基于 phone_test 的加权重采样（cluster bootstrap）。

        注意：bootstrap 会出现同一 phone_test 被抽到多次；若用 bool mask 会“合并重复样本”导致 CI 偏小。
        这里用权重 w_i（出现次数）做加权 ANOVA 分解，保持 bootstrap 口径正确。
        """

        w = np.asarray(weights, dtype=float)
        if w.ndim != 1 or w.shape[0] != I:
            raise ValueError("weights 形状不正确")
        if float(np.sum(w)) <= 0:
            raise ValueError("weights 全为 0，无法分解")

        J = int(y.shape[1])
        W = float(np.sum(w))
        n_cells = float(W * J)
        denom = float(max(1.0, n_cells - 1.0))

        # grand mean（按 cell 权重：每个 phone 的每个 state 都被重复 w_i 次）
        grand = float(np.sum(w[:, None] * y) / (W * J))

        # phone 主效应：mean_i 对 state 均匀平均
        mean_i = np.mean(y, axis=1)
        ss_phone = float(np.sum((w * J) * (mean_i - grand) ** 2))

        # state 主效应：对 phone 按 w_i 加权
        mean_j = np.sum(w[:, None] * y, axis=0) / W
        ss_state = float(np.sum(W * (mean_j - grand) ** 2))

        # total SS（同样按 w_i 加权）
        ss_total = float(np.sum(w[:, None] * (y - grand) ** 2))
        ss_inter = float(max(0.0, ss_total - ss_phone - ss_state))

        var_phone = float(ss_phone / denom)
        var_state = float(ss_state / denom)
        var_inter = float(ss_inter / denom)

        # within-seed：E[Var(T|cell)]，按 cell 权重做平均
        var_within = float(np.sum(w[:, None] * (s * s)) / (W * J))

        var_total = float(var_phone + var_state + var_inter + var_within)
        if not (np.isfinite(var_total) and var_total > 0):
            return np.asarray([np.nan, np.nan, np.nan, np.nan], dtype=float)

        return np.asarray(
            [var_phone / var_total, var_state / var_total, var_inter / var_total, var_within / var_total],
            dtype=float,
        )

    fracs = np.zeros((int(n_boot), 4), dtype=float)
    for b in range(int(n_boot)):
        sel = rng.choice(np.arange(I), size=I, replace=True)
        # 允许重复 phone_test：对“真实使用状态分布”做重采样（cluster bootstrap）
        w = np.bincount(sel, minlength=I)
        fracs[b] = _decomp_weighted(w)

    qs = np.quantile(fracs, [0.025, 0.5, 0.975], axis=0)
    lo, mid, hi = qs[0], qs[1], qs[2]

    labels = ["使用", "老化", "交互", "随机"]
    cols = [PALETTE_SKIP_GRADIENT[0], PALETTE_SKIP_GRADIENT[2], PALETTE_SKIP_GRADIENT[1], PALETTE_SKIP_GRADIENT[3]]

    x = np.arange(4, dtype=float)
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    for i in range(4):
        ax.errorbar(
            [x[i]],
            [mid[i]],
            yerr=[[mid[i] - lo[i]], [hi[i] - mid[i]]],
            fmt="o",
            color=cols[i],
            ecolor="#333333",
            elinewidth=1.2,
            capsize=4,
            markersize=7,
            zorder=3,
        )
        ax.text(x[i], mid[i] + 0.03, _fmt_pct_zh(float(mid[i])), ha="center", va="bottom", fontsize=10, color="#333333")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 1.02)
    ax.set_ylabel("方差占比（0~1）")
    ax.set_title(f"Q3：观测锚定分解的抽样不确定性（Bootstrap 95% CI）{style.title_suffix}")
    ax.grid(axis="y", alpha=0.25)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：对 phone_test 维度做 cluster bootstrap（有放回重采样），得到分解占比的 95% 置信区间。\n"
            "CI 较宽通常意味着样本量偏小或使用状态分布重尾；这正是“需要更多观测基数”的信号。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_decomposition(rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    style = apply_style(mode)
    if not rows:
        raise ValueError("variance_decomposition_usage_aging.csv 为空")
    r = rows[0]

    fu = float(r.get("frac_usage_phone", "nan"))
    fa = float(r.get("frac_aging_state", "nan"))
    fi = float(r.get("frac_interaction", "nan"))
    fs = float(r.get("frac_seed_within", "nan"))

    vu = float(r.get("var_usage_phone_h2", "nan"))
    va = float(r.get("var_aging_state_h2", "nan"))
    vi = float(r.get("var_interaction_h2", "nan"))
    vs = float(r.get("var_seed_within_h2", "nan"))
    vt = float(r.get("var_total_h2", "nan"))

    def _fmt_pct(x: float) -> str:
        if not np.isfinite(x):
            return "?"
        v = float(x) * 100.0
        # 避免显示为 0.0%（读者容易误判“严格为 0”）
        if v < 0.05:
            return "<0.1%"
        return f"{v:.1f}%"

    # 用水平 100% 堆叠条形图避免 legend 遮挡（单一类别更直观）。
    c_usage = PALETTE_SKIP_GRADIENT[0]  # 使用：紫
    c_inter = PALETTE_SKIP_GRADIENT[1]  # 交互：亮青（小块用白边增强分隔）
    c_aging = PALETTE_SKIP_GRADIENT[2]  # 老化：青绿
    c_seed = PALETTE_SKIP_GRADIENT[3]  # 随机：深绿

    fig, ax = plt.subplots(figsize=(7.8, 3.2))
    left = 0.0
    segs = [
        ("使用状态（phone_test）", fu, c_usage),
        ("老化差异（battery_state）", fa, c_aging),
        ("交互项（usage×aging）", fi, c_inter),
        ("随机过程（seed）", fs, c_seed),
    ]
    for _, frac, col in segs:
        ax.barh([0], [frac], left=[left], color=col, alpha=0.95, height=0.55, edgecolor="white", linewidth=1.2)
        left += float(frac)

    ax.set_yticks([0])
    ax.set_yticklabels(["AndroWatts×老化状态"])
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("方差占比（0~1）")
    ax.grid(axis="x", alpha=0.22)
    ax.grid(axis="y", visible=False)

    title_main = "Q3：TTE 波动来源分解（使用×老化×随机）"
    if np.isfinite(fu) and np.isfinite(fa) and np.isfinite(fi) and np.isfinite(fs):
        title_sub = f"使用 {_fmt_pct(fu)} | 老化 {_fmt_pct(fa)} | 交互 {_fmt_pct(fi)} | 随机 {_fmt_pct(fs)}"
        ax.set_title(f"{title_main}{style.title_suffix}\n{title_sub}")
    else:
        ax.set_title(f"{title_main}{style.title_suffix}")

    # 图例放到右侧，避免与 x 轴标签/刻度拥挤（单条横向堆叠图更适合侧边图例）
    handles = [
        Patch(facecolor=c_usage, label="使用"),
        Patch(facecolor=c_aging, label="老化"),
        Patch(facecolor=c_inter, label="交互"),
        Patch(facecolor=c_seed, label="随机"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9, title="来源")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.28, 0.86, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：用 law of total variance + 二因素平方和分解近似：\n"
            "Var(T) ≈ Var_phone + Var_state + Var_interaction + E[Var(T|cell)]。\n"
            f"绝对方差（h^2）：usage={vu:.3g}，aging={va:.3g}，interaction={vi:.3g}，seed={vs:.3g}，total={vt:.3g}。\n"
            "其中 usage=手机使用状态（亮度/频率/流量等）差异；aging=电池健康/OCV 差异；seed=随机过程（后台唤醒/网络突发等）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.08, 0.86, 0.98))
    return fig


def _fig_tte_vs_power(rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    xs = []
    ys = []
    labs = []
    for r in rows:
        try:
            p = float(r.get("obs_total_w", "nan"))
            t = float(r.get("tte_mean_h", "nan"))
        except Exception:
            continue
        if not (np.isfinite(p) and np.isfinite(t) and p > 0):
            continue
        xs.append(p)
        ys.append(t)
        labs.append(str(r.get("battery_state_label", "?")))

    if not xs:
        raise ValueError("cells_tte.csv 中无有效点（obs_total_w/tte_mean_h）")

    # 老化档位配色（6 档）
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    palette = {
        "new": "#4C78A8",
        "slight": "#72B7B2",
        "moderate": "#F58518",
        "aged": "#E45756",
        "old": "#54A24B",
        "eol": "#B279A2",
    }

    fig, ax = plt.subplots(figsize=(7.8, 5.6))
    for lab in order:
        pts = [(x, y) for x, y, l in zip(xs, ys, labs) if l == lab]
        if not pts:
            continue
        x = np.array([p[0] for p in pts], dtype=float)
        y = np.array([p[1] for p in pts], dtype=float)
        ax.scatter(x, y, s=28, alpha=0.80, color=palette.get(lab, "#4C78A8"), label=lab, edgecolors="none")

    ax.set_xlabel("观测总功耗（W，AndroWatts rail 聚合）")
    ax.set_ylabel("模型预测 TTE 均值（小时）")
    ax.set_title(f"Q3：真实使用强度 × 老化档位对续航的影响{style.title_suffix}")
    ax.set_ylim(bottom=0.0)
    ax.legend(frameon=False, fontsize=9, loc="best", title="老化档位")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：每个点对应一个 (phone_test×battery_state) 条件；横轴是公开测量的功耗强度，纵轴是连续时间模型预测的耗尽时间。\n"
            "若同一功耗水平下不同颜色呈现明显垂直分层，说明“老化/OCV/内阻增长”会系统性缩短续航；\n"
            "而同一颜色在横向跨度很大，说明“使用状态差异”同样是主要驱动因素。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_tte_heatmap(rows: list[dict[str, str]], *, mode: PlotMode):
    """phone_test（按功耗排序）×老化档位 的 TTE 热力图。"""

    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # 收集维度
    phones = sorted({int(r["phone_test_id"]) for r in rows})
    labels = sorted({str(r["battery_state_label"]) for r in rows})
    # 为了更好读：把常见 6 档按语义排序
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    labels = [l for l in order if l in labels] + [l for l in labels if l not in order]

    # 每个 phone 的观测功耗（用于排序）
    p_by_phone: dict[int, float] = {}
    for r in rows:
        pid = int(r["phone_test_id"])
        if pid not in p_by_phone:
            try:
                p_by_phone[pid] = float(r.get("obs_total_w", "nan"))
            except Exception:
                p_by_phone[pid] = float("nan")

    phones_sorted = sorted(phones, key=lambda pid: float(p_by_phone.get(pid, float("inf"))))
    idx_phone = {pid: i for i, pid in enumerate(phones_sorted)}
    idx_lab = {lab: j for j, lab in enumerate(labels)}

    mat = np.full((len(phones_sorted), len(labels)), np.nan, dtype=float)
    for r in rows:
        try:
            pid = int(r["phone_test_id"])
            lab = str(r["battery_state_label"])
            t = float(r.get("tte_mean_h", "nan"))
        except Exception:
            continue
        if not (np.isfinite(t) and pid in idx_phone and lab in idx_lab):
            continue
        mat[idx_phone[pid], idx_lab[lab]] = float(t)

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    vmin = float(np.nanpercentile(mat, 5)) if np.isfinite(np.nanmin(mat)) else 0.0
    vmax = float(np.nanpercentile(mat, 95)) if np.isfinite(np.nanmax(mat)) else 1.0
    im = ax.imshow(mat, aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
    cbar = fig.colorbar(im, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label("TTE（小时）")

    ax.set_xlabel("老化档位（battery_state_label）")
    ax.set_ylabel("phone_test（按观测总功耗从低到高排序）")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    # y 轴不展示具体 phone_test_id（太长），只展示序号
    ax.set_yticks(np.arange(len(phones_sorted)))
    ax.set_yticklabels([str(i + 1) for i in range(len(phones_sorted))])
    ax.set_title(f"Q3：TTE 热力图（真实使用状态×老化档位）{style.title_suffix}")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        lo = float(np.nanmin([p for p in p_by_phone.values() if np.isfinite(p)]) if p_by_phone else float("nan"))
        hi = float(np.nanmax([p for p in p_by_phone.values() if np.isfinite(p)]) if p_by_phone else float("nan"))
        fig.text(
            0.02,
            0.02,
            "说明：每一行是一个真实 phone_test（来自 AndroWatts 聚合样本），按观测总功耗从低到高排序；每一列是一个老化档位。\n"
            f"本批样本的观测功耗范围约为 {lo:.2f}W ~ {hi:.2f}W（仅用于排序）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_margin_penalty_vs_power(rows: list[dict[str, str]], *, mode: PlotMode):
    """展示“老化对风险指标的影响”随使用强度变化（避免 02/03 那类易被误读为‘模型偏离真实’的图）。"""

    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # 每个 phone_test：对比 new vs eol 的裕量变化（更贴近“突然掉电/欠压”口径）
    # 注：这里的横轴 obs_total_w 来自观测数据（锚定使用强度）；纵轴来自模型输出（不是观测续航）。
    by_phone: dict[int, dict[str, float]] = {}
    for r in rows:
        try:
            pid = int(r["phone_test_id"])
            lab = str(r["battery_state_label"])
            p = float(r.get("obs_total_w", "nan"))
            tte = float(r.get("tte_mean_h", "nan"))
            mrg = float(r.get("min_headroom_margin_mean", "nan"))
        except Exception:
            continue
        if not (np.isfinite(p) and np.isfinite(tte) and np.isfinite(mrg)):
            continue
        d = by_phone.setdefault(pid, {})
        d["obs_total_w"] = float(p)
        d[f"tte_{lab}"] = float(tte)
        d[f"margin_{lab}"] = float(mrg)

    xs: list[float] = []
    dy_margin: list[float] = []
    dy_tte_pct: list[float] = []
    for pid, d in sorted(by_phone.items()):
        if ("margin_new" not in d) or ("margin_eol" not in d) or ("tte_new" not in d) or ("tte_eol" not in d):
            continue
        p = float(d["obs_total_w"])
        m_new = float(d["margin_new"])
        m_eol = float(d["margin_eol"])
        t_new = float(d["tte_new"])
        t_eol = float(d["tte_eol"])
        if not (np.isfinite(p) and np.isfinite(m_new) and np.isfinite(m_eol) and np.isfinite(t_new) and np.isfinite(t_eol) and t_new > 0):
            continue
        xs.append(p)
        dy_margin.append(m_eol - m_new)  # <0 表示更接近欠压边界（更危险）
        dy_tte_pct.append(100.0 * (t_eol - t_new) / t_new)  # <0 表示续航缩短

    if not xs:
        raise ValueError("无法从 cells_tte.csv 提取 new/eol 对照（缺少 battery_state_label 或数据不完整）")

    x = np.asarray(xs, dtype=float)
    y1 = np.asarray(dy_margin, dtype=float)
    y2 = np.asarray(dy_tte_pct, dtype=float)

    # 按功耗三分位（可用于分组着色与视觉引导）
    q1, q2 = np.quantile(x, [1 / 3, 2 / 3]).tolist()
    bins = np.digitize(x, [q1, q2])  # 0/1/2
    col_bins = [PALETTE_SKIP_GRADIENT[0], PALETTE_SKIP_GRADIENT[2], PALETTE_SKIP_GRADIENT[3]]
    c = np.array([col_bins[int(b)] for b in bins], dtype=object)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.3), sharex=True)

    # A) 供电裕量变化（更贴题面“突然掉电/欠压”）
    ax1.scatter(x, y1, s=48, alpha=0.88, color=c, edgecolors="white", linewidths=0.7)
    ax1.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.55)
    ax1.axvline(q1, color="#666666", linewidth=1.0, alpha=0.35, linestyle="--")
    ax1.axvline(q2, color="#666666", linewidth=1.0, alpha=0.35, linestyle="--")
    ax1.set_xlabel("观测总功耗（W，AndroWatts rail 聚合）")
    ax1.set_ylabel("Δ裕量 = margin(eol) - margin(new)")
    ax1.set_title("老化对“欠压裕量”的影响（越负越危险）")

    # B) 续航变化百分比（辅助：解释为什么 TTE 端有时看不出强交互）
    ax2.scatter(x, y2, s=48, alpha=0.88, color=c, edgecolors="white", linewidths=0.7)
    ax2.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.55)
    ax2.axvline(q1, color="#666666", linewidth=1.0, alpha=0.35, linestyle="--")
    ax2.axvline(q2, color="#666666", linewidth=1.0, alpha=0.35, linestyle="--")
    ax2.set_xlabel("观测总功耗（W，AndroWatts rail 聚合）")
    ax2.set_ylabel("ΔTTE（%）= (eol-new)/new")
    ax2.set_title("老化对 TTE 的影响（百分比）")

    fig.suptitle(f"Q3：观测锚定下的“使用强度×老化”交互（new vs eol）{style.title_suffix}", y=1.02)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.26, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：横轴功耗来自公开观测（锚定使用强度），纵轴为机理模型输出（不是观测续航）。\n"
            "- 左图：裕量下降更敏感地揭示“高功耗 + 增阻”导致更接近欠压边界，从而解释‘突然掉电’现象；\n"
            "- 右图：TTE 缩短通常更接近比例缩放，因此交互在 TTE 上可能不如裕量明显。\n"
            "虚线为功耗三分位边界（低/中/高负载）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_tte_heatmap_power_bins(rows: list[dict[str, str]], *, mode: PlotMode, n_bins: int = 3):
    """把 24×6 的热力图压缩成 n_bins×6（按功耗分位分组），显著减少重叠与视觉噪声。"""

    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    style = apply_style(mode)
    phone_ids, _state_ids, p_obs, y, _s = _build_cell_grids(rows)

    # 按观测功耗排序并分组
    order = np.argsort(p_obs)
    groups = np.array_split(order, int(n_bins))
    if len(groups) < 2:
        raise ValueError("n_bins 太小，无法分组")

    # 老化标签按语义顺序
    # 注：battery_state_id 的顺序并不等同于 label 语义顺序，因此这里从原始 rows 重建 label->col
    labels_all = sorted({str(r.get("battery_state_label", "")) for r in rows if str(r.get("battery_state_label", "")).strip()})
    order_labels = ["new", "slight", "moderate", "aged", "old", "eol"]
    labels = [l for l in order_labels if l in labels_all] + [l for l in labels_all if l not in order_labels]
    if not labels:
        raise ValueError("cells_tte.csv 中缺少 battery_state_label")

    # 组×label 的均值 TTE
    # 从 rows 中构造 (phone_id, label)->tte
    t_map: dict[tuple[int, str], float] = {}
    for r in rows:
        try:
            pid = int(r["phone_test_id"])
            lab = str(r["battery_state_label"])
            t = float(r.get("tte_mean_h", "nan"))
        except Exception:
            continue
        if np.isfinite(t):
            t_map[(pid, lab)] = float(t)

    mat = np.full((len(groups), len(labels)), np.nan, dtype=float)
    y_labels = []
    for gi, idx in enumerate(groups):
        p_lo = float(np.min(p_obs[idx]))
        p_hi = float(np.max(p_obs[idx]))
        name = ["低功耗", "中功耗", "高功耗"][gi] if gi < 3 else f"第{gi+1}组"
        y_labels.append(f"{name}\n({p_lo:.2f}~{p_hi:.2f}W)")
        pids = [int(phone_ids[i]) for i in idx.tolist()]
        for j, lab in enumerate(labels):
            xs = [t_map.get((pid, lab), float("nan")) for pid in pids]
            xs = [float(v) for v in xs if np.isfinite(v)]
            mat[gi, j] = float(np.mean(xs)) if xs else float("nan")

    # 配色：用用户指定的 Skip Gradient 做连续色带
    cmap = LinearSegmentedColormap.from_list("skip_gradient", list(PALETTE_SKIP_GRADIENT))
    vmin = float(np.nanpercentile(mat, 5)) if np.isfinite(np.nanmin(mat)) else 0.0
    vmax = float(np.nanpercentile(mat, 95)) if np.isfinite(np.nanmax(mat)) else 1.0

    fig, ax = plt.subplots(figsize=(9.2, 3.9))
    im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    cbar = fig.colorbar(im, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label("TTE（小时，均值）")

    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_xlabel("老化档位（battery_state_label）")
    ax.set_title(f"Q3：TTE（均值）在使用强度分位×老化档位上的变化{style.title_suffix}")

    # 在格子里写数值（小时），便于论文读者快速读结论
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if not np.isfinite(v):
                continue
            rgba = im.cmap(im.norm(float(v)))
            lum = 0.299 * float(rgba[0]) + 0.587 * float(rgba[1]) + 0.114 * float(rgba[2])
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=10, color=("black" if lum > 0.65 else "white"))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：把 24 个 phone_test 按观测总功耗分位点分成低/中/高三档，每格为该档内对 6 个老化档位的平均 TTE。\n"
            "该图用于展示‘使用强度’与‘老化’对预测续航的主效应方向（趋势），避免 24×6 热图在正文里过于拥挤。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _read_single_row_csv(path: Path) -> dict[str, str]:
    rows = _read_csv(path)
    if not rows:
        raise ValueError(f"{path} 为空")
    return dict(rows[0])


def _fig_decomposition_cells_compare(reports_dirs: list[Path], *, labels: list[str], mode: PlotMode):
    """跨电芯（Cell01/02/03）对照：验证 11 的分解结论是否稳健。"""

    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    style = apply_style(mode)
    if len(reports_dirs) != len(labels):
        raise ValueError("reports_dirs 与 labels 长度不一致")
    if len(reports_dirs) < 2:
        raise ValueError("至少需要 2 个 reports_dir 才能对照")

    items = []
    for d, lab in zip(reports_dirs, labels):
        r = _read_single_row_csv(Path(d) / "variance_decomposition_usage_aging.csv")
        items.append(
            {
                "label": str(lab),
                "frac_usage_phone": float(r.get("frac_usage_phone", "nan")),
                "frac_aging_state": float(r.get("frac_aging_state", "nan")),
                "frac_interaction": float(r.get("frac_interaction", "nan")),
                "frac_seed_within": float(r.get("frac_seed_within", "nan")),
            }
        )

    c_usage = PALETTE_SKIP_GRADIENT[0]
    c_inter = PALETTE_SKIP_GRADIENT[1]
    c_aging = PALETTE_SKIP_GRADIENT[2]
    c_seed = PALETTE_SKIP_GRADIENT[3]
    segs = [
        ("使用", "frac_usage_phone", c_usage),
        ("老化", "frac_aging_state", c_aging),
        ("交互", "frac_interaction", c_inter),
        ("随机", "frac_seed_within", c_seed),
    ]

    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    y_pos = np.arange(len(items))

    def _luminance(hex_color: str) -> float:
        hc = hex_color.lstrip("#")
        r = int(hc[0:2], 16) / 255.0
        g = int(hc[2:4], 16) / 255.0
        b = int(hc[4:6], 16) / 255.0
        return 0.299 * r + 0.587 * g + 0.114 * b

    for yi, it in enumerate(items):
        left = 0.0
        for name, key, col in segs:
            frac = float(it.get(key, float("nan")))
            ax.barh([yi], [frac], left=[left], color=col, alpha=0.95, height=0.56, edgecolor="white", linewidth=1.2)
            if np.isfinite(frac) and frac > 0.01:
                ax.text(
                    left + frac / 2.0,
                    yi,
                    _fmt_pct_zh(frac),
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=("black" if _luminance(col) > 0.62 else "white"),
                )
            left += float(frac)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([it["label"] for it in items])
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("方差占比（0~1）")
    ax.set_title(f"Q3：观测锚定分解的跨电芯稳健性{style.title_suffix}")

    handles = [Patch(facecolor=col, label=lab) for lab, _k, col in segs]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=10, title="来源")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 0.84, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：仅更换 battery_state_table 中的电芯（Cell01/02/03），保持 phone_test 抽样与仿真设置不变。\n"
            "若三条柱的占比结构一致，则说明“使用主导、老化次之、交互更小”的结论对电芯选择不敏感（更稳健）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout(rect=(0.0, 0.08, 0.84, 0.98))
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 master_table 数据集实验出图（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q3/paper 与 q3/study）")
    ap.add_argument(
        "--reports-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_master_table"),
        help="输入报表目录（默认 out_reports/q3/observed_master_table）",
    )
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    cells_path = reports_dir / "cells_tte.csv"
    decomp_path = reports_dir / "variance_decomposition_usage_aging.csv"
    if not cells_path.exists() or not decomp_path.exists():
        raise FileNotFoundError("缺少报表文件：请先运行 scripts/run_q3_master_table_experiment.py")

    cell_rows = _read_csv(cells_path)
    decomp_rows = _read_csv(decomp_path)

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_dir = ensure_dir(Path(args.out_dir) / "q3" / str(m) / "observed_master_table")
        n_fig = 0

        fig = _fig_decomposition(decomp_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "01_variance_decomposition_usage_aging.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        import matplotlib.pyplot as plt

        plt.close(fig)
        n_fig += 1

        fig = _fig_tte_vs_power(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "02_tte_vs_obs_power_by_aging.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        fig = _fig_tte_heatmap(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "03_tte_heatmap_phone_by_power_vs_aging.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        # v2：更“论文级”的 11（不覆盖旧图，新增 04/05 以供挑选）
        fig = _fig_decomposition_power_bins(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "04_variance_decomposition_power_bins.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        fig = _fig_decomposition_bootstrap_ci(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "05_variance_decomposition_bootstrap_ci.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        fig = _fig_margin_penalty_vs_power(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "06_aging_penalty_margin_vs_obs_power.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        fig = _fig_tte_heatmap_power_bins(cell_rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "07_tte_heatmap_power_bins_vs_aging.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)
        n_fig += 1

        # 可选：跨电芯对照（若用户已生成 Cell02/Cell03 报表则自动补充）
        parent = reports_dir.parent
        candidates = [
            (reports_dir, "Cell01"),
            (parent / "observed_master_table_cell02", "Cell02"),
            (parent / "observed_master_table_cell03", "Cell03"),
        ]
        dirs = []
        labs = []
        for d, lab in candidates:
            if (Path(d) / "variance_decomposition_usage_aging.csv").exists():
                dirs.append(Path(d))
                labs.append(str(lab))
        if len(dirs) >= 2:
            fig = _fig_decomposition_cells_compare(dirs, labels=labs, mode=m)  # type: ignore[arg-type]
            p = out_dir / "08_variance_decomposition_cells_compare.png"
            savefig(fig, p, mode=m)  # type: ignore[arg-type]
            plt.close(fig)
            n_fig += 1

        print(f"[{m}] generated {n_fig} figures -> {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
