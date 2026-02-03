# 图 05：drivers 矩阵（组件级反事实 ΔTTE）

## 对应赛题 Q2 的哪个要求？

- “identify the specific drivers of rapid battery drain in each case”

## 本文件夹包含

- `10_component_driver_matrix.png`：论文版（paper）
- `10_component_driver_matrix_study.png`：学习版（study，含数值标注）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/drivers/10_component_driver_matrix.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/drivers/10_component_driver_matrix.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/make_q2_plots.py`

## 关键输入（配置/数据）

- 场景：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗/电池参数：
  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
图中每一列对应一个“组件级反事实动作”（把该组件功耗置零）。  
它回答的是“归因/敏感性”问题，并不要求这些动作在真实手机上可直接实现；可执行策略建议请在 Q4 用“可操作的动作”（如降低亮度、限制后台、切换网络模式）再翻译一次。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
