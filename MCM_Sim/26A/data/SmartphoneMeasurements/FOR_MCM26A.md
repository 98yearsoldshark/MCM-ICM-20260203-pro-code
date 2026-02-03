# 本数据目录如何服务 2026 MCM Problem A（智能手机电池耗电建模）

赛题原文/译文位置（本仓库）：`MCM_Sim/26A/论文/赛题/`。

赛题 A 的核心要求是：建立一个 **连续时间（continuous-time）SOC(t)** 模型，并在不同使用场景下预测 **TTE（Time-to-Empty）**；允许使用公开数据做参数估计与验证，但强调“数据是支撑而非替代”，不能只做离散曲线拟合/黑盒回归。

## 1. 本目录扮演什么角色（定位）

本目录提供的是“手机侧”的补充数据：

- **用户级使用强度统计**（`user_behavior_dataset.csv`）：帮助你构造“轻/中/重度用户”的日均使用量范围，用于场景设定、敏感性分析与建议（而非直接提供 SOC(t) 轨迹）。
- **通信功耗实测**（`SmartphoneMeasurements.zip`）：提供 WiFi / WiFi Direct / Bluetooth / LTE 的功耗与吞吐对照，帮助你把 `P_network(t)` 的量级设得合理，并支持论文中的“哪些活动最耗电”论证。

它们通常不替代本仓库面向赛题 A 专门整理的主数据（AndroWatts + 电池老化拼接表）：

- `MCM_Sim/26A/data/数据集/`（主表与变量字典）
- `MCM_Sim/26A/data/open_data/`（AndroWatts：手机侧功耗/状态测量证据）

## 2. 如何用 `user_behavior_dataset.csv` 支撑建模/写作

数据是“按天汇总”的用户级统计（min/day、hours/day、mAh/day、MB/day），建议用法：

1) **构造情景参数范围**
   - 例如用 `Screen On Time (hours/day)` 的分位数定义轻/中/重度用户的屏幕时长范围。
   - 用 `Data Usage (MB/day)` 为网络活动强度提供一个量级范围（并在模型里映射到 WiFi/LTE 的占比假设）。

2) **把“日耗电 mAh/day”映射为平均电流（仅用于量级检查）**
   - `I_avg ≈ (Battery Drain mAh/day) / 24h`
   - 注意：这只是平均量级；赛题需要的是 `I(t)` 或 `P(t)` 随时间变化的连续模型，仍需你构造随时间变化的使用模式（例如“早晚高峰 + 白天间歇”的 piecewise 函数）。

3) **敏感性分析与建议**
   - 你可以把“屏幕时长下降 1h/day”“流量下降 20%”作为扰动，观察 TTE 的相对变化，并形成可解释的建议。

## 3. 如何用 `SmartphoneMeasurements.zip` 支撑建模/写作

zip 内含上游仓库 `SmartphoneMeasurements-main/README.md`（可用 `unzip -p SmartphoneMeasurements.zip SmartphoneMeasurements-main/README.md` 查看）。

建议用法：

1) **增量功耗（Delta power）**
   - 以 `Baseline`（通信全部关闭）为参考，计算 WiFi/LTE/Bluetooth 等实验的 `P - P_baseline`，得到“通信活动带来的额外功耗”量级。

2) **把网络吞吐与功耗联系起来**
   - iPerf 目录提供吞吐日志；Monsoon 目录提供功耗曲线。
   - 你可以在论文里展示：“同等吞吐下，WiFi vs WiFi Direct vs LTE 的功耗差异”，用于解释“某些网络模式更耗电”的驱动因素。

3) **构造 `P_network(t)` 的分段函数**
   - 例如将网络活动设为若干段（下载/上传/空闲），每段使用该数据集给出的功耗均值或分布。

注意：
- 这是特定机型 + 特定实验条件下的测量；写作时应明确其外推限制。
- zip 内未包含 LICENSE 文件；使用前请回到上游仓库确认许可条款并在论文中引用。

