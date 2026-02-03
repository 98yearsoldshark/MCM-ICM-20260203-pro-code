# 核心算法快速导览（建议只看这些）

你如果只想最快理解“模型怎么工作的”，可以只看下面这些文件；其余如 `viz/`（画图）与 `scripts/`（命令行入口）可先忽略。

## 总体规则（强制约定）

- **核心算法模块禁止依赖画图/报告**：`mcm26a/{battery,power,scenarios,sim,analysis,uq}/` 内不要 `import matplotlib/pandas`。
- **画图永远放在 `mcm26a/viz/`**，只允许 `viz -> (analysis/sim/...)` 单向依赖；核心算法不反向依赖 `viz`。
- **I/O 与编排放在 `src/scripts/`**：脚本负责读配置、跑仿真、打印/保存结果；物理/数学公式不要写进脚本。
- **单位显式写进变量名**（避免混用）：
  - 时间：`*_s`, `*_h`
  - 功率：`*_W`
  - 能量：`*_Wh`
  - 电压/电流：`*_V`, `*_A`
  - 温度：`*_C`
  - 电阻：`*_ohm`
- **每个模型都有“参数 dataclass + 状态 dataclass + 仿真入口 + 结果 dataclass”**，并保持命名一致：
  - `simulate_modelX_*`
  - `SimResultX`
  - 可选 `TraceResultX`（返回轨迹数组，不做画图）

## 建议阅读顺序（从浅到深）

### Model-0（能量守恒，先跑通）

1. `MCM_Sim/26A/src/mcm26a/power/model0.py`：场景输入 -> 组件功耗分解 `PowerBreakdown`
2. `MCM_Sim/26A/src/mcm26a/battery/model0.py`：电池名义能量参数（Wh + soc_min）
3. `MCM_Sim/26A/src/mcm26a/sim/model0.py`：能量守恒算 TTE（支持 repeat 场景整周期加速）

### Model-1（等效电路 ECM + 截止电压）

1. `MCM_Sim/26A/src/mcm26a/battery/model1_ecm.py`：ECM 方程（功率闭合解二次方程得到电流/端电压）
2. `MCM_Sim/26A/src/mcm26a/sim/model1.py`：RK4 积分 + cutoff 事件终止 + TTE

补充（Z 奖向“可校准机理”增强）：
- Model-1/2/3 现在都支持 **SOC 相关内阻曲线**（可选）：
  - `battery.ecm.R0_curve`：R0(SOC) 分段线性
  - `battery.ecm.R1_curve`：R1(SOC) 分段线性
  - 若不提供，则退化为常数 `R0_ohm/R1_ohm`（向后兼容）
- 该增强用于解释“低 SOC 区压降/松弛更强”的结构性误差，并为后续多数据校准留接口。

### Model-2（热-电耦合：温度影响内阻/有效容量）

1. `MCM_Sim/26A/src/mcm26a/battery/model2_thermal.py`：集总热模型 + 温度系数（R0/R1/Q_eff 随温度变化）
2. `MCM_Sim/26A/src/mcm26a/sim/model2.py`：在 Model-1 基础上加入温度状态并积分

### Model-3（老化：容量衰减 + 内阻增长）

1. `MCM_Sim/26A/src/mcm26a/battery/model3_aging.py`：老化状态 + 温度加速（Q10）+ per-Ah/per-day 老化骨架
2. `MCM_Sim/26A/src/mcm26a/sim/model3.py`：在 Model-2 基础上加入老化状态并积分；输出 cap_loss/r_growth

## 与画图/论文输出有关的模块（可忽略）

- `MCM_Sim/26A/src/mcm26a/viz/`：所有论文版/学习版图像生成
- `MCM_Sim/26A/src/out_plots/`：自动生成图像输出目录
