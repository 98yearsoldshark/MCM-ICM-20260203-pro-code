# 插入建议

- 建议插入位置：在正文解释“为什么不同场景的 TTE 差这么多”时，选择 1 张低负载代表轨迹 + 1 张高负载代表轨迹。本文建议用 Q2.13（待机）与 Q2.14（游戏）成对出现。
- 用途：用连续时间轨迹解释“drivers + 不确定性 + 终止边界”的机理链路，提升可解释性。

# 可直接粘贴到论文的文本（中文）

## Q2.13 解释性轨迹：待机/轻后台场景的连续时间演化

为直观展示连续时间模型如何解释“场景之间差异”和“不确定性来源”，我们给出关键状态量的代表性轨迹。图 Q2-13 展示了在 $SOC_0=1.0$、待机/轻后台场景下的时间序列（SOC、端电压、温度与总功耗）。

（在此插入图 Q2-13）

图 Q2-13：待机/轻后台场景下的代表性轨迹（SOC、端电压、温度、总功耗）。

可以看到，SOC 在长时间尺度上缓慢下降，而总功耗 $P_{total}$ 出现间歇性尖峰，这些尖峰来自随机后台唤醒或短时网络尾态事件。尖峰瞬时幅度可能不大，但在长时程累积后会显著影响 TTE 的离散度，并推动端电压更早触达欠压截止阈值。端电压 $V_{term}$ 在整个过程中缓慢下降，并在接触 $V_{cut}$ 时触发关机，这与本文将 TTE 定义为“首次触发终止边界”的口径一致。

（这是讲解内容，论文中可删除）  
读图要点：左上 SOC 近似线性下降（低负载下主要由平均功率决定）；右下 $P_{total}$ 的尖峰对应后台唤醒/短时网络尾态；右上 $V_{term}$ 最终触碰虚线（$V_{cut}$）触发关机。  
它与 “04 不确定性宽度排名” 是配套的：待机为何不确定性更大？因为尖峰事件是随机过程。  

# 可直接粘贴到论文的文本（英文）

## Q2.13 Mechanistic explanation via trajectories (standby)

To illustrate how the continuous-time model explains scenario-to-scenario differences, we examine representative trajectories of the key state variables. Figure Q2-13 shows the simulated time series under the standby/light-background scenario at $SOC_0=1.0$.

(Insert Figure Q2-13 here.)

Figure Q2-13: Example trajectories under standby/light-background (SOC, terminal voltage, temperature, and total power).

The SOC decreases slowly over a long horizon, while the total power exhibits intermittent spikes due to stochastic background wake-ups. These rare events are small in instantaneous magnitude but accumulate over time and contribute to both uncertainty (wide TTE spread) and the eventual voltage cutoff. The terminal voltage declines gradually and triggers shutdown when it reaches $V_{cut}$, consistent with the first-termination definition of TTE.
