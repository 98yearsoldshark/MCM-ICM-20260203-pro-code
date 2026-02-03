# 参量估计（Parameter Estimation）——论文可直接插入片段（中文）

本节用于把“参量估计所需数据盘点”落地为可复现的拟合结果与图表，并说明这些参数如何回填到连续时间机理模型中。

## 数据与原则

为满足赛题对“连续时间（continuous-time）机理模型”的要求，我们**仅将公开数据用于参量估计与模型验证**，而不使用数据直接拟合/回归续航曲线（避免黑盒替代机理）。

手机侧参量估计主要使用 AndroWatts（Zenodo，CC BY 4.0，DOI：10.5281/zenodo.14314943）的聚合数据表：

- `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`

其包含亮度、CPU/GPU 频率、Wi‑Fi 流量、温度统计量等状态特征，以及按 power rail 统计的能耗/功耗代理列，可用于构造可解释的“功耗分解观测量”。

## 1) 亮度–屏幕功耗（Brightness → P_screen）

我们用 power rail 的显示相关列构造观测屏幕功耗（W），并把 `Brightness(0~100)` 映射为 `brightness_nits`（默认上限 500 nits），在屏幕点亮样本上拟合线性模型：

\\[
P_{screen} \\approx P_{0,screen} + k_{screen}\\cdot \\text{brightness}_{nits}.
\\]

对应图表与拟合结果见：
- 图：`01-亮度-屏幕功耗/figure_paper.png`（论文版）、`01-亮度-屏幕功耗/figure_study.png`（学习版）
- 参数：`01-亮度-屏幕功耗/fit_results.csv`
- 来源与口径：`01-亮度-屏幕功耗/about.md`

## 2) 负载–CPU/GPU功耗（Load → P_cpu/P_gpu）

公开数据中无法直接观测“真实任务负载”，但可观测 CPU/GPU 频率。我们采用可复现的 proxy 将频率归一化得到 `load∈[0,1]`，并用 CPU/GPU 相关 rail 构造观测功耗，拟合 Model‑0 形式：

\\[
P_{cpu} \\approx k_{cpu}\\cdot u_{cpu},\\qquad
P_{gpu} \\approx k_{gpu}\\cdot u_{gpu}.
\\]

同时为了支撑更真实的 no7/Model‑1（超线性）讨论，我们额外给出幂律诊断拟合（`P=k u^\\gamma`）作为对照。

对应图表与拟合结果见：
- 图：`02-负载-CPU_GPU功耗/figure_paper.png`、`02-负载-CPU_GPU功耗/figure_study.png`
- 参数：`02-负载-CPU_GPU功耗/fit_results.csv`
- 来源与口径：`02-负载-CPU_GPU功耗/about.md`

## 3) 网络回落曲线（Network Tail / RRC）

赛题要求建模“网络状态与回落（tail）”对续航的影响。聚合数据不直接给出 `P(t)` 的回落段，因此我们采用更稳健且可解释的**能量守恒反推**：

\\[
E_{radio} \\approx P_{idle}\\,t + e_{mb}\\,\\text{bytes}_{MB} + E_{tail}.
\\]

其中 `E_tail` 表示尾态/连接维护等导致的“与传输量无关”的常量能量开销。进一步用连接态基准功耗估计等效时间常数：

\\[
\\tau_{tail} \\approx \\frac{E_{tail}}{P_{conn}-P_{idle}},
\\]

从而生成可用于论文展示与模型回填的回落曲线：

\\[
P_{tail}(t)=P_{idle}+(P_{conn}-P_{idle})\\exp(-t/\\tau_{tail}).
\\]

对应图表与拟合结果见：
- 图：`03-网络回落曲线/figure_paper.png`、`03-网络回落曲线/figure_study.png`
- 参数：`03-网络回落曲线/fit_results.csv`
- 来源与推导：`03-网络回落曲线/about.md`

## 4) 吞吐–功耗关系（Throughput → P_radio）

在 Wi‑Fi 样本上，我们构造平均吞吐 `throughput_MBps = bytes_MB/t`，并回归无线功耗：

\\[
P_{radio} \\approx P_{idle} + e_{mb}\\cdot \\text{throughput}_{MB/s}.
\\]

该结果主要用于“每 MB 能耗量级”的交叉验证，并与第 3 节的能量分解保持一致性检查。

对应图表与拟合结果见：
- 图：`04-吞吐-功耗关系/figure_paper.png`、`04-吞吐-功耗关系/figure_study.png`
- 参数：`04-吞吐-功耗关系/fit_results.csv`
- 来源与口径：`04-吞吐-功耗关系/about.md`

## 5) 温度-时间曲线（Thermal: ΔT(t)）

由于当前运行环境缺少 perfetto TraceProcessor 依赖，暂无法直接从 `.perfetto-trace` 导出完整温度时间序列 `T(t)`。为保证参量估计可落地，我们先使用 AndroWatts 中的温升统计量 `DIFF_SOC_TEMP`（首尾差）反推一阶集总热模型量级：

\\[
\\Delta T(t) \\approx (\\eta R_{th})\\,P\\,\\bigl(1-\\exp(-t/\\tau)\\bigr),\\qquad \\tau=R_{th}C_{th}.
\\]

并据此生成温度响应曲线（温度-时间曲线）用于论文展示与 Model‑2 热参数的初始标定。

对应图表与拟合结果见：
- 图：`05-温度-时间曲线/figure_paper.png`、`05-温度-时间曲线/figure_study.png`
- 参数：`05-温度-时间曲线/fit_results.csv`
- 来源与假设：`05-温度-时间曲线/about.md`

## 参量估计汇总表（建议放入论文）

我们将“可直接回填模型”的关键参数汇总为一张表（含数据来源路径）：

- `参数估计汇总表.md`
- `参数估计汇总表.csv`

## 复现方式（建议写入附录/补充材料）

在仓库根目录执行：

```bash
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/00_run_all.py"
```

将自动生成 5 类拟合的 `data.csv / fit_results.csv / figure_paper.png / figure_study.png / about.md` 以及汇总表。

