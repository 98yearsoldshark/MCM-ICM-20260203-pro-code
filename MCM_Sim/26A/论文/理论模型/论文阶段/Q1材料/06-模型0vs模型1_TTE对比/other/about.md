# about

- 本图文件：`figure.png`
- 图意：在五类典型使用场景（S1–S5）下，对比两种停止准则的耗尽时间 TTE（雷达图叠加）：
  - Model-0：SOC 阈值终止（soc_min）
  - Model-1：截止电压终止（V_cut）
- 图形设置要点：
  - 5 个顶点对应 5 场景（S1–S5）；
  - 半径为对数刻度（默认刻度 2/4/8/16/32h），更适合同时容纳“待机长续航”和“高负载短续航”；
  - 底层网格与外框均为五边形（避免圆弧网格带来的视觉误读）。
- 场景配置（仅用于本图的 5 场景口径）：`MCM_Sim/26A/src/configs/scenarios_q1_v1_5cases.json`
- 生成脚本：`MCM_Sim/26A/src/scripts/make_q1_tte_radar_model0_vs_model1.py`
- 复现命令（会同时生成 paper/study，并输出 data.csv）：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_radar_model0_vs_model1.py --mode both
```

## 旧版本备份（如需回滚/追溯）

本文件夹在重构前曾用于“Model-0 vs Model-1 的 TTE 对比图”。为避免覆盖丢失，旧图与旧数据已备份到：

- `figure_old_tte_model0_vs_model1.png`
- `data_old_tte_model0_vs_model1.csv`

此外，本次改动前误生成过“场景口径表（图片）”，也已保留到：
- `figure_table_scenarios_paper.png`
- `figure_table_scenarios_study.png`
- `data_table_scenarios.csv`
