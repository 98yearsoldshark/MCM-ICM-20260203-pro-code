# -*- coding: utf-8 -*-
# 绘图工具：把 runs.csv 的汇总结果画成论文可用图片
#
# 设计目标：
# - 不依赖 seaborn，避免额外安装负担
# - 以“gamma × w”热图为主（bet-hedging 主图的核心形态）

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

# 在无 GUI/无 DISPLAY 环境下强制使用非交互式后端
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  （必须在设置后端之后再导入 pyplot）
from matplotlib.colors import Normalize, TwoSlopeNorm  # noqa: E402

# 轨迹图需要用到模型里的派生量计算
from .model0 import male_fraction, x_from_resource  # noqa: E402

# 尝试启用中文字体（在 macOS 上通常可用；若不可用会自动回退）
plt.rcParams["font.sans-serif"] = [
    "Heiti SC",
    "Songti SC",
    "PingFang SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def _as_sorted_unique(values: Iterable[float]) -> list[float]:
    xs = sorted({float(v) for v in values})
    return xs


def _robust_limits(mat: np.ndarray, *, low: float = 2.0, high: float = 98.0) -> tuple[float, float]:
    """用分位数给出更“抗离群点”的色条范围。"""
    x = mat[np.isfinite(mat)]
    if x.size == 0:
        return 0.0, 1.0
    vmin = float(np.percentile(x, low))
    vmax = float(np.percentile(x, high))
    if vmin == vmax:
        # 避免色条跨度为 0
        eps = 1e-9 if vmin == 0 else abs(vmin) * 1e-3
        return vmin - eps, vmax + eps
    return vmin, vmax


def _add_cell_annotations(
    ax: plt.Axes,
    mat: np.ndarray,
    *,
    fmt: str,
    norm: Normalize | None,
    fontsize: int = 8,
) -> None:
    """在热图每个格子中心写数值（论文展示更直观）。"""
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if not np.isfinite(val):
                continue
            try:
                txt = fmt.format(float(val))
            except Exception:
                txt = str(val)
            if norm is None:
                color = "black"
            else:
                # 背景越深，文字越浅；阈值 0.55 是经验值
                color = "white" if float(norm(val)) >= 0.55 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=fontsize, color=color)


def _set_heatmap_axes(ax: plt.Axes, *, gammas: Sequence[float], ws: Sequence[float]) -> None:
    ax.set_xticks(np.arange(len(gammas)))
    ax.set_xticklabels([str(g) for g in gammas])
    ax.set_yticks(np.arange(len(ws)))
    ax.set_yticklabels([str(w) for w in ws])

    # 画网格线，让“格子”更像表格（论文更清晰）
    ax.set_xticks(np.arange(len(gammas) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(ws) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.8, alpha=0.9)
    ax.tick_params(which="minor", bottom=False, left=False)


def plot_grid_heatmap(
    df: pd.DataFrame,
    *,
    value_col: str,
    gammas: Sequence[float] | None = None,
    ws: Sequence[float] | None = None,
    title: str,
    out_path: Path,
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str = "viridis",
    center: float | None = None,
    robust: bool = False,
    annotate: bool = True,
    fmt: str = "{:.2f}",
    contour_levels: Sequence[float] | None = None,
    contour_color: str = "black",
) -> None:
    """画 gamma×w 的热图（只使用可变策略 S_var 的网格点）。"""
    if value_col not in df.columns:
        raise KeyError(f"缺少列：{value_col}")

    sub = df[df["p_m_override"].isna()].copy()
    if sub.empty:
        raise ValueError("未找到 S_var 行（p_m_override 全部非空）")

    if gammas is None:
        gammas = _as_sorted_unique(sub["gamma"].tolist())
    if ws is None:
        ws = _as_sorted_unique(sub["w"].tolist())

    pivot = sub.pivot_table(index="w", columns="gamma", values=value_col, aggfunc="mean")
    pivot = pivot.reindex(index=list(ws), columns=list(gammas))
    mat = pivot.to_numpy(dtype=float)

    if robust and (vmin is None or vmax is None):
        rvmin, rvmax = _robust_limits(mat)
        vmin = rvmin if vmin is None else vmin
        vmax = rvmax if vmax is None else vmax

    if center is not None:
        # TwoSlopeNorm：以 center 为 0 点（或阈值点）做发散配色更直观
        if vmin is None or vmax is None:
            rvmin, rvmax = _robust_limits(mat)
            vmin = rvmin if vmin is None else vmin
            vmax = rvmax if vmax is None else vmax
        c = float(center)
        vmin_f = float(vmin)
        vmax_f = float(vmax)
        # matplotlib 要求严格：vmin < vcenter < vmax。若数据不跨越 center，则做对称扩展避免报错。
        if not (vmin_f < c < vmax_f):
            span = max(abs(vmin_f - c), abs(vmax_f - c))
            if span == 0.0:
                span = 1e-9
            eps = span * 1e-6 + 1e-12
            vmin_f = c - span - eps
            vmax_f = c + span + eps
        norm = TwoSlopeNorm(vmin=vmin_f, vcenter=c, vmax=vmax_f)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax) if (vmin is not None or vmax is not None) else None

    fig, ax = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    im = ax.imshow(mat, origin="lower", aspect="auto", cmap=cmap, norm=norm)

    ax.set_title(title)
    ax.set_xlabel("gamma（性别比敏感度）")
    ax.set_ylabel("w（记忆长度，年）")

    _set_heatmap_axes(ax, gammas=gammas, ws=ws)

    if annotate:
        _add_cell_annotations(ax, mat, fmt=fmt, norm=norm)

    if contour_levels:
        try:
            ax.contour(mat, levels=list(contour_levels), colors=contour_color, linewidths=1.2, origin="lower")
        except Exception:
            # 等值线仅是增强信息，失败就跳过
            pass

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(value_col)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_bet_hedging_triptych(
    df: pd.DataFrame,
    *,
    gammas: Sequence[float] | None = None,
    ws: Sequence[float] | None = None,
    out_path: Path,
    subtitle: str = "",
    annotate: bool = True,
) -> None:
    """一张 3 子图：P_ext / P_host / mean_H（bet-hedging 主图）。

    为了更适合写进论文：
    - 增加格子网格线
    - 默认在格子中心标注数值（小网格时非常直观）
    """
    sub = df[df["p_m_override"].isna()].copy()
    if sub.empty:
        raise ValueError("未找到 S_var 行（p_m_override 全部非空）")

    if gammas is None:
        gammas = _as_sorted_unique(sub["gamma"].tolist())
    if ws is None:
        ws = _as_sorted_unique(sub["w"].tolist())

    def grid(col: str) -> np.ndarray:
        piv = sub.pivot_table(index="w", columns="gamma", values=col, aggfunc="mean")
        piv = piv.reindex(index=list(ws), columns=list(gammas))
        return piv.to_numpy(dtype=float)

    mats = {
        "P_ext": grid("P_ext"),
        "P_host": grid("P_host"),
        "mean_H": grid("mean_H"),
    }

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True)
    for ax, (col, mat) in zip(axes, mats.items()):
        if col.startswith("P_"):
            cmap = "Reds"
            norm = Normalize(vmin=0.0, vmax=1.0)
            fmt = "{:.2f}"
        else:
            cmap = "viridis"
            norm = None
            fmt = "{:.2f}"

        im = ax.imshow(mat, origin="lower", aspect="auto", cmap=cmap, norm=norm)
        ax.set_title(col)
        ax.set_xlabel("gamma（敏感度）")
        ax.set_ylabel("w（年）")
        _set_heatmap_axes(ax, gammas=gammas, ws=ws)
        if annotate and (mat.size <= 120):
            _add_cell_annotations(ax, mat, fmt=fmt, norm=norm)

        # 标出“最优格子”（风险最小/水平最大）
        if np.isfinite(mat).any():
            if col.startswith("P_"):
                idx = np.nanargmin(mat)
            else:
                idx = np.nanargmax(mat)
            i, j = np.unravel_index(int(idx), mat.shape)
            ax.scatter([j], [i], s=140, marker="*", c="black", edgecolors="white", linewidths=0.8, zorder=5)

        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    title = "bet-hedging 扫描（S_var 网格）"
    if subtitle:
        title += "\n" + subtitle
    fig.suptitle(title, fontsize=12)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_tradeoff_scatter(
    df: pd.DataFrame,
    *,
    out_path: Path,
    x_col: str = "P_host",
    y_col: str = "P_ext",
    title: str = "风险权衡（越靠左下越好）",
    annotate_top_k: int = 5,
    auto_zoom: bool = True,
) -> None:
    """画风险权衡散点图：横轴 P_host，纵轴 P_ext（双目标最小化）。

    该图通常比单纯热图更“论文友好”：直接展示策略间的帕累托权衡。
    """
    if x_col not in df.columns or y_col not in df.columns:
        raise KeyError(f"缺少列：{x_col}/{y_col}")

    d = df.copy()
    d["_is_var"] = d["p_m_override"].isna()

    # 映射 w -> marker（不同记忆长度用不同形状）
    ws = sorted({float(w) for w in d.loc[d["_is_var"], "w"].tolist()})
    markers = ["o", "s", "^", "D", "v", "P", "X", "*"]
    w_to_marker = {w: markers[i % len(markers)] for i, w in enumerate(ws)}

    fig, ax = plt.subplots(figsize=(6.4, 4.8), constrained_layout=True)

    # 可变策略：按 gamma 着色
    var = d[d["_is_var"]].copy()
    if not var.empty:
        gvals = var["gamma"].astype(float).to_numpy()
        gmin, gmax = float(np.min(gvals)), float(np.max(gvals))
        gnorm = Normalize(vmin=gmin, vmax=gmax) if gmin != gmax else Normalize(vmin=gmin - 1, vmax=gmax + 1)
        cmap = plt.get_cmap("viridis")

        for w in ws:
            sub = var[var["w"].astype(float) == float(w)]
            if sub.empty:
                continue
            ax.scatter(
                sub[x_col],
                sub[y_col],
                s=70,
                marker=w_to_marker[w],
                c=cmap(gnorm(sub["gamma"].astype(float).to_numpy())),
                edgecolors="black",
                linewidths=0.4,
                alpha=0.95,
                label=f"w={w}",
            )

        sm = plt.cm.ScalarMappable(norm=gnorm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("gamma（敏感度）")

    # 固定策略：黑色大叉号
    fix = d[~d["_is_var"]].copy()
    if not fix.empty:
        ax.scatter(fix[x_col], fix[y_col], s=110, marker="X", c="black", label="固定性别比")
        for _, r in fix.iterrows():
            ax.annotate(str(r["strategy"]), (float(r[x_col]), float(r[y_col])), xytext=(5, 4), textcoords="offset points", fontsize=8)

    ax.set_title(title)
    ax.set_xlabel(f"{x_col}（宿主越界概率）")
    ax.set_ylabel(f"{y_col}（七鳃鳗准灭绝概率）")
    if auto_zoom:
        # 自动缩放：当点都挤在 0 附近时，满刻度 0~1 会显得“信息匮乏”
        xs_all = d[x_col].astype(float).to_numpy()
        ys_all = d[y_col].astype(float).to_numpy()
        xmax = float(np.nanmax(xs_all)) if np.isfinite(xs_all).any() else 1.0
        ymax = float(np.nanmax(ys_all)) if np.isfinite(ys_all).any() else 1.0
        xmax = min(1.0, max(0.1, xmax * 1.15 + 0.03))
        ymax = min(1.0, max(0.1, ymax * 1.15 + 0.03))
        ax.set_xlim(-0.01, xmax)
        ax.set_ylim(-0.01, ymax)
    else:
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)

    # 计算帕累托前沿（只对可变策略）
    if not var.empty:
        xs = var[x_col].astype(float).to_numpy()
        ys = var[y_col].astype(float).to_numpy()
        n = len(var)
        pareto = np.ones(n, dtype=bool)
        for i in range(n):
            if not pareto[i]:
                continue
            # 若存在 j 使得 (xj<=xi 且 yj<=yi) 且至少一个严格小，则 i 被支配
            dominated = (xs <= xs[i]) & (ys <= ys[i]) & ((xs < xs[i]) | (ys < ys[i]))
            if np.any(dominated):
                pareto[i] = False

        front = var.iloc[np.where(pareto)[0]].copy()
        ax.scatter(front[x_col], front[y_col], s=110, facecolors="none", edgecolors="red", linewidths=1.6, label="帕累托前沿")

        # 标注最靠左下的若干点（避免拥挤，只标前 K）
        front = front.assign(_score=front[x_col].astype(float) + front[y_col].astype(float)).sort_values("_score")
        for _, r in front.head(int(annotate_top_k)).iterrows():
            ax.annotate(
                f"g={r['gamma']}, w={r['w']}",
                (float(r[x_col]), float(r[y_col])),
                xytext=(6, -10),
                textcoords="offset points",
                fontsize=8,
                color="red",
            )

    ax.legend(fontsize=8, loc="upper right", frameon=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=260)
    plt.close(fig)


def plot_model0_trajectories_compare(
    t: np.ndarray,
    ys: dict[str, np.ndarray],
    *,
    R_series: np.ndarray,
    gamma_w_pm: dict[str, tuple[float, float, float | None]],
    out_path: Path,
    title: str = "",
) -> None:
    """对同一条环境序列，比较多种策略的代表性轨迹（更适合写进论文）。"""
    if t.ndim != 1:
        raise ValueError("t 需要是一维数组。")
    if not ys:
        raise ValueError("ys 不能为空。")

    years = int(len(R_series))
    if years <= 0:
        raise ValueError("R_series 不能为空。")

    # 把分段常数的 R_k 映射到每个采样点
    idx = np.floor(t).astype(int)
    idx = np.clip(idx, 0, years - 1)
    R_t = np.asarray(R_series, dtype=float)[idx]

    fig, axes = plt.subplots(4, 1, figsize=(10.8, 8.2), sharex=True, constrained_layout=True)
    axR, axH, axN, axP = axes

    # 1) 环境资源（分段常数，用阶梯线）
    axR.step(t, R_t, where="post", color="black", linewidth=1.6)
    axR.set_ylabel("R(t)")
    axR.grid(True, alpha=0.25)

    # 颜色循环
    colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["C0", "C1", "C2", "C3"])

    # 2-4) H / N / p_m 轨迹
    for k, (name, y) in enumerate(ys.items()):
        if y.ndim != 2 or y.shape[0] != len(t) or y.shape[1] < 6:
            raise ValueError(f"策略 {name} 的 y 形状不对，应为 (len(t), n_states>=6)。")

        color = colors[k % len(colors)]
        H = y[:, 0]
        N = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
        x_bar = y[:, 5]

        gamma, w, p_m_override = gamma_w_pm.get(name, (1.0, 0.0, None))
        if p_m_override is not None:
            pm = np.full_like(H, float(p_m_override), dtype=float)
        else:
            # w>0 用 x_bar；w<=0 用瞬时 x
            if w > 0:
                x_eff = np.clip(x_bar, 0.0, 1.0)
            else:
                x_eff = np.array([x_from_resource(R=float(r), L=float(l), K_u=1.0, eps_L=1e-9) for r, l in zip(R_t, y[:, 1])])
            pm = np.array([male_fraction(float(xe), float(gamma)) for xe in x_eff], dtype=float)

        axH.plot(t, H, label=name, color=color, linewidth=1.8, alpha=0.95)
        axN.plot(t, N, label=name, color=color, linewidth=1.8, alpha=0.95)
        axP.plot(t, pm, label=name, color=color, linewidth=1.8, alpha=0.95)

    axH.set_ylabel("H(t)")
    axH.grid(True, alpha=0.25)
    axN.set_ylabel("N(t)")
    axN.grid(True, alpha=0.25)
    axP.set_ylabel("p_m(t)")
    axP.set_xlabel("t（年）")
    axP.set_ylim(0.48, 0.82)
    axP.grid(True, alpha=0.25)

    if title:
        fig.suptitle(title, fontsize=12)

    # 合并图例（放在最后一行右上角）
    axP.legend(fontsize=8, ncol=2, loc="upper right", frameon=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=260)
    plt.close(fig)


def plot_model0_trajectories_compare_timevarying(
    t: np.ndarray,
    ys: dict[str, np.ndarray],
    *,
    R_t: np.ndarray,
    gamma_w_pm: dict[str, tuple[float, float, float | None]],
    out_path: Path,
    title: str = "",
) -> None:
    """连续时间变资源 R(t) 下的策略轨迹对比（适合季节项）。"""
    if t.ndim != 1:
        raise ValueError("t 需要是一维数组。")
    R_t = np.asarray(R_t, dtype=float)
    if R_t.shape != t.shape:
        raise ValueError("R_t 需要与 t 同长度。")
    if not ys:
        raise ValueError("ys 不能为空。")

    fig, axes = plt.subplots(4, 1, figsize=(10.8, 8.2), sharex=True, constrained_layout=True)
    axR, axH, axN, axP = axes

    axR.plot(t, R_t, color="black", linewidth=1.6)
    axR.set_ylabel("R(t)")
    axR.grid(True, alpha=0.25)

    colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["C0", "C1", "C2", "C3"])

    for k, (name, y) in enumerate(ys.items()):
        if y.ndim != 2 or y.shape[0] != len(t) or y.shape[1] < 6:
            raise ValueError(f"策略 {name} 的 y 形状不对，应为 (len(t), n_states>=6)。")

        color = colors[k % len(colors)]
        H = y[:, 0]
        N = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
        x_bar = y[:, 5]

        gamma, w, p_m_override = gamma_w_pm.get(name, (1.0, 0.0, None))
        if p_m_override is not None:
            pm = np.full_like(H, float(p_m_override), dtype=float)
        else:
            if w > 0:
                x_eff = np.clip(x_bar, 0.0, 1.0)
            else:
                x_eff = np.array(
                    [x_from_resource(R=float(r), L=float(l), K_u=1.0, eps_L=1e-9) for r, l in zip(R_t, y[:, 1])],
                    dtype=float,
                )
            pm = np.array([male_fraction(float(xe), float(gamma)) for xe in x_eff], dtype=float)

        axH.plot(t, H, label=name, color=color, linewidth=1.8, alpha=0.95)
        axN.plot(t, N, label=name, color=color, linewidth=1.8, alpha=0.95)
        axP.plot(t, pm, label=name, color=color, linewidth=1.8, alpha=0.95)

    axH.set_ylabel("H(t)")
    axH.grid(True, alpha=0.25)
    axN.set_ylabel("N(t)")
    axN.grid(True, alpha=0.25)
    axP.set_ylabel("p_m(t)")
    axP.set_xlabel("t（年）")
    axP.set_ylim(0.48, 0.82)
    axP.grid(True, alpha=0.25)

    if title:
        fig.suptitle(title, fontsize=12)

    axP.legend(fontsize=8, ncol=2, loc="upper right", frameon=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=260)
    plt.close(fig)


def plot_triad_trajectories_compare(
    t: np.ndarray,
    ys: dict[str, np.ndarray],
    *,
    R_series: np.ndarray,
    gamma_w_pm: dict[str, tuple[float, float, float | None]],
    out_path: Path,
    title: str = "",
) -> None:
    """三元系统（含 B）代表性轨迹图：R/H/N/p_m/B。"""
    if t.ndim != 1:
        raise ValueError("t 需要是一维数组。")
    if not ys:
        raise ValueError("ys 不能为空。")

    years = int(len(R_series))
    if years <= 0:
        raise ValueError("R_series 不能为空。")

    idx = np.floor(t).astype(int)
    idx = np.clip(idx, 0, years - 1)
    R_t = np.asarray(R_series, dtype=float)[idx]

    fig, axes = plt.subplots(5, 1, figsize=(10.8, 9.6), sharex=True, constrained_layout=True)
    axR, axH, axN, axP, axB = axes

    axR.step(t, R_t, where="post", color="black", linewidth=1.6)
    axR.set_ylabel("R(t)")
    axR.grid(True, alpha=0.25)

    colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["C0", "C1", "C2", "C3"])

    for k, (name, y) in enumerate(ys.items()):
        if y.ndim != 2 or y.shape[0] != len(t) or y.shape[1] < 7:
            raise ValueError(f"策略 {name} 的 y 形状不对，应为 (len(t), n_states>=7)。")

        color = colors[k % len(colors)]
        H = y[:, 0]
        N = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
        x_bar = y[:, 5]

        gamma, w, p_m_override = gamma_w_pm.get(name, (1.0, 0.0, None))
        if p_m_override is not None:
            pm = np.full_like(H, float(p_m_override), dtype=float)
        else:
            x_eff = np.clip(x_bar, 0.0, 1.0) if w > 0 else np.array(
                [x_from_resource(R=float(r), L=float(l), K_u=1.0, eps_L=1e-9) for r, l in zip(R_t, y[:, 1])],
                dtype=float,
            )
            pm = np.array([male_fraction(float(xe), float(gamma)) for xe in x_eff], dtype=float)

        axH.plot(t, H, label=name, color=color, linewidth=1.8, alpha=0.95)
        axN.plot(t, N, label=name, color=color, linewidth=1.8, alpha=0.95)
        axP.plot(t, pm, label=name, color=color, linewidth=1.8, alpha=0.95)

        # B：model1/2 有一个 B（index=6）；model3 额外有第二个 B（index=7）
        axB.plot(t, y[:, 6], label=f"{name}-B1", color=color, linewidth=1.6, alpha=0.95)
        if y.shape[1] >= 8:
            axB.plot(t, y[:, 7], label=f"{name}-B2", color=color, linewidth=1.6, alpha=0.95, linestyle="--")

    axH.set_ylabel("H(t)")
    axH.grid(True, alpha=0.25)
    axN.set_ylabel("N(t)")
    axN.grid(True, alpha=0.25)
    axP.set_ylabel("p_m(t)")
    axP.set_ylim(0.48, 0.82)
    axP.grid(True, alpha=0.25)
    axB.set_ylabel("B(t)")
    axB.set_xlabel("t（年）")
    axB.grid(True, alpha=0.25)

    if title:
        fig.suptitle(title, fontsize=12)

    # 图例放在最后（避免遮挡）
    axB.legend(fontsize=8, ncol=2, loc="upper right", frameon=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=260)
    plt.close(fig)
