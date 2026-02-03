# about

## 这组文件包含什么

- `figure.png`：全程电压对比（预测 vs 观测，含 V_cut 与 TTE 竖线）
- `figure_zoom.png`：最低点附近局部放大（对齐最低点，诊断尖峰形态）
- `residual_hist.png`：残差直方图
- `rmse_by_step.png`：按 Step_Index 分解 RMSE

## 来源与复现

- 原始输出目录：
  - `MCM_Sim/26A/src/out_plots/model1/paper/validation/10_16_2015_initial_capacity_sp20_1/`
  - `battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth/`
- 对应验证报表（含数值指标）：
  - `MCM_Sim/26A/src/out_reports/validation/10_16_2015_initial_capacity_sp20_1/`
  - `battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth.json`
- 数据集（CALCE UMD，SP20-1）：
  - `MCM_Sim/26A/data/calce-umd/extracted/battery-data/SP/10_16_2015_Initial capacity_SP20-1.xlsx`
- 使用配置（ECM 参数）：
  - `MCM_Sim/26A/src/configs/ablation/battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth.json`
- 生成脚本：
  - `MCM_Sim/26A/src/scripts/validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py`
- 复现命令（示例）：

```bash
PYTHONPATH=MCM_Sim/26A/src \\
python MCM_Sim/26A/src/scripts/validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py \\
  --xlsx \"MCM_Sim/26A/data/calce-umd/extracted/battery-data/SP/10_16_2015_Initial capacity_SP20-1.xlsx\" \\
  --phone \"MCM_Sim/26A/src/configs/ablation/battery_calce_sp20_1_ecmfit_r0fixed_2rc_tauconstrained_diffz_vgate_relax2stage_10_16deepfix_v3smooth.json\"
```

## 关键指标（来自对应 JSON 报表）

- overall：RMSE=25.443 mV，MAE=18.539 mV
- phone_domain：TTE 误差=−90.9 s（−0.459%）
- 备注：该数据集的 `soc0_used≈0.107` 为脚本在起始休止段自动估计得到（见对应 JSON）。

