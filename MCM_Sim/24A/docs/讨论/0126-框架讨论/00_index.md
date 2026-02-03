## 目的

这套文档用于把 2024 MCM Problem A（Resource Availability and Sex Ratios）从“题意”落到“可写可证可复现”的建模框架上，重点覆盖：

- 海七鳃鳗（sea lamprey）性别比例随资源变化（低资源雄性约 78%，高资源雄性约 56%）
- 对生态系统的影响、对七鳃鳗种群的利弊、系统稳定性
- “受益第三方”两种含义同时纳入：  
  - `B_L`：七鳃鳗的寄生虫/病原体（beneficiary-on-lamprey）  
  - `B_H`：宿主鱼的机会性寄生虫/病原体（beneficiary-on-host; 由七鳃鳗造成伤口/应激触发）

文档目标是：从初学者也能跟上的“最小模型”出发，逐步加结构、加可解释性、加可分析性，形成一套能支撑高分论文叙事的模型族（baseline/对照/扩展/鲁棒性）。

## 文件导航

- `01_problem.md`：基于英文原题的题目重述、任务拆解、交付要求
- `02_system_boundary.md`：系统边界、变量与参数表、符号约定（建议直接拷进论文）
- `03_model_family.md`：模型族总览（baseline + 两种受益者 + 二者同时存在），以及性别比例策略对照设计
- `04_equations.md`：核心方程（阶段结构 + 受精限制 + 资源驱动性别比）与可选增强（延迟/季节/随机）
- `05_analysis_plan.md`：如何回答四问：入侵阈值、稳定性、韧性指标、对照实验、敏感性分析
- `06_paper_blueprint.md`：论文写作蓝图（图表清单、叙事结构、结论模板、AI 使用合规）
- `07_beginner_checklist.md`：常见误区与“自查问题”（便于你后续提问与纠错）
- `08_data_notes_0126_life_cycle.md`：从你 0126 调查笔记中提取的可用数值与建模含义（生命周期/食物来源）
- `09_paper_notes_0126_1333.md`：三篇论文（生态实证/综述/建模）学习笔记：可用数据、图像理解与建模启示
- `10_paper_notes_0126_1451.md`：补充一篇“性别比建模”论文笔记（方法可借鉴，生态结论需谨慎）
- `11_bet_hedging_module.md`：随机丰歉年（马尔可夫环境）下的 bet-hedging 主线设计（Z 主亮点）
- `12_synthesis_results.md`：把论文证据与框架方程/指标对齐的“结果化提炼”（方便直接写论文）
- `13_code_status.md`：当前代码实现状态与产物位置（便于后续初学者提问对齐）
- 仿真计划（开始写代码前必读）：`MCM_Sim/24A/docs/讨论/0126-仿真计划/00_index.md`
- 论文预处理阅读入口：`MCM_Sim/24A/docs/论文/0126-13:33/_organized/index.md`
- 论文预处理阅读入口（新增）：`MCM_Sim/24A/docs/论文/0126-14:51/_organized/index.md`

## 使用方式（建议）

1. 先读 `01_problem.md` 和 `02_system_boundary.md`，确保题意与符号统一。
2. 选定论文主线：建议以 `Model-3`（H + lamprey + B_L + B_H）为“展示扩展”，但用 `Model-0/1/2` 做对照与解释。
3. Z 主亮点选定为 bet-hedging：先读 `11_bet_hedging_module.md`，再回到 `04_equations.md`/`05_analysis_plan.md` 把随机环境指标嵌入四问。
4. 按 `06_paper_blueprint.md` 把图表压缩成 25 页内的叙事（随机环境部分建议 1 页解决）。
