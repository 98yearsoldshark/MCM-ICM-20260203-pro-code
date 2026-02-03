# CALCE-UMD 电池数据（直链下载镜像）

本目录用于存放 **CALCE（University of Maryland）公开电池数据**的直链下载文件与解压结果，供 `MCM_Sim/26A` 使用与复现实验。

下载时间：2026-01-30

交接与快速上手：
- 面向接手者的完整说明：`HANDOVER.md`
- 面向赛题 A 的使用说明：`FOR_MCM26A.md`
- 可直接运行的小例子：`examples/`（含完整性校验、CSV/MAT 读取与绘图 demo）
- 完整性校验报告（可再生成）：`INTEGRITY_REPORT.md`

## 与本仓库其他说明文档的对应（补充“数据集简介/许可摘要”）

本仓库曾有一个“电池相关数据集总览”文档对 CALCE 数据集做过摘要说明；该总览已拆分进各目录 README 并删除以避免重复/过期信息。为避免信息分散，本 README 在此补充/对齐其中的关键条目（并以 CALCE 官方页面说明为准）：

- 数据集：University of Maryland CALCE Battery Research Group / CALCE Battery Data
- 官方入口：`http://www.calce.umd.edu/battery-data`
- 常见覆盖范围（概述）：多型号 Li-ion 电芯在不同 SOC（例如 0%/50%/100%）与温度（约 -40C 至 50C）条件下的容量/阻抗等测试数据
- 常见文件格式：`.xlsx` / `.txt`（也可能包含其他格式，按具体子集为准）
- 数据体量：完整集合可能达到 GB 级（2-3GB 量级是常见说法；与选取子集有关）
- 许可/引用：CALCE 通常允许学术研究使用，但往往要求在论文/报告中注明来源并按网页给出的参考文献进行引用（本仓库已将网页快照保存在 `sources/` 便于核对）

## 数据来源（网页备份）

- `sources/battery-data.html`：CALCE “Battery Data” 页面备份
- `sources/battery-accelerated-cycle-life-testing.html`：加速寿命测试相关页面备份
- `sources/battery-anomaly-detection-data.html`：异常检测数据页面备份
- `sources/urls.txt`：从上述页面整理出的可直接下载 URL（每行一个）

## 目录结构

- `raw/`：原始压缩包（`.zip`），按分类整理
  - `raw/battery-data/`：A123 / CS2 / CX2 / SP（原站顶层链接）
  - `raw/accelerated/`：Accelerated cycle life testing
  - `raw/anomaly/`：Anomaly detection dataset
  - `raw/pl/`：不同 SOC 区间/倍率等实验数据
  - `raw/storage/`：容量/阻抗在不同温度与存储期的表征数据（原站 URL 路径为 `pln/`）
- `extracted/`：解压后的数据（每个 zip 解压到同名目录），与 `raw/` 的分类一致
- `download_list.md`：直接下载链接清单（带本地保存路径）
- `manifest.csv`：本地文件清单（raw_path / size_bytes / sha256 / source_url）
- `scripts/sync_calce_umd.py`：一键下载与解压脚本（可重复运行）

## 数据体积（参考）

可用下面命令查看当前占用：

```bash
du -sh MCM_Sim/26A/data/calce-umd/raw MCM_Sim/26A/data/calce-umd/extracted
```

## 重新下载/更新

在仓库根目录运行：

```bash
python3 MCM_Sim/26A/data/calce-umd/scripts/sync_calce_umd.py
```

脚本逻辑（简述）：
- 读取 `sources/urls.txt`
- 下载到 `raw/`（已存在且可正常打开的 zip 会跳过）
- 解压到 `extracted/`（目标目录非空则跳过）
- 生成/更新 `download_list.md` 与 `manifest.csv`

## 使用与引用提示

CALCE 数据可能有使用条款/引用要求。用于建模、论文或报告时，请以 CALCE 官方页面说明为准并按要求引用。
