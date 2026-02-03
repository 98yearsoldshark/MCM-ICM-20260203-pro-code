# 图 01：TTE 矩阵（场景 × 初始电量）

## 对应赛题 Q2 的哪个要求？

- “Use your model to compute or approximate the time-to-empty under various initial charge levels and usage scenarios.”

## 本文件夹包含

- `01_tte_matrix.png`：论文版（paper）
- `01_tte_matrix_study.png`：学习版（study，带更多标注）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/tte/01_tte_matrix.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/tte/01_tte_matrix.png`

## 如何生成（脚本入口）

- 生成命令（会同时生成 paper/study）：
  - `python MCM_Sim/26A/src/scripts/make_q2_plots.py`

（这是讲解内容，论文中可删除）  
`make_q2_plots.py` 内部会对关键参数做先验采样（UQ）并运行连续时间仿真，因此该图的每个格子不是“单次仿真值”，而是“分布均值”。这能更好地对齐赛题 Q2 的“quantify uncertainty”。

## 备注：对齐赛题 Table 2（S1–S5）

- 本项目的“浏览/社交媒体”对应赛题的 **S2 Browsing/Social Media**。
- 出图时使用的场景 ID：`S1b_browse`（以避免与原有 `S1_video`/`S2_navigation` 的编号冲突）。

## 关键输入（配置/数据）

- 场景配置（含 variants 定义）：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗参数（stateful）：`MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
- 电池参数（热-电-老化）：`MCM_Sim/26A/src/configs/phone_default_v3_aging.json`
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
