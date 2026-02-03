# configs/

本目录存放“参数集/场景定义”等配置文件（JSON/YAML）。

后续通常会加入：
- `phone_default.json`：电池标称容量、截止电压、热参数等。
- `power_default.json`：组件级功耗系数（屏幕/CPU/网络/…）。
- `scenarios.json`：命名使用场景及其时间表/随机生成配置。

当前已提供：
- `scenarios_v0.json`：Model-0/Model-1 共用的“标准场景集”草案（分段常值 schedule）。
  - `repeat=true` 表示该 schedule 循环重复直到电池耗尽（用于 TTE）。
  - `variants` 支持两种覆写：
    - `overrides`：对整个场景的字段做统一覆写（作用于所有 schedule 段）。
    - `segment_overrides`：对指定段（0-based 段索引）做覆写。
  - 说明：已预留字段 `ambient_temp_c`（环境温度，°C），用于 Model-2 热模型（默认 23°C）。
- `phone_default_v0.json`：通用默认电池参数（4000mAh@3.85V ≈ 15.4Wh），用于 Model-0 快速跑通。
- `phone_default_v1_ecm.json`：通用默认电池参数（含 ECM：OCV 曲线 + R0/R1/C1 + 截止电压），用于 Model-1。
- `phone_default_v2_thermal.json`：通用默认电池参数（ECM + 热参数 + 温度影响系数），用于 Model-2。
- `phone_default_v3_aging.json`：通用默认电池参数（ECM + 热参数 + 老化参数：容量衰减/内阻增长），用于 Model-3。
- `power_params_v0.json`：Model-0 名义功耗参数（单位 W），用于端到端流程验证（后续应校准/替换）。
- `power_params_v0.json` 的不确定性范围目前在代码中以“组尺度因子”形式给出（参见 `mcm26a/uq/model0_uq.py`）。

校准产物（由脚本生成）：
- `battery_calce_sp20_1.json`：由一份 CALCE 低电流 OCV 测试数据拟合得到的电池配置（包含更真实的 OCV-SOC 曲线）。
  - 生成脚本：`src/scripts/calibrate_calce_ocv.py`
- `battery_calce_sp20_1_ecmfit.json`：在 `battery_calce_sp20_1.json` 的 OCV 基础上，进一步拟合常参 ECM（R0/R1/C1）的版本。
  - 生成脚本：`src/scripts/calibrate_model1_ecm_from_calce_sp20_1.py`
- `battery_calce_sp20_1_ecmfit_r1soc_unweighted.json`：把 R1 扩展为 R1(SOC) 分段线性曲线（未加权，偏重拟合放电段）。
  - 生成脚本：`src/scripts/calibrate_model1_ecm_socdep_from_calce_sp20_1.py --w-step4 1 --w-step4-early 1`
- `battery_calce_sp20_1_ecmfit_r1soc_balanced.json`：R1(SOC) 版本（加权折中：兼顾放电与休止早期松弛）。
  - 生成脚本：`src/scripts/calibrate_model1_ecm_socdep_from_calce_sp20_1.py --w-step4 2 --w-step4-early 4`
- `battery_calce_sp20_1_ecmfit_r0fixed_r1soc.json`：推荐版本（分阶段辨识）：先用含阶跃/脉冲的数据估计 R0，再固定 R0 用低电流数据拟合 R1(SOC)+C1（用于修复“优化变差”：低电流拟合导致 R0 触底、验证集变差）。
  - 生成脚本：`src/scripts/calibrate_model1_ecm_r0fixed_r1soc_from_calce_sp20_1.py`
- `battery_calce_sp20_1_ecmfit_r0r1soc.json`：进一步把 R0 也扩展为 R0(SOC)（当前实验性，仍只用同一份数据）。
  - 生成脚本：`src/scripts/calibrate_model1_ecm_socdep_r0r1_from_calce_sp20_1.py`

SOC 相关曲线字段（可选）：
- `battery.ecm.R0_curve`：`{type:"piecewise_linear", points:[[soc, R0_ohm], ...]}`
- `battery.ecm.R1_curve`：`{type:"piecewise_linear", points:[[soc, R1_ohm], ...]}`
- 若提供曲线，则 Model-1/2/3 会优先使用曲线；否则退化为常数 `R0_ohm/R1_ohm`。
