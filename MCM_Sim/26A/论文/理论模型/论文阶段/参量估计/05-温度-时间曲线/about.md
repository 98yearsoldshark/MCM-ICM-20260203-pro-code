# 05 温度-时间曲线（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
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

注：本拟合得到的是 “η·R_th” 的乘积，因此我们假设 η_device_heat=0.95 以分离出 R_th 与 C_th。

## 产物

- `data.csv`：用于拟合的样本点（P、t、ΔT）
- `fit_results.csv`：拟合出的 K/τ 以及推导的 R_th/C_th
- `figure_paper.png` / `figure_study.png`：论文版/学习版图（含温升拟合与温度响应曲线）
