# 图 10：观测对照（长时间/TTE 分布：user_behavior_dataset）

## 对应赛题 Q2 的哪个要求？

- “Compare predictions to observed or plausible behavior”  
  这里对照的是“长时间尺度的合理范围”，用于补强场景集覆盖的现实性。

## 本文件夹包含

- `../figure.png`：论文主图（paper，当前采用 daily plausibility 组合图 v7：TTE 分布 + 日耗电分布，均含分位轴）
- `figure_study.png`：学习版主图（study，当前同步到 v7）
- `fihure_en.png`：英文版图片（paper，按用户要求的文件名拼写）
- `figure_daily_combo_paper_v*.png` / `figure_daily_combo_study_v*.png`：主图的版本留存（便于回滚/对比）
- `subfig_daily_tte_*.png` / `subfig_daily_drain_*.png`：组合图的两张子图（便于单独引用）
- `subfig_active_tte_*.png`：active 口径的补充对照（可选附录）

## 图片来源（原始产物路径）

- 主图（paper）：`MCM_Sim/26A/src/out_plots/q2/paper/observed_user_behavior/05_daily_plausibility_combo_v7.png`
- 主图（study）：`MCM_Sim/26A/src/out_plots/q2/study/observed_user_behavior/05_daily_plausibility_combo_v7.png`
- 英文版主图（paper）：`MCM_Sim/26A/src/out_plots/q2/paper/observed_user_behavior/05_daily_plausibility_combo_v7en.png`
- 组合子图（paper）：
  - daily-TTE：`MCM_Sim/26A/src/out_plots/q2/paper/observed_user_behavior/03_tte_hist_overlay_daily_v7.png`
  - daily-drain：`MCM_Sim/26A/src/out_plots/q2/paper/observed_user_behavior/04_drain_hist_overlay_daily_v7.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_user_behavior.py --mode paper`
- `python MCM_Sim/26A/src/scripts/validate_q2_user_behavior.py --mode study`
- 生成新图且不覆盖旧图（推荐用于对比/迭代）：  
  `python MCM_Sim/26A/src/scripts/validate_q2_user_behavior.py --mode paper --tag v7`  
  `python MCM_Sim/26A/src/scripts/validate_q2_user_behavior.py --mode study --tag v7`
 - 生成英文版子图：  
  `python MCM_Sim/26A/src/scripts/validate_q2_user_behavior.py --mode paper --tag v7en --lang en`

## 关键输入（数据/配置）

- 数据：`MCM_Sim/26A/data/SmartphoneMeasurements/user_behavior_dataset.csv`
- 场景：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗/电池参数：
  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`

（这是讲解内容，论文中可删除）  
该对照是“汇总统计→等效 TTE”的代理，所以在论文中建议表述为 *plausible long-horizon behavior*，而不是“严格观测到的完整放电曲线”。

（这是讲解内容，论文中可删除）  
百分比含义：把模型场景的数值当作一个点，放到真实分布里看它处于哪个“经验分位”。例如 **12%** 表示该点小于等于真实样本的 12%，也即更偏向“高消耗/短续航”一侧；**47%** 表示接近人群中位水平。

## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
