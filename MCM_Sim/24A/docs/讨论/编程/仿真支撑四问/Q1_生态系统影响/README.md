## Q1：当七鳃鳗能改变性别比例时，对更大生态系统有何影响？

### 纯文本回答（可直接写进论文）

我们用“宿主鱼 H（归一化到 0~1）”作为更大生态系统的代理变量：  
七鳃鳗的寄生阶段 `J` 以比例形式损伤宿主（`dH/dt = r_H H(1-H) - damage(J)·H`），而宿主丰度又通过成熟率饱和项 `mu_J_eff(H)` 反馈影响七鳃鳗的成体产生（形成 `H ↔ J` 闭环）。因此，“能否调节性别比例”会同时改变七鳃鳗自身的增长/波动，并通过寄生压强改变宿主的长期水平与越界风险。

我们将“性别比例策略”抽象为雄性比例 `p_m(t)` 的反应范式：

- 固定对照：`S_50/S_56/S_78`（分别对应常数 `p_m=0.50/0.56/0.78`）
- 可变策略：`S_var(gamma,w)`  
  `gamma` 表示对幼体人均资源 `x` 的敏感度；`w` 表示记忆/滞后（用一阶低通滤波近似发育延迟）。资源差时更偏雄（`p_m ↑`，减少雌性从而抑制未来繁殖）；资源好时更偏雌（`p_m ↓`，提高补充率）。

在随机环境（两态马尔可夫丰歉年）下，我们用三类指标刻画“对更大生态系统的影响”：

1) **越界风险**：`P_host = P(min_t H(t) < H_safe)`（宿主跌破安全阈值的概率，越小越好）  
2) **长期典型水平**：`geom_mean_H`（burn-in 后时间加权几何平均，更贴近 bet-hedging 的“长期 log-fitness”语境，越大越好）  
3) **尾部风险**：`q10_min_H`（跨随机重复的“最低谷”10% 分位数，越大越好；并用 `H_safe` 的等值线标出安全/危险边界）

结论（以本目录的“Z 级临界区”参数为例：`R_H/R_L=10, p=0.05, years=200, reps=200, H_safe=0.3, q=0.2`）：

- 固定策略会走向“极端权衡”：  
  `S_50/S_56` 让七鳃鳗维持高水平，从而宿主越界概率极高（`P_host≈0.985/0.965`）；  
  `S_78` 几乎抑制/消灭七鳃鳗（`P_ext=1`），宿主安全但生态结构被“单边清空”。
- 可变策略存在“中间最优区间”：例如 `S_var(gamma=2,w=0)` 同时实现 `P_host=0` 与 `P_ext=0`，且提高宿主的 `q10_min_H` 与 `geom_mean_H`。  
  直观上，这是 **bet-hedging**：在长期可能出现的连续歉年中，策略通过提高雄性比例来降低未来繁殖强度，避免寄生者过冲与宿主崩溃；在丰年再把性别比调回更利于补充的区间。
- “过度敏感”会反噬：当 `gamma` 过大（如 8），七鳃鳗对资源波动的响应过激，反而显著增大其准灭绝风险（`P_ext≈0.995`），并把系统推向另一端极端。

因此，**七鳃鳗可变性别比并不必然“让生态更糟/更好”，而是在随机环境下提供一个可调的风险-收益旋钮**：适度敏感的调节可在保持七鳃鳗存续的同时显著降低宿主越界风险，从而改善更大生态系统的“韧性/安全性”。

---

### 每张图的含义与其对 Q1 的支撑作用

`results/figures/bet_hedging_triptych.png`

- 含义：对 `S_var(gamma,w)` 网格画 3 张热图：`P_ext`（七鳃鳗准灭绝概率）、`P_host`（宿主越界概率）、`mean_H`（宿主算术均值）。横轴 `gamma`，纵轴 `w`；格内数值为该格子策略的统计量；黑色星号为该子图意义下的“最优格子”（概率类取最小，均值类取最大）。
- 作用：一图同时展示“七鳃鳗生存风险 vs 宿主安全风险”的空间结构，直观看到：`gamma` 增大时 `P_host` 迅速降到 0，但 `P_ext` 在过大 `gamma` 时上升，证明存在 **中间最优**。

`results/figures/pareto_tradeoff.png`

- 含义：每个点代表一种策略；横轴 `P_host`，纵轴 `P_ext`（越靠左下越好）。点的颜色表示 `gamma`，形状表示 `w`，黑色大叉是固定策略；红圈标出可变策略的帕累托前沿。
- 作用：把“Q1 的生态影响”转化为**双目标风险权衡**：可以清晰指出既不牺牲宿主、也不靠“灭绝七鳃鳗”来取胜的策略（例如图上标注的 `g=2,w=0`）。

`results/figures/q10_min_H.png`

- 含义：`q10_min_H` 热图（宿主最低谷 10% 分位数）；黑色等值线是 `H_safe`。
- 作用：当 `P_host` 已经接近 0/1 而“看不出差异”时，这张图仍能区分策略的**尾部安全裕度**：在 `gamma≈2` 附近跨过 `H_safe` 等值线，支撑“宿主风险从危险区进入安全区”的结论。

`results/figures/geom_mean_H.png`

- 含义：`geom_mean_H` 热图（burn-in 后时间加权几何平均）。
- 作用：用 bet-hedging 更合理的指标刻画“长期典型宿主水平”，避免被偶然高峰拉高的算术均值误导；它与 `q10_min_H` 共同构成“典型水平 + 尾部风险”的 Z 级叙事组合。

`results/figures/q10_min_N.png`

- 含义：`q10_min_N` 热图（七鳃鳗最低谷 10% 分位数）；等值线为 `N_q`（准灭绝阈值）。
- 作用：用于排除“宿主安全只是因为七鳃鳗被压到极低”的伪解释：在宿主安全区（`P_host≈0`）内，仍可区分“七鳃鳗仍健在（`q10_min_N>N_q`）”与“逼近灭绝边缘”的策略。

`results/figures/geom_mean_N.png`

- 含义：`geom_mean_N` 热图（七鳃鳗的长期典型水平）。
- 作用：与 `geom_mean_H` 对应，说明改善宿主并不必然意味着把七鳃鳗“压没了”，并为后续 Q2/Q3 的“种群利弊/韧性”提供同一套主指标口径。

`results/figures/P_rec_N.png`

- 含义：`P_rec_N` 热图，表示“从 burn-in 后的最坏低谷恢复到 `N_target=rec_target_frac·N_ref` 并持续 `rec_hold_years` 年”的成功概率。
- 作用：在 Q1 语境中它是**生态闭环的动态证据**：宿主安全的策略不应导致七鳃鳗在连续歉年后永远回不来；该图可用于挑选“既保护宿主、又保留七鳃鳗恢复能力”的策略区间。

`results/figures/median_T_rec_N.png`

- 含义：`median_T_rec_N` 热图（恢复所需时间的中位数；未恢复的记为 `years`）。
- 作用：与 `P_rec_N` 配套：同样的恢复概率下，恢复更快意味着系统更“韧性”，可用于把 Q1 的“影响”进一步细化为“更快回到可接受生态状态”。

`results/figures/trajectories_compare.png`

- 含义：在同一条代表性随机环境序列（挑选“最坏连续歉年最长”的那条）下，画出 `R(t), H(t), N(t), p_m(t)` 的策略对比轨迹。
- 作用：提供“机制可视化”：能够直观看到可变策略如何在连年歉收期间提高 `p_m`、压制未来繁殖，从而让 `N` 不发生过冲，最终让 `H` 避免跌破危险区。

`results/figures/seasonal_trajectories.png`

- 含义：在季节资源 `R(t)=R0(1+A sin(2πt/T))` 下的 `R/H/N/p_m` 轨迹对比。
- 作用：补充展示“资源节律 → 性别比响应 → 种群/宿主动态”的链路，便于把 Q1 的结论写成“可解释的生态控制机制”，而不仅是统计热图。

---

### 结果文件（便于写论文）

表格：

- `results/tables/bet_hedging_runs.csv`：bet-hedging 主表（含 `P_host/mean_H/q10_min_H/geom_mean_H`，以及 `P_ext/q10_min_N/geom_mean_N/P_rec_N/median_T_rec_N` 等用于权衡的列）
- `results/tables/seasonal_runs.csv`：季节资源对照表

---

### 可复现实验（原始输出目录）

这些结果来自以下运行目录（可回溯 `config.json` 与环境序列）：

- bet-hedging（Z 级临界区）：`MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02/`
- seasonal：`MCM_Sim/24A/outputs/temp/Q1_seasonal_demo/`

复现命令（与上述目录一致）：

```bash
python MCM_Sim/24A/run_sim.py bet-hedging \
  --out-dir MCM_Sim/24A/outputs/temp/Z_bet_critical_p005_rh10_q02 \
  --seed 123 --years 200 --reps 200 --steps-per-year 12 \
  --R-L 1.0 --RH-over-RL 10 --p 0.05 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.2 --burn-in 10

python MCM_Sim/24A/run_sim.py seasonal \
  --out-dir MCM_Sim/24A/outputs/temp/Q1_seasonal_demo \
  --years 20 --steps-per-year 48 \
  --R0 2.0 --A 0.5 --T 1.0 \
  --gammas 0.5,1,2,4,8 --ws 0,3,5 \
  --H-safe 0.3 --q 0.05 --burn-in 5
```
