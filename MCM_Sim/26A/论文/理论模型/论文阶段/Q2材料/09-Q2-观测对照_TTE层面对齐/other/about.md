# 图 09：观测对照（TTE 层面对齐：E_batt / P_mean）

## 对应赛题 Q2 的哪个要求？

- “Compare predictions to observed or plausible behavior”  
  且是 **TTE 层面**（不是仅对照瞬时功耗）。

## 本文件夹包含

- `02_tte_compare_per_test.png`：论文版（paper，per-test：点数更多）
- `02_tte_compare_per_test_study.png`：学习版（study，per-test）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/observed_tte_trace_smartphone_measurements/02_tte_compare_per_test.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/observed_tte_trace_smartphone_measurements/02_tte_compare_per_test.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_tte_trace_smartphone_measurements.py`
  - 推荐命令（per-test，冲高奖口径：点数更充分）：
    - `PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/validate_q2_tte_trace_smartphone_measurements.py --granularity test --seeds 10 --dt 10 --cpu-load-mode linear --wifi-e-per-mb-j 0.5`

## 关键输入（数据/配置）

- SmartphoneMeasurements：`MCM_Sim/26A/data/SmartphoneMeasurements/SmartphoneMeasurements.zip`
- 电池参数（用于 E_batt 与仿真）：`MCM_Sim/26A/src/configs/phone_default_v3_aging.json`
- 功耗参数（stateful）：`MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`

## 对应报表（可复核数值）

- `MCM_Sim/26A/src/out_reports/q2/validation_tte_trace_smartphone_measurements/per_test_tte.csv`

（这是讲解内容，论文中可删除）  
观测侧的 $TTE_{obs}^{equiv}$ 是“短时平均功耗 → 能量换算”的代理，不等同“整机放电到关机”。论文中建议明确写成 “observed proxy / plausible TTE evidence” 以避免审稿人误解。

另外，本图在生成时对模型的网络参数做了一个**可追溯的量级校准**（不改配置文件）：
- `--wifi-e-per-mb-j 0.5`：把 `rrc.e_per_mb_J[wifi]` 临时覆盖到 0.5 J/MB（与 SmartphoneMeasurements 的单位数据能耗量级一致），用于避免网络场景系统性高估 TTE。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
