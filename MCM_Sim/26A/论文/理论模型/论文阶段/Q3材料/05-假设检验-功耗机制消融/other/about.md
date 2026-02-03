# 05-假设检验-功耗机制消融

## 这张图回答赛题 Q3 的哪一部分？
- **建模假设（modeling assumptions）**：如果我们删掉/弱化某个机理项，预测会怎样变？
- 同时回答赛题 Q2 的追问口径（但放在 Q3 更自然）：
  - drivers of rapid drain：哪些机制最“伤续航”
  - surprisingly little：哪些机制对结果影响很小

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/ablation/40_mechanism_ablation_heatmap.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 消融明细：`MCM_Sim/26A/src/out_reports/q3/ablation.csv`（筛选 `ablation_type=mechanism`）
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.2 Assumptions：机制消融（Mechanism Ablation）”

## 写作要点（建议）
- 一句话解释读图：去掉某机制后 TTE 增加越多 → 该机制越是续航杀手。
- 强调：这是“结构性假设检验”，不是对观测数据拟合（符合赛题对连续时间机理模型的硬要求）。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
