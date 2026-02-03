# 图 04：不确定性宽度排名（p95−p05）

## 对应赛题 Q2 的哪个要求？

- “Quantify uncertainty” + “identify where the model performs well or poorly”

## 本文件夹包含

- `07_uq_spread_ranking.png`：论文版（paper）
- `07_uq_spread_ranking_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/uq/07_uq_spread_ranking.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/uq/07_uq_spread_ranking.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/make_q2_plots.py`

## 关键输入（配置/数据）

- 与图 01/03 使用同一套 Monte Carlo 样本池（UQ + 随机过程）：
  - `MCM_Sim/26A/src/configs/scenarios_v0.json`
  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
该图把“不确定性分布”压缩成一个很有说服力的单指标排序：适合在正文里用一句话概括“模型边界在哪里”，并且不占太多版面。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
