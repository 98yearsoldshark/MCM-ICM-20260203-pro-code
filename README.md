# 2026 美赛（MCM/ICM）赛前与赛中代码资料库

本仓库用于整理我在 **2026 美国大学生数学建模（MCM/ICM）** 备赛与比赛过程中的：
- 建模代码（仿真/参数估计/可视化/报告自动化）
- 数据与复现实验脚本（尽量做到“可追溯、可一键拉取/重建”）
- 写作素材与过程记录（用于沉淀方法论与复盘）

当前主线项目为：`MCM_Sim/26A`（2026 MCM Problem A：智能手机电池耗电建模）。

---

## 快速开始（以 26A 为例）

建议使用 `python3`（本机若只有 `python3`，不要用 `python`）。

1) 运行脚本（无需安装成包）：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/<script>.py
```

2) GitHub 版“只提交脚本、不提交大数据”的数据恢复：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile core
```

数据拉取/重建脚本索引：`MCM_Sim/26A/data/SYNC_GUIDE.md`

---

## 目录结构（简述）

- `MCM_Sim/`
  - 多个历年/模拟项目；其中 `MCM_Sim/26A` 为 2026 A 题主项目（代码 + 论文材料 + 数据说明）。
- `MCM_Toolkit_2026/`
  - 2026 相关工具/资料（按需使用）。
- `0ys-files/`
  - 过程记录、日记、协作设计草稿（用于复盘与沉淀）。
- `u_tools/`
  - 零散工具脚本。
- `mcm_temp/`
  - 临时目录（可随时清空，不建议提交）。

---

## GitHub 提交建议

本仓库默认通过 `.gitignore` 忽略：
- 自动生成输出：`out_plots/`、`out_reports/` 等；
- 可再下载/可再生成的大体积数据（CALCE/NASA/Zenodo 等的 raw/extracted/zip 等）。

如果你克隆后发现缺数据，请优先按 `MCM_Sim/26A/data/SYNC_GUIDE.md` 运行对应同步脚本恢复。

