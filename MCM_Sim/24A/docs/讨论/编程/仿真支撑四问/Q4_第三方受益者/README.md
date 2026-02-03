## Q4：性别比例可变动是否会给其他生物（如寄生虫）带来优势？

### 纯文本回答（可直接写进论文）

我们把“受益第三方（B）”同时赋予两种生态含义（题面允许建模扩展，且用户要求两者都考虑）：

- `B_L`（图表中记为 B1）：与七鳃鳗寄生阶段 `J` 强相关的寄生虫/病原体。它的增长率随 `J` 增大而增大（传播链更完整），同时对 `J` 造成额外死亡（反噬）。  
- `B_H`（图表中记为 B2）：宿主鱼的机会性寄生虫/病原体。它依赖宿主“受损/易感性”指标 `W(H,J)`（随接触强度 `H·J` 饱和），并对宿主造成额外死亡。

核心问题是：当七鳃鳗能调节性别比例（`p_m(t)` 随资源/滞后变化）时，系统的 `H(t)` 与 `J(t)` 的统计分布会被重塑，从而改变第三方的“可入侵性、可维持性、以及是否容易暴发”。

我们提供三层证据（从易解释到更“硬核”）：

1) **常值环境入侵阈值（R0 口径）**  
   在 `B≈0` 的线性区间，`B_L` 的入侵阈值为  
   `R0_BL = (beta·f_J(J*))/d`；`B_H` 的入侵阈值为  
   `R0_BH = (beta·W(H*,J*))/d`。若 `R0>1` 则小量引入会增长并入侵。

2) **随机环境入侵指数（λ 口径）**  
   在随机环境轨迹 `J(t),H(t)` 上，计算线性增长率的时间平均  
   `lambda_BL ≈ (1/T)∫(beta·f_J(J(t)) - d)dt`（`>0` 可入侵），`lambda_BH` 同理。  
   这比常值阈值更接近题面“环境不确定性”的生态现实。

3) **四元（H + lamprey + B_L + B_H）全动力学**  
   直接在 Model-3 中仿真 `H,L,J,M,F,B_L,B_H`，统计第三方是否能在长期维持（endemic）或是否会出现短期暴发（outbreak），并同步输出系统层面的尾部风险/几何平均，把“第三方受益”与整体稳定性串联起来。

结论（用本目录的示例运行来描述趋势，而非宣称“永远如此”）：

- **第三方确实可能获得优势**：在多数策略下，`R0_BL/R0_BH>1` 且 `lambda_BL/lambda_BH>0`，意味着只要系统能维持一定的 `J` 或 `H·J` 接触强度，第三方就具备入侵条件。  
  极端偏雄固定策略 `S_78` 由于显著压低 `J`，会把 `R0` 与 `lambda` 压到 0 附近甚至为负，第三方难以入侵——这说明“第三方受益”与“七鳃鳗是否被压到极低”高度相关。
- **可变性别比不是单向利好第三方**：在全动力学中，增大 `gamma` 往往降低 `B_L/B_H` 的均值与维持概率、并降低 `B_H` 的暴发概率；反之，较小 `gamma`（更偏向维持较高的七鳃鳗水平）更有利于第三方。  
  也就是说，可变性别比通过改变 `J(t)` 与 `W(H,J)` 的分布，提供了一个“把第三方从优势区推回劣势区”的调参通道。
- **把 Q4 写成 Z 级故事的关键**：不要只回答“会/不会”；而是回答“在何种环境与策略参数下会（入侵/暴发/维持），机制是什么，代价是什么”。本目录的三层证据链可以支持这种写法。

---

### 每张图的含义与其对 Q4 的支撑作用

（A）常值环境入侵阈值：`R0` 口径

`results/figures/R0_BL.png`

- 含义：`S_var(gamma,w)` 网格下 `R0_BL` 热图（以 1 为中心；等值线=1）。
- 作用：回答“B_L 是否有入侵优势”的最直接证据。`R0_BL` 随 `J*` 增大而增大，因此也可解释为“七鳃鳗越多，B_L 越占优势”。

`results/figures/R0_BH.png`

- 含义：`R0_BH` 热图（以 1 为中心；等值线=1）。
- 作用：量化“宿主受损/接触强度”是否足以支撑 `B_H` 入侵。它把 Q4 与 Q1/Q3 的“宿主安全/稳定性”连接起来：宿主越被压低、`H·J` 越高，`R0_BH` 越大。

（B）随机环境入侵指数：`lambda` 口径

`results/figures/lambda_BL.png`

- 含义：随机环境下的入侵指数 `lambda_BL` 热图（>0 可入侵）。
- 作用：在随机环境下给出比 `R0` 更现实的判断：即使平均 `J` 不大，只要 `J(t)` 的时间结构（如连续丰年段）足够支撑正的长期平均增长，第三方仍可入侵。

`results/figures/lambda_BH.png`

- 含义：随机环境下 `lambda_BH` 热图（>0 可入侵）。
- 作用：回答“B_H 是否会在随机环境中获得优势”，并用于比较不同策略如何通过改变 `H(t),J(t)` 的协同波动来改变机会性寄生的入侵条件。

（C）全动力学：维持 vs 暴发（Model-3）

说明：本目录的全动力学示例中，阈值定义为  
`persist：mean_B > B_th`，`outbreak：max_B > B_out_th`（本次 `B_th=B_out_th=0.3`，见 `triad_markov_runs.csv`）。

`results/figures/mean_B1.png`

- 含义：`B_L` 的长期均值 `mean_B1`（burn-in 后）。
- 作用：给出第三方“优势强度”的连续刻画（比 0/1 的概率更信息丰富）；可用于论文中讨论“虽然都可入侵，但强度差多少”。

`results/figures/P_B1_persist.png`

- 含义：`B_L` 的长期维持概率 `P_B1_persist`（均值超过阈值）。
- 作用：回答“是否能形成地方性流行/长期寄生”的问题；它往往比 “outbreak” 更接近生态学上“稳定受益”。

`results/figures/P_B1_outbreak.png`

- 含义：`B_L` 的暴发概率 `P_B1_outbreak`（峰值超过阈值）。
- 作用：回答“是否容易出现短期暴发事件”。当该图接近 1 时，不代表“图没信息”，而是说明在给定阈值下暴发几乎不可避免，应转而用 `persist` 与 `mean_B1` 来区分策略差异（这也是我们同时输出三种口径的原因）。

`results/figures/mean_B2.png`

- 含义：`B_H` 的长期均值 `mean_B2`（burn-in 后）。
- 作用：即使 `P_B2_persist` 可能为 0（阈值较高），该图仍能显示 `B_H` 的“背景水平”并区分策略。

`results/figures/P_B2_persist.png`

- 含义：`B_H` 的长期维持概率（均值超过阈值）。
- 作用：判断 `B_H` 更像“长期地方病”还是“长期维持不了”。本次示例中出现全 0，主要是阈值 `B_th=0.3` 相对 `mean_B2` 偏高；应结合 `mean_B2` 与 `P_B2_outbreak` 一起解释，而不是把全 0 视为“模型无效”。

`results/figures/P_B2_outbreak.png`

- 含义：`B_H` 的暴发概率（峰值超过阈值）。
- 作用：把 `B_H` 的生态含义落到“机会性暴发”：即使长期均值不高，也可能在某些宿主受损阶段出现明显峰值；策略参数增大 `gamma` 往往降低此概率，体现可变性别比对第三方优势的“抑制通道”。

（D）系统层面的风险与典型水平（把 Q4 与 Q1/Q3 串起来）

`results/figures/q10_min_N.png`、`results/figures/geom_mean_N.png`

- 含义：在引入第三方后的系统里，七鳃鳗的尾部风险与几何平均。
- 作用：回答“第三方受益的代价”：第三方越占优势，往往越会压低 `N` 的尾部与几何平均，从而把系统推向更不利的稳定性区域。

`results/figures/q10_min_H.png`、`results/figures/geom_mean_H.png`

- 含义：宿主的尾部风险与几何平均（引入第三方后的版本）。
- 作用：判断“第三方受益”是否同时恶化宿主安全（尤其是 `B_H` 通过额外死亡反噬宿主），并辅助写出“第三方优势 ↔ 生态稳定性”的耦合结论。

`results/figures/trajectories_triad.png`

- 含义：代表性随机环境序列下的 `R/H/N/p_m/B1/B2` 轨迹对比（同一条环境序列下多策略）。
- 作用：机制可视化：展示 `B_L` 往往随 `J/N` 的变化快速上升并产生峰值、`B_H` 则在宿主受损阶段出现机会性抬升；同时可直观看到不同 `gamma,w` 如何改变 `p_m(t)` 的响应与第三方的涌现过程。

---

### 结果文件（便于写论文）

- `results/tables/q4_constant_runs.csv`：常值阈值表（`R0_BL/R0_BH`）
- `results/tables/q4_markov_runs.csv`：随机入侵指数表（`lambda_BL/lambda_BH`）
- `results/tables/triad_markov_runs.csv`：全动力学表（`mean/max/P_persist/P_outbreak` 以及系统层面的 `q10_min_* / geom_mean_*`）

---

### 可复现实验（原始输出目录）

- 常值阈值：`MCM_Sim/24A/outputs/temp/Q4_q4_constant_demo/`
- 随机入侵：`MCM_Sim/24A/outputs/temp/Q4_q4_markov_demo/`
- 全动力学（Model-3，示例阈值）：`MCM_Sim/24A/outputs/temp/Z_Q4_triad_Bth0.3_p005_rh10_q02_v2/`

复现命令：

```bash
python MCM_Sim/24A/run_sim.py q4-constant \
  --out-dir MCM_Sim/24A/outputs/temp/Q4_q4_constant_demo \
  --years 300 --steps-per-year 12 --R0 2.0 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5

python MCM_Sim/24A/run_sim.py q4-markov \
  --out-dir MCM_Sim/24A/outputs/temp/Q4_q4_markov_demo \
  --seed 123 --years 60 --reps 20 --steps-per-year 12 \
  --R-L 1.0 --RH-over-RL 5.0 --p 0.2 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.05 --burn-in 10

python MCM_Sim/24A/run_sim.py triad-markov \
  --out-dir MCM_Sim/24A/outputs/temp/Z_Q4_triad_Bth0.3_p005_rh10_q02_v2 \
  --model 3 --seed 126 --years 120 --reps 60 --steps-per-year 12 \
  --R-L 1.0 --RH-over-RL 10 --p 0.05 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.2 --burn-in 10 \
  --B-init 1e-6 --B-th 0.3
```
