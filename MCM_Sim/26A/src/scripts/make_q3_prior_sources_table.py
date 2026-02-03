#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：先验来源表（可引用）——导出 CSV + 生成论文插图。

目的（对齐赛题 Q3）：
- Q3 的敏感性/不确定性分析强依赖“先验区间”；若不说明来源，结论会被质疑“主观拍脑袋”。
- 本脚本把当前实现中用到的关键先验区间整理成表，并用项目内 **公开数据集** 做量级锚定（能引用）。

输出：
- `MCM_Sim/26A/论文/理论模型/论文阶段/Q3材料/12-先验来源表-参数区间与来源/other/data.csv`
- `.../figure.png`（论文可直接插入的表格图）

注：表格“tight 先验”仅用于 sanity check（方向验证），不代表唯一正确范围。
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


# 目录定位：
# .../<project_root>/MCM_Sim/26A/src/scripts/<this_file>
REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "src"
DATA_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "data"
Q3_MATERIAL_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "论文" / "理论模型" / "论文阶段" / "Q3材料"
OUT_DIR = Q3_MATERIAL_DIR / "12-先验来源表-参数区间与来源"
OUT_OTHER = OUT_DIR / "other"


def _q(arr: np.ndarray, qs=(0.05, 0.5, 0.95)) -> tuple[float, float, float]:
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    q05, q50, q95 = np.quantile(arr, list(qs))
    return (float(q05), float(q50), float(q95))


def _ratio_to_median(q05: float, q50: float, q95: float) -> tuple[float, float]:
    if not np.isfinite(q50) or q50 == 0:
        return (float("nan"), float("nan"))
    return (float(q05 / q50), float(q95 / q50))


def _load_androwatts_component_share() -> dict[str, dict[str, float]]:
    """从 AndroWatts 聚合表中提取“部件能耗占比”的分位数（用于锚定 scale 的量级）。

注意：
- 这里用的是“能耗占比”的统计，而不是绝对功耗（因为字段单位在不同版本中可能不一致）。
- 占比的分布能稳健反映“同类手机应用下，CPU/屏幕/无线等相对贡献的典型波动范围”。
"""

    p = DATA_DIR / "open_data" / "material" / "res_test" / "aggregated.csv"
    df = pd.read_csv(p)

    # 映射：模型的“功耗链条/部件” -> AndroWatts 中可对齐的能耗项（单位不统一不影响占比）
    cols = {
        "screen": ["Display_ENERGY_UW"],
        "cpu": ["CPU_BIG_ENERGY_UW", "CPU_MID_ENERGY_UW", "CPU_LITTLE_ENERGY_UW"],
        "gpu": ["GPU_ENERGY_UW", "GPU3D_ENERGY_UW"],
        "gps": ["GPS_ENERGY_UW"],
        "wifi": ["WLANBT_ENERGY_UW"],
        "cellular": ["CELLULAR_ENERGY_UW"],
        "infrastructure": ["INFRASTRUCTURE_ENERGY_UW"],
    }

    comp = {}
    for k, cs in cols.items():
        x = None
        for c in cs:
            v = pd.to_numeric(df[c], errors="coerce")
            x = v if x is None else x + v
        comp[k] = x
    comp_df = pd.DataFrame(comp).replace([np.inf, -np.inf], np.nan).dropna()
    comp_df["total"] = comp_df[list(cols.keys())].sum(axis=1)
    comp_df = comp_df[comp_df["total"] > 0]

    shares = comp_df[list(cols.keys())].div(comp_df["total"], axis=0)
    out: dict[str, dict[str, float]] = {}
    for k in cols.keys():
        q05, q50, q95 = _q(shares[k].to_numpy())
        r_lo, r_hi = _ratio_to_median(q05, q50, q95)
        out[k] = {
            "share_q05": q05,
            "share_q50": q50,
            "share_q95": q95,
            "share_ratio_lo": r_lo,
            "share_ratio_hi": r_hi,
            "n": float(len(shares)),
        }
    return out


def _load_battery_state_soh_quantiles() -> dict[str, float]:
    p = DATA_DIR / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"
    df = pd.read_csv(p)
    soh = pd.to_numeric(df["SOH"], errors="coerce").dropna().to_numpy()
    q05, q50, q95 = _q(soh)
    return {"soh_q05": q05, "soh_q50": q50, "soh_q95": q95, "n": float(len(soh))}


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


def _render_table_png(csv_path: Path, png_path: Path) -> None:
    """把 data.csv 渲染成一张可插入论文的表格图。"""

    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import textwrap

    df = pd.read_csv(csv_path)
    # 论文版：尽量紧凑，只保留关键列（否则太宽）
    keep_cols = ["参数", "含义", "先验(默认)", "数据锚定/来源"]
    df = df[keep_cols]

    # 对长文本做自动换行（否则 table cell 会被截断，论文不可读）
    wrap_width = {
        "参数": 18,
        "含义": 24,
        "先验(默认)": 18,
        "数据锚定/来源": 36,
    }
    wrapped = df.copy()
    for c in wrapped.columns:
        w = int(wrap_width.get(c, 24))
        wrapped[c] = wrapped[c].map(lambda x: textwrap.fill("" if x is None else str(x), width=w, break_long_words=False))

    # 简单的中文字体回退（macOS 通常有 PingFang SC）
    mpl.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Songti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    mpl.rcParams["axes.unicode_minus"] = False

    # 依据换行后的“总行数”动态定尺寸：避免文字过密。
    nrows = int(len(wrapped))
    # 每行的“行高”与该行最大换行数相关
    line_counts = []
    for _, r in wrapped.iterrows():
        line_counts.append(max(str(r[c]).count("\n") + 1 for c in wrapped.columns))
    total_lines = sum(line_counts) + 2  # +表头与留白
    fig_h = max(6.5, 0.22 * total_lines)
    fig_w = 14.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    ax.axis("off")
    ax.set_title("表 Q3-12  先验参数区间与来源（用于敏感性/不确定性分析）", fontsize=12, pad=12)

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

    # 让表头更醒目
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#f0f0f0")
            cell.set_text_props(weight="bold")
        cell.set_edgecolor("#cccccc")

    # 依据每行换行数调高度（保证多行文本不重叠）
    base_h = 0.95 / float(max(1, nrows + 1))
    for ridx in range(1, nrows + 1):
        # table 的 row index 从 0=header, 1..nrows=数据行
        n_lines = int(line_counts[ridx - 1])
        h = base_h * float(n_lines)
        for cidx in range(len(col_labels)):
            table[(ridx, cidx)].set_height(h)

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUT_OTHER.mkdir(parents=True, exist_ok=True)

    aw = _load_androwatts_component_share()
    soh = _load_battery_state_soh_quantiles()

    # 组织表格：尽量“可引用 + 可解释”
    rows: list[dict[str, str]] = []

    def add(
        name: str,
        meaning: str,
        prior_default: str,
        prior_tight: str,
        anchor: str,
        source: str,
    ) -> None:
        rows.append(
            {
                "参数": name,
                "含义": meaning,
                "先验(默认)": prior_default,
                "先验(tight)": prior_tight,
                "数据锚定/来源": anchor,
                "来源文件/许可": source,
            }
        )

    # battery
    add(
        "batt_capacity_scale",
        "容量缩放（制造/机型差异+标定误差）",
        "logU[0.90, 1.10]",
        "logU[0.97, 1.03]",
        "工程先验：以手机电池标称容量±10% 覆盖机型/批次差异；老化主效应由 SOH 单独描述。",
        "（工程先验；可在论文中补充任一公开电池规格书作为引用）",
    )
    add(
        "batt_r0_scale",
        "欧姆内阻 R0 缩放（端电压下陷关键驱动）",
        "logU[0.80, 1.30]",
        "logU[0.95, 1.05]",
        "工程先验：覆盖温度/批次/老化导致的直流内阻变化；老化主效应由 (SOH, α_R) 共同调制。",
        "（工程先验；可用公开 ECM 参数辨识论文/数据集补强）",
    )
    add(
        "batt_r1_scale",
        "极化支路 R1 缩放（动态恢复/尖峰后回升形状）",
        "logU[0.80, 1.30]",
        "logU[0.95, 1.05]",
        "工程先验：同 R0，允许不同手机/不同工况下的极化强度变化。",
        "（工程先验；可用公开 ECM 参数辨识论文/数据集补强）",
    )
    add(
        "v_cut_V",
        "欠压截止阈值（设备级关机阈值，单位 V）",
        "U[3.2, 3.4]",
        "U[3.27, 3.33]",
        "工程先验：智能手机通常会在 3.2~3.4V 附近触发欠压/关机保护（比电芯最低电压更保守）。",
        "（工程先验；建议在论文中补充公开电源管理/电池保护文档引用）",
    )
    add(
        "soc_min",
        "最小 SOC（保护性下限）",
        "{0, 0.03, 0.05, 0.10}",
        "{0.03, 0.05}",
        "工程先验：不同设备对“0% 电量”的标定不同，通常保留 3%~10% 的保护余量。",
        "（工程先验）",
    )
    add(
        "soh",
        "健康度 SOH（容量保持率，慢变量）",
        "U[0.70, 1.00]",
        "U[0.90, 1.00]",
        f"公开电池状态表（n={int(soh['n'])}）SOH 分位数：P05={soh['soh_q05']:.3f}, P50={soh['soh_q50']:.3f}, P95={soh['soh_q95']:.3f}。默认先验覆盖中度老化到新电池。",
        "data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv（开源数据；许可见同目录说明）",
    )
    add(
        "alpha_r",
        "老化增阻强度 α_R（SOH→R0 增长映射系数，慢变量）",
        "logU[0.1, 3.0]",
        "logU[0.5, 1.5]",
        "工程先验：用于覆盖“温和/中等/激进”增阻情形；tight 仅用于 sanity check（先验收窄应降低参数方差占比）。",
        "（工程先验；可后续用 CALCE/NASA 等公开老化数据拟合收窄）",
    )

    # power chain
    add(
        "eta_pmic",
        "电源管理链效率 η_PMIC（电池端→负载端）",
        "U[0.90, 0.95]",
        "U[0.92, 0.95]",
        "工程先验：典型 DC-DC/PMIC 在中等负载效率约 90%~95%。",
        "（工程先验；建议补充任一公开 PMIC 数据手册引用）",
    )

    # component power scaling (anchored by AndroWatts shares)
    def aw_anchor(key: str, note: str = "") -> str:
        a = aw[key]
        return (
            f"AndroWatts( n={int(a['n'])} ) 部件能耗占比分位数："
            f"P05={a['share_q05']:.3f}, P50={a['share_q50']:.3f}, P95={a['share_q95']:.3f}；"
            f"相对中位数约 {a['share_ratio_lo']:.2f}~{a['share_ratio_hi']:.2f}。"
            + (f" {note}" if note else "")
        )

    add(
        "base_scale",
        "基础功耗缩放（系统常开 + 轻载）",
        "logU[0.70, 1.30]",
        "logU[0.90, 1.10]",
        aw_anchor("infrastructure", "用于锚定“系统基础+基础设施”量级。"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "screen_scale",
        "屏幕功耗缩放（亮度模型之外的设备差异）",
        "logU[0.70, 1.30]",
        "logU[0.90, 1.10]",
        aw_anchor("screen", "屏幕占比本身受亮度/使用强影响；我们把主要可变性放在 brightness 与场景输入，scale 保持较窄。"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "cpu_scale",
        "CPU 功耗缩放（同类任务/同场景下的软硬件效率差异）",
        "logU[0.60, 1.40]",
        "logU[0.90, 1.10]",
        aw_anchor("cpu"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "gpu_scale",
        "GPU 功耗缩放（图形负载差异）",
        "logU[0.60, 1.40]",
        "logU[0.90, 1.10]",
        aw_anchor("gpu"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "gps_scale",
        "GPS 功耗缩放（定位模块差异）",
        "logU[0.70, 1.30]",
        "logU[0.90, 1.10]",
        "AndroWatts 中 GPS 占比普遍极小（接近 0），不足以提供稳定锚定；此处采用工程先验。",
        "（工程先验；可后续补充公开定位功耗测量研究）",
    )
    add(
        "background_base_scale",
        "后台基线功耗缩放（常驻服务/系统维护）",
        "logU[0.70, 1.30]",
        "logU[0.90, 1.10]",
        aw_anchor("infrastructure", "与 base_scale 同源锚定：后台与基础设施能耗同属“常驻+轻载”类别。"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )

    # radio
    add(
        "rrc_state_scale",
        "无线状态机功耗缩放（IDLE/CONNECTED/TAIL 的状态功耗）",
        "logU[0.60, 1.60]",
        "logU[0.90, 1.10]",
        aw_anchor("wifi", "无线项在不同应用/网络环境下差异较大；该 scale 用于吸收机型/环境不确定性。"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "rrc_data_scale",
        "无线数据能耗缩放（每 MB 能耗）",
        "logU[0.60, 1.60]",
        "logU[0.90, 1.10]",
        aw_anchor("cellular", "蜂窝网络占比虽小但波动明显；用于锚定数据传输相关不确定性量级。"),
        "data/open_data/material/res_test/aggregated.csv（AndroWatts，CC BY 4.0）",
    )
    add(
        "rrc_tail_scale",
        "尾态时长缩放（TAIL 持续时间不确定性）",
        "logU[0.70, 1.30]",
        "logU[0.90, 1.10]",
        "工程先验：不同系统/网络协议的 tail timer 存在差异；在缺乏一致公开标定数据时用 ±30% 覆盖。",
        "（工程先验；可后续补充公开 RRC tail 测量研究）",
    )
    add(
        "poor_signal_psi_scale",
        "弱信号惩罚缩放（poor vs good 信号能耗倍率）",
        "logU[0.90, 1.30]",
        "logU[0.95, 1.05]",
        "工程先验：弱信号通常提高发射功率并增加重传；在无设备特定测量时用温和倍率区间覆盖。",
        "（工程先验）",
    )

    # stochastic + interaction
    add(
        "bg_lambda_scale",
        "后台唤醒频率缩放（Poisson 到达率）",
        "logU[0.50, 2.00]",
        "logU[0.80, 1.25]",
        "工程先验：后台任务频率跨用户/应用差异很大；用倍数先验覆盖“安静/中等/嘈杂”系统。",
        "（工程先验；可后续用真实日志/测量数据定界）",
    )
    add(
        "interaction_scale",
        "交互项缩放（屏幕×网络×高 CPU 的协同功耗）",
        "U[0.00, 1.60]",
        "U[0.00, 1.00]",
        "工程先验：用于吸收“单项功耗叠加≠真实总功耗”的二阶效应（例如高负载导致额外损耗/调度开销）。",
        "（工程先验；可后续通过实测功耗回归标定）",
    )

    csv_path = OUT_OTHER / "data.csv"
    _write_csv(csv_path, rows)
    _render_table_png(csv_path, OUT_DIR / "figure.png")

    # 额外：写一个 markdown 表（便于直接复制进论文或做二次排版）
    md_path = OUT_OTHER / "table_zh.md"
    df_out = pd.read_csv(csv_path)
    # 避免依赖 pandas 的可选依赖 tabulate：这里手写一个简单的 Markdown 表生成器。
    cols = df_out.columns.tolist()
    def _esc(x: object) -> str:
        s = "" if x is None else str(x)
        s = s.replace("|", "\\|").replace("\n", "<br>")
        return s

    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, r in df_out.iterrows():
        lines.append("| " + " | ".join(_esc(r[c]) for c in cols) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote -> {csv_path}")
    print(f"wrote -> {OUT_DIR / 'figure.png'}")
    print(f"wrote -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
