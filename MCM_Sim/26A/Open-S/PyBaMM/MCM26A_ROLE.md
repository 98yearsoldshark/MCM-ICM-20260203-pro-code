# MCM 2026A（智能手机电池耗电建模）中，本目录的作用

赛题原文/译文见：
- `MCM_Sim/26A/论文/赛题/A英文纯文本.md`
- `MCM_Sim/26A/论文/赛题/A中文纯文本.md`

题目核心要求是：给出一个**连续时间（continuous-time）**、具备**明确机理**的电池模型，用于在不同使用条件下预测 **SOC(t)** 与 **TTE（Time-to-Empty）**，并做敏感性分析与可执行建议。

本目录 `MCM_Sim/26A/Open-S/PyBaMM/` 的定位是：用开源电池机理建模框架 **PyBaMM** 作为“机理基准/对照实验台”，帮助主模型更可信、更好写、更好验证。

## 1. 为什么需要 PyBaMM（对齐赛题的“连续时间 + 机理”）

在 `MCM_Sim/26A/src/` 我们会优先实现更轻量的连续时间模型（Model-0/1/2/3），以便：
- 快速跑通“场景 -> 功耗 -> SOC -> TTE -> 策略对比”全流程；
- 能做大规模参数扫描/不确定性传播；
- 论文叙事更清晰（逐步加复杂度）。

但赛题也强调：不能只做离散拟合/黑盒回归，必须有连续时间机理支撑。

PyBaMM 的价值在于：
- 它实现了标准的锂离子电池机理模型（如 SPM/DFN），本质是连续时间微分方程（组）；
- 给定负载协议（电流 A 或功率 W），能输出电压/电流/容量消耗等时间序列，并自动处理“截止电压关机”事件；
- 可以作为我们简化模型（Model-0/1/2）的**物理对照**：用来验证趋势、解释非线性、支撑论文论证。

一句话：**主模型负责“快 + 可解释 + 能做策略”，PyBaMM 负责“机理对照 + 增强可信度”。**

## 2. 本目录提供了什么（交接给下一个工作者）

- `README.md`：安装/运行入口
- `docs/`：概念、核心 API、Experiment 写法速查、以及“功耗(W) -> Experiment”的映射思路
- `demos/`：可直接运行的 demo（生成图 + CSV，产物在 `outputs/`）
- `pybamm_bridge.py`：将“分段功率曲线（W）”快速转成 PyBaMM Experiment，并一键返回 TTE 的轻量接口

建议接手者先跑：
```bash
cd MCM_Sim/26A/Open-S/PyBaMM
python demos/run_all.py
```

## 3. 如何在论文中用 PyBaMM（建议写法）

### 3.1 作为“机理基准”支撑我们的连续时间模型

在论文里，你可以这样交代：
- 我们提出的主模型是连续时间 SOC 动力学（并逐步加入电压截止/温度/老化等效应）；
- 为了避免“只靠经验拟合”，我们使用 PyBaMM（SPM，参数集 Chen2020）作为机理对照；
- 对照结果展示：在相同功率负载下，电压会因内阻与浓差极化出现非线性下降，从而导致 TTE 对功率的响应并非严格线性；
- 因此，我们的简化模型（例如 ECM 或修正有效能量）在某些功率区间更合理，并据此给出策略建议。

可直接复用的图：
- `outputs/demo_04_tte_vs_power.png`：TTE 随功率变化曲线（可用于“边际收益递减”的讨论）
- `outputs/demo_03_phone_like_power_profile.png`：类手机功耗剖面的 V/I/P 响应（可用于解释“高负载导致更早触发关机阈值”）

### 3.2 作为“生成可解释数据”的工具（帮你做验证/敏感性）

赛题要求要做敏感性与假设讨论。PyBaMM 可用来快速做“可解释的对照实验”，例如：
- 扫描功率（W）/负载模式，得到 TTE 的变化范围；
- 改变截止电压阈值（例如 3.0~3.3V）观察关机时间变化；
- 改变环境温度（参数键常见为 `Ambient temperature [K]`）观察 TTE 变化（如果你启用/升级热相关模型）。

## 4. 与 26A 主代码的接口建议（功耗 -> PyBaMM）

手机侧最自然的是功耗 `P(t)`（W）。PyBaMM 支持功率控制 step，因此最稳妥的接法是：

1) 把功耗曲线离散成分段常数：`(P_i, dt_i)`  
2) 生成 `Experiment`：`Discharge at {P_i} W for {dt_i} seconds`  
3) 想要自动算 TTE：在末尾追加 `Discharge at {P_last} W until {V_cut} V`

本目录已提供可复用实现：`pybamm_bridge.py`，示例（概念）：

```python
import sys
from pathlib import Path

# 让 Python 找到本目录（更推荐后续把 pybamm_bridge.py 复制/迁移到 src/ 包内）
sys.path.insert(0, str(Path("MCM_Sim/26A/Open-S/PyBaMM").resolve()))

import pybamm_bridge

segments = [
    ("Idle", 1.0, 20 * 60),
    ("Video", 4.0, 15 * 60),
]
tte_h = pybamm_bridge.simulate_tte_hours_from_power_segments(
    segments,
    final_power_w=2.5,   # 跑完分段后，以 2.5W 持续放到截止电压
    cutoff_v=3.2,
)
print(tte_h)
```

## 5. 边界与注意事项（避免误用）

- **参数不等于手机电池真实参数**：demo 使用的 `Chen2020` 是“代表性电芯参数集”。用于趋势/机理解释是合理的；要做高精度绝对预测，需要真实电芯参数并标定。
- **计算量**：优先用 `SPM`（本目录默认）。`DFN` 更精细但更慢，建议只做少量对照图。
- **论文合规**：使用 PyBaMM/参数集要在参考文献中引用来源（PyBaMM 项目与参数集对应论文）。

## 6. 完整性检查（你可以用来确认“没缺东西”）

本目录可用以下命令做“自检”：

```bash
cd MCM_Sim/26A/Open-S/PyBaMM
python demos/run_all.py
```

正常情况下会生成：
- `outputs/demo_00_env_check.txt`
- `outputs/demo_01_spm_basic.{png,csv}`
- `outputs/demo_02_cccv_cycle.{png,csv}`
- `outputs/demo_03_phone_like_power_profile.{png,csv}`
- `outputs/demo_04_tte_vs_power.{png,csv}`

