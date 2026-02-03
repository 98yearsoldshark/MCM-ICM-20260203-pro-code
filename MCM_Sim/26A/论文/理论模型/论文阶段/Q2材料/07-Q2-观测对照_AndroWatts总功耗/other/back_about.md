# back_ 版本说明：参量估计回填后的 AndroWatts 总功耗对照

本 back_ 版本用于回答“参量估计得到的物理量级，回填到功耗模型后，与公开观测数据的贴合度如何？”。

与本目录原始 `figure.png` 的区别：
- 原始图使用的是 `src/configs/power_params_v2_no7_awcal_mo_v2.json`（no7 升级 + AndroWatts 多目标校准版），目标是尽可能贴合 AndroWatts。
- back_ 图使用的是 **参量估计回归得到的初值/量级**（更“数据驱动+可解释”，但不保证比多目标校准更拟合）。

## 对应文件

- `../back_figure.png`：paper 版（不含长段解释）
- `back_figure_study.png`：study 版（带更多标注）
- `back_data.csv`：逐样本观测 vs 预测（W）
- `back_metrics.csv`：汇总指标（r/MAE/MAPE）

## 生成方式（可复现）

命令（会写到新的 out_plots/out_reports 目录，不覆盖原产物）：

```bash
python MCM_Sim/26A/src/scripts/validate_q2_open_data.py \
  --power "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/suggested_configs/power_params_v1_stateful_paramest_0202.json" \
  --out-report-dir "MCM_Sim/26A/src/out_reports_back_paramest/q2/validation_open_data" \
  --out-plot-dir "MCM_Sim/26A/src/out_plots_back_paramest" \
  --max-n 250 --seed 0 --seeds-per-case 20
```

关键输入：
- AndroWatts 聚合数据：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- 回填功耗参数：`MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/suggested_configs/power_params_v1_stateful_paramest_0202.json`

## 与原图的指标对比（total 总功耗）

- 原始（多目标校准版）：r=0.915，MAE=0.345 W，MAPE=15.3%，pred_mean=2.579 W
- back_（参量估计回填）：r=0.904，MAE=0.534 W，MAPE=25.3%，pred_mean=2.770 W

解释口径建议：
- 我们把“参量估计回归结果”当作**物理量级的可解释初值**；
- 若要追求最佳拟合（Q2 观测对照），仍以“多目标校准版配置”作为主结果；
- back_ 版本更适合作为 Q3 的“假设/参数改变后，预测如何变化”的支撑材料。
