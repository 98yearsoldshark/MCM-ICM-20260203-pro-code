# 参量估计（Parameter Estimation）

本目录用于把“参量估计所需数据盘点”落地为可复现的：
- 数据抽取（CSV）
- 参数拟合（表格）
- 曲线绘制（paper/study 两版 PNG）
- 来源与处理步骤说明（about.md）

## 目录约定

每个子任务一个文件夹：

- `01-亮度-屏幕功耗/`
- `02-负载-CPU_GPU功耗/`
- `03-网络回落曲线/`
- `04-吞吐-功耗关系/`
- `05-温度-时间曲线/`

每个文件夹内默认包含：
- `figure_paper.png`：论文版（更简洁）
- `figure_study.png`：学习版（含方法/注释）
- `data.csv`：用于拟合/作图的“干净数据”
- `fit_results.csv`：拟合得到的参数与误差指标
- `about.md`：数据来源（精确到路径）+ 处理/拟合方法说明

根目录会生成：
- `参数估计汇总表.csv`：把各子任务的关键参数汇总成一张表，便于写论文与回填配置
- `参数估计汇总表.md`：同上（便于直接粘贴到论文）
- `paper_fragment_zh.md`：可直接插入论文的中文段落（含公式、图表引用与复现命令）

## 英文论文图（paper_en）

若需要英文论文版图片（坐标/标题为英文），可运行：

```bash
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/30_make_paper_figures_en.py"
```

将生成：
- `01-*/figure_paper_en.png`（01~05）

## 额外高价值图（extra，含中/英文）

为加强“证据链/可解释检验”，可额外生成一些当前目录中没有的补强图：

```bash
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/31_make_extra_figures_zh_en.py"
```

输出示例（每张都有中文与英文两版）：
- `03-网络回落曲线/extra01_tail_deltaP_vs_invT*.png`（尾态能量证据：ΔP≈E_tail/t）
- `03-网络回落曲线/extra02_energy_balance_1to1*.png`（能量守恒 1:1 检验）
- `05-温度-时间曲线/extra01_deltaT_1to1*.png`（热模型 1:1 检验）
- `05-温度-时间曲线/extra02_deltaT_norm_linearity*.png`（归一化线性检验）

## 如何复现

从仓库根目录执行（推荐）：

```bash
python3 "MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/scripts/00_run_all.py"
```

也可以单独运行某一项脚本（见 `scripts/` 目录）。

## 数据合规提示（务必在论文中说明）

- AndroWatts（Zenodo，CC BY 4.0）：可作为最终提交的公开数据来源（用于 01/02/04/05 的主结果）。
- SmartphoneMeasurements.zip：本仓库当前仅保留 zip 快照，zip 内未见 LICENSE；若用于最终提交，请回溯上游并确认许可证。
