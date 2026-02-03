# Battery Historian（Android 耗电分析）样例数据集

本目录用于收集/整理 **Android Battery Historian** 的输入样例数据（bugreport），方便离线测试解析与可视化流程。

如果你在做 2026 MCM 问题 A（智能手机电池耗电建模），建议先阅读：`赛题A_用途说明.md`（把本目录与赛题建模需求对齐的说明）。

## 目录结构

- `download_list.md`：可直接下载的样例文件直链清单（含来源说明）。
- `raw/`：已下载的样例文件（bugreport 文本 + 一个解析结果 HTML）。
- `raw/sha256.txt`：`raw/` 下文件的 SHA-256 校验值。
- `sources/`：来源仓库的 README 与 commit 记录（用于追溯）。

## Battery Historian 是什么

Battery Historian 是 Google 官方提供的 Android 电池耗电分析工具，主要通过解析 **bugreport**（其中包含 `batterystats` 等信息）来展示时间线、统计指标，并支持两份 bugreport 的 A/B 对比。

- 官方仓库：`google/battery-historian`
- 截至 **2026-01-30**，该仓库在 GitHub 上处于 **Archived（只读）** 状态，但仍可使用其 Docker 镜像/源码进行学习与本地分析。
- 官方仓库通常不附带可直接上传的公开 bugreport 示例文件，因此本目录额外整理了第三方公开样例用于练习。

## 如何使用这些样例文件（简要）

1. 启动 Battery Historian（推荐按官方 README 使用 Docker 镜像启动本地服务）。
2. 打开页面后上传本目录的 `raw/bugreport_*.txt`（或你自己生成的 `bugreport.zip` / `bugreport.txt`）。

提示：不同 Android 版本生成的 bugreport 结构会有差异；本目录样例偏旧（文件名中 `KK`/`L` 分别对应 KitKat / Lollipop），适合用于“工具链跑通”和“解析器健壮性”验证。

## 如何生成你自己的 bugreport（更接近真实手机数据）

在 Android 设备上开启 USB 调试后：

- Android 7.0 及以上（常见输出为 zip）：
  - `adb bugreport bugreport.zip`
- Android 6.0 及以下（常见输出为文本）：
  - `adb bugreport > bugreport.txt`

注意：bugreport 往往包含设备信息、应用包名、网络状态等敏感内容；共享/提交前建议脱敏处理。

## 完整性校验

在本目录下执行（macOS 可用）：

```bash
cd MCM_Sim/26A/Load-Model/Battery-Historian
shasum -a 256 -c raw/sha256.txt
```

## 来源与许可

本目录的示例 bugreport 文件来自公开仓库 `shannon-alan/battery-historian-2.0`，其仓库根目录包含 Apache-2.0 许可文本；更多信息见 `sources/`。
