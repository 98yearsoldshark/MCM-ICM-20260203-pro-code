## Q3：性别比例变化对生态系统稳定性有何影响？

### 纯文本回答（可直接写进论文）

赛题中的“生态系统稳定性”并不仅仅指“线性系统是否发散”，更关键的是：在随机环境与反馈滞后存在时，系统是否会出现深度低谷、长期恢复不过来、或被扰动推入另一种状态。为此我们采用两条互补证据链：

1) **常值环境下的局部稳定（线性化）**  
   以常值资源 `R=R0` 的共存（或灭绝）平衡点为基准，计算 Jacobian 的最大特征值实部 `max_real`：  
   - `max_real < 0`：局部渐近稳定（小扰动会衰减）  
   - `return_time ≈ 1/|max_real|`：回归时间尺度（越小越“快回归”）  
   这回答“系统在平均意义下是否容易振荡/失稳”。

2) **随机环境下的韧性（经验稳定性）**  
   在两态马尔可夫丰歉年环境中，统计从“最坏低谷”恢复到目标水平的概率与时间（`P_rec_N/median_T_rec_N`），并用 bet-hedging 的两类稳健指标补充：  
   - `q10_min_N`：最低谷 10% 分位数（尾部风险）  
   - `geom_mean_N`：时间加权几何平均（长期典型水平）  
   这回答“系统是否会被连续歉年推入长期低位/准灭绝”。

对“性别比例可变动”的影响，我们的解释是：`p_m(t)` 的调节把环境冲击转化为“繁殖强度的自适应控制”。适度的敏感度 `gamma` 能在歉年自动减少雌性比例（降低未来补充、避免过冲与资源-寄生反馈的恶化），在丰年再恢复；而记忆 `w` 则代表滞后/窗口平均，会带来“平滑噪声”与“反应变慢”的双重效应。因此，稳定性并非单调随 `gamma/w` 改善：过度敏感或过度滞后都可能降低韧性。

本目录的结果显示（示例参数见下方“可复现实验”）：

- **局部稳定性**：在 `R0=2.0` 的常值资源下，本次扫描的 `S_var(gamma,w)` 网格整体 `max_real<0`，即局部稳定；不同参数的 `|max_real|` 不同，表示回归速度差异。注意：固定 `S_78` 的“极强稳定”主要对应七鳃鳗接近灭绝的平衡点，生态含义需结合 `N_star` 解读。
- **随机韧性**：在随机环境下，`q10_min_N/geom_mean_N` 与 `P_rec_N/median_T_rec_N` 提供了比“是否越界”更细的稳定性刻画；可变策略在某些参数区间能显著抬高尾部低谷并缩短恢复时间，从而提高系统韧性；但当 `gamma` 过大时会出现“失稳式崩盘”（表现为 `P_ext` 上升、恢复失败、几何平均下滑）。

结论上可以写成：**可变性别比通过“对环境风险的自适应节流”增强系统韧性，但存在最佳调节强度；稳定性提升来自尾部风险降低与恢复能力增强，而不是简单的线性稳定性差异。**

---

### 每张图的含义与其对 Q3 的支撑作用

`results/figures/max_real.png`

- 含义：常值资源下，`S_var(gamma,w)` 的 `max_real` 热图（最大特征值实部，<0 稳定）。
- 作用：回答“线性意义下是否稳定/多快回归”；图中更负的区域代表更快的局部回归。它提供了严格的数学稳定性证据链（Jacobian 线性化）。

`results/figures/q10_min_N.png`

- 含义：随机环境下七鳃鳗尾部风险 `q10_min_N`（最低谷 10% 分位数）；等值线为 `N_q`。
- 作用：把“稳定性”落到“最坏情景是否会跌入危险区”的可解释指标上，避免仅用 `P_ext` 造成的饱和问题。

`results/figures/geom_mean_N.png`

- 含义：`geom_mean_N`（burn-in 后几何平均）。
- 作用：用 bet-hedging 视角刻画长期典型状态；在随机环境下，比算术均值更能反映“长期稳定可持续”的策略差异。

`results/figures/P_rec_N.png`

- 含义：恢复成功率 `P_rec_N`（从最坏低谷回到 `N_target` 并维持一段时间）。
- 作用：直接量化“韧性”：即使系统线性稳定，也可能在随机冲击下长期回不到健康水平；该图补上这一层。

`results/figures/median_T_rec_N.png`

- 含义：恢复时间中位数（未恢复记为 `years`）。
- 作用：与 `P_rec_N` 配套，把稳定性从“能否回去”细化到“回去要多久”；恢复慢意味着更容易叠加其他扰动而失稳。

`results/figures/q10_min_H.png` 与 `results/figures/geom_mean_H.png`

- 含义：宿主尾部风险与几何平均（与 Q1 同口径）。
- 作用：把“稳定性”扩展到系统层面：某些策略即使让 `N` 稳，也可能让 `H` 在尾部情景下越界；这两图用于论证“稳定性是整体生态闭环的性质”。

`results/figures/trajectories_compare.png`

- 含义：代表性随机环境序列下的 `R/H/N/p_m` 轨迹对比。
- 作用：解释“为何稳定性会变”：可视化滞后 `w` 与敏感度 `gamma` 如何改变 `p_m` 的响应、以及由此导致的过冲、低谷与恢复过程，为论文中的机制讨论提供直观证据。

---

### 结果文件（便于写论文）

- `results/tables/stability_runs.csv`：常值资源下的 `max_real/return_time/dominant_period`
- `results/tables/bet_hedging_runs.csv`：随机环境下的 `q10_min_N/geom_mean_N/P_rec_N/median_T_rec_N` 等韧性指标

---

### 可复现实验（原始输出目录）

- 常值稳定：`MCM_Sim/24A/outputs/temp/Q3_stability_demo/`
- 随机韧性（Z 级临界区）：`MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02/`

复现命令：

```bash
python MCM_Sim/24A/run_sim.py stability \
  --out-dir MCM_Sim/24A/outputs/temp/Q3_stability_demo \
  --years 300 --steps-per-year 12 --R0 2.0 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 --eps 1e-6

python MCM_Sim/24A/run_sim.py bet-hedging \
  --out-dir MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02 \
  --seed 123 --years 200 --reps 200 --steps-per-year 12 \
  --R-L 1.0 --RH-over-RL 10 --p 0.05 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.2 --burn-in 10
```
