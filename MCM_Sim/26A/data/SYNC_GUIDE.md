# 26A 数据下载/复现脚本索引（面向 GitHub 版）

目标：把项目整理到 GitHub 时 **不提交 GB 级数据**，只提交脚本/说明；需要时可一键拉取或重建。

总入口（推荐）：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile core
```

该命令会调用各数据目录自带的同步脚本，把 Q1/Q2/Q3 常用数据拉取到 `MCM_Sim/26A/data/` 的预期路径。

---

## 各数据源脚本

| 数据源 | 目录 | 建议 GitHub 提交策略 | 同步/重建脚本 |
|---|---|---|---|
| AndroWatts（Zenodo，open_data） | `data/open_data/` | 建议只保留 `material/res_test/aggregated.csv` 与 README；忽略 `material/trace_parser/`、`material/application-android-conso-tel/` | `data/open_data/scripts/sync_open_data_from_zenodo.py` |
| CALCE-UMD（电池侧） | `data/calce-umd/` | 忽略 `raw/`、`extracted/`，只提交 scripts/sources/manifest/download_list | `data/calce-umd/scripts/sync_calce_umd.py` |
| NASA PCoE（电池侧） | `data/NASA-BatteryData/` | 忽略 zip 与解压目录，只提交 scripts/README/HANDOVER | `data/NASA-BatteryData/scripts/sync_nasa_batterydata.py` |
| SmartphoneMeasurements（通信功耗补充） | `data/SmartphoneMeasurements/` | 忽略 `SmartphoneMeasurements.zip`，保留 `user_behavior_dataset.csv` 与 README | `data/SmartphoneMeasurements/scripts/sync_smartphone_measurements.py` |
| BatteryArchive 导出（可选增强） | `data/Battery-Archive/` | 忽略 `raw/`、`extracted/` | `data/Battery-Archive/scripts/sync_battery_archive.py` |
| Battery Intelligence Lab（可选增强） | `data/Battery-Intelligence-Lab/` | 忽略 `raw/`、`extracted/` | `data/Battery-Intelligence-Lab/scripts/sync_assets.py` |
| 派生主表（AndroWatts×电池状态） | `data/MCM2026_battery_state_table/` | **不提交** `master_modeling_table.csv`，用脚本重建 | `data/MCM2026_battery_state_table/scripts/build_master_modeling_table.py` |
| 外部对照材料（许可不清晰，不建议用于论文正式数据） | `data/02-A_share/` | 建议 GitHub 忽略（本仓库已忽略） | 手工恢复说明：`data/02-A_share/来源与恢复.md` |

---

## 02-A_share（外部对照材料）来源与恢复链接（手工）

> 重要：该资料许可不清晰，**不建议**作为论文正式数据源；仅用于内部对照。

- 腾讯文档（资料说明页）：`https://docs.qq.com/doc/p/b7541fe9ed4814288ba22bacd36817751e9610c7`
- 该页面内提取到的“分享版资料（百度网盘）”：
  - 链接：`https://pan.baidu.com/s/1KO0xFZTPp2G8YJOobzMVpg`
  - 提取码：`bjiu`
- 说明：该资料的下载通常需要人工在浏览器完成（登录/验证码/权限等），因此这里仅记录链接与提取码，不提供自动下载。

## 备注

1) 如果某些站点（例如 Zenodo）在你的网络环境下不可访问，请切换网络/VPN，或在可访问环境下运行同步脚本。

2) 赛题硬口径是：数据用于“参数估计/验证/量级锚定”，不能替代连续时间机理模型本身；因此即便不下载全部原始数据（trace/app），只要保留 `aggregated.csv` 这类“聚合可引用证据”，也能满足建模主线。
