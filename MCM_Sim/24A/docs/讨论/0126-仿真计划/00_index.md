## 目的

本目录用于把“论文可写的模型框架”落到“可复现的仿真实验计划”，先把：

- 要跑哪些模型/策略
- 环境随机过程如何生成
- 指标怎么定义/怎么统计
- 输出文件与命名约定

在写代码前定清楚，确保后续仿真整洁、不会边写边改导致返工。

主参考（建模框架）：

- `MCM_Sim/24A/docs/讨论/0126-框架讨论/04_equations.md`
- `MCM_Sim/24A/docs/讨论/0126-框架讨论/05_analysis_plan.md`
- `MCM_Sim/24A/docs/讨论/0126-框架讨论/11_bet_hedging_module.md`
- `MCM_Sim/24A/docs/讨论/0126-框架讨论/12_synthesis_results.md`

文件导航：

- `01_仿真规格书.md`：仿真范围、数值推进方式、实验矩阵、指标与输出规范（写代码时按它实现）

快速运行入口（代码）：

- `MCM_Sim/24A/run_sim.py`：仿真主入口（统一输出到 `MCM_Sim/24A/outputs/`）
  - 默认输出到 `MCM_Sim/24A/outputs/temp/`（中间产物）；如需“最终版”结果，建议显式 `--out-dir MCM_Sim/24A/outputs/<你的目录名>`
  - bet-hedging（Model-0，随机环境）：`python MCM_Sim/24A/run_sim.py bet-hedging --years 200 --reps 300`
  - seasonal（Model-0，季节资源）：`python MCM_Sim/24A/run_sim.py seasonal --years 80 --R0 2.0 --A 0.5 --T 1.0`
  - stability（Model-0，常值局部稳定）：`python MCM_Sim/24A/run_sim.py stability --R0 2.0 --years 400`
  - triad-markov（三元系统 Model-1/2/3，随机环境）：`python MCM_Sim/24A/run_sim.py triad-markov --model 1 --years 200 --reps 300`
  - Q4（受益者入侵分析）：
    - 常值阈值：`python MCM_Sim/24A/run_sim.py q4-constant --R0 2.0`
    - 随机入侵：`python MCM_Sim/24A/run_sim.py q4-markov --years 200 --reps 300`

辅助脚本：

- `MCM_Sim/24A/scripts/smoke_test.py`：最小烟雾测试（验证入口/输出是否跑通）
- `MCM_Sim/24A/scripts/make_figures.py`：从旧 `runs.csv` 重绘论文级图片（不重跑仿真）
