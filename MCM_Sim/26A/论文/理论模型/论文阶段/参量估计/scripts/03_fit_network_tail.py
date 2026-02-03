#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03 网络回落曲线（tail）：用 AndroWatts 的“能量守恒”反推出 tail 能量与等效时间常数。

为什么不用 SmartphoneMeasurements 直接拟合？
- 该 zip 的 Monsoon 采样窗在本仓库样例中多为 ~120s，而 iPerf 日志多为 ~180s，
  “传输结束→回落”段经常不在采样窗内，无法稳定拟合 tail 下降段。

本脚本采用更稳健、且完全基于 AndroWatts（CC BY 4.0）的方式：

对每条测试（聚合样本）建立无线能量分解：

  E_radio ≈ P_idle * t + e_per_mb * bytes_MB + E_tail

其中：
- t：测试时长（由 sum(ENERGY_UW)/sum(ENERGY_AVG_UWS) 估计）
- bytes_MB：Wi-Fi 总流量（MB）
- P_idle：无线维持功耗（W）
- e_per_mb：每 MB 传输能耗（J/MB）
- E_tail：与“RRC/尾态/连接维护开销”等相关的常量能量项（J）

然后用“连接态基准功耗”估计 tail 的等效时间常数：
  τ_tail ≈ E_tail / (P_conn - P_idle)

并生成一条可直接放进论文的“回落曲线”：
  P_tail(t) = P_idle + (P_conn - P_idle) * exp(-t/τ_tail)

输出位置：
- `.../参量估计/03-网络回落曲线/`
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR, ensure_dir, r2_score, rmse, to_repo_path, write_csv, write_text

from mcm26a.observed.andro_watts import estimate_duration_s, load_aggregated_csv
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _to_float(v) -> float:
    try:
        x = float(v)
    except Exception:
        return float("nan")
    return float(x) if np.isfinite(x) else float("nan")


def _radio_power_W(row: pd.Series) -> float:
    wlan = _to_float(row.get("WLANBT_ENERGY_AVG_UWS"))
    cell = _to_float(row.get("CELLULAR_ENERGY_AVG_UWS"))
    cell2 = _to_float(row.get("CELLULAR_ENERGY_AVG_UWS.1"))
    wlan = 0.0 if not np.isfinite(wlan) else max(0.0, wlan)
    cell = 0.0 if not np.isfinite(cell) else max(0.0, cell)
    cell2 = 0.0 if not np.isfinite(cell2) else max(0.0, cell2)
    return float(wlan + cell + cell2) * 1e-6


def _radio_energy_J(row: pd.Series) -> float:
    """用 *_ENERGY_UW 列（实际为 uW*s）汇总无线能量，换算为 J。"""

    wlan = _to_float(row.get("WLANBT_ENERGY_UW"))
    cell = _to_float(row.get("CELLULAR_ENERGY_UW"))
    cell2 = _to_float(row.get("CELLULAR_ENERGY_UW.1"))
    wlan = 0.0 if not np.isfinite(wlan) else max(0.0, wlan)
    cell = 0.0 if not np.isfinite(cell) else max(0.0, cell)
    cell2 = 0.0 if not np.isfinite(cell2) else max(0.0, cell2)
    # uW*s -> J
    return float(wlan + cell + cell2) * 1e-6


def main() -> None:
    out_dir = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / "03-网络回落曲线"
    ensure_dir(out_dir)

    src_path = Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"
    df = load_aggregated_csv(src_path)

    rows = []
    for _, row in df.iterrows():
        t = float(estimate_duration_s(row))
        wifi_bytes = _to_float(row.get("WIFI_data", row.get("TOTAL_DATA_WIFI_BYTES", 0.0)))
        wifi_bytes = 0.0 if not np.isfinite(wifi_bytes) else max(0.0, float(wifi_bytes))
        bytes_MB = float(wifi_bytes / 1e6)
        thr = float(bytes_MB / t) if t > 0 else 0.0

        p_radio = _radio_power_W(row)
        e_radio = _radio_energy_J(row)

        # 判定 radio_mode（与适配器一致：Wi-Fi 有流量或 WLAN rail >= CELL rail）
        wlan_uW = _to_float(row.get("WLANBT_ENERGY_AVG_UWS")) or 0.0
        cell_uW = (_to_float(row.get("CELLULAR_ENERGY_AVG_UWS")) or 0.0) + (_to_float(row.get("CELLULAR_ENERGY_AVG_UWS.1")) or 0.0)
        mode = "wifi" if (thr > 0.0 or wlan_uW >= cell_uW) else "lte"

        rows.append(
            {
                "phone_test_id": int(row.get("ID", -1) or -1),
                "radio_mode": mode,
                "duration_s_est": t,
                "bytes_MB": bytes_MB,
                "throughput_MBps": thr,
                "P_radio_W": p_radio,
                "E_radio_J": e_radio,
            }
        )

    data = pd.DataFrame(rows)
    data = data[(data["radio_mode"] == "wifi")].copy()
    data = data[np.isfinite(data["E_radio_J"]) & np.isfinite(data["duration_s_est"]) & np.isfinite(data["bytes_MB"])].copy()
    data = data[(data["duration_s_est"] >= 5.0) & (data["duration_s_est"] <= 120.0)].copy()
    data = data[(data["E_radio_J"] > 0.0) & (data["E_radio_J"] < 2000.0)].copy()
    data.to_csv(out_dir / "data.csv", index=False, encoding="utf-8")

    # 线性回归：E = P_idle*t + e*bytes + E_tail
    # 说明：这里用普通最小二乘即可（量级不大）；再把系数裁剪为非负，避免出现不合理的负功耗/负能耗。
    t = data["duration_s_est"].to_numpy(float)
    b = data["bytes_MB"].to_numpy(float)
    y = data["E_radio_J"].to_numpy(float)
    X = np.column_stack([t, b, np.ones_like(t)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    beta = np.maximum(0.0, beta)
    P_idle, e_per_mb, E_tail = map(float, beta.tolist())

    # 个别环境下 numpy 的底层 BLAS 可能会对 matmul 抛出溢出/除零告警（但结果仍为有限值）。
    # 这里显式屏蔽告警，避免运行输出被噪声淹没。
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        y_hat = X @ beta
    r2 = r2_score(y, y_hat)
    e_rmse = rmse(y, y_hat)

    # 估计连接态基准功耗：P_conn ≈ median(P_radio - e*throughput)（取较高吞吐子集）
    # 这里 throughput 由 bytes/t 得到，因此 e*throughput = (e*bytes)/t，能在平均功耗层面扣除“传输项”
    data["P_conn_proxy_W"] = data["P_radio_W"] - e_per_mb * data["throughput_MBps"]
    hi = data[data["throughput_MBps"] >= float(data["throughput_MBps"].quantile(0.80))].copy()
    P_conn = float(np.nanmedian(hi["P_conn_proxy_W"])) if len(hi) >= 20 else float(np.nanmedian(data["P_conn_proxy_W"]))
    dP = max(1e-6, float(P_conn - P_idle))
    tau_tail = float(E_tail / dP)

    fit_rows = [
        {
            "model": "energy_balance_with_tail",
            "equation": "E_radio = P_idle*t + e_per_mb*bytes_MB + E_tail",
            "n": int(len(data)),
            "P_idle_W": P_idle,
            "e_per_mb_J": e_per_mb,
            "E_tail_J": E_tail,
            "P_conn_W_est": P_conn,
            "tau_tail_s_est": tau_tail,
            "r2": r2,
            "rmse_J": e_rmse,
            "data_source": to_repo_path(src_path),
            "radio_energy_cols": "WLANBT_ENERGY_UW + CELLULAR_ENERGY_UW + CELLULAR_ENERGY_UW.1 (uW*s -> J)",
            "radio_power_cols": "WLANBT_ENERGY_AVG_UWS + CELLULAR_ENERGY_AVG_UWS + CELLULAR_ENERGY_AVG_UWS.1 (uW -> W)",
            "tail_tau_def": "tau_tail = E_tail / (P_conn - P_idle)",
        }
    ]
    write_csv(out_dir / "fit_results.csv", fit_rows)

    about = f"""# 03 网络回落曲线（tail）参量估计（基于 AndroWatts）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`{to_repo_path(src_path)}`
  - 本拟合仅使用 Wi-Fi 样本（吞吐来自 `TOTAL_DATA_WIFI_BYTES`）。

## 核心思想：用“能量守恒”反推 tail

聚合数据没有直接的 `P(t)` 回落段，但同时提供：
- 无线 rail 的平均功率 proxy（*_ENERGY_AVG_UWS）
- 无线 rail 的总能量 proxy（*_ENERGY_UW，实际为 uW*s）
- Wi-Fi 总流量（bytes）
- 测试时长可由 (总能量)/(平均功率) 估计

因此我们用可解释的能量分解模型：

E_radio ≈ P_idle*t + e_per_mb*bytes_MB + E_tail

并用高吞吐样本估计连接态基准功耗 `P_conn`，得到等效回落时间常数：

τ_tail ≈ E_tail / (P_conn - P_idle)

## 产物

- `data.csv`：Wi-Fi 样本的 (t, bytes, P_radio, E_radio)
- `fit_results.csv`：拟合出的 P_idle / e_per_mb / E_tail，以及 τ_tail 的等效估计
- `figure_paper.png`/`figure_study.png`：图像（含“短时长导致平均功耗抬升”的 tail 证据 + 回落曲线）
"""
    write_text(out_dir / "about.md", about)

    # --- 出图 ---
    import matplotlib.pyplot as plt

    thr = data["throughput_MBps"].to_numpy(float)
    p_radio = data["P_radio_W"].to_numpy(float)
    dur = data["duration_s_est"].to_numpy(float)

    # 画回落曲线
    t_grid = np.linspace(0.0, 60.0, 300)
    p_tail = P_idle + (P_conn - P_idle) * np.exp(-t_grid / max(1e-6, tau_tail))

    for mode in ["paper", "study"]:
        style = apply_style(mode)
        fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.2))

        # (a) 平均功耗 vs 吞吐（用时长着色，展示 tail 能量在短测试中“摊薄”导致功耗抬升）
        ax = axes[0]
        sc = ax.scatter(thr, p_radio, c=dur, s=16, alpha=0.30, cmap="viridis", edgecolors="none")
        cb = fig.colorbar(sc, ax=ax)
        cb.set_label("测试时长 t（s）")
        xs = np.linspace(0.0, float(np.nanmax(thr)), 200)
        ax.plot(xs, P_idle + e_per_mb * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="无 tail：P_idle + e·thr")
        ax.set_title(f"无线功耗与吞吐（时长着色）{style.title_suffix}")
        ax.set_xlabel("Wi-Fi 平均吞吐（MB/s）")
        ax.set_ylabel("无线平均功耗（W）")
        ax.legend(loc="upper left", frameon=False)

        # (b) 等效网络回落曲线
        ax = axes[1]
        ax.plot(t_grid, p_tail, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.6, label="回落曲线（指数）")
        ax.hlines(P_idle, xmin=0, xmax=float(t_grid.max()), color=PALETTE_SKIP_GRADIENT[2], linewidth=2.0, linestyles="--", label="P_idle")
        ax.set_title(f"网络回落曲线（等效 τ）{style.title_suffix}")
        ax.set_xlabel("距传输结束的时间（s）")
        ax.set_ylabel("无线功耗 P_radio（W）")
        ax.legend(loc="upper right", frameon=False)

        if style.annotate:
            axes[1].text(
                0.02,
                0.98,
                f"拟合：E = P_idle·t + e·bytes + E_tail\\n"
                f"P_idle={P_idle:.3f}W, e={e_per_mb:.3f}J/MB\\n"
                f"E_tail={E_tail:.3f}J\\n"
                f"P_conn≈{P_conn:.3f}W\\n"
                f"τ_tail≈{tau_tail:.2f}s\\n"
                f"R²={r2:.3f}, RMSE={e_rmse:.3f}J",
                transform=axes[1].transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox={"fc": "white", "ec": "none", "alpha": 0.75},
            )

        fig.suptitle(f"AndroWatts：网络 tail 参量估计（能量守恒反推）{style.title_suffix}")
        savefig(fig, out_dir / f"figure_{mode}.png", mode=mode)
        plt.close(fig)


if __name__ == "__main__":
    main()
