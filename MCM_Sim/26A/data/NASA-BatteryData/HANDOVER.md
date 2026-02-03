# 交接说明：NASA-BatteryData（for MCM 2026 Problem A）

本文件面向“下一位接手者”，用于快速理解本目录的目的、内容结构、数据结构要点，以及如何把这些数据用在 `MCM_Sim/26A` 的赛题 A（手机电池耗电建模）中，并避免在团队内重复存储同一份 NASA 数据。

## 0. 这是什么（范围界定）

本目录的职责是：
- 作为 **NASA PCoE 公开电池数据**的本地镜像（尽量保持“原样”）
- 为赛题 A 提供“电池本体层（SOC/电压/温度/老化）”的可追溯数据支撑
- 让团队在写作时能回答：**我们用的是什么数据？字段是什么？能支持哪部分论证？**

本目录不直接解决：
- 手机端“功耗来源”（屏幕/CPU/网络/后台）的统计建模与参数采集（那部分通常来自手机规格、公开测量、或自采数据）

## 1. 目录结构（必须掌握）

- `README.md`：快速说明（入口）
- `HANDOVER.md`：交接说明（本文件）
- `5.+Battery+Data+Set.zip`：
  - 典型 Battery Aging + EIS（阻抗）数据；外层 zip 内包含多个内层 zip
  - 内层 zip 内含 `.mat` 与 `README.txt`（字段定义以 `README.txt` 为准）
- `11.+Randomized+Battery+Usage+Data+Set/`：
  - Random Walk / Randomized usage 数据（已解压）
  - 每个子目录都有 `README_*.html` / `README_*.Rmd`（强烈建议优先阅读）
  - 数据在 `data/Matlab/*.mat` 与 `data/R/*.Rda`

11 号数据集的子实验目录（常用入口）：
- 室温：`Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post/`（均匀分布随机放电）
- 室温：`Battery_Uniform_Distribution_Variable_Charge_Room_Temp_DataSet_2Post/`（均匀分布随机放电 + 变充电）
- 室温：`Battery_Uniform_Distribution_Charge_Discharge_DataSet_2Post/`（均匀分布随机充放电）
- 室温：`RW_Skewed_High_Room_Temp_DataSet_2Post/`（偏向大电流的随机放电）
- 室温：`RW_Skewed_Low_Room_Temp_DataSet_2Post/`（偏向小电流的随机放电）
- 40C：`RW_Skewed_High_40C_DataSet_2Post/`（偏向大电流的随机放电，含 reference power discharge 等步骤）
- 40C：`RW_Skewed_Low_40C_DataSet_2Post/`（偏向小电流的随机放电）

建议的“先读哪些说明文档”（每个子实验目录下）：
- `README_*.Rmd`：字段/流程说明（更易复制到论文引用）
- `README_*.html`：同内容的渲染版（更易阅读）

## 2. 对赛题 A 的“可用点”映射（怎么把数据写进论文）

题面要求见：`MCM_Sim/26A/论文/赛题/A中文纯文本.md`。

你可以把 NASA 数据用于以下写作/建模位置（建议在论文中明确“数据用于参数估计/合理性校验，而非黑盒拟合”）：

1) **连续时间 SOC 方程的参数量级**
- 用数据中的 `current(t)` 与 `Capacity(Ah)`（或对电流积分）说明：在 Li-ion 电池上，`dSOC/dt = -I/Q_eff` 的量纲、量级是合理的。
- 把 `Q_eff` 设为可随温度/老化变化的参数（例如 `Q_eff = Q0 * f_T(T) * f_SoH(SoH)`），并用实验数据中的容量衰减作为支撑。

2) **电压-电流-温度关系（把“电池本体”从 SOC 方程扩展到可观测量）**
- 题面只强制 SOC(t) 连续时间模型；但为了把手机“功耗”落到电池端，经常需要一个电压模型：
  - 最简：`V(t) ≈ OCV(SOC) - I(t)R`
  - 更真实：加 1~2 个 RC 极化支路（连续时间状态方程）
- NASA 的电压/电流/温度曲线可以用来证明：在随机负载下存在明显瞬态与恢复过程，支持使用 RC 极化状态（而不是纯 OCV 或纯拟合曲线）。

3) **TTE（time-to-empty）预测的合理性验证**
- 11 号数据集包含“随机电流序列 + 参考循环”，并在部分实验中包含 **reference power discharge（恒功率放电）**：
  - 这与手机“以功耗驱动电池”很接近：`P_load(t)` -> `I(t) = P_load(t)/V(t)`
  - 你可以用恒功率放电来对比：在同样的功率下，老化/温度变化会如何缩短可用时间。

4) **敏感性分析（温度/老化/负载分布）**
- 11 号数据集包含室温与 40C、以及“偏向大电流/偏向小电流”的随机负载分布，可直接用来说明：
  - 同样平均功率（或平均电流），负载波动与高峰值电流会加剧电压下垂与有效可用容量损失（对“掉电快”解释有帮助）
  - 温度升高/降低会改变内阻与容量（具体趋势以你模型假设+数据观测为准）

## 3. 数据结构速查（非常实用）

### 3.1 5. Battery Data Set（`5.+Battery+Data+Set.zip` 内）

以 `B0005.mat` 为例：
- 顶层变量名通常与文件名一致（如 `B0005`）
- `B0005.cycle`：包含多个循环（charge/discharge/impedance）
- 每个 cycle 常见字段：
  - `type`：`charge` / `discharge` / `impedance`
  - `ambient_temperature`：环境温度（C）
  - `time`：cycle 开始时间（MATLAB date vector）
  - `data`：测量数据结构（随 `type` 不同字段略有差异）

字段的权威定义来自各内层 zip 自带的 `README.txt`（论文引用时也建议提及该说明文档）。

### 3.2 11. Randomized Battery Usage Data Set（已解压目录内）

以 `RW9.mat` 为例：
- `.mat` 内有 `data` 结构体（Matlab struct）
- `data.step`：step 数组；每个 step 常见字段：
  - `comment`：本 step 的语义标签（例如 reference charge / reference discharge / random walk discharge / rest 等）
  - `type`：`C`（充电）/ `D`（放电）/ `R`（休息）
  - `relativeTime`：相对本 step 的时间（s）
  - `time`：相对实验开始的时间（s）
  - `voltage`（V）、`current`（A）、`temperature`（C）、`date`

不同子实验目录的 `README_*.Rmd/html` 会说明：
- 电流符号约定（有的实验里“负电流=充电、正电流=放电”）
- 随机电流的取值集合、持续时间（1min/5min）、温度条件、参考循环频率等

## 4. 推荐工作流（避免污染原始数据）

1) **保持本目录“只读心态”**
- 尽量不要在本目录里生成大量中间产物（CSV、图、缓存），避免后续误删/误提交。

2) **中间产物建议放到临时/工作目录**
- 若项目已有约定目录：优先遵循团队约定。
- 如果没有约定：建议使用类似 `mcm_temp/`（仓库里已有该目录）或新建 `MCM_Sim/26A/work/` 来存放：
  - 解析后的 CSV
  - 提取的特征（容量曲线、OCV-SOC 曲线、等效电路参数）
  - 绘图与表格

3) **只抽取“你需要的那一小部分”**
- 11 号数据的 `data.step` 很大（十万级很常见）。建议先按 `comment/type` 过滤，再做积分/拟合。
- 5 号数据集是“外层 zip + 内层 zip”；如果只是验证字段/曲线，没必要全量解压。

## 5. Python 解析注意事项（踩坑提示）

- **MATLAB v5**：本目录内 `.mat` 多为 Matlab v5（`scipy.io.loadmat` 可直接读）。
- **大数组与内存**：RW 数据 step 数量巨大；尽量使用“流式/按索引筛选”，避免一步展开成超大表。
- **电流符号**：务必以对应子目录的 README 为准，不要想当然。
- **TTE 的阈值**：数据里常用的截止电压（例如 3.2V/2.7V/2.5V）不等于手机关机阈值；写作时需要解释“我们如何把实验截止阈值映射到手机端”。
- **功率驱动时的隐式耦合**：若用 `I(t)=P(t)/V(t)`，而 `V` 又依赖 `I` 与 `SOC`，会出现隐式耦合；建议在报告中说明你的求解策略（近似/迭代/DAE 处理等）。

## 6. 与仓库其他数据目录的关系（避免重复）

同一类 Li-ion 数据在仓库中可能还会出现于：
- `MCM_Sim/26A/data/Battery-Archive/`
- `MCM_Sim/26A/data/Battery-Intelligence-Lab/`（更多是索引与外部链接/下载镜像）
- `MCM_Sim/26A/data/calce-umd/`

建议团队约定：
- **NASA 数据以本目录为准**（不要在多个地方再复制一份“解压后的 NASA 数据”）
- 若确需“恒温筛选版/重命名版”，放在 `mcm_temp/` 或单独目录，并在其中写明“来源=本目录 + 处理脚本/规则”

备注：如果你看到类似 `mcm_temp/NASA（恒Ta）` 的目录，那通常是历史上为了“恒温筛选/便于阅读”而生成的副本；其数据内容可能与本目录的 `5.+Battery+Data+Set.zip` 重叠，优先核对后再决定是否保留。

## 7. 引用建议（写作时最容易漏）

- 11 号数据集：各子目录 README 提供了推荐引用论文（Bole/Kulkarni/Daigle, PHM Society 2014），建议按其要求引用。
- 5 号数据集：至少应引用 NASA 数据仓库/数据说明文档（内层 zip 的 `README.txt` 可作为字段定义来源），并在文中说明你如何用该数据进行参数估计/验证。
