# 插入建议

- 建议插入位置：`MCM_Sim/26A/论文/相关文本信息/no8/_0131-1507-论文.md` 的 **4.1.1 Basic Differential Equation Derivation** 中，首次写到 `OCV(SOC)` 与端电压方程附近。
- 用途：把"抽象符号 OCV(SOC)"落到一条可视化曲线，并在同图标注 `V_cut=3.30V`（后续所有 TTE/关机判断的共同门槛）。

# 可直接粘贴到论文的文本（中文）

为闭合电池侧的常微分方程（ODE）系统，我们引入开路电压（OCV）作为荷电状态（SOC）到电压的单调映射。实际中 OCV 通常由实验获得；本文采用分段线性近似以保持单调性，并支持稳定的反求（例如利用静置段电压估计初始 SOC）。

（在此插入图 Q1-01）

图 Q1-01：Model-1 使用的 OCV-SOC 分段线性曲线。红色虚线标记了手机关机逻辑采用的保守放电截止电压 \(V_{\mathrm{cut}}=3.30\text{ V}\)。

借助该映射，端电压可表示为 \(V_{\mathrm{term}}=\mathrm{OCV}(\mathrm{SOC})-\Delta V\)，其中 \(\Delta V\) 汇总瞬时欧姆压降与极化电压。由此我们获得 Q1 所需的"按电压截止"停止准则，并据此给出物理一致的耗尽时间 TTE（Time-to-Empty）定义。

# 可直接粘贴到论文的文本（英文）

To close the battery-side ODE system, we introduce the open-circuit voltage (OCV) as a monotonic mapping from the state of charge (SOC) to voltage. In practice, OCV is obtained experimentally; here we use a piecewise-linear approximation that preserves monotonicity and supports stable inversion (e.g., estimating the initial SOC from a rest voltage).

(Insert Figure Q1-01 here.)

Figure Q1-01: Piecewise-linear OCV-SOC curve used in Model-1. The red dashed line marks the conservative discharge cut-off voltage \(V_{\mathrm{cut}}=3.30\text{ V}\) adopted by the smartphone shutdown logic.

With this mapping, the terminal voltage is computed as \(V_{\mathrm{term}}=\mathrm{OCV}(\mathrm{SOC})-\Delta V\), where \(\Delta V\) aggregates instantaneous ohmic drop and polarization voltages. This provides the voltage-based stopping criterion required by Q1 and enables a physics-consistent definition of time-to-empty (TTE).
