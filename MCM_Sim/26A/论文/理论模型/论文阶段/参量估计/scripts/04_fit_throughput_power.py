#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04 吞吐–功耗关系：用 AndroWatts 的 Wi-Fi 流量与无线 rail 功耗拟合能耗系数。

输出位置：
- `.../参量估计/04-吞吐-功耗关系/`

核心定义（与 Model-1 网络模块一致的维度）：
- 吞吐：throughput_MBps（MB/s）
- 无线功耗：P_radio（W）
- 线性模型：P_radio ≈ P_idle + e_per_mb_J * throughput_MBps
  - 其中 e_per_mb_J（J/MB）可直接作为 RRC 模型中的 “每 MB 能耗” 参数量级。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR, ensure_dir, linear_fit_with_intercept, summarize_fit, to_repo_path, write_csv, write_text

from mcm26a.observed.andro_watts import estimate_duration_s, load_aggregated_csv
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _to_float(v) -> float:
    try:
        x = float(v)
    except Exception:
        return float("nan")
    return float(x) if np.isfinite(x) else float("nan")


def main() -> None:
    out_dir = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / "04-吞吐-功耗关系"
    ensure_dir(out_dir)

    src_path = Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"
    df = load_aggregated_csv(src_path)

    rows = []
    for _, row in df.iterrows():
        dur_s = float(estimate_duration_s(row))
        wifi_bytes = _to_float(row.get("WIFI_data", row.get("TOTAL_DATA_WIFI_BYTES", 0.0)))
        wifi_bytes = 0.0 if not np.isfinite(wifi_bytes) else max(0.0, float(wifi_bytes))
        thr = 0.0 if dur_s <= 0 else float(wifi_bytes / dur_s / 1e6)  # MB/s

        wlan_uW = _to_float(row.get("WLANBT_ENERGY_AVG_UWS"))
        cell_uW = _to_float(row.get("CELLULAR_ENERGY_AVG_UWS"))
        cell2_uW = _to_float(row.get("CELLULAR_ENERGY_AVG_UWS.1"))
        wlan_uW = 0.0 if not np.isfinite(wlan_uW) else max(0.0, wlan_uW)
        cell_uW = 0.0 if not np.isfinite(cell_uW) else max(0.0, cell_uW)
        cell2_uW = 0.0 if not np.isfinite(cell2_uW) else max(0.0, cell2_uW)

        p_radio_W = (wlan_uW + cell_uW + cell2_uW) * 1e-6

        # 口径：若 Wi-Fi 有流量或 WLAN rail >= CELL rail，则认为主要是 Wi-Fi（与适配器一致）
        radio_mode = "wifi" if (thr > 0.0 or wlan_uW >= (cell_uW + cell2_uW)) else "lte"

        rows.append(
            {
                "phone_test_id": int(row.get("ID", -1) or -1),
                "duration_s_est": dur_s,
                "throughput_MBps": thr,
                "radio_mode": radio_mode,
                "obs_radio_w": float(p_radio_W),
                "wlan_w": float(wlan_uW * 1e-6),
                "cell_w": float((cell_uW + cell2_uW) * 1e-6),
            }
        )

    data = pd.DataFrame(rows)
    # 过滤：只用 Wi-Fi（吞吐来自 Wi-Fi bytes，LTE 无法从该表得到 throughput）
    data = data[data["radio_mode"] == "wifi"].copy()
    data = data[(data["obs_radio_w"] > 0.0) & (data["obs_radio_w"] < 2.0)].copy()

    # 为拟合稳定：剔除吞吐为 0 的点（这些点可视为 idle，但会与 “Wi-Fi 开着但不传输” 混在一起）
    fit_data = data[data["throughput_MBps"] > 0.005].copy()

    x = fit_data["throughput_MBps"].to_numpy()
    y = fit_data["obs_radio_w"].to_numpy()

    p0, e = linear_fit_with_intercept(x, y)
    y_hat = p0 + e * x
    summ = summarize_fit(y, y_hat)

    # 保存数据与拟合结果
    data.to_csv(out_dir / "data.csv", index=False, encoding="utf-8")
    fit_rows = [
        {
            "model": "linear_wifi_throughput",
            "equation": "P_radio = P_idle + e_per_mb_J * throughput_MBps",
            "n": summ.n,
            "P_idle_W": p0,
            "e_per_mb_J": e,
            "r2": summ.r2,
            "rmse_W": summ.rmse,
            "data_source": to_repo_path(src_path),
            "throughput_def": "TOTAL_DATA_WIFI_BYTES / duration_s_est / 1e6 (MB/s)",
            "duration_def": "sum(ENERGY_UW)/sum(ENERGY_AVG_UWS) (see mcm26a.observed.andro_watts.estimate_duration_s)",
            "power_def": "P_radio = (WLANBT + CELLULAR + CELLULAR.1)_ENERGY_AVG_UWS * 1e-6",
        }
    ]
    write_csv(out_dir / "fit_results.csv", fit_rows)

    about = f"""# 04 吞吐–功耗关系（参量估计）

## 数据来源（主结果）

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`{to_repo_path(src_path)}`
  - 流量：`TOTAL_DATA_WIFI_BYTES`
  - 无线 rail：`WLANBT_ENERGY_AVG_UWS`、`CELLULAR_ENERGY_AVG_UWS`、`CELLULAR_ENERGY_AVG_UWS.1`

## 变量定义

- 估计测试时长：`duration_s_est ≈ sum(ENERGY_UW)/sum(ENERGY_AVG_UWS)`（见项目适配器实现）
- 平均吞吐：`throughput_MBps = TOTAL_DATA_WIFI_BYTES / duration_s_est / 1e6`
- 观测无线功耗：
  - `P_radio = (WLANBT + CELLULAR + CELLULAR.1)_ENERGY_AVG_UWS * 1e-6 (W)`

## 拟合模型（可直接映射到 RRC 参数）

`P_radio ≈ P_idle + e_per_mb_J * throughput_MBps`

- 截距 `P_idle`：可视为“Wi-Fi 维持/控制面”量级
- 斜率 `e_per_mb_J`：每 MB 传输能耗（J/MB）

## 产物

- `data.csv`：Wi-Fi 样本的（吞吐, 无线功耗）表
- `fit_results.csv`：线性模型参数与误差
- `figure_paper.png`/`figure_study.png`：论文版/学习版图
"""
    write_text(out_dir / "about.md", about)

    # 绘图：paper 版使用分箱中位数，study 版显示散点 + 拟合指标
    import matplotlib.pyplot as plt

    # 分箱（吞吐分 12 桶）
    data2 = data.copy()
    # 只展示非零吞吐部分（更聚焦线性关系）
    data2 = data2[data2["throughput_MBps"] > 0.0]
    data2["bin"] = pd.cut(data2["throughput_MBps"], bins=12)
    grp = data2.groupby("bin", observed=True)
    x_mid = grp["throughput_MBps"].median().to_numpy()
    y_med = grp["obs_radio_w"].median().to_numpy()
    y_q25 = grp["obs_radio_w"].quantile(0.25).to_numpy()
    y_q75 = grp["obs_radio_w"].quantile(0.75).to_numpy()

    for mode in ["paper", "study"]:
        style = apply_style(mode)
        fig, ax = plt.subplots(figsize=(6.8, 4.2))
        if mode == "paper":
            ax.fill_between(x_mid, y_q25, y_q75, color=PALETTE_SKIP_GRADIENT[1], alpha=0.25, linewidth=0)
            ax.plot(x_mid, y_med, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.0, label="分箱中位数（IQR）")
        else:
            ax.scatter(
                fit_data["throughput_MBps"],
                fit_data["obs_radio_w"],
                s=16,
                alpha=0.22,
                color=PALETTE_SKIP_GRADIENT[0],
                edgecolors="none",
                label="样本点（thr>0.005）",
            )

        xs = np.linspace(0.0, float(np.nanmax(fit_data["throughput_MBps"])), 200)
        ax.plot(xs, p0 + e * xs, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="线性拟合")

        ax.set_title(f"吞吐–无线功耗关系（AndroWatts, Wi-Fi）{style.title_suffix}")
        ax.set_xlabel("Wi-Fi 平均吞吐（MB/s）")
        ax.set_ylabel("无线功耗（W）")
        ax.legend(loc="best", frameon=False)

        if style.annotate:
            ax.text(
                0.02,
                0.98,
                "拟合：P = P_idle + e·thr\\n"
                f"n={summ.n}\\n"
                f"P_idle={p0:.3f} W\\n"
                f"e={e:.3f} J/MB\\n"
                f"R²={summ.r2:.3f}, RMSE={summ.rmse:.3f}W",
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=9,
                bbox={"fc": "white", "ec": "none", "alpha": 0.75},
            )

        savefig(fig, out_dir / f"figure_{mode}.png", mode=mode)
        plt.close(fig)


if __name__ == "__main__":
    main()
