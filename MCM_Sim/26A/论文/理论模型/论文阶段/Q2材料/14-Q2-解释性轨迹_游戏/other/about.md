# 图 14：解释性轨迹（游戏：高 CPU/GPU 负载）

## 对应赛题 Q2 的哪个要求？

- “Show how your model explains differences in outcomes”  
  用轨迹对比展示：高负载下 TTE 由欠压边界主导，且温度反馈更明显。

## 本文件夹包含

- `trace_soc100.png`：论文版（paper）
- `trace_soc100_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/trajectories/S3_gaming/trace_soc100.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/trajectories/S3_gaming/trace_soc100.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/make_q2_trajectory_plots.py`

## 关键输入（配置/数据）

- 场景：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗参数：`MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
- 电池参数：`MCM_Sim/26A/src/configs/phone_default_v3_aging.json`
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
