# MCM 2026 Problem A - 数据集（派生表）

本目录存放 **MCM 2026 A 题（手机电池耗电建模）** 的派生数据表与说明文档：将“手机侧功耗/设备状态（AndroWatts）”与“电池侧老化参数（Mendeley）”按固定规则处理并拼接，供建模与复现使用。

更完整的来源、变量定义与预处理细节请阅读：

- `MCM2026_数据来源与说明文档.md`（同目录）
- `MCM2026_数据来源与说明文档.docx`（同目录）

## 数据来源（原始目录在本仓库中的位置）

- 数据源 A：AndroWatts（Zenodo）→ `MCM_Sim/26A/data/open_data/`
- 数据源 B：Battery Degradation Datasets (Two Types of Lithium-ion Batteries)（Mendeley Data）→ `MCM_Sim/26A/data/Battery Degradation Datasets (Two Types of Lithium-ion Batteries)/`

## 本目录文件说明

- `MCM2026A题锂电池数据表：master_modeling_table.csv`
  - 说明文档中称为：`MCM2026_master_modeling_table.csv`（本仓库实际文件名不同，但指同一张主表）
  - 规模：36000 行 × 93 列
  - 含义：1000 条手机功耗测试 × 36 个电池老化状态 的笛卡尔积拼接结果
  - 推荐主键：`(phone_test_id, battery_state_id)`
  - GitHub 版建议：**不提交该大文件**，用脚本重建（见下文）

- `MCM2026_battery_state_table.csv`
  - 规模：36 行 × 15 列
  - 含义：从 Mendeley 两份 Excel 中抽取 6 档老化状态（每个 cell 6 档）并拟合 OCV(SOC) 多项式后的电池参数表

- `锂电池数据集：变量字典.csv`
  - 说明文档中称为：`MCM2026_data_dictionary.csv`
  - 含义：主表各字段的单位、含义、来源、预处理说明（5 列：`variable/unit/description/source/preprocessing`）

- `MCM2026_数据来源与说明文档.md` / `MCM2026_数据来源与说明文档.docx`
  - 含义：数据来源、预处理、拼接规则与主表结构说明

## GitHub 版（不提交主表）如何复现

主表属于“派生表”，可以从两份更小的输入表按固定规则重建，因此推荐：
- GitHub 仓库中忽略 `MCM2026A题锂电池数据表：master_modeling_table.csv`；
- 需要时在本地运行脚本重建（并生成一个 manifest 便于追溯）。

运行方式：

```bash
python3 MCM_Sim/26A/data/MCM2026_battery_state_table/scripts/build_master_modeling_table.py --sample-check
```

默认输入：
- `MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
- `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026_battery_state_table.csv`

默认输出：
- `MCM_Sim/26A/data/MCM2026_battery_state_table/MCM2026A题锂电池数据表：master_modeling_table.csv`
- `MCM_Sim/26A/data/MCM2026_battery_state_table/manifest_master_table.csv`

## 主表结构要点（用于快速上手）

说明文档给出的主表构造规则：

- 手机侧（AndroWatts）`aggregated.csv`：1000 条测试（`phone_test_id`）
- 电池侧（Mendeley）电池状态：36 个（`battery_state_id`）
- 两侧无共同主键，因此做场景组合（笛卡尔积）得到 36000 行

主表里常用的关键字段（名称/含义以变量字典为准）：

- `phone_test_id`：手机功耗测试编号（由 AndroWatts 的 `ID` 重命名）
- `battery_state_id`：电池状态 ID（数据集/电芯/老化档位组合）
- `Q_full_Ah`：满充容量（Ah）
- `SOH`：容量健康度（相对新电池）
- `Q_eff_C`：有效电荷量（`Q_full_Ah * 3600`）
- `soc0`：初始 SOC（`BATTERY__PERCENT/100`）
- `temp_c`：平均 SOC 温度（`AVG_SOC_TEMP/1000`）
- `I_obs_A`：观测电流尺度（`BATTERY_DISCHARGE_RATE_UAS * 1e-6`）
- `P_total_uW`：合计功耗（`sum(*_ENERGY_UW)`）
- `ocv_c0` ~ `ocv_c5`：OCV(SOC) 五次多项式拟合系数

额外派生列（用于连续时间 SOC 近似初始化）：

- `dSOC_dt_est_per_s ≈ -I_obs_A / Q_eff_C`
- `t_empty_h_est ≈ soc0 / (-dSOC/dt) / 3600`（常流近似）
