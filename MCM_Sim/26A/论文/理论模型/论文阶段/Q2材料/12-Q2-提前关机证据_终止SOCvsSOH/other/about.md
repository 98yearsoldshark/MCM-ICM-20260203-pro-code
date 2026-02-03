# 图 12：提前关机证据（终止时 SOC vs SOH）

## 对应赛题 Q2 的哪个要求？

- “Show how your model explains differences in outcomes”  
  用“欠压提前关机”解释为什么 TTE 不等于线性耗尽。
- “identify where the model performs well or poorly”  
  低 SOH + 高负载时更接近模型边界。

## 本文件夹包含

- `02_soc_end_vs_soh.png`：论文版（paper）
- `02_soc_end_vs_soh_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/observed_master_table/02_soc_end_vs_soh.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/observed_master_table/02_soc_end_vs_soh.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_master_table.py --mode paper`
- `python MCM_Sim/26A/src/scripts/validate_q2_master_table.py --mode study`

## 关键输入（数据/配置）

- 与图 11 相同（AndroWatts 负载 + 老化状态表）：
  - `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
  - `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
