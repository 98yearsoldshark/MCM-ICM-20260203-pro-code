# scripts/

本目录存放命令行入口脚本（可直接运行，产出图表/表格/结果文件）。

后续可能会加入：
- `run_scenarios.py`：批量仿真命名使用场景并导出结果。
- `run_sensitivity.py`：全局敏感性 / 不确定性传播。
- `make_figures.py`：生成论文用图表与表格。

当前已提供：
- `fetch_data.py`：一键拉取/同步大体积公开数据（CALCE/NASA/BatteryArchive/BIL 等），用于把仓库整理到 GitHub 时“只提交脚本，不提交数据”。
- `run_model0_summary.py`：用 Model-0 批量计算标准场景 TTE，并输出功耗均值概览。
- `run_model0_policy_sweep.py`：用 Model-0 扫描“省电策略/反事实”，输出 TTE 增益排序。
- `run_model0_uq.py`：对 Model-0 做不确定性传播，输出 TTE 分位数区间与粗略敏感性（相关性）。
- `run_model0_breakdown.py`：对单一场景输出能耗贡献分解（Wh 与占比）。
- `run_model1_summary.py`：用 Model-1（ECM + 截止电压事件）批量计算标准场景 TTE（用于与 Model-0 对比）。
- `run_model1_policy_sweep.py`：用 Model-1（ECM）扫描“省电策略/反事实”，输出 TTE 增益排序（可与 Model-0 对比稳健性）。
- `run_model2_summary.py`：用 Model-2（ECM + 热模型）批量计算标准场景 TTE，并输出温升信息（用于解释低温/高负载续航变化）。
- `run_model2_policy_sweep.py`：用 Model-2（ECM + 热模型）扫描“省电策略/反事实”，输出 ΔTTE 与 Δ温升（更贴近真实“续航-发热”权衡）。
- `run_model3_summary.py`：用 Model-3（ECM + 热模型 + 老化）批量计算标准场景 TTE，并输出老化状态变化（容量衰减/内阻增长）。
- `run_model3_cycles.py`：用 Model-3 做多次“放电到 cutoff”循环，观察 TTE 随老化退化（用于寿命讨论）。
- `run_model3_policy_sweep.py`：用 Model-3 扫描策略的“续航-温升-老化”三重影响（用于延寿建议与权衡分析）。
- `calibrate_calce_ocv.py`：仅用一份 CALCE 低电流 OCV 测试数据拟合 OCV-SOC 曲线，并生成可用于 Model-1/2/3 的电池配置文件。
- `calibrate_model1_ecm_from_calce_sp20_1.py`：只用同一份数据，进一步校准常参 ECM（R0/R1/C1）并可迭代回写 OCV（用于“先跑通闭环”的 baseline）。
- `calibrate_model1_ecm_socdep_from_calce_sp20_1.py`：把 R1 扩展为 R1(SOC) 曲线（分段线性、SOC 越低 R1 不减），并支持对休止段加权以兼顾松弛。
- `calibrate_model1_ecm_socdep_r0r1_from_calce_sp20_1.py`：进一步把 R0 也扩展为 R0(SOC) 曲线（实验性/可继续迭代）。
- `calibrate_model1_ecm_r0fixed_r1soc_from_calce_sp20_1.py`：分阶段辨识：先用含阶跃/脉冲的数据估计 R0，再固定 R0 用低电流数据拟合 R1(SOC)+C1（用于修复“优化变差”）。
- `make_model0_plots.py`：批量生成 Model-0 的可视化图（paper/study 两套），输出到 `src/out_plots/`。
- `make_model1_plots.py`：批量生成 Model-1（ECM）的可视化图（paper/study 两套），输出到 `src/out_plots/`。
- `make_q2_plots.py`：批量生成 Q2 图像（TTE 矩阵 / 不确定性分布 / variants / drivers / 能耗占比 / 温度对照 / 参数敏感性热力图，paper/study 两套）。默认使用 `power_params_v2_no7_awcal_mo_v2.json`（no7 升级 + AndroWatts 多目标校准版：更贴近公开测量的总功耗量级，且兼顾主要组件分解）；其中“参数敏感性热力图”会读取 `src/out_reports/q2/param_sensitivity.csv`（需先跑 `run_q2_report.py`）。
- `run_q2_report.py`：生成 Q2 数值报表（`tte_samples.csv` / `uq_samples.csv` / `tte_summary.csv` / `termination_stats.csv` / `soc_end_at_cutoff.csv` / `uq_spread.csv` / `param_sensitivity.csv` / `param_sensitivity_overall.csv` / `temperature_variants_stats.csv` / `drivers_delta.csv` / `drivers_matrix.csv` / `mechanism_drivers_delta.csv` / `component_drivers_delta.csv` / `component_drivers_matrix.csv` / `energy_share.csv`），输出到 `src/out_reports/q2/`。
- `run_q2_ablation.py`：Q2 小型消融实验：逐项移除（尾态/后台/交互/弱信号）观察 TTE 变化，用于定位“加入机制是否合理”并形成论文证据链。
- `run_q2_recommendations.py`：把 Q2 的 drivers/敏感性/终止概率等结果自动汇总成“可执行建议”，输出到 `src/out_reports/q2/recommendations/`（md + csv）。
- `run_q2_diagnostics_summary.py`：Q2 诊断总表（模型好/差边界）：汇总各条证据链的关键指标（功耗量级对照/通信能耗对照/TTE 代理对照/dt 稳定性等），输出到 `src/out_reports/q2/diagnostics/`。
- `run_q2_little_effect.py`：Q2 “surprisingly little” 定量口径与自动输出：基于 `component_drivers_matrix.csv` 与 `tte_summary.csv` 输出 `little_effect_factors.csv` 及配套图像到 `src/out_reports/q2/little_effect/` 与 `src/out_plots/q2/{paper|study}/little_effect/`。
- `make_q2_trajectory_plots.py`：Q2 场景轨迹图包：为每个场景×SOC0 输出 SOC/V/T/P 的 2x2 面板图（paper/study），用于解释“为什么不同场景 TTE 差这么多”，输出到 `src/out_plots/q2/{paper|study}/trajectories/`。
- `run_q2_calibration_effect.py`：Q2 校准前/后对比：对两份 run_q2_report 输出目录做标准化对比汇总（TTE/终止概率/drivers 排名变化）并出图，输出到 `src/out_reports/q2/calibration_effect/` 与 `src/out_plots/q2/{paper|study}/calibration_effect/`。
- `calibrate_q2_power_multiobjective.py`：Q2 功耗参数多目标校准（AndroWatts total+组件 + SmartphoneMeasurements 的 Wi‑Fi J/MB 量级软约束），输出新参数 JSON 与 before/after 指标到 `src/out_reports/q2/calibration_multiobjective*/`。
- `run_q2_numerical_stability.py`：Q2 数值稳定性检验（dt sweep），输出 `dt_sweep.csv`/`dt_sweep_summary.csv` 与图像到 `src/out_reports/q2/numerical_stability/` 与 `src/out_plots/q2/{paper|study}/numerical_stability/`。
- `validate_q2_tte_proxy_current.py`：Q2 代理 TTE 对照链条：用 AndroWatts 的观测电流 I_obs 构造“常流到 0 的 TTE 上界”，并与“欠压截止的 TTE（模型）”对比解释提前关机，输出到 `src/out_reports/q2/validation_tte_proxy_current/` 与 `src/out_plots/q2/{paper|study}/observed_tte_proxy_current/`。
- `validate_q2_tte_trace_smartphone_measurements.py`：Q2 TTE 层面对照（SmartphoneMeasurements）：用 Monsoon 实测平均功耗构造 `TTE_obs_equiv=E_batt/P_mean`，并与模型仿真 TTE 对比，输出到 `src/out_reports/q2/validation_tte_trace_smartphone_measurements/` 与 `src/out_plots/q2/{paper|study}/observed_tte_trace_smartphone_measurements/`。
- `run_q2_validation_multi_summary.py`：Q2 多数据集实验（`out_reports/q2/validation_multi_*`）的只读汇总脚本：读取各验证子目录的 CSV（不跑仿真）并生成 `summary.md` 与关键指标表，便于快速判断“哪里贴近真实/哪里偏差最大”。推荐在你手动分别跑完各数据集验证脚本后使用。
- `run_q2_full_suite.py`：Q2 一键复现套件：串行跑完 Q2 主线报表、图像、公开对照与稳定性实验（用于固定“满分口径”的证据链）。
- `run_q3_report.py`：生成 Q3 数值报表（全局敏感性 PRCC/Spearman（含 SOH/α_R）、局部敏感性、结构消融、老化 SOH 扫描、仅随机过程波动、以及“不确定性来源分解”），输出到 `src/out_reports/q3/`。同时生成 `global_prcc_top5.csv` 便于直接写论文。
  - 为兼顾质量与耗时，支持把 `--replicates` 细分为：`--replicates-fluct/--replicates-local/--replicates-ablation/--replicates-aging`（不填则沿用 `--replicates`）。
- `make_q3_plots.py`：批量生成 Q3 图像（敏感性热力图/局部 tornado/机制消融/老化扫描/随机波动分布，paper/study 两套），输出到 `src/out_plots/q3/`。
- `make_q3_trace_examples.py`：生成 Q3 的“代表性轨迹图”（paper/study 两套），用于在正文中直观展示“结构假设/外部条件变化”导致的曲线差异，输出到 `src/out_plots/q3/{paper|study}/traces/`。
- `run_q3_open_data_experiment.py`：Q3 数据集实验（AndroWatts）：把 `data/open_data/.../aggregated.csv` 映射为“真实使用状态”样本，跑 TTE 的 seed 波动并做“来源分解（使用状态差异 vs 随机过程）”，输出到 `src/out_reports/q3/observed_open_data/`。
- `make_q3_open_data_plots.py`：为上述数据集实验出图（paper/study 两套），输出到 `src/out_plots/q3/{paper|study}/observed_open_data/`。
- `run_q3_master_table_experiment.py`：Q3 数据集实验（AndroWatts × 老化状态表）：在“真实使用状态（phone_test）”与“电池老化状态（battery_state）”的笛卡尔组合上跑 Model-3，并把 TTE 波动来源分解为 usage/aging/interaction/seed，输出到：
  - 报表：`src/out_reports/q3/observed_master_table/`（`cells_tte.csv`、`variance_decomposition_usage_aging.csv`）
  - 图像：见下一条
- `make_q3_master_table_plots.py`：为上述 master_table 数据集实验出图（paper/study 两套），输出到 `src/out_plots/q3/{paper|study}/observed_master_table/`。
- `run_q3_smartphone_measurements_experiment.py`：Q3 数据集实验（SmartphoneMeasurements/Monsoon）：用外部实测功耗轨迹 P(t) 做“波动 vs 均值”的建模假设检验，输出到 `src/out_reports/q3/observed_smartphone_measurements/`（含 `trace_vs_mean.csv` 与重采样轨迹 `traces/*.csv`）。
- `make_q3_smartphone_measurements_plots.py`：为上述 SmartphoneMeasurements 实验出图（paper/study 两套），输出到 `src/out_plots/q3/{paper|study}/observed_smartphone_measurements/`。
- `validate_q2_open_data.py`：Q2 观测对照实验（AndroWatts/Zenodo）：把 `data/open_data/.../aggregated.csv` 的设备状态映射为模型输入段，验证“总功耗量级 + 主要 drivers 占比”是否与公开测量一致，输出：
  - 报表：`src/out_reports/q2/validation_open_data/per_case.csv`、`metrics.csv`
  - 图像：`src/out_plots/q2/{paper|study}/observed_open_data/`
- `validate_q2_user_behavior.py`：Q2 观测对照（长时间/TTE）：用 `data/SmartphoneMeasurements/user_behavior_dataset.csv` 做“日耗电→等效 TTE”的粗对齐，输出：
  - 报表：`src/out_reports/q2/validation_user_behavior/`
  - 图像：`src/out_plots/q2/{paper|study}/observed_user_behavior/`
- `validate_q2_smartphone_measurements.py`：Q2 观测对照（通信功耗/吞吐）：解析 `data/SmartphoneMeasurements/SmartphoneMeasurements.zip`（Monsoon+iPerf），输出：
  - 报表：`src/out_reports/q2/validation_smartphone_measurements/`
  - 图像：`src/out_plots/q2/{paper|study}/observed_smartphone_measurements/`
- `validate_q2_master_table.py`：Q2 数据集驱动验证（AndroWatts × 电池老化状态表）：从 AndroWatts 选取 3 个“功耗分位点”代表性负载（轻/中/重），再扫描 36 个电池状态（SOH+OCV），用观测功耗作为恒定输入驱动 Model-3，输出 “TTE vs SOH” 与 “提前关机剩余 SOC” 的证据链：
  - 报表：`src/out_reports/q2/validation_master_table/tte_by_state.csv`
  - 图像：`src/out_plots/q2/{paper|study}/observed_master_table/`
- `validate_model1_ecm_on_calce_sp20_1_incremental_ocv.py`：在 CALCE Incremental OCV 数据上验证 Model-1（ECM）电压预测误差，输出 JSON 报表与图像到 `src/out_reports/` 与 `src/out_plots/`（按数据集文件名自动分目录，避免覆盖）。
