# 插入建议

- 建议插入位置：与 `02-模型1验证_12_09预测vs观测` 同一小节（建议放在 Figure Q1-02 之后，作为第二个独立验证案例）。
- 用途：展示在另一条 Incremental OCV 实验中，模型对"更极端尖峰/更复杂回弹"的解释能力，并给出定量误差。

# 可直接粘贴到论文的文本（中文）

为进一步检验鲁棒性，我们将同一套 2RC ECM 结构应用于同一电芯的另一条 Incremental OCV 实验（12_2）。该实验在接近耗尽边界处包含更极端的欠压尖峰，因此对"进入尖峰"与"尖峰回弹"的动力学是一种更严格的压力测试。

（在此插入图 Q1-03）

图 Q1-03：CALCE Incremental OCV 验证（12_2）。蓝线为观测端电压，红线为 Model-1 预测（2RC ECM）。灰色水平虚线为截止电压 \(V_{\mathrm{cut}}=3.30\text{ V}\)；竖虚线给出以首次跌破 \(V_{\mathrm{cut}}\) 定义的观测/预测耗尽时间（TTE）。

尽管尖峰更尖锐，模型仍能匹配各平台电压及其恢复趋势，整体 RMSE 为 12.05 mV（MAE 8.06 mV），TTE 误差为 -103.1 s（-0.162%）。这表明在接近截止电压的工作区间，电压对内部压降高度敏感，多时间尺度极化状态是必要的建模要素。

可选（附录）：`figure_zoom.png` 为最深尖峰附近局部放大，用于检查进入/回弹曲率是否合理。

# 可直接粘贴到论文的文本（英文）

To further test robustness, we evaluate the same 2RC ECM structure on another Incremental OCV run from the same cell (12_2). This run contains a more extreme under-voltage spike near the depletion boundary, making it a stringent stress test for spike entry and rebound dynamics.

(Insert Figure Q1-03 here.)

Figure Q1-03: CALCE Incremental OCV validation (12_2). Blue: measured terminal voltage; red: Model-1 prediction (2RC ECM). The horizontal dashed line is \(V_{\mathrm{cut}}=3.30\text{ V}\); the vertical dotted lines indicate the observed and predicted TTE defined by the first crossing of \(V_{\mathrm{cut}}\).

Despite the sharper spike, the model still matches the plateau levels and the recovery trend, achieving an overall RMSE of 12.05 mV (MAE 8.06 mV) and a TTE error of −103.1 s (−0.162%). This confirms that multi-time-scale polarization states are essential near the cut-off regime, where voltage is highly sensitive to internal drops.

Optional (appendix): `figure_zoom.png` provides a local zoom around the deepest spike to inspect the curvature of entry/rebound.
