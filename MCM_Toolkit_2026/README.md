# MCM_Toolkit_2026

面向美国大学生数学建模竞赛（MCM/ICM）的本地算法工具库：精简、标准化、可直接运行的 Demo。

## 快速开始

1) 创建/激活虚拟环境（建议在项目根目录创建 `.venv/`；如已存在可直接用）  
2) 安装依赖：

```bash
pip install -r MCM_Toolkit_2026/requirements.txt
```

可选依赖（按需安装，例如 XGBoost/LightGBM、SMOTE、jieba 分词等）：

```bash
pip install -r MCM_Toolkit_2026/requirements_optional.txt
```

3) 运行任意算法脚本（每个脚本都包含 `solve(data, params)` + `if __name__ == '__main__':` Mock Data Demo）：

```bash
python MCM_Toolkit_2026/c03_监督学习_Supervised/logistic_regression.py
```

## 算法索引（当前已整理）

| 算法/功能 | 所属类别 | 适用场景 | 输入数据要求（data/params） |
|---|---|---|---|
| 数据清洗（去重/缺失/异常值） | c01_数据处理_DataProcess | 清洗表格数据 | `data=DataFrame`；`params` 控制 drop_duplicates/fillna/outlier_zscore |
| 标准化/归一化 | c01_数据处理_DataProcess | 特征缩放（KNN/PCA 等常用） | `data=DataFrame/ndarray`；`params.method in {standard,minmax}` |
| 插值（1D/2D） | c01_数据处理_DataProcess | 缺失数据补全/平滑插值 | `interpolation.py`；支持 linear/spline/lagrange/griddata |
| 异常检测（Grubbs/马氏距离） | c01_数据处理_DataProcess | 单变量/多变量异常点识别 | `outlier_detection.py`；`data.kind in {grubbs,mahalanobis}` |
| 小波异常检测（CWT） | c01_数据处理_DataProcess | 时间序列突变/奇异点定位 | `wavelet_anomaly.py`；返回 peaks |
| Robust PCA（RPCA） | c01_数据处理_DataProcess | 低秩+稀疏分解/异常检测 | `robust_pca.py`；输出 L(低秩) 与 S(异常) |
| 压缩感知重建（OMP/LASSO） | c01_数据处理_DataProcess | 欠定观测下稀疏信号恢复 | `compressive_sensing.py`；`data={'A','y'}` |
| 分箱统计 | c01_数据处理_DataProcess | 分箱查看分布/坏样本率 | `data=DataFrame`；`params.feature/target/bins` |
| 表格预处理器（Imputer/Scaler/One-Hot） | c01_数据处理_DataProcess | 结构化数据建模前处理（可直接接 Pipeline） | `data=DataFrame`；`params.target_col` 可选；见 `preprocessor.py` |
| 类别编码（One-Hot/Label/Target） | c01_数据处理_DataProcess | 类别特征处理 | `data=DataFrame`；`params.mode in {onehot,label,target}` |
| 时间序列特征（收益率/滞后/滚动） | c01_数据处理_DataProcess | 金融/序列预测的特征模板 | `data=DataFrame(close)`；`params.horizon/target_type/lags/windows` |
| WOE/IV | c02_特征工程_FeatureEngineering | 二分类特征筛选（流失/违约） | `data=DataFrame`；`params.target/bins/binning` |
| 相关系数/VIF | c02_特征工程_FeatureEngineering | 共线性诊断 | `data=DataFrame`；可用 `params.target_col` 排除目标列 |
| 不平衡采样（ROS/SMOTE/RUS） | c02_特征工程_FeatureEngineering | 类别极不均衡 | 可选依赖 `imbalanced-learn`；见 `resampling.py` |
| 线性回归/多项式回归 | c03_监督学习_Supervised | 回归预测、拟合关系 | `data=(X,y)` 或 `DataFrame+target_col`；`params.degree` |
| 曲线拟合（polyfit/curve_fit） | c03_监督学习_Supervised | 经验公式拟合/增长规律 | `curve_fitting.py`；`params.model/degree/func` |
| 逻辑回归 | c03_监督学习_Supervised | 分类（含 ROC/AUC） | `data=(X,y)` 或 `DataFrame+target_col`；`params.model_params` |
| 朴素贝叶斯 | c03_监督学习_Supervised | 快速分类基线 | `params.model in {gaussian,multinomial,bernoulli}` |
| KNN（分类/回归） | c03_监督学习_Supervised | 小样本/非线性/相似度 | `params.task` + `params.standardize` |
| 决策树（分类/回归） | c03_监督学习_Supervised | 可解释模型/特征重要性 | `params.task` + `params.model_params` |
| 感知机（Perceptron） | c03_监督学习_Supervised | 线性分类基线/快速验证 | `perceptron.py`；`params.model_params` |
| SVM（SVC/SVR） | c03_监督学习_Supervised | 分类/回归（小样本强基线） | `svm.py`；`params.task/model_type/kernel/C/...` |
| 判别分析（LDA/QDA） | c03_监督学习_Supervised | Fisher 判别/多类分类 | `discriminant_analysis.py`；`params.model_type` |
| 文本分类（分词/向量化/分类） | c03_监督学习_Supervised | 评论/舆情/新闻等文本任务 | `text_classification.py`；tokenization 可选 `jieba` |
| 随机森林（分类/回归） | c04_集成模型_Ensemble | 强基线、鲁棒 | `params.task` + `params.model_params` |
| AdaBoost（分类/回归） | c04_集成模型_Ensemble | 集成提升 | `params.task` + `params.model_params` |
| GBDT（分类/回归） | c04_集成模型_Ensemble | 集成提升 | `params.task` + `params.model_params` |
| XGBoost（可选） | c04_集成模型_Ensemble | 结构化数据强模型 | 可选依赖 `xgboost`；见 `xgboost_model.py` |
| LightGBM（可选） | c04_集成模型_Ensemble | 结构化数据强模型 | 可选依赖 `lightgbm`；见 `lightgbm_model.py` |
| KMeans | c05_无监督_Unsupervised | 聚类分群 | `data=DataFrame/ndarray`；`params.n_clusters` |
| DBSCAN | c05_无监督_Unsupervised | 密度聚类/噪声点 | `params.eps/min_samples` |
| Apriori（频繁项集/关联规则） | c05_无监督_Unsupervised | 关联规则挖掘 | `data=transactions(list[list[str]])` 或 one-hot DataFrame |
| 文本聚类（TF-IDF+KMeans） | c05_无监督_Unsupervised | 新闻/评论/报告分群 | `text_clustering.py`；tokenization 可选 `jieba` |
| PCA | c06_降维_DimReduction | 降维/压缩/可视化前处理 | `params.n_components` + `params.standardize` |
| t-SNE | c06_降维_DimReduction | 非线性降维可视化 | `tsne.py`；`params.perplexity/n_iter` |
| 协同过滤（Item-based） | c07_推荐系统_Recommendation | 简易推荐系统 | `data=评分长表`；`params.target_item/min_count/top_n` |
| MLP（分类/回归） | c08_神经网络_NeuralNetwork | 非线性拟合/基线 NN | `params.task` + `params.model_params` |
| CNN（可选） | c08_神经网络_NeuralNetwork | 图像分类基线（demo） | `cnn_digits_optional.py`；需安装 `tensorflow` |
| GRNN（广义回归） | c08_神经网络_NeuralNetwork | 小样本非线性回归/核回归基线 | `grnn.py`；`params.sigma` 或 `sigma_candidates` |
| RBF 网络（回归） | c08_神经网络_NeuralNetwork | 非线性回归强基线 | `rbf_network.py`；`params.n_centers/sigma` |
| 小波神经网络（WNN） | c08_神经网络_NeuralNetwork | 非线性回归/序列预测（波形特征） | `wavelet_neural_network.py`；`params.n_hidden/epochs` |
| ROC/AUC/KS | c09_评估与调参_Evaluation | 二分类评估 | `data={'y_true','y_score'}` |
| 阈值选择（KS/Youden/F1） | c09_评估与调参_Evaluation | 从概率到标签的阈值决策 | `thresholding.py` |
| 二分类绘图（ROC/PR/KS/校准/混淆） | c09_评估与调参_Evaluation | 快速出图 | `classification_plots.py`（可选保存） |
| 交叉验证/网格搜索 | c09_评估与调参_Evaluation | 调参/验证 | `params.estimator` + `params.mode` |
| AHP（层次分析法） | c10_评价与决策_DecisionMaking | 主观赋权/一致性检验 | `data=A(两两比较矩阵)`；`params.method/cr_threshold` |
| 熵权法 | c10_评价与决策_DecisionMaking | 客观赋权 | `data=决策矩阵X`；`params.is_benefit` |
| CRITIC 权重 | c10_评价与决策_DecisionMaking | 客观赋权（对比强度+冲突性） | `critic_weight.py`；`params.normalize_method/is_benefit` |
| TOPSIS | c10_评价与决策_DecisionMaking | 多指标排序（贴近理想解） | `data=决策矩阵X`；`params.weights_method/weights/is_benefit` |
| VIKOR | c10_评价与决策_DecisionMaking | 多指标折衷排序 | `vikor.py`；`params.weights_method/v/is_benefit` |
| 模糊综合评价 | c10_评价与决策_DecisionMaking | 多指标分级评价 | `data={'weights','membership'}`；可选 `grade_scores` |
| 层次模糊综合评价（两级） | c10_评价与决策_DecisionMaking | 子系统-指标分级评价 | `fuzzy_comprehensive_hierarchical.py`；`data={'criterion_weights',...}` |
| 灰色关联分析（GRA） | c10_评价与决策_DecisionMaking | 相关性/相似度评价、方案对比 | `data=X(m×n)`；`params.rho/normalize_method` |
| DS 证据理论（简化） | c10_评价与决策_DecisionMaking | 多源信息融合 | `ds_evidence_theory.py`；`data={'probs'}` 或 `{'masses'}` |
| DEA（CCR/BCC 输入导向） | c10_评价与决策_DecisionMaking | 效率评价（多输入多输出） | `data={'X','Y'}`；`params.returns_to_scale` |
| 物元分析法（Matter-Element） | c10_评价与决策_DecisionMaking | 多指标分级评价/等级判定 | `matter_element.py`；`data={'X','classical_domains','weights'}` |
| 灰色预测 GM(1,1) | c11_预测预报_Forecasting | 小样本单变量短期预测 | `data=x0`；`params.horizon/alpha` |
| 马尔科夫链预测 | c11_预测预报_Forecasting | 离散状态转移、多步分布预测 | `data=states`；`params.n_steps/smoothing` |
| 隐马尔科夫（HMM） | c11_预测预报_Forecasting | 序列状态推断/分段 | `hmm.py`；支持离散/高斯发射（不依赖 hmmlearn） |
| 灰色马尔科夫（简化） | c11_预测预报_Forecasting | GM(1,1) + 状态修正 | `data=x0`；`params.horizon/n_states/bins` |
| AR(p) 自回归 | c11_预测预报_Forecasting | 线性自回归预测 | `autoregression.py`；`params.lags/horizon` |
| ARIMA 预测 | c11_预测预报_Forecasting | 差分平稳序列预测 | `data=y`；`params.order/horizon` |
| 指数平滑（Holt-Winters） | c11_预测预报_Forecasting | 趋势/季节序列短期预测 | `params.trend/seasonal/seasonal_periods` |
| 移动平均/滑动平均 | c11_预测预报_Forecasting | 简单平滑/基线预测 | `moving_average.py`；`params.windows/modes` |
| 线性规划（linprog） | c12_优化算法_Optimization | 连续规划/资源分配 | `data={'c','A_ub','b_ub',...}`；`params.maximize` |
| MILP/ILP（整数规划） | c12_优化算法_Optimization | 0-1 规划/整数决策 | `milp.py`（HiGHS） |
| 匈牙利算法（指派问题） | c12_优化算法_Optimization | 指派/匹配 | `assignment_hungarian.py` |
| 二次规划（QP） | c12_优化算法_Optimization | 凸二次规划/组合约束 | `quadratic_programming.py`（SciPy；可选 cvxopt） |
| 非线性规划（NLP） | c12_优化算法_Optimization | 非线性目标 + 约束 | `nonlinear_programming.py`（SLSQP/trust-constr） |
| 遗传算法（GA） | c12_优化算法_Optimization | 连续变量全局优化 | `data={'objective','bounds'}`；GA 参数见文件 |
| 粒子群（PSO） | c12_优化算法_Optimization | 连续变量全局优化 | `data={'objective','bounds'}`；PSO 参数见文件 |
| 模拟退火（SA） | c12_优化算法_Optimization | 连续变量全局优化/跳出局部最优 | `data={'objective','bounds'}`；SA 参数见文件 |
| 蚁群算法（TSP） | c12_优化算法_Optimization | 旅行商/路径规划 | `data={'coords'}` 或 `{'distance_matrix'}` |
| TSP 启发式（最近邻/2-opt/退火） | c12_优化算法_Optimization | 快速得到可用解/作为后处理 | `tsp_heuristics.py`；`params.method` |
| NSGA-II | c12_优化算法_Optimization | 多目标优化（Pareto 前沿） | `data={'objective','bounds'}`；NSGA2 参数见文件 |
| 免疫遗传算法（IGA） | c12_优化算法_Optimization | 组合优化（选址/选点）+ 多样性抑制 | `immune_algorithm.py`；支持 `n_ones` |
| 人工鱼群（TSP） | c12_优化算法_Optimization | TSP 离散群智能基线 | `artificial_fish_swarm_tsp.py` |
| 量子遗传（QGA） | c12_优化算法_Optimization | 二进制编码连续优化（最大化/最小化） | `quantum_genetic_algorithm.py` |
| MOPSO | c12_优化算法_Optimization | 多目标优化（外部档案库+拥挤度网格） | `mopso.py` |
| 0-1 背包（DP） | c16_动态规划_DynamicProgramming | 经典动态规划/资源约束 | `knapsack_01.py`（支持回溯；大规模退化为 1D） |
| Dijkstra 最短路 | c13_图论算法_GraphTheory | 单源最短路（非负权） | `data={'n','edges'}` 或 `{'n','adj_matrix'}` |
| A*（栅格路径规划） | c13_图论算法_GraphTheory | 2D 网格最短路/路径规划 | `astar_grid.py`；`data={'grid','start','goal'}` |
| Floyd-Warshall | c13_图论算法_GraphTheory | 全源最短路 | `data=adj_matrix`；可选 `params.path` |
| Kruskal MST | c13_图论算法_GraphTheory | 最小生成树/最小生成森林 | `data={'n','edges'}` |
| Prim MST | c13_图论算法_GraphTheory | 最小生成树（稠密图） | `data=adj_matrix` |
| 最大流（Max Flow） | c13_图论算法_GraphTheory | 网络流/产能分配 | `max_flow.py`；`data={'capacity','source','sink'}` |
| 最小费用最大流 | c13_图论算法_GraphTheory | 网络流 + 成本最小 | `min_cost_max_flow.py`；`data={'edges','source','sink'}` |
| Monte Carlo 模拟 | c14_仿真模拟_Simulation | 概率/期望/积分估计 | `data={'sampler','func'}`；`params.n_samples` |
| 排队论仿真（M/M/c/K & 修理工模型） | c14_仿真模拟_Simulation | 等待时间/拥堵/阻塞率评估 | `queueing_models.py`；`data.model in {'mmck','repairman'}` |
| 元胞自动机交通流（NaSch） | c14_仿真模拟_Simulation | 交通流基本图（密度-流量） | `traffic_flow_nasch.py`；可扫密度 |
| 统计检验/置信区间 | c15_统计分析_Statistics | t/卡方/K-S/ANOVA 等 | `hypothesis_tests.py`；`params.test` |
| CCA（典型相关分析） | c15_统计分析_Statistics | 两组变量相关结构分析 | `data={'X','Y'}`；`params.n_components` |
| ODE 初值问题（solve_ivp） | c17_微分方程_DifferentialEquations | 微分方程数值解 | `ode_ivp.py`；`data={'fun','t_span','y0'}` |

## 速查笔记

- `MCM_Toolkit_2026/notes/ml_quick_reference.md`
- `MCM_Toolkit_2026/notes/folder6_index.md`（目录 6 的题型算法映射索引）
- `MCM_Toolkit_2026/notes/folder5_index.md`（目录 5 的 30 个算法映射索引）
- `MCM_Toolkit_2026/notes/folder4_index.md`（目录 4 的算法集合映射索引）
- `MCM_Toolkit_2026/notes/folder2_index.md`（目录 2 的常用代码包映射索引）

## 端到端示例（来自资料案例的模板化版本）

- `MCM_Toolkit_2026/c00_示例_Examples/churn_logistic_regression.py`：二分类（预处理+LR+阈值/KS）
- `MCM_Toolkit_2026/c00_示例_Examples/employee_turnover_decision_tree.py`：二分类（预处理+决策树+网格搜索）
- `MCM_Toolkit_2026/c00_示例_Examples/movie_recommendation_item_cf.py`：电影推荐（Item-based 协同过滤）
- `MCM_Toolkit_2026/c00_示例_Examples/folder6_grey_relational_xlsx_demo.py`：读取 xlsx + 灰色关联分析
- `MCM_Toolkit_2026/c00_示例_Examples/folder6_logistic_xlsx_demo.py`：读取 xlsx + 逻辑回归二分类
- `MCM_Toolkit_2026/c00_示例_Examples/folder5_curve_fitting_xlsx_demo.py`：读取 xlsx + 曲线拟合（polyfit/curve_fit）
