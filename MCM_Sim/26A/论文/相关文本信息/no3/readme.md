一. 本目录下 MCM_Sim/26A/论文/相关文本信息/no3/智能手机电池建模文献调研.md 是对于以下 4 个方面的具体内容的查找并整理，并提供相应的论文来源（作者/年份/标题）：
    1. 电池等效电路模型参数 (Thevenin ECM Parameters)我需要 Thevenin 1-RC 或 2-RC 等效电路模型 的具体参数辨识结果。请查找包含以下参数具体数值（或随 SOC 变化的查找表/拟合公式）的论文：欧姆内阻 $R_0$ (Ohmic resistance)极化电阻 $R_1, R_2$ (Polarization resistance)极化电容 $C_1, C_2$ (Polarization capacitance)关键： 最好能找到这些参数随 SOC (0-100%) 和 温度 (Temperature) 变化的函数关系或三维图表数据。
    2. OCV-SOC 曲线与 Shepherd 模型系数查找适用于智能手机电池的 Open Circuit Voltage (OCV) vs. SOC 的拟合方程。特别关注 Modified Shepherd Model 或 Nernst Equation 的改良形式。关键需求： 寻找具体的系数值（如 Shepherd 模型中的 $E_0$ (标准电压), $K$ (极化系数), $A, B$ (指数项系数)），以便我能复现出“两头陡峭、中间平缓”的 S 形曲线。
    3. 智能手机组件功耗的量化模型 (Component Power Profiling)屏幕 (OLED)：查找 OLED 屏幕功耗与 APL (Average Picture Level) 及亮度 ($L$) 关系的经验公式（例如 $P = C_1 \cdot L + C_2 \cdot L \cdot APL + P_{base}$）。网络 (5G/4G/WiFi)：查找发射功率 ($P_{tx}$) 与 信号强度 (Signal Strength in dBm) 之间的定量关系模型（例如指数增长模型），以及数据吞吐量 (Throughput) 对功耗的影响。处理器 (CPU/SoC)：查找基于 DVFS (动态电压频率调整) 的功耗模型，即功率与频率 $f$ 和利用率 $u$ 的关系（$P \propto V^2 f$）。
    4. 极端条件下的物理特性 (Instability & Aging)恒功率负载不稳定性 (CPL Instability)：查找关于锂电池在“恒功率负载”下导致 电压坍塌 (Voltage Collapse) 或 DC-DC 转换效率 ($\eta$) 在低压下骤降的实验数据或理论分析论文。温度与老化 (Temp & SOH)：查找 Arrhenius 方程 在锂电池内阻建模中的具体参数（活化能 $E_a$ 等），用于描述低温下内阻剧增。查找描述电池 循环寿命 (Cycle Life) 对内阻 $R_0$ 增长影响的经验公式（如 $R_{aged} = R_{new} \cdot (1 + k \cdot \sqrt{N})$）。
二. 问题 1 (Problem 1: Continuous-Time Model) 的准备工作已经圆满完成，甚至超出了预期。
你现在手里有：
    物理骨架：二阶 Thevenin 模型（双极化 RC） + Shepherd OCV 模型 + 恒功率雪崩反馈。
    肌肉（参数）：ECM 参数表：$R_0, R_1, C_1, R_2, C_2$ 随 SOC 的具体数值（特别是 10% 以下的剧增，这是雪崩的关键）。温度系数：Arrhenius 方程的修正因子（低温 $R_0$ 翻倍）。OCV 拟合系数：6 阶多项式系数，直接可用。功耗模型：OLED 的 APL 公式，CPU 的 DVFS 系数，5G 的 RRC 状态功耗。
    灵魂（机制）：明确了“物理关机”是由电压（$V_{term} < 3.0V$）触发的，而不仅仅是 SOC=0。