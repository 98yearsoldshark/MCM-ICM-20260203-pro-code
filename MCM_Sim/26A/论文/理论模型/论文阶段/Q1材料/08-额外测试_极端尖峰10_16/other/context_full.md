# 插入建议

- 建议插入位置：可放在 Q1 的验证小节末尾作为 *stress test*，或放入附录（Appendix）作为补充验证。
- 用途：展示在"极端尖峰"（更深的瞬态欠压）情况下，模型仍能保持合理的回弹/恢复形态与 TTE 预测。

# 可直接粘贴到论文的文本（中文）

作为额外压力测试，我们在 CALCE 的"Initial capacity"实验（10_16）上评估 Model-1。该数据包含更深的瞬态欠压尖峰，对模型能否同时刻画"进入尖峰"、"瞬时回弹"以及随后向下一平台的松弛恢复提出了更高要求。

（在此插入图 Q1-08）

图 Q1-08：CALCE 10_16（极端尖峰）额外验证。蓝线为观测端电压，红线为 Model-1 预测（2RC ECM）。灰色水平虚线为 \(V_{\mathrm{cut}}=3.30\text{ V}\)；竖虚线给出以首次跌破 \(V_{\mathrm{cut}}\) 定义的观测/预测耗尽时间（TTE）。

该测试中模型整体 RMSE 为 25.44 mV（MAE 18.54 mV），TTE 误差为 -90.9 s（-0.459%）。残差主要集中在最极端瞬态附近，提示后续可通过引入更强的"电流相关极化/门控"机制进一步降低尖峰段误差；但整体轨迹与耗尽时刻已能被连续时间机理模型稳定复现。

可选（附录）：`figure_zoom.png` 为最深尖峰附近局部放大。

# 可直接粘贴到论文的文本（英文）

As an additional stress test, we evaluate Model-1 on a CALCE "Initial capacity" experiment (10_16) that contains a much deeper transient under-voltage spike. This case challenges the model's ability to represent the spike entry, the immediate rebound, and the subsequent relaxation toward the next plateau.

(Insert Figure Q1-08 here.)

Figure Q1-08: Additional validation on CALCE 10_16 (extreme spike). Blue: measured terminal voltage; red: Model-1 prediction (2RC ECM). The dashed line is \(V_{\mathrm{cut}}=3.30\text{ V}\); vertical dotted lines indicate observed/predicted TTE defined by the first crossing of \(V_{\mathrm{cut}}\).

The model achieves an overall RMSE of 25.44 mV (MAE 18.54 mV) and a TTE error of −90.9 s (−0.459%). Most residuals are concentrated around the most extreme transient, suggesting that further improvements could be obtained by introducing a current-dependent polarization model; nevertheless, the proposed continuous-time mechanism model preserves the overall trajectory and depletion timing.

Optional (appendix): `figure_zoom.png` provides a local zoom around the deepest spike.
