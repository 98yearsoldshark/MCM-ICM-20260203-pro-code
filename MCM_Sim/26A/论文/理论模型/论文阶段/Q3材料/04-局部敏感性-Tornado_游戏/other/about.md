# 04-局部敏感性-Tornado_游戏

## 这张图回答赛题 Q3 的哪一部分？
- **参数取值（parameter values）**：在基准点附近（已标定/默认参数）做小幅扰动，预测结果（TTE）变化有多大。
- 给读者一个“工程直觉”：哪些参数在当前手机/电池状态下最关键。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/sensitivity/10_local_tornado_S3_gaming.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 局部敏感性表：`MCM_Sim/26A/src/out_reports/q3/local_sensitivity.csv`
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.1 参数敏感性：Local tornado（选一个代表场景即可）”

## 写作要点（建议）
- 强调：这是“局部”结论（只对基准点附近有效），与“全局 PRCC”互补。
- 建议只放 1 张（如游戏/导航等高功耗场景），避免正文过多 tornado 图占版面。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
