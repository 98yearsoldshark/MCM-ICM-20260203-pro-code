# 本目录如何服务 2026 MCM Problem A（智能手机电池耗电建模）

本文档用于把 `MCM_Sim/26A/data/Battery-Intelligence-Lab/` 与赛题 **Problem A：智能手机电池耗电建模** 关联起来，方便后续接手者理解“为什么要有这个目录、怎么用它、用到哪一部分资源”，并避免与 `calce-umd/` 等其他数据源目录混用。

赛题原文/译文位置（本仓库）：`MCM_Sim/26A/论文/赛题/`（`A中文纯文本.md`、`A英文纯文本.md`）。

## 1. 赛题需要什么（与本目录的对应关系）

赛题强调：

- 必须建立 **连续时间（continuous-time）** 的 SOC 动力学模型，并用于预测 **TTE（Time-to-Empty）**；
- 数据用于参数估计与验证，但不能用离散拟合/纯黑盒回归替代机理模型；
- 需要讨论温度影响、使用条件、以及“电池历史/老化”对续航的影响。

`Battery-Intelligence-Lab/` 提供的资源主要服务于“电芯/电池层”（而不是手机 App/屏幕/CPU 的负载层）：

- **Models（代码）**：参数辨识/机理模型/退化模型/温度估计等参考实现，帮助你把连续时间模型写得更“像研究级机理模型”，并给出可追溯的方法来源。
- **Data（Oxford ORA 数据集）**：长期退化、真实电流剖面循环、EIS 等数据，可用于说明老化项/温度项/模型验证思路（注意：不是手机场景数据，更多用于“论证与方法验证”，而非直接拟合手机耗电曲线）。

## 2. 本目录包含什么（你可以直接用的资源）

本目录镜像自 Battery Intelligence Lab 的 “Data and code” 页面列出的内容（快照见 `sources/data-and-code.md`）：

### 2.1 Models（代码仓库，已下载并解压）

位置：
- 原始 zip：`raw/models/<RepoName>/`
- 解压后：`extracted/models/<RepoName>/`

包含（示例）：
- `PyBOP`：电池模型参数化与优化/辨识方法参考（适合写“如何用数据支撑参数”的方法段落）。
- `SLIDE`：Li-ion 退化模拟代码参考（适合写老化项/退化机理/参数含义）。
- `Spectral_li-ion_SPM`：单颗粒模型（SPM）谱方法实现参考（适合写低阶机理模型）。
- `EKF-Battery-Impedance-Temperature`：基于阻抗测量的电池温度估计（适合写温度作为状态/扰动的建模思路）。
- `Supercapacitor-Model`：与赛题相关性较弱，但可作为“低阶 PDE/谱方法”风格参考。

### 2.2 Data（Oxford ORA 数据集，已下载，默认不解压大 zip）

位置：
- `raw/data/<DatasetSlug>/`

主要数据集：
- Oxford Battery Degradation Dataset 1：长期老化实验（`.mat` + `Readme.txt`），可用于“容量随时间/循环变化”的讨论。
- Energy trading battery degradation dataset：一年实验，含电流/电压/温度剖面与月度容量测量（`.csv` + `Readme.txt`），适合用来展示“非恒定电流剖面下的模型验证/容量衰减如何进入 Q_eff”。
- Path dependence battery degradation dataset：路径依赖老化数据，含分组 zip、参考测试与 EIS（`EIS.zip` 等），适合用于“老化具有路径依赖/历史依赖”的论证与 EIS/阻抗相关讨论。

> 重要：ORA 的 `Group_*.zip` 等文件体积很大，脚本默认只下载、不解压。若确实需要解压，请运行：  
> `python3 MCM_Sim/26A/data/Battery-Intelligence-Lab/scripts/sync_assets.py --extract-data-zips`

## 3. 如何把这些资源用进你的“连续时间”模型（建议写法）

一个满足题意、且容易解释的最小连续时间骨架通常包含：

1) **SOC 动力学（库仑计数）**  
`dSOC/dt = - I(t) / Q_eff(t, T, age)`

2) **功耗/电流映射（从手机负载到电池电流）**  
你可以在手机侧构造 `P_load(t)`（屏幕/CPU/网络等），并用 `I(t) ≈ P_load(t) / V(t)` 把功率映射为电流。  
电池侧再用等效电路或低阶机理模型给出 `V(t)`（可近似/迭代求解）。

3) **温度项（T）与老化项（age）如何进入**  
本目录的代码与 ORA 数据可以帮助你在报告中把以下内容讲清楚：
- 温度影响内阻/可用容量 → 解释“冷天更快掉电/电压更早到阈值”；
- 容量衰减与历史依赖 → 解释“同样使用模式但电池更旧 → TTE 更短”；
- 在非恒定电流剖面下模型仍是连续时间方程（不是离散回归）。

## 4. 本目录内最关键的“可复现/可交接”文件

- `download_list.md`：人类可读清单（含直链与分组）
- `sources/urls.txt`：唯一事实来源的直链列表（批量下载入口）
- `scripts/sync_assets.py`：按直链下载并整理；生成 `manifest.csv`
- `manifest.csv`：每个文件的大小/sha256/状态/来源 URL（用于校验与交接）
- `INTEGRITY_REPORT.md`：完整性检查报告（缺失/大小不一致会在此暴露）
- `HANDOVER.md`：面向下一位接手者的流程说明与坑位

## 5. 为什么 `manifest.csv` 里会出现 `skip`（不是缺失）

本目录脚本默认“幂等”（重复运行不会重复下载/解压），所以会出现：

- `status_download=skip`：文件在 `raw/...` 已存在且非空，本次跳过重复下载。
- `status_extract=skip / skip_nonempty`：解压目录已存在（或目录非空），跳过重复解压。
- `status_extract=n/a`：不适用（例如非 zip；或 data/*.zip 默认不解压）。

如果你想强制重下某个文件：删除对应 `raw/...` 文件后重新运行同步脚本即可。

## 6. 引用与合规提醒（建议）

在论文中引用数据/代码时，建议至少同时给出：

- Battery Intelligence Lab “Data and code” 页面链接（见 `sources/data-and-code.md` 顶部的 URL Source）
- 对应 Oxford ORA 数据集的 object 页面链接（见 `download_list.md` / `sources/ora_*.html`）
- 若使用某个 GitHub 仓库代码/思路：引用仓库链接与访问日期（必要时附 commit/zip 的 sha256 可追溯）

提示：这些资源为研究级（research-grade），使用前应阅读各自许可与数据说明（ORA 的 `Readme.txt` / `Guide_to_Datafiles.pdf` 等）。

