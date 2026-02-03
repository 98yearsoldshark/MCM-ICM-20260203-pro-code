# PyBaMM（开源电池机理建模框架）交接包

本目录为 MCM 2026A 项目准备的 **PyBaMM 学习/上手/复现**材料，目标是让后续接手者在 30~60 分钟内：
- 明白 PyBaMM 是什么、能解决什么问题；
- 能跑通 4~5 个 demo（生成图与 CSV）；
- 知道如何把“手机功耗（W）时间序列”映射成 PyBaMM 的放电实验（Experiment）。

官方链接：
- 官网：https://www.pybamm.org/
- 代码：https://github.com/pybamm-team/PyBaMM

## 目录结构

- `docs/`：交接文档（概念 + API + cheat sheet + 与 26A 题的接口思路）
- `demos/`：可直接运行的最小示例（会写入 `outputs/`）
- `outputs/`：demo 运行产物（默认不建议纳入版本控制）

## 快速开始（推荐 Python 3.11）

在本目录创建独立虚拟环境（避免污染其它项目依赖）：

```bash
cd MCM_Sim/26A/Open-S/PyBaMM
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demos/run_all.py
```

备注：如果你用的是 Python 3.9/3.8，可能会因为 PyBaMM 版本的 `python_requires` 限制而无法安装；此时请换用 Python 3.10+（建议 3.11）。

如果你使用 conda：

```bash
cd MCM_Sim/26A/Open-S/PyBaMM
conda env create -f environment.yml
conda activate mcm26a-pybamm
python demos/run_all.py
```

## Demo 列表

- `demos/demo_00_env_check.py`：环境自检（Python / pybamm / casadi / numpy / matplotlib 版本），输出到 `outputs/demo_00_env_check.txt`
- `demos/demo_01_spm_basic.py`：最小放电仿真（SPM，1C 放电至截止电压），输出电压曲线 + CSV
- `demos/demo_02_cccv_cycle.py`：CCCV 充放电循环（演示 Experiment 字符串写法），输出电压/电流曲线 + CSV
- `demos/demo_03_phone_like_power_profile.py`：类“手机功耗”的分段功率（W）放电协议，输出功率/电压/电流曲线 + CSV
- `demos/demo_04_tte_vs_power.py`：扫功率（W）得到 TTE（time-to-empty，放电至截止电压），输出曲线 + CSV

所有 demo 的输出默认写到 `outputs/`。

## 常见问题（Troubleshooting）

- 安装失败（尤其是旧 Python）：优先用 `python3.11 -m venv ...` 或 `conda` 新建环境，并先 `pip install -U pip`。
- 首次 import 很慢/有网络请求：demo 已调用 `pybamm.telemetry.disable()`；你也可以在自己的脚本里同样调用一次（不影响计算结果）。
- 仿真太慢：先用 `SPM`（demo 默认如此）；`DFN` 更慢，建议只用于少量对照。

## 建议阅读顺序

1. `docs/00_overview.md`：PyBaMM 能做什么、与本题的关系
2. `docs/01_core_api.md`：PyBaMM 的 6 个核心对象（Model/Parameters/Experiment/Simulation/Solver/Solution）
3. `docs/02_experiment_cheatsheet.md`：Experiment 写法速查
4. `docs/03_mcm26a_mapping.md`：如何把“手机功耗（W）”接到 PyBaMM
5. `MCM26A_ROLE.md`：本目录如何对齐赛题要求、以及在论文中怎么用
