# 08-使用波动-随机过程ΔTTE分布

## 这张图回答赛题 Q3 的哪一部分？
- **使用模式的波动（fluctuations in usage patterns）**：在同一参数与同一场景下，仅随机过程不同（seed 不同）会导致 TTE 分布如何变化？
- 用相对误差 `ΔTTE(%)` 表达，避免不同场景 TTE 量级差异淹没随机波动。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/fluctuation/20_seed_variation_violin.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 单次 seed 的运行明细：`MCM_Sim/26A/src/out_reports/q3/seed_runs.csv`
  - seed-only 汇总：`MCM_Sim/26A/src/out_reports/q3/fluctuation_only.csv`
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.3 使用波动：固定参数下的随机过程波动”

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。

## 观测锚定（关联图）
- `anchors/anchor_10_alpha_sweep.png`：Monsoon 观测轨迹的 α-sweep（波动结构是否重要）。
- `anchors/anchor_11_usage_aging_interaction.png`：AndroWatts×电池老化状态的方差分解（使用/老化/交互/随机）。
- `anchor_10_alpha_sweep.png` / `anchor_11_usage_aging_decomp.png`：同一锚定图的便捷副本（兼容不同目录结构）。
