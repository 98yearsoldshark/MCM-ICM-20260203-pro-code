# 14-使用波动-突发性sweep_均值固定

## 这张图回答赛题 Q3 的哪一部分？

- **使用模式的波动（fluctuations in usage patterns）**：在平均使用强度近似不变的条件下，仅改变“突发性/脉冲化”结构，观察预测（TTE）如何变化。
- 补强口径：说明“均值功耗视角”可能低估突发负载在欠压边界附近造成的影响。

## 图源与生成位置

- 图文件源（paper/study）：
  - `MCM_Sim/26A/src/out_plots/q3/paper/fluctuation/22_burstiness_sweep.png`
  - `MCM_Sim/26A/src/out_plots/q3/study/fluctuation/22_burstiness_sweep.png`
- 本目录内：
  - `figure.png`：论文版
  - `other/figure_study.png`：学习版

## 生成脚本与报表

- 脚本：`MCM_Sim/26A/src/scripts/run_q3_fluctuation_burstiness_sweep.py`
- 报表（可复核）：
  - `src/out_reports/q3/fluctuation_burstiness_sweep/summary.csv`
  - `src/out_reports/q3/fluctuation_burstiness_sweep/runs.csv`
  - 本目录同步：`other/summary.csv`、`other/runs.csv`

## 关键方法（均值固定）

本 sweep 的核心是“只改波动结构，不改均值”：
- Poisson 类突发（后台唤醒/网络 burst）：
  - 幅度（每次突发工作量/数据量）按 α 放大；
  - 到达率按 1/α 缩小；
  - 因而单位时间的平均工作量近似不变，但方差与突发性更强。
- Markov 类随机切换（信号/亮屏抖动）：
  - 同时缩放两方向转移率：rate *= α；
  - 保持稳态分布（长期均值）不变，仅改变切换频率与时间相关性。

## 赛题适用性

- 该图完全由连续时间机理模型产生，不依赖额外外部数据集，适合作为 Q3 的“可控对照实验”。
- 若需要更强的观测锚定，可与 11（AndroWatts+电池状态表分解）和 13（NASA 脉冲下陷）共同构成证据链：观测现象 → 机理解释 → 可控敏感性 sweep。

