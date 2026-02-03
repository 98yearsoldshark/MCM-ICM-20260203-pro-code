# Battery Intelligence Lab（Data and code）资源下载与整理

本目录用于整理并（可选）下载 Battery Intelligence Lab 的 “Data and code” 页面中列出的 **Models（代码）** 与 **Data（Oxford ORA 数据集）**，并保留外部资源链接，便于团队在 `MCM_Sim/26A` 下统一做来源管理与可追溯复现。

## 你应该先看什么

1) `download_list.md`：下载清单（含直链）
2) `FOR_MCM26A.md`：本目录如何服务 2026 MCM Problem A（建议团队写作时引用）
3) `scripts/sync_assets.py`：一键下载与解压（会生成 `manifest.csv`）
4) `manifest.csv`：下载/解压清单（大小、sha256、状态、来源 URL）
5) `sources/data-and-code.md`：网页快照（用于追溯页面原文与发布时间）

## 目录结构

- `raw/`：原始下载文件
  - `raw/models/<RepoName>/`：GitHub 仓库 zip
  - `raw/data/<DatasetSlug>/`：Oxford ORA 数据集原始文件
- `extracted/`：解压后的内容（仅对 `.zip` 解压）
- `manifest.csv`：下载/解压清单（用于校验、团队交付、追溯）
- `sources/`：网页快照与直链列表
  - `sources/data-and-code.md`
  - `sources/ora_*.html`
  - `sources/urls.txt`
- `scripts/`：脚本
  - `generate_download_list.py`：重新抓取/解析页面，更新 `download_list.md` 与 `sources/urls.txt`
  - `sync_assets.py`：按 `sources/urls.txt` 下载并整理到 `raw/` 与 `extracted/`

## 外部资源（不在本目录重复镜像）

该页面也列出外部站点（PyBaMM / Battery Archive / CALCE / NASA）。为避免重复下载与内容重叠，本目录默认 **不镜像** 这些站点的数据，仅保留链接与指向本仓库其他目录的说明：

- CALCE 数据：`MCM_Sim/26A/data/calce-umd/`
- Battery Archive：`MCM_Sim/26A/data/Battery-Archive/`
- NASA：如需本地化，建议另建独立目录

## 使用方式

### 1) 刷新下载清单（可选）

运行：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/generate_download_list.py
```

脚本会（简述）：
- 抓取 BIL 页面内容快照到 `sources/data-and-code.md`
- 抓取 Oxford ORA 三个数据集页面快照到 `sources/ora_*.html`
- 解析 ORA 页面中的文件直链，并更新 `download_list.md` 与 `sources/urls.txt`
- 查询 GitHub 仓库默认分支，生成对应的 zip 直链

### 2) 下载并整理（主要步骤）

运行：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py
```

完成后会生成/更新：
- `raw/`（原始文件）
- `extracted/`（zip 解压结果；默认只解压 Models 的 GitHub 仓库 zip）
- `manifest.csv`（校验与追溯用）

### 3) `manifest.csv` 常见状态说明（为什么会出现 `skip`）

`manifest.csv` 中有两个主要状态列：`status_download` 与 `status_extract`。常见取值含义如下：

- `downloaded`：本次运行成功下载。
- `skip`：本地 `raw/...` 已存在且非空，为避免重复下载而跳过（幂等）。
- `skipped_low_disk`：磁盘空间不足且该文件尚未存在，脚本为保护磁盘而跳过新下载。
- `failed(...)`：下载失败（网络/权限/站点错误等），需重试或手动下载。
- `extracted`：本次运行成功解压。
- `skip / skip_nonempty`：解压目录已存在（或目录非空），为避免重复解压而跳过。
- `n/a`：不适用（例如非 zip 文件，或 data/*.zip 默认不解压）。

因此：**`skip` 不代表缺失**，通常表示“之前已完成下载/解压”。

如确实需要解压 Oxford ORA 的大体积 zip（可能占用大量磁盘），请显式开启：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py --extract-data-zips
```
