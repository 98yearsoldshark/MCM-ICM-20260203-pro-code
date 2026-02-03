#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成“参量估计”章节的英文论文版图片：figure_paper_en.png

说明：
- 不覆盖原有中文图片（figure_paper.png / figure_study.png）。
- 英文版仅生成 paper 风格（简洁、可直接插论文）。
- 本脚本只依赖各子目录已生成的 data.csv 与 fit_results.csv；不会重跑拟合。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR

from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _param_dir(name: str) -> Path:
    return Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / name


def _make_01_brightness_screen() -> None:
    import matplotlib.pyplot as plt

    out_dir = _param_dir("01-亮度-屏幕功耗")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv")
    row = fit[fit["model"] == "linear_brightness"].iloc[0]
    p0 = float(row["P0_W"])
    k = float(row["k_W_per_nit"])

    x = data["brightness_nits"].to_numpy(dtype=float)
    y = data["obs_screen_w"].to_numpy(dtype=float)

    data2 = data.copy()
    data2["bin"] = pd.cut(data2["brightness_nits"], bins=12)
    grp = data2.groupby("bin", observed=True)
    b_mid = grp["brightness_nits"].median().to_numpy()
    y_med = grp["obs_screen_w"].median().to_numpy()
    y_q25 = grp["obs_screen_w"].quantile(0.25).to_numpy()
    y_q75 = grp["obs_screen_w"].quantile(0.75).to_numpy()

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.fill_between(b_mid, y_q25, y_q75, color=PALETTE_SKIP_GRADIENT[1], alpha=0.25, linewidth=0)
    ax.plot(b_mid, y_med, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.0, label="Binned median (IQR)")

    xs = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 200)
    ax.plot(xs, p0 + k * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="Linear fit: P0 + k·nits")

    ax.set_title("Brightness vs Screen Power (AndroWatts)")
    ax.set_xlabel("Screen brightness (nits)")
    ax.set_ylabel("Screen power (W)")
    ax.legend(loc="best", frameon=False)

    savefig(fig, out_dir / "figure_paper_en.png", mode="paper")
    plt.close(fig)


def _make_02_load_cpu_gpu() -> None:
    import matplotlib.pyplot as plt

    out_dir = _param_dir("02-负载-CPU_GPU功耗")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv")

    k_cpu = float(fit[(fit["component"] == "CPU") & (fit["model"] == "linear_through_origin")].iloc[0]["k_W"])
    k_gpu = float(fit[(fit["component"] == "GPU") & (fit["model"] == "linear_through_origin")].iloc[0]["k_W"])

    cpu_mask = np.isfinite(data["cpu_load"]) & np.isfinite(data["obs_cpu_w"]) & (data["cpu_load"] > 0.02)
    gpu_mask = np.isfinite(data["gpu_load"]) & np.isfinite(data["obs_gpu_w"]) & (data["gpu_load"] > 0.02)
    u_cpu = data.loc[cpu_mask, "cpu_load"].to_numpy(dtype=float)
    p_cpu = data.loc[cpu_mask, "obs_cpu_w"].to_numpy(dtype=float)
    u_gpu = data.loc[gpu_mask, "gpu_load"].to_numpy(dtype=float)
    p_gpu = data.loc[gpu_mask, "obs_gpu_w"].to_numpy(dtype=float)

    apply_style("paper")
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.0), sharey=False)
    xs = np.linspace(0.0, 1.0, 200)

    ax = axes[0]
    ax.scatter(u_cpu, p_cpu, s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[0], edgecolors="none")
    ax.plot(xs, k_cpu * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="P = k·load")
    ax.set_title("CPU: Load vs Power")
    ax.set_xlabel("CPU load (0–1, frequency proxy)")
    ax.set_ylabel("CPU power (W)")
    ax.legend(loc="upper left", frameon=False)

    ax = axes[1]
    ax.scatter(u_gpu, p_gpu, s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[1], edgecolors="none")
    ax.plot(xs, k_gpu * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="P = k·load")
    ax.set_title("GPU: Load vs Power")
    ax.set_xlabel("GPU load (0–1, frequency proxy)")
    ax.set_ylabel("GPU power (W)")
    ax.legend(loc="upper left", frameon=False)

    fig.suptitle("AndroWatts: Load vs CPU/GPU Power")
    savefig(fig, out_dir / "figure_paper_en.png", mode="paper")
    plt.close(fig)


def _make_03_network_tail() -> None:
    import matplotlib.pyplot as plt

    out_dir = _param_dir("03-网络回落曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]

    P_idle = float(fit["P_idle_W"])
    e_per_mb = float(fit["e_per_mb_J"])
    P_conn = float(fit["P_conn_W_est"])
    tau_tail = float(fit["tau_tail_s_est"])

    thr = data["throughput_MBps"].to_numpy(dtype=float)
    p_radio = data["P_radio_W"].to_numpy(dtype=float)
    dur = data["duration_s_est"].to_numpy(dtype=float)

    t_grid = np.linspace(0.0, 60.0, 300)
    p_tail = P_idle + (P_conn - P_idle) * np.exp(-t_grid / max(1e-6, tau_tail))

    apply_style("paper")
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.2))

    ax = axes[0]
    sc = ax.scatter(thr, p_radio, c=dur, s=16, alpha=0.30, cmap="viridis", edgecolors="none")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("Test duration t (s)")
    xs = np.linspace(0.0, float(np.nanmax(thr)), 200)
    ax.plot(xs, P_idle + e_per_mb * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="No-tail baseline: P_idle + e·thr")
    ax.set_title("Radio power vs throughput (colored by duration)")
    ax.set_xlabel("Average Wi-Fi throughput (MB/s)")
    ax.set_ylabel("Mean radio power (W)")
    ax.legend(loc="upper left", frameon=False)

    ax = axes[1]
    ax.plot(t_grid, p_tail, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.6, label="Equivalent tail curve (exp)")
    ax.hlines(P_idle, xmin=0.0, xmax=float(t_grid.max()), color=PALETTE_SKIP_GRADIENT[2], linewidth=2.0, linestyles="--", label="P_idle")
    ax.set_title("Tail decay (equivalent tau)")
    ax.set_xlabel("Time since transfer ends (s)")
    ax.set_ylabel("Radio power P_radio (W)")
    ax.legend(loc="upper right", frameon=False)

    fig.suptitle("AndroWatts: Network tail parameter estimation (energy balance)")
    savefig(fig, out_dir / "figure_paper_en.png", mode="paper")
    plt.close(fig)


def _make_04_throughput_power() -> None:
    import matplotlib.pyplot as plt

    out_dir = _param_dir("04-吞吐-功耗关系")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]
    p0 = float(fit["P_idle_W"])
    e = float(fit["e_per_mb_J"])

    # 与原脚本保持一致：只用非零吞吐分箱展示；拟合点 thr>0.005
    data2 = data.copy()
    data2 = data2[data2["throughput_MBps"] > 0.0].copy()
    data2["bin"] = pd.cut(data2["throughput_MBps"], bins=12)
    grp = data2.groupby("bin", observed=True)
    x_mid = grp["throughput_MBps"].median().to_numpy()
    y_med = grp["obs_radio_w"].median().to_numpy()
    y_q25 = grp["obs_radio_w"].quantile(0.25).to_numpy()
    y_q75 = grp["obs_radio_w"].quantile(0.75).to_numpy()

    fit_data = data[data["throughput_MBps"] > 0.005].copy()
    x_fit = fit_data["throughput_MBps"].to_numpy(dtype=float)

    apply_style("paper")
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.fill_between(x_mid, y_q25, y_q75, color=PALETTE_SKIP_GRADIENT[1], alpha=0.25, linewidth=0)
    ax.plot(x_mid, y_med, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.0, label="Binned median (IQR)")

    xs = np.linspace(0.0, float(np.nanmax(x_fit)), 200)
    ax.plot(xs, p0 + e * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="Linear fit")

    ax.set_title("Throughput vs Radio Power (AndroWatts, Wi-Fi)")
    ax.set_xlabel("Average Wi-Fi throughput (MB/s)")
    ax.set_ylabel("Radio power (W)")
    ax.legend(loc="best", frameon=False)

    savefig(fig, out_dir / "figure_paper_en.png", mode="paper")
    plt.close(fig)


def _make_05_temperature_time() -> None:
    import matplotlib.pyplot as plt

    out_dir = _param_dir("05-温度-时间曲线")
    data = pd.read_csv(out_dir / "data.csv")
    fit = pd.read_csv(out_dir / "fit_results.csv").iloc[0]
    K = float(fit["K_etaRth_K_per_W"])
    tau_s = float(fit["tau_s"])

    P = data["P_total_W"].to_numpy(dtype=float)
    t = data["duration_s_est"].to_numpy(dtype=float)
    y = data["delta_temp_C"].to_numpy(dtype=float)

    def model_deltaT(P_arr: np.ndarray, t_arr: np.ndarray) -> np.ndarray:
        P_arr = np.asarray(P_arr, dtype=float)
        t_arr = np.asarray(t_arr, dtype=float)
        return K * P_arr * (1.0 - np.exp(-t_arr / max(1e-6, tau_s)))

    t_levels = [10.0, 30.0, 60.0, 120.0]
    p_grid = np.linspace(float(np.nanmin(P)), float(np.nanmax(P)), 200)

    apply_style("paper")
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2))

    ax = axes[0]
    sc = ax.scatter(P, y, c=t, s=16, alpha=0.30, cmap="viridis", edgecolors="none")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("Test duration t (s)")
    for i, tt in enumerate(t_levels):
        ax.plot(
            p_grid,
            model_deltaT(p_grid, np.full_like(p_grid, tt)),
            color=PALETTE_SKIP_GRADIENT[min(i, 3)],
            linewidth=2.0,
            label="Model curve (t={}s)".format(int(tt)),
        )
    ax.set_title("Fit: Temperature rise vs power and duration")
    ax.set_xlabel("Mean device power P (W)")
    ax.set_ylabel("Temperature rise ΔT (°C)")
    ax.legend(loc="upper left", frameon=False)

    ax = axes[1]
    t_grid = np.linspace(0.0, 180.0, 300)
    for i, p0 in enumerate([0.8, 1.5, 2.5, 4.0]):
        dT = model_deltaT(np.full_like(t_grid, p0), t_grid)
        ax.plot(t_grid, dT, color=PALETTE_SKIP_GRADIENT[min(i, 3)], linewidth=2.2, label="P={:.1f}W".format(p0))
    ax.set_title("Thermal response (first-order model)")
    ax.set_xlabel("Time t (s)")
    ax.set_ylabel("Temperature rise ΔT (°C)")
    ax.legend(loc="lower right", frameon=False)

    fig.suptitle("AndroWatts: Thermal parameter estimation (from ΔT statistics)")
    savefig(fig, out_dir / "figure_paper_en.png", mode="paper")
    plt.close(fig)


def main() -> None:
    _make_01_brightness_screen()
    _make_02_load_cpu_gpu()
    _make_03_network_tail()
    _make_04_throughput_power()
    _make_05_temperature_time()
    print("[ok] figure_paper_en.png 已生成（01~05）。")


if __name__ == "__main__":
    main()

