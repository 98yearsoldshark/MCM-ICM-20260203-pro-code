# 来自目录 6 的整理索引（按赛题类别）

本文件用于把原始资料目录：

- `6、按赛题类别划分的常用算法代码/`

中“常见题型算法”映射到 `MCM_Toolkit_2026/` 内的可直接运行 Python 实现（统一 `solve(data, params)` + `__main__` Demo）。

> 说明：为保持最终算法库体积最小，默认不把大量 Matlab 源码/图片/压缩包复制进 `MCM_Toolkit_2026`，仅将高频算法重写为 Python 并索引到这里。

## 评价与决策类

对应 Toolkit：

- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/ahp.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/entropy_weight.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/critic_weight.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/topsis.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/vikor.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/fuzzy_comprehensive.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/grey_relational.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/ds_evidence_theory.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/dea.py`
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/matter_element.py`（物元分析法）

## 预测与预报类

- `MCM_Toolkit_2026/c11_预测预报_Forecasting/grey_gm11.py`
- `MCM_Toolkit_2026/c11_预测预报_Forecasting/grey_markov.py`
- `MCM_Toolkit_2026/c11_预测预报_Forecasting/markov_chain.py`
- `MCM_Toolkit_2026/c11_预测预报_Forecasting/autoregression.py`
- `MCM_Toolkit_2026/c11_预测预报_Forecasting/arima.py`
- `MCM_Toolkit_2026/c11_预测预报_Forecasting/exponential_smoothing.py`

## 神经网络/非线性预测（进阶）

目录 6 中的 Matlab 资料包含 GRNN/RBF/小波神经网络等预测案例；已补齐为可直接运行的 Python 版本：

- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/grnn.py`（GRNN / 核回归；支持 CV 选 sigma）
- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/rbf_network.py`（RBF 网络回归；KMeans 选中心 + 岭回归闭式解）
- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/wavelet_neural_network.py`（Morlet 小波网络；在线 SGD）

## 优化与控制类

- `MCM_Toolkit_2026/c12_优化算法_Optimization/linear_programming.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/genetic_algorithm.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/particle_swarm.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/simulated_annealing.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/ant_colony_tsp.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/tsp_heuristics.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/nsga2.py`
- `MCM_Toolkit_2026/c12_优化算法_Optimization/immune_algorithm.py`（免疫遗传算法：浓度抑制 + 记忆库；支持“选 k 个点”）
- `MCM_Toolkit_2026/c12_优化算法_Optimization/artificial_fish_swarm_tsp.py`（人工鱼群求解 TSP，离散版本）
- `MCM_Toolkit_2026/c12_优化算法_Optimization/quantum_genetic_algorithm.py`（量子遗传算法 QGA：二进制编码映射连续变量）
- `MCM_Toolkit_2026/c12_优化算法_Optimization/mopso.py`（多目标粒子群 MOPSO：外部档案库 + 网格拥挤度）

## 数据处理类

- `MCM_Toolkit_2026/c01_数据处理_DataProcess/interpolation.py`
- `MCM_Toolkit_2026/c01_数据处理_DataProcess/outlier_detection.py`
- `MCM_Toolkit_2026/c01_数据处理_DataProcess/wavelet_anomaly.py`
- `MCM_Toolkit_2026/c01_数据处理_DataProcess/robust_pca.py`
- `MCM_Toolkit_2026/c01_数据处理_DataProcess/compressive_sensing.py`
- `MCM_Toolkit_2026/c06_降维_DimReduction/pca.py`
- `MCM_Toolkit_2026/c06_降维_DimReduction/tsne.py`

## 相关性分析类

- `MCM_Toolkit_2026/c15_统计分析_Statistics/canonical_correlation.py`
- `MCM_Toolkit_2026/c05_无监督_Unsupervised/apriori.py`（关联规则）
- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/grey_relational.py`（灰色关联）

## 分类与判别类

- `MCM_Toolkit_2026/c03_监督学习_Supervised/svm.py`
- `MCM_Toolkit_2026/c03_监督学习_Supervised/discriminant_analysis.py`
- 其他常见监督学习模型可见：`MCM_Toolkit_2026/c03_监督学习_Supervised/`

## 仍可按需补齐（低频/赛题强相关）

- 其他综合评价：更多评价法（PROMETHEE/ELECTRE 等）
- 神经网络时序进阶：混沌相空间重构 + 多步滚动预测等（Toolkit 已给出通用模型，可按题目再封装）
