## Q2：七鳃鳗种群性别比例变化的优点与缺点是什么？

### 纯文本回答（可直接写进论文）

我们把“七鳃鳗种群利弊”拆成三句话：

1) **优点（bet-hedging）**：当环境存在随机切换与连续歉年风险时，允许 `p_m(t)` 随资源条件调整，相当于在“繁殖强度”上做自适应节流/放大，从而提高长期典型水平（几何平均）并改善尾部风险。  
2) **缺点（过度响应/滞后）**：若对资源过于敏感（`gamma` 过大），或记忆太长导致响应滞后（`w` 过大且环境切换快），可能出现“错配”：该抑制时不抑制、该恢复时恢复慢，反而增加准灭绝风险或降低恢复能力。  
3) **必须与宿主代价一起看**：七鳃鳗“成功”若以宿主长期越界为代价，则对生态系统不可接受，因此我们在比较时显式加入 `P_host` 约束。

为使论证不被“概率指标饱和（全 0/全 1）”掩盖，我们采用四组互补指标：

- **持久性/灭绝风险**：`P_ext = P(min_t N(t) < N_q)`（准灭绝概率，越小越好）
- **尾部风险**：`q10_min_N`（最低谷 10% 分位数，越大越安全）
- **长期适应度代理**：`geom_mean_N`（burn-in 后时间加权几何平均；bet-hedging 的主指标之一）
- **韧性（恢复）**：`P_rec_N` 与 `median_T_rec_N`（从最坏低谷回升到“健康目标”`N_target=rec_target_frac·N_ref` 的概率与时间）

结论（以本目录“Z 级临界区”参数为例：`R_H/R_L=10, p=0.05, years=200, reps=200, q=0.2`）：

- 固定策略的两个极端：  
  `S_78`（长期偏雄）会显著降低补充率，导致七鳃鳗准灭绝（`P_ext=1`）；  
  `S_50/S_56`（更偏雌）能保持七鳃鳗高水平（`P_ext=0`，`geom_mean_N` 高），但宿主越界概率极高（`P_host≈0.985/0.965`），属于“以生态崩溃换种群繁荣”。
- 可变策略呈现清晰的“甜点区”：  
  例如 `S_var(gamma≈2,w≈0)` 在本情景中能做到 `P_ext=0` 且 `P_host=0`，并给出较好的 `q10_min_N/geom_mean_N`（即“既不被灭绝，也不过度压榨宿主”）。  
  但当 `gamma` 进一步增大（如 8），`P_ext` 会骤升（过度响应导致种群在连续歉年中崩盘），体现了可变策略的潜在代价。

**环境相图（p × R_H/R_L）**进一步揭示：最优 `(gamma,w)` 不是常数，而会随环境相关性与波动幅度迁移——这正是 bet-hedging 的“适应性亮点”（冲 Z 的关键证据链）。在连续歉年更常见（`p` 更小）且波动更强（`R_H/R_L` 更大）时，最优解倾向于更强的即时调节（更大的 `gamma`、更小的 `w`）；当环境切换快（`p` 较大）或波动弱时，较小 `gamma` 与更长记忆可更稳健。

---

### 每张图的含义与其对 Q2 的支撑作用

`results/figures/bet_hedging_triptych.png`

- 含义：`S_var(gamma,w)` 网格的 `P_ext / P_host / mean_H` 三联热图。
- 作用：其中 `P_ext` 子图直接回答“性别比可变如何影响准灭绝风险”；同时结合 `P_host` 子图可说明：降低 `P_ext` 的同时可能带来宿主代价，必须做权衡。

`results/figures/q10_min_N.png`

- 含义：七鳃鳗尾部风险 `q10_min_N`；黑色等值线为 `N_q`。
- 作用：在 `P_ext` 尚未明显分化（或已经饱和）时，用尾部指标继续区分策略的“最坏情景安全裕度”，是 bet-hedging 论文叙事的核心证据之一。

`results/figures/geom_mean_N.png`

- 含义：`geom_mean_N`（burn-in 后几何平均）。
- 作用：作为“长期适应度/长期典型水平”的代理指标，能把“平均很高但偶尔归零”的策略与“平均稍低但长期稳健”的策略区分开，为冲 Z 的 bet-hedging 叙事提供量化抓手。

`results/figures/P_rec_N.png`

- 含义：从最坏低谷恢复到目标 `N_target` 的成功概率。
- 作用：回答“变化带来的优点/缺点”时，这是最直观的“韧性指标”：同样不灭绝的策略之间，恢复成功率更高意味着更能对冲连续歉年冲击。

`results/figures/median_T_rec_N.png`

- 含义：恢复时间的中位数（未恢复记为 `years`）。
- 作用：与 `P_rec_N` 配套：不仅要“能恢复”，还要“恢复得快”；恢复慢会让种群长期处在低位，更容易受到其他扰动叠加而进入准灭绝。

`results/figures/pareto_tradeoff.png`

- 含义：`P_host`（横轴）与 `P_ext`（纵轴）的散点与帕累托前沿。
- 作用：把 Q2 的“七鳃鳗利弊”提升到生态可接受的语境：指出哪些策略是“对七鳃鳗好但对宿主不可接受”，哪些策略能在约束下仍保持较好 `P_ext`。

`results/figures/trajectories_compare.png`

- 含义：同一条“最坏连续歉年最长”的随机环境序列下，比较多策略的 `R/H/N/p_m` 轨迹。
- 作用：机制解释用：展示可变策略如何通过调节 `p_m` 改变未来补充，进而改变 `N` 的过冲与低谷深度；能把统计结果写成“因果链”。

`results/figures/geom_mean_H.png` 与 `results/figures/q10_min_H.png`

- 含义：宿主的几何平均与尾部风险热图。
- 作用：用于在 Q2 中说明“七鳃鳗自身获益”往往意味着“宿主代价”；把 Q2 的结论写成“优势/劣势来自何种权衡”，而不是单独讨论 `N`。

`results/figures/phase_best_gamma.png`

- 含义：环境相图：在 `P_host<=0.2` 生态约束下，使目标（默认 `geom_mean_N`）最大的最优 `gamma`（格内同时标注最优 `gamma,w`）。
- 作用：直接回答“如何选择策略以最大化 bet-hedging 表现”：当环境更相关/更剧烈时，最优 `gamma,w` 会迁移；这能把模型从“单场景结果”升级为“适应性相图”（Z 级亮点）。

`results/figures/phase_objective.png`

- 含义：同一相图上，颜色表示最优可达到的目标值（这里是 `geom_mean_N`），格内标注最优 `gamma,w`。
- 作用：补全相图叙事：不仅知道“选什么参数”，还知道“能得到多大收益”，并可用于论文中的敏感性讨论与管理建议。

---

### 结果文件（便于写论文）

- `results/tables/bet_hedging_runs.csv`：Q2 主表（含 `P_ext/q10_min_N/geom_mean_N/P_rec_N/median_T_rec_N` 及对照所需的宿主列）

---

### 可复现实验（原始输出目录）

这些结果来自：

- bet-hedging（Z 级临界区）：`MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02/`
- 环境相图（多组 run 汇总）：`MCM_Sim/24A/outputs/temp/Z_env_phase_demo/`

复现命令：

```bash
python MCM_Sim/24A/run_sim.py bet-hedging \
  --out-dir MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02 \
  --seed 123 --years 200 --reps 200 --steps-per-year 12 \
  --R-L 1.0 --RH-over-RL 10 --p 0.05 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.2 --burn-in 10

python MCM_Sim/24A/scripts/make_env_phase.py \
  --run-dirs MCM_Sim/24A/outputs/temp/Z_bet_p005_rh5_q02,MCM_Sim/24A/outputs/temp/Z_bet_p02_rh5_q02,MCM_Sim/24A/outputs/temp/Z_bet_p05_rh5_q02,MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02,MCM_Sim/24A/outputs/temp/Z_bet_p02_rh10_q02,MCM_Sim/24A/outputs/temp/Z_bet_p05_rh10_q02 \
  --host-max 0.2 --objective geom_mean_N \
  --out-dir MCM_Sim/24A/outputs/temp/Z_env_phase_demo
```
