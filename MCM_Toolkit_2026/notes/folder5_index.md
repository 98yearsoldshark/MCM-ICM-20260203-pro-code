# 来自目录 5 的整理索引（30 个常用算法）

本文件用于把原始资料目录：

- `5、30个常用算法Python代码/`

中“30 个常用算法”映射到 `MCM_Toolkit_2026/` 内的可直接运行 Python 实现（统一 `solve(data, params)` + `__main__` Demo）。

> 说明：目录 5 与目录 6、7 有大量重叠；为避免重复实现，这里只做“可替代性映射”和少量补齐（拟合/QP/NLP/层次模糊/HMM 等）。

## 逐条映射（资料条目 -> Toolkit）

1) `ARIMA时间序列预测模型Python代码.txt`  
-> `MCM_Toolkit_2026/c11_预测预报_Forecasting/arima.py`

2) `BP神经网络模型Python代码.txt`  
-> `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/mlp.py`（sklearn 的 MLP，等价 BP 思路）

3) `K-means聚类模型Python代码.docx`  
-> `MCM_Toolkit_2026/c05_无监督_Unsupervised/kmeans.py`

4) `TOPSIS综合评价模型Python代码.docx`  
-> `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/topsis.py`

5) `一维、二维插值模型Python代码.txt`  
-> `MCM_Toolkit_2026/c01_数据处理_DataProcess/interpolation.py`

6) `主成分分析算法Python代码.txt`  
-> `MCM_Toolkit_2026/c06_降维_DimReduction/pca.py`

7) `二次规划模型Python代码.docx`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/quadratic_programming.py`（默认 SciPy；可选 cvxopt）

8) `决策树分类模型Python代码.txt`  
-> `MCM_Toolkit_2026/c03_监督学习_Supervised/decision_tree.py`

9) `判别分析Fisher模型Python代码.rar`  
-> `MCM_Toolkit_2026/c03_监督学习_Supervised/discriminant_analysis.py`（LDA/QDA）

10) `卷积神经网络模型Python代码.txt`  
-> `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/cnn_digits_optional.py`（可选，需要 tensorflow；用 sklearn digits 无需联网）

11) `多目标模糊综合评价模型Python代码.docx`  
-> `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/fuzzy_comprehensive_hierarchical.py`（两级/层次模糊）  
-> `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/fuzzy_comprehensive.py`（单层模糊）

12) `层次分析法Python代码.txt`  
-> `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/ahp.py`

13) `支持向量机模型Python代码.txt`  
-> `MCM_Toolkit_2026/c03_监督学习_Supervised/svm.py`

14) `数学建模拟合模型Python代码.txt`  
-> `MCM_Toolkit_2026/c03_监督学习_Supervised/curve_fitting.py`（polyfit + curve_fit）

15) `整数规划模型Python代码.docx`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/milp.py`（ILP/MILP）  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/assignment_hungarian.py`（匈牙利指派：资料中混在该 docx 内）

16) `智能优化之模拟退火模型Python代码.txt`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/simulated_annealing.py`

17) `智能优化之粒子群模型Python代码.txt`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/particle_swarm.py`

18) `智能优化之遗传算法Python代码.txt`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/genetic_algorithm.py`

19) `最短路径算法Python代码.docx`  
-> `MCM_Toolkit_2026/c13_图论算法_GraphTheory/dijkstra.py`（也可看 floyd/astar）

20) `模糊综合评价模型Python代码.txt`  
-> `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/fuzzy_comprehensive.py`

21) `灰色预测模型Python代码.txt`  
-> `MCM_Toolkit_2026/c11_预测预报_Forecasting/grey_gm11.py`

22) `线性规划模型Python代码.txt`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/linear_programming.py`

23) `蒙特卡洛模型Python代码.docx`  
-> `MCM_Toolkit_2026/c14_仿真模拟_Simulation/monte_carlo.py`

24) `逻辑回归模型Python代码.txt`  
-> `MCM_Toolkit_2026/c03_监督学习_Supervised/logistic_regression.py`

25) `随机森林分类模型Python代码.txt`  
-> `MCM_Toolkit_2026/c04_集成模型_Ensemble/random_forest.py`

26) `非线性规划模型Python代码.docx`  
-> `MCM_Toolkit_2026/c12_优化算法_Optimization/nonlinear_programming.py`（SLSQP/trust-constr）

27) `0-1背包问题动态规划模型Python代码/`  
-> `MCM_Toolkit_2026/c16_动态规划_DynamicProgramming/knapsack_01.py`

28) `动态规划模型Python代码/`  
-> `MCM_Toolkit_2026/c16_动态规划_DynamicProgramming/`（动态规划专题；其中含 0-1 背包可直接用）

29) `神经网络分类模型Python代码/`  
-> `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/mlp.py`

30) `马尔科夫预测模型Python代码/`（资料中实际给的是 HMM 示例）  
-> `MCM_Toolkit_2026/c11_预测预报_Forecasting/markov_chain.py`（马尔科夫链）  
-> `MCM_Toolkit_2026/c11_预测预报_Forecasting/hmm.py`（隐马尔科夫；不依赖 hmmlearn）

