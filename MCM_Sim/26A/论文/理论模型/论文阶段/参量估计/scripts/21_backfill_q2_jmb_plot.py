#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于“参量估计”的 Wi-Fi 每 MB 能耗（e_per_mb）结果，对 Q2 的观测图（SmartphoneMeasurements：J/MB）做 back_ 版本补充。

目的（论文口径）：
- SmartphoneMeasurements 给出的 e=ΔP/吞吐（J/MB）来自 Monsoon 的“整机功耗增量”，通常包含 CPU/协议栈/系统调度/尾态等开销；
- AndroWatts 聚合表反推的 e_per_mb 更接近 radio rails 的量级约束（更像网络模块的下界/基准项）；
- 因此两者不必完全一致：我们把参量估计线画在观测分布上，作为“可解释的先验/量级锚定”。

输出（不覆盖原产物）：
- Q2材料/08/.../back_figure.png（paper 版）
- Q2材料/08/.../other/back_figure_study.png（study 版）
- Q2材料/08/.../other/back_data.csv（与 back_ 图一致的筛选数据快照）
- Q2材料/08/.../other/back_about.md（来源与复现方式）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _repo_root() -> Path:
    # 当前文件在：
    # MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/<this_file>
    # parents[7] 回到项目根目录（包含 MCM_Sim/ 这一层）
    return Path(__file__).resolve().parents[7]


def _read_param_estimates(repo_root: Path) -> dict[str, float]:
    """读取本项目“参量估计”目录下的 e_per_mb（两种口径）。"""

    param_dir = repo_root / "MCM_Sim" / "26A" / "论文" / "理论模型" / "论文阶段" / "参量估计"

    # 口径 A：能量守恒（含尾态能量项）-> e_per_mb
    p_tail = param_dir / "03-网络回落曲线" / "fit_results.csv"
    df_tail = pd.read_csv(p_tail)
    e_tail = float(df_tail.loc[0, "e_per_mb_J"])

    # 口径 B：功率回归（P_radio vs throughput）-> e_per_mb
    p_thr = param_dir / "04-吞吐-功耗关系" / "fit_results.csv"
    df_thr = pd.read_csv(p_thr)
    e_thr = float(df_thr.loc[0, "e_per_mb_J"])

    return {"e_per_mb_energy_balance_J_per_MB": e_tail, "e_per_mb_throughput_reg_J_per_MB": e_thr}


def _plot(df: pd.DataFrame, *, e_tail: float, e_thr: float, out_png: Path, annotate: bool) -> None:
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    # 中文字体回退（macOS 通常有 PingFang SC）
    mpl.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Songti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    mpl.rcParams["axes.unicode_minus"] = False

    # 用户给定配色（最多 4）
    C_PURPLE = "#845ec2"
    C_TEAL = "#00c2a8"
    C_DARK = "#008b74"
    C_CYAN = "#4ffbdf"

    # 仅保留我们关心的两类链路
    df = df.copy()
    df = df[df["link"].isin(["router", "direct"])].copy()
    df["energy_per_mb_j"] = pd.to_numeric(df["energy_per_mb_j"], errors="coerce")
    df = df[np.isfinite(df["energy_per_mb_j"]) & (df["energy_per_mb_j"] > 0)].copy()

    router = df[df["link"] == "router"]["energy_per_mb_j"].to_numpy(dtype=float)
    direct = df[df["link"] == "direct"]["energy_per_mb_j"].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=200)

    # log y：让“低值段”可读，同时不被长尾压扁（paper 更清晰）
    ax.set_yscale("log")

    data = [direct, router]
    labels = ["Wi-Fi Direct", "Wi-Fi（路由器）"]

    # matplotlib>=3.9: labels->tick_labels；为兼容旧版本做 try/except
    try:
        bp = ax.boxplot(
            data,
            tick_labels=labels,
            showfliers=False,
            widths=0.55,
            patch_artist=True,
            medianprops={"color": "white", "linewidth": 1.6},
            boxprops={"linewidth": 1.2},
            whiskerprops={"linewidth": 1.0},
            capprops={"linewidth": 1.0},
        )
    except TypeError:
        bp = ax.boxplot(
            data,
            labels=labels,
            showfliers=False,
            widths=0.55,
            patch_artist=True,
            medianprops={"color": "white", "linewidth": 1.6},
            boxprops={"linewidth": 1.2},
            whiskerprops={"linewidth": 1.0},
            capprops={"linewidth": 1.0},
        )

    # 着色：direct=紫，router=绿
    colors = [C_PURPLE, C_TEAL]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.88)
        patch.set_edgecolor("#333333")

    ax.grid(True, which="both", axis="y", alpha=0.22)
    ax.set_ylabel("单位数据能耗（J/MB，对数刻度）")
    ax.set_title("通信观测：单位数据能耗分布与参量估计对照" + ("（study）" if annotate else ""))

    # 参量估计对照线（两种口径）
    ax.axhline(e_tail, color=C_DARK, linestyle="--", linewidth=1.4, label="参量估计：能量守恒  e={:.3f} J/MB".format(e_tail))
    ax.axhline(e_thr, color=C_CYAN, linestyle="--", linewidth=1.4, label="参量估计：功率回归  e={:.3f} J/MB".format(e_thr))
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)

    if annotate:
        def _q(x: np.ndarray) -> tuple[float, float, float]:
            x = x[np.isfinite(x) & (x > 0)]
            if x.size == 0:
                return (float("nan"), float("nan"), float("nan"))
            return (float(np.quantile(x, 0.05)), float(np.quantile(x, 0.50)), float(np.quantile(x, 0.95)))

        d05, d50, d95 = _q(direct)
        r05, r50, r95 = _q(router)
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：SmartphoneMeasurements 的 e=ΔP/吞吐（J/MB）来自 Monsoon 的整机功耗增量，"
            "因此可能高于 AndroWatts（radio rails）反推出的 e_per_mb。\n"
            "Direct：P05={:.3f}, P50={:.3f}, P95={:.3f}；Router：P05={:.3f}, P50={:.3f}, P95={:.3f}。\n"
            "写作建议：把参量估计线作为“网络模块能耗的量级约束/下界”，并用尾态与交互项解释观测长尾。".format(d05, d50, d95, r05, r50, r95),
            ha="left",
            va="bottom",
            fontsize=8.6,
        )
    else:
        fig.tight_layout()

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    repo_root = _repo_root()
    q2_dir = repo_root / "MCM_Sim" / "26A" / "论文" / "理论模型" / "论文阶段" / "Q2材料" / "08-Q2-观测对照_通信单位能耗JMB"

    # Q2 图 08 的数据版本（材料目录中已保留，便于二次绘图）
    data_csv = q2_dir / "other" / "data.csv"
    df = pd.read_csv(data_csv)

    est = _read_param_estimates(repo_root)
    e_tail = float(est["e_per_mb_energy_balance_J_per_MB"])
    e_thr = float(est["e_per_mb_throughput_reg_J_per_MB"])

    # 输出：不覆盖原 figure.png
    _plot(df, e_tail=e_tail, e_thr=e_thr, out_png=q2_dir / "back_figure.png", annotate=False)
    _plot(df, e_tail=e_tail, e_thr=e_thr, out_png=q2_dir / "other" / "back_figure_study.png", annotate=True)

    # 数据快照（与 back_ 图一致的筛选口径）
    out_data = q2_dir / "other" / "back_data.csv"
    df2 = df[df["link"].isin(["router", "direct"])].copy()
    df2["energy_per_mb_j"] = pd.to_numeric(df2["energy_per_mb_j"], errors="coerce")
    df2 = df2[np.isfinite(df2["energy_per_mb_j"]) & (df2["energy_per_mb_j"] > 0)].copy()
    out_data.parent.mkdir(parents=True, exist_ok=True)
    df2.to_csv(out_data, index=False, encoding="utf-8")

    # back_ 说明
    about = q2_dir / "other" / "back_about.md"
    about.write_text(
        (
            "# back_ 版本说明：参量估计 vs SmartphoneMeasurements（单位数据能耗 J/MB）\n\n"
            "本 back_ 版本把参量估计得到的 Wi-Fi `e_per_mb`（J/MB）画成对照线，叠加到 SmartphoneMeasurements 的观测分布上，\n"
            "用于论文中说明：我们对网络能耗的量级采用“可引用的公开数据”做锚定，而观测长尾可由尾态/交互等机制解释。\n\n"
            "## 对应文件\n\n"
            "- `../back_figure.png`：paper 版（简洁）\n"
            "- `back_figure_study.png`：study 版（含解释）\n"
            "- `back_data.csv`：用于 back_ 图的数据快照（Direct/Router 且 e>0）\n\n"
            "## 参量估计对照线来源\n\n"
            "- 能量守恒（含尾态能量项）：e={:.6f} J/MB，见 `论文/理论模型/论文阶段/参量估计/03-网络回落曲线/fit_results.csv`\n"
            "- 功率回归（P_radio vs 吞吐）：e={:.6f} J/MB，见 `论文/理论模型/论文阶段/参量估计/04-吞吐-功耗关系/fit_results.csv`\n\n"
            "## 重要口径说明（避免误解）\n\n"
            "- SmartphoneMeasurements 的 e=ΔP/吞吐来自 Monsoon 的“整机功耗增量”，可能包含 CPU/协议栈/系统调度/尾态等开销；\n"
            "- AndroWatts 的参量估计更接近 radio rails 的量级约束（更像网络模块的下界/基准项）；\n"
            "- 因此两者不必数值完全一致：若观测显著更大，合理解释是“网络活动触发的系统协同开销 + 尾态”。\n"
        ).format(e_tail, e_thr),
        encoding="utf-8",
    )

    print("wrote ->", q2_dir / "back_figure.png")
    print("wrote ->", q2_dir / "other" / "back_figure_study.png")
    print("wrote ->", out_data)
    print("wrote ->", about)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

