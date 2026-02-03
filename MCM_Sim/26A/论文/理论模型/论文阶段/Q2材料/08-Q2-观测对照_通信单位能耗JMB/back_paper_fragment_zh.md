# 插入建议（论文中可删除）

与 `paper_fragment_zh.md` 的区别：本 back_ 版本把“参量估计得到的 e_wifi（J/MB）”以对照线叠加到观测分布上，对应图片为 `back_figure.png`。

# 插入建议

- 建议插入位置：Q2 的观测对照小节中，紧跟 AndroWatts 总功耗量级对照之后；用于解释网络模型的关键参数取值从何而来。
- 用途：把“网络每传 1MB 的能量成本”同时在两套公开数据上对齐：一套用于参量估计（AndroWatts），另一套用于观测分布（SmartphoneMeasurements）。

# 中文正文（可直接粘贴）

## Q2.8(back) 观测对照：单位数据能耗分布与参量估计锚定（J/MB）

网络活动的单位数据能耗（J/MB）会随链路类型、协议栈开销以及尾态（tail states）显著变化，是造成续航“出乎意料地下降”的关键机制之一。为使网络子模型的参数量级可追溯，我们在 SmartphoneMeasurements（Monsoon+iPerf）观测分布的基础上，叠加参量估计得到的 $e_{wifi}$（J/MB）作为对照线：参量估计来源于 AndroWatts 聚合表的能量守恒/回归拟合（见参量估计章节）。

（在此插入图 Q2-8(back)）

图 Q2-8(back)：SmartphoneMeasurements 单位数据能耗（J/MB）观测分布（Wi‑Fi Direct vs 路由器 Wi‑Fi），并叠加参量估计得到的 $e_{wifi}$ 对照线。

该图的作用是提供一个“量级锚定”的证据链：即使 SmartphoneMeasurements 的 $e=\\Delta P/\\dot D$ 来自整机功耗增量（包含 CPU/协议栈/系统调度/尾态等开销），其分布仍与 AndroWatts 的 radio rails 量级估计处于同一数量级；观测长尾则可由尾态与协同开销解释，从而支持在后续仿真中将网络能耗建模为“具有不确定性、且与使用模式耦合”的机制，而非固定可加常数。

