# SmartphoneMeasurements（手机侧公开测量数据：补充）

本目录用于存放与 **2026 MCM Problem A（智能手机电池耗电建模）** 相关的“手机侧”公开数据集（偏使用行为/通信功耗实测），作为 `MCM_Sim/26A` 建模与写作的补充证据来源。

注意：
- 本目录尽量保留原始下载文件（不改名/不改内容），便于追溯。
- 许可信息以原始发布页面/仓库为准；本目录部分文件本身不包含 LICENSE。
- 整理/描述过程中可能使用了 AI 工具辅助生成文字说明，若用于公开发布请自行复核措辞与事实。

## GitHub 版（不提交 zip）如何复现

准备提交到 GitHub 时，建议在 `.gitignore` 中忽略 `SmartphoneMeasurements.zip`。
克隆仓库后可运行脚本一键下载：

```bash
python3 MCM_Sim/26A/data/SmartphoneMeasurements/scripts/sync_smartphone_measurements.py
```

脚本会下载 `SmartphoneMeasurements.zip` 并更新 `manifest.csv`（记录 sha256/来源 URL）。

## 本仓库电池相关公开数据集总览（索引）

（原 `【先看这个】数据集说明.md` 的内容已拆分到对应目录/README，以下是“去哪找”的索引。）

1) NASA 锂电池老化数据（Battery Data Set）
   - 本仓库位置：`MCM_Sim/26A/data/NASA-BatteryData/`

2) NASA 随机负载/随机使用数据
   - 本仓库位置（PCoE #11 Randomized Battery Usage Data Set，已解压）：`MCM_Sim/26A/data/NASA-BatteryData/11.+Randomized+Battery+Usage+Data+Set/`
   - 说明：若你需要 Data.gov 的 `battery_alt_dataset.zip`（26 个电池包、CSV，UCF），见 `MCM_Sim/26A/data/NASA-BatteryData/README.md` 的“battery_alt_dataset.zip”说明（本仓库未镜像该 zip）。

3) 智能手机使用行为数据（用户级统计）
   - 本目录：`user_behavior_dataset.csv`

4) Samsung 设备实测功耗与吞吐（通信功耗对比）
   - 本目录：`SmartphoneMeasurements.zip`

5) CALCE 数据集（UMD CALCE Battery Data）
   - 本仓库位置：`MCM_Sim/26A/data/calce-umd/`

## 本目录内容

### A) `user_behavior_dataset.csv`（Mobile Usage Behavior Analysis）

- 来源仓库（上游，需自行核对许可）：`https://github.com/GeorgeHanyMilad/Mobile-Usage-Behavior-Analysis`
- 文件规模：700 行 × 11 列（每行一个用户）
- 字段（列名以文件为准）：
  - `User ID`
  - `Device Model`
  - `Operating System`
  - `App Usage Time (min/day)`
  - `Screen On Time (hours/day)`
  - `Battery Drain (mAh/day)`
  - `Number of Apps Installed`
  - `Data Usage (MB/day)`
  - `Age`
  - `Gender`
  - `User Behavior Class`

适合用途（对赛题 A）：
- 用于构造“轻度/中度/重度用户”的日均使用强度范围（屏幕时长、应用使用、流量、日耗电 mAh）
- 用于敏感性分析与建议：改变亮度/屏幕时长/数据使用量等时，TTE 如何变化（注意：这是用户级统计，不直接提供连续时间轨迹）

### B) `SmartphoneMeasurements.zip`（pspachos/SmartphoneMeasurements）

- 来源仓库（上游，需自行核对许可）：`https://github.com/pspachos/SmartphoneMeasurements`
- zip 内容：一个 GitHub 仓库快照（`SmartphoneMeasurements-main/`）
- 内含 README 给出的关键信息（摘录要点）：
  - 设备：Samsung S4 Mini、Galaxy Note 3、Galaxy Note 4、MEGA
  - Monsoon 电源/功耗监测：采样间隔约 0.2s；列：`Time(s), Current(A), Power(W), Voltage(V)`
  - 吞吐：iPerf（WiFi / WiFi Direct），Bluetooth（定长文件计时），LTE（测速 App）
  - 场景：Baseline、WiFi、WiFi Direct、Bluetooth、LTE（每机型约 13 组测试）

适合用途（对赛题 A）：
- 提供“通信相关活动（WiFi/Bluetooth/LTE 等）”的功耗量级与吞吐对照，用于构造 `P_network(t)` 或校验你手机侧功耗分解的量级合理性。

## 完整性/交接（建议）

建议先读：
- `HANDOVER.md`：交接与使用注意事项
- `FOR_MCM26A.md`：本目录如何服务赛题 A（建模/写作映射）

如果你需要核对文件是否在搬运过程中损坏：
- 见 `manifest.csv`（本目录原始数据文件清单 + sha256）
