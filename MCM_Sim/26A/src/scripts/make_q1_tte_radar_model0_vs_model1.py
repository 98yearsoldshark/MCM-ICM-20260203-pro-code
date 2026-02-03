#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06：用雷达图对比 Model-0（SOC 阈值）vs Model-1（截止电压）的 TTE（五类典型场景）。

用户需求（本次改动）：
- 把原来的柱状图（按场景的 TTE 条形对比）改为五边形雷达图；
- 雷达图 5 个顶点对应 S1~S5 五种典型使用情形；
- 叠加显示两套停止准则：
  - Model-0：SOC 阈值（soc_min）
  - Model-1：端电压截止（V_cut）
- 配色：蓝/绿/橘（#008CFF / #099F2D / #EC5A00），并通过透明度叠加显示。

注意：
- 本图属于 Q1 的“模型对比可视化”；不修改任何 Q2/Q3 代码与配置。
- 输出会写入 Q1材料/06 对应目录（会覆盖该目录的 figure.png，因为这是主图）。
  若你希望保留旧图，请先自行备份（本项目会在 other/ 中保留历史版本）。
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np

from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0, simulate_model1_ecm
from mcm26a.viz.style import PlotMode, apply_style, savefig

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path as MplPath
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D


# 指定配色（用户要求）
COLOR_GREEN = "#099F2D"
COLOR_BLUE = "#008CFF"
COLOR_ORANGE = "#EC5A00"  # 用户输入里最后一位疑似字母 O，这里按常见十六进制写法修正为 0


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A

Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "06-模型0vs模型1_TTE对比"


def _radar_factory(num_vars: int, *, frame: str = "polygon") -> np.ndarray:
    """创建雷达图 projection（五边形底图/网格需要 RESOLUTION=1）。

    参考：matplotlib 官方 radar chart 示例的思想（简化版）。
    """

    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarAxes(PolarAxes):
        name = "radar"
        # 关键：将圆弧分辨率设为 1，使得网格线/数据线在视觉上表现为“多边形”而非“圆弧”
        RESOLUTION = 1

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # 让第一个轴指向正上方（北），更符合阅读直觉
            self.set_theta_zero_location("N")

        def fill(self, *args, closed: bool = True, **kwargs):
            return super().fill(*args, closed=closed, **kwargs)

        def plot(self, *args, **kwargs):
            lines = super().plot(*args, **kwargs)
            # 自动闭合折线：避免用户传入未闭合数组导致缺边
            for ln in lines:
                x, y = ln.get_data()
                if len(x) > 0 and x[0] != x[-1]:
                    ln.set_data(np.append(x, x[0]), np.append(y, y[0]))
            return lines

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            if frame == "circle":
                return Circle((0.5, 0.5), 0.5)
            if frame == "polygon":
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="none")
            raise ValueError("unknown frame: %s" % frame)

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            if frame == "polygon":
                # 用正多边形 path 生成边框 spine
                spine = Spine(axes=self, spine_type="circle", path=MplPath.unit_regular_polygon(num_vars))
                spine.set_transform(Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes)
                return {"polar": spine}
            raise ValueError("unknown frame: %s" % frame)

        def draw(self, renderer):
            # 关键：把 r 方向网格（默认是圆弧）改成“多边形圈”。
            # 做法是把网格线的插值步数从默认的高分辨率改为 num_vars，
            # 这样每一圈网格会以 num_vars 个顶点拼成五边形（对本题是 5 场景）。
            if frame == "polygon":
                for gl in self.yaxis.get_gridlines():
                    gl.get_path()._interpolation_steps = num_vars
            super().draw(renderer)

    register_projection(RadarAxes)
    return theta


def _write_csv(path: Path, *, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _radar_plot(
    *,
    labels: list[str],
    values_m0: list[float],
    values_m1: list[float],
    mode: PlotMode,
    out_png: Path,
    lang: str,
) -> None:
    style = apply_style(mode)

    n = len(labels)
    if n < 3:
        raise ValueError("radar plot needs at least 3 axes")

    theta = _radar_factory(n, frame="polygon")
    angles = theta.tolist()  # for explicit plotting

    v0 = [float(x) for x in values_m0]
    v1 = [float(x) for x in values_m1]

    vmax = float(max(max(v0), max(v1)))
    # 对数刻度必须 >0，给一个保守下限
    r_min = 1.0
    # 用户希望刻度为 2/4/8/16/32h（对数刻度更直观）；若最大值略超 32，则保持最后一圈为 32，并把边界略放大。
    ticks = [2.0, 4.0, 8.0, 16.0, 32.0]
    r_max = max(32.0, vmax * 1.05)
    # 若最大值显著超过 32，则扩展到 64（避免截断/挤压）
    if vmax > 40.0:
        ticks.append(64.0)
        r_max = 64.0

    fig = plt.figure(figsize=(7.6, 6.0))
    ax = plt.subplot(111, projection="radar")

    # 顺时针（与之前一致）
    ax.set_theta_direction(-1)
    ax.set_varlabels(labels)

    # 对数半径刻度（2/4/8/16/32h）
    ax.set_rscale("log")
    ax.set_ylim(r_min, r_max)
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{int(t)}h" for t in ticks], color="gray", fontsize=9)
    # 把半径刻度标签放到右侧，避免遮挡标题
    ax.set_rlabel_position(90)

    # 网格/外圈颜色用绿色（用户指定蓝绿橘三色）
    # - spoke（角度方向）网格线可以直接用 xaxis.grid（是直线）
    # - ring（半径方向）默认会画“圆弧”，这里改为手动画“多边形圈”，更符合“五边形底图”的审美
    ax.xaxis.grid(True, color=COLOR_GREEN, alpha=0.22, lw=0.9)
    ax.yaxis.grid(False)
    for r in ticks:
        ax.plot(angles, [r] * n, color=COLOR_GREEN, alpha=0.22, lw=0.9, zorder=0, label="_nolegend_")
    ax.spines["polar"].set_color(COLOR_GREEN)
    ax.spines["polar"].set_alpha(0.35)
    ax.spines["polar"].set_linewidth(1.2)

    # 两个模型叠加：线 + 半透明填充
    if lang == "en":
        label0 = "Model-0 (SOC threshold)"
        label1 = "Model-1 (voltage cut-off)"
    else:
        label0 = "Model-0（SOC阈值）"
        label1 = "Model-1（截止电压）"

    ax.plot(angles, v0, color=COLOR_BLUE, lw=2.2, marker="o", markersize=4.0, label=label0)
    ax.fill(angles, v0, color=COLOR_BLUE, alpha=0.15)

    ax.plot(angles, v1, color=COLOR_ORANGE, lw=2.2, marker="o", markersize=4.0, label=label1)
    ax.fill(angles, v1, color=COLOR_ORANGE, alpha=0.15)

    # 题目最终论文通常是英文；这里提供中英两套标题，并在 study 版本附加英文后缀（避免全局 style 的中文后缀影响本图）。
    if lang == "en":
        title = "TTE Comparison Across Scenarios (Radar / Log Scale)"
        if mode == "study":
            title += " (study)"
    else:
        title = f"不同场景下的耗尽时间 TTE 对比（雷达图/对数刻度）{style.title_suffix}"
    ax.set_title(title, pad=18)

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.10, 1.0, 0.98))
        if lang == "en":
            note = (
                "Notes: Five vertices correspond to five typical usage scenarios (S1–S5). Radius is TTE (hours).\n"
                "Blue = Model-0 (SOC threshold). Orange = Model-1 (voltage cut-off). Semi-transparent fills highlight gaps.\n"
                "A larger gap in high-load scenarios indicates early shutdown due to voltage sag."
            )
        else:
            note = (
                "说明：五个顶点分别为五类典型使用情形（S1~S5）。半径表示 TTE（小时）。\n"
                "蓝色为 Model-0（SOC 阈值终止），橘色为 Model-1（截止电压终止）；透明填充用于突出差异。\n"
                "雷达图强调“相对形状与差异”，便于快速观察在哪些场景下欠压提前关机更显著。"
            )
        fig.text(0.01, 0.02, note, ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1-06：生成 Model-0 vs Model-1 的 TTE 雷达图（五场景）")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json"),
        help="Q1 五场景配置 JSON（默认使用 scenarios_q1_v1_5cases.json）",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数（Model-0/Model-1 共用；保持 Q1 简洁）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="电池参数（Model-1: 1RC ECM；Model-0 读取 energy_Wh/soc_min）",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="Model-1 积分步长（秒）")
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument(
        "--out-dir",
        default=str(Q1_DIR),
        help="输出目录（默认写入 Q1材料/06-模型0vs模型1_TTE对比）",
    )
    ap.add_argument("--mode", default="paper", choices=("paper", "study", "both"), help="输出模式：paper/study/both")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    other_dir = out_dir / "other"
    other_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(Path(args.scenarios))
    power = PowerParams0.from_json(Path(args.power))
    batt1 = BatteryParams1ECM.from_json(Path(args.phone))
    batt0 = BatteryParams0.from_json(Path(args.phone))

    # 固定顺序：S1~S5（严格按用户要求）
    order = [
        "S1_standby_light",
        "S2_browse_social",
        "S3_video_streaming",
        "S4_gaming",
        "S5_nav_call",
    ]

    labels: list[str] = []
    tte0: list[float] = []
    tte1: list[float] = []
    rows: list[list[object]] = []

    for sid in order:
        sc = materialize_scenario(raw, sid)
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        title = title_en if str(args.lang) == "en" else title_zh

        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=float(args.soc0))
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=float(args.soc0), dt_s=float(args.dt))

        # 这里按小时口径画图；若 None 则置 NaN（理论上这些 repeat 场景应都会耗尽）
        v0 = float("nan") if r0.tte_h is None else float(r0.tte_h)
        v1 = float("nan") if r1.tte_h is None else float(r1.tte_h)

        labels.append(title.replace(" ", "") if str(args.lang) == "zh" else title)
        tte0.append(v0)
        tte1.append(v1)
        rows.append(
            [sid, title_zh, title_en, v0, v1, (None if (not math.isfinite(v0) or not math.isfinite(v1)) else (v1 - v0))]
        )

    # 数据版本（与 figure.png 对应）
    _write_csv(
        other_dir / "data.csv",
        header=["scenario_id", "title_zh", "title_en", "tte_model0_h", "tte_model1_h", "delta_h_model1_minus_model0"],
        rows=rows,
    )

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure.png" if m == "paper" else "other/figure_study.png")
        _radar_plot(labels=labels, values_m0=tte0, values_m1=tte1, mode=m, out_png=out_png, lang=str(args.lang))  # type: ignore[arg-type]

    print(f"[OK] 已生成 Q1-06 雷达图：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
