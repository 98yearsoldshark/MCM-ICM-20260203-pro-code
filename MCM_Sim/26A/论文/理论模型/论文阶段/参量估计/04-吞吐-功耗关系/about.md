# 04 吞吐–功耗关系（参量估计）

## 数据来源（主结果）

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
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
