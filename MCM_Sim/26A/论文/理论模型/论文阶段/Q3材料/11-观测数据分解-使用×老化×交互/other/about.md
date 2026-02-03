# 11-观测数据分解-使用×老化×交互

## 这张图回答赛题 Q3 的哪一部分？
- **使用模式波动（fluctuations）**：用真实“使用状态分布”锚定 day-to-day 变化来源；
- **参数取值/历史老化（parameter values / history & aging）**：把 SOH/OCV 等健康状态纳入分解；
- **假设检验**：证明“使用×老化”的交互项不是拍脑袋，而是可量化的二阶效应。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/observed_master_table/01_variance_decomposition_usage_aging.png`
- 本目录内拷贝：`figure.png`

## 数据来源（开源/公开）
- 使用状态（AndroWatts 聚合表）：
  - `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- 电池老化状态表（SOH/OCV）：
  - `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`

## 生成脚本与关联报表
- 实验脚本：
  - `MCM_Sim/26A/src/scripts/run_q3_master_table_experiment.py`
- 关键报表：
  - `MCM_Sim/26A/src/out_reports/q3/observed_master_table/variance_decomposition_usage_aging.csv`
  - `MCM_Sim/26A/src/out_reports/q3/observed_master_table/cells_tte.csv`
- 出图脚本：
  - `MCM_Sim/26A/src/scripts/make_q3_master_table_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.3 使用波动 + 老化：观测数据锚定的方差分解”

## 写作要点（建议）
- 这张图非常贴题面 “realistic usage conditions” 与 “battery history/aging”，建议优先放正文。
- 可一句话给读者结论：使用主效应最大，老化次之，交互项与随机项更小（具体比例见图/报表）。

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。

## 备注（同步说明）
- 2026-02-01：为了改进“随机项显示为 0.0%”导致的误读，本目录 `figure.png` 已同步更新为新版：随机项以 “<0.1%” 显示（数值来自 `variance_decomposition_usage_aging.csv` 的 `frac_seed_within≈3.8e-05`）。

---

## v2 升级图（不替换正文 figure.png，供你挑选/对照）

为回应“单条堆叠图信息密度偏低、且 02/03 容易被误读为‘模型偏离真实’”的问题，我们新增了更偏论文叙事的 v2 图，均未覆盖 `../figure.png`：

- `figure_v2_variance_decomposition_power_bins.png`：
  - 总体分解 + 按观测总功耗三分位分组（低/中/高）分解；
  - 目的：让读者看到“高功耗下老化更显著/更接近欠压边界”的方向（交互效应更直观）。
- `figure_v2_variance_decomposition_bootstrap_ci.png`：
  - 对 phone_test 做 cluster bootstrap 得到 95% CI；
  - 目的：回答评委常问的“换样本/随机状态会不会结论就变了？”（稳健性证据）。
- `figure_v2_aging_penalty_margin_vs_obs_power.png`：
  - new vs eol：展示老化导致的 Δ裕量（risk）随使用强度变化；
  - 目的：用“欠压裕量”这个更贴题背景（突然掉电/欠压）的指标来呈现交互，而不是仅看 TTE。
- `figure_v2_tte_heatmap_power_bins_vs_aging.png`：
  - 将 24×6 压缩为 3×6（低/中/高功耗 × 老化档位）并在格内标注小时数；
  - 目的：保留趋势信息，但显著减少正文图的拥挤与重叠。

对应的数据版本（便于你/AI 直接读取，不依赖图像 OCR）：
- `data_v2_power_bins_decomposition.csv`
- `data_v2_bootstrap_ci.csv`
- `data_v2_aging_penalty_new_vs_eol.csv`
- `data_v2_tte_heatmap_power_bins.csv`
- `data_v2_cells_compare.csv`

以及跨电芯稳健性对照图：
- `figure_v2_variance_decomposition_cells_compare.png`
