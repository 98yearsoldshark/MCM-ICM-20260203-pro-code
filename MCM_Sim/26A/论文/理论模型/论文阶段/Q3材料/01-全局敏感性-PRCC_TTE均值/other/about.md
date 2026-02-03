# 01-全局敏感性-PRCC_TTE均值

## 这张图回答赛题 Q3 的哪一部分？
- **参数取值（parameter values）**：在合理先验范围内扰动参数，观察预测（这里是平均 TTE）如何变化。
- 用 PRCC（秩偏相关）回答“哪些参数最关键、方向如何、跨场景是否一致”。

## 场景覆盖（与 Table 2 对齐）
- 已补充 **Browsing/Social Media（浏览/社交媒体）** 对应的独立场景：`S1b_browse`（配置见 `src/configs/scenarios_v0.json`）。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/sensitivity/01_prcc_tte_mean_h.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - PRCC 原始表：`MCM_Sim/26A/src/out_reports/q3/global_prcc.csv`
  - Top5 汇总：`MCM_Sim/26A/src/out_reports/q3/global_prcc_top5.csv`
  - 采样参数表：`MCM_Sim/26A/src/out_reports/q3/global_param_samples.csv`
  - 每个样本的输出：`MCM_Sim/26A/src/out_reports/q3/global_outputs.csv`
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 稳定性复现实验（N / K 扩容对照）

评委常见质疑是“换个随机种子/多采样一点，排名会不会变？”。我们用嵌套设计做了稳定性检验：
- 脚本：`MCM_Sim/26A/src/scripts/run_q3_prcc_stability.py`
- 输出：`MCM_Sim/26A/src/out_reports/q3/sanity_prcc_stability/`
  - 本目录同步拷贝：`other/stability_summary.csv`、`other/prcc_top5.csv`、`other/seed_runs_long.csv`

结论（基线 N=240,K=4；对照 N=600,K=8）：
- 对 `S4_mixed_day` 与 `S3_gaming`，**top5 参数集合的 Jaccard 相似度均为 1.0**（排名集合完全一致）。
- PRCC 数值会随 N/K 略有变化，但“谁最敏感/方向如何”的结论保持稳定。

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.1 参数敏感性（Global / PRCC）”

## 使用提示（写作时怎么说）
- 先解释：PRCC 的含义（控制其他参数后的单调影响强弱）。
- 再解释：为什么要多 seed 重复（减少随机过程噪声）。
- 最后给结论：跨场景哪些参数长期主导、哪些是场景特异（例如无线/计算密集场景）。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
