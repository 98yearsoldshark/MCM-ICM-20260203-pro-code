# BatteryArchive.org 可直接下载清单（Redash 公共接口）

本目录数据通过 BatteryArchive 的公开 Redash 仪表板导出。

生成时间：2026-01-30T11:03:41

## 一键下载（推荐）

```bash
python3 MCM_Sim/26A/data/Battery-Archive/scripts/sync_battery_archive.py
```

脚本默认会将每个 query 的逐 cell CSV **打包为 `tar.gz`**（节省磁盘空间），输出位置：

- `extracted/cycling/*.tar.gz`
- `extracted/disruptive/*.tar.gz`

解压示例：

```bash
tar -xzf MCM_Sim/26A/data/Battery-Archive/extracted/cycling/energy_and_capacity_decay.tar.gz
```

## 循环测试（Cycling tests）

- Cell 列表 dashboard token：`dG5C30gXNzH77rMeApZ4lIOrjy0m7pencFScWFA5`
- Data dashboard token：`61PzyYn9u56njtPDOh37VVBFasGusUlxc7WZ1FSj`
- Cell 列表 query：`29` Cycle Test Cell List

Data dashboard 的查询（按查询名/ID）：

- `30` Charge voltage by step
- `31` Discharge voltage by step
- `28` Efficiencies
- `26` Energy and Capacity Decay
- `40` Max and Min Voltage by Cycle

接口示例（获取循环 Cell 列表）：

```bash
curl -sS -X POST "https://database.batteryarchive.org/api/queries/29/results?api_key=dG5C30gXNzH77rMeApZ4lIOrjy0m7pencFScWFA5" \
  -H "Content-Type: application/json" \
  -d '{"queryId":<QUERY_ID>,"parameters":{...}}'
```

## 破坏测试（Disruptive tests）

- Cell 列表 dashboard token：`dmTEMEmQeR2qNe8O6ubte3IubX4StYsZrpJvUmr8`
- Data dashboard token：`ipzyQoxii9sEERUcnoxb2p5G5oEpYmULTdRUybOb`
- Cell 列表 query：`23` Disruptive Test Cell List

Data dashboard 的查询（按查询名/ID）：

- `37` Disruptive Test: Displacement
- `20` Disruptive Test: Force
- `25` Disruptive Test: Temperatures
- `19` Disruptive Test: Voltage

注：更详细的“每个输出文件来自哪个 query/参数”的对应关系见 `manifest.csv`。
