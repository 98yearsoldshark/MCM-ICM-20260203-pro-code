#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05 温度-时间曲线：用 AndroWatts 的温升统计量反推一阶热模型参数，并生成温度响应曲线。

为什么这么做：
- 我们仓库目前没有可直接解析 perfetto trace 的依赖（perfetto TraceProcessor 未安装），
  因此无法从 `.perfetto-trace` 直接导出 T(t)。
- 但 AndroWatts 的 aggregated.csv 已给出：
  - 平均温度 `AVG_SOC_TEMP`（m°C）
  - 首尾差 `DIFF_SOC_TEMP`（m°C）
  - 以及各 rail 平均功率 proxy（*_ENERGY_AVG_UWS）
  - 还可由 (ENERGY_UW)/(ENERGY_AVG_UWS) 估计测试时长

因此我们采用“温升-功耗-时长”的可解释拟合来估计热模型的关键量级：

  ΔT ≈ (η * R_th) * P * (1 - exp(-t/τ)),   τ = R_th * C_th

输出：
- `.../参量估计/05-温度-时间曲线/` 下生成 data/fit/图与来源说明。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from _common import PROJECT_DIR, ensure_dir, r2_score, rmse, to_repo_path, write_csv, write_text

from mcm26a.observed.andro_watts import estimate_duration_s, load_aggregated_csv
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _to_float(v) -> float:
    try:
        x = float(v)
    except Exception:
        return float("nan")
    return float(x) if np.isfinite(x) else float("nan")


def _total_power_W(row: pd.Series) -> float:
    cols = [c for c in row.index if str(c).endswith("_ENERGY_AVG_UWS")]
    s_uW = 0.0
    for c in cols:
        v = _to_float(row.get(c))
        if np.isfinite(v) and v > 0:
            s_uW += float(v)
    return float(s_uW) * 1e-6


def _model_deltaT(X, K: float, tau_s: float) -> np.ndarray:
    """ΔT = K * P * (1-exp(-t/tau))"""

    P, t = X
    P = np.asarray(P, dtype=float)
    t = np.asarray(t, dtype=float)
    tau_s = max(1e-6, float(tau_s))
    return K * P * (1.0 - np.exp(-t / tau_s))


def main() -> None:
    out_dir = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / "05-温度-时间曲线"
    ensure_dir(out_dir)

    src_path = Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"
    df = load_aggregated_csv(src_path)

    rows = []
    for _, row in df.iterrows():
        dur_s = float(estimate_duration_s(row))
        p_w = float(_total_power_W(row))
        avg_temp_c = _to_float(row.get("AVG_SOC_TEMP")) / 1000.0
        diff_temp_c = _to_float(row.get("DIFF_SOC_TEMP")) / 1000.0

        rows.append(
            {
                "phone_test_id": int(row.get("ID", -1) or -1),
                "duration_s_est": dur_s,
                "P_total_W": p_w,
                "avg_temp_C": avg_temp_c,
                "delta_temp_C": diff_temp_c,
            }
        )

    data = pd.DataFrame(rows)
    # 过滤：去掉明显异常/无意义点
    data = data[np.isfinite(data["P_total_W"]) & np.isfinite(data["duration_s_est"]) & np.isfinite(data["delta_temp_C"])].copy()
    data = data[(data["P_total_W"] > 0.2) & (data["P_total_W"] < 20.0)].copy()
    data = data[(data["duration_s_est"] >= 5.0) & (data["duration_s_est"] <= 120.0)].copy()
    data = data[(data["delta_temp_C"] > 0.05) & (data["delta_temp_C"] < 30.0)].copy()

    data.to_csv(out_dir / "data.csv", index=False, encoding="utf-8")

    P = data["P_total_W"].to_numpy(dtype=float)
    t = data["duration_s_est"].to_numpy(dtype=float)
    y = data["delta_temp_C"].to_numpy(dtype=float)

    # 非线性拟合
    popt, pcov = curve_fit(
        _model_deltaT,
        (P, t),
        y,
        p0=[0.8, 15.0],  # K(K/W), tau(s)
        bounds=([0.0, 0.1], [50.0, 300.0]),
        maxfev=50_000,
    )
    K, tau_s = float(popt[0]), float(popt[1])
    y_hat = _model_deltaT((P, t), K, tau_s)
    r2 = r2_score(y, y_hat)
    e_rmse = rmse(y, y_hat)

    # 把 K 解释为 eta*R_th，并给出在 eta=0.95 假设下的 R_th/C_th 量级
    eta_device_heat = 0.95
    R_th = K / eta_device_heat if eta_device_heat > 0 else float("nan")
    C_th = tau_s / R_th if (np.isfinite(R_th) and R_th > 1e-12) else float("nan")

    # 95% CI（基于协方差的近似）
    se_K = float(np.sqrt(pcov[0, 0])) if pcov.size else float("nan")
    se_tau = float(np.sqrt(pcov[1, 1])) if pcov.size else float("nan")

    fit_rows = [
        {
            "model": "first_order_thermal_from_deltaT",
            "equation": "ΔT = (η R_th) * P * (1-exp(-t/τ)),  τ=R_th*C_th",
            "n": int(len(data)),
            "K_etaRth_K_per_W": K,
            "tau_s": tau_s,
            "r2": r2,
            "rmse_C": e_rmse,
            "K_95CI_low": K - 1.96 * se_K if np.isfinite(se_K) else float("nan"),
            "K_95CI_high": K + 1.96 * se_K if np.isfinite(se_K) else float("nan"),
            "tau_95CI_low": tau_s - 1.96 * se_tau if np.isfinite(se_tau) else float("nan"),
            "tau_95CI_high": tau_s + 1.96 * se_tau if np.isfinite(se_tau) else float("nan"),
            "assumed_eta_device_heat": eta_device_heat,
            "R_th_K_per_W_est": R_th,
            "C_th_J_per_K_est": C_th,
            "data_source": to_repo_path(src_path),
            "temp_cols": "AVG_SOC_TEMP, DIFF_SOC_TEMP (m°C -> °C)",
            "power_def": "P_total = sum(*_ENERGY_AVG_UWS) * 1e-6",
            "duration_def": "estimate_duration_s ≈ sum(ENERGY_UW)/sum(ENERGY_AVG_UWS)",
        }
    ]
    write_csv(out_dir / "fit_results.csv", fit_rows)

    about = f"""# 05 温度-时间曲线（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`{to_repo_path(src_path)}`
  - 温度字段：`AVG_SOC_TEMP`、`DIFF_SOC_TEMP`（单位 m°C，本项目换算为 °C）

## 为什么不直接导出 T(t)

perfetto trace 本身在仓库内存在（`open_data/material/trace_parser/in/traces/*.perfetto-trace`），
但当前运行环境缺少 `perfetto.trace_processor` 依赖，暂无法直接解析导出完整 T(t)。
因此我们先用 aggregated.csv 中的温升统计量做“可解释反推”，得到热模型量级参数。

## 拟合模型

我们把温度看作一阶集总热系统（单温度节点）：

ΔT(t) = (η·R_th)·P·(1-exp(-t/τ)),  其中 τ=R_th·C_th

在每条测试中：
- P：整机平均功耗（由所有 *_ENERGY_AVG_UWS 汇总得到）
- t：测试时长（由 sum(ENERGY_UW)/sum(ENERGY_AVG_UWS) 估计）
- ΔT：观测温升（DIFF_SOC_TEMP）

## 参数解释（用于回填 Model-2 热模型）

- τ：热时间常数（秒）
- R_th：热阻（K/W）
- C_th：热容（J/K）

注：本拟合得到的是 “η·R_th” 的乘积，因此我们假设 η_device_heat={eta_device_heat} 以分离出 R_th 与 C_th。

## 产物

- `data.csv`：用于拟合的样本点（P、t、ΔT）
- `fit_results.csv`：拟合出的 K/τ 以及推导的 R_th/C_th
- `figure_paper.png` / `figure_study.png`：论文版/学习版图（含温升拟合与温度响应曲线）
"""
    write_text(out_dir / "about.md", about)

    # --- 出图 ---
    import matplotlib.pyplot as plt

    # 用于画拟合曲线：固定几个代表性时长
    t_levels = [10.0, 30.0, 60.0, 120.0]
    p_grid = np.linspace(float(np.nanmin(P)), float(np.nanmax(P)), 200)

    for mode in ["paper", "study"]:
        style = apply_style(mode)
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2))

        # (a) 温升拟合散点
        ax = axes[0]
        sc = ax.scatter(
            P,
            y,
            c=t,
            s=16,
            alpha=0.30 if mode == "paper" else 0.35,
            cmap="viridis",
            edgecolors="none",
        )
        cb = fig.colorbar(sc, ax=ax)
        cb.set_label("测试时长 t（s）")
        for i, tt in enumerate(t_levels):
            ax.plot(
                p_grid,
                _model_deltaT((p_grid, np.full_like(p_grid, tt)), K, tau_s),
                color=PALETTE_SKIP_GRADIENT[min(i, 3)],
                linewidth=2.0,
                label=f"模型曲线（t={tt:.0f}s）",
            )
        ax.set_title(f"温升-功耗-时长拟合{style.title_suffix}")
        ax.set_xlabel("整机平均功耗 P（W）")
        ax.set_ylabel("温升 ΔT（°C）")
        ax.legend(loc="upper left", frameon=False)

        # (b) 温度-时间曲线（基于拟合参数）
        ax = axes[1]
        t_grid = np.linspace(0.0, 180.0, 300)
        for i, p0 in enumerate([0.8, 1.5, 2.5, 4.0]):
            dT = _model_deltaT((np.full_like(t_grid, p0), t_grid), K, tau_s)
            ax.plot(t_grid, dT, color=PALETTE_SKIP_GRADIENT[min(i, 3)], linewidth=2.2, label=f"P={p0:.1f}W")
        ax.set_title(f"温度响应曲线（热一阶模型）{style.title_suffix}")
        ax.set_xlabel("时间 t（s）")
        ax.set_ylabel("温升 ΔT（°C）")
        ax.legend(loc="lower right", frameon=False)

        if style.annotate:
            ax.text(
                0.02,
                0.98,
                "拟合结果：\\n"
                f"K=ηR_th={K:.3f} K/W\\n"
                f"τ={tau_s:.1f} s\\n"
                f"假设 η={eta_device_heat:.2f} → R_th≈{R_th:.3f} K/W\\n"
                f"→ C_th≈{C_th:.1f} J/K\\n"
                f"R²={r2:.3f}, RMSE={e_rmse:.3f}°C",
                transform=axes[1].transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox={"fc": "white", "ec": "none", "alpha": 0.75},
            )

        fig.suptitle(f"AndroWatts：温度参量估计（由温升反推热模型）{style.title_suffix}")
        savefig(fig, out_dir / f"figure_{mode}.png", mode=mode)
        plt.close(fig)


if __name__ == "__main__":
    main()
