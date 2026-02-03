# 本数据目录如何服务 2026 MCM Problem A（智能手机电池耗电建模）

本文档用于把 `MCM_Sim/26A/data/calce-umd/` 与赛题 **Problem A：智能手机电池耗电建模** 关联起来，方便后续接手者理解“为什么要有这个目录、怎么用它、用到哪一部分数据”。

赛题原文/译文位置（本仓库）：`MCM_Sim/26A/论文/赛题/`。

## 1. 赛题需要什么（与数据的对应关系）

赛题要求建立一个**连续时间（continuous-time）**的电池 SOC 模型，用于在真实使用情景下预测 **TTE（Time-to-Empty）**，并且强调需要**机理清晰**，不能只做离散曲线拟合/黑盒回归。

因此我们通常会把手机电池系统拆为两层：

1) **手机负载层（usage → power/current）**：屏幕/CPU/网络/GPS/后台等，决定瞬时功耗 `P_load(t)`  
2) **电芯/电池层（current → SOC/voltage/temperature/aging）**：给出 SOC(t)、端电压 V(t)、温度影响与老化影响

`calce-umd/` 提供的是第二层（电芯/电池层）需要的**实验数据支撑**：OCV-SOC、动态工况放电响应、阻抗/内阻、温度影响、容量衰减/老化等。

> 注意：CALCE 数据并不是“某款手机电池”的实测数据，但它能提供 Li-ion 电芯行为的**合理参数范围**与**验证数据**，用于支撑你在报告中对模型参数、温度项、老化项的合理性说明与验证。

## 2. 这个目录里哪些子集最相关（建议优先级）

你不需要一次性用完所有数据。按赛题需求，推荐的“从易到难”的使用顺序如下：

### 2.1 OCV–SOC（用于从电压估 SOC / 建立电压方程）

用途：
- 建立 `OCV = OCV(SOC, T)`（温度可选）
- 支撑常见电池模型：`V(t) = OCV(SOC,T) - I(t) * R(SOC,T) - V_rc(t)`（Thevenin/RC 等效）

对应位置（示例）：
- `raw/battery-data/SP/` 与 `raw/battery-data/A123/`（具体以 `sources/battery-data.html` 的说明为准）

### 2.2 动态放电工况（用于验证“非恒定负载”下的响应）

用途：
- 用类似 DST/FUDS/US06 等变化电流曲线，验证你的连续时间模型在 `I(t)` 变化时的 SOC/V 响应
- 对“手机使用场景下功耗随时间波动”这一点给出可信的模型支撑

对应位置（示例）：
- `raw/battery-data/SP/`（SP2 动态工况相关压缩包）
- `raw/battery-data/A123/`（部分动态工况/OCV 数据）

### 2.3 阻抗/内阻与温度（用于冷天续航下降、压降、热效应的解释）

用途：
- 用阻抗/内阻随温度变化来支撑：
  - 冷天“可用容量下降/电压更早跌落”的解释
  - 大电流时端电压压降增大（影响 TTE 的关机阈值）

对应位置（示例）：
- `raw/storage/` 与 `extracted/storage/`（大量 CSV，适合直接读取）

快速 demo：
- `examples/01_plot_storage_impedance.py`（会自动挑一个 CSV 画 Nyquist/Bode 图）

### 2.4 老化/容量衰减（用于讨论“电池历史/寿命/充电习惯”的影响）

用途：
- 把 `Q_eff`（有效容量）设置为时间/循环数/温度的函数：`Q_eff(t)` 或 `Q_eff(N_cycles)`
- 给出“同样使用模式但电池更旧 → TTE 更短”的量化结论

对应位置（示例）：
- `raw/accelerated/`（加速寿命数据）
- `raw/battery-data/CS2/`、`raw/battery-data/CX2/`（循环退化数据）
- `raw/anomaly/`（异常退化：可作为“异常/不健康电池”的对比素材）

快速 demo：
- `examples/02_plot_anomaly_dataset2.py`（读取 `Dataset2.mat` 并画容量随循环衰减）

## 3. 如何把它用进你的连续时间模型（建议写法）

一个容易解释、且满足“连续时间”要求的最小模型骨架：

1) **SOC 动力学（库仑计数）**

`dSOC/dt = - I(t) / Q_eff`

其中 `Q_eff` 可以引入温度/老化项：`Q_eff = Q0 * f_age(...) * f_temp(...)`。

2) **电压方程（用于把功率负载换成电流）**

若手机侧更容易得到 `P_load(t)`，可用：

`I(t) ≈ P_load(t) / V(t)`

再由电池模型给 `V(t)`，形成闭环（可用近似/迭代处理）。

3) **参数来自哪里（报告中的“可追溯性”）**

用 `calce-umd/` 的 OCV/动态/阻抗数据来说明：
- `OCV(SOC,T)` 的形状合理
- `R(SOC,T)` 的量级合理（尤其温度影响）
- 在非恒定 `I(t)` 下模型输出与实验曲线趋势一致

## 4. 本目录内“最重要的可复现文件”

- `sources/`：网页快照（测试说明/样本编号/引用论文都在这里）
- `sources/urls.txt`：直链列表（单一事实来源）
- `manifest.csv`：原始 zip 的 sha256 与来源 URL（可校验、可追溯）
- `INTEGRITY_REPORT.md`：完整性校验报告（可再生成）
- `scripts/sync_calce_umd.py`：按 `urls.txt` 重新同步数据
- `examples/`：可直接运行的校验/绘图 demo

## 5. 一键校验与快速上手

从仓库根目录运行：

```bash
# 1) 完整性校验（建议每次交接/搬运后都跑一次）
python3 MCM_Sim/26A/data/calce-umd/examples/00_verify_integrity.py --report INTEGRITY_REPORT.md

# 2) 画一张阻抗图（验证 storage CSV 可读）
python3 MCM_Sim/26A/data/calce-umd/examples/01_plot_storage_impedance.py

# 3) 画一张异常数据容量衰减图（验证 .mat 可读）
python3 MCM_Sim/26A/data/calce-umd/examples/02_plot_anomaly_dataset2.py
```

## 6. 引用与合规提醒

CALCE 页面通常要求：若你在论文/报告中使用其数据，应引用对应的文章/论文（在网页里以 “The above data files have been referenced in:” 给出）。

在本仓库中复核引用信息的最省事方法：
- 打开 `sources/*.html`，搜索关键词 `referenced in`。

