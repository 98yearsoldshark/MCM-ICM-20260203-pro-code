# 图 03：TTE 不确定性分布（UQ）

## 对应赛题 Q2 的哪个要求？

- “Quantify uncertainty”  
  以分布/区间形式给出 TTE，而不是单一数值。

## 本文件夹包含

- `02_tte_distribution_soc1.png`：论文版（paper）
- `02_tte_distribution_soc1_study.png`：学习版（study，含术语解释）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/uq/02_tte_distribution_soc1.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/uq/02_tte_distribution_soc1.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/make_q2_plots.py`

## 关键输入（配置/数据）

- 场景：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗参数：`MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
- 电池参数：`MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
该图与 “01 TTE 矩阵” 使用同一套 Monte Carlo 样本池：矩阵取均值，这里展示分布形状（长尾/宽度），更直观地回答“模型输出的可信区间”。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
