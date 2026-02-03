# 交接说明：CALCE-UMD 电池数据（`calce-umd/`）

本文件面向“下一位接手者”，用于快速理解本目录里有哪些数据、怎么来的、怎么验证、怎么更新与如何开始使用。

> 重要：本数据来自 CALCE（UMD）公开页面。用于论文/报告发表时，应按原页面要求引用对应论文/文献（见下文“引用与合规”）。
>

## 1. 你接手时先看什么

建议阅读顺序：

1) `README.md`：总体介绍与目录结构  
2) `FOR_MCM26A.md`：与 2026 MCM Problem A 的关联说明（为什么用这套数据、用哪些子集）  
3) `manifest.csv`：原始 zip 清单（含 sha256、来源 URL）  
4) `INTEGRITY_REPORT.md`：完整性校验报告（可再生成）  
5) `examples/`：可直接运行的 demo（校验/读取/绘图）  
6) `sources/`：网页快照（测试说明、样本编号、引用论文都在这里）  
7) `raw/` 与 `extracted/`：实际数据文件

## 2. 数据来源（可追溯）

本目录数据的 URL 均来自以下页面，并已保存网页快照：

- Battery Data：`https://calce.umd.edu/battery-data`（快照：`sources/battery-data.html`）
- Accelerated cycle life testing：`https://calce.umd.edu/battery-accelerated-cycle-life-testing`（快照：`sources/battery-accelerated-cycle-life-testing.html`）
- Anomaly detection data：`https://calce.umd.edu/battery-anomaly-detection-data`（快照：`sources/battery-anomaly-detection-data.html`）

解析出的直链列表保存在：`sources/urls.txt`（当前为 94 条）。

## 3. 本地目录结构（关键约定）

- `sources/`：网页快照 + `urls.txt`
- `raw/`：原始压缩包（**最终以 94 个 zip 为准**）
  - `raw/battery-data/A123/`
  - `raw/battery-data/CS2/`
  - `raw/battery-data/CX2/`
  - `raw/battery-data/SP/`
  - `raw/pl/`
  - `raw/storage/`
  - `raw/accelerated/`
  - `raw/anomaly/`
- `extracted/`：解压后的数据（每个 zip 解压到同名目录）
  - 示例：`raw/battery-data/CS2/CS2_3.zip` → `extracted/battery-data/CS2/CS2_3/`
- `manifest.csv`：原始文件清单（用于校验/追溯）
  - 列：`raw_path,size_bytes,sha256,source_url`
- `download_list.md`：直链下载清单（按目录分组，便于人工核对）
- `scripts/`：同步脚本
  - `scripts/sync_calce_umd.py`

## 4. 分类规则（URL → 本地路径）

同步脚本会将 URL 映射到 `raw/` 下的路径（便于统一管理）：

- URL 路径包含 `/accelerated/` → `raw/accelerated/*.zip`
- URL 路径包含 `/anomaly/` → `raw/anomaly/*.zip`
- URL 路径包含 `/pl/` → `raw/pl/*.zip`
- URL 路径包含 `/pln/`（Storage 页面提供的 zip）→ **统一归档**到 `raw/storage/*.zip`
- Battery Data 主页顶层 zip（通过文件名前缀归类）：
  - `A123_*` → `raw/battery-data/A123/`
  - `CS2_*` → `raw/battery-data/CS2/`
  - `CX2_*` → `raw/battery-data/CX2/`
  - `SP*` → `raw/battery-data/SP/`

说明：
- 脚本会对 URL 中的 `%20` 等进行 decode，本地文件名使用空格（更易读）。
- 解压目录名使用 zip 文件名去掉 `.zip`（同样会是 decode 后的名字）。

## 5. 如何更新/重下（可复现流程）

当 CALCE 页面更新、或你需要重新拉取一遍数据时：

1) 更新 `sources/urls.txt`
   - 方式 A：人工编辑（添加/删除 URL）
   - 方式 B：重新抓取页面并解析（如你要自动化，可再写一个解析脚本；目前仓库内以 `urls.txt` 作为“单一事实来源”）
2) 运行同步脚本：

```bash
python3 MCM_Sim/26A/data/calce-umd/scripts/sync_calce_umd.py
```

脚本行为（简化描述）：
- 若 `raw/` 下对应 zip 已存在且 zip 可被正常打开：跳过下载
- 否则：重新下载该 zip
- 若 `extracted/` 下对应目录不存在或为空：解压
- 生成/覆盖：`download_list.md`、`manifest.csv`

## 6. 如何校验完整性（交付/团队协作常用）

推荐校验方式：

- 以 `manifest.csv` 为准，随机抽查或全量校验 `sha256`
- 检查 zip 可读（脚本已隐式做了“能否打开 zip”的检查）

示例：对单个文件校验 sha256（macOS）：

```bash
shasum -a 256 MCM_Sim/26A/data/calce-umd/raw/battery-data/CS2/CS2_3.zip
```

对照 `manifest.csv` 中同一行的 `sha256` 即可。

推荐一键校验（可生成报告）：

```bash
python3 MCM_Sim/26A/data/calce-umd/examples/00_verify_integrity.py --report INTEGRITY_REPORT.md
```

## 7. 读取数据的实践建议（给建模/分析同学）

数据格式不止 Excel：本目录内同时包含大量 **CSV**（主要来自 Storage/Impedance）与 **MAT**（如 anomaly Dataset2、部分 PL 数据），这两类通常更容易跨平台读取。

### 7.1 CSV（Storage/Impedance）

- 典型路径：`extracted/storage/Impedance_*/**/*.csv`
- 常见含义（推断）：`freq(Hz), Zreal(Ohm), Zimag(Ohm), |Z|(Ohm), phase(deg)`
- 可运行 demo：`examples/01_plot_storage_impedance.py`（Nyquist/Bode 图）

### 7.2 MAT（Anomaly/PL）

- Anomaly Dataset2：`extracted/anomaly/Dataset2/Dataset2.mat`
  - 可运行 demo：`examples/02_plot_anomaly_dataset2.py`（容量衰减曲线）

### 7.3 Excel（.xls/.xlsx）

Excel 仍占多数（大量日志为 `.xls/.xlsx`）。常用读取方式：

- `.xlsx`：`pandas.read_excel(..., engine="openpyxl")`
- `.xls`（老格式）：`pandas.read_excel(..., engine="xlrd")`  
  - 注意：`xlrd` 新版本默认不支持 xlsx；且 `.xls` 读取在不同环境可能需要额外依赖

建议做的“二次加工”（可选，但强烈建议团队统一）：

1) 把常用数据表批量转成 `parquet/csv`（读取更快，跨平台更稳）
2) 在 `src/mcm26a/` 下写一个数据加载器（统一字段名/单位/时间轴）
3) 给每个数据集写一个最小示例（读取一条曲线、画电压-时间或容量-循环数）

## 8. 引用与合规（必须交接清楚）

CALCE 页面明确说明：若将数据用于发表/公开报告，应引用对应的 CALCE 文章/论文（通常在每个数据块下方以 “The above data files have been referenced in:” 列出）。

因此：
- 在最终论文/报告中，至少引用与所用数据集对应的参考文献
- 若需要复核引用列表：直接打开 `sources/*.html` 搜索 “referenced in” 或 “The above data files”

## 9. 已知注意事项 / 坑位记录

- 数据量较大：`raw/` 约 5.7 GiB，`extracted/` 约 10 GiB；请预留磁盘空间、避免把 `extracted/` 同步到不必要的地方。
- 文件名含空格：例如 `SP1_Initial capacity_10_16_2015.zip`，写脚本时务必正确处理路径（建议用 Python `Path`，或 shell 中加引号）。
- 解压后目录结构不完全统一：多数 zip 内还有一层同名目录；个别（如 `CX2_8`）内部目录大小写可能与 zip 名不一致（脚本不强行重命名，以保留原始结构）。
- 如果你计划把数据提交到 git：强烈不建议（体积过大）；推荐用外部存储（NAS/对象存储）+ `manifest.csv` 做版本化索引。

## 10. 接手者的下一步（建议）

若你的任务是做建模/仿真/寿命预测，建议按优先级：

1) 先确定你要用哪个子数据集（CS2/CX2/accelerated/anomaly 等）  
2) 基于 `sources/` 快照整理“测试条件 → 字段/单位 → 目标变量”的数据字典  
3) 写一个最小可复现的 notebook / 脚本：读取 1 个电芯、画 1-2 张关键图（电压-时间、容量-循环等）  
4) 再决定是否把数据转换为 parquet 并做统一 schema
