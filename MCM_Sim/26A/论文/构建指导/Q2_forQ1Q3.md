# 26A 并行开发指导（Q2 进行中）：给 Q1/Q3 工作者的影响判别表与工作边界

适用范围：`MCM_Sim/26A/src` 单一代码库同时支撑 Q1/Q2/Q3（赛题见 `MCM_Sim/26A/论文/赛题/A英文纯文本.md`）。

当前假设：Q2 工作者正在推进 **Q2（TTE + 不确定性 + drivers + 观测对照 + 策略）**；与此同时，你希望 Q1（电池端）与 Q3（敏感性/假设）能并行推进，但**不要影响 Q2 的复现与结果口径**。

目标：明确“哪些改动会改变 Q2 数值结论/导致脚本崩溃”，以及 Q1/Q3 应如何工作才能并行安全。

---

## 一句话规则（最重要）

1) **Q2 的共享核心（功耗 stateful / UQ 采样结构 / drivers 接口）不要改**。  
2) 需要试新想法，优先 **新增文件/新增开关/新增配置版本**，保持默认行为不变。  
3) 任何会影响 Q2 口径的改动，都必须：写清楚变更点 + 让 Q2 工作者重跑报表/出图。

---

## Q2 侧当前“冻结/锁定”文件（Q1/Q3 不要直接改）

这些文件是 Q2 的底座，改动会直接改变 TTE/UQ/drivers 结果，甚至让脚本崩溃：

### 1) 功耗模型（Q2 的核心）
- `MCM_Sim/26A/src/mcm26a/power/model1_stateful.py`
- `MCM_Sim/26A/src/configs/power_params_v1_stateful.json`

### 2) 不确定性与参数空间（Q2/Q3 共用）
- `MCM_Sim/26A/src/mcm26a/uq/q2_uq.py`（尤其是 `Q2UQSample` 字段名与 `apply_q2_uq_sample()`）

### 3) drivers 机制/组件消融接口（Q2/Q3 共用）
- `MCM_Sim/26A/src/mcm26a/analysis/q2_drivers.py`（尤其是 `mech_id`、输出列名、函数签名）

### 4) 场景口径与默认输入（影响 Q2 所有结论）
- `MCM_Sim/26A/src/configs/scenarios_v0.json`

### 5) Q2 主要出图/报表脚本（不建议并行改）
- `MCM_Sim/26A/src/scripts/run_q2_report.py`
- `MCM_Sim/26A/src/scripts/make_q2_plots.py`
- `MCM_Sim/26A/src/mcm26a/viz/q2_plots.py`

---

## 影响判别表（Q1/Q3 改动对 Q2 的影响）

影响等级（面向 Q2）：
- 0：无影响（并行安全）
- 1：低影响（Q2 能跑但数值会变；需记录并重跑）
- 2：中影响（Q2 结论/图大概率变化；需同步）
- 3：高影响/阻断（可能直接让 Q2 崩溃或“结果不可比”；必须先同步）

| 改动对象 | 典型文件/目录 | 对 Q2 影响 | 是否允许并行 | 规则（如何不影响 Q2） |
|---|---|---:|---|---|
| 论文写作/叙事整理 | `MCM_Sim/26A/论文/**` | 0 | 允许 | 纯文档可并行，但避免覆盖同一段落 |
| 新增只读脚本/实验 | `MCM_Sim/26A/src/scripts/*.py`（新增） | 0 | 允许 | 只新增；不要改 Q2 主脚本；输出落新子目录 |
| 新增配置文件（推荐方式） | `MCM_Sim/26A/src/configs/*_q1exp_*.json`、`*_q3exp_*.json` | 1 | 允许 | 只新增不覆盖；让脚本显式指向新配置 |
| 改 Q2 默认功耗/场景配置 | `configs/power_params_v1_stateful.json`、`configs/scenarios_v0.json` | 2~3 | 不允许（先同步） | 必须复制成新文件；并由 Q2 工作者确认是否升级口径 |
| 改 Q2 UQ/Drivers 接口 | `mcm26a/uq/q2_uq.py`、`mcm26a/analysis/q2_drivers.py` | 3 | 不允许（先同步） | 禁止重命名字段/函数；新增必须向后兼容 |
| 改电池 Model-3 热/老化（会影响 TTE 与终止原因） | `mcm26a/battery/model3_aging.py`、`mcm26a/sim/model3.py` | 2~3 | 不允许（先同步） | 若要研究：请用新参数开关/新模型文件，默认行为保持不变 |
| 改全局绘图风格 | `mcm26a/viz/style.py` | 2 | 不建议 | 会影响所有 Q2 论文图一致性，需要同步 |

---

## 给 Q1 工作者：如何在不影响 Q2 的前提下工作

Q1 允许做（并行安全）：
- 只在 **电池端**迭代：`MCM_Sim/26A/src/mcm26a/calibration/**`、`MCM_Sim/26A/src/scripts/calibrate_*.py`
- 新增电池配置版本：`MCM_Sim/26A/src/configs/battery_calce_*_vX.json`（只新增不覆盖）
- 电压验证出图：输出到 `out_plots/model1/**` 与 `out_reports/validation/**`

Q1 禁区（会影响 Q2）：
- 不要改功耗 stateful：`mcm26a/power/model1_stateful.py`、`configs/power_params_v1_stateful.json`
- 不要改 Q2 参数空间/接口：`mcm26a/uq/q2_uq.py`、`mcm26a/analysis/q2_drivers.py`
- 不要改 `configs/scenarios_v0.json`

---

## 给 Q3 工作者：如何在不影响 Q2 的前提下工作

Q3 允许做（并行安全）：
- 只在 Q3 新模块里扩展输出/敏感性/可视化：`mcm26a/analysis/q3_*`、`mcm26a/viz/q3_*`、`scripts/run_q3_*`
- 如需新指标：优先在 Q3 的报表层“派生计算”，不要动 Q2 的核心表结构

Q3 禁区（会影响 Q2）：
- 不要改 `mcm26a/power/model1_stateful.py` 与 `configs/power_params_v1_stateful.json`
- 不要改 `mcm26a/uq/q2_uq.py`、`mcm26a/analysis/q2_drivers.py` 的既有字段与接口
- 不要改 `configs/scenarios_v0.json`（若要扩展，复制成 `scenarios_q3exp_*.json`）

---

## 最小自检（Q1/Q3 每次阶段性保存后都应跑）

1) 语法自检：
```bash
python -m compileall -q MCM_Sim/26A/src
```

2) Q2 冒烟（保证没破坏 Q2，建议小参数）：
```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/run_q2_report.py --dt 10 --uq-samples 5 --driver-seeds 5
```

