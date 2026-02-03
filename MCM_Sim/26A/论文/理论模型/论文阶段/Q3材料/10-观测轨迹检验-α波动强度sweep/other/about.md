# 10-观测轨迹检验-α波动强度sweep

## 这张图回答赛题 Q3 的哪一部分？
- **使用模式波动（fluctuations in usage patterns）**：在“均值功耗相同”的前提下，仅改变波动强度（burstiness）会不会改变 TTE？
- 这是一个更强的口径：从“统计相关”升级为“可控对照（因果）”。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/observed_smartphone_measurements/03_fluctuation_sweep.png`
- 本目录内拷贝：`figure.png`

## 数据来源（开源/公开）
- SmartphoneMeasurements（Monsoon 电源采样）：
  - 位置：`MCM_Sim/26A/data/SmartphoneMeasurements/SmartphoneMeasurements.zip`
  - 使用方式：读取功耗时间序列 `P(t)` 作为外生输入驱动电池 ODE（不用于“拟合功耗模型”）。

## 生成脚本与关联报表
- 先生成重采样轨迹与 Trace vs Mean 报表（可复现原始选择与重采样）：
  - `MCM_Sim/26A/src/scripts/run_q3_smartphone_measurements_experiment.py`
  - 输出：`MCM_Sim/26A/src/out_reports/q3/observed_smartphone_measurements/trace_vs_mean.csv`
- 再做 α-sweep（生成本图的核心报表）：
  - `MCM_Sim/26A/src/scripts/run_q3_smartphone_measurements_sweep_experiment.py`
  - 输出：`MCM_Sim/26A/src/out_reports/q3/observed_smartphone_measurements/fluctuation_sweep.csv`
- 出图脚本：
  - `MCM_Sim/26A/src/scripts/make_q3_smartphone_measurements_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.3 使用波动：观测轨迹驱动的假设检验（alpha sweep）”

## 写作要点（建议）
- 明确：这里的数据只用于“锚定波动结构是否重要”，并不替代连续时间机理模型（符合赛题 Data-as-support 的要求）。
- 强调构造：`P_alpha(t)=P̄ + alpha*(P(t)-P̄)`，均值严格不变，因此变化只来自“波动强度”。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
