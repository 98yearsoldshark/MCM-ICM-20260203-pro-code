# 图 07：观测对照（AndroWatts：短时总功耗）

## 对应赛题 Q2 的哪个要求？

- “Compare predictions to observed or plausible behavior”
- 同时作为“模型表现好/差”讨论的量化证据（高功耗尾部偏差）。

## 本文件夹包含

- `01_total_power_scatter.png`：论文版（paper）
- `01_total_power_scatter_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/observed_open_data/01_total_power_scatter.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/observed_open_data/01_total_power_scatter.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_open_data.py`

## 关键输入（数据/配置）

- AndroWatts 聚合数据：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- 功耗参数（stateful）：`MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`

## 对应报表（图中指标来源）

- `MCM_Sim/26A/src/out_reports/q2/validation_open_data/metrics.csv`

（这是讲解内容，论文中可删除）  
图中用了 hexbin（密度格）而不是普通散点，避免 1000 点“糊成一团”。红色虚线为理想一致线 $y=x$，绿色线为线性拟合，用于诊断系统性偏差（例如高功耗段偏低/偏高）。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
