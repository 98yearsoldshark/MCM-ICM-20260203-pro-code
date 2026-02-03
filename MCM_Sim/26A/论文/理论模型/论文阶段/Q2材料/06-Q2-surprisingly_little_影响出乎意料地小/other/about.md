# 图 06：“surprisingly little” 定量口径图

## 对应赛题 Q2 的哪个要求？

- “Which ones change the model surprisingly little?”

## 本文件夹包含

- `01_little_effect_rank.png`：论文版（paper）
- `01_little_effect_rank_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/little_effect/01_little_effect_rank.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/little_effect/01_little_effect_rank.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/run_q2_little_effect.py`

## 关键输入（配置/数据）

- 该脚本**不重新仿真**，而是读取 Q2 主报表输出（更稳定、可复现）：
  - 组件 drivers 矩阵：`MCM_Sim/26A/src/out_reports/q2/component_drivers_matrix.csv`
  - 基线 TTE 汇总：`MCM_Sim/26A/src/out_reports/q2/tte_summary.csv`

（这是讲解内容，论文中可删除）  
“little band”的默认口径是：`max(abs_thresh_h=0.25h, rel_thresh_pct=2% * TTE_baseline)`。你如果想更严格/更宽松，可以在脚本参数里调整，但要在正文写清楚阈值。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
