# 07-假设检验-电池结构1RCvs2RC

## 这张图回答赛题 Q3 的哪一部分？
- **建模假设（modeling assumptions）**：电池端“极化支路结构”选 1RC 还是 2RC，会不会改变续航预测？
- 这是一个典型的“结构假设敏感性”（结构变了，但我们尽量保持等效电阻口径一致，避免混杂）。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/ablation/42_battery_structure_ablation.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 明细：`MCM_Sim/26A/src/out_reports/q3/ablation.csv`（筛选 `ablation_type=battery_structure`）
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.2 Assumptions：结构假设（1RC vs 2RC）”

## 备注（可选增强）
- 若正文空间允许，可在附录再给 1 张代表性轨迹图（电压/极化分解），让读者直观看到“快/慢支路”的物理意义。
  - 例如：`MCM_Sim/26A/src/out_plots/q3/paper/traces/60_s5_voltage_1rc_vs_2rc.png`

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
