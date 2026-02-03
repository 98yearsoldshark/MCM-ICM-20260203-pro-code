# 来自目录 10 的整理索引（41+30 常用算法：Matlab + Python）

本文件用于把原始资料目录：

- `0ys-files/temp/10-数学建模41+30种算法常用代码（可运行免调试Matlab+python）【公众号：数模加油站】/`

映射到 `MCM_Toolkit_2026/` 中的可运行 Python 实现（统一 `solve(data, params)` + `__main__` Demo）。

## 1) 总体结论

- 该目录的“30 个 Python 常用算法”与目录 5/2 的 30 算法高度重复，Toolkit 已覆盖；不再重复搬运。
- “41 种 Matlab 常用算法”中，大部分算法 Toolkit 也已覆盖（最短路、聚类、SVM、评价模型、灰色预测、智能优化等）。
- 其中确实存在 Toolkit 之前未收录、但对建模实战有价值的内容，已补齐为 Python：
  - 排队论仿真：`MCM_Toolkit_2026/c14_仿真模拟_Simulation/queueing_models.py`
  - 元胞自动机交通流（NaSch）：`MCM_Toolkit_2026/c14_仿真模拟_Simulation/traffic_flow_nasch.py`
  - 简单移动平均平滑：`MCM_Toolkit_2026/c11_预测预报_Forecasting/moving_average.py`

## 2) 目录 10 / Matlab 41 的核心映射（节选）

> 说明：这里只列“最常用/最代表性”的映射；其余同类算法可直接在 Toolkit 对应分类目录中查找。

- 最短路径（Dijkstra）：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/dijkstra.py`
- 最短路（Floyd-Warshall）：`MCM_Toolkit_2026/c13_图论算法_GraphTheory/floyd_warshall.py`
- KMeans：`MCM_Toolkit_2026/c05_无监督_Unsupervised/kmeans.py`
- SVM：`MCM_Toolkit_2026/c03_监督学习_Supervised/svm.py`
- TOPSIS：`MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/topsis.py`
- AHP：`MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/ahp.py`
- PCA：`MCM_Toolkit_2026/c06_降维_DimReduction/pca.py`
- 灰色关联：`MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/grey_relational.py`
- 灰色预测 GM(1,1)：`MCM_Toolkit_2026/c11_预测预报_Forecasting/grey_gm11.py`
- ARIMA：`MCM_Toolkit_2026/c11_预测预报_Forecasting/arima.py`
- 指数平滑（含 Holt-Winters）：`MCM_Toolkit_2026/c11_预测预报_Forecasting/exponential_smoothing.py`
- 遗传算法/粒子群/模拟退火：`MCM_Toolkit_2026/c12_优化算法_Optimization/genetic_algorithm.py`、`particle_swarm.py`、`simulated_annealing.py`
- HMM（隐马尔可夫）：`MCM_Toolkit_2026/c11_预测预报_Forecasting/hmm.py`
- GRNN/RBF/小波神经网络（目录 10 中以压缩包/脚本形式出现）：见
  - `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/grnn.py`
  - `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/rbf_network.py`
  - `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/wavelet_neural_network.py`

## 2.1 未纳入（按策略忽略）

以下内容在目录 10 中出现，但为保持 Toolkit “体积最小 + 通用可复用”，按策略未纳入：

- `数字图像处理matlab代码.rar`：脚本量大且偏 Matlab 工具箱调用，迁移为 Python 需要引入 `opencv/skimage` 等重依赖
- `小波特征提取算法代码.txt`：为特定二值图像形状的“小波矩特征”实现（强绑定输入格式与显示流程），属于长尾任务；若你后续题目确实需要可再补

## 3) 目录 10 / Python 30 的处理说明

该目录下的 zip：

- `.../数学建模常用的30个常用算法(Python代码)（公众号：数模加油站）.zip`

包含大量与目录 5 相同的算法材料（含 docx/txt/py），并夹带二进制产物（如 exe）。

处理策略：

- **不把原 zip 解包复制进 Toolkit**（避免体积膨胀与乱码文件名问题）。
- 直接使用 Toolkit 已整理的“30 算法映射索引”：`MCM_Toolkit_2026/notes/folder5_index.md`

## 4) 已检查的压缩包/文档清单（用于“没有遗漏”的确认）

> 说明：这里只记录“文件清单 + 处理决策”，避免把重复/低质材料搬进 Toolkit。

### 4.1 压缩包（zip/rar）

- `Matlab 41种常用算法代码（免调试）/时间序列模型ARIMA的讲解与matlab代码实现（含多个实例）.rar`
  - 内容：`ARIMA.m` 等 Matlab 脚本 + 1 份 PDF 教程
  - 决策：代码能力由 `MCM_Toolkit_2026/c11_预测预报_Forecasting/arima.py` 等覆盖；PDF 属于长篇理论材料，按策略不纳入
- `Matlab 41种常用算法代码（免调试）/GRNN的数据预测-基于广义回归神经网络货运量预测.rar`
  - 内容：Matlab 脚本（`chapter8.*.m`）+ `.mat` 数据 + `.ppt` 案例课件
  - 决策：算法由 `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/grnn.py` 覆盖；数据/课件按“最小体积”原则不纳入
- `Matlab 41种常用算法代码（免调试）/RBF神经网络做回归预测代码.zip`
  - 内容：单个 Matlab 脚本（`jingxiangjiyuce.m`）
  - 决策：算法由 `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/rbf_network.py` 覆盖
- `Matlab 41种常用算法代码（免调试）/隐马尔可夫预测代码（含有大量案例）.zip`
  - 内容：主要是 wavelet hidden Markov tree（HMT）图像去噪相关代码与素材（非“通用序列 HMM 预测”）
  - 决策：属于“图像/小波去噪”长尾方向，且需引入额外依赖与更长说明，按策略不纳入；Toolkit 内仍提供通用序列 HMM：`MCM_Toolkit_2026/c11_预测预报_Forecasting/hmm.py`
- `Matlab 41种常用算法代码（免调试）/数字图像处理matlab代码.rar`
  - 决策：见 2.1（图像处理重依赖/偏工具箱调用，不纳入）
- `数学建模常用的30个常用算法(Python代码)/数学建模常用的30个常用算法(Python代码)（公众号：数模加油站）.zip`
  - 决策：不搬运；映射到 `MCM_Toolkit_2026/notes/folder5_index.md`
- `.../判别分析Fisher模型Python代码.rar`
  - 决策：算法由 `MCM_Toolkit_2026/c03_监督学习_Supervised/discriminant_analysis.py` 覆盖；原始训练/测试数据不纳入

### 4.2 文档（doc/docx）

目录中出现的 `*.doc/*.docx`（如“最短路径/蒙特卡洛/整数规划/二次规划/TOPSIS/KMeans/非线性规划”等）已做快速阅读核对：

- 多数为“算法简介 + 小段示例代码/截图”，与 Toolkit 现有实现重复
- 决策：不搬运文档本体；直接映射到 Toolkit 对应脚本（见本文件第 2 节及 `folder5_index.md`）
