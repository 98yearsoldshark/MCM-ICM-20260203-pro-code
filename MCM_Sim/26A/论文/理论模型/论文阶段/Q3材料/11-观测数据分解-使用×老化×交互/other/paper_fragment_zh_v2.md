<!-- 备选版本：若你决定用 v2 图替换/补充正文 figure.png，可直接拷贝本段到论文 Q3 小节。 -->

## 7.3 观测数据锚定（增强版）：使用强度分位下的 usage×aging 分解与稳健性

在真实使用环境中，“使用强度”并非固定常数，而是在低/中/高负载间波动；同时，老化带来的增阻会让高负载更接近欠压边界。为把这种 **usage×aging 交互**以评委友好的方式呈现，我们把 AndroWatts 的 phone\_test 按观测总功耗三分位分组（低/中/高），并在每个组内对 (phone\_test×battery\_state) 的平衡设计仿真结果做方差分解。

![图 Q3-11(v2)：TTE 波动来源分解（总体 + 按观测功耗分位分组）。](./figure_v2_variance_decomposition_power_bins.png)

图中每条堆叠条表示在对应的使用强度组内，TTE 的总体波动可分解为四部分：**使用主效应（phone\_test）**、**老化主效应（battery\_state）**、二者的 **交互项** 以及 **随机过程（seed）**。总体上，使用差异仍是主导因素；但当使用强度升高时，老化相关项（以及交互项）在比例与风险意义上更重要——这为题面所描述的“同样使用却更快掉电/突然关机”提供了一个可量化解释：高负载使电池工作点更靠近欠压边界，增阻/OCV 变化会放大瞬时压降并提前触发截止。

为了避免“敏感性结论只对当前样本有效”的质疑，我们对 phone\_test 做 cluster bootstrap，计算分解占比的 95% 置信区间，结果显示主结论在抽样扰动下保持稳定。

![图 Q3-11(v2b)：观测锚定分解的抽样不确定性（Bootstrap 95% CI）。](./figure_v2_variance_decomposition_bootstrap_ci.png)

此外，我们用 new 与 eol 的对照强调：即便 TTE 端看起来近似比例缩放，**欠压裕量（headroom margin）** 在高功耗下会出现更明显的下降，从而更直接连接到“突然掉电”的物理机制（详见附图）。

![图 Q3-11(v2c)：new vs eol：老化对欠压裕量与 TTE 的影响随使用强度变化。](./figure_v2_aging_penalty_margin_vs_obs_power.png)

为进一步降低正文读图门槛，我们将原始 24×6 的 cell 结果压缩为 3×6（低/中/高功耗 × 6 个老化档位），并在格内标注均值小时数，用于快速传达“使用强度与老化共同缩短续航”的主效应趋势。

![图 Q3-11(v2d)：TTE（均值）在使用强度分位×老化档位上的变化（压缩热图）。](./figure_v2_tte_heatmap_power_bins_vs_aging.png)

最后，为避免“结论只对某个电芯成立”的质疑，我们在同一 battery\_dataset 下分别选取 Cell01/02/03 的老化状态表重复该实验，并得到近似一致的分解结构（使用主导、老化次之、交互更小），从而增强泛化性与可信度（适合放在 Appendix 或正文小图）。

![图 Q3-11(v2e)：观测锚定分解的跨电芯稳健性对照（Cell01/02/03）。](./figure_v2_variance_decomposition_cells_compare.png)
