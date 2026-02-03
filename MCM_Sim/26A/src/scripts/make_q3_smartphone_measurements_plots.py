#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：生成 Q3 SmartphoneMeasurements（波动假设检验 + α-sweep）图像，paper/study 两套。

读取：
- out_reports/q3/observed_smartphone_measurements/trace_vs_mean.csv
- out_reports/q3/observed_smartphone_measurements/fluctuation_sweep.csv
- out_reports/q3/observed_smartphone_measurements/traces/*.csv

输出：
- out_plots/q3/{paper|study}/observed_smartphone_measurements/
"""

from __future__ import annotations

import argparse
import csv
import re
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


def _sanitize(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\\-]+", "_", str(s)).strip("_")


def _label_zh(lab: str) -> str:
    m = {
        "new": "新电池",
        "slight": "轻度老化",
        "moderate": "中度老化",
        "aged": "老化",
        "old": "严重老化",
        "eol": "寿命末期",
    }
    return m.get(str(lab), str(lab))


def _load_trace_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = _read_csv(path)
    t = np.array([float(r.get("t_s", "nan")) for r in rows], dtype=float)
    p = np.array([float(r.get("p_w", "nan")) for r in rows], dtype=float)
    m = np.isfinite(t) & np.isfinite(p)
    return t[m], p[m]


def _fig_power_traces(trace_dir: Path, rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # 选 3 条代表性轨迹：低波动 / 中等波动 / 高波动（按 CV 分位点）。
    # 这样比“取前 3 条”更贴近 Q3 叙事，也更利于论文展示。
    recs: dict[tuple[str, str, int], tuple[float, float]] = {}  # (phone,test,dt)->(cv, meanW)
    for r in rows:
        phone = str(r.get("phone", "")).strip()
        test = str(r.get("test", "")).strip()
        try:
            dt_s = float(r.get("dt_s", "nan"))
            cv = float(r.get("trace_cv", "nan"))
            mw = float(r.get("trace_mean_W", "nan"))
        except Exception:
            continue
        if not phone or not test or not np.isfinite(dt_s) or not np.isfinite(cv) or not np.isfinite(mw):
            continue
        k = (phone, test, int(round(dt_s)))
        if k not in recs:
            recs[k] = (float(cv), float(mw))

    items = [(k, cv, mw) for k, (cv, mw) in recs.items()]
    items.sort(key=lambda x: x[1])  # by cv
    if not items:
        raise ValueError("trace_vs_mean.csv 中没有可用的 (phone,test,dt_s) 组合")

    pick = [items[0]]
    if len(items) >= 2:
        pick.append(items[len(items) // 2])
    if len(items) >= 3:
        pick.append(items[-1])
    # 去重（当样本少时可能重复）
    seen = set()
    keys = []
    for (k, _cv, _mw) in pick:
        if k in seen:
            continue
        seen.add(k)
        keys.append(k)

    fig, axes = plt.subplots(len(keys), 1, figsize=(7.8, 2.7 * len(keys)), sharex=False)
    if len(keys) == 1:
        axes = [axes]

    for ax, (phone, test, dt_tag) in zip(axes, keys):
        name = f"{_sanitize(phone)}__{_sanitize(test)}_dt{int(dt_tag)}s.csv"
        p = trace_dir / name
        if not p.exists():
            raise FileNotFoundError(str(p))

        t, y = _load_trace_csv(p)
        if t.size <= 1:
            continue
        mu = float(np.mean(y))
        cv = float(np.std(y) / mu) if mu > 1e-12 else float("nan")

        ax.plot(t, y, color="#4C78A8", lw=1.5, alpha=0.95)
        ax.axhline(mu, color="#E45756", lw=1.3, alpha=0.85, linestyle="--", label="均值功耗")
        ax.set_ylabel("功耗（W）")
        extra = f"CV≈{cv:.2f}" if np.isfinite(cv) else "CV=?"
        ax.set_title(f"{phone}/{test}：P(t) 与均值（dt={dt_tag}s，{extra}）{style.title_suffix}")
        ax.legend(frameon=False, fontsize=9, loc="upper right")

    axes[-1].set_xlabel("时间（秒）")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.24, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：蓝线为 Monsoon 实测功耗轨迹（循环重复作为外生输入）；红虚线为该轨迹的平均功耗。\n"
            "Q3 的一个关键假设是：把真实波动简化为均值是否会影响 TTE？该问题在存在欠压截止（V_cut）时尤其重要。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _fig_tte_trace_vs_mean(rows: list[dict[str, str]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    def case_key(r: dict[str, str]) -> str:
        return f"{r.get('phone','?')}/{r.get('test','?')}"

    def case_label_zh(case: str) -> str:
        """用于图内标注的短中文名（避免 x 轴长标签导致大量留白/拥挤）。"""

        if "/" not in case:
            return case
        phone, test = case.split("/", 1)
        m = {
            "smartphoneBaseline": "基线",
            "smartphoneServerTcpRouter": "TCP 路由",
            "smartphoneClientTcpRouter": "TCP 路由",
        }
        t = m.get(test, test)
        t = t.replace("smartphone", "")
        t = t.replace("Client", "客户端").replace("Server", "服务端")
        # 标注尽量短：一行即可
        label = f"{phone}-{t}".strip("-")
        if len(label) > 18:
            label = label[:18] + "…"
        return label

    cases = sorted({case_key(r) for r in rows})
    labels = sorted({str(r.get("battery_state_label", "")) for r in rows if str(r.get("battery_state_label", "")).strip()})
    # 常见排序
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    labels = [l for l in order if l in labels] + [l for l in labels if l not in order]

    # 当标签过多时，只展示 new/eol（若存在）
    show_labels = labels
    if len(labels) > 2:
        show_labels = [l for l in ["new", "eol"] if l in labels]
        if not show_labels:
            show_labels = labels[:2]

    # case×label -> delta（从报表读取，避免重复计算造成口径漂移）
    delta_frac: dict[tuple[str, str], float] = {}
    meta: dict[str, tuple[float, float]] = {}  # case -> (meanW, cv)

    for r in rows:
        c = case_key(r)
        lab = str(r.get("battery_state_label", "")).strip()
        if not c or not lab:
            continue
        try:
            d = float(r.get("delta_tte_frac", "nan"))
            mw = float(r.get("trace_mean_W", "nan"))
            cv = float(r.get("trace_cv", "nan"))
        except Exception:
            continue
        if np.isfinite(d):
            delta_frac[(c, lab)] = float(d)
        if np.isfinite(mw) and np.isfinite(cv):
                meta[c] = (float(mw), float(cv))

    def _collect(lab: str) -> tuple[np.ndarray, np.ndarray]:
        xs = []
        ys = []
        for c in cases:
            if c not in meta:
                continue
            cv = float(meta[c][1])
            d = delta_frac.get((c, lab), float("nan"))
            if not (np.isfinite(cv) and np.isfinite(d)):
                continue
            xs.append(float(cv))
            ys.append(float(100.0 * d))
        return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)

    x_new, y_new = _collect("new")
    x_eol, y_eol = _collect("eol")

    # 若 case 数量过多：改用散点图（更不拥挤，也更利于“统计规律”叙事）。
    n_cases = len({c for c in cases if c in meta})
    if n_cases > 12:
        # ----------------------------
        # 论文版：用“分箱中位数 + IQR”替代纯散点，显著减少重叠、读图更直观；
        # 学习版：保留散点（含趋势线/相关系数），便于理解数据细节。
        # ----------------------------
        if not style.annotate:
            fig, ax = plt.subplots(figsize=(7.8, 4.6))

            c_new = PALETTE_SKIP_GRADIENT[0]
            c_eol = PALETTE_SKIP_GRADIENT[3]

            # 轻量散点背景（极低透明度）：给读者“样本量/离散度”的直觉，但不抢主题
            ax.scatter(x_new, y_new, s=18, color=c_new, alpha=0.20, edgecolor="none")
            ax.scatter(x_eol, y_eol, s=18, color=c_eol, alpha=0.20, edgecolor="none", marker="s")

            def _bin_summary(x: np.ndarray, y: np.ndarray, *, edges: np.ndarray):
                centers = []
                med = []
                q25 = []
                q75 = []
                ns = []
                for i in range(len(edges) - 1):
                    lo = float(edges[i])
                    hi = float(edges[i + 1])
                    if i == len(edges) - 2:
                        m = (x >= lo) & (x <= hi)
                    else:
                        m = (x >= lo) & (x < hi)
                    yy = y[m]
                    if yy.size == 0:
                        continue
                    centers.append(0.5 * (lo + hi))
                    med.append(float(np.median(yy)))
                    q25.append(float(np.quantile(yy, 0.25)))
                    q75.append(float(np.quantile(yy, 0.75)))
                    ns.append(int(yy.size))
                return np.asarray(centers), np.asarray(med), np.asarray(q25), np.asarray(q75), np.asarray(ns)

            # 用分位点做分箱，确保每个箱子都有近似均匀的样本量（比等宽更稳健）
            xs_all = np.concatenate([x_new, x_eol]) if (x_new.size and x_eol.size) else (x_new if x_new.size else x_eol)
            # 至少 4 箱，最多 7 箱（样本较少时避免过度分箱）
            n_bins = 6
            qs = np.linspace(0.0, 1.0, n_bins + 1)
            edges = np.quantile(xs_all, qs)
            # 去重（避免重复边界导致空箱）
            edges = np.unique(edges)
            if edges.size < 3:
                # 退化情况：直接用线性等分
                edges = np.linspace(float(np.min(xs_all)), float(np.max(xs_all)), 4)

            cx_n, m_n, q1_n, q3_n, n_n = _bin_summary(x_new, y_new, edges=edges)
            cx_e, m_e, q1_e, q3_e, n_e = _bin_summary(x_eol, y_eol, edges=edges)

            # IQR 阴影
            if cx_n.size:
                ax.fill_between(cx_n, q1_n, q3_n, color=c_new, alpha=0.14, linewidth=0.0)
                ax.plot(cx_n, m_n, color=c_new, lw=2.2, marker="o", markersize=6, label="新电池（中位数）")
            if cx_e.size:
                ax.fill_between(cx_e, q1_e, q3_e, color=c_eol, alpha=0.14, linewidth=0.0)
                ax.plot(cx_e, m_e, color=c_eol, lw=2.2, marker="s", markersize=6, label="寿命末期（中位数）")

            ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.75)
            ax.set_xlabel("功耗波动强度 CV（无量纲）")
            ax.set_ylabel("ΔTTE（%）")
            ax.set_title(f"Q3：用均值替代波动轨迹的误差 vs 波动强度{style.title_suffix}")
            ax.legend(frameon=False, fontsize=9, loc="upper right", title="老化档位")

            ys = np.concatenate([y_new, y_eol]) if (y_new.size and y_eol.size) else (y_new if y_new.size else y_eol)
            if ys.size:
                y_min = float(np.min(ys))
                y_max = float(np.max(ys))
                ax.set_ylim(min(-0.3, y_min - 0.35), max(0.2, y_max + 0.25))

            fig.tight_layout()
            return fig

        fig, ax = plt.subplots(figsize=(7.8, 4.6))

        c_new = PALETTE_SKIP_GRADIENT[0]
        c_eol = PALETTE_SKIP_GRADIENT[3]

        ax.scatter(x_new, y_new, s=32, color=c_new, alpha=0.78, edgecolor="white", linewidth=0.7, label="新电池")
        ax.scatter(x_eol, y_eol, s=32, marker="s", color=c_eol, alpha=0.78, edgecolor="white", linewidth=0.7, label="寿命末期")

        # 趋势线（线性）：study 版用于帮助“肉眼抓趋势”，不追求因果解释。
        def _fit_line(x: np.ndarray, y: np.ndarray):
            if x.size < 3:
                return None
            a, b = np.polyfit(x, y, deg=1)
            xx = np.linspace(float(np.min(x)), float(np.max(x)), 100)
            yy = a * xx + b
            return xx, yy, float(a), float(b)

        fit_new = _fit_line(x_new, y_new)
        fit_eol = _fit_line(x_eol, y_eol)
        if fit_new is not None:
            xx, yy, *_ = fit_new
            ax.plot(xx, yy, color=c_new, lw=1.4, alpha=0.85)
        if fit_eol is not None:
            xx, yy, *_ = fit_eol
            ax.plot(xx, yy, color=c_eol, lw=1.4, alpha=0.85)

        ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.75)
        ax.set_xlabel("功耗波动强度 CV（无量纲）")
        ax.set_ylabel("ΔTTE（%）")
        ax.set_title(f"Q3：用均值替代波动轨迹的误差 vs 波动强度{style.title_suffix}")
        ax.legend(frameon=False, fontsize=9, loc="upper right", title="老化档位")

        # 视野：自动给一点上下边距
        ys = np.concatenate([y_new, y_eol]) if (y_new.size and y_eol.size) else (y_new if y_new.size else y_eol)
        if ys.size:
            y_min = float(np.min(ys))
            y_max = float(np.max(ys))
            ax.set_ylim(min(-0.3, y_min - 0.35), max(0.2, y_max + 0.25))

        if style.annotate:
            # Spearman（无需 scipy）：用于“单调相关”解释
            def _spearman(x: np.ndarray, y: np.ndarray) -> float:
                m = np.isfinite(x) & np.isfinite(y)
                x = x[m]
                y = y[m]
                if x.size < 3:
                    return float("nan")

                def _rank(a: np.ndarray) -> np.ndarray:
                    idx = np.argsort(a)
                    r = np.empty_like(idx, dtype=float)
                    r[idx] = np.arange(a.size, dtype=float)
                    s = a[idx]
                    i = 0
                    while i < s.size:
                        j = i
                        while j + 1 < s.size and s[j + 1] == s[i]:
                            j += 1
                        if j > i:
                            avg = 0.5 * (i + j)
                            r[idx[i : j + 1]] = avg
                        i = j + 1
                    return r

                rx = _rank(x)
                ry = _rank(y)
                rx = rx - float(np.mean(rx))
                ry = ry - float(np.mean(ry))
                denom = float(np.sqrt(float(np.sum(rx * rx) * np.sum(ry * ry))))
                return float(np.sum(rx * ry) / denom) if denom > 1e-12 else float("nan")

            r_new = _spearman(x_new, y_new)
            r_eol = _spearman(x_eol, y_eol)
            fig.tight_layout(rect=(0.0, 0.26, 1.0, 0.98))
            fig.text(
                0.02,
                0.02,
                "说明：把真实功耗轨迹 P(t) 简化为均值 P̄ 可能引入误差（欠压截止 + I^2R 非线性）。\n"
                "ΔTTE(%) = (TTE_trace - TTE_mean) / TTE_mean，ΔTTE<0 表示波动更伤续航。\n"
                f"补充：Spearman 相关（CV vs ΔTTE%）：新电池 r≈{r_new:.2f}；寿命末期 r≈{r_eol:.2f}。",
                ha="left",
                va="bottom",
                fontsize=9,
            )
        else:
            fig.tight_layout()

        return fig

    # ----------------------------
    # 重新设计（论文更“干净/高级”）：
    # - 横轴：功耗波动强度（CV），避免长 x 标签造成拥挤与大留白；
    # - 纵轴：ΔTTE(%)；用竖向“哑铃”表示 new vs eol（同一波动下，老化状态不同）。
    # ----------------------------
    fig, ax = plt.subplots(figsize=(7.8, 4.6))

    # 颜色：最多 4 色，采用 Skip Gradient；这里只用 2 色（new/eol）。
    c_new = PALETTE_SKIP_GRADIENT[0]
    c_eol = PALETTE_SKIP_GRADIENT[3]

    # 组织每个 case 的点
    pts = []
    for c in cases:
        if c not in meta:
            continue
        mw, cv = meta[c]
        y_new = 100.0 * delta_frac.get((c, "new"), float("nan"))
        y_eol = 100.0 * delta_frac.get((c, "eol"), float("nan"))
        pts.append((c, float(cv), float(mw), float(y_new), float(y_eol)))

    # 按波动强度从小到大排，读者更容易读趋势
    pts.sort(key=lambda x: x[1])

    # paper：尽量干净；study：带解释与标注
    label_points = bool(style.annotate)

    # 画连接线 + 点（哑铃图）
    for c, cv, mw, y_new, y_eol in pts:
        ys = [y_new, y_eol]
        ys = [y for y in ys if np.isfinite(y)]
        if ys:
            ax.vlines(cv, min(ys), max(ys), color="#444444", linewidth=1.4, alpha=0.75, zorder=2)

        if np.isfinite(y_new):
            ax.scatter(
                [cv],
                [y_new],
                s=82,
                marker="o",
                color=c_new,
                edgecolor="white",
                linewidth=1.2,
                zorder=3,
                label="新电池" if c == pts[0][0] else None,
            )
            if label_points:
                ax.text(cv, y_new - 0.12, f"{y_new:+.1f}%", ha="center", va="top", fontsize=9, color="#333333")
        if np.isfinite(y_eol):
            ax.scatter(
                [cv],
                [y_eol],
                s=82,
                marker="s",
                color=c_eol,
                edgecolor="white",
                linewidth=1.2,
                zorder=3,
                label="寿命末期" if c == pts[0][0] else None,
            )
            if label_points:
                ax.text(cv, y_eol - 0.12, f"{y_eol:+.1f}%", ha="center", va="top", fontsize=9, color="#333333")

        # case 标注：只在学习版显示，论文版避免拥挤（可在正文配表/注释说明样本来源）
        if style.annotate:
            y_top = max([y for y in [y_new, y_eol] if np.isfinite(y)] + [0.0])
            ax.text(cv, y_top + 0.12, case_label_zh(c), ha="center", va="bottom", fontsize=10, color="#222222")

    ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.75)
    ax.set_xlabel("功耗波动强度 CV（无量纲）")
    ax.set_ylabel("ΔTTE（%）")
    ax.set_title(f"Q3：用均值替代波动轨迹的误差 vs 波动强度{style.title_suffix}")
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="老化档位")

    # 视野：把 0 附近留一点空间，同时确保极端点不顶到边界。
    ys_all = []
    for _, _, _, yn, ye in pts:
        if np.isfinite(yn):
            ys_all.append(float(yn))
        if np.isfinite(ye):
            ys_all.append(float(ye))
    if ys_all:
        y_min = min(ys_all)
        y_max = max(ys_all)
        # 顶部至少留出 0.2%，底部留 0.3%，让标注不挤
        ax.set_ylim(min(-0.3, y_min - 0.35), max(0.2, y_max + 0.25))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.26, 1.0, 0.98))
        notes = []
        for c, cv, mw, _, _ in pts:
            notes.append(f"{case_label_zh(c)}：P̄≈{mw:.2f}W，CV≈{cv:.2f}")
        note = "；".join(notes)
        fig.text(
            0.02,
            0.02,
            "说明：对同一平均功耗，电池端存在非线性（I^2R 损耗 + 欠压截止），因此“波动结构”可能改变 TTE。\n"
            "ΔTTE(%) = (TTE_trace - TTE_mean) / TTE_mean。\n"
            "本图用 ΔTTE（%）直接量化“用均值替代波动轨迹”的误差；ΔTTE<0 表示波动更伤续航。\n"
            + ("补充：" + note if note else ""),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    return fig


def _fig_fluctuation_sweep(rows: list[dict[str, str]], *, mode: PlotMode):
    """画“波动强度 sweep（α）”结果：跨 traces 聚合的 ΔTTE(%) vs α。"""

    import matplotlib.pyplot as plt

    style = apply_style(mode)

    # 读取并整理
    alphas = sorted({float(r.get("alpha", "nan")) for r in rows if r.get("alpha") is not None})
    alphas = [a for a in alphas if np.isfinite(a)]
    if not alphas:
        raise ValueError("fluctuation_sweep.csv 中没有 alpha 列")

    labels = sorted({str(r.get("battery_state_label", "")).strip() for r in rows if str(r.get("battery_state_label", "")).strip()})
    order = ["new", "slight", "moderate", "aged", "old", "eol"]
    labels = [l for l in order if l in labels] + [l for l in labels if l not in order]
    # 论文重点：new vs eol（若存在）
    show_labels = [l for l in ["new", "eol"] if l in labels] or labels[:2]

    # label,alpha -> list[delta%]
    data: dict[tuple[str, float], list[float]] = {}
    traces = sorted({str(r.get("trace", "")).strip() for r in rows if str(r.get("trace", "")).strip()})
    for r in rows:
        lab = str(r.get("battery_state_label", "")).strip()
        if lab not in show_labels:
            continue
        try:
            a = float(r.get("alpha", "nan"))
            d = float(r.get("delta_tte_pct", "nan"))
        except Exception:
            continue
        if not (np.isfinite(a) and np.isfinite(d)):
            continue
        data.setdefault((lab, float(a)), []).append(float(d))

    if not any((lab, a) in data for lab in show_labels for a in alphas):
        raise ValueError("fluctuation_sweep.csv 中缺少可用的 (label,alpha,delta_tte_pct) 数据")

    # 颜色：最多 4 色，采用 Skip Gradient
    c_map = {
        "new": PALETTE_SKIP_GRADIENT[0],
        "eol": PALETTE_SKIP_GRADIENT[3],
    }
    # 兜底：若 label 不在预设里，循环取色
    fallback = iter(PALETTE_SKIP_GRADIENT)

    def _color(lab: str) -> str:
        if lab in c_map:
            return c_map[lab]
        return next(fallback)

    # 统计量：中位数 + IQR
    series = {}
    for lab in show_labels:
        meds = []
        p25 = []
        p75 = []
        ns = []
        for a in alphas:
            xs = data.get((lab, float(a)), [])
            xs = [x for x in xs if np.isfinite(x)]
            if not xs:
                meds.append(float("nan"))
                p25.append(float("nan"))
                p75.append(float("nan"))
                ns.append(0)
                continue
            meds.append(float(np.percentile(xs, 50)))
            p25.append(float(np.percentile(xs, 25)))
            p75.append(float(np.percentile(xs, 75)))
            ns.append(len(xs))
        series[lab] = (np.array(meds, dtype=float), np.array(p25, dtype=float), np.array(p75, dtype=float), ns)

    fig, ax = plt.subplots(figsize=(7.8, 4.6))

    for lab in show_labels:
        med, lo, hi, ns = series[lab]
        col = _color(lab)
        ax.plot(
            alphas,
            med,
            color=col,
            lw=2.1,
            marker="o",
            markersize=5.5,
            alpha=0.95,
            label=_label_zh(lab),
        )
        ax.fill_between(alphas, lo, hi, color=col, alpha=0.14, linewidth=0.0)

    ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.75)
    ax.set_xlim(min(alphas) - 0.02, max(alphas) + 0.02)
    ax.set_xlabel("波动强度系数 α（0=均值常功耗，1=原始波动）")
    ax.set_ylabel("ΔTTE（%）")
    ax.set_title(f"Q3：均值固定下的波动强度 sweep（跨轨迹聚合）{style.title_suffix}")
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="老化档位")

    # y 轴视野：自动留白，避免线贴边
    ys = []
    for lab in show_labels:
        med, lo, hi, _ns = series[lab]
        for arr in (med, lo, hi):
            xs = arr[np.isfinite(arr)]
            ys.extend(xs.tolist())
    if ys:
        y_min = float(min(ys))
        y_max = float(max(ys))
        ax.set_ylim(min(-0.4, y_min - 0.35), max(0.25, y_max + 0.25))

    if style.annotate:
        # 读者最关心“α=1 时误差有多大、方向如何”，因此在学习版给一个简洁数字摘要。
        def _fmt(lab: str, a: float) -> str:
            xs = data.get((lab, float(a)), [])
            xs = [x for x in xs if np.isfinite(x)]
            if not xs:
                return f"{_label_zh(lab)}：无数据"
            return (
                f"{_label_zh(lab)}：中位数≈{np.percentile(xs,50):+.2f}%，"
                f"IQR≈[{np.percentile(xs,25):+.2f}%, {np.percentile(xs,75):+.2f}%]，"
                f"n={len(xs)}"
            )

        a1 = max(alphas)
        lines = [_fmt(lab, a1) for lab in show_labels]
        fig.tight_layout(rect=(0.0, 0.28, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：保持平均功耗 P̄ 不变，只改变功耗时间结构的波动强度（α）。\n"
            "- α=0：等价于“均值常功耗”假设；α=1：等价于“真实波动轨迹”。\n"
            "- 若 ΔTTE<0：说明波动会缩短续航（机理上常见于欠压截止 + I^2R 损耗非线性）。\n"
            "- 阴影为跨轨迹的 25%~75% 分位区间（IQR），实线为中位数。\n"
            + "；".join(lines),
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3 SmartphoneMeasurements 实验出图（paper/study）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_plots"), help="输出目录（会创建 q3/paper 与 q3/study）")
    ap.add_argument(
        "--reports-dir",
        default=str(SRC_DIR / "out_reports" / "q3" / "observed_smartphone_measurements"),
        help="输入报表目录（默认 out_reports/q3/observed_smartphone_measurements）",
    )
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    csv_path = reports_dir / "trace_vs_mean.csv"
    sweep_path = reports_dir / "fluctuation_sweep.csv"
    trace_dir = reports_dir / "traces"
    if not csv_path.exists():
        raise FileNotFoundError("缺少 trace_vs_mean.csv：请先运行 run_q3_smartphone_measurements_experiment.py")
    if not sweep_path.exists():
        raise FileNotFoundError("缺少 fluctuation_sweep.csv：请先运行 run_q3_smartphone_measurements_sweep_experiment.py")
    if not trace_dir.exists():
        raise FileNotFoundError("缺少 traces/：请先运行 run_q3_smartphone_measurements_experiment.py")

    rows = _read_csv(csv_path)
    rows_sweep = _read_csv(sweep_path)
    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_dir = ensure_dir(Path(args.out_dir) / "q3" / str(m) / "observed_smartphone_measurements")

        fig = _fig_power_traces(trace_dir, rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "01_power_traces.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        import matplotlib.pyplot as plt

        plt.close(fig)

        fig = _fig_tte_trace_vs_mean(rows, mode=m)  # type: ignore[arg-type]
        p = out_dir / "02_tte_trace_vs_mean.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)

        fig = _fig_fluctuation_sweep(rows_sweep, mode=m)  # type: ignore[arg-type]
        p = out_dir / "03_fluctuation_sweep.png"
        savefig(fig, p, mode=m)  # type: ignore[arg-type]
        plt.close(fig)

        print(f"[{m}] generated 3 figures -> {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
