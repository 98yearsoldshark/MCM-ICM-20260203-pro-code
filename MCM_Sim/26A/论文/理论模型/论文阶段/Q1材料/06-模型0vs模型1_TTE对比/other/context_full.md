# 插入建议

- 建议插入位置：`MCM_Sim/26A/论文/相关文本信息/no8/_0131-1507-论文.md` 的 **4.3 The Solution of Model 1** 末尾（或在第 8 节 Model Evaluation 中作为对照图）。
- 用途：用一张图说明"从 Model-0（SOC 阈值）到 Model-1（截止电压 + 电池机理）"会如何系统性改变 TTE 结论。

# 可直接粘贴到论文的文本（中文）

为剥离并量化"电池端电化学机理"对续航估计的影响，我们将基线模型（Model-0）与机理模型（Model-1）进行对照。Model-0 在固定 SOC 阈值处终止放电，默认所有电量都可被利用；而 Model-1 在端电压达到截止电压 \(V_{\mathrm{cut}}\) 时终止，并显式考虑欧姆压降与极化压降，因此在高负载下可能发生提前关机。

（在此插入图 Q1-06）

图 Q1-06：Model-0（SOC 阈值）与 Model-1（截止电压）的耗尽时间 TTE 对比。由于高负载会使端电压更快跌破 \(V_{\mathrm{cut}}\)，Model-1 在高负载场景下通常预测更短的可用续航。

该对照把"物理一致的停止准则"与"用户可感知续航"建立了可解释联系：两模型之间的差值可视为欠压导致的"表观损失"（并非电量真的耗尽）。

# 可直接粘贴到论文的文本（英文）

To isolate the impact of battery-side electrochemical mechanisms, we compare a baseline model (Model-0) that terminates discharge at a fixed SOC threshold with our mechanistic model (Model-1) that terminates at a terminal-voltage cut-off \(V_{\mathrm{cut}}\). While Model-0 treats all charge as "accessible," Model-1 accounts for internal voltage drops that can cause early shutdown under high load.

(Insert Figure Q1-06 here.)

Figure Q1-06: Time-to-empty (TTE) comparison between Model-0 (SOC threshold) and Model-1 (voltage cut-off). Model-1 predicts shorter endurance under high-load scenarios because the terminal voltage reaches \(V_{\mathrm{cut}}\) before the battery is truly depleted.

This comparison provides an interpretable link between a physics-based stopping rule and user-facing endurance: the gap between the two models quantifies the amount of "apparent loss" caused by under-voltage.
