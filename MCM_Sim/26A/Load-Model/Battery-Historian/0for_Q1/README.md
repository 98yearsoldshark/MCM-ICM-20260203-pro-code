# Q1 专用整理：Battery Historian（bugreport）→ 场景输入函数

本文件夹用于服务题面 **Q1 / Requirement 1：Continuous-Time Model** 中的这句话：

> “You may want to begin with the simplest reasonable description of battery drain and then extend it to incorporate additional contributors such as screen usage, processor load, network connections, GPS usage, and other background tasks.”

Battery Historian 的价值在于：把“手机真实使用行为”变成**可解释、可追溯**的外生输入 `u(t)`，从而驱动你的连续时间 SOC 模型。

本目录不追求“完全自动解析”（不同 Android 版本差异很大），而是提供一套**可复现实例**与**手工/半自动提取流程**，便于你在论文 Q1 里说明：

- 我们如何把屏幕/网络/GPS/后台等因素转为分段输入；
- 为什么这些输入是“有证据链”的（不是拍脑袋设定）。

---

## 你会用到哪些原始内容

- 原始样例（可复现输入）：
  - `MCM_Sim/26A/Load-Model/Battery-Historian/raw/bugreport_*.{txt,html}`
- 原始说明（推荐先读）：
  - `MCM_Sim/26A/Load-Model/Battery-Historian/赛题A_用途说明.md`
  - `MCM_Sim/26A/Load-Model/Battery-Historian/README.md`

---

## 与主代码（src/）的接口：我们要提取什么

你最终要把 bugreport 里的时间线抽象成 `src` 里场景系统能接的字段：

- 目标结构：`mcm26a.scenarios.schedule.Segment`（分段常值输入）
  - 位置：`MCM_Sim/26A/src/mcm26a/scenarios/schedule.py`

字段映射与提取步骤见：

- `docs/01_字段到Segment映射.md`
- `docs/02_手工提取流程.md`

---

## 重要注意（写论文也要写清楚）

- 样例 bugreport 的 Android 版本较老（KK/L），更适合演示“方法流程”而非直接当作现代机型参数真值。
- bugreport 可能包含隐私信息：如果你采集自己的 bugreport，请在提交/共享前做脱敏，并确认符合题面“公开可用/开放许可”的要求。

