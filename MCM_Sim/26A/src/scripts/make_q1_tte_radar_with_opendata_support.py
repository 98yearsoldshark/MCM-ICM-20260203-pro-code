#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-06（扩展图）：在 Model-0 vs Model-1 的 TTE 雷达图上叠加“公开测量数据支持的量级”。

赛题 Q1 的硬要求是连续时间机理模型（SOC(t) 的 ODE/方程组）；数据只能用于“参数估计与验证”，不能替代模型。
因此本图的定位不是“真值轨迹验证”，而是：
  - 使用开源测量数据给出“典型功耗/续航量级”参考；
  - 让评委相信我们的场景功耗设定与 TTE 输出在现实范围内（plausibility check）。

数据源（许可清晰，适合写入论文引用）：
- AndroWatts（Zenodo, CC BY 4.0）：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`

注意：
- AndroWatts 的数据并非按 S1~S5 场景采集，因此这里用一组“可解释的规则”把数据行粗分到五类。
- 输出写入 Q1-06 的 `other/opendata_support/`，不会覆盖 `Q1材料/06.../figure.png` 主图。
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path as MplPath
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D

from mcm26a.battery import BatteryParams0, BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model0, simulate_model1_ecm
from mcm26a.viz.style import PlotMode, apply_style, savefig


COLOR_GREEN = "#099F2D"
COLOR_BLUE = "#008CFF"
COLOR_ORANGE = "#EC5A00"
COLOR_BLACK = "#222222"


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A

Q1_DIR = ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "06-模型0vs模型1_TTE对比"
OPEN_DATA_CSV_DEFAULT = ROOT_DIR / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"


def _radar_factory(num_vars: int, *, frame: str = "polygon") -> np.ndarray:
    """创建雷达图 projection（五边形外框 + 五边形网格）。"""

    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarAxes(PolarAxes):
        name = "radar"
        RESOLUTION = 1

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_theta_zero_location("N")

        def fill(self, *args, closed: bool = True, **kwargs):
            return super().fill(*args, closed=closed, **kwargs)

        def plot(self, *args, **kwargs):
            lines = super().plot(*args, **kwargs)
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
            raise ValueError(f"unknown frame: {frame!r}")

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            if frame == "polygon":
                spine = Spine(axes=self, spine_type="circle", path=MplPath.unit_regular_polygon(num_vars))
                spine.set_transform(Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes)
                return {"polar": spine}
            raise ValueError(f"unknown frame: {frame!r}")

    register_projection(RadarAxes)
    return theta


def _write_csv(path: Path, *, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@dataclass(frozen=True)
class OpenDataScenarioStats:
    n: int
    p_W_median: float
    p_W_p25: float
    p_W_p75: float
    tte_h_median: float
    tte_h_p25: float
    tte_h_p75: float


def _rank01(s: pd.Series) -> pd.Series:
    # 使用百分位秩（0~1）比固定阈值更稳健：对单位尺度不敏感，且可解释为“在数据集中处于什么水平”。
    return s.rank(pct=True, method="average").clip(0.0, 1.0)


def _assign_scenarios_v1_simple(df: pd.DataFrame) -> pd.Series:
    """V1：简化规则（上一版）。

说明：优点是短小直接；缺点是“特征利用不充分”，对 S2/S3/S5 的区分力度有限。
    """

    def need(name: str) -> pd.Series:
        if name not in df.columns:
            raise ValueError(f"open data missing column: {name}")
        return df[name]

    bright = need("Brightness").astype(float)
    wifi_bytes = need("TOTAL_DATA_WIFI_BYTES").astype(float)

    p_cpu = (
        need("CPU_BIG_ENERGY_AVG_UWS").astype(float)
        + need("CPU_MID_ENERGY_AVG_UWS").astype(float)
        + need("CPU_LITTLE_ENERGY_AVG_UWS").astype(float)
    ) * 1e-6
    p_gpu = (need("GPU_ENERGY_AVG_UWS").astype(float) + need("GPU3D_ENERGY_AVG_UWS").astype(float)) * 1e-6
    p_cell = (need("CELLULAR_ENERGY_AVG_UWS").astype(float) + need("CELLULAR_ENERGY_AVG_UWS.1").astype(float)) * 1e-6
    p_infra = (need("INFRASTRUCTURE_ENERGY_AVG_UWS").astype(float) + need("INFRASTRUCTURE_ENERGY_AVG_UWS.1").astype(float)) * 1e-6

    q = lambda s, p: float(pd.Series(s).quantile(p))
    q_wifi60 = q(wifi_bytes, 0.60)
    q_wifi40 = q(wifi_bytes, 0.40)
    q_cpu50 = q(p_cpu, 0.50)
    q_cpu40 = q(p_cpu, 0.40)
    q_cpu80 = q(p_cpu, 0.80)
    q_cpu85 = q(p_cpu, 0.85)
    q_gpu40 = q(p_gpu, 0.40)
    q_gpu70 = q(p_gpu, 0.70)
    q_gpu85 = q(p_gpu, 0.85)
    q_cell80 = q(p_cell, 0.80)
    q_infra80 = q(p_infra, 0.80)

    mask = {
        "S1_standby_light": (bright <= 10.0) & (p_cpu <= q_cpu50),
        "S4_gaming": (bright >= 30.0) & (p_cpu >= q_cpu85) & (p_gpu >= q_gpu85),
        "S2_browse_social": (bright >= 30.0)
        & (wifi_bytes >= q_wifi60)
        & (p_cpu >= q_cpu40)
        & (p_cpu <= q_cpu80)
        & (p_gpu <= q_gpu70),
        "S3_video_streaming": (bright >= 30.0)
        & (wifi_bytes >= q_wifi60)
        & (p_cpu >= q_cpu40)
        & (p_cpu <= q_cpu85)
        & (p_gpu >= q_gpu40)
        & (p_gpu <= q_gpu85),
        "S5_nav_call": (bright >= 30.0)
        & (wifi_bytes <= q_wifi40)
        & ((p_cell >= q_cell80) | (p_infra >= q_infra80)),
    }

    # 优先级：先分配特征最鲜明的类，避免重叠导致“都被 S2/S3 吃掉”
    priority = ["S4_gaming", "S5_nav_call", "S3_video_streaming", "S2_browse_social", "S1_standby_light"]
    assigned = pd.Series([None] * len(df))
    for sid in priority:
        idx = mask[sid] & assigned.isna()
        assigned.loc[idx] = sid

    return assigned


def _assign_scenarios_v2_feature_rules(df: pd.DataFrame) -> tuple[pd.Series, dict[str, dict[str, float]]]:
    """V2：更“科学/可解释”的场景映射规则（推荐）。

核心想法：
- 由于 AndroWatts 没有自带场景标签，我们用“可解释的、与场景定义一致的设备状态/功耗轨特征”构造映射；
- 使用百分位秩（0~1）形成无量纲强度指标，减少单位/尺度不确定性带来的偏差；
- 采用“门控(gating) + 优先级(priority)”避免类别大量重叠：
  先分配特征最鲜明的类（如游戏），再分配相对模糊的类（如浏览/视频），最后分配待机/轻度。

我们使用的 5 个强度指标（全部来自 aggregated.csv 的开源字段）：
- screen_intensity：亮度 + 显示轨功耗（Brightness, Display_ENERGY_AVG_UWS, L22M_DISP_ENERGY_AVG_UWS）
- cpu_intensity：CPU 轨功耗 + CPU 大核频率（CPU_*_ENERGY_AVG_UWS, CPU_BIG_FREQ_KHz）
- gpu_intensity：GPU 轨功耗 + GPU 频率（GPU*_ENERGY_AVG_UWS, GPU0_FREQ）
- wifi_intensity：WiFi 数据量（TOTAL_DATA_WIFI_BYTES）
- infra_intensity：基础设施/蜂窝相关功耗（INFRASTRUCTURE + CELLULAR rails，注意：GPS 在该数据里几乎恒定，只能弱使用）
"""

    def need(name: str) -> pd.Series:
        if name not in df.columns:
            raise ValueError(f"open data missing column: {name}")
        return df[name]

    # 组件功耗代理（W）：使用 *_ENERGY_AVG_UWS（与电池放电指标强相关，且数值更接近手机功耗量级）
    disp_w = (need("Display_ENERGY_AVG_UWS").astype(float) + need("L22M_DISP_ENERGY_AVG_UWS").astype(float)) * 1e-6
    cpu_w = (
        need("CPU_BIG_ENERGY_AVG_UWS").astype(float)
        + need("CPU_MID_ENERGY_AVG_UWS").astype(float)
        + need("CPU_LITTLE_ENERGY_AVG_UWS").astype(float)
    ) * 1e-6
    gpu_w = (need("GPU_ENERGY_AVG_UWS").astype(float) + need("GPU3D_ENERGY_AVG_UWS").astype(float)) * 1e-6
    infra_w = (
        need("INFRASTRUCTURE_ENERGY_AVG_UWS").astype(float)
        + need("INFRASTRUCTURE_ENERGY_AVG_UWS.1").astype(float)
        + need("CELLULAR_ENERGY_AVG_UWS").astype(float)
        + need("CELLULAR_ENERGY_AVG_UWS.1").astype(float)
    ) * 1e-6

    bright = need("Brightness").astype(float)
    wifi_bytes = need("TOTAL_DATA_WIFI_BYTES").astype(float)

    cpu_big_khz = pd.to_numeric(need("CPU_BIG_FREQ_KHz"), errors="coerce")
    gpu0_freq = pd.to_numeric(need("GPU0_FREQ"), errors="coerce")
    cpu_big_khz = cpu_big_khz.fillna(cpu_big_khz.median())
    gpu0_freq = gpu0_freq.fillna(gpu0_freq.median())

    r_bright = _rank01(bright)
    r_disp = _rank01(disp_w)
    r_cpu_p = _rank01(cpu_w)
    r_gpu_p = _rank01(gpu_w)
    r_cpu_f = _rank01(cpu_big_khz)
    r_gpu_f = _rank01(gpu0_freq)
    r_wifi = _rank01(wifi_bytes)
    r_infra = _rank01(infra_w)

    # 组合强度指标（0~1）
    screen_int = 0.6 * r_bright + 0.4 * r_disp
    cpu_int = 0.6 * r_cpu_p + 0.4 * r_cpu_f
    gpu_int = 0.6 * r_gpu_p + 0.4 * r_gpu_f
    wifi_int = r_wifi
    infra_int = r_infra

    # 门控规则（全部基于 0~1 的无量纲强度阈值）
    # - 阈值并非“拍脑袋”：它表达的是“在该公开数据集中处于较高/中等/较低水平”
    mask = {
        # S4 游戏：CPU+GPU 同时高，且屏幕应处于开启/较亮状态
        "S4_gaming": (screen_int > 0.45) & (cpu_int > 0.75) & (gpu_int > 0.75),
        # S3 视频/直播：WiFi 数据量高，CPU/GPU 中等（避免被游戏吃掉）
        "S3_video_streaming": (screen_int > 0.45)
        & (wifi_int > 0.78)
        & (cpu_int.between(0.25, 0.80))
        & (gpu_int.between(0.25, 0.80)),
        # S2 浏览/社交：WiFi 中等，CPU/GPU 中等偏上但不至于像游戏
        "S2_browse_social": (screen_int > 0.45)
        & (wifi_int.between(0.45, 0.78))
        & (cpu_int.between(0.35, 0.85))
        & (gpu_int < 0.78),
        # S5 导航/通话：WiFi 低但 infra/cellular rail 偏高（注意：该数据集并不专门测导航/通话，属于近似）
        "S5_nav_call": (screen_int > 0.45) & (wifi_int < 0.42) & (infra_int > 0.72),
        # S1 待机/轻度：屏幕强度低 + CPU/GPU 低（允许少量 WiFi 背景流量）
        "S1_standby_light": (screen_int < 0.35) & (cpu_int < 0.50) & (gpu_int < 0.55) & (wifi_int < 0.60),
    }

    # 优先级：先分配最鲜明的类，再分配较模糊的类
    priority = ["S4_gaming", "S5_nav_call", "S3_video_streaming", "S2_browse_social", "S1_standby_light"]
    assigned = pd.Series([None] * len(df))
    for sid in priority:
        idx = mask[sid] & assigned.isna()
        assigned.loc[idx] = sid

    # 给论文/复现留一个“映射诊断摘要”：每类的强度指标中位数（用于证明规则的合理性）
    summary: dict[str, dict[str, float]] = {}
    for sid in priority:
        m = assigned == sid
        if int(m.sum()) == 0:
            summary[sid] = {
                "n": 0,
                "screen_int_median": float("nan"),
                "cpu_int_median": float("nan"),
                "gpu_int_median": float("nan"),
                "wifi_int_median": float("nan"),
                "infra_int_median": float("nan"),
            }
            continue
        summary[sid] = {
            "n": int(m.sum()),
            "screen_int_median": float(screen_int[m].median()),
            "cpu_int_median": float(cpu_int[m].median()),
            "gpu_int_median": float(gpu_int[m].median()),
            "wifi_int_median": float(wifi_int[m].median()),
            "infra_int_median": float(infra_int[m].median()),
        }

    return assigned, summary


def _compute_opendata_support(
    df: pd.DataFrame, *, energy_Wh: float, mapping: str
) -> tuple[dict[str, OpenDataScenarioStats], dict[str, dict[str, float]]]:
    """将 AndroWatts 映射到 S1~S5，并输出每类的功耗/续航量级统计 + 映射诊断信息。"""

    pow_cols = [c for c in df.columns if c.endswith("_ENERGY_AVG_UWS")]
    if not pow_cols:
        raise ValueError("open data missing *_ENERGY_AVG_UWS columns")
    df = df.copy()
    df["P_total_W"] = df[pow_cols].sum(axis=1) * 1e-6

    if mapping == "v1":
        assigned = _assign_scenarios_v1_simple(df)
        diag = {}
    elif mapping == "v2":
        assigned, diag = _assign_scenarios_v2_feature_rules(df)
    else:
        raise ValueError(f"unknown mapping: {mapping!r}")

    out: dict[str, OpenDataScenarioStats] = {}
    for sid in [
        "S1_standby_light",
        "S2_browse_social",
        "S3_video_streaming",
        "S4_gaming",
        "S5_nav_call",
    ]:
        d = df.loc[assigned == sid]
        if d.empty:
            out[sid] = OpenDataScenarioStats(
                n=0,
                p_W_median=float("nan"),
                p_W_p25=float("nan"),
                p_W_p75=float("nan"),
                tte_h_median=float("nan"),
                tte_h_p25=float("nan"),
                tte_h_p75=float("nan"),
            )
            continue

        pW = d["P_total_W"].astype(float).to_numpy()
        tte_h = float(energy_Wh) / np.maximum(pW, 1e-9)  # 满电近似
        out[sid] = OpenDataScenarioStats(
            n=int(len(pW)),
            p_W_median=float(np.median(pW)),
            p_W_p25=float(np.percentile(pW, 25)),
            p_W_p75=float(np.percentile(pW, 75)),
            tte_h_median=float(np.median(tte_h)),
            tte_h_p25=float(np.percentile(tte_h, 25)),
            tte_h_p75=float(np.percentile(tte_h, 75)),
        )

    return out, diag


def _plot_radar(
    *,
    labels: list[str],
    tte_m0: list[float],
    tte_m1: list[float],
    tte_open: list[float],
    open_counts: list[int],
    mode: PlotMode,
    out_png: Path,
    lang: str,
) -> None:
    style = apply_style(mode)

    n = len(labels)
    theta = _radar_factory(n, frame="polygon")
    angles = theta.tolist()

    v0 = [float(x) for x in tte_m0]
    v1 = [float(x) for x in tte_m1]
    vo = [float(x) for x in tte_open]

    ticks = [2.0, 4.0, 8.0, 16.0, 32.0]
    vmax = float(np.nanmax([np.nanmax(v0), np.nanmax(v1), np.nanmax(vo)]))
    r_min = 1.0
    r_max = max(32.0, vmax * 1.05)
    if vmax > 40.0:
        ticks.append(64.0)
        r_max = 64.0

    fig = plt.figure(figsize=(8.2, 6.6))
    ax = plt.subplot(111, projection="radar")
    ax.set_theta_direction(-1)
    ax.set_varlabels(labels)

    ax.set_rscale("log")
    ax.set_ylim(r_min, r_max)
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{int(t)}h" for t in ticks], color="gray", fontsize=9)
    ax.set_rlabel_position(90)

    # 五边形网格：角度方向用 xaxis.grid；半径方向用手动画 polygon ring
    ax.xaxis.grid(True, color=COLOR_GREEN, alpha=0.22, lw=0.9)
    ax.yaxis.grid(False)
    for r in ticks:
        ax.plot(angles, [r] * n, color=COLOR_GREEN, alpha=0.22, lw=0.9, zorder=0, label="_nolegend_")
    ax.spines["polar"].set_color(COLOR_GREEN)
    ax.spines["polar"].set_alpha(0.35)
    ax.spines["polar"].set_linewidth(1.2)

    if lang == "en":
        label0 = "Model-0 (SOC threshold)"
        label1 = "Model-1 (voltage cut-off)"
        labelo = "Open data (AndroWatts, implied)"
        title = "TTE Comparison Across Scenarios (Radar / Log Scale)"
        if mode == "study":
            title += " (study)"
    else:
        label0 = "Model-0（SOC阈值）"
        label1 = "Model-1（截止电压）"
        labelo = "公开数据（AndroWatts 推得量级）"
        title = f"不同场景下的耗尽时间 TTE 对比（雷达图/对数刻度）{style.title_suffix}"

    # 两个模型 + 公开数据量级
    ax.plot(angles, v0, color=COLOR_BLUE, lw=2.2, marker="o", markersize=4.0, label=label0)
    ax.fill(angles, v0, color=COLOR_BLUE, alpha=0.12)

    ax.plot(angles, v1, color=COLOR_ORANGE, lw=2.2, marker="o", markersize=4.0, label=label1)
    ax.fill(angles, v1, color=COLOR_ORANGE, alpha=0.12)

    ax.plot(angles, vo, color=COLOR_BLACK, lw=1.8, ls="--", marker="s", markersize=3.6, label=labelo)

    ax.set_title(title, pad=18)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.12, 1.0, 0.98))
        if lang == "en":
            note = (
                "Notes: The black dashed polygon is NOT a ground-truth trajectory. It is an order-of-magnitude support\n"
                "derived from open measurements (AndroWatts). Each vertex uses a rule-based mapping; n is matched samples.\n"
                + "n = [" + ", ".join(str(int(x)) for x in open_counts) + "] (S1..S5)"
            )
        else:
            note = (
                "说明：黑色虚线不是逐时刻真值轨迹，而是由 AndroWatts 开源测量推得的“量级支撑”（满电 TTE≈E/P）。\n"
                "每个顶点通过规则将数据行粗映射到 S1..S5；n 为匹配到的样本数。\n"
                + "n = [" + ", ".join(str(int(x)) for x in open_counts) + "] (S1..S5)"
            )
        fig.text(0.01, 0.02, note, ha="left", va="bottom", fontsize=9)
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1-06：叠加公开测量数据量级支撑（不覆盖主图）")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_q1_v1_5cases.json"),
        help="Q1 五场景配置 JSON",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v0.json"),
        help="功耗参数（用于 Model-0/Model-1 仿真）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="电池参数（energy_Wh + ECM 参数）",
    )
    ap.add_argument(
        "--open-data",
        default=str(OPEN_DATA_CSV_DEFAULT),
        help="公开测量数据（AndroWatts aggregated.csv）路径",
    )
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="Model-1 积分步长（秒）")
    ap.add_argument(
        "--mapping",
        default="v2",
        choices=("v1", "v2"),
        help="AndroWatts→S1..S5 映射规则版本：v1(简化) / v2(特征门控，推荐)",
    )
    ap.add_argument("--lang", default="en", choices=("zh", "en"), help="图中语言：zh/en（默认 en）")
    ap.add_argument("--mode", default="both", choices=("paper", "study", "both"), help="输出模式")
    ap.add_argument(
        "--out-dir",
        default=str(Q1_DIR / "other" / "opendata_support_v2"),
        help="输出目录（默认写入 Q1-06/other/opendata_support_v2；不会覆盖主图）",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(Path(args.scenarios))
    power = PowerParams0.from_json(Path(args.power))
    batt1 = BatteryParams1ECM.from_json(Path(args.phone))
    batt0 = BatteryParams0.from_json(Path(args.phone))

    # 固定顺序：S1~S5
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

    for sid in order:
        sc = materialize_scenario(raw, sid)
        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        title = title_en if str(args.lang) == "en" else title_zh
        labels.append(title.replace(" ", "") if str(args.lang) == "zh" else title)

        r0 = simulate_model0(sc, power_params=power, battery_params=batt0, soc0=float(args.soc0))
        r1 = simulate_model1_ecm(sc, power_params=power, battery_params=batt1, soc0=float(args.soc0), dt_s=float(args.dt))
        tte0.append(float("nan") if r0.tte_h is None else float(r0.tte_h))
        tte1.append(float("nan") if r1.tte_h is None else float(r1.tte_h))

    # open data：计算“量级支撑”曲线
    od = pd.read_csv(Path(args.open_data))
    stats, diag = _compute_opendata_support(od, energy_Wh=float(batt0.energy_Wh), mapping=str(args.mapping))

    tte_open: list[float] = []
    open_counts: list[int] = []
    rows: list[list[object]] = []
    for sid in order:
        st = stats[sid]
        tte_open.append(float(st.tte_h_median))
        open_counts.append(int(st.n))

        title_zh = str(raw["scenarios"][sid].get("title_zh", sid))
        title_en = str(raw["scenarios"][sid].get("title_en", title_zh))
        rows.append(
            [
                sid,
                title_zh,
                title_en,
                int(st.n),
                st.p_W_median,
                st.p_W_p25,
                st.p_W_p75,
                st.tte_h_median,
                st.tte_h_p25,
                st.tte_h_p75,
            ]
        )

    _write_csv(
        out_dir / "data_opendata_support.csv",
        header=[
            "scenario_id",
            "title_zh",
            "title_en",
            "n_samples",
            "P_total_W_median",
            "P_total_W_p25",
            "P_total_W_p75",
            "TTE_full_h_median",
            "TTE_full_h_p25",
            "TTE_full_h_p75",
        ],
        rows=rows,
    )

    # 输出映射诊断（v2 才有）：用于论文/附录解释“为什么这条黑线可信”
    if diag:
        diag_rows: list[list[object]] = []
        for sid, d in diag.items():
            diag_rows.append([sid, d.get("n", 0), d.get("screen_int_median"), d.get("cpu_int_median"), d.get("gpu_int_median"), d.get("wifi_int_median"), d.get("infra_int_median")])
        _write_csv(
            out_dir / "mapping_diagnostics.csv",
            header=["scenario_id", "n", "screen_int_median", "cpu_int_median", "gpu_int_median", "wifi_int_median", "infra_int_median"],
            rows=diag_rows,
        )

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for m in modes:
        out_png = out_dir / ("figure_paper.png" if m == "paper" else "figure_study.png")
        _plot_radar(
            labels=labels,
            tte_m0=tte0,
            tte_m1=tte1,
            tte_open=tte_open,
            open_counts=open_counts,
            mode=m,  # type: ignore[arg-type]
            out_png=out_png,
            lang=str(args.lang),
        )

    about = (
        "# about\n\n"
        "- 目的：为 Q1-06 雷达图提供“公开测量数据支持的量级”（sanity check），不替代连续时间机理模型。\n"
        "- 数据源：AndroWatts（Zenodo，CC BY 4.0），见 `MCM_Sim/26A/data/open_data/README_zh.md`。\n"
        "- 计算口径：P 取 open data 的 `*_ENERGY_AVG_UWS` 求和并换算为 W；满电 TTE≈E/P（E 取 phone 配置里的 energy_Wh）。\n"
        f"- 场景映射：使用 `--mapping {args.mapping}` 将 open data 行粗分到 S1..S5，并在图中标注每类样本数 n。\n"
        "  - v2 会输出 `mapping_diagnostics.csv`，给出每类关键强度指标的中位数，便于解释映射规则是否符合直觉。\n\n"
        "复现命令：\n\n"
        "```bash\n"
        "PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_radar_with_opendata_support.py --mode both --lang en --mapping v2\n"
        "```\n"
    )
    (out_dir / "about.md").write_text(about, encoding="utf-8")

    print(f"[OK] 已生成公开数据量级支撑图：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
