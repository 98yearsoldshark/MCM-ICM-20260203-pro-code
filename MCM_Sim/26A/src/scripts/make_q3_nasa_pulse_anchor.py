#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：观测锚定——脉冲/随机负载下的电压下陷示例（NASA PCoE 数据）。

用途（对齐赛题 Q3）：
- Q3-2 使用 `min_headroom_margin` 作为欠压/崩塌风险指标。为避免“指标是我们自定义的”质疑，
  我们用公开实验数据展示：在**脉冲负载**下，端电压会出现明显下陷并逼近 cut-off；在休止段电压回弹。
  这与模型中的“裕量缩小→更易提前关机”的机理方向一致。

输出：
- 报表：`src/out_reports/q3/observed_nasa_battery/pulse_demo_rw4_steps9730_9739.csv`
- 图像：
  - paper：`src/out_plots/q3/paper/observed_nasa_battery/01_pulse_voltage_sag.png`
  - study：`src/out_plots/q3/study/observed_nasa_battery/01_pulse_voltage_sag.png`

说明：
- 本脚本只做“观测锚定示例”，不用于拟合/替代连续时间模型。
- 时间轴使用“分钟”，便于读者直观理解；原始数据单位为秒（s）。
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "src"
DATA_DIR = REPO_ROOT / "MCM_Sim" / "26A" / "data"


SKIP_GRADIENT = ["#845ec2", "#4ffbdf", "#00c2a8", "#008b74"]


def _ensure_cn_font() -> None:
    import matplotlib as mpl

    mpl.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Songti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    mpl.rcParams["axes.unicode_minus"] = False


def _concat_steps(mat_path: Path, step_indices: list[int]) -> pd.DataFrame:
    mat = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    data = mat["data"]
    steps = data.step  # numpy array of matlab structs

    rows: list[dict[str, object]] = []
    t_offset = 0.0
    for idx in step_indices:
        s = steps[int(idx)]
        rt = np.asarray(getattr(s, "relativeTime"), dtype=float)
        cur = np.asarray(getattr(s, "current"), dtype=float)
        vol = np.asarray(getattr(s, "voltage"), dtype=float)
        temp = np.asarray(getattr(s, "temperature"), dtype=float) if hasattr(s, "temperature") else np.full_like(vol, np.nan)

        if rt.size == 0:
            continue
        # 每个 step 的 relativeTime 都从 ~0 开始；这里将其平移并拼接为连续时间轴。
        rt0 = float(rt[0])
        t = t_offset + (rt - rt0)
        t_offset += float(rt[-1] - rt0)

        typ = str(getattr(s, "type", ""))
        comment = str(getattr(s, "comment", ""))

        for ti, ii, vi, te in zip(t.tolist(), cur.tolist(), vol.tolist(), temp.tolist()):
            rows.append(
                {
                    "t_s": float(ti),
                    "current_A": float(ii),
                    "voltage_V": float(vi),
                    "temp_C": float(te),
                    "step_idx": int(idx),
                    "step_type": typ,
                    "step_comment": comment,
                }
            )

    return pd.DataFrame(rows)


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def _shade_intervals(ax, x: np.ndarray, mask: np.ndarray, *, color: str, alpha: float = 0.08) -> None:
    """对 mask=True 的区间做背景淡色阴影（便于读者识别“放电脉冲段”）。"""

    if x.size == 0:
        return
    m = mask.astype(bool)
    # 找连续区间
    starts = np.where((m[1:] & ~m[:-1]))[0] + 1
    ends = np.where((~m[1:] & m[:-1]))[0] + 1
    if m[0]:
        starts = np.r_[0, starts]
    if m[-1]:
        ends = np.r_[ends, m.size - 1]
    for s, e in zip(starts.tolist(), ends.tolist()):
        ax.axvspan(float(x[s]), float(x[e]), color=color, alpha=alpha, lw=0)


def _plot(df: pd.DataFrame, out_png: Path, *, mode: str) -> None:
    import matplotlib.pyplot as plt

    _ensure_cn_font()

    x_min = (df["t_s"].to_numpy(dtype=float) / 60.0)
    i_a = df["current_A"].to_numpy(dtype=float)
    v_v = df["voltage_V"].to_numpy(dtype=float)

    # 识别“脉冲放电段”：用电流阈值即可（该数据集的 rest 段电流=0）
    is_discharge = i_a > 0.05

    # 论文版更紧凑；学习版留更多说明空间
    fig_h = 5.2 if mode == "paper" else 6.0
    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(10.5, fig_h),
        dpi=200,
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.2], "hspace": 0.06},
    )

    # 背景阴影：放电脉冲段
    _shade_intervals(ax1, x_min, is_discharge, color=SKIP_GRADIENT[0], alpha=0.06)
    _shade_intervals(ax2, x_min, is_discharge, color=SKIP_GRADIENT[0], alpha=0.06)

    # current
    ax1.plot(x_min, i_a, color=SKIP_GRADIENT[0], lw=1.2)
    ax1.set_ylabel("电流 I (A)")
    ax1.grid(True, axis="y", color="#e6e6e6", lw=0.8)

    # voltage
    ax2.plot(x_min, v_v, color=SKIP_GRADIENT[3], lw=1.2)
    v_cut = 3.20  # 该实验数据在 ~3.2V 附近截止（见 step 内最低电压）
    ax2.axhline(v_cut, color="#888888", ls="--", lw=1.0)
    ax2.text(x_min.min() + 0.2, v_cut + 0.01, "实验 cut-off≈3.20V", color="#666666", fontsize=9)
    ax2.set_ylabel("电压 V (V)")
    ax2.set_xlabel("时间 (分钟)")
    ax2.grid(True, color="#e6e6e6", lw=0.8)

    title = "观测锚定：脉冲负载下的电压下陷与回弹（NASA PCoE 随机负载数据）"
    ax1.set_title(title, fontsize=12, pad=10)

    if mode == "study":
        # 解释性注释：在一次“放电→休止”循环上标注下陷/回弹
        # 选取全局最低点附近
        k_min = int(np.nanargmin(v_v))
        x0 = float(x_min[k_min])
        y0 = float(v_v[k_min])
        ax2.scatter([x0], [y0], s=30, color=SKIP_GRADIENT[1], zorder=5)
        ax2.annotate(
            "脉冲放电下陷：负载↑ → 欧姆压降+极化\n裕量缩小，逼近 cut-off",
            xy=(x0, y0),
            xytext=(x0 - 25, y0 + 0.35),
            arrowprops={"arrowstyle": "->", "color": "#444444", "lw": 1.0},
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#cccccc"},
        )

        ax2.annotate(
            "休止回弹：极化释放/扩散恢复\n电压回升（但 SOC 继续下降）",
            xy=(x0 + 18, min(4.1, y0 + 0.25)),
            xytext=(x0 + 8, min(4.15, y0 + 0.55)),
            arrowprops={"arrowstyle": "->", "color": "#444444", "lw": 1.0},
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#cccccc"},
        )

        ax1.text(
            0.01,
            0.02,
            "阴影区=放电脉冲段（I>0）\n白底区=休止段（I=0）",
            transform=ax1.transAxes,
            fontsize=9,
            color="#333333",
            va="bottom",
            ha="left",
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#cccccc"},
        )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    # 选用：NASA Randomized Battery Usage Data Set（RW4），挑一个接近 cut-off 的脉冲段窗口。
    mat_path = (
        DATA_DIR
        / "NASA-BatteryData"
        / "11.+Randomized+Battery+Usage+Data+Set"
        / "11. Randomized Battery Usage Data Set"
        / "Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post"
        / "data"
        / "Matlab"
        / "RW4.mat"
    )

    step_indices = list(range(9730, 9740))  # 交替脉冲放电/休止，且最低电压逼近 cut-off

    df = _concat_steps(mat_path, step_indices)
    if df.empty:
        raise RuntimeError("拼接后的数据为空，检查 mat_path 或 step_indices 是否正确。")

    report_path = SRC_DIR / "out_reports" / "q3" / "observed_nasa_battery" / "pulse_demo_rw4_steps9730_9739.csv"
    _write_csv(report_path, df)

    out_paper = SRC_DIR / "out_plots" / "q3" / "paper" / "observed_nasa_battery" / "01_pulse_voltage_sag.png"
    out_study = SRC_DIR / "out_plots" / "q3" / "study" / "observed_nasa_battery" / "01_pulse_voltage_sag.png"
    _plot(df, out_paper, mode="paper")
    _plot(df, out_study, mode="study")

    print(f"wrote -> {report_path}")
    print(f"wrote -> {out_paper}")
    print(f"wrote -> {out_study}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

