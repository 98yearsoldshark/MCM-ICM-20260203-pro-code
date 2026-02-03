# 交接说明：Battery Intelligence Lab（Data and code）

本文件面向“下一位接手者”，用于快速理解本目录的目的、内容结构、下载/校验方式，以及如何在团队内避免与其他数据源目录重复。

## 0. 这是什么（范围界定）

本目录的职责是：

- 记录 Battery Intelligence Lab “Data and code” 页面上列出的资源（Models + Data + 外部链接）
- 生成直链下载清单（`download_list.md` / `sources/urls.txt`）
- 将 Models（GitHub 仓库 zip）与 Data（Oxford ORA 文件）下载到本地并整理（`raw/`、`extracted/`）
- 生成可校验/可追溯的清单（`manifest.csv`）

本目录默认 **不镜像**：
- “Links to external sites” 中的外部站点（PyBaMM / Battery Archive / CALCE / NASA），只保留链接与指向本仓库其他目录的说明。

## 1. 目录结构（必须掌握）

- `download_list.md`：人类可读的下载清单（含直链与分组）
- `FOR_MCM26A.md`：本目录如何服务 2026 MCM Problem A（写作/建模使用建议）
- `README.md`：快速使用说明（从这里开始）
- `manifest.csv`：下载/解压清单（大小、sha256、状态、来源 URL）
- `raw/`：原始下载文件（按 models/ 与 data/ 分类）
- `extracted/`：解压后的内容（仅对 zip 解压）
- `sources/`：
  - `data-and-code.md`：Battery Intelligence Lab 页面快照（markdown）
  - `ora_*.html`：Oxford ORA 数据集页面快照（用于追溯/防止页面变动导致链接丢失）
  - `urls.txt`：直链列表（每行一个 URL，便于批量下载）
- `scripts/`：
  - `generate_download_list.py`：生成/更新上述文件的脚本
  - `sync_assets.py`：按 `sources/urls.txt` 下载并整理到 `raw/` 与 `extracted/`

## 2. 数据来源与可追溯性

核心来源页面：
- `http://battery-intelligence-lab.github.io/data-and-code/`

备注：
- 在部分网络环境中，`*.github.io` 可能会被重置连接；脚本使用 `https://r.jina.ai/` 代理抓取页面内容，并在快照顶部保留 “URL Source / Published Time” 信息用于追溯。

Oxford ORA 数据集页面（脚本会抓取并快照）：
- Oxford Battery Degradation Dataset 1（ORA object）
- Oxford Energy trading battery degradation dataset（ORA object）
- Oxford Path dependence battery degradation dataset（ORA object）

## 3. 如何更新（标准流程）

当你怀疑链接变更、或希望刷新文件列表时（可选）：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/generate_download_list.py
```

更新后，建议做 2 个基本检查：

1) `sources/urls.txt` 是否仍能覆盖主要条目（Models + ORA 文件直链）
2) `download_list.md` 中 ORA 文件列表是否完整（至少包含 Readme/Guide 等关键文件）

随后执行下载与整理（主要步骤）：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py
```

运行后请检查：
- `manifest.csv` 中是否存在 `failed(...)` 或 `skipped_low_disk`
- `raw/` 下是否已生成对应文件
- 若为 zip：`extracted/` 下对应目录是否非空（脚本会生成 `.extracted.ok` 作为标记）

如果你确实需要把 ORA 的大 zip（如 Group_1~4）也解压，请显式开启（注意磁盘占用会显著增加）：

```bash
python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py --extract-data-zips
```

## 4. 与其他数据源目录的关系（避免重复）

该页面包含外部资源链接，但本仓库已拆分为独立目录管理：

- CALCE：`MCM_Sim/26A/data/calce-umd/`
- Battery Archive：`MCM_Sim/26A/data/Battery-Archive/`
- NASA：建议独立建目录（尚未在此处镜像）

如果你需要在“总索引”里引用这些外部数据，推荐：
- 在 `download_list.md` 中保留外链
- 在说明中指向本仓库已有目录（而不是复制一份数据）

## 5. 已知注意事项 / 坑位

- **数据体积**：ORA 的部分 zip/`.mat` 可能很大，下载前请确认磁盘空间与团队约定（是否需要全量镜像）。
- **链接稳定性**：ORA 文件直链形式为 `https://ora.ox.ac.uk/objects/<uuid>/files/<id>`；若 ORA 页面结构变化，解析规则可能需要调整。
- **默认分支**：GitHub 仓库 zip 直链依赖默认分支名（main/master）。脚本会通过 GitHub API 获取默认分支；若遇到 API 限流，可临时改为手动指定。
 - **磁盘保护**：`sync_assets.py` 会在磁盘剩余不足（< 512MiB 且该文件尚未存在）时跳过新下载并标记为 `skipped_low_disk`。

## 6. 常用校验方法（团队交付建议）

- 校验文件是否齐全：对照 `manifest.csv` 的 `status_download`/`status_extract`
- `skip` 含义：表示本地已存在而跳过重复下载/解压（幂等），不等于缺失
- 校验文件是否被篡改：对照 `manifest.csv` 中 `sha256`（可抽查或全量核对）
