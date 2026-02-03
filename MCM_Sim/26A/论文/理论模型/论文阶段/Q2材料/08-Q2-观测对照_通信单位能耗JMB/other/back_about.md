# back_ 版本说明：参量估计 vs SmartphoneMeasurements（单位数据能耗 J/MB）

本 back_ 版本把参量估计得到的 Wi-Fi `e_per_mb`（J/MB）画成对照线，叠加到 SmartphoneMeasurements 的观测分布上，
用于论文中说明：我们对网络能耗的量级采用“可引用的公开数据”做锚定，而观测长尾可由尾态/交互等机制解释。

## 对应文件

- `../back_figure.png`：paper 版（简洁）
- `back_figure_study.png`：study 版（含解释）
- `back_data.csv`：用于 back_ 图的数据快照（Direct/Router 且 e>0）

## 参量估计对照线来源

- 能量守恒（含尾态能量项）：e=0.150448 J/MB，见 `论文/理论模型/论文阶段/参量估计/03-网络回落曲线/fit_results.csv`
- 功率回归（P_radio vs 吞吐）：e=0.191627 J/MB，见 `论文/理论模型/论文阶段/参量估计/04-吞吐-功耗关系/fit_results.csv`

## 重要口径说明（避免误解）

- SmartphoneMeasurements 的 e=ΔP/吞吐来自 Monsoon 的“整机功耗增量”，可能包含 CPU/协议栈/系统调度/尾态等开销；
- AndroWatts 的参量估计更接近 radio rails 的量级约束（更像网络模块的下界/基准项）；
- 因此两者不必数值完全一致：若观测显著更大，合理解释是“网络活动触发的系统协同开销 + 尾态”。
