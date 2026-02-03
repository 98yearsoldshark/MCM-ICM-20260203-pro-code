# ECM（1RC / 2RC）等效电路模型资料包

本目录目标：把 **ECM（Thevenin）1RC/2RC** 的“基础算法 + 可运行 demo + 可复刻参考实现”整理成可交接的资料包。

你将得到：
- 基础公式与离散化写法（适配 KF/EKF）
- 1RC/2RC 的最小仿真 demo（脉冲电流 → 端电压响应）
- 第三方参考实现（已下载到 `third_party/`）
- 与 2026 MCM 赛题 A 的对应关系（写论文用）：`MCM26A_PROBLEM_CONTEXT.md`

---

## 1. 模型约定（强烈建议先统一）

**符号与单位**
- 电流 `I`：默认 **I>0 表示放电**（SOC 下降）
- 容量 `Q`：单位 Ah；`Q_coulomb = 3600*Q`
- 参数：`R0, R1, R2` 单位 ohm；`C1, C2` 单位 F
- 采样周期：`Δt` 单位 s

**端电压**
- 1RC：`V = OCV(SOC) - I*R0 - V1`
- 2RC：`V = OCV(SOC) - I*R0 - V1 - V2`

其中 `V1/V2` 为极化支路（`R||C`）的“支路电压/过电势”状态量（不是电容电压的唯一叫法，但在电池文献里很常见）。

---

## 2. 连续模型与离散化（1RC/2RC 通用）

**连续时间**
- `dSOC/dt = - I / (3600*Q)`
- `dVj/dt = -Vj/(Rj*Cj) + I/Cj`，j=1..n

**离散化（零阶保持，推荐写法）**
- `SOC_k = SOC_{k-1} - (Δt/(3600*Q)) * I_{k-1}`
- `Vj_k = a_j * Vj_{k-1} + b_j * I_{k-1}`
  - `a_j = exp(-Δt/(Rj*Cj))`
  - `b_j = Rj * (1 - a_j)`

---

## 3. Demo（可直接跑）

- 脉冲响应仿真（同时跑 1RC 与 2RC，对比端电压响应）：
  - `python3 MCM_Sim/26A/Load-Model/ECM-1RCor2RC/demo/demo_ecm_pulse.py`

输出：
- 屏幕打印关键结果
- 生成图：电流、端电压、SOC、极化电压随时间变化（需要 matplotlib）

补充：直接读取本仓库 26A 的 ECM 配置
```python
from ecm_core import load_1rc_params_from_mcm_json

p1 = load_1rc_params_from_mcm_json("MCM_Sim/26A/src/configs/phone_default_v1_ecm.json")
```

--- 

## 4. 本仓库内已有的 ECM 实现（与本目录的关系）

本项目 **26A** 已经实现了一个 1RC ECM（但输入是“功率闭合”而非“电流输入”）：
- `MCM_Sim/26A/src/mcm26a/battery/model1_ecm.py:1`
- `MCM_Sim/26A/src/configs/phone_default_v1_ecm.json:1`（示例参数与 OCV 曲线）

本目录提供的 demo 更偏“教科书/滤波器友好”的 **I-V 形式**（便于直接写 EKF）。

---

## 5. 参考实现（已下载）

第三方仓库放在 `third_party/`，用于对照/复用：
- `third_party/thevenin/`：NREL 的 Thevenin（nRC）模型实现与文档（Python 包）

更完整的下载方式与版本号：见 `DOWNLOADS.md` 与 `THIRD_PARTY_VERSIONS.md`。
