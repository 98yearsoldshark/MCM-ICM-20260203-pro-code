# Q1 专用整理：ECM（1RC/2RC）连续时间模型最小演示

本文件夹用于服务题面 **Q1 / Requirement 1：Continuous-Time Model**：

- 给出一套**可直接写进论文**的连续时间电池电学模型（SOC ODE + 极化支路 ODE + 端电压方程）。
- 提供一个最小 demo，用“脉冲电流 → 电压响应/松弛”直观说明 **1RC vs 2RC（两个时间常数）**。

注意：这里是“电池侧（电芯层）”的连续时间模型演示；手机侧负载 `P(t)`/`I(t)` 如何构造见 `Load-Model/Battery-Historian/0for_Q1/` 与 `src/mcm26a/scenarios/`。

---

## 你应该引用/阅读哪些原始文件（推荐顺序）

1) 模型与符号约定（写论文用）  
`MCM_Sim/26A/Load-Model/ECM-1RCor2RC/README.md`

2) 与赛题 A 的对应关系（写作上下文）  
`MCM_Sim/26A/Load-Model/ECM-1RCor2RC/MCM26A_PROBLEM_CONTEXT.md`

3) 可运行 demo（1RC/2RC 脉冲响应）  
`MCM_Sim/26A/Load-Model/ECM-1RCor2RC/demo/demo_ecm_pulse.py`

---

## 一键运行（推荐用本文件夹的入口）

下面脚本会调用上面的 demo，并把图保存到本文件夹 `outputs/`：

```bash
python3 MCM_Sim/26A/Load-Model/ECM-1RCor2RC/0for_Q1/src/run_demo_ecm_pulse.py
```

输出：
- `MCM_Sim/26A/Load-Model/ECM-1RCor2RC/0for_Q1/outputs/ecm_pulse_demo.png`

---

## 这份 demo 在 Q1 里回答了什么

- **连续时间**：`SOC` 与极化电压 `V1/V2` 由 ODE 描述。
- **机理解释**：端电压由 `OCV(SOC)` 与 `I·R0`（瞬时压降）和 `V1/V2`（松弛/恢复）共同决定。
- **为什么需要 2RC**：单一时间常数往往只能拟合“快松弛”或“慢松弛”其一；2RC 能同时表达两种尺度。

