# 开源数据说明（中文）

本目录是论文 **“Power Efficiency Unpacked: Modeling Per-Component Power Consumption in Mobile Devices”** 的配套开源数据与代码归档（原始说明见 `README.txt`）。

> 注意：作者声明已尽力匿名化，但仍可能残留可识别作者身份的信息；如需公开传播请先自行审查与脱敏。

## GitHub 版（不提交大文件）如何复现

本目录中体积最大的两部分通常是：
- `material/trace_parser/`（perfetto trace + 解析工具）
- `material/application-android-conso-tel/`（复现实验安卓 app）

如果你准备把仓库整理到 GitHub，推荐只保留小文件（特别是 `material/res_test/aggregated.csv`），并在 `.gitignore` 中忽略上述大目录；需要时可通过脚本从 Zenodo 记录重新拉取：

```bash
python3 MCM_Sim/26A/data/open_data/scripts/sync_open_data_from_zenodo.py
```

提示：部分网络环境可能无法访问 Zenodo；此时请切换网络/VPN 或在可访问环境下运行。

## 与 MCM 2026 Problem A 的关系（数据来源 / 本项目用到的文件）

本目录对应 `MCM_Sim/26A/data/数据集/MCM2026_数据来源与说明文档.md` 中的 **数据源 A（手机功耗/设备状态）：AndroWatts 数据集（Zenodo）**：

- 用途：提供 1000 次移动设备组件刺激测试的聚合指标（设备状态 + 各组件/电源轨功耗指标）。
- Zenodo：`https://zenodo.org/records/14314943`
- DOI：`10.5281/zenodo.14314943`
- 许可：CC BY 4.0（以 Zenodo 记录为准；本目录自带 `README.txt` 中未包含许可证文本）

本项目实际用到的关键文件（对应说明文档第 2 节）：

- `material/res_test/aggregated.csv`：1000 条测试聚合指标（主输入）
- `README.txt`：原始英文说明
- `material/trace_parser/README.md`：列出从 perfetto trace 提取的指标列表（用于佐证字段来源）

与本仓库最终建模主表的关系（对应说明文档第 3.1/3.3 节）：

- `aggregated.csv` 的 `ID` 在主表中被重命名为 `phone_test_id`
- 单位换算：`AVG_SOC_TEMP`（m°C）→ `temp_c = AVG_SOC_TEMP/1000`；`BATTERY__PERCENT`（%）→ `soc0 = BATTERY__PERCENT/100`
- 电流尺度：`I_obs_A = BATTERY_DISCHARGE_RATE_UAS * 1e-6`
- 合计功耗：`P_total_uW = sum(all *_ENERGY_UW columns)`
- 合计能量代理：`E_total_uWh_est = sum(all *_ENERGY_AVG_UWS columns)`，并可与 `P_total_uW` 的比值近似估计测试时长 `duration_h_est`

## 这是什么数据？

这是一份用于**移动设备功耗建模/分组件功耗归因**的数据集与复现实验材料，主要包含三类内容：

1) **聚合后的结构化数据**：`material/res_test/aggregated.csv`  
   - 1000 条测试（行），每行对应一次实验运行的聚合统计。
   - 包含：屏幕/CPU/GPU/Wi‑Fi/温度/电量等状态特征，以及按“电源轨（power rail）/组件”统计的能耗指标。

2) **原始系统追踪（perfetto traces）与解析工具**：`material/trace_parser/`  
   - `trace_parser/in/traces/` 里是原始 perfetto trace（体积较大）。
   - `trace_parser/main.py` 用 Perfetto Python API 从 trace 里提取指标并输出 CSV。

3) **分析/建模脚本与已生成的结果表**：`material/analysis.py` + 若干 `*.csv`  
   - `analysis.py` 读取 `aggregated.csv`，做特征处理、模型训练/评估，并生成对比表（作者说明里提到“需要调参/调整”）。
   - `model_comparison.csv`、`grid_search_results.csv`、`per_component_accuracy.csv`、`size_comparison.csv` 是作者脚本产出的结果表（可直接查看）。

## 目录结构（关键信息）

```
open_data/
  README.txt                       # 原始英文说明
  README_zh.md                     # 本中文说明
  material/
    res_test/aggregated.csv        # 1000 次测试的聚合数据（核心）
    analysis.py                    # 建模/分析脚本（需要依赖与调整）
    model_comparison.csv           # 模型效果对比（表格结果）
    grid_search_results.csv        # 网格搜索结果
    per_component_accuracy.csv     # 分组件/分组预测准确度
    size_comparison.csv            # 样本量影响分析
    trace_parser/                  # perfetto trace 解析工具（含 README.md）
    application-android-conso-tel/ # 触发硬件负载的安卓应用源码（复现实验用）
```

## aggregated.csv 字段怎么理解？

文件路径：`material/res_test/aggregated.csv`

### 1) 基本显示相关
- `RougeMesuré`, `VertMesuré`, `BleuMesuré`：屏幕颜色（红/绿/蓝）水平（法语字段名；`analysis.py` 中被重命名为 `RedLvl/GreenLvl/BlueLvl`）。
- `Brightness`：屏幕亮度。

### 2) 分组件/电源轨能耗（两套列）
- `*_ENERGY_AVG_UWS`：按电源轨统计的能耗类指标（脚本里作为“组件能耗/ground truth”使用，并会对这些列求和）。
- `*_ENERGY_UW`：另一套同名指标（脚本里会整体丢弃 `rails_discard` 这批列）。

说明：
- `analysis.py` 中定义了 `rails = [...]`（即所有 `*_ENERGY_AVG_UWS` 列），并计算：
  - `sum_odpm = sum(rails)`（将各电源轨能耗求和）
- 部分列名带 `.1`（如 `Memory_ENERGY_AVG_UWS.1`），表示同名但不同来源/轨道的第二列；不要简单去重。

### 3) CPU/GPU 频率与网络等状态特征
- `CPU_LITTLE_FREQ_KHz`, `CPU_MID_FREQ_KHz`, `CPU_BIG_FREQ_KHz`：CPU 三个簇的平均频率（KHz）。
  - 注意：`CPU_MID_FREQ_KHz` 中存在字符串值 `err`（该列不是纯数值）；`analysis.py` 的做法是将 `err` 置为缺失后用中位数填充。
- `GPU0_FREQ`, `GPU_1FREQ`, `GPU_MEM_AVG`：GPU 相关频率/平均值。
- `TOTAL_DATA_WIFI_BYTES`：Wi‑Fi 总数据量（字节）。

### 4) 电池/温度
- `BATTERY_DISCHARGE_TOTAL_UA`：电池放电总量（单位见作者定义）。
- `BATTERY_DISCHARGE_RATE_UAS`：电池放电速率（单位见作者定义）。
  - `analysis.py` 里将其换算为能量：`Battery_discharge_uWs = BATTERY_DISCHARGE_RATE_UAS * 4.4`（4.4 为脚本常量）。
- `AVG_SOC_TEMP`, `DIFF_SOC_TEMP`：SoC 温度统计。
- `BATTERY__PERCENT`：电量百分比。

### 5) 其他字段
- `C_ID`, `C_PL`, `M_ID`, `M_PL`：作者实验/采集相关的附加特征字段（在 `analysis.py` 中会对其中部分 0 值做缺失填充处理）。

## 怎么用？（推荐三种用法）

### 用法 A：直接把 aggregated.csv 当作建模数据

常见任务：
- 预测整机能耗/电池放电能量（回归）
- 分组件（Display/CPU/GPU/网络等）能耗归因/预测

最小示例（读取 + 处理 `err` + 构造一个目标变量）：

```python
import numpy as np
import pandas as pd

df = pd.read_csv("material/res_test/aggregated.csv", index_col=0)

# 处理 CPU_MID_FREQ_KHz 的 'err'
df["CPU_MID_FREQ_KHz"] = pd.to_numeric(df["CPU_MID_FREQ_KHz"].replace("err", np.nan))
df["CPU_MID_FREQ_KHz"] = df["CPU_MID_FREQ_KHz"].fillna(df["CPU_MID_FREQ_KHz"].median())

# 按作者脚本构造电池放电能量目标（单位/系数来自原脚本）
df["Battery_discharge_uWs"] = df["BATTERY_DISCHARGE_RATE_UAS"] * 4.4
```

接下来你可以自行选择特征列（如亮度/颜色/频率/流量/温度等）训练回归模型。

### 用法 A（对 MCM 2026 A 的落地方式）：作为“手机侧功耗模型”的数据支撑

赛题要求的是**连续时间 SOC(t)** 模型，而不是离散回归。一个常见拆法是：

1) 用本数据集学习/验证：在给定手机状态特征 `x(t)`（亮度、CPU/GPU 频率、Wi‑Fi 流量、温度…）时，
   手机负载功耗（或能量消耗率）如何变化：`P_load(t) = f(x(t))`
2) 把 `P_load(t)` 接到电池连续时间模型：
   - 近似电流：`I(t) ≈ P_load(t) / V(t)`
   - SOC 动力学：`dSOC/dt = - I(t) / Q_eff`
   - `V(t)`、`Q_eff` 可来自你在 `src/` 中实现的 ECM/热/老化子模型（或其他机理模型）

因此，这份 open_data 更像是“手机用电侧（power demand）”的**公开测量证据**，用于支撑报告里对：
- 屏幕亮度/颜色对耗电的影响量级
- CPU/GPU 频率负载对耗电的影响量级
- 网络活动对耗电的影响量级
的论证与参数范围设定；而不是替代电池机理模型本身。

### 用法 B：直接查看作者已生成的结果表

这些文件无需跑脚本即可直接用：
- `material/model_comparison.csv`：多种模型的 MSE、R²、误差分位数等对比
- `material/grid_search_results.csv`：网格搜索最优参数与得分
- `material/per_component_accuracy.csv`：分组/分组件预测准确性统计
- `material/size_comparison.csv`：样本量变化对指标的影响

### 用法 C：从原始 perfetto trace 重新提取指标（trace_parser）

路径：`material/trace_parser/`（另有英文说明：`material/trace_parser/README.md`）

要点：
- 输入：perfetto trace 文件（`.perfetto-trace` 或 `.proto`）
- 输出：CSV（**如果目标 CSV 已存在会被清空重写**）
- `--slice` 只对“power rails”计算窗口生效，其他指标仍对全 trace 统计

示例（从本仓库自带 traces 解析）：

```bash
cd MCM_Sim/26A/data/open_data/material/trace_parser
mkdir -p out
python3 main.py --input ./in/traces --out ./out/out.csv --slice '[0:100]'
```

依赖：
- `perfetto`（Perfetto Trace Processor Python API）
- `protobuf`（脚本里用到 `google.protobuf`）

## 复现作者的 analysis.py（可选）

`analysis.py` 是研究代码风格脚本（非“开箱即用”包），建议按以下方式使用：

```bash
cd MCM_Sim/26A/data/open_data/material
python3 analysis.py
```

说明：
- 脚本使用相对路径读取 `./res_test/aggregated.csv`，所以建议在 `material/` 目录下运行。
- 依赖较多（如 `pandas/numpy/scikit-learn/scipy/matplotlib/seaborn/shap/xgboost` 等）。
- 脚本中包含部分 `exit()`、绘图与调参逻辑；如果你想完整复现论文表格，可能需要按你的环境/需求调整参数与输出逻辑。

## 可信度/可用性评估（基于本仓库内容的“合理猜测”）

结论（偏保守）：**可信度中等偏高，但“可迁移性/合规性”需要你额外确认。**

支持其可信的信号（加分项）：
- **来源明确**：目录 `README.txt` 指向具体论文标题，且文件内容与“移动设备分组件功耗建模”主题一致。
- **可追溯性强**：同时包含
  - 原始 trace（`material/trace_parser/in/traces`，体积很大）
  - trace 解析脚本（`material/trace_parser/main.py`）
  - 刺激硬件组件的安卓应用源码（`material/application-android-conso-tel`）
  这使得数据不是“只有一张表”，而是有原始数据与提取工具链。
- **内部一致性良好**（我们在本仓库数据上做过快速自检）：
  - 把所有 `*_ENERGY_AVG_UWS` 相加得到 `sum_odpm`，与 `BATTERY_DISCHARGE_RATE_UAS * 4.4` 的相关系数约 **0.97**（强相关），说明“组件能耗聚合量”和“电池放电能量 proxy”方向一致。
  - 所有 `ENERGY` 列无负值；除 `CPU_MID_FREQ_KHz` 含 `err` 外，其它列类型与取值范围较正常。

主要风险/注意事项（减分项）：
- **许可证信息不在压缩包内**：本目录未见 `LICENSE`/授权条款，但 Zenodo 记录标注许可为 **CC BY 4.0**（见 `MCM_Sim/26A/data/数据集/MCM2026_数据来源与说明文档.md`）。建议在最终报告中明确注明 Zenodo 记录号/DOI 与许可信息。
- **外推性有限**：很可能来自单一型号/单一固件/单一电池状态的实验数据，不能代表所有手机与所有电池老化状态。
- **实验构造偏“可控刺激”**：`application-android-conso-tel` 是专门刺激硬件的应用，数据可能更像“基准测试”而非真实用户混合行为。
- **单位/换算需谨慎**：脚本用常数 `4.4` 将放电量换为能量（可理解为固定电压近似）；若你在模型里用变电压 `V(SOC,T)`，需要解释该近似如何兼容。

## 快速自检（建议交接/搬运后跑一次）

从仓库根目录运行（只依赖 `pandas` + `numpy`）：

```bash
python3 - <<'PY'
import numpy as np
import pandas as pd

df = pd.read_csv("MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv", index_col=0)
rails = [c for c in df.columns if c.endswith("_ENERGY_AVG_UWS")]
sum_odpm = df[rails].sum(axis=1)
bat_uWs = df["BATTERY_DISCHARGE_RATE_UAS"] * 4.4

print("rows, cols:", df.shape)
print("rails:", len(rails))
print("CPU_MID_FREQ_KHz err count:", (df["CPU_MID_FREQ_KHz"] == "err").sum())
print("corr(sum_odpm, bat_uWs):", float(pd.Series(sum_odpm).corr(pd.Series(bat_uWs))))
PY
```
