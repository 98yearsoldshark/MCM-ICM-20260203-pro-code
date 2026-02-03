# 26A 并行开发指导（Q3 进行中）：给 Q1/Q2 工作者的影响判别表与工作边界

适用范围：`MCM_Sim/26A/src` 单一代码库同时支撑 Q1/Q2/Q3（赛题见 `MCM_Sim/26A/论文/赛题/A英文纯文本.md`）。

当前状态：我在推进 **Q3（Sensitivity and Assumptions）**：敏感性（Local/Global PRCC）、结构消融、老化扫描、随机波动统计与论文级图像。

目标：你可以让两位工作者并行推进 **Q1（电池端曲线/ECM 校准）** 与 **Q2（drivers/UQ/验证与策略）**，同时 **不破坏 Q3 的复现与口径**，尽量避免冲突与返工。

---

## 一句话规则（最重要）

1) **接口/返回结构/配置 schema 不要改**（会让 Q3 跑崩或口径静默漂移）。  
2) 需要试新想法时，优先 **新增文件**（新脚本/新配置/新 mech_id），不要覆盖旧文件。  
3) 输出目录按约定分层，避免互相覆盖：`out_plots/{model|q}/(paper|study)/主题/实验名/…`、`out_reports/{q}/…`。

---

## Q3 侧当前“冻结/锁定”文件（Q1/Q2 不要直接改）

这些文件是 Q3 主干，短期会频繁改动；他人请避免编辑，减少冲突：

- `MCM_Sim/26A/src/mcm26a/analysis/q3_sensitivity.py`
- `MCM_Sim/26A/src/mcm26a/viz/q3_plots.py`
- `MCM_Sim/26A/src/scripts/run_q3_report.py`
- `MCM_Sim/26A/src/scripts/make_q3_plots.py`

另外：我已把 `min_headroom_margin`（离“不可供电 Δ<0”边界的裕量指标）接入 Model-1/2/3 仿真结果结构；为避免接口冲突，以下文件也请暂勿改动：

- `MCM_Sim/26A/src/mcm26a/sim/model1.py`
- `MCM_Sim/26A/src/mcm26a/sim/model2.py`
- `MCM_Sim/26A/src/mcm26a/sim/model3.py`

---

## 影响判别表（Q1/Q2 改动对 Q3 的影响）

影响等级（面向 Q3）：
- 0：无影响（并行安全）
- 1：低影响（Q3 仍能跑，但数值口径会变；需记录变更并可能重跑 Q3）
- 2：中影响（Q3 结论/图可能需要重出；需提前通知）
- 3：高影响/阻断（可能直接让 Q3 报表/出图崩溃；必须先同步）

| 改动对象 | 典型文件/目录 | 对 Q3 影响 | 是否允许并行 | 规则（如何不影响 Q3） |
|---|---|---:|---|---|
| 新增“只读”脚本/实验 | `MCM_Sim/26A/src/scripts/*.py`（新增） | 0 | 允许 | 只新增；输出落新子目录 |
| 新增配置文件（推荐） | `MCM_Sim/26A/src/configs/*_q1exp_*.json`、`*_q2exp_*.json` | 1 | 允许 | 只新增不覆盖；脚本显式指向新配置 |
| 改 Q3 默认配置数值 | `configs/power_params_v1_stateful.json` / `phone_default_v3_aging.json` / `scenarios_v0.json` | 2 | 不建议 | 先复制再改；并在日志里记录“口径变更”，通知我重跑 Q3 |
| 改 Q2 UQ/Drivers 接口（Q3 复用） | `mcm26a/uq/q2_uq.py`、`mcm26a/analysis/q2_drivers.py` | 3 | 禁止（先同步） | 不重命名字段/函数/输出列；新增需保持向后兼容 |
| 改功耗 stateful 核心（Q2/Q3 共用） | `mcm26a/power/model1_stateful.py` | 3 | 禁止（先同步） | 可加开关/新机制，但默认行为与字段必须保持不变 |
| 改电池热/老化接口 schema | `mcm26a/battery/model3_aging.py` | 3 | 禁止（先同步） | `from_json()` 字段不可破坏；新增字段必须有默认值 |
| 改仿真主循环/终止条件/累计 | `mcm26a/sim/model*.py` | 3 | 禁止（先同步） | 这会改变 Q3 输出字段与口径；如必须改只能“新增字段且默认不变” |
| 改全局绘图风格 | `mcm26a/viz/style.py` | 2~3 | 不建议 | 会影响所有论文图一致性；需要先同步并全量冒烟测试 |

---

## 给 Q1 工作者：并行安全的工作边界（在我做 Q3 的同时）

### Q1 优先做（并行安全）
- 校准/拟合策略：`MCM_Sim/26A/src/mcm26a/calibration/**`、`MCM_Sim/26A/src/scripts/calibrate_*.py`
- 新增电池配置版本：`MCM_Sim/26A/src/configs/battery_calce_*_vX.json`（**只新增不覆盖**）
- 验证/画图脚本：`MCM_Sim/26A/src/scripts/validate_model1_*.py`

### Q1 禁区（不要碰）
- `MCM_Sim/26A/src/mcm26a/sim/model1.py`、`model2.py`、`model3.py`
- `MCM_Sim/26A/src/mcm26a/battery/model3_aging.py`
- `MCM_Sim/26A/src/mcm26a/power/model1_stateful.py`
- `MCM_Sim/26A/src/mcm26a/uq/q2_uq.py`、`MCM_Sim/26A/src/mcm26a/analysis/q2_drivers.py`
- `MCM_Sim/26A/src/configs/power_params_v1_stateful.json`

### Q1 输出要求（避免覆盖）
- 图：`MCM_Sim/26A/src/out_plots/model1/{paper|study}/validation/<数据集>/<配置名>/...`
- 报表：`MCM_Sim/26A/src/out_reports/validation/<数据集>/<配置名>.json|csv`

---

## 给 Q2 工作者：并行安全的工作边界（在我做 Q3 的同时）

### Q2 优先做（并行安全）
- 新增 Q2 实验脚本/验证脚本：`MCM_Sim/26A/src/scripts/validate_q2_*.py`（新增）  
- 新增 Q2 汇总/叙事产物：`MCM_Sim/26A/src/out_reports/q2/**`（新子目录）
- 如果要扩展 drivers：优先“新增 mech_id 或新增输出列”，不要重命名/删除既有内容

### Q2 需要特别小心（会影响 Q3）
- `MCM_Sim/26A/src/mcm26a/uq/q2_uq.py`：字段名/函数签名不要变（Q3 复用）
- `MCM_Sim/26A/src/mcm26a/analysis/q2_drivers.py`：`mech_id` 与接口不要破坏（Q3 复用）
- `MCM_Sim/26A/src/mcm26a/power/model1_stateful.py`：这是 Q2/Q3 共用底座（先同步再改）

---

## 最小自检（两位工作者每次阶段性保存后都跑）

1) 语法自检：
```bash
python -m compileall -q MCM_Sim/26A/src
```

2) Q1 自检（示例，按正在改的验证脚本挑一个即可）：
```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/validate_model1_ecm_on_calce_sp20_1_incremental_ocv.py
```

3) Q2 自检（示例，小参数跑通即可）：
```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/run_q2_report.py --dt 10 --uq-samples 5 --driver-seeds 5
```

4) 若有人“确实动到了共享核心”（不推荐），必须额外跑一次 Q3 冒烟：
```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/run_q3_report.py --dt 10 --replicates 4 --global-samples 30 --global-seeds-per-sample 2
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q3_plots.py --mode study
```

