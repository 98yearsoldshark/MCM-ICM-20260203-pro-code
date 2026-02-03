# 插入建议

- 建议插入位置：`MCM_Sim/26A/论文/相关文本信息/no10/_0131-1827-论文.md` 的 **4.2.2（Time to First Termination）** 之后，新建一个小节 **“Q2: Time-to-Empty predictions”**，把本图作为该小节的第 1 张总览图。
- 用途：直接回答赛题 Q2 的 “不同初始电量 × 不同场景下的 TTE”，并为后续“不确定性/驱动因素/对照验证”提供总入口。

# 可直接粘贴到论文的文本（中文）

## Q2.1 不同初始电量与使用场景下的耗尽时间（TTE）

基于第 4 节建立的连续时间 SOC 模型，我们在若干具有代表性的使用场景以及多个初始电量水平下计算耗尽时间 TTE（Time-to-Empty）。本文将 TTE 定义为系统首次触发关机边界的时间（见第 4.2.2 节）：（i）欠压截止 $V_{term}(t)\le V_{cut}$，（ii）能量耗尽 $SOC(t)\le SOC_{min}$，或（iii）供电不可行 $\Delta(t)<0$。

为同时反映参数不确定性与用户/后台行为的随机性，我们采用蒙特卡洛过程：对每个（场景，$SOC_0$）抽样关键不确定参数（例如 $V_{cut}$、$\eta_{PMIC}$、各组件功耗缩放因子等），并模拟后台随机唤醒。图 Q2-1 给出了每个单元格的 TTE 均值（单位：小时）。

（在此插入图 Q2-1）

图 Q2-1：不同场景 × 初始电量下的平均耗尽时间 TTE（小时）。

图 Q2-1 呈现两个清晰规律。其一，不同场景会带来数量级差异：当 $SOC_0=1.0$ 时，模型预测待机/轻后台约 **61.5 h**，标准一天的混合使用约 **36.2 h**，视频流约 **9.7 h**，导航（GPS+地图数据）约 **7.2 h**，而高 CPU/GPU 负载的游戏仅约 **3.4 h**。其二，初始电量降低会近似按比例缩短 TTE，但并非严格线性；原因在于关机事件通常由端电压动态触发（欠压提前关机），而不仅由 SOC 线性耗尽决定。

（这是讲解内容，论文中可删除）  
这张图是 Q2 的“主答案图”：它同时满足“多场景×多 SOC0 的 TTE 输出”，且每个格子来自 Monte Carlo 的均值，因此天然衔接后续“不确定性量化”（图 03/04）与“drivers 识别”（图 05/06）。

# 可直接粘贴到论文的文本（英文）

## Q2.1 Time-to-Empty across scenarios and initial charge levels

Using the continuous-time SOC model developed in Section 4, we compute the **time-to-empty (TTE)** under a set of representative usage scenarios and multiple initial charge levels. Here, TTE is defined as the **first termination time** when any shutdown boundary is reached (Section 4.2.2): (i) undervoltage cutoff $V_{term}(t)\le V_{cut}$, (ii) energy depletion $SOC(t)\le SOC_{min}$, or (iii) power infeasibility $\Delta(t)<0$.

To reflect both parameter uncertainty and the inherent randomness of user/background activities, we use a Monte Carlo procedure: for each (scenario, $SOC_0$), we sample key uncertain parameters (e.g., $V_{cut}$, $\eta_{PMIC}$, scaling factors of component power) and simulate stochastic background wake-ups. Figure Q2-1 reports the **mean** TTE (hours) for each cell.

(Insert Figure Q2-1 here.)

Figure Q2-1: Mean TTE (hours) for different scenarios and initial charge levels.

Figure Q2-1 highlights two dominant patterns. First, usage scenarios create orders-of-magnitude differences: under full charge ($SOC_0=1.0$), the model predicts about **61.5 h** for standby/light background, **36.2 h** for a mixed “typical day”, **9.7 h** for video streaming, **7.2 h** for navigation (GPS + maps), and only **3.4 h** for gaming (high CPU/GPU). Second, decreasing initial charge shortens TTE approximately proportionally, but deviations from perfect linear scaling emerge because the shutdown event is triggered by voltage dynamics rather than SOC alone.
