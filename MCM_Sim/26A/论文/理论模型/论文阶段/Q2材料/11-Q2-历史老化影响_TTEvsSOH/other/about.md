# 图 11：历史/老化影响（TTE vs SOH）

## 对应赛题的哪个要求？

- 赛题背景强调 battery history/aging 会影响续航；该图用公开老化状态表把这种影响量化为 TTE 差异。
- 可作为 Q2 的扩展 driver，也可放入 Q4（aging 影响与建议）或讨论部分。

## 本文件夹包含

- `01_tte_vs_soh.png`：论文版（paper）
- `01_tte_vs_soh_study.png`：学习版（study，可能含更多标注/散点）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/observed_master_table/01_tte_vs_soh.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/observed_master_table/01_tte_vs_soh.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_master_table.py --mode paper`
- `python MCM_Sim/26A/src/scripts/validate_q2_master_table.py --mode study`

## 关键输入（数据/配置）

- 手机负载（AndroWatts）：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- 老化状态表：`MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`
- 电池模型参数基线：`MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
该实验为了“隔离电池端机理”，采用了 **观测功耗作为恒定输入**（而不是让功耗模型再引入误差），因此更适合讲“老化/历史如何影响续航”。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
