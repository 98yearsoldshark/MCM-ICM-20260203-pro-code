# 来自目录 4 的整理索引（Python 各类算法代码集合）

本文件用于把原始资料目录：

- `4、Python各类算法代码集合/`

映射到 `MCM_Toolkit_2026/` 内的可直接运行 Python 实现（统一 `solve(data, params)` + `__main__` Demo）。

> 说明：目录 4 中包含大量“教材式示例脚本”（约 700 个 `.py`），且存在大量带 `(1)` 的重复文件；Toolkit 不复制原始脚本，只提炼高频算法并做索引。

## 41-1 神经网络分类模型

- 资料：`4、Python各类算法代码集合/41-1 .../神经网络分类.py`（感知机示例；原代码会联网下载 iris）
- Toolkit：
  - `MCM_Toolkit_2026/c03_监督学习_Supervised/perceptron.py`（sklearn 封装；离线 iris demo）
  - `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/mlp.py`（BP/MLP 通用基线）
  - `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/cnn_digits_optional.py`（CNN demo，可选依赖 tensorflow）

## 41-2 数学建模常用算法（Python 程序及数据）

### 顶层“30 个常用算法”文件

该部分与目录 5 基本重复，直接参考：

- `MCM_Toolkit_2026/notes/folder5_index.md`

### 第 4 章：概率论与数理统计

- `MCM_Toolkit_2026/c15_统计分析_Statistics/hypothesis_tests.py`：置信区间、t 检验、卡方检验、正态性/K-S、单因素 ANOVA 等

### 第 5/6 章：线性规划 / 整数规划与非线性规划

- `MCM_Toolkit_2026/c12_优化算法_Optimization/linear_programming.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/milp.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/nonlinear_programming.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/quadratic_programming.py`

### 第 7 章：插值与拟合

- `MCM_Toolkit_2026/c01_数据处理_DataProcess/interpolation.py`
- `MCM_Toolkit_2026/c03_监督学习_Supervised/curve_fitting.py`

### 第 8 章：微分方程模型

- `MCM_Toolkit_2026/c17_微分方程_DifferentialEquations/ode_ivp.py`：ODE 初值问题（`solve_ivp`）

（资料中也大量使用 `sympy.dsolve`/`sympy.rsolve` 做符号解；Toolkit 目前默认不引入 `sympy` 依赖，如需可再补一个可选模块。）

### 第 9 章：综合评价方法

- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/`（AHP/熵权/TOPSIS/VIKOR/模糊综合/灰色关联/DEA/DS 等）

### 第 10 章：图论模型

- 最短路/生成树：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/`
- 最大流：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/max_flow.py`
- 最小费用最大流：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/min_cost_max_flow.py`（用 LP 求解，无需 networkx）

### 第 15/16/17/18/19 章：灰色系统 / Monte Carlo / 智能算法 / 时间序列 / SVM

- 灰色预测：`MCM_Toolkit_2026/c11_预测预报_Forecasting/grey_gm11.py`、`grey_markov.py`
- Monte Carlo：`MCM_Toolkit_2026/c14_仿真模拟_Simulation/monte_carlo.py`
- 智能优化：`MCM_Toolkit_2026/c12_优化算法_Optimization/`（GA/PSO/SA/ACO/NSGA-II 等）
- 时间序列：`MCM_Toolkit_2026/c11_预测预报_Forecasting/`（AR/ARIMA/指数平滑/马尔科夫/HMM 等）
- SVM：`MCM_Toolkit_2026/c03_监督学习_Supervised/svm.py`

### 第 20 章：数字图像处理

资料中涉及 `PIL/cv2` 等；Toolkit 暂未精选转写（如赛题确实需要图像处理，可按具体任务再补对应模块）。

