# Q2 提炼：TTE / 不确定性 / drivers / 观测对照（给 Q2 工作者）

来源：`0131-0949-Q123混合.md`（no7 混合稿）中的 Q2 相关内容。

目的：把 Q2 交付物与“已经有的脚本/输出”对齐，方便你直接做实验、补齐赛题口径，并写进论文。

---

## 1) Q2 题面要求（要点）

Q2 要求在连续时间机理模型基础上，对不同初始电量与使用场景输出 `TTE(Time-to-Empty)`，并做到：

1) 多场景 + 多 SOC0：给出 TTE（矩阵/表格更好）并解释差异；
2) 与观测或合理行为对照（observed or plausible behavior）；
3) 量化不确定性（区间/分布），说明不确定性来源；
4) drivers：指出哪些活动/条件导致最大续航下降，哪些“surprisingly little”；
5) 说明模型哪里表现好/差（边界条件）；
6) 给建议（用户/OS 的可执行策略）。

---

## 2) no7 给出的 Q2 输出清单（建议全部做）

- 五场景 TTE：均值 + 95%CI（或 p05/p50/p95）；
- 欠压/不可供电概率：`Pr(V_term<=V_cut)`、`Pr(Δ<0)`；
- 关机剩余 SOC 分布：证明“欠压提前关机”；
- 模块能量分解：占比（share）+ 交互能耗；
- drivers：边际贡献 `ΔTTE`（反事实）；
- 敏感性：局部 + PRCC/Spearman + 消融；
- 约束失败统计：证明模型不是“回归凑曲线”。

---

## 3) 当前代码库里 Q2 已实现哪些（直接可用）

### 3.1 图（paper/study 两套）

入口：`MCM_Sim/26A/src/scripts/make_q2_plots.py`

输出目录：`MCM_Sim/26A/src/out_plots/q2/{paper|study}/`

已有图（示例）：
- `tte/01_tte_matrix.png`：场景×SOC0 的平均 TTE
- `uq/02_tte_distribution_soc1.png`：TTE 分布（violin）
- `uq/07_uq_spread_ranking.png`：不确定性宽度排名（哪里更不可预测）
- `variants/05_variants_compare.png`：变体对照
- `drivers/03_drivers_tornado.png`：策略动作 drivers（反事实 ΔTTE）
- `drivers/08_mechanism_drivers_tornado.png`：机制 drivers（去掉尾态/弱信号/后台等）
- `drivers/09_component_drivers_tornado.png`：组件 drivers（移除屏幕/CPU/无线等）
- `drivers/10_component_driver_matrix.png`：按场景的 drivers 矩阵（回答 “in each case”）
- `energy/04_energy_share.png`：能耗占比（含交互项）

### 3.2 表（写论文/做表格用）

入口：`MCM_Sim/26A/src/scripts/run_q2_report.py`

输出目录：`MCM_Sim/26A/src/out_reports/q2/`

核心 CSV：
- `tte_samples.csv` / `tte_summary.csv`
- `termination_stats.csv`（终止原因概率）
- `soc_end_at_cutoff.csv`（欠压截止的剩余 SOC 证据）
- `uq_spread.csv`（不确定性宽度/CV）
- `drivers_delta.csv`（策略动作）
- `mechanism_drivers_delta.csv`（机制消融）
- `component_drivers_delta.csv` / `component_drivers_matrix.csv`（组件 drivers）
- `energy_share.csv`

---

## 4) “observed behavior” 对照：推荐数据与当前进度

赛题明确要求对照观测或合理行为。当前我们已接入一个公开观测数据源用于功耗量级对照：

### 4.1 AndroWatts（Zenodo，1000 条测试聚合）

数据位置：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`

验证脚本：`MCM_Sim/26A/src/scripts/validate_q2_open_data.py`

输出：
- 报表：`MCM_Sim/26A/src/out_reports/q2/validation_open_data/metrics.csv`
- 图像：`MCM_Sim/26A/src/out_plots/q2/{paper|study}/observed_open_data/`

该对照的定位：验证“总功耗量级 + 主要 drivers（屏幕/CPU/GPU/网络）的相对关系”与公开测量一致，为 Q2 的 plausibility/validation 加分。

---

## 5) Q2 还可以进一步补强的点（对齐 no7 的 Q3 与赛题口径）

建议优先级（从“赛题硬口径”到“Z 奖加分”）：

1) 全局敏感性（PRCC/Spearman）：用 `tte_samples.csv` 的抽样结果直接计算“参数 drivers 排名”（更硬的 Q3 证据链）。
2) 显式加入 `η_PMIC`（电源转换效率）并纳入敏感性：作为缺数据时的合理假设参数（no7 提到 η_PMIC）。
3) 用 `SmartphoneMeasurements.zip` 的 Monsoon 实测功耗曲线校准网络/通信模块的量级（让 observed 更硬）。

