# NASA-BatteryData（Li-ion 电池实验数据）

本目录用于存放/镜像 **NASA PCoE（Prognostics Center of Excellence）公开锂电池数据**，供 `MCM_Sim/26A` 的 **2026 MCM Problem A：Modeling Smartphone Battery Drain** 使用。

下载/整理时间：2026-01-30  
题面位置：`MCM_Sim/26A/论文/赛题/A中文纯文本.md`、`MCM_Sim/26A/论文/赛题/A英文纯文本.md`

交接与快速上手：
- 面向接手者的完整说明：`HANDOVER.md`（推荐先读）

## GitHub 版（不提交大文件）如何复现数据

本仓库准备提交到 GitHub 时，通常会在 `.gitignore` 中忽略本目录下的 GB 级数据文件。
克隆仓库后请运行同步脚本一键拉取：

```bash
python3 MCM_Sim/26A/data/NASA-BatteryData/scripts/sync_nasa_batterydata.py
```

脚本会：
- 下载 `5.+Battery+Data+Set.zip`；
- 下载并解压 `11.+Randomized+Battery+Usage+Data+Set.zip` 到本目录预期路径；
- 生成 `manifest.csv` 作为可追溯清单。

## 与本仓库其他说明文档的对应（补充下载链接/摘要）

本仓库曾有一个“电池相关数据集总览”文档对 NASA 数据集做过摘要说明；该总览已拆分进各目录 README 并删除以避免重复/过期信息。为避免信息分散，本 README 在此补充/对齐其中的关键条目（并以本目录实际内容为准）：

### 1) NASA 锂电池老化数据集（对应本目录：`5.+Battery+Data+Set.zip`）

- 数据集：NASA PCoE Battery Dataset / Battery Data Set（常用于容量衰减与 RUL 研究）
- 官方入口（下载/说明）：`https://ti.arc.nasa.gov/tech/dash/groups/pcoe-prognostic-data-repository/`
- 本地文件：`5.+Battery+Data+Set.zip`（约 200MB，压缩包内还有多层 zip 与 README）

常见数据特点（作为“快速认知”，论文写作或严谨建模以 zip 内 `README.txt` 为准）：
- 电池类型：常见为 18650 Li-ion 电芯（标称容量约 2Ah）
- 工况：充电/放电/阻抗谱（EIS）
- 衰减量级：容量从约 2Ah 下降到约 1.4Ah（约 30% 衰减）是常见案例
- 采样率：部分数据约 10Hz（不同子集可能不同）

常见引用（数据集说明中给出的引用之一）：
> B. Saha and K. Goebel (2007). "Battery Data Set", NASA Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA

### 2) “battery_alt_dataset.zip / Randomized and Recommissioned Battery Dataset” 的说明（本目录未镜像该 zip）

总览文档提到的 **battery_alt_dataset.zip**（Data.gov 页面、UCF Probabilistic Mechanics Lab）与本目录已镜像的 **NASA PCoE #11 Randomized Battery Usage Data Set** 并非同一份数据。

- 该数据集下载入口（信息保留，便于后续需要时自行补全/引用）：
  - Data.gov 页面：`https://data.nasa.gov/dataset/randomized-and-recommissioned-battery-dataset`
  - 通常需要从页面下载 `battery_alt_dataset.zip`（据描述为 CSV，体量约 500MB，含 26 个电池包）
- 引用（说明文档中给出的引用之一）：
> Fricke, K., Nascimento, R., Corbetta, M., Kulkarni, C., & Viana, F. "Accelerated Battery Life Testing Dataset", NASA Prognostics Data Repository, Probabilistic Mechanics Lab, University of Central Florida, and NASA Ames Research Center, Moffett Field, CA

如果你只需要“随机负载/随机工况”来验证连续时间 SOC/TTE 框架，本目录的 `11.+Randomized+Battery+Usage+Data+Set/`（已解压）通常已经足够；若你必须使用上述 `battery_alt_dataset.zip`，请按链接另行下载并在团队内约定存放位置（建议不要混入本目录，避免与 PCoE 数据混淆）。

## 本目录对赛题 A 的作用（为什么需要它）

赛题 A 要求建立 **连续时间（continuous-time）SOC 模型**，并在不同使用场景下预测 **TTE（time-to-empty）**。本目录的数据主要用来做“电池本体层”的支撑，而不是替代整机（屏幕/CPU/网络）功耗建模：

- **参数范围与可解释性**：用真实 Li-ion 实验数据约束 `dSOC/dt = -I(t)/Q_eff` 中的有效容量 `Q_eff`、电压范围（关机阈值/满电电压）、内阻/极化动态等参数量级。
- **随机负载/功率负载下的验证**：11 号数据集包含随机电流序列、以及“参考恒功率放电”步骤，可用于检验你的 TTE 推断是否合理（尤其当你用功率来驱动电池模型时）。
- **温度/老化效应**：数据包含室温与 40C 的实验、以及长时间循环导致容量衰减/内阻上升，可用于讨论“为什么同样使用强度下，有时掉电更快”（温度与老化是常见原因）。

重要提醒：这些数据来自 18650 等实验电芯，**不等同于手机整机电池**。它们用于支撑“电池动力学/老化/温度效应”的物理合理性；手机端负载（屏幕、基带、后台）仍需你单独建模。

## 目录结构

- `5.+Battery+Data+Set.zip`：NASA 经典 Battery Aging 数据（压缩包内还包含多个内层 zip）
- `11.+Randomized+Battery+Usage+Data+Set/`：NASA Randomized/Random Walk 使用数据（已解压，含 `.mat`/`.Rda` 与说明文档）

## 数据体积（参考）

```bash
du -sh MCM_Sim/26A/data/NASA-BatteryData
```

## 数据集内容概览（你会用到什么）

### 5. Battery Data Set（压缩包：`5.+Battery+Data+Set.zip`）

外层 zip 内的主要条目（内层 zip 文件名）：
- `1. BatteryAgingARC-FY08Q4.zip`
- `2. BatteryAgingARC_25_26_27_28_P1.zip`
- `3. BatteryAgingARC_25-44.zip`
- `4. BatteryAgingARC_45_46_47_48.zip`
- `5. BatteryAgingARC_49_50_51_52.zip`
- `6. BatteryAgingARC_53_54_55_56.zip`

典型内容（以 `1. BatteryAgingARC-FY08Q4.zip` 为例）：
- 电池编号：`B0005 / B0006 / B0007 / B0018`
- 每个 `.mat` 内部：顶层变量（同名，如 `B0005`），包含 `cycle` 数组；每个 cycle 有 `type`（charge/discharge/impedance）、温度、时间与测量数据。

用途建议：
- 做“容量衰减 vs 循环/时间”的量级估计（用于你的 `Q_eff(SoH)`）
- 讨论内阻/阻抗随老化变化（可作为等效电路/极化参数变化的证据）

### 11. Randomized Battery Usage Data Set（目录：`11.+Randomized+Battery+Usage+Data+Set/...`）

包含多个子实验（室温/40C、随机电流/随机放电等），每个子目录通常包含：
- `README_*.html` / `README_*.Rmd`：数据结构与实验流程说明（最重要）
- `data/Matlab/*.mat`：MATLAB v5 格式数据（Python 可用 `scipy.io.loadmat` 读取）
- `data/R/*.Rda`：R 格式数据

子实验目录（便于定位你要的数据）：
- `Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post/`
- `Battery_Uniform_Distribution_Variable_Charge_Room_Temp_DataSet_2Post/`
- `Battery_Uniform_Distribution_Charge_Discharge_DataSet_2Post/`
- `RW_Skewed_High_Room_Temp_DataSet_2Post/`
- `RW_Skewed_Low_Room_Temp_DataSet_2Post/`
- `RW_Skewed_High_40C_DataSet_2Post/`
- `RW_Skewed_Low_40C_DataSet_2Post/`

用途建议：
- 直接用于“随机负载下的 SOC/TTE 仿真与对比”（更贴近手机“忽高忽低”的使用行为）
- 利用“reference power discharge（恒功率放电）”步骤，把你的手机功耗建模与电池电压/SOC 模型对接

## Python 读取提示（最小示例）

读取 RW 数据（以 RW9 为例）：

```python
from scipy.io import loadmat

p = ("MCM_Sim/26A/data/NASA-BatteryData/"
     "11.+Randomized+Battery+Usage+Data+Set/11. Randomized Battery Usage Data Set/"
     "Battery_Uniform_Distribution_Charge_Discharge_DataSet_2Post/data/Matlab/RW9.mat")

mat = loadmat(p, squeeze_me=True, struct_as_record=False)
data = mat["data"]             # Matlab struct
steps = data.step              # numpy array of structs
first = steps[0]
print(first.comment, first.type)
print(first.relativeTime.shape, first.voltage.shape, first.current.shape)
```

注意事项：
- RW 的 `data.step` 数量可能非常大（十万级）。**不要一次性转成 DataFrame 再全量展开**，建议按需筛选 `comment`/`type` 后再处理。
- 5 号数据集在 zip 内有内层 zip；如果你不想解压到磁盘，可以用 Python 先抽取某个内层 zip/某个 `.mat` 再读取。

## 引用与许可（务必在论文中说明）

- 11 号数据集的 `README_*.Rmd` 明确给出了建议引用的论文（Bole/Kulkarni/Daigle, PHM Society 2014）。使用该数据集时建议按其 README 要求引用。
- 5 号数据集的详细字段定义在压缩包内各子 zip 的 `README.txt` 中；用于报告时建议说明数据来自 NASA PCoE 电池数据集，并在参考文献中给出数据仓库/说明文档来源。
