#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用“参量估计”结果回填（补强）Q3 的“先验来源表”，生成 back_ 版本（不覆盖原产物）。

为什么要做：
- Q3 的敏感性/不确定性结论高度依赖“先验区间/默认值”；仅写“工程先验”容易被质疑。
- 我们已经从公开数据（AndroWatts 聚合表）做了参量估计：亮度-屏幕功耗、负载-CPU/GPU功耗、网络尾态/吞吐能耗、温升-热模型量级。
- 这里把这些“可复现的点估计+来源”写进 Q3 的先验表，作为可引用证据（同时不破坏原表结构）。

输出（带 back_ 前缀）：
- `MCM_Sim/26A/论文/理论模型/论文阶段/Q3材料/12-先验来源表-参数区间与来源/back_figure.png`
- `.../other/back_data.csv`
- `.../other/back_table_zh.md`
- `.../other/back_about.md`
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


def _repo_root() -> Path:
    # 当前文件在：
    # MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/<this_file>
    return Path(__file__).resolve().parents[7]


def _render_table_png(csv_path: Path, png_path: Path) -> None:
    """把 data.csv 渲染成一张可插入论文的表格图（中文 + 自动换行）。"""

    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import textwrap

    df = pd.read_csv(csv_path)
    keep_cols = ["参数", "含义", "先验(默认)", "数据锚定/来源"]
    df = df[keep_cols]

    wrap_width = {"参数": 18, "含义": 24, "先验(默认)": 20, "数据锚定/来源": 40}
    wrapped = df.copy()
    for c in wrapped.columns:
        w = int(wrap_width.get(c, 24))
        wrapped[c] = wrapped[c].map(lambda x: textwrap.fill("" if x is None else str(x), width=w, break_long_words=False))

    mpl.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Songti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    mpl.rcParams["axes.unicode_minus"] = False

    nrows = int(len(wrapped))
    line_counts = []
    for _, r in wrapped.iterrows():
        line_counts.append(max(str(r[c]).count("\n") + 1 for c in wrapped.columns))
    total_lines = sum(line_counts) + 2
    fig_h = max(6.5, 0.22 * float(total_lines))
    fig_w = 14.5

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    ax.axis("off")
    ax.set_title("表 Q3-12(back)  先验参数区间与来源（加入参量估计锚定）", fontsize=12, pad=12)

    cell_text = wrapped.values.tolist()
    col_labels = wrapped.columns.tolist()
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellLoc="left",
        colLoc="left",
        loc="upper left",
        bbox=[0.0, 0.0, 1.0, 0.95],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.2)

    for (r, _c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#f0f0f0")
            cell.set_text_props(weight="bold")
        cell.set_edgecolor("#cccccc")

    base_h = 0.95 / float(max(1, nrows + 1))
    for ridx in range(1, nrows + 1):
        n_lines = int(line_counts[ridx - 1])
        h = base_h * float(n_lines)
        for cidx in range(len(col_labels)):
            table[(ridx, cidx)].set_height(h)

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _to_md_table(df: pd.DataFrame) -> str:
    cols = df.columns.tolist()

    def esc(x: object) -> str:
        s = "" if x is None else str(x)
        s = s.replace("|", "\\|").replace("\n", "<br>")
        return s

    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(esc(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    repo = _repo_root()
    q3_dir = repo / "MCM_Sim" / "26A" / "论文" / "理论模型" / "论文阶段" / "Q3材料" / "12-先验来源表-参数区间与来源"
    q3_other = q3_dir / "other"

    # 原表（当前项目口径）
    base_csv = q3_other / "data.csv"
    df_base = pd.read_csv(base_csv)

    # 参量估计汇总（点估计+来源）
    est_csv = repo / "MCM_Sim" / "26A" / "论文" / "理论模型" / "论文阶段" / "参量估计" / "参数估计汇总表.csv"
    est = pd.read_csv(est_csv)
    est_map = {str(r["parameter_key"]): r for _, r in est.iterrows()}

    def get(key: str) -> float:
        v = est_map.get(key, {}).get("value", float("nan"))
        return float(v)

    # 取核心结果（用于 Q2/Q3 的功耗-电池耦合）
    P0 = get("power.screen.P0_W")
    k_screen = get("power.screen.k_W_per_nit")
    k_cpu = get("power.cpu.k_W")
    k_gpu = get("power.gpu.k_W")
    e_wifi = get("power.rrc.e_per_mb_J (wifi)")
    tau_tail = get("power.rrc.tau_tail_s (wifi)")
    R_th = get("battery.thermal.R_th_K_per_W")
    C_th = get("battery.thermal.C_th_J_per_K")

    # 生成“back_ 增补行”：保持列结构一致，尽量写成可直接引用的中文。
    # 先验范围这里给“保守区间”（量级 + 可解释），避免把回归点估计当作真值。
    add_rows = [
        {
            "参数": "P0_screen",
            "含义": "屏幕点亮基准功耗（W）",
            "先验(默认)": "logU[{:.3f}, {:.3f}]".format(0.7 * P0, 1.3 * P0),
            "先验(tight)": "logU[{:.3f}, {:.3f}]".format(0.9 * P0, 1.1 * P0),
            "数据锚定/来源": "参量估计（AndroWatts 聚合表）：P0≈{:.3f}W。用于屏幕亮度模型的截距项。".format(P0),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/01-亮度-屏幕功耗/fit_results.csv（来自 AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "k_screen",
            "含义": "亮度→功耗线性系数（W/nit）",
            "先验(默认)": "logU[{:.2e}, {:.2e}]".format(0.7 * k_screen, 1.3 * k_screen),
            "先验(tight)": "logU[{:.2e}, {:.2e}]".format(0.9 * k_screen, 1.1 * k_screen),
            "数据锚定/来源": "参量估计（AndroWatts 聚合表）：k≈{:.2e} W/nit（Brightness->nits 映射见参量估计说明）。".format(k_screen),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/01-亮度-屏幕功耗/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "k_cpu",
            "含义": "CPU 负载功耗系数（P=k·load，W）",
            "先验(默认)": "logU[{:.2f}, {:.2f}]".format(0.6 * k_cpu, 1.4 * k_cpu),
            "先验(tight)": "logU[{:.2f}, {:.2f}]".format(0.9 * k_cpu, 1.1 * k_cpu),
            "数据锚定/来源": "参量估计（AndroWatts 聚合表）：k_cpu≈{:.2f}W（通过 freq proxy 归一化负载回归）。".format(k_cpu),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/02-负载-CPU_GPU功耗/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "k_gpu",
            "含义": "GPU 负载功耗系数（P=k·load，W）",
            "先验(默认)": "logU[{:.2f}, {:.2f}]".format(0.6 * k_gpu, 1.4 * k_gpu),
            "先验(tight)": "logU[{:.2f}, {:.2f}]".format(0.9 * k_gpu, 1.1 * k_gpu),
            "数据锚定/来源": "参量估计（AndroWatts 聚合表）：k_gpu≈{:.3f}W（通过 GPU freq proxy 归一化负载回归）。".format(k_gpu),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/02-负载-CPU_GPU功耗/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "e_wifi",
            "含义": "Wi-Fi 每 MB 传输能耗（J/MB）",
            "先验(默认)": "logU[{:.3f}, {:.3f}]".format(0.6 * e_wifi, 1.6 * e_wifi),
            "先验(tight)": "logU[{:.3f}, {:.3f}]".format(0.9 * e_wifi, 1.1 * e_wifi),
            "数据锚定/来源": "参量估计（AndroWatts）：e≈{:.3f} J/MB（能量守恒反推，含尾态能量项）。".format(e_wifi),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/03-网络回落曲线/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "tau_tail_wifi",
            "含义": "Wi-Fi 尾态等效时间常数 τ_tail（s）",
            "先验(默认)": "logU[{:.1f}, {:.1f}]".format(0.7 * tau_tail, 1.3 * tau_tail),
            "先验(tight)": "logU[{:.1f}, {:.1f}]".format(0.9 * tau_tail, 1.1 * tau_tail),
            "数据锚定/来源": "参量估计（AndroWatts）：τ≈{:.1f}s（定义：τ=E_tail/(P_conn-P_idle)，用于解释拖尾）。".format(tau_tail),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/03-网络回落曲线/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "R_th",
            "含义": "热阻 R_th（K/W）",
            "先验(默认)": "logU[{:.3f}, {:.3f}]".format(0.7 * R_th, 1.3 * R_th),
            "先验(tight)": "logU[{:.3f}, {:.3f}]".format(0.9 * R_th, 1.1 * R_th),
            "数据锚定/来源": "参量估计（AndroWatts 温升统计量反推）：R_th≈{:.3f} K/W（用于集总热模型量级）。".format(R_th),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/05-温度-时间曲线/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
        {
            "参数": "C_th",
            "含义": "热容 C_th（J/K）",
            "先验(默认)": "logU[{:.2f}, {:.2f}]".format(0.7 * C_th, 1.3 * C_th),
            "先验(tight)": "logU[{:.2f}, {:.2f}]".format(0.9 * C_th, 1.1 * C_th),
            "数据锚定/来源": "参量估计（AndroWatts 温升统计量反推）：C_th≈{:.2f} J/K（由 τ=R_th*C_th 得到）。".format(C_th),
            "来源文件/许可": "论文/理论模型/论文阶段/参量估计/05-温度-时间曲线/fit_results.csv（AndroWatts，CC BY 4.0）",
        },
    ]

    # 合成 back_ 表：原表 + 增补行
    df_add = pd.DataFrame(add_rows)
    df_out = pd.concat([df_base, df_add], ignore_index=True)

    out_csv = q3_other / "back_data.csv"
    df_out.to_csv(out_csv, index=False, encoding="utf-8")

    out_md = q3_other / "back_table_zh.md"
    out_md.write_text(_to_md_table(df_out), encoding="utf-8")

    out_png = q3_dir / "back_figure.png"
    _render_table_png(out_csv, out_png)

    about = q3_other / "back_about.md"
    about.write_text(
        "# back_ 版本说明：Q3 先验来源表（加入参量估计锚定）\n\n"
        "本 back_ 版本在原“先验来源表”的基础上，增补了若干可直接回填到功耗/热模型的物理量级参数（点估计 + 可追溯来源）。\n"
        "目的不是把回归结果当作真值，而是把敏感性分析的先验范围建立在可引用的公开数据锚定之上。\n\n"
        "## 生成位置\n\n"
        "- `../back_figure.png`：论文可插图（表格图）\n"
        "- `back_data.csv`：表格数据版本（含增补行）\n"
        "- `back_table_zh.md`：同表的 Markdown 版本\n\n"
        "## 参量估计来源（点估计）\n\n"
        "- 亮度-屏幕功耗：`论文/理论模型/论文阶段/参量估计/01-亮度-屏幕功耗/fit_results.csv`\n"
        "- 负载-CPU/GPU功耗：`论文/理论模型/论文阶段/参量估计/02-负载-CPU_GPU功耗/fit_results.csv`\n"
        "- 网络尾态/单位数据能耗：`论文/理论模型/论文阶段/参量估计/03-网络回落曲线/fit_results.csv`\n"
        "- 温升-热模型量级：`论文/理论模型/论文阶段/参量估计/05-温度-时间曲线/fit_results.csv`\n\n"
        "注：增补行的先验范围使用“保守倍数区间”（例如 ±30% 或 ±60%），用于敏感性/不确定性传播；\n"
        "tight 先验仅用于 sanity check（验证结论方向是否稳定）。\n",
        encoding="utf-8",
    )

    print("wrote ->", out_png)
    print("wrote ->", out_csv)
    print("wrote ->", out_md)
    print("wrote ->", about)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

