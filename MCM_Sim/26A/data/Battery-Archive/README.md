# Battery-Archive（BatteryArchive.org 导出数据）

本目录用于存放从 **BatteryArchive.org** 的公开仪表板（Redash Public Dashboards）导出的电池数据，并提供可复现的下载脚本与清单。

如果你是接手维护/复现的同学，建议先阅读：`交接说明.md`。

## 目录结构

- `sources/`：BatteryArchive.org 页面快照（用于追溯 iframe 中的 dashboard token）
- `raw/`：Redash dashboard 元数据（`api/dashboards/public/<token>` 的 JSON）
- `extracted/`：导出的 CSV 数据
  - `extracted/cycling/`：循环测试（Cycling tests）
    - `cell_list.csv`：循环测试电芯列表
    - `*.tar.gz`：按查询（query）打包的压缩包（每个包里是“每个 cell 一个 CSV”）
  - `extracted/disruptive/`：破坏/安全测试（Disruptive tests）
    - `cell_list.csv`：破坏测试电芯列表
    - `*.tar.gz`：按查询打包的压缩包（每个包里是“每个 cell 一个 CSV”）
- `download_list.md`：可直接下载的清单（包含 dashboard token、query 列表、脚本用法）
- `manifest.csv`：导出清单（每个 CSV 的来源 query/参数、行数、hash、状态等）
- `scripts/sync_battery_archive.py`：一键同步脚本（推荐）

## 一键下载 / 更新

在仓库根目录执行：

```bash
python3 MCM_Sim/26A/data/Battery-Archive/scripts/sync_battery_archive.py
```

脚本会：

1. 下载 `cycle_list.html` / `disruptive_list.html` 等页面快照到 `sources/`
2. 自动解析 public dashboard token（无需手工维护）
3. 先导出 cell 列表，再逐 cell 导出各类曲线/时序数据到 `extracted/`
4. 按 query 自动打包为 `tar.gz`（节省磁盘空间）
5. 生成 `download_list.md` 与 `manifest.csv`

## 解压说明

示例（解压某个 query 的数据到当前目录）：

```bash
tar -xzf MCM_Sim/26A/data/Battery-Archive/extracted/cycling/energy_and_capacity_decay.tar.gz
```

解压后会得到同名目录（例如 `energy_and_capacity_decay/`），里面是每个 cell 一个 CSV。
文件名对 `cell_id` 做了 URL 编码（例如 `/` 会变成 `%2F`）。

## 覆盖情况（以 `manifest.csv` 为准）

由于部分 query 在公开接口侧可能存在缺失/异常，某些压缩包里不一定包含 **全部** cell 的 CSV。
当前导出数量可在 `manifest.csv` 的 `records` 列查看（表示压缩包内 CSV 数量）。

## 数据格式说明（简要）

不同 query 的列结构可能不同，常见两类：

- **长表（long format）**：`series`, `test_time`, `value`（部分还带 `cycle_index`）
  - `series` 通常形如 `v: <cell_id>`、`ah_c: <cell_id>` 等
- **带显式 cell_id 的表**：直接包含 `cell_id` 列（脚本也会在缺失时补齐 `cell_id`，便于合并）

以实际 CSV 的表头为准；更详细的来源对应关系请看 `manifest.csv`。

## 引用与许可

BatteryArchive 的页面要求在使用其导出的数据时引用 BatteryArchive.org，并遵守各来源机构的数据复用/引用政策（见 `sources/study_summaries.html` 及 BatteryArchive 网站说明）。
