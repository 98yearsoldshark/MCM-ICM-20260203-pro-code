# 来自目录 2 的整理索引（数学建模常用 python 代码包）

本文件用于把原始资料目录：

- `2、数学建模常用python代码包/`

映射到 `MCM_Toolkit_2026/` 内的可直接运行 Python 实现（统一 `solve(data, params)` + `__main__` Demo）。

## 目录结构说明

目录 2 主要包含两部分：

- A：`2、数学建模常用python代码包/Python资料 数学建模常用算法（Python 程序及数据）`
- B：`2、数学建模常用python代码包/数学建模30种常用算法(Python代码)`

其中：

- B 与目录 5 的“30 个常用算法”高度一致（代表性文件 hash 一致），可直接用：
  - `MCM_Toolkit_2026/notes/folder5_index.md`
- A 与目录 4 的“41-2 数学建模常用算法（Python 程序及数据）”基本同源（主要差别在于目录 4 存在大量 `(1)` 重复文件），可直接用：
  - `MCM_Toolkit_2026/notes/folder4_index.md`

因此目录 2 的整理以“建立替代映射”为主，通常无需重复转写实现。

## 目录 2 的覆盖情况（重点补齐项）

在整理目录 4 时，已补齐目录 2 中同样高频出现且 Toolkit 之前缺失的部分：

- 感知机（Perceptron）：`MCM_Toolkit_2026/c03_监督学习_Supervised/perceptron.py`
- 最大流：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/max_flow.py`
- 最小费用最大流：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/min_cost_max_flow.py`
- 统计检验/置信区间：`MCM_Toolkit_2026/c15_统计分析_Statistics/hypothesis_tests.py`
- ODE 初值问题：`MCM_Toolkit_2026/c17_微分方程_DifferentialEquations/ode_ivp.py`

## 可选依赖提示（资料中出现但 Toolkit 默认不强绑）

目录 2 中有不少示例依赖：

- `sympy`（符号解：`dsolve/rsolve`）
- `cvxpy/cvxopt`（凸优化示例）
- `cv2`（图像处理）

Toolkit 目前默认不强制安装这些依赖；若你的赛题确实需要，可再按具体需求补一个“可选模块 + requirements_optional”。

