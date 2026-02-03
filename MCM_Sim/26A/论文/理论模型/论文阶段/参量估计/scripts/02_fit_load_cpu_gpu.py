#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02 负载–CPU/GPU功耗：从 AndroWatts（aggregated.csv）抽取并拟合参数。

输出位置：
- `.../参量估计/02-负载-CPU_GPU功耗/`

核心思路：
- “负载”在公开数据中不可直接观测，这里使用 CPU/GPU 频率作为 proxy（可解释、可复现）；
- 用 power-rails 的 CPU/GPU 聚合功耗作为观测功耗；
- 拟合 Model-0 的线性关系（P = k*load），并提供可选的超线性（P = k*load^gamma）诊断。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from _common import PROJECT_DIR, ensure_dir, finite_rows, linear_fit_through_origin, summarize_fit, to_repo_path, write_csv, write_text

from mcm26a.observed.andro_watts import load_aggregated_csv
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _cpu_load_from_freq(row: pd.Series) -> float:
    """按项目既有口径，从 big/mid/little 频率构造 cpu_load∈[0,1]。"""

    cpu_big = float(row.get("CPU_big", 0.0) or 0.0)
    cpu_mid = float(row.get("CPU_mid", 0.0) or 0.0)
    cpu_lit = float(row.get("CPU_little", 0.0) or 0.0)

    max_big = 2_900_000.0
    max_mid = 4_650_000.0
    max_lit = 1_800_000.0

    nb = float(min(1.0, max(0.0, cpu_big / max_big)))
    nm = float(min(1.0, max(0.0, cpu_mid / max_mid)))
    nl = float(min(1.0, max(0.0, cpu_lit / max_lit)))
    return float(min(1.0, 0.60 * nb + 0.30 * nm + 0.10 * nl))


def _gpu_load_from_freq(row: pd.Series) -> float:
    gpu0 = float(row.get("GPU0", 0.0) or 0.0)
    gpu1 = float(row.get("GPU1", 0.0) or 0.0)
    max_gpu0 = 900_000.0
    max_gpu1 = 900_000.0
    u0 = float(min(1.0, max(0.0, gpu0 / max_gpu0)))
    u1 = float(min(1.0, max(0.0, gpu1 / max_gpu1)))
    return float(max(u0, u1))


def _sum_uW(row: pd.Series, cols: list[str]) -> float:
    s = 0.0
    for c in cols:
        v = row.get(c, 0.0)
        try:
            v = float(v)
        except Exception:
            v = 0.0
        if not np.isfinite(v):
            v = 0.0
        s += float(v)
    return float(s)


def _pow_model(u: np.ndarray, k: float, gamma: float) -> np.ndarray:
    u = np.asarray(u, dtype=float)
    u = np.clip(u, 0.0, 1.0)
    return k * (u ** gamma)


def main() -> None:
    out_dir = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / "02-负载-CPU_GPU功耗"
    ensure_dir(out_dir)

    src_path = Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"
    df = load_aggregated_csv(src_path)

    cpu_cols = [
        "CPU_BIG_ENERGY_AVG_UWS",
        "CPU_MID_ENERGY_AVG_UWS",
        "CPU_LITTLE_ENERGY_AVG_UWS",
        "S9M_VDD_CPUCL0_M_ENERGY_AVG_UWS",
        "TPU_ENERGY_AVG_UWS",
    ]
    gpu_cols = ["GPU3D_ENERGY_AVG_UWS", "GPU_ENERGY_AVG_UWS"]

    rows = []
    for _, row in df.iterrows():
        cpu_load = _cpu_load_from_freq(row)
        gpu_load = _gpu_load_from_freq(row)

        p_cpu_W = _sum_uW(row, cpu_cols) * 1e-6
        p_gpu_W = _sum_uW(row, gpu_cols) * 1e-6

        rows.append(
            {
                "phone_test_id": int(row.get("ID", -1) or -1),
                "cpu_load": cpu_load,
                "gpu_load": gpu_load,
                "obs_cpu_w": float(p_cpu_W),
                "obs_gpu_w": float(p_gpu_W),
            }
        )

    data = pd.DataFrame(rows)
    # 过滤合理范围（避免极少数异常值）
    data = data[(data["obs_cpu_w"] >= 0.0) & (data["obs_cpu_w"] < 8.0)]
    data = data[(data["obs_gpu_w"] >= 0.0) & (data["obs_gpu_w"] < 8.0)]
    data_path = out_dir / "data.csv"
    data.to_csv(data_path, index=False, encoding="utf-8")

    # --- CPU：拟合 P = k * load（过原点，更贴近 Model-0 的参数形式）
    cpu_mask = finite_rows(data["cpu_load"], data["obs_cpu_w"]) & (data["cpu_load"] > 0.02)
    u_cpu = data.loc[cpu_mask, "cpu_load"].to_numpy()
    p_cpu = data.loc[cpu_mask, "obs_cpu_w"].to_numpy()
    k_cpu = linear_fit_through_origin(u_cpu, p_cpu)
    p_cpu_hat = k_cpu * u_cpu
    cpu_summ = summarize_fit(p_cpu, p_cpu_hat)

    # 诊断：拟合超线性 P = k * load^gamma（仅用于论文“可解释增强”讨论）
    k_cpu_nl = float("nan")
    g_cpu_nl = float("nan")
    cpu_summ_nl = None
    if len(u_cpu) >= 200:
        try:
            popt, pcov = curve_fit(
                _pow_model,
                u_cpu,
                p_cpu,
                p0=[max(1e-6, float(np.median(p_cpu) / max(1e-6, np.median(u_cpu)))), 1.2],
                bounds=([0.0, 0.2], [50.0, 3.0]),
                maxfev=20_000,
            )
            k_cpu_nl, g_cpu_nl = float(popt[0]), float(popt[1])
            p_hat = _pow_model(u_cpu, k_cpu_nl, g_cpu_nl)
            cpu_summ_nl = summarize_fit(p_cpu, p_hat)
        except Exception:
            cpu_summ_nl = None

    # --- GPU：同理
    gpu_mask = finite_rows(data["gpu_load"], data["obs_gpu_w"]) & (data["gpu_load"] > 0.02)
    u_gpu = data.loc[gpu_mask, "gpu_load"].to_numpy()
    p_gpu = data.loc[gpu_mask, "obs_gpu_w"].to_numpy()
    k_gpu = linear_fit_through_origin(u_gpu, p_gpu)
    p_gpu_hat = k_gpu * u_gpu
    gpu_summ = summarize_fit(p_gpu, p_gpu_hat)

    k_gpu_nl = float("nan")
    g_gpu_nl = float("nan")
    gpu_summ_nl = None
    if len(u_gpu) >= 200:
        try:
            popt, pcov = curve_fit(
                _pow_model,
                u_gpu,
                p_gpu,
                p0=[max(1e-6, float(np.median(p_gpu) / max(1e-6, np.median(u_gpu)))), 1.2],
                bounds=([0.0, 0.2], [50.0, 3.0]),
                maxfev=20_000,
            )
            k_gpu_nl, g_gpu_nl = float(popt[0]), float(popt[1])
            p_hat = _pow_model(u_gpu, k_gpu_nl, g_gpu_nl)
            gpu_summ_nl = summarize_fit(p_gpu, p_hat)
        except Exception:
            gpu_summ_nl = None

    # 写拟合表
    fit_rows = [
        {
            "component": "CPU",
            "model": "linear_through_origin",
            "equation": "P = k * load",
            "n": cpu_summ.n,
            "k_W": k_cpu,
            "r2": cpu_summ.r2,
            "rmse_W": cpu_summ.rmse,
            "load_proxy": "CPU freq proxy (0.60*big+0.30*mid+0.10*little, normalized)",
            "power_cols": "+".join(cpu_cols),
            "data_source": to_repo_path(src_path),
        },
        {
            "component": "GPU",
            "model": "linear_through_origin",
            "equation": "P = k * load",
            "n": gpu_summ.n,
            "k_W": k_gpu,
            "r2": gpu_summ.r2,
            "rmse_W": gpu_summ.rmse,
            "load_proxy": "GPU freq proxy (max(gpu0,gpu1), normalized)",
            "power_cols": "+".join(gpu_cols),
            "data_source": to_repo_path(src_path),
        },
    ]
    if cpu_summ_nl is not None:
        fit_rows.append(
            {
                "component": "CPU",
                "model": "powerlaw_diagnostic",
                "equation": "P = k * load^gamma",
                "n": cpu_summ_nl.n,
                "k_W": k_cpu_nl,
                "gamma": g_cpu_nl,
                "r2": cpu_summ_nl.r2,
                "rmse_W": cpu_summ_nl.rmse,
            }
        )
    if gpu_summ_nl is not None:
        fit_rows.append(
            {
                "component": "GPU",
                "model": "powerlaw_diagnostic",
                "equation": "P = k * load^gamma",
                "n": gpu_summ_nl.n,
                "k_W": k_gpu_nl,
                "gamma": g_gpu_nl,
                "r2": gpu_summ_nl.r2,
                "rmse_W": gpu_summ_nl.rmse,
            }
        )

    write_csv(out_dir / "fit_results.csv", fit_rows)

    about = f"""# 02 负载–CPU/GPU功耗（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`{to_repo_path(src_path)}`
  - CPU 频率：`CPU_LITTLE_FREQ_KHz/CPU_MID_FREQ_KHz/CPU_BIG_FREQ_KHz`
  - GPU 频率：`GPU0_FREQ/GPU_1FREQ/GPU_MEM_AVG`（本拟合用前两者）
  - CPU 功耗 rail：{', '.join(cpu_cols)}
  - GPU 功耗 rail：{', '.join(gpu_cols)}

## 负载 proxy（可解释口径）

公开数据中没有“真实任务负载”，但存在 CPU/GPU 频率。我们采用可复现的 proxy：

- CPU：
  - 归一化后按簇加权：`load = 0.60*big + 0.30*mid + 0.10*little`（并裁剪到 0~1）
- GPU：
  - `load = max(gpu0, gpu1)` 归一化（裁剪到 0~1）

## 拟合模型

主模型（用于回填 Model-0 参数）：
- `P = k * load`（过原点拟合）

诊断模型（用于论文讨论“超线性/非线性”可能性）：
- `P = k * load^gamma`

## 产物

- `data.csv`：干净样本表（含 cpu_load/gpu_load 与观测功耗）
- `fit_results.csv`：参数与误差（R2/RMSE）
- `figure_paper.png`/`figure_study.png`：论文版/学习版图
"""
    write_text(out_dir / "about.md", about)

    # 出图：CPU/GPU 两个子图
    import matplotlib.pyplot as plt

    for mode in ["paper", "study"]:
        style = apply_style(mode)
        fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.0), sharey=False)

        # CPU
        ax = axes[0]
        if mode == "paper":
            ax.scatter(u_cpu, p_cpu, s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[0], edgecolors="none")
        else:
            ax.scatter(data["cpu_load"], data["obs_cpu_w"], s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[0], edgecolors="none")
        xs = np.linspace(0, 1, 200)
        ax.plot(xs, k_cpu * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="P=k*load")
        ax.set_title(f"CPU：负载-功耗{style.title_suffix}")
        ax.set_xlabel("CPU 负载（0-1，频率 proxy）")
        ax.set_ylabel("CPU 功耗（W）")
        ax.legend(loc="upper left", frameon=False)
        if style.annotate:
            ax.text(
                0.02,
                0.98,
                f"n={cpu_summ.n}\\n"
                f"k={k_cpu:.3f} W\\n"
                f"R²={cpu_summ.r2:.3f}, RMSE={cpu_summ.rmse:.3f}W",
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox={"fc": "white", "ec": "none", "alpha": 0.75},
            )

        # GPU
        ax = axes[1]
        if mode == "paper":
            ax.scatter(u_gpu, p_gpu, s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[1], edgecolors="none")
        else:
            ax.scatter(data["gpu_load"], data["obs_gpu_w"], s=14, alpha=0.18, color=PALETTE_SKIP_GRADIENT[1], edgecolors="none")
        ax.plot(xs, k_gpu * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="P=k*load")
        ax.set_title(f"GPU：负载-功耗{style.title_suffix}")
        ax.set_xlabel("GPU 负载（0-1，频率 proxy）")
        ax.set_ylabel("GPU 功耗（W）")
        ax.legend(loc="upper left", frameon=False)
        if style.annotate:
            ax.text(
                0.02,
                0.98,
                f"n={gpu_summ.n}\\n"
                f"k={k_gpu:.3f} W\\n"
                f"R²={gpu_summ.r2:.3f}, RMSE={gpu_summ.rmse:.3f}W",
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox={"fc": "white", "ec": "none", "alpha": 0.75},
            )

        fig.suptitle(f"AndroWatts：负载–CPU/GPU功耗关系{style.title_suffix}")
        savefig(fig, out_dir / f"figure_{mode}.png", mode=mode)
        plt.close(fig)


if __name__ == "__main__":
    main()
