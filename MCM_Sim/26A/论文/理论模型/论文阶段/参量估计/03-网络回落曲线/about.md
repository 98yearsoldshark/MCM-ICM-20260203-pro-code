# 03 网络回落曲线（tail）参量估计（基于 AndroWatts）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
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
