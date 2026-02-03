# 插入建议

- 建议插入位置：`MCM_Sim/26A/论文/相关文本信息/no8/_0131-1507-论文.md` 的 **4.3 The Solution of Model 1**（给出求解流程后），用于展示"模型能输出什么"。
- 用途：展示 Model-1 在一个具体场景下的连续时间轨迹（SOC、端电压、功率上限），让 Q1 的 ODE 输出更直观。

# 可直接粘贴到论文的文本（中文）

在完成电池侧参数化后，我们对一个代表性的手机负载场景进行连续时间仿真，展示状态变量随时间的演化。图 Q1-05 给出了"游戏"场景的典型轨迹：随着能量被消耗，SOC 单调下降；端电压同时受 SOC 下降与极化压降影响而逐步降低；当 \(V_{\mathrm{term}}\) 首次达到截止电压 \(V_{\mathrm{cut}}\) 时，系统判定关机并得到对应的耗尽时间（TTE）。

（在此插入图 Q1-05）

图 Q1-05：高 CPU/GPU 负载（游戏）下的连续时间轨迹示例。自上而下分别为：SOC(t)、端电压 \(V_{\mathrm{term}}(t)\)（含截止电压参考线）、以及可用功率预算 \(P_{\max}(t)\)（headroom 约束）。该耦合演化提供了基于机理的 TTE 估计。

该轨迹视角把微分方程输出与用户可感知的续航结果直接关联；在 Q2 中我们将复用类似图形用于解释哪些因素驱动快速耗电。

# 可直接粘贴到论文的文本（英文）

After parameterizing the battery-side model, we simulate the continuous-time evolution of the state variables under a representative smartphone workload. Figure Q1-05 illustrates a "Gaming" trace: SOC decreases as energy is consumed, the terminal voltage gradually drops due to both SOC decline and polarization, and the device shuts down once \(V_{\mathrm{term}}\) reaches the cut-off voltage \(V_{\mathrm{cut}}\).

(Insert Figure Q1-05 here.)

Figure Q1-05: Example continuous-time trajectory under a high CPU/GPU workload (gaming). From top to bottom: SOC(t), terminal voltage \(V_{\mathrm{term}}(t)\) with the cut-off line, and the admissible power budget \(P_{\max}(t)\) (headroom constraint). The coupled evolution provides a mechanistic time-to-empty (TTE) estimate.

This trajectory view connects the differential equations to user-visible outcomes and will be reused in Q2 to explain which factors drive rapid battery drain.
