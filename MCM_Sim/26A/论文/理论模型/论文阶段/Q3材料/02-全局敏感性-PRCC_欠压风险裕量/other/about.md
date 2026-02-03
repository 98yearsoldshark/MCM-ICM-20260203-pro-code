# 02-全局敏感性-PRCC_欠压风险裕量

## 这张图回答赛题 Q3 的哪一部分？
- **参数取值（parameter values）**：参数扰动对“欠压/电压崩塌风险”指标的影响。
- 重点对齐题面现象：同样用法却有时“掉电很快/提前关机”。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/sensitivity/04_prcc_min_headroom_margin.png`
- 本目录内拷贝：`figure.png`

## 指标口径（写作建议）
- `min_headroom_margin` 是一个 **无量纲裕量**：在每个时刻计算“距离电压崩塌边界还有多近”，并取全程最小值。
- 值越接近 0，代表越接近“电压解不存在/欠压截止”的边界，小的负载突发或内阻增加都可能触发提前关机。

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - PRCC 原始表：`MCM_Sim/26A/src/out_reports/q3/global_prcc.csv`（输出列 `min_headroom_margin`）
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 稳定性复现实验（N / K 扩容对照）

因为风险类指标更容易被质疑“你换个随机种子是不是就变了？”，我们专门对 PRCC 的 top5 做了嵌套稳定性检验：
- 脚本：`MCM_Sim/26A/src/scripts/run_q3_prcc_stability.py`
- 输出：`MCM_Sim/26A/src/out_reports/q3/sanity_prcc_stability/`
  - 本目录同步拷贝：`other/stability_summary.csv`、`other/prcc_top5.csv`、`other/seed_runs_long.csv`

结论（基线 N=240,K=4；对照 N=600,K=8）：
- 对 `S4_mixed_day` 与 `S3_gaming`，`min_headroom_margin` 的 **top5 参数集合 Jaccard 相似度均为 1.0**（集合完全一致）。

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.1 参数敏感性：风险指标（欠压/崩塌裕量）”

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
