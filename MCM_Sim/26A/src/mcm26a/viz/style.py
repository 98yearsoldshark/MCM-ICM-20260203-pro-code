"""绘图风格：paper（论文用，简洁）与 study（学习用，带解释）。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# 避免在某些受限环境下 ~/.matplotlib 不可写导致崩溃/卡顿：
# 把 matplotlib 配置/字体缓存定向到项目内的可写目录。
if "MPLCONFIGDIR" not in os.environ:
    _cfg = Path(__file__).resolve().parents[2] / ".mplconfig"
    _cfg.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(_cfg)

# 在无 GUI 的命令行环境中生成 PNG：强制使用非交互式后端，避免偶发崩溃。
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

PlotMode = Literal["paper", "study"]

# 统一配色表（最多 4 色）：Skip Gradient（用户指定）。
# 说明：该配色表对“分组/堆叠对比”更友好；Q3 的分解类图优先使用。
PALETTE_SKIP_GRADIENT: tuple[str, str, str, str] = ("#845ec2", "#4ffbdf", "#00c2a8", "#008b74")

# 热力图渐变色（用于 TTE 等“低→高”单调量的展示）。
# 用户给的调色板为 RdYlGn（红→黄→绿）；为满足“低值=绿，高值=红”的口径，这里反向使用：
# - 低值：绿色
# - 中间：黄
# - 高值：红色
COLORS_HEATMAP_TTE: tuple[str, ...] = (
    "#006837",
    "#1A9850",
    "#66BD63",
    "#A6D96A",
    "#D9EF8B",
    "#FEE08B",
    "#FDAE61",
    "#F46D43",
    "#D73027",
    "#A50026",
)


def get_cmap_tte():
    """返回 TTE 热力图专用 colormap（低值→高值）。"""

    return LinearSegmentedColormap.from_list("mcm26a_tte", list(COLORS_HEATMAP_TTE), N=256)


@dataclass(frozen=True)
class PlotStyle:
    mode: PlotMode
    dpi: int
    annotate: bool
    title_suffix: str


def get_style(mode: PlotMode) -> PlotStyle:
    if mode == "paper":
        return PlotStyle(mode=mode, dpi=300, annotate=False, title_suffix="")
    if mode == "study":
        return PlotStyle(mode=mode, dpi=220, annotate=True, title_suffix="（学习版）")
    raise ValueError(f"unknown mode: {mode!r}")


def apply_style(mode: PlotMode) -> PlotStyle:
    """统一设置 matplotlib 全局风格（中文字体优先尝试本机常见字体）。"""

    style = get_style(mode)
    grid_alpha = 0.18 if mode == "paper" else 0.25

    mpl.rcParams.update(
        {
            "figure.dpi": style.dpi,
            "savefig.dpi": style.dpi,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 11 if mode == "paper" else 10,
            "axes.titlesize": 12 if mode == "paper" else 11,
            "axes.labelsize": 11,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.grid.axis": "y",
            "grid.alpha": grid_alpha,
            "grid.linestyle": "-",
            "grid.linewidth": 0.8,
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            # 中文字体候选：macOS 常见 PingFang；Windows 常见 SimHei；再退回 DejaVu Sans。
            "font.sans-serif": ["PingFang SC", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
        }
    )
    return style


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def savefig(fig, path: str | Path, *, mode: PlotMode) -> None:
    """保存图像（统一 bbox/tight）。"""

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, bbox_inches="tight")
