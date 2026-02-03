# 26A 数据目录说明（面向 2026 MCM Problem A：Modeling Smartphone Battery Drain）

题面位置：`MCM_Sim/26A/论文/赛题/A英文纯文本.md`（以及对应中文译文）。

本题强调：**必须建立连续时间（continuous-time）的机理/机制模型**来输出 `SOC(t)` 并预测 `TTE(Time-to-Empty)`；数据只能用于**参数估计与验证**，不能用离散曲线拟合/黑盒回归替代模型。

因此本目录的资源被组织为两条主线：

- **手机侧（负载层）**：为 `P_load(t)`/`I(t)` 的量级、分解、场景设定提供公开证据；
- **电池侧（电芯层）**：为 `OCV(SOC)`、内阻/极化动态、温度/老化等提供公开实验数据锚点，用于参数辨识与独立验证。

---

## GitHub 版仓库：如何“只提交脚本，不提交大数据”

为便于把项目整理到 GitHub，本仓库建议：
- 在 `.gitignore` 中忽略 GB 级数据（例如 CALCE/NASA/BatteryArchive/BIL 的 raw/extracted）；  
- 只提交：脚本、README、清单（download_list/manifest）、以及我们自己生成的派生表格；  
- 克隆仓库后通过脚本一键拉取数据。

总入口（推荐）：

```bash
PYTHONPATH=MCM_Sim/26A/src python3 MCM_Sim/26A/src/scripts/fetch_data.py --profile core
```

说明：
- `--profile core` 会拉取 Q1/Q2/Q3 常用的三类数据：CALCE + NASA + SmartphoneMeasurements；  
- 只想拉某一类数据也可用 `--profile q1/q2/q3`；完整拉取用 `--profile all`（耗时/占空间都更大）。

各数据源也可单独运行其目录下的同步脚本（例如 `calce-umd/scripts/sync_calce_umd.py`、`NASA-BatteryData/scripts/sync_nasa_batterydata.py`）。

脚本索引总览：`MCM_Sim/26A/data/SYNC_GUIDE.md`。

---

## 快速上手：哪些数据“必用”，哪些“可选”

### A. 建议优先用（最贴近题面、已能直接支撑主线）

- `open_data/`：AndroWatts（Zenodo，手机侧功耗/状态测量证据）
  - 直接可用核心：`open_data/material/res_test/aggregated.csv`
- `MCM2026_battery_state_table/`：派生表（AndroWatts × Mendeley 老化状态）
  - 直接可用核心：
    - `MCM2026A题锂电池数据表：master_modeling_table.csv`（主表）
    - `MCM2026_battery_state_table.csv`（老化状态表）
    - `锂电池数据集：变量字典.csv`（字段字典）
- `calce-umd/`：CALCE（UMD）电池数据镜像（电池侧：OCV/动态响应/阻抗等）
  - 当前模型/脚本最常用：`calce-umd/extracted/battery-data/SP/`（SP20-1 的 Channel_*.xlsx）
- `Battery Degradation Datasets (Two Types of Lithium-ion Batteries)/`：Mendeley（CC BY 4.0，电池老化/容量衰减）
  - 用于构造 `SOH/Q_eff/OCV(SOC)` 的老化敏感性与参数来源（也被用于生成派生表）

### B. 可选增强（不用也能完成题面，但可提升论证/扩展性）

- `01-SOC_SOH/`：SOC/SOH 诊断与 OCV 曲线（fresh vs aged 成对实验数据）
  - 用途：把 `OCV(SOC)` 与 `SOH→容量衰减/内阻增长` 的敏感性范围“锚定到公开实验”，强化题目对“历史/老化”的要求（特别适合 Q3/Q4）。
  - 入口：见 `01-SOC_SOH/README.md` 与 `01-SOC_SOH/USAGE_IN_MCM_26A.md`（交接文档）
- `SmartphoneMeasurements/`：手机侧补充（网络功耗实测 + 用户行为统计）
  - 用于给 `P_network(t)`、轻/中/重度用户范围提供额外佐证
- `NASA-BatteryData/`：NASA PCoE（通用电芯老化/随机负载数据）
  - 用于“额外验证”：随机电流/温度/老化下的 `SOC/V/TTE` 框架检验
- `Battery-Archive/`：BatteryArchive.org 导出（通用电芯循环/破坏测试）
  - 用于“参数范围/老化趋势/电压曲线”补充证据（不等同手机整机）
- `Battery-Intelligence-Lab/`：Battery Intelligence Lab（Models + Oxford ORA 数据）
  - 更偏“研究级方法/代码参考”，用于提升方法段落可信度与可复现性

### C. 明显冗余/临时

- `temp/`：临时文件（当前仅含重复说明文本）
- `.DS_Store`：系统文件（可忽略）

---

## 目录逐项说明（用途 / 你会用到哪部分）

### 1) `open_data/`（AndroWatts：手机侧功耗/状态，Zenodo）

定位：为手机负载层提供“可引用的公开测量证据”，用于构造或校验 `P_load(t)` 的量级与分解（屏幕/CPU/GPU/网络等）。

你最可能用到：

- `open_data/material/res_test/aggregated.csv`：1000 次测试的聚合指标（主输入）
- `open_data/README_zh.md`、`open_data/README.txt`：来源与字段说明

通常不必用到（除非要追溯到最原始 trace 并重新提取指标）：

- `open_data/material/trace_parser/in/`：原始 perfetto traces（体积大）
- `open_data/material/application-android-conso-tel/`：刺激硬件组件的安卓 app 源码
- `open_data/material/analysis.py` 与作者生成的对比表：用于复现实验论文结果，非赛题刚需

注意：`README.txt` 提醒“已匿名化但可能残留可识别信息”；若你要公开发布仓库或附录，请自行审查脱敏。

### 2) `MCM2026_battery_state_table/`（派生表：主表/状态表/变量字典）

定位：把“手机侧 1000 条聚合测试”与“电池侧 36 个老化状态”做场景组合（笛卡尔积），便于快速做：

- 场景仿真（不同初始 SOC、温度、老化档位、使用强度）
- 敏感性分析（亮度/网络/后台负载变化对 TTE 的影响）
- 建议输出（哪些因素最影响续航）

建议先读：

- `MCM2026_数据来源与说明文档.md`：来源/单位换算/拼接规则（最关键）
- `README.md`：本目录文件索引

提示：该目录是“派生数据表”，它可以帮助你快速跑通端到端的 `SOC(t)/TTE` 框架；但题面强调机理模型，论文里仍应说明这些表并非黑盒拟合结果，而是来源明确、带规则的组合与派生特征。

### 3) `calce-umd/`（UMD CALCE：电池侧 OCV/动态/阻抗/老化）

定位：为“电池电学子模型（OCV/ECM/松弛/内阻/温度）”提供公开实验数据锚点，用于：

- 参数估计（例如 OCV 曲线、R0/R1/C1 等）
- 独立验证（给定 `I(t)`，能否解释 `V(t)` 的脉冲压降与休止恢复）
- 温度/老化扩展（可选）

建议先读：

- `calce-umd/FOR_MCM26A.md`：该目录如何映射到赛题 A（推荐阅读顺序）
- `calce-umd/README.md`：目录结构与复现方式

你最可能用到：

- `calce-umd/extracted/battery-data/SP/`：SP 系列（我们目前用 SP20-1 作为电压验证集）

可选扩展（体积大，按需启用）：

- `calce-umd/raw/storage/`：温度/存储期下阻抗变化（支撑“冷天续航下降”论证）
- `calce-umd/raw/accelerated/`、`calce-umd/raw/anomaly/`：加速老化/异常电池（支撑“历史/健康状态”扩展）
- `calce-umd/raw/battery-data/{A123,CS2,CX2}/`：其他电芯体系（用于泛化展示/对比，不是手机主线刚需）

### 4) `Battery Degradation Datasets (Two Types of Lithium-ion Batteries)/`（Mendeley：老化/容量衰减）

定位：用公开老化数据提供 `Q_eff(SOH)` 的量级证据，并从 Q-V 曲线派生 `OCV(SOC)`（或其多项式近似），支撑题面要求的“history/aging”讨论与敏感性分析。

许可证与引用：见该目录 `README.md`（DOI 与 CC BY 4.0）。

### 5) `SmartphoneMeasurements/`（手机侧补充）

定位：提供网络（WiFi/LTE/Bluetooth 等）功耗测量与用户行为统计，用于“场景参数范围”和“网络功耗量级”佐证。

建议先读：

- `SmartphoneMeasurements/FOR_MCM26A.md`
- `SmartphoneMeasurements/README.md`

注意：部分 zip 上游仓库未附 LICENSE 文件；论文引用时务必回溯上游并注明来源/访问日期。

### 6) `NASA-BatteryData/`（NASA PCoE：通用电芯数据）

定位：通用电芯层的老化/随机负载验证素材；适合在论文里做“额外验证”或“温度/老化的可迁移性示例”。

建议先读：`NASA-BatteryData/README.md`（含数据集结构与引用提示）。

### 7) `Battery-Archive/`（BatteryArchive.org 导出）

定位：通用电芯循环/效率/电压曲线（以及破坏测试）数据，主要用于“参数范围/趋势”补充证据。

建议先读：

- `Battery-Archive/README.md`
- `Battery-Archive/交接说明.md`

### 8) `Battery-Intelligence-Lab/`（Models + Oxford ORA 数据）

定位：方法与实现参考（参数辨识/退化/温度估计等）+ ORA 数据集；更适合增强“方法可信度/可复现性”，不是手机主线数据。

建议先读：

- `Battery-Intelligence-Lab/FOR_MCM26A.md`
- `Battery-Intelligence-Lab/README.md`

---

## 搬运/复现实用提醒

1) **开源许可要求**  
题面要求“数据必须有清晰文档且开源许可可用”。本仓库各子目录 README 已尽量记录 DOI/URL/许可；写论文时建议：

- 在参考文献中给出 DOI/URL + 访问日期；
- 在“数据与方法”中明确：数据用于参数估计与验证，而非替代连续时间机理模型。

2) **路径问题（重要）**  
当前 `src/configs/*.json` 里可能包含**绝对路径**（例如指向 `calce-umd/extracted/...xlsx`）。若你移动仓库位置：

- 建议重新运行 `src/scripts/` 中的校准/验证脚本生成新配置，或
- 手工把配置里的路径改为相对路径。

3) **优先保持“可追溯性”**  
如果你要删减体积，建议优先保留每个数据源目录下的：

- `README.md` / `FOR_MCM26A.md` / `HANDOVER.md`
- `download_list.md` / `manifest.csv` / `INTEGRITY_REPORT.md`

它们是你写作时最容易引用、也最能证明“数据可复现/可追溯”的材料。
