# 表格v2 生成说明

本目录由脚本自动生成，用于补全 Q2 写作中的两张关键表格：

- 表 7-1：不确定参数集合（与代码 `Q2UQSample` 的抽样口径一致）
- 表 9-1：TTE 汇总（点估 + 区间 + 风险概率 + Top-2 不确定源）

## 输入来源

- Q2 报表：`MCM_Sim/26A/src/out_reports/q2/`（已存在产物，不重新跑仿真）
- 场景配置：`MCM_Sim/26A/src/configs/scenarios_v0.json`
- 功耗/电池基准配置：
  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`
  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`
- 参量估计锚定（用于表内“数据依据/来源”的文字）：`MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/参数估计汇总表.csv`

## 复现

在仓库根目录运行：

```bash
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/15-补数据/表格v2/scripts/build_tables_v2.py"
```
