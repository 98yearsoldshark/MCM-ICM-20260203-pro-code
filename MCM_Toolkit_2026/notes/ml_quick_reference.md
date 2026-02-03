# 机器学习速查（MCM/ICM）

## 1) 常见数据坑

- 数据泄漏：先划分训练/测试，再在训练集上拟合标准化/编码/分箱/特征选择，再应用到测试集
- 类别变量：别直接喂给线性/距离模型；优先 One-Hot 或目标编码（注意泄漏）
- 特征尺度：KNN / KMeans / PCA / MLP 对尺度敏感，建议标准化
- 不平衡：仅看 accuracy 会误导；优先 AUC/PR/Recall/F1/KS，并考虑采样或 class_weight

## 2) 二分类评估（快速选）

- AUC：对阈值不敏感，适合总体排序能力
- KS：金融风控常用，等价于 max(TPR-FPR)
- PR/AP：正类很少时比 ROC 更敏感
- 阈值选择：可用 KS 最大、F1 最大、或按业务约束（如召回率>=x）

## 3) 监督学习（何时用 + 关键超参）

### 线性回归 / 逻辑回归
- 场景：可解释、基线模型、特征工程后效果稳定
- 关键：正则化强度 C（LR）；多重共线性可用 VIF/特征筛选

### 朴素贝叶斯
- 场景：文本/高维稀疏特征的强基线（MultinomialNB 常用）

### 决策树 / 随机森林
- 场景：非线性、可解释（树）、鲁棒基线（RF）
- 关键：max_depth、min_samples_split、n_estimators（RF）

### AdaBoost / GBDT
- 场景：结构化数据强基线；比单棵树更强
- 关键：n_estimators、learning_rate、max_depth（弱学习器复杂度）

### XGBoost / LightGBM（可选依赖）
- 场景：结构化数据竞赛常胜模型
- 关键：n_estimators + learning_rate（一起调）、max_depth/num_leaves、subsample、colsample_bytree、reg_lambda
- 建议：用 early stopping 防过拟合（需要验证集）

## 4) 无监督（聚类/降维/关联规则）

### KMeans
- 关键：n_clusters；用肘部法/轮廓系数挑 k；记得标准化

### DBSCAN
- 关键：eps、min_samples；能识别噪声点；对尺度敏感（建议标准化）

### PCA
- 关键：n_components；先标准化；看 explained_variance_ratio

### Apriori
- 关键：min_support、min_confidence、lift；适合中小规模交易数据

## 5) 文本（快速链路）

- 中文：jieba 分词（可选）或直接 char-level TF-IDF
- 模型：LogReg / MultinomialNB 是强基线
- 注意：去停用词、限定 max_features、控制 ngram_range

