# Open-S（开源工具与对照实验台）

本目录用于存放/交接 26A 项目中调研与集成的开源电池建模工具，定位是：
- 为赛题 A 的“**连续时间 + 机理**”要求提供更强的物理对照与论证材料；
- 作为主模型（通常更轻量，如 ECM/能量模型）的 **benchmark / sanity-check**；
- 提供可复现实验脚本（生成图与 CSV），用于论文里的对照图、敏感性示例与趋势验证。

赛题原文位置：`MCM_Sim/26A/论文/赛题/A英文纯文本.md`

## 1. 赛题 A 合规性对照（哪些技术满足“连续时间 + 机理”）

赛题 A 明确要求模型必须：
- 有显式连续时间描述（ODE/ODE system），输出 `SOC(t)`；
- 有清晰物理/机理依据；不能用离散拟合/黑盒回归替代模型本体；
- 给出 TTE、敏感性与建议。

本目录包含的工具对齐情况：
- `PyBaMM/`：满足（推荐使用）
  - PyBaMM 提供标准锂电机理模型（如 SPM/DFN），本质是连续时间微分方程（组），可输出电压/电流/容量消耗并自然定义截止电压事件下的 TTE。
  - 更适合做“机理对照 + 增强可信度”，不建议作为你们全流程唯一仿真器（计算量与参数标定成本更高）。
- `LIONSIMBA/`：理论上满足，但本项目不采用
  - 工具偏 MATLAB/Octave 生态；在当前工程约束下集成成本高，因此仅保留调研记录。

## 2. 目录结构

- `PyBaMM/`：PyBaMM 交接包（安装、demo、功耗映射、桥接函数）
- `LIONSIMBA/`：调研记录（为何不采用）

## 3. PyBaMM 推荐用法（怎么用才“加分且不翻车”）

PyBaMM 在 26A 的最佳定位是：**机理基准/对照实验台**。常见写法：

1) 你们的主模型：用更轻量的连续时间模型跑全流程（场景 → 功耗 → SOC/TTE → 策略对比）。
2) PyBaMM 对照：在相同的功耗/放电协议下，用 PyBaMM 输出电压与 TTE，对比趋势与非线性来源（例如内阻与极化导致的截止提前）。
3) 论文论证：用 PyBaMM 结果支撑“为何主模型需要/不需要加入某项机理修正”，并用于敏感性讨论（如截止电压、温度、功率强度）。

你可以直接复用的对照产物（位于 `PyBaMM/outputs/`）：
- `demo_04_tte_vs_power`：扫功率得到 TTE 曲线（用于“边际收益递减/非线性”讨论）
- `demo_03_phone_like_power_profile`：类手机功耗剖面的 V/I/P 响应（用于解释“高负载更早触发关机阈值”）

## 4. 快速开始（PyBaMM）

推荐 Python 3.11（避免版本约束导致安装失败）：

```bash
cd MCM_Sim/26A/Open-S/PyBaMM
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demos/run_all.py
```

如果你使用 conda（可选）：

```bash
cd MCM_Sim/26A/Open-S/PyBaMM
conda env create -f environment.yml
conda activate mcm26a-pybamm
python demos/run_all.py
```

正常情况下会生成：
- `outputs/demo_00_env_check.txt`
- `outputs/demo_01_spm_basic.{png,csv}`
- `outputs/demo_02_cccv_cycle.{png,csv}`
- `outputs/demo_03_phone_like_power_profile.{png,csv}`
- `outputs/demo_04_tte_vs_power.{png,csv}`

## 5. 把“手机功耗 P(t)”接入 PyBaMM（最稳妥的接口方式）

手机侧最自然的输入通常是功耗 `P(t)`（W）。PyBaMM 支持功率控制 step，因此推荐做法是：

1) 把 `P(t)` 离散成分段常数：`(P_i, dt_i)`
2) 生成 `Experiment` step：`Discharge at {P_i} W for {dt_i} seconds`
3) 为了计算 TTE：末尾追加 `Discharge at {P_last} W until {V_cut} V`

本目录已提供桥接实现（轻量接口）：
- `MCM_Sim/26A/Open-S/PyBaMM/pybamm_bridge.py`
- 映射说明：`MCM_Sim/26A/Open-S/PyBaMM/docs/03_mcm26a_mapping.md`

## 6. 论文写作与合规提醒

- PyBaMM/参数集不等于“手机电池真实参数”。用于趋势解释/机理对照是合理的；若要高精度绝对预测，需要真实电芯参数并标定。
- 论文需要对 PyBaMM 与参数集做引用（参考文献中写清楚 PyBaMM 项目与所用参数集/论文来源）。
- 不要把“demo 拟合出的曲线”当成模型本体；主模型仍应显式写出连续时间方程与假设，并据此给出 TTE、敏感性与建议。

