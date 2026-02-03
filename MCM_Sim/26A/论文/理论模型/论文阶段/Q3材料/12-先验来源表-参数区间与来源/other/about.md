# 12-先验来源表-参数区间与来源

## 这张“表格图”回答赛题 Q3 的哪一部分？

Q3 的核心是“当你改变建模假设/参数取值/使用波动时，预测如何变化”。其中：
- **参数取值改变** 的结论高度依赖“参数先验范围”；
- 若不说明先验来自哪里，任何敏感性/方差分解都可能被质疑为“主观设定”。

因此，这张表用于给 Q3 的敏感性分析提供一个 **可审查、可引用、可复现** 的输入口径。

## 图源与生成位置

- 本目录：
  - `figure.png`：论文可直接插入的表格图（由脚本生成）
  - `other/data.csv`：表格数据版本（便于核对/二次排版）
  - `other/table_zh.md`：同一份表的 Markdown 版本（便于直接粘贴进论文）

## 生成脚本

- `MCM_Sim/26A/src/scripts/make_q3_prior_sources_table.py`

## 关键数据锚定来源（开源）

- AndroWatts（能耗分解/部件占比锚定）：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- 电池状态表（SOH 分布锚定）：`MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`

## 说明（评委口径）

- 表中 “tight 先验” 仅用于 sanity check：验证“不确定性分解/敏感性方向”是否符合直觉，并不宣称这是唯一正确的范围。
- 对于暂缺统一公开标定的数据项，表中明确标注为“工程先验”，并指出未来可用真实数据收窄的方向（符合赛题 data-as-support 的写法）。

