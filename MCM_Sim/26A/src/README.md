# MCM 2026 A - 代码库（src/）

本目录存放 2026 MCM A 题（智能手机电池耗电）建模与仿真代码。

约定（请保持一致）：
- 文档、注释、模块说明统一使用中文。
- 每个 Python 文件顶部写一句简短中文说明（模块 docstring 即可）。

设计目标：
- 机理核心（连续时间方程、模型组件、参数集）清晰、可复用、可测试。
- 将 **手机功耗需求建模（power demand）** 与 **电池电-热动力学（battery dynamics）** 解耦，便于逐步升级。
- 先用 Model-0 快速跑通端到端流程，再逐步升级至更强模型；后续拿到真实数据时，可无痛加入校准/验证。

建模路线（建议论文也按此叙述“逐步加复杂度”）：
- Model-0：连续时间功率/能量模型（先跑通：场景 -> 功耗 -> SOC -> TTE）。
- Model-1：等效电路 ECM（OCV-SOC + R0/RC），引入截止电压事件，TTE 更贴近真实关机逻辑。
  - 支持可选的 `R0_curve/R1_curve`（SOC 相关内阻曲线），用于解释低 SOC 区压降/松弛增强。
- Model-2：热模型（温度影响 OCV/R0/Q_eff），解释低温续航下降与高负载升温。
- Model-3：老化模型（容量衰减 + 内阻增长），解释“同样用法但越用越不耐电”。
  - 进一步可做“续航-发热-寿命”的三目标权衡（面向 Z 奖叙事）。

## 只看核心算法（推荐）

如果你想最快读懂“核心算法怎么做的”，建议直接按：
`mcm26a/CORE_ALGO.md` 的顺序阅读；可以先忽略 `mcm26a/viz/` 与 `out_plots/`。

## 目录结构

- `mcm26a/`（核心包）：
  - `battery/`：电池子模型（SOC/电压/等效电路），可选热/老化。
  - `power/`：组件级功耗模型（屏幕/CPU/网络/GPS/后台等）。
  - `scenarios/`：使用场景（分段时间表 + 随机过程生成器）。
  - `sim/`：仿真引擎（ODE 积分、事件终止、TTE 计算）。
  - `analysis/`：敏感性、消融实验、功耗贡献分解。
  - `uq/`：不确定性量化（先验区间、采样、传播）。
  - `calibration/`：参数校准（已支持 CALCE 单数据集的 OCV/ECM 校准闭环；后续可接入更多数据做系统校准/验证）。
  - `utils/`：通用小工具（单位、日志、随机数等）。
- `configs/`：参数与场景配置（JSON/YAML）。
- `scripts/`：命令行入口（批量跑场景、生成图表/表格等）。
- `out_reports/`：自动生成的数值结果（JSON/CSV），如校准/验证误差报表。

## 运行方式（无需安装为包）

参考其它 `MCM_Sim` 项目：通过 `PYTHONPATH` 直接运行脚本即可：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/<script>.py
```

## 数据下载（GitHub 版）

如果你把仓库整理到 GitHub 并在 `.gitignore` 中忽略了大体积数据（CALCE/NASA 等），克隆后可先运行：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile core
```

它会调用各数据目录自带的同步脚本，把 Q1/Q2/Q3 常用数据拉取到 `MCM_Sim/26A/data/` 的预期路径。

常用脚本（建议先从 Model-0 开始）：
- `scripts/run_model0_summary.py`：标准场景 TTE 概览
- `scripts/run_model0_policy_sweep.py`：策略/反事实扫描（ΔTTE）
- `scripts/run_model0_uq.py`：不确定性传播（TTE 分位数区间）
- `scripts/make_model0_plots.py`：一键生成 Model-0 图像（paper/study 两套），输出到 `src/out_plots/`
- `scripts/run_model1_summary.py`：Model-1（ECM）标准场景 TTE 概览（用于与 Model-0 对比）
- `scripts/run_model1_policy_sweep.py`：Model-1（ECM）策略/反事实扫描（ΔTTE）
- `scripts/make_model1_plots.py`：一键生成 Model-1 图像（paper/study 两套），输出到 `src/out_plots/`
- `scripts/calibrate_model1_ecm_r0fixed_r1soc_from_calce_sp20_1.py`：分阶段校准（推荐）：先用含阶跃/脉冲数据估计 R0，再固定 R0 用低电流数据拟合 R1(SOC)+C1（用于修复“优化变差”）
- `scripts/calibrate_model1_ecm2rc_r0fixed_from_calce_sp20_1.py`：2RC 扩展：在固定 R0 的前提下拟合 C1/C2 与 R1(SOC)/R2(SOC)，用于解释“快/慢两种松弛时间尺度”
- `scripts/validate_model1_ecm_on_calce_sp20_1_incremental_ocv.py`：用 CALCE Incremental OCV 数据验证 Model-1（电压预测误差报表与图像：`src/out_reports/validation/<dataset_id>/` + `src/out_plots/model1/{paper|study}/validation/<dataset_id>/`）
- `scripts/validate_model1_ecm2rc_on_calce_sp20_1_incremental_ocv.py`：同上，但验证的是 2RC 版本；额外输出 v1/v2 分解与电流轨迹图（便于学习/诊断）
- `scripts/run_q1_battery_param_est_and_validation_suite.py`：一键完成 Q1 电池端“参数估计 + 三组验证 + 汇总表”（输出：`src/out_reports/validation/_q1_battery_validation_summary.*`）
- `scripts/run_model2_summary.py`：Model-2（ECM + 热模型）标准场景 TTE + 温升概览（用于解释低温/高负载续航变化）
- `scripts/run_model2_policy_sweep.py`：Model-2（热-电耦合）策略扫描：同时输出续航提升与温升变化（用于做“续航-发热”权衡分析）
- `scripts/run_model3_summary.py`：Model-3（热-电耦合 + 老化）标准场景 TTE + 老化状态变化概览（用于解释“越用越不耐电”）

Q2/Q3（贴赛题“drivers / UQ / sensitivity / assumptions”）：
- `scripts/run_q2_report.py`：生成 Q2 数值报表（drivers、UQ、温度变体、能耗占比等），输出到 `src/out_reports/q2/`
- `scripts/make_q2_plots.py`：一键生成 Q2 图像（paper/study 两套），输出到 `src/out_plots/q2/`
- `scripts/run_q3_report.py`：生成 Q3 数值报表（PRCC/Spearman、局部 tornado、消融、老化扫描、波动统计），输出到 `src/out_reports/q3/`
- `scripts/make_q3_plots.py`：一键生成 Q3 图像（paper/study 两套），输出到 `src/out_plots/q3/`
- `scripts/make_q3_trace_examples.py`：生成 Q3 代表性轨迹图（paper/study 两套），输出到 `src/out_plots/q3/{paper|study}/traces/`
