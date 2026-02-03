#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成“参量估计”额外高价值图（目前目录中没有的），同时输出中文/英文论文版（paper）两套。

命名约定（不覆盖已有 figure_paper.png）：
- 中文：extraXX_*.png
- 英文：extraXX_*_en.png

图的设计目标：
- 更硬的“证据链”与“可解释检验”，适合论文作为补强（尤其是 Q2/Q3 的机制论证）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR

from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


@dataclass(frozen=True)
class Lang:
    name: str  # "zh" or "en"

    def t(self, zh: str, en: str) -> str:
        return zh if self.name == "zh" else en


def _param_dir(name: str) -> Path:
    return Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / name


def _tight_limits(vals: np.ndarray, pad: float = 0.06) -> tuple[float, float]:
    v = np.asarray(vals, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return (0.0, 1.0)
    lo = float(np.min(v))
    hi = float(np.max(v))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return (0.0, 1.0)
    span = hi - lo
    return (lo - pad * span, hi + pad * span)


def _plot_network_tail_deltaP_invT(*, lang: Lang) -> None:
    """尾态更直接的证据：ΔP ≈ E_tail / t -> ΔP vs 1/t 近似过原点直线。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("03-网络回落曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]

    P_idle = float(fit["P_idle_W"])
    e = float(fit["e_per_mb_J"])
    E_tail = float(fit["E_tail_J"])

    t = pd.to_numeric(data["duration_s_est"], errors="coerce").to_numpy(dtype=float)
    thr = pd.to_numeric(data["throughput_MBps"], errors="coerce").to_numpy(dtype=float)
    p = pd.to_numeric(data["P_radio_W"], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(t) & np.isfinite(thr) & np.isfinite(p) & (t > 0)
    t = t[m]
    thr = thr[m]
    p = p[m]

    baseline = P_idle + e * thr
    dP = p - baseline
    inv_t = 1.0 / t

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.4))

    sc = ax.scatter(inv_t, dP, s=18, alpha=0.28, c=thr, cmap="viridis", edgecolors="none")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label(lang.t("吞吐（MB/s）", "Throughput (MB/s)"))

    xs = np.linspace(float(np.min(inv_t)), float(np.max(inv_t)), 200)
    ax.plot(xs, E_tail * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label=lang.t("理论直线：ΔP=E_tail·(1/t)", "Theory: ΔP = E_tail·(1/t)"))

    ax.set_title(
        lang.t(
            "尾态证据：平均功耗残差 ΔP 与 1/时长的线性关系",
            "Tail evidence: power residual ΔP vs 1/duration",
        )
    )
    ax.set_xlabel(lang.t("1 / 测试时长 t（1/s）", "1 / test duration t (1/s)"))
    ax.set_ylabel(lang.t("功耗残差 ΔP（W）", "Power residual ΔP (W)"))
    ax.legend(loc="upper left", frameon=False)

    out_name = "extra01_tail_deltaP_vs_invT.png" if lang.name == "zh" else "extra01_tail_deltaP_vs_invT_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def _plot_network_energy_balance_1to1(*, lang: Lang) -> None:
    """能量守恒拟合的 1:1 对照：E_obs vs E_pred。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("03-网络回落曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]

    P_idle = float(fit["P_idle_W"])
    e = float(fit["e_per_mb_J"])
    E_tail = float(fit["E_tail_J"])

    t = pd.to_numeric(data["duration_s_est"], errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(data["bytes_MB"], errors="coerce").to_numpy(dtype=float)
    E_obs = pd.to_numeric(data["E_radio_J"], errors="coerce").to_numpy(dtype=float)
    thr = pd.to_numeric(data["throughput_MBps"], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(t) & np.isfinite(b) & np.isfinite(E_obs)
    t = t[m]
    b = b[m]
    E_obs = E_obs[m]
    thr = thr[m]

    E_pred = P_idle * t + e * b + E_tail

    # 简单指标（用于图内角落）
    ee = E_pred - E_obs
    rmse = float(np.sqrt(np.mean(ee * ee))) if ee.size else float("nan")
    r = float(np.corrcoef(E_obs, E_pred)[0, 1]) if E_obs.size >= 3 else float("nan")

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.8))

    sc = ax.scatter(E_obs, E_pred, s=18, alpha=0.28, c=thr, cmap="viridis", edgecolors="none")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label(lang.t("吞吐（MB/s）", "Throughput (MB/s)"))

    lo, hi = _tight_limits(np.concatenate([E_obs, E_pred]))
    ax.plot([lo, hi], [lo, hi], color=PALETTE_SKIP_GRADIENT[3], linewidth=2.0, linestyle="--", label=lang.t("理想一致：y=x", "Ideal: y=x"))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")

    ax.set_title(lang.t("能量守恒检验：观测无线能量 vs 预测", "Energy balance check: observed vs predicted radio energy"))
    ax.set_xlabel(lang.t("观测无线能量 E_obs（J）", "Observed radio energy E_obs (J)"))
    ax.set_ylabel(lang.t("预测无线能量 E_pred（J）", "Predicted radio energy E_pred (J)"))
    ax.legend(loc="upper left", frameon=False)

    ax.text(
        0.98,
        0.02,
        lang.t(f"r={r:.2f}  RMSE={rmse:.2f}J", f"r={r:.2f}  RMSE={rmse:.2f}J"),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.85", "alpha": 0.9},
    )

    out_name = "extra02_energy_balance_1to1.png" if lang.name == "zh" else "extra02_energy_balance_1to1_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def _plot_thermal_deltaT_1to1(*, lang: Lang) -> None:
    """温升模型 1:1 对照：ΔT_obs vs ΔT_pred。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("05-温度-时间曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]

    K = float(fit["K_etaRth_K_per_W"])
    tau_s = float(fit["tau_s"])

    P = pd.to_numeric(data["P_total_W"], errors="coerce").to_numpy(dtype=float)
    t = pd.to_numeric(data["duration_s_est"], errors="coerce").to_numpy(dtype=float)
    dT_obs = pd.to_numeric(data["delta_temp_C"], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(P) & np.isfinite(t) & np.isfinite(dT_obs)
    P = P[m]
    t = t[m]
    dT_obs = dT_obs[m]

    dT_pred = K * P * (1.0 - np.exp(-t / max(1e-6, tau_s)))
    ee = dT_pred - dT_obs
    rmse = float(np.sqrt(np.mean(ee * ee))) if ee.size else float("nan")
    r = float(np.corrcoef(dT_obs, dT_pred)[0, 1]) if dT_obs.size >= 3 else float("nan")

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.scatter(dT_obs, dT_pred, s=18, alpha=0.28, color=PALETTE_SKIP_GRADIENT[0], edgecolors="none")

    lo, hi = _tight_limits(np.concatenate([dT_obs, dT_pred]))
    ax.plot([lo, hi], [lo, hi], color=PALETTE_SKIP_GRADIENT[3], linewidth=2.0, linestyle="--", label=lang.t("理想一致：y=x", "Ideal: y=x"))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")

    ax.set_title(lang.t("热模型检验：观测温升 vs 预测温升", "Thermal model check: observed vs predicted ΔT"))
    ax.set_xlabel(lang.t("观测温升 ΔT_obs（°C）", "Observed ΔT_obs (°C)"))
    ax.set_ylabel(lang.t("预测温升 ΔT_pred（°C）", "Predicted ΔT_pred (°C)"))
    ax.legend(loc="upper left", frameon=False)

    ax.text(
        0.98,
        0.02,
        lang.t(f"r={r:.2f}  RMSE={rmse:.2f}°C", f"r={r:.2f}  RMSE={rmse:.2f}°C"),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.85", "alpha": 0.9},
    )

    out_name = "extra01_deltaT_1to1.png" if lang.name == "zh" else "extra01_deltaT_1to1_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def _plot_thermal_normalized_linearity(*, lang: Lang) -> None:
    """归一化线性检验：ΔT/(1-exp(-t/τ)) ≈ K·P。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("05-温度-时间曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]

    K = float(fit["K_etaRth_K_per_W"])
    tau_s = float(fit["tau_s"])

    P = pd.to_numeric(data["P_total_W"], errors="coerce").to_numpy(dtype=float)
    t = pd.to_numeric(data["duration_s_est"], errors="coerce").to_numpy(dtype=float)
    dT = pd.to_numeric(data["delta_temp_C"], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(P) & np.isfinite(t) & np.isfinite(dT) & (P > 0) & (t > 0)
    P = P[m]
    t = t[m]
    dT = dT[m]

    denom = 1.0 - np.exp(-t / max(1e-6, tau_s))
    denom = np.clip(denom, 1e-6, None)
    y = dT / denom

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.scatter(P, y, s=18, alpha=0.28, color=PALETTE_SKIP_GRADIENT[1], edgecolors="none")

    xs = np.linspace(float(np.nanmin(P)), float(np.nanmax(P)), 200)
    ax.plot(xs, K * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label=lang.t("模型直线：K·P", "Model line: K·P"))

    ax.set_title(lang.t("线性检验：归一化温升 vs 功耗", "Linearity check: normalized ΔT vs power"))
    ax.set_xlabel(lang.t("整机平均功耗 P（W）", "Mean device power P (W)"))
    ax.set_ylabel(lang.t("ΔT / (1-exp(-t/τ))（K）", "ΔT / (1-exp(-t/τ)) (K)"))
    ax.legend(loc="upper left", frameon=False)

    out_name = "extra02_deltaT_norm_linearity.png" if lang.name == "zh" else "extra02_deltaT_norm_linearity_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def _plot_screen_heatmap_brightness_apl(*, lang: Lang) -> None:
    """屏幕功耗的二维结构：亮度×APL -> 屏幕功耗中位数热力图。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("01-亮度-屏幕功耗")
    data = pd.read_csv(out_dir / "data.csv")

    b = pd.to_numeric(data["brightness_nits"], errors="coerce")
    apl = pd.to_numeric(data["apl"], errors="coerce")
    p = pd.to_numeric(data["obs_screen_w"], errors="coerce")
    df = pd.DataFrame({"b": b, "apl": apl, "p": p}).dropna()
    df = df[(df["b"] > 1.0) & (df["apl"] >= 0.0) & (df["apl"] <= 1.0) & (df["p"] > 0.0) & (df["p"] < 2.0)].copy()

    # 分箱
    b_bins = np.linspace(float(df["b"].min()), float(df["b"].max()), 13)
    a_bins = np.linspace(0.0, 1.0, 11)
    df["b_bin"] = pd.cut(df["b"], bins=b_bins, include_lowest=True)
    df["a_bin"] = pd.cut(df["apl"], bins=a_bins, include_lowest=True)

    piv = df.groupby(["a_bin", "b_bin"], observed=True)["p"].median().unstack()
    Z = piv.to_numpy(dtype=float)

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    im = ax.imshow(Z, origin="lower", aspect="auto", cmap="viridis")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(lang.t("屏幕功耗中位数（W）", "Median screen power (W)"))

    # 轴刻度：取 bin 中心
    b_centers = 0.5 * (b_bins[:-1] + b_bins[1:])
    a_centers = 0.5 * (a_bins[:-1] + a_bins[1:])
    ax.set_xticks(np.linspace(0, len(b_centers) - 1, 6))
    ax.set_xticklabels(["{:.0f}".format(x) for x in np.linspace(float(b_centers.min()), float(b_centers.max()), 6)])
    ax.set_yticks(np.linspace(0, len(a_centers) - 1, 6))
    ax.set_yticklabels(["{:.1f}".format(y) for y in np.linspace(0.0, 1.0, 6)])

    ax.set_title(lang.t("屏幕功耗二维结构：亮度 × APL", "Screen power surface: brightness × APL"))
    ax.set_xlabel(lang.t("屏幕亮度（nits）", "Brightness (nits)"))
    ax.set_ylabel(lang.t("APL（内容平均亮度，0-1）", "APL (avg picture level, 0–1)"))

    out_name = "extra01_screen_heatmap_brightness_apl.png" if lang.name == "zh" else "extra01_screen_heatmap_brightness_apl_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def _plot_cpu_gpu_loglog(*, lang: Lang) -> None:
    """CPU/GPU 的超线性证据：log-log 轴展示 power-law 拟合（诊断用）。"""

    import matplotlib.pyplot as plt

    out_dir = _param_dir("02-负载-CPU_GPU功耗")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv")

    # 诊断行（若缺失则直接跳过）
    cpu_row = fit[(fit.get("component") == "CPU") & (fit.get("model") == "powerlaw_diagnostic")]
    gpu_row = fit[(fit.get("component") == "GPU") & (fit.get("model") == "powerlaw_diagnostic")]
    if cpu_row.empty or gpu_row.empty:
        return

    k_cpu = float(cpu_row.iloc[0]["k_W"])
    g_cpu = float(cpu_row.iloc[0]["gamma"])
    k_gpu = float(gpu_row.iloc[0]["k_W"])
    g_gpu = float(gpu_row.iloc[0]["gamma"])

    u_cpu = pd.to_numeric(data["cpu_load"], errors="coerce").to_numpy(dtype=float)
    p_cpu = pd.to_numeric(data["obs_cpu_w"], errors="coerce").to_numpy(dtype=float)
    u_gpu = pd.to_numeric(data["gpu_load"], errors="coerce").to_numpy(dtype=float)
    p_gpu = pd.to_numeric(data["obs_gpu_w"], errors="coerce").to_numpy(dtype=float)

    m_cpu = np.isfinite(u_cpu) & np.isfinite(p_cpu) & (u_cpu > 0.02) & (p_cpu > 1e-3)
    m_gpu = np.isfinite(u_gpu) & np.isfinite(p_gpu) & (u_gpu > 0.02) & (p_gpu > 1e-3)

    apply_style("paper")
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.0))

    xs = np.logspace(np.log10(0.02), 0.0, 200)

    ax = axes[0]
    ax.scatter(u_cpu[m_cpu], p_cpu[m_cpu], s=14, alpha=0.20, color=PALETTE_SKIP_GRADIENT[0], edgecolors="none")
    ax.plot(xs, k_cpu * (xs ** g_cpu), color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label=lang.t("幂律拟合", "Power-law fit"))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(lang.t("CPU：log-log 诊断", "CPU: log-log diagnostic"))
    ax.set_xlabel(lang.t("CPU 负载（log）", "CPU load (log)"))
    ax.set_ylabel(lang.t("CPU 功耗（W，log）", "CPU power (W, log)"))
    ax.legend(loc="lower right", frameon=False)

    ax = axes[1]
    ax.scatter(u_gpu[m_gpu], p_gpu[m_gpu], s=14, alpha=0.20, color=PALETTE_SKIP_GRADIENT[1], edgecolors="none")
    ax.plot(xs, k_gpu * (xs ** g_gpu), color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label=lang.t("幂律拟合", "Power-law fit"))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(lang.t("GPU：log-log 诊断", "GPU: log-log diagnostic"))
    ax.set_xlabel(lang.t("GPU 负载（log）", "GPU load (log)"))
    ax.set_ylabel(lang.t("GPU 功耗（W，log）", "GPU power (W, log)"))
    ax.legend(loc="lower right", frameon=False)

    fig.suptitle(lang.t("AndroWatts：CPU/GPU 超线性证据（幂律诊断）", "AndroWatts: CPU/GPU superlinearity (power-law diagnostic)"))

    out_name = "extra01_cpu_gpu_loglog.png" if lang.name == "zh" else "extra01_cpu_gpu_loglog_en.png"
    savefig(fig, out_dir / out_name, mode="paper")
    plt.close(fig)


def main() -> None:
    for lang in [Lang("zh"), Lang("en")]:
        _plot_screen_heatmap_brightness_apl(lang=lang)
        _plot_cpu_gpu_loglog(lang=lang)
        _plot_network_tail_deltaP_invT(lang=lang)
        _plot_network_energy_balance_1to1(lang=lang)
        _plot_thermal_deltaT_1to1(lang=lang)
        _plot_thermal_normalized_linearity(lang=lang)

    print("[ok] 参量估计 extra 图（中英）已生成。")


if __name__ == "__main__":
    main()

