# 图 02：条件对照（OAT，统一 x 轴）的相对影响矩阵

## 对应赛题 Q2 的哪个要求？

- “Which activities or conditions produce the greatest reductions in battery life?”
- 同时也是后续 “解释差异” 的入口：把 TTE 的变化归因到网络/温度/亮度等条件。

## 本文件夹包含

- `../figure.png`：论文版（paper）
- `figure_study.png`：学习版（study，底部含术语解释）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/variants/05_variants_compare.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/variants/05_variants_compare.png`

## 如何生成（脚本入口）

- 第一步：生成统一条件集合的 OAT 统计表（no12 口径，修正 x 轴语义）
  - `PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/run_q2_conditions_oat_stats.py --dt 10 --seeds 50 --soc0 1.0`
  - 输出：`MCM_Sim/26A/src/out_reports/q2/conditions_oat_stats.csv`
- 第二步：出图（paper/study 两套）
  - `python MCM_Sim/26A/src/scripts/make_q2_plots.py --dt 10 --driver-seeds 50 --uq-samples 80 --uq-seed 1`
  - 为保证“图与数据同源”，该图会优先读取：
    - `MCM_Sim/26A/src/out_reports/q2/conditions_oat_stats.csv`

## 关键输入（配置/数据）

- 场景与 variants 定义：`MCM_Sim/26A/src/configs/scenarios_v0.json`
  - 本图不直接使用“各场景自带 variants 拼盘”，而是对 **所有场景** 应用同一组“条件开关”（OAT），保证 x 轴统一、可解释。
- 功耗/电池参数：
  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
这张图的读法是：
- 每一行是一个 usage scenario（场景），每一列是一个 condition variant（只改少量条件的对照）。
- 每个格子显示 **相对变化**：`ΔTTE / TTE_baseline（%）`（红色=续航缩短，绿色=续航变长），并在学习版中同时显示 `ΔTTE（小时）`。
- 与 no12 一致：baseline 强制室温常值（20°C），温度列（-15°C/38°C）作为“方向性对照”。
- 相比“6 个小图”，这种矩阵更适合论文：评委一眼就能回答“哪些条件导致最大幅度缩短 / 哪些 surprisingly little”。

生成流程上，我们刻意把 `conditions_oat_stats.csv` 作为中间产物，是为了让 figure.png 与 `other/data.csv` 可追溯到同一来源（冲高奖口径）。

推荐复现实验命令：
- `PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/run_q2_conditions_oat_stats.py --dt 10 --seeds 50 --soc0 1.0`
- `python MCM_Sim/26A/src/scripts/make_q2_plots.py --dt 10 --driver-seeds 50 --uq-samples 80 --uq-seed 1`
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
