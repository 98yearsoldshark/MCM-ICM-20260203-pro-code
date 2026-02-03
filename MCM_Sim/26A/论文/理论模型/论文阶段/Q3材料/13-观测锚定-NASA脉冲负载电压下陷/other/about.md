# 13-观测锚定-NASA脉冲负载电压下陷

## 这张图回答赛题 Q3 的哪一部分？

主要用于支撑 Q3 的两点：
- **使用模式波动（fluctuations）**：脉冲/突发负载会产生比均值更“伤续航/更伤裕量”的非线性影响；
- **风险指标的可解释性**：为 `min_headroom_margin`（最小电压裕量）提供直接的物理观测证据，避免被误读为“自定义评分”。

## 图源与生成位置

- 图文件源（paper/study）：
  - `MCM_Sim/26A/src/out_plots/q3/paper/observed_nasa_battery/01_pulse_voltage_sag.png`
  - `MCM_Sim/26A/src/out_plots/q3/study/observed_nasa_battery/01_pulse_voltage_sag.png`
- 本目录内：
  - `figure.png`：论文版（干净）
  - `other/figure_study.png`：学习版（带解释标注）

## 观测数据来源（开源）

- 数据集：NASA PCoE “Randomized Battery Usage Data Set”（随机/脉冲负载实验）
- 本项目本地路径：
  - `MCM_Sim/26A/data/NASA-BatteryData/11.+Randomized+Battery+Usage+Data+Set/.../data/Matlab/RW4.mat`
- 本图截取窗口：RW4 的若干 step（交替的 pulsed load discharge / rest），并将每段 `relativeTime` 平移拼接为连续时间轴。

## 生成脚本与数据版本

- 脚本：`MCM_Sim/26A/src/scripts/make_q3_nasa_pulse_anchor.py`
- 报表（逐时刻观测数据）：
  - `MCM_Sim/26A/src/out_reports/q3/observed_nasa_battery/pulse_demo_rw4_steps9730_9739.csv`
  - 本目录同步：`other/data.csv`

## 写作口径（避免踩雷）

- 本图只用于 **观测锚定（support）**：说明脉冲负载确实会造成电压下陷/回弹，并可能逼近 cut-off。
- 本项目的核心预测仍来自连续时间机理模型；我们不使用该图做黑盒拟合或替代 ODE 模型（符合赛题要求）。

