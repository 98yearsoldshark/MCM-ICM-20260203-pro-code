# 01-SOC_SOH（SOC/SOH 诊断与 OCV 曲线）数据说明

本目录用于支撑 **MCM 2026 Problem A（智能手机电池建模）** 的“电池本体端”建模与论证：提供一套公开的锂电池 **OCV-SOC 曲线** 与 **fresh/aged（新/老化）实验轨迹**，用于校准/验证 **OCV、内阻、容量衰减（SOH）** 等关键机理。

> 重要：赛题要求“数据只能用于参数估计与验证，不能用纯拟合/黑盒替代连续时间模型”。因此，本数据集在本项目中只作为 **机理参数锚点与验证样例**，不会替代我们在 `src/` 中建立的连续时间方程组。

---

## 数据来源与许可（务必阅读）

本目录附带的 MATLAB 代码头部已明确：

- 来源：J. A. Braun, R. Behmann, D. Schmider, W. G. Bessler,  
  “State of charge and state of health diagnosis of batteries with voltage-controlled models”,  
  *Journal of Power Sources* 544 (2022) 231828.
- 许可：**CC-BY-NC-4.0（署名-非商业）**。
- 额外提示：代码/算法可能涉及专利（脚本头部提及 DE/WO 专利号）。

建议在论文参考文献与 AI Use/数据使用声明中明确：
- 数据/算法引用与 DOI；
- 仅用于建模比赛/学术性质（非商业）；
- 不在最终提交物中分发原始数据文件（只展示我们生成的图表与汇总统计）。

---

## 文件清单

- `OCV_vs_SOC_curve.csv`
  - 列：`SOC, V0`
  - 说明：SOC ∈ [0,1]，步长 0.001（共 1001 点）；`V0` 为开路电压（V）。
- `Experimental_data_fresh_cell.csv`
- `Experimental_data_aged_cell.csv`
  - 列：`Time, Current, Voltage, Temperature`
  - 单位：Time=秒（s），Current=安培（A），Voltage=伏（V），Temperature=摄氏度（°C）
  - 电流符号（与原脚本一致）：**I>0 代表放电，I<0 代表充电**
- `SOC_SOH_simple_model.m`
  - “simple” 电压控制模型：把实验电压 V(t) 当输入，利用 OCV 曲线反推 SOC，并用“电量吞吐比”估 SOH。
- `SOC_SOH_extendend_model.m`
  - “extended” 模型（DAE）：引入 `SOC_shell`（壳层扩散/滞后）、RC 支路与电流相关电阻 `R1 = R1a|I|+R1b`，用于更精细的 SOC/SOH 诊断。

---

## 本数据集在赛题 A 中的作用（为什么要放进来）

赛题 A 的核心难点是：**连续时间、机理化、可解释** 的手机电池模型（SOC(t)、TTE、敏感性、建议）。

手机侧功耗/场景（屏幕、CPU、无线、后台）我们在 `src/mcm26a/power/` 与 `src/configs/scenarios_v0.json` 处理；而电池侧必须具备：

1) **OCV(SOC)**：决定端电压平台/“拐点”形态，是欠压关机（V_cut）与可用能量的基础。  
2) **内阻与极化**：决定高负载时瞬时压降、休止段回弹（以及“尖峰/平台”的形态）。  
3) **SOH（老化）影响**：题面明确提到“电池寿命与历史使用/充电习惯”，我们需要能解释“越用越不耐电”的机理路径。

`01-SOC_SOH` 提供了可公开引用的、同时包含 fresh 与 aged 的实验轨迹，使我们可以：
- 把 “SOH 扫描/敏感性” 的区间从拍脑袋变成“有公开实验支撑的合理范围”；
- 给出一条可写进论文的证据链：**SOH↓ → 有效容量↓ + 内阻↑ → 更易欠压提前关机 → TTE 缩短**。

---

## 建议的用法（交接给下一个工作者）

### 用法 A：把 OCV 曲线转换为项目配置（最直接、收益高）

我们在 `src/configs/phone_default_v*_*.json` 中使用 `battery.ecm.ocv_curve.points`（分段线性）表示 OCV(SOC)。

建议做法：
- 从 `OCV_vs_SOC_curve.csv` 读取 1001 点；
- 为避免配置文件过大，可 **抽稀**（例如保留 41~101 个点）；
- 生成新的电池配置 JSON（例如 `src/configs/phone_ocv_soc_soh_v0.json`），用于 Q3 “不同 OCV 来源”的假设敏感性对照。

### 用法 B：用 fresh/aged 轨迹估一个“可写进论文”的 SOH 锚点

目标：得到一组“可解释”的参数映射，例如：
- `SOH ≈ Q_eff / Q_nom`（容量衰减）
- `R0_growth_frac ≈ α_R(1-SOH)`（内阻增长）

建议步骤（不需要复现原论文算法也能做）：
1. 选择放电片段（I>0）并按电压阈值做“近似满电/近似空电”校准（参考 MATLAB 脚本里的 4.19V / 3.01V 规则）。
2. 在每个“从满到空”的放电段上积分 `∫ I dt` 得到有效容量（Ah）。
3. 比较 fresh vs aged 的有效容量比值作为 SOH 近似（以及给出区间/方差）。
4. 用电流突变点估计 `ΔV/ΔI` 作为 R0 的粗估（同样可比较 fresh vs aged 得到增长比例）。

### 用法 C：作为“电池端验证集”补强 Q1/Q3（可选）

虽然本项目主仿真是“功率闭合（P→I）”，但电池参数校准模块里已有 **电流驱动** 的 ECM/2RC 拟合（见 `src/mcm26a/calibration/`）。

因此可以用本数据做：
- 给定 I(t) → 预测 V(t) 的误差统计（MAE/RMSE），作为电池端机理正确性的证据；
- 进一步支撑 Q3：当假设从 1RC→2RC、或加入扩散/滞后结构时，误差与 TTE 推断如何变化。

---

## 快速自查（不改代码也能先看懂数据）

你可以用任何工具快速画图确认：
- OCV(SOC) 是否单调、是否存在平台/拐点；
- fresh vs aged 的电压范围、温度范围是否合理；
- 电流符号：I>0 是放电（与脚本一致）。

（项目内后续若加入脚本，请把输出放到 `src/out_plots/...` 与 `src/out_reports/...`，不要在 data 目录中生成大量衍生文件。）

