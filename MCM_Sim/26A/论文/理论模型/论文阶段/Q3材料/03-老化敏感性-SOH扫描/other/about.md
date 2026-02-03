# 03-老化敏感性-SOH扫描

## 这张图回答赛题 Q3 的哪一部分？
- **参数取值（parameter values）**：老化相关参数（SOH、增阻强度等）变化时，TTE 预测如何变化。
- 同时对齐题面：电池“history/aging”对续航和提前关机风险的影响。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/aging/30_aging_soh_scan.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 扫描结果：`MCM_Sim/26A/src/out_reports/q3/aging_scan.csv`
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 扫描点如何选择（避免“拍脑袋”）
- 我们支持两种方式：
  - 手工指定：`--soh-list 1.0,0.9,0.8,...`
  - **观测锚定（推荐）**：`--soh-list auto`，从 `data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv` 的 SOH 分布提取分位点作为扫描点（更可解释、可复现）。
- 本图默认使用观测锚定的分位点（详见 `other/data.csv` 的 SOH 列）。

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.1 参数敏感性：老化（SOH 扫描）”

## 写作要点（建议）
- 明确我们把 SOH 同时映射到 **容量衰减** 与 **内阻增长** 两条机理路径（而非单纯回归）。
- 强调：不同场景对 SOH 的敏感性不同（高负载场景更容易欠压，曲线更陡）。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
