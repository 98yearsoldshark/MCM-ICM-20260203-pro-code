# 进阶算法笔记（来自目录 6 的补齐）

本笔记把资料目录里“少见/进阶”的算法要点，整理成可直接复用的文字说明，并给出 Toolkit 内对应实现路径（均带 `solve(data, params)` + `__main__` Demo）。

## 1) 免疫遗传算法（IGA / Immune GA）

对应实现：

- `MCM_Toolkit_2026/c12_优化算法_Optimization/immune_algorithm.py`

资料来源（Matlab 版）：

- `6、按赛题类别划分的常用算法代码/.../免疫优化算法在物流配送中心选址中的应用代码/*.m`

核心机制（竞赛可记这 3 点）：

1. **适应度（fitness）**：目标函数值（默认最小化）。
2. **相似度/浓度（concentration）**：衡量个体与群体的“雷同程度”，相似度高则浓度高。
3. **优秀度（excellence）**：用一个权重 `ps` 组合“适应度好 + 浓度低”，驱动繁殖概率，并配合“记忆库（elite memory）”保留优秀抗体。

常用相似度定义（资料版是“基因集合重合度”）：

- 对“选址/选点”类（从 n 个候选点选 k 个），可把解表示为 0/1 向量且固定 `k` 个 1：
  - 相似度 `sim(x,y) = |Sx ∩ Sy| / k`

参数建议：

- `ps` 越大越像“纯遗传算法”；`ps` 越小越强调“去重/多样性”
- `memory_size` 小而稳（例如 5~20），有助于避免好解被随机操作破坏
- 对“必须选 k 个点”的问题，推荐直接用 `n_ones=k` 约束（比后期修复稳定）

## 2) 人工鱼群算法（AFSA）求解 TSP（离散版）

对应实现：

- `MCM_Toolkit_2026/c12_优化算法_Optimization/artificial_fish_swarm_tsp.py`

资料来源（Matlab 版）：

- `6、按赛题类别划分的常用算法代码/.../人工鱼群求解TSP问题源代码/*.m`

资料实现的 4 种行为：

- 追尾（Follow）：在“视野邻域”内跟随更优路径（若不拥挤）
- 觅食（Prey）：随机扰动当前路径（资料中用“选 DJ 个位置做循环移位”）找更优解
- 聚群（Swarm）：尝试向邻域中心路径靠拢（中心由“每个位置最常出现的城市”构造）
- 随机（Random）：若以上都无改进，随机生成新路径

关键点：

- `Visual` 在资料里不是欧氏距离，而是“路径汉明距离阈值”（对应位置不同的数量）。
- 若你已有 ACO/2-opt/退火等基线，AFSA 更适合做“对照/备份”，不一定比经典 TSP 方法更强。

## 3) 量子遗传算法（QGA）

对应实现：

- `MCM_Toolkit_2026/c12_优化算法_Optimization/quantum_genetic_algorithm.py`

资料来源（Matlab 版）：

- `6、按赛题类别划分的常用算法代码/.../量子遗传算法代码/*.m`

核心概念：

- 每一位不是 0/1，而是量子比特振幅 `(α, β)`，满足 `α^2 + β^2 = 1`
- **测量（collapse）**：以概率 `P(0)=α^2`、`P(1)=β^2` 采样出经典二进制串
- **量子旋转门（Qgate）**：根据“当前位与全局最优位是否一致 + 当前个体优劣”，用小角度 `delta` 旋转 `(α,β)`，逐步把概率推向最优位

在资料版中：

- 通过二进制编码把连续变量映射到区间：`x = low + int(bits)/(2^L-1) * (high-low)`
- 默认是“最大化”目标函数（Toolkit 里 `maximize=False` 会自动转成最大化 `-f`）

## 4) 多目标粒子群（MOPSO）

对应实现：

- `MCM_Toolkit_2026/c12_优化算法_Optimization/mopso.py`

资料来源（Matlab 版）：

- `6、按赛题类别划分的常用算法代码/.../多目标粒子群优化算法代码/*.m`

核心机制：

- **外部档案库（Repository/Archive）**：存储当前非支配解（Pareto 近似解集）
- **网格（Hypercubes）**：把目标空间划成网格，统计每个网格里有多少解（拥挤度）
- **Leader 选择**：更偏向从“解更稀疏”的网格里选 leader（参数 `beta` 控制压力）
- **Archive 裁剪**：若 archive 过大，优先从“更拥挤”的网格删解（参数 `gamma`）

注意：

- 这里默认所有目标都是“越小越好”（minimization）。
- 如果你只需要多目标的稳定实现，Toolkit 也提供 `NSGA-II`：`MCM_Toolkit_2026/c12_优化算法_Optimization/nsga2.py`。

## 5) GRNN / RBF / 小波神经网络（预测类）

对应实现：

- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/grnn.py`
- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/rbf_network.py`
- `MCM_Toolkit_2026/c08_神经网络_NeuralNetwork/wavelet_neural_network.py`

资料来源（Matlab 版）：

- GRNN：`.../基于广义回归神经网络货运量预测代码/chapter8.1.m`
- RBF：`.../混沌时间序列的RBF神经网络预测代码/Main_RBF*.m`
- WNN：`.../小波神经网络的时间序列预测代码/chapter32/wavenn.m`

三者在竞赛中怎么选：

- GRNN：参数少、实现短、适合小样本快速回归；关键是选 `sigma/spread`
- RBF 网络：介于“核方法”和“神经网络”之间；常作为非线性回归强基线
- 小波神经网络：对周期/局部特征更敏感；更像“带可学习参数的小波基函数”

通用建议：

- 先把序列做成监督学习样本（滞后特征、滚动窗口），再套上述模型；必要时做归一化
- 若想要“比赛更稳”的时间序列，优先试 `ARIMA / 指数平滑`（见 `c11_预测预报_Forecasting/`）

## 6) 物元分析法（Matter-Element / Extension Evaluation）

对应实现：

- `MCM_Toolkit_2026/c10_评价与决策_DecisionMaking/matter_element.py`

资料来源（Matlab 版，压缩包内为 Excel + 脚本）：

- `6、按赛题类别划分的常用算法代码/.../物元分析法多指标评价模型（matlab）.zip`

要点：

- 需要为每个指标给出各等级的“经典域区间” `[a(i,j), b(i,j)]`，节域一般取所有经典域的整体范围
- 通过关联函数 `k(i,j)` 计算“指标 i 的当前值对等级 j 的符合程度”，再用权重加权得到各等级的组合关联度 `kp(j)`
- `kp` 最大的等级作为评价等级；`j*` 可作为连续化的“等级特征值”
