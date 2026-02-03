# 插入建议

- 建议插入位置：接在图 01/02 之后，作为 **Q2.3（Quantify uncertainty）** 小节的主图。
- 用途：用分布/区间而不是单一数值回答赛题 “quantify uncertainty”。

# 可直接粘贴到论文的文本（中文）

## Q2.3 TTE 预测的不确定性量化（UQ）

真实手机的耗电行为存在不确定性，原因主要有两类：（i）部分关键参数在现实中并非固定常数（例如截止电压策略 $V_{cut}$、PMIC 转换效率 $\eta_{PMIC}$、有效容量等），（ii）即使在相同“场景标签”下，用户/后台行为仍会引入随机性（例如后台随机唤醒、网络尾态的偶发触发）。为在不违背赛题“连续时间机理模型”硬约束的前提下量化不确定性，我们采用蒙特卡洛抽样，把不确定参数与随机过程传播到 ODE 仿真输出，从而得到 TTE 的分布。

图 Q2-3 展示了 $SOC_0=1.0$ 时不同场景的 TTE 分布；小提琴图的红线为中位数，上方括号为 5%–95% 区间。

（在此插入图 Q2-3）

图 Q2-3：不同场景下的 TTE 分布（$SOC_0=1.0$）。

可以观察到：高负载、短时耗尽的场景（例如游戏）分布相对更窄，TTE 主要由持续能量消耗决定；而低负载、长时持续的场景（待机/混合使用）分布明显更宽，因为稀疏的后台唤醒与间歇网络尾态会在长时间尺度上累积并放大波动，使“剩余可用时间”天然更可变。

（这是讲解内容，论文中可删除）  
写作时建议明确说明：这里的不确定性来自“参数不确定（$V_{cut}$、$\eta_{PMIC}$、组件功耗缩放等）+ 行为随机性（后台 Poisson 唤醒、网络尾态）”，以避免被误解为“纯统计拟合/黑盒回归”。

# 可直接粘贴到论文的文本（英文）

## Q2.3 Quantifying uncertainty in TTE predictions

Real smartphone battery behavior is uncertain because (i) several parameters are not fixed constants in practice (e.g., cutoff voltage policy, PMIC efficiency, effective capacity), and (ii) user/background activities introduce randomness even under the same “scenario label”. To quantify this uncertainty without violating the problem requirement of a continuous-time mechanism model, we propagate uncertainty through the ODE simulation using Monte Carlo sampling.

Figure Q2-3 shows the resulting **TTE distributions** for $SOC_0=1.0$ across scenarios. Each violin summarizes the simulated TTE samples; the red bar denotes the median, and the annotated bracket indicates the 5%–95% interval.

(Insert Figure Q2-3 here.)

Figure Q2-3: Distribution of TTE (SOC0=1.0) under Monte Carlo uncertainty propagation.

Two observations are noteworthy. First, scenarios dominated by sustained high load (e.g., gaming) exhibit relatively tight distributions: TTE is mainly determined by deterministic energy draw. Second, low-power long-duration scenarios (standby and mixed day) exhibit much wider spreads because rare background wake-ups and intermittent network tails accumulate over long horizons, making the remaining time-to-empty inherently more variable.
