# 06-假设检验-电池模型复杂度

## 这张图回答赛题 Q3 的哪一部分？
- **建模假设（modeling assumptions）**：电池端需要多复杂？忽略热/老化是否会显著改变预测？
- 通过“同一功耗输入、不同电池模型”的对照，检验复杂度假设是否合理。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/ablation/41_battery_model_ablation.png`
- 本目录内拷贝：`figure.png`

## 额外补充图（放大热效应，建议附录）
- 变体放大图：`MCM_Sim/26A/src/out_plots/q3/paper/ablation/43_battery_model_cold_hot_effects.png`
  - 本目录内拷贝：`other/figure_cold_hot_effects.png`
  - 说明：比较 cold/hot 变体下 Model-2 相对 Model-1 的 ΔTTE、Δmargin、ΔT_end，可更直观看到热耦合在环境变化下的作用。

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 明细：`MCM_Sim/26A/src/out_reports/q3/ablation.csv`（筛选 `ablation_type=battery_model`）
- 轻量报表（推荐）：`MCM_Sim/26A/src/scripts/run_q3_battery_model_ablation_only.py`
  - 输出：`MCM_Sim/26A/src/out_reports/q3/battery_model_ablation.csv`（含温度峰值/环境变体信息）
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.2 Assumptions：电池模型复杂度消融”

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
