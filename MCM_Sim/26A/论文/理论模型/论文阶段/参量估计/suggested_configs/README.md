# suggested_configs（参量估计建议配置）

本目录由脚本自动生成：`scripts/10_generate_suggested_configs.py`

来源（估计结果）：
- `MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/参数估计汇总表.md`

生成的文件：
- `power_params_v0_paramest_0202.json`
  - 基于 `src/configs/power_params_v0.json`，回填：screen(P0,k)、cpu.k、gpu.k
- `power_params_v1_stateful_paramest_0202.json`
  - 基于 `src/configs/power_params_v1_stateful.json`，回填：screen/cpu/gpu + Wi‑Fi 的 `tau_tail_s` 与 `e_per_mb_J`
- `phone_default_v2_thermal_paramest_0202.json`
  - 基于 `src/configs/phone_default_v2_thermal.json`，回填：`R_th_K_per_W`、`C_th_J_per_K`

建议用法：
1) 作为对照实验（与原 config 并行跑），观察结果变化；  
2) 作为后续校准/随机搜索的初值或先验范围；  
3) 不建议直接覆盖 `src/configs/` 的默认文件（保留可复现基线）。  
