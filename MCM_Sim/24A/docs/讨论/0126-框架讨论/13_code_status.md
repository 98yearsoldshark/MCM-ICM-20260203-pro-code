## 当前实现状态（代码/仿真/图表）

本文件用于回答“目前做到了哪一步、产物在哪里、还有哪些没做”，方便你后续以初学者视角提问时快速对齐上下文。

---

## 1 代码与目录（你最常用的入口）

- 仿真入口（CLI）：`MCM_Sim/24A/run_sim.py`
- 核心模型与工具包：`MCM_Sim/24A/src/mcm24a/`
- 快速自检（能不能跑）：`MCM_Sim/24A/scripts/smoke_test.py`
- 重绘论文级图片（不重跑仿真）：`MCM_Sim/24A/scripts/make_figures.py`
- 环境相图（不重跑仿真）：`MCM_Sim/24A/scripts/make_env_phase.py`（汇总多组 bet-hedging run 得到 `p × R_H/R_L` 相图）
- 输出目录：`MCM_Sim/24A/outputs/`
- 默认中间产物：`MCM_Sim/24A/outputs/temp/`（便于保持 `outputs/` 干净；最终版可用 `--out-dir` 指定到其他目录）

---

## 2 已实现的模型逻辑（摘要）

### 2.1 Model-0（基线）

- 系统：宿主鱼 `H` + 七鳃鳗 `L/J/M/F` + 记忆变量 `x_bar`
- 性别比：`p_m(x_eff)` 锚定题面 0.78/0.56，并支持 `gamma`（敏感度）与 `w`（记忆长度）
- 反馈闭环：`J` 伤害宿主；宿主又反向影响 `J->成体` 成熟率（避免“宿主只挨打不反作用”）
- 可选人类捕捞：对成体额外移除 `u_A(A)`，支持恒定 + 门控（近似“吃/不吃”的开关）

### 2.2 Model-1/2/3（三元扩展：受益第三方）

- Model-1：`B_L`（依赖七鳃鳗寄生期/伤口资源增长，并反噬七鳃鳗）
- Model-2：`B_H`（依赖宿主受损/应激增长，并伤害宿主）
- Model-3：`B_L + B_H` 同时存在

### 2.3 环境与 bet-hedging

- 常值资源：用于平衡点与局部稳定（Q3）
- 季节资源：`R(t)=R0(1+A sin(2πt/T))`（展示周期响应）
- 随机环境：两态马尔可夫丰/歉年（配对对照 CRN）
- bet-hedging 指标：准灭绝概率 `P_ext`、宿主越界概率 `P_host`；并补充“恢复时间/恢复成功率”（Q3 韧性）
- 为冲 Z：补充 **尾部风险** `q10_min_N/q10_min_H` 与 **几何平均** `geom_mean_N/geom_mean_H`（避免概率指标饱和）

---

## 3 可直接运行的命令（输出=论文素材）

所有命令默认把结果写入 `MCM_Sim/24A/outputs/temp/run-<timestamp>/`（中间产物目录），核心文件为：

- `runs.csv`（每个策略一行的汇总指标）
- `config.json`（参数快照，含参考稳态与阈值）
- `env_sequences.npz`（随机环境时生成，共同随机数对照用）
- `figures/*.png`（论文图）

已整理好的“四问结果包”（便于直接写论文）：

- `MCM_Sim/24A/docs/讨论/编程/仿真支撑四问/`

常用命令：

- bet-hedging（Model-0，随机环境扫描）：
  - `python MCM_Sim/24A/run_sim.py bet-hedging --years 200 --reps 300`
- seasonal（Model-0，季节资源）：
  - `python MCM_Sim/24A/run_sim.py seasonal --years 80 --R0 2.0 --A 0.5 --T 1.0`
- stability（Model-0，常值局部稳定）：
  - `python MCM_Sim/24A/run_sim.py stability --R0 2.0 --years 400`
- triad-markov（三元系统，随机环境全动力学）：
  - `python MCM_Sim/24A/run_sim.py triad-markov --model 1 --years 200 --reps 300`
- Q4（受益者入侵分析）：
  - 常值阈值：`python MCM_Sim/24A/run_sim.py q4-constant --R0 2.0`
  - 随机入侵：`python MCM_Sim/24A/run_sim.py q4-markov --years 200 --reps 300`

---

## 4 已做完 vs 还没做（按“论文价值”排序）

已做完（可直接写进论文、可复现）：

- Model-0/1/2/3 的 ODE 仿真框架 + 三类环境（常值/季节/随机）
- bet-hedging 扫描输出（含风险权衡图、代表性轨迹图）
- Q3：局部稳定（Jacobian 特征值）+ 随机环境韧性（恢复时间/恢复成功率）
- Q4：常值入侵阈值 `R0` + 随机环境入侵指数 `lambda`
- Q4（三元系统）：补充 `P_B*_outbreak`（峰值爆发概率；更贴近“机会性寄生虫短期暴发”生态含义）

还没做（属于“下一层加分”，不做也能冲 O，但做得好更像 Z）：

- 生命周期调查数据的“半定量落参”更完整：把“3–7 年幼体期/变态窗口/早期高死亡”等映射到参数范围或更结构化阶段模型
- 更强的延迟结构（例如多舱室/Erlang 分布或显式 DDE）来强化“反馈滞后”机制展示
- 更系统的敏感性/不确定性分析（Sobol/PRCC 等）与结论鲁棒性可视化
- 最终版“题目重述”中文润色稿（可直接贴进论文）尚未单独成稿
