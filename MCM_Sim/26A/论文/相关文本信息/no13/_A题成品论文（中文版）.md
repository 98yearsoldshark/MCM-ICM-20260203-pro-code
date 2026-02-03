# A 题

# 问题重述

# 问题一重述

- 目标是基于能量守恒和功率定义，在连续时间框架下建立手机电池荷电状态（State of Charge, SOC） $s(t)$  的演化模型。首先把手机视作一个整体负载，仅用总功耗  $P(t)$  刻画能量消耗，得到 SOC 的基线微分方程及其积分形式；随后将总功耗细分为屏幕、CPU、网络、GPS 与后台任务等子功耗分量，并用归一化使用强度轨迹  $B(t), L(t), N(t), G(t), H(t)$  驱动各分量，从而构造“使用模式  $\rightarrow$  功耗分量  $\rightarrow$  总功耗  $\rightarrow$  SOC 演化”的多因素连续时间模型。

- 模型的输入（已知量）包括：研究时间区间  $[0, T]$ ，电池额定总能量  $E_{\mathrm{max}}$ ，初始 SOC  $s_0$ ，以及以下两类外生时间函数之一：

1. 已知总功耗轨迹  $P(t)$ ;

2. 或已知各使用强度轨迹  $B(t), L(t), N(t), G(t), H(t)$  及功耗比例系数  $k_{\mathrm{scr}}, k_{\mathrm{cpu}}, k_{\mathrm{net}}, k_{\mathrm{gps}}, k_{\mathrm{bg}}$ 。

模型的输出（待求/状态函数）为：

○ SOC 连续时间轨迹  $s(t)$ ;

○ 与之对应的能量轨迹  $E(t)$ ;

$\circ$  以及在多因素情形下由模型给出的总功耗  $P(t)$  与各子功耗  $P_{\mathrm{scr}}(t), P_{\mathrm{cpu}}(t), P_{\mathrm{net}}(t), P_{\mathrm{gps}}(t), P_{\mathrm{bg}}(t)$  的函数形式与分解关系。

# 问题二重述

- 在问题一“功耗-SOC连续时间模型”的基础上，本问题需在给定初始电量  $s_0$  与使用场景  $k$  的条件下，利用功耗轨迹  $P(t)$  及其分解  $P_i(t)$ ，计算或近似电池从  $s_0$  放电至“耗尽阈值”  $s_{\mathrm{min}}$  所需的时间，即耗尽时间（Time-to-Empty, TTE）。

- 在每个  $(s_0, k)$  组合下，将模型预测的耗尽时间  $T_p(s_0, k)$  与观测到或认为合理的耗尽时间  $T_o(s_0, k)$  对比，得到误差  $E_T(s_0, k)$ ，并通过对功耗不确定性的建模给出耗尽时间预测的不确定性指标  $\sigma_T(s_0, k)$ 。

- 利用总功耗的分解及其时间平均，分析不同场景下屏幕、CPU、网络、GPS、后台任务等功耗分量对耗尽时间的贡献，识别导致快速耗电的主导活动或条件，以及对耗尽时间影响相对较小的因素，并据此解释不同场景下耗尽时间差异以及模型在何种情形表现优/劣。

# 模型输入（已知量）主要包括：

- 电池物理参数：额定容量  $C$  、满电可用能量  $E_{\mathrm{max}}$  （可由  $C$  与电池标称电压换算）；耗尽判据  $s_{\mathrm{min}}$  。

- 使用场景信息：场景集合  $\mathcal{K}$ ，每个场景  $k \in \mathcal{K}$  对应的环境温度  $T_{\mathrm{env}}^{(k)}$  及各功耗分量轨迹  $P_i^{(k)}(t)$ 。

- 初始电量集合  $S$  中各初始 SOC 百分比  $s_0 \in S$ 。

- 参考耗尽时间：每个  $(s_0, k)$  组合下的观测或合理耗尽时间  $T_{o}(s_{0}, k)$ 。

• 评价与分类参数: 误差阈值  $\varepsilon$  、不确定性阈值  $\delta$ , 及用于汇总误差的权重  $w_{S_{0}, k}$  。

# 模型输出（决策变量与派生量）主要包括：

- 各  $(s_0, k)$  组合的 SOC 轨迹  $s(t; s_0, k)$  与预测耗尽时间  $T_p(s_0, k)$ 。

- 预测 - 参考耗尽时间误差  $E_{T}(s_{0}, k)$  与不确定性度量  $\sigma_{T}(s_{0}, k)$  。

- 各功耗分量在放电全过程中的平均功率  $\overline{P}_i(s_0, k)$  及其在总平均功率中的占比  $\rho_i(s_0, k)$ ，用于量化每个活动/条件对耗尽时间缩短的贡献。

基于  $E_{T}(s_{0}, k)$  与  $\sigma_{T}(s_{0}, k)$  的“模型表现良好/较差”情形划分，以及按贡献大小对活动/条件的影响排序和“影响出乎意料地小”的因素识别。

# 问题三重述

- 在问题一、二的 SOC - 耗尽时间建模基础上，将手机放电过程统一抽象为：给定建模假设集合  $M_{k}$  、参数向量  $\theta$  以及各子系统使用模式轨迹

$u(t) = \{u_{j}(t)\}_{j\in \mathcal{J}}$  ，由能量守恒与功耗模型生成SOC演化  $s(t)$  ，并据此确定耗尽时间  $T_{e}(\theta ,u)$  。在此框架下，通过改变建模假设集合  $M_{k}$  、扰动参数向量  $\theta$  以及施加使用模式波动  $\delta u_{j}(t)$  ，系统性分析  $T_{e}$  与  $s(t)$  预测的变化。

• 模型输入（已知量或外部给定）包括：标称容量  $E_{\mathrm{max}}$  、有效容量  $C_{\mathrm{eff}}$  、基准参数向量  $\theta^{\star}$  （含各  $k_{j}, \alpha_{T}$  等）、温度工作范围  $[T_{\min}, T_{\max}]$  、建模假设集合族  $\{M_{k}\}$  、基准使用模式轨迹  $\{\bar{u}_{j}(t)\}_{j \in \mathcal{J}}$  、参数不确定性刻画（如  $\theta$  的方差协方差结构）以及初始 SOC  $s_{0}$  。

模型输出（决策或派生量）包括：各假设集合  $M_{k}$  下的耗尽时间  $T_{e}^{(k)}$  及其相对变化指标  $r_{T}^{(k)}$  ，对参数分量  $\theta_{i}$  的局部敏感度  $S_{T_e,\theta_i}$  与归一化敏感度 $\tilde{S}_{T_e,\theta_i}$  ，参数不确定性传播到耗尽时间的变化范围或方差，使用模式波动下的SOC曲线族  $s(t;u)$  与耗尽时间范围  $[T_e^{\min},T_e^{\max}]$  ，以及基于敏感度构造的关键影响因素重要性指标  $I_{\theta_i},I_{u_j}$  。

# 问题四重述

- 在前述 SOC - 功耗连续时间模型与耗尽时间预测框架之上，本问题要求将“能量-功耗-行为”层面的定量结论转化为对智能手机用户和操作系统（OS）的实用省电建议。核心任务包括：

3. 在给定设备参数、电池老化程度和使用场景下，度量各类可控行为（如降低屏幕亮度、禁用后台任务、切换网络模式、关闭 GPS 等）对耗尽时间  $T$  的影响，得到耗尽时间变化量  $\Delta T$  或相对变化，并据此排序行为优先级。

4. 抽象操作系统电源管理策略为从状态  $x(t)$  到控制  $u_{\mathrm{os}}$  的策略函数  $\pi$ ，在能量约束下度量不同策略对耗尽时间的影响，并寻找延长续航的优选策略。

5. 通过容量保持率  $\eta$  将电池老化映射到有效容量  $C_{\mathrm{eff}}$  的变化，分析老化对耗尽时间  $T(\eta)$  和归一化续航  $R(\eta)$  的影响，从而给出针对不同老化程度的差异化建议。

6. 在统一 SOC - 功耗建模框架下，将上述分析推广到一般便携设备  $d$ ，建立耗尽时间  $T_{d}$  与其容量  $C_{d}$ 、功耗特征  $P_{d}(t)$  之间的缩放关系，使基于手

机建立的模型与建议可迁移至其他设备。

7. 构造从当前或预测状态（如SOC、负载、网络活动强度、环境温度等）到推荐操作集合及其预期续航改善区间的映射，以形成面向终端用户与OS设计者的“模型驱动建议表”。

- 在本问题的建模中，输入（已知量）主要包括：

。电池标称容量  $E_{\mathrm{max}}$  、容量保持率  $\eta$  、有效容量  $C_{\mathrm{eff}}$  、初始 SOC  $s_0$  与耗尽阈值  $s_{\mathrm{min}}$

设备集合  $\mathcal{D}$  中各设备的有效容量  $C_d$  与总功耗轨迹  $P_d(t)$ ;

○ 环境温度轨迹  $T_{\mathrm{env}}(t)$  及其对功耗/容量的已知影响；

$\bigcirc$  用户基线行为配置  $u_{\mathrm{usr}}^{0}$  （如亮度、网络模式、后台任务开关等）与基线OS策略  $\pi^0$

○ 在给定设备、老化程度和策略下，功耗对行为的响应函数，如各模块功耗  $P_{\mathrm{scr}}, P_{\mathrm{cpu}}, P_{\mathrm{net}}, P_{\mathrm{gps}}, P_{\mathrm{bg}}$  随状态和控制的变化规律。

输出（决策变量及派生量）包括：

$\mathrm{u}_{\mathrm{usr}}$  （相对于基线行为的配置改动）及在不同调整下的耗尽时间  $T_{\mathrm{opt}}$  与增量  $\Delta T$ ；

。行为影响优先级指标  $I_{\mathrm{usr}}^{(k)}$  及由此得到的行为排序；

○ 操作系统电源管理策略函数  $\pi$  及在代表性场景下对应的耗尽时间  $T_{\mathrm{opt}}$  、增量  $\Delta T$  或相对提升；

。不同容量保持率下的耗尽时间函数  $T(\eta)$  与归一化续航  $R(\eta) = T(\eta) / T(1)$ ;

○ 一般便携设备  $d$  的耗尽时间  $T_{d}$  与  $(C_d, P_d)$  的缩放关系；

从状态到推荐操作及预期续航改善的映射  $\mathcal{A}$  。

# 1.2 模型假设

- 假设1：在研究时间区间内，电池剩余能量  $E(t)$  与SOC之间近似线性，且可由常数额定能量  $E_{\mathrm{max}}$  表征，即  $s(t) = E(t) / E_{\mathrm{max}}$ ，忽略电压曲线非线性等高阶效应。

- 假设2：仅考虑放电场景，不出现外部充电或能量回馈，各模块功耗与总功耗在整个过程中非负；忽略温度、自放电等慢变效应对瞬时能量收支的直接影响。

- 假设3：在研究时间尺度上，各子模块功耗对其归一化使用强度（亮度、CPU利用率、网络活动等）可采用一阶线性近似且单调非减，故可用正的比例系数  $k_{\mathrm{scr}}, k_{\mathrm{cpu}}, k_{\mathrm{net}}, k_{\mathrm{gps}}, k_{\mathrm{bg}}$  描述功耗－强度关系，总功耗等于各子功耗之和。

- 假设 4：线性能量-SOC 关系与场景相关的放电系数。

电池在场景  $k$  下可视为单一能量储存器，剩余能量  $E(t)$  与SOC百分比 $s(t)$  近似线性，并满足  $s(t) = 100E(t) / E_{\mathrm{max}}^{(k)}$  。环境温度  $T_{\mathrm{env}}^{(k)}$  等条件仅通过改变有效满电能量  $E_{\mathrm{max}}^{(k)}$  体现，进而只影响“功耗  $\rightarrow$  SOC下降速率”的比例系数。

- 假设5：使用场景下功耗轨迹已知且仅放电不充电。

在每个场景  $k$  下，各功耗分量  $P_{i}^{(k)}(t)$  及其和  $P^{(k)}(t)$  在分析区间内视为已知非负函数，且手机仅从电池取能，无能量回充，因而 SOC 随时间单调不增。

- 假设 6: 平均功率近似用于解析解释。

虽然耗尽时间的精确定义依赖于瞬时功耗积分，但为便于解释不同活动和条件对耗尽时间的影响，可引入“放电全过程总/分量平均功率”的近似，从而得到简洁的近似解析关系，以定量比较各功耗分量的贡献大小。

- 假设 7：在给定建模假设集合  $M_{k}$  与参数向量  $\theta$  下，手机电池的 SOC 动力学可用一阶常微分方程描述，其右端由有效容量  $C_{\mathrm{eff}}$  与各子系统功耗线性叠加的总功耗  $P(t)$  决定，且该动力系统在分析时间区间内解的存在性与唯一性成立。

• 假设 8: 在基准点  $\left(M_{k_{0}}, \theta^{\star}, \bar{u}(t)\right)$  的邻域内, 耗尽时间  $T_{e}(\theta, u)$  对参数向量各分量  $\theta_{i}$  以及对使用模式轨迹  $u_{j}(t)$  的扰动均可视为 Fréchet 可微,从而可通过一阶线性化与方差传播近似刻画参数不确定性与使用模式波动对  $T_{e}$  的影响。

- 假设9：不同建模假设集合  $M_{k}$  仅改变容量 - 温度关系、功耗叠加形式或SOC定义等机理结构，不改变能量守恒的基本框架；在比较不同  $M_{k}$  对预测的影响时，统一采用相同的初始时刻  $t_{0}$  、初始SOC  $s_{0}$  以及基准使用模式或其约束集合，以保证跨模型结果可比。

假设10（功耗可控结构）：

对给定设备与外部环境，在用户行为配置  $u_{\mathrm{usr}}$  和 OS 策略  $\pi$  固定时，总功耗  $P(t)$  为确定的非负函数，且可分解为若干物理模块功耗之和。每个模块功耗对其直接控制量（如亮度、后台任务强度等）单调非减，即提升相关设置不会降低对应功耗。

- 假设 11 (老化只改变有效容量):

电池老化通过容量保持率  $\eta$  线性缩放有效容量

$$
C _ {\mathrm {e f f}} = \eta E _ {\mathrm {m a x}}, \quad 0 <   \eta \leq 1,
$$

但在给定操作条件下，不改变“控制  $\rightarrow$  功耗”的结构性关系；即功耗模型对控制变量与状态的依赖形式在不同老化阶段保持一致。

- 假设 12（平均功耗近似与跨设备缩放）：

在行为优先级评估、OS 策略比较及跨设备推广时，可用从放电开始到耗尽时间的时间平均功耗  $\bar{P}$  近似表征整个放电过程的功耗水平，从而近似获得耗尽时间与容量、平均功耗之间的反比关系

$$
T \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}, \qquad T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} _ {d}}.
$$

# 1.3 符号说明

# 1.3.1 集合与索引

<table><tr><td>符号</td><td>定义</td><td>取值范围</td></tr><tr><td>T</td><td>研究时间的连续区间</td><td>[0,T]</td></tr><tr><td>t</td><td>时间索引变量</td><td>t∈T</td></tr><tr><td>M</td><td>功耗子模块集合</td><td>{scr, cpu, net, gps, bg}</td></tr><tr><td>m</td><td>子模块索引</td><td>m∈M</td></tr></table>

# 1.3.2 模型参数

<table><tr><td>符号</td><td>含义</td><td>单位</td></tr><tr><td>Emax</td><td>电池满电时可提供的总能量</td><td>J或Wh（选定一种并保持一致）</td></tr><tr><td>s0</td><td>初始时刻 t=0 的 SOC（比例 0~1）</td><td>-</td></tr><tr><td>kscr</td><td>屏幕功耗与亮度强度 B(t) 的比例系数</td><td>W</td></tr><tr><td>kcpu</td><td>CPU 功耗与负载强度 L(t) 的比例系数</td><td>W</td></tr><tr><td>knet</td><td>网络功耗与网络活动强度 N(t) 的比例系数</td><td>W</td></tr><tr><td>kgps</td><td>GPS 功耗与使用强度 G(t) 的比例系数</td><td>W</td></tr><tr><td>kbg</td><td>后台任务功耗与活动强度 H(t) 的比例系数</td><td>W</td></tr><tr><td>T</td><td>研究时间上界</td><td>s 或 h（与 Emax, P(t) 的单位配套）</td></tr></table>

# 问题一

# 1.3.3 决策变量

本问题中的未知函数（决策/状态变量）与外生输入变量如下：

# - 决策变量（待求函数）

$\circ s(t)$  ：SOC轨迹，为定义在  $\mathcal{T}$  上的一次连续可微函数，  $s:\mathcal{T}\to [0,1]$  满足初始条件  $s(0) = s_0$  。其物理意义为时刻  $t$  电池剩余能量占满电能量的比例。

$\circ$ $E(t)$  ：电池剩余能量轨迹，由  $s(t)$  通过  $E(t) = E_{\max}s(t)$  唯一确定，因此可视为由  $s(t)$  派生的中间状态函数，  $E:\mathcal{T}\to [0,E_{\mathrm{max}}]$  。

# - 外生输入变量（已知时间函数）

$\circ$  总功耗轨迹  $P(t)$  ：若直接测得或给定，为定义在  $\mathcal{T}$  上的非负可积函数 $P:\mathcal{T}\to [0, + \infty)$  。

。使用强度轨迹  $B(t), L(t), N(t), G(t), H(t)$  : 当采用多因素模型时视为已知, 均为定义在  $\mathcal{T}$  上的有界可测函数, 取值范围为  $[0,1]$ , 分别代表屏幕亮度、CPU 负载、网络活动、GPS 使用及后台任务活动强度。

# 1.4. 模型的构建与推导

# 1.4.1 中间变量与子模型构建

# 1. 能量守恒原理  $\rightarrow$  电池能量演化

从物理上看，电池是能量储存器，其剩余能量  $E(t)$  随时间的变化完全由对外输出的功率  $P(t)$  决定。功率是单位时间内能量变化率，若约定“向外输出能量为正”，则电池能量随时间的变化满足

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t), \quad t \in \mathcal {T},
$$

即当外部功耗  $P(t)$  为正时，电池剩余能量  $E(t)$  随时间单调减少。

# 2. SOC 定义  $\rightarrow$  能量到无量纲状态的抽象

为方便描述，将有量纲的能量  $E(t)$  归一化为无量纲状态变量 SOC。根据 SOC 的定义，其为电池剩余能量占额定总能量的比例：

$$
s (t) = \frac {E (t)}{E _ {\mathrm {m a x}}}, \quad t \in \mathcal {T}.
$$

该关系给出从物理能量变量到无量纲状态变量的直接线性映射。

# 3. 能量微分关系与 SOC 定义结合  $\rightarrow$  基线 SOC 微分方程

对SOC定义式随时间求导，利用链式法则有

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = \frac {1}{E _ {\max}} \frac {\mathrm {d} E (t)}{\mathrm {d} t}.
$$

将能量守恒关系  $\mathrm{d}E(t) / \mathrm{d}t = -P(t)$  代入上式，得到SOC的基线连续时间微分方程：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\mathrm {m a x}}}, \quad t \in \mathcal {T},
$$

并配以初始条件

$$
s (0) = s _ {0}.
$$

在该方程中， $E_{\mathrm{max}}$  起到尺度因子的作用：在相同功耗轨迹  $P(t)$  下， $E_{\mathrm{max}}$  越大，右端绝对值越小，SOC下降越缓慢。

# 4. 微分形式积分  $\rightarrow$  基线SOC积分形式

为显式体现累计能量消耗与SOC变化之间的关系，对基线微分方程在  $[0,t]$  上积分，得到

$$
\int_ {0} ^ {t} \frac {\mathrm {d} s (\tau)}{\mathrm {d} \tau} \mathrm {d} \tau = - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau .
$$

利用左侧积分的牛顿-莱布尼茨公式并代入初始条件  $s(0) = s_0$ ，SOC 的积分形式为

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau , t \in \mathcal {T}.
$$

该式说明：从初始时刻到时刻  $t$  所消耗的累计能量（积分项）按  $1 / E_{\mathrm{max}}$  的比例线性折算为 SOC 的下降量。

# 5. 功耗分解原理  $\rightarrow$  总功耗与子功耗的加和模型

为刻画不同功能模块对总功耗及 SOC 演化的贡献，将手机抽象为若干功耗子模块组成的系统。令  $P_{m}(t)$  为模块  $m \in \mathcal{M}$  在时刻  $t$  的功耗，则总功耗满足能量守恒意义上的加和关系：

$$
P (t) = \sum_ {m \in \mathcal {M}} P _ {m} (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t).
$$

在纯放电情形下，各子功耗  $P_{m}(t)$  及总功耗  $P(t)$  均应非负。

# 6. 使用强度抽象  $\rightarrow$  功耗-使用强度线性子模型

各模块功耗受其使用强度驱动。为便于建模，将物理可控或可观察的使用行为归一化为[0,1]区间的无量纲强度：

屏幕亮度  $B(t)$ ;

CPU 负载  $L(t)$

○ 网络活动强度  $N(t)$

。GPS使用强度  $G(t)$

后台任务活动强度  $H(t)$  。

在一阶线性近似下，假设每个模块功耗与对应强度成正比，比例系数为该模块在“单位强度”下的功耗水平，则有

$$
\begin{array}{l} P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t), \\ P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t), \\ P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t), \\ P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t), \\ P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t), \\ \end{array}
$$

其中

$$
k _ {\mathrm {s c r}}, k _ {\mathrm {c p u}}, k _ {\mathrm {n e t}}, k _ {\mathrm {g p s}}, k _ {\mathrm {b g}} > 0.
$$

这些比例系数的物理意义为：在对应强度恒为1时，各模块的平均功耗水平。系数越大，给定强度下该模块功耗越高，对总功耗的贡献越大，从而加速SOC的衰减。

将上述关系代入功耗分解式，可得总功耗在使用强度变量下的表示：

$$
P (t) = k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t).
$$

# 7. 功耗分解回代  $\rightarrow$  多因素SOC动力学方程

将上述多因素总功耗表达式代入基线 SOC 微分方程 $s(t)/t=-P(t)/E{}$,得到显式依赖使用强度轨迹的SOC连续时间方程: $ = -,s(0)=s_0.

# 相应的积分形式为

s(t) = s_0 - {}{0}^{\wedge}\{t\}.$$ 该方程组给出了从使用模式 (B,L,N,G,H) 到 SOC 轨迹 s(t) 的连续时间映射,同时体现了参数 Emax 与各 k. 对 SOC 演化方向与速度的影响: Emax 越大或各 k. 越小, SOC 下降越慢。

# 1.4.2 目标函数

从严格的数学建模角度，可将SOC轨迹的求解视为在函数空间中寻找一个函数  $s(t)$ ，使其尽可能精确地满足由能量守恒与功耗分解所给出的微分方程。为此引入基于残差平方的目标泛函，用以形式化“物理方程被满足”的目标：

在给定总功耗轨迹  $P(t)$  的基线模型下, 定义

$$
J [ s ] = \int_ {0} ^ {T} \left(\frac {\mathrm {d} s (t)}{\mathrm {d} t} + \frac {1}{E _ {\max}} P (t)\right) ^ {2} \mathrm {d} t.
$$

在多因素模型中,由于$P(t)=k{}B(t)+k{}L(t)+k{}N(t)+k{}G(t)+k{}H(t),$ 目标泛函可写为

$$
\begin{array}{l} J [ s ] = \int_ {0} ^ {T} \left(\frac {\mathrm {d} s (t)}{\mathrm {d} t} + \frac {1}{E _ {\mathrm {m a x}}} [ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) ]\right) d t. \\ \left. + k _ {\mathrm {b g}} H (t) \right] \bigg) ^ {2} \mathrm {d} t. \\ \end{array}
$$

# 睿森科研简介

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/e97d168cc8699917a100f8e992b4260c4848970ded54a97f50bc60bd3846f33b.jpg)


# 关于我们

睿森科研 深耕论文辅导领域5年为广大学子提供专业化、个性化的论文咨询服务

# 坚持初心，砥砺前行

我们始终秉持“授人以鱼不如授人以渔”的初心，为广大师生提供专业化、高水平的论文教育产品以及咨询服务。自19年以来，年均辅导学员人数达数千人，并呈现迅速上升趋势。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/d4793a47442262bc1ea7f4beecacb4fc7b4f43c280ec717978bef606cec013a0.jpg)


# 国内学术能力提升领导品牌，师资雄厚

提供会议论文辅导与发表、科研论文辅导与发表、硕博核心/S刊辅导、本硕博毕业论文辅导、以及各类大学生竞赛辅导等项目。我们的师资团队由2000余位专业论文咨询师组成。其中海内外高校博士及大学教授1000多人。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/e948db7bbbfa80d4c5137a89687cdf6f058f77f2a569d834f2b0b07b207de531.jpg)


# 业务内容

科研论文、本硕博毕业论文辅导各类大学生竞赛辅导

# 科研论文，毕业论文辅导

我们提供SCI、SSCI、CSSCI、EI源刊、中文核心、学报等科研论文辅导；本硕博毕业论文、课题辅导。已成功助力数千名学员拿到相应辅导的录用通知，因此保研、申博成果的学员不计其数。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/04f9f2fc184cc017683a188643a4cc84a2bd6c82e67b432d57925a4232149c80.jpg)


# 大学生竞赛辅导

各类数学建模竞赛、数学竞赛、英语竞赛、互联网+、挑战杯、力学竞赛、创青春等大学生竞赛辅导，已成功助力数百名学员荣获国奖！

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/0551ae7f4b6fd663dea6dbef83f57db3eb4e7cdc721050144ccd791e234b5e46.jpg)


求解目标：在满足初始条件及各物理约束的函数集合中，求解使  $J[s]$  取得最小值的 SOC 轨迹  $s(t)$  。理想情况下，物理上完全自治的 SOC 轨迹满足微分方程严格成立，使得残差为零，对应  $J[s] = 0$  。

# 1.4.3 约束条件

# (1) SOC 定义约束

该约束将 SOC 与有量纲的电池剩余能量联系起来，是 SOC 物理意义的基础：

$$
s (t) = \frac {E (t)}{E _ {\mathrm {m a x}}}, \quad t \in \mathcal {T}.
$$

# (2) 功耗与能量变化关系约束

功耗定义为电池对外提供能量的速率，从而给出能量随时间的演化规律：

$$
P (t) = - \frac {\mathrm {d} E (t)}{\mathrm {d} t}, \quad t \in \mathcal {T}.
$$

# (3) 连续时间建模与光滑性约束

为保证 SOC 连续时间方程的意义，要求 SOC 在研究时间区间内连续可微：

$$
s (t) \in C ^ {1} [ 0, T ].
$$

# (4) 能量非负与容量上界约束

在正常放电过程中，电池剩余能量不能为负亦不应超过额定容量：

$$
0 \leq E (t) \leq E _ {\max }, \quad \forall t \in [ 0, T ].
$$

# (5) 放电单调性与功耗非负约束

放电过程中电池不会自发充电，对应剩余能量单调不增、总功耗非负：

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} \leq 0 \quad \Leftrightarrow \quad P (t) \geq 0, \quad \forall t \in [ 0, T ],
$$

从 SOC 的角度等价于

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} \leq 0, \quad \forall t \in [ 0, T ].
$$

# (6) 总功耗与子功耗的能量守恒约束

总功耗必须严格等于所有功能模块功耗之和，体现功耗分解的一致性：

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t), \quad \forall t \in [ 0, T ].
$$

# (7) 各功耗分量非负约束

各用电模块只消耗电能而不向电池回馈能量，因此其功耗应非负：

$$
P _ {\mathrm {s c r}} (t) \geq 0, P _ {\mathrm {c p u}} (t) \geq 0, P _ {\mathrm {n e t}} (t) \geq 0, P _ {\mathrm {g p s}} (t) \geq 0, P _ {\mathrm {b g}} (t) \geq 0, \forall t \in [ 0, T ].
$$

# (8) 使用强度变量的物理范围约束

屏幕亮度、CPU 负载、网络/GPS/后台活动强度均为归一化指标，取值限制在 [0,1] 区间：

$$
0 \leq B (t), L (t), N (t), G (t), H (t) \leq 1, \quad \forall t \in [ 0, T ].
$$

# (9) 功耗-使用强度关系与单调性约束

在线性近似下，各模块功耗与对应使用强度之间具有正比例关系，且比例系数为正，以体现“强度越高，功耗越大或不减”的物理单调性：

$$
\begin{array}{l} P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t), \\ P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t), \\ P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t), \\ P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t), \\ P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t), \\ \end{array}
$$

$$
k _ {\mathrm {s c r}}, k _ {\mathrm {c p u}}, k _ {\mathrm {n e t}}, k _ {\mathrm {g p s}}, k _ {\mathrm {b g}} > 0.
$$

# (10) SOC 取值范围与初始条件约束

由能量取值范围和 SOC 定义可得 SOC 必须位于  $[0,1]$ ，并满足给定的初始条件：

$$
\begin{array}{l} 0 \leq s (t) \leq 1, \quad \forall t \in [ 0, T ], \\ s (\mathbf {0}) = s _ {\mathbf {0}}, \quad \mathbf {0} \leq s _ {\mathbf {0}} \leq \mathbf {1}. \\ \end{array}
$$

# 1.5 模型汇总

在上述推导基础上，问题一的SOC连续时间模型可汇总为一个“残差最小化  $+$  物理约束”的标准数学形式。以多因素模型为例：

# 目标函数（求解目标）

$$
\begin{array}{l} \min _ {s (\cdot)} J [ s ] = \int_ {0} ^ {T} \left(\frac {\mathrm {d} s (t)}{\mathrm {d} t} + \frac {1}{E _ {\max}} [ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) ]\right) d t. \\ \left. + k _ {\mathrm {b g}} H (t) \right] \bigg) ^ {2} \mathrm {d} t. \\ \end{array}
$$

# 约束条件

1. SOC 与能量关系：

$$
s (t) = \frac {E (t)}{E _ {\mathrm {m a x}}}, \quad t \in [ 0, T ].
$$

2. 功耗与能量变化：

$$
P (t) = - \frac {\mathrm {d} E (t)}{\mathrm {d} t}, \quad t \in [ 0, T ].
$$

3. SOC 光滑性：

$$
s (t) \in C ^ {1} [ 0, T ].
$$

4. 能量范围：

$$
0 \leq E (t) \leq E _ {\max }, \quad \forall t \in [ 0, T ].
$$

5. 放电单调性与功耗非负：

$$
P (t) \geq 0, \quad \frac {\mathrm {d} E (t)}{\mathrm {d} t} \leq 0, \quad \frac {\mathrm {d} s (t)}{\mathrm {d} t} \leq 0.
$$

6. 总功耗分解：

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t).
$$

7. 子功耗非负：

$$
P _ {\mathrm {s c r}} (t), P _ {\mathrm {c p u}} (t), P _ {\mathrm {n e t}} (t), P _ {\mathrm {g p s}} (t), P _ {\mathrm {b g}} (t) \geq 0.
$$

8. 使用强度范围：

$$
0 \leq B (t), L (t), N (t), G (t), H (t) \leq 1.
$$

9. 功耗 - 强度线性关系及系数正性：

$$
P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t),
$$

$$
P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t),
$$

$$
P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t),
$$

$$
P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t),
$$

$$
P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t),
$$

$$
k _ {\mathrm {s c r}}, k _ {\mathrm {c p u}}, k _ {\mathrm {n e t}}, k _ {\mathrm {g p s}}, k _ {\mathrm {b g}} > 0.
$$

10. SOC 取值与初始条件：

$$
0 \leq s (t) \leq 1, \quad \forall t \in [ 0, T ], \qquad s (0) = s _ {0}.
$$

在这些约束下，目标函数的最小值为零时，对应的  $s(t)$  必然满足

$$
\begin{array}{l} \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\max}} \\ = - \frac {1}{E _ {\mathrm {m a x}}} \big [ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t) \big ], \\ \end{array}
$$

配合积分形式

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau ,
$$

从而形成一个从总功耗（基线模型）及其多因素分解（扩展模型）到SOC演化的统一连续时间描述框架，满足问题一对SOC连续时间方程、功耗分解与使用模式映射及参数物理意义的全部要求。

# 问题一的模型求解

# 2.1 算法设计

# - 算法名称与原理概述

采用的算法为基于一阶 SOC 微分方程的显式数值积分算法（梯形积分 / 四阶 Runge-Kutta 法，RK4）。其核心是对模型中给出的 SOC 动力学方程

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\max}}, \quad s (0) = s _ {0}
$$

及其多因素扩展形式

$$
\begin{array}{l} \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{E _ {\max}} \left[ k _ {\text {s c r}} B (t) + k _ {\text {c p u}} L (t) + k _ {\text {n e t}} N (t) + k _ {\text {g p s}} G (t) + k _ {\text {b g}} H (t) \right], \quad s (0) \\ = s _ {0} \\ \end{array}
$$

进行时间离散，将连续时间的常微分方程转化为离散时间上的递推公式  $s_{n+1}$  由  $s_n$  显式给出，从而得到 SOC 在一系列离散时刻上的近似值。梯形法通过近似积分

$$
\int_ {t _ {n}} ^ {t _ {n + 1}} P (\tau) \mathrm {d} \tau \approx \frac {\Delta t}{2} (P (t _ {n}) + P (t _ {n + 1}))
$$

来逼近积分形式

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau ,
$$

而RK4则在每一步上采用四个阶段点对  $\frac{\mathrm{d}s}{\mathrm{d}t}$  进行高阶加权求和，提高时间积分精度。

# 与模型数学特性的匹配与必要性说明

1. 方程性质：模型给出的 SOC 方程是一维、线性的、右端仅显式依赖时间（通过  $P(t)$  或  $B, L, N, G, H$ ），无状态反馈，且在实际应用中不表现出刚性行为，属于典型的非刚性一阶 ODE。这类方程无需复杂的隐式求解器，显式梯形法与 RK4 具有足够的稳定性与高阶精度。

2. 积分形式与无解析积分的情形：尽管基线模型给出了积分形式

$$
s (t) = s _ {0} - \frac {1}{E _ {\max}} \int_ {0} ^ {t} P (\tau) d \tau ,
$$

但在实际中  $P(t)$  或使用强度轨迹  $B(t), L(t), N(t), G(t), H(t)$  可能是测量数据或复杂时间函数，难以求解析积分，因此需要数值积分来逼近上述积分。梯形法与RK4正是对该积分式和对应微分方程的数值实现。

# 3. 约束易于在离散层面处理：模型要求

$$
0 \leq s (t) \leq 1, \quad \frac {\mathrm {d} s (t)}{\mathrm {d} t} \leq 0, \quad P (t) \geq 0,
$$

以及

$$
0 \leq B (t), L (t), N (t), G (t), H (t) \leq 1, k _ {\mathrm {s c r}}, k _ {\mathrm {c p u}}, k _ {\mathrm {n e t}}, k _ {\mathrm {g p s}}, k _ {\mathrm {b g}} > 0.
$$

在显式时间步进中，可在每个时间步后对  $s_n$  做投影（截断到[0,1]且保证单调不增），并利用线性关系

$$
P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t), \dots , P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t)
$$

自动保证各功耗非负及总功耗分解，从而保证离散解满足模型约束。

# 4. 与目标泛函  $J[s]$  的关系：模型中给出的目标泛函

$$
J [ s ] = \int_ {0} ^ {T} \left(\frac {\mathrm {d} s (t)}{\mathrm {d} t} + \frac {1}{E _ {\max}} P (t)\right) ^ {2} \mathrm {d} t
$$

在多因素情形下扩展为

$$
\begin{array}{l} J [ s ] = \int_ {0} ^ {T} \left(\frac {\mathrm {d} s (t)}{\mathrm {d} t} + \frac {1}{E _ {\mathrm {m a x}}} [ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) ]\right), \\ \left. + k _ {\mathrm {b g}} H (t) \right] \biggr) ^ {2} \mathrm {d} t \\ \end{array}
$$

的极小值点即为满足 SOC 微分方程的轨迹。显式数值积分在时间网格上构造  $s_{n}$ , 使离散残差

$$
r _ {n} \approx \frac {s _ {n + 1} - s _ {n}}{\Delta t} + \frac {1}{E _ {\mathrm {m a x}}} P (t _ {n} + \theta \Delta t)
$$

(0 ≤ θ ≤ 1) 在数值误差范围内逼近零, 从而在离散层面近似实现  $J[s]$  的最小化。

# - 算法核心要素

# 1. 决策变量的离散表示（编码方式）

- 连续 SOC 轨迹  $s(t)$  在时间网格

$$
t _ {n} = n \Delta t, \quad n = 0, 1, \dots , N, \quad \Delta t = \frac {T}{N}
$$

上用向量

$$
\mathbf {s} = (s _ {0}, s _ {1}, \dots , s _ {N})
$$

表示，其中  $s_n \approx s(t_n)$ 。

- 对应能量轨迹在离散点为

$$
E _ {n} = E _ {\max} s _ {n}, \quad n = 0, \dots , N,
$$

来自连续关系  $E(t) = E_{\max}s(t)$ 。

- 功耗及使用强度轨迹在网格上的离散表示：

$$
P _ {n} \approx P (t _ {n}), \quad B _ {n} \approx B (t _ {n}), L _ {n} \approx L (t _ {n}), \dots , H _ {n} \approx H (t _ {n}).
$$

# 2. 搜索空间与约束

搜索空间可视为所有满足

$$
0 \leq s _ {n} \leq 1, \quad s _ {n + 1} \leq s _ {n}, \quad n = 0, \dots , N - 1
$$

的离散序列，以及由

$$
E _ {n} = E _ {\mathrm {m a x}} s _ {n}, \quad P _ {\mathrm {s c r}, n} = k _ {\mathrm {s c r}} B _ {n}, \dots , P _ {\mathrm {b g}, n} = k _ {\mathrm {b g}} H _ {n}
$$

推得的能量与功耗序列。通过时间步进和投影操作显式保证这些约束。

# 3. 目标函数到离散残差（适应度）的转化

在离散层面，引入残差

$$
r _ {n} = \frac {s _ {n + 1} - s _ {n}}{\Delta t} + \frac {1}{E _ {\mathrm {m a x}}} P _ {n + 1 / 2},
$$

其中  $P_{n+1/2}$  由插值近似

$$
P _ {n + 1 / 2} \approx \frac {1}{2} \left(P _ {n} + P _ {n + 1}\right)
$$

或由 RK4 阶段点得到。离散目标泛函

$$
J _ {d} (\mathbf {s}) = \sum_ {n = 0} ^ {N - 1} r _ {n} ^ {2} \Delta t
$$

逼近连续  $J[s]$  。梯形法与RK4的设计，使得在给定  $P(t)$  时  $r_n$  的数量级为高阶小量，从而  $J_d$  近似为零。

# - 关键算法参数及符号

时间步长:  $\Delta t > 0$  。

步数:  $N \in \mathbb{N}^{+}$ , 满足  $\Delta t = T / N$  。

○ 误差容限（时间离散误差）： $\varepsilon > 0$ ，用于网格加密的收敛判据。

○ 积分方法选择指示符： $\eta \in \{\mathrm{Trap}, \mathrm{RK4}\}$ ，分别对应梯形法与四阶 Runge-Kutta 法。

$\circ$  若采用残差监控, 还可定义残差容限  $\varepsilon_{J} > 0$ , 要求离散目标  $J_{d}(\mathbf{s}) \leq \varepsilon_{J}$  。

# 2.2 求解流程

# 步骤 1: 数据准备与初始参数设定

- 步骤目的

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/ee66a6671f8c065e0f2243f8348a1779f57b09bf276883ce4ffa0703a5b5afc8.jpg)


# 大学生创新创业大赛

# 精品辅导

互联网+|挑战杯|创青春|三创赛等

# 我们的优势

强大的师资力量

- 多对一全程服务

- 辅导前试听机制

- 无限次在线答疑

- 定制化课程内容

·学员奖学金激励

# 课程内容

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/e4c0d4f60d2822b77990341bd1ad39654b47a707303fc538d339542969069df9.jpg)


# 项目诊断

根据不同的项目，结合各方面背景，提供项目改进意见和项目方向规划。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/b44009666ea34b756308772ad3e7b2a157c3649f2cdd15ac53bd108467f19b73.jpg)


# 参赛规划

依据学校、专业以及项目特点，制定参赛路线。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/fa4673f0ee4a51866ca5e36dba9fbc40ea9e81e39cdfa75c3e159bd488628d35.jpg)


# 商业计划书修改

提供针对性的书写指导，并在完成后逐页提供修改意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/4d3e9db683a71ce86898b258b053b10ed88ea1ac6223a57144eb393a85c8982d.jpg)


# PPT指导与修改

提供针对性的制作指导，并在完成后提供逐页提供修改意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/357197067da19d2f0924713a2304dd914755b11d7daa9e9f643d27e4260eb9f7.jpg)


# 答辩指导与训练

对答辩进行训练，并提供针对性的指导意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/c161d2b174f453eebad6bd98450ca6cd189526abcc5717b9e8ae16c135c419e0.jpg)


# 全程无限次答疑

比赛中遇见的各个问题，在辅导期间全程免费答疑。

# 辅导成绩

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/3ec6c536a79091c13625fc964b98f0f78738a1b19f0648366203011660dfcd4b.jpg)


互联网+省银以上10余项

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/90c355a51786a40b8d09b3a5aaff370e37dfb6e77d0e4608b2f77614b7f3070f.jpg)


创青春省二以上10余项


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/78822c3cc072e284e15381b9941491a3064478443d9b0ab6849054df2151cc6b.jpg)


三创赛国奖3项

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/b91f3bfe0820540803dca580f1129e0a4982642e5f895bd53f7b476dcae9fbc0.jpg)


容森科研

# 新学期

# 科研论文新规划

试听机制

合同保障

全科覆盖

实力师资

# 雏鹰计划

- 全过程辅导（到论文定稿）：

高质量中文/英文期刊、EI/CPCI会议

- 辅导加发表一体化（到论文发表）：

一对一：高质量中文/英文期刊、EI/CPCI会议

双人团（两篇文章）：EI会议

- 时间周期：定稿2-4个月，录用1个月内，见刊2-6个月，检索1-3个月

# 卓研计划

- 全过程辅导（到论文定稿）：

SCI、EI源刊、中文核心、学报

- 辅导加发表一体化（到论文发表）：

一对一：SCI、EI源刊

二人小班（共同完成一篇论文）：SCI、EI源刊

三人小班（共同完成一篇论文）：SCI、EI源刊

- 时间周期：定稿3-6个月，录用2-8个月，见刊0.5-2个月，检索0.5-2个月

详情请扫描二维码咨询学术顾问

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/0fa456ba7021092158bd28fd4529912887bff078e12de0357dd79cc7f1fd0d43.jpg)


# 大学生学科类竞赛

# 保奖班

# 数学/英语/物理等

# 火热招生中

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/7e36f04bc099cc768ee929535b62f1503913d5dc991739e6e3c0c2306c574211.jpg)


# 我们的优势

强大的师资力量

- 辅导前试听机制

- 定制化课程内容

- 多对一全程服务

- 无限次在线答疑

学员奖学金激励

# 课程大纲

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/64e3013b4e1bd1f2ec88623664af90e9c35d95cdf510926ad6072c67635bc03b.jpg)


基础知识讲解培训

依据相关竞赛大纲，逐点讲解

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/6ffbfbe6541762238c1145ad4479c93afc17910186b0498697748fee3b1c30bd.jpg)


竞赛考点难点分析

针对竞赛难点，重点突破

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/8cc42ea9e3d5ba73b27c08b90102bf9427a7f6cd57dcc763307f4eda00d3dbe2.jpg)


真题选讲点评

结合历年真题，精选例题详解

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/8e0f562657f69ef8b1c0b7410f6e1691c89e125b6f541b2113f68d96ba220609.jpg)


全真模拟练习

竞赛全真模拟，赛后详细解析

# 大学生计算机类竞赛保奖班

# ACM/蓝桥杯等

# 国奖导师带你冲！！

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/25a530464aabdba54505a23e925e1892dbcc99ad06f6880799c7ec9e228eb9b7.jpg)


# 我们的优势

强大的师资力量

- 多对一全程服务

- 辅导前试听机制

- 无限次在线答疑

- 定制化课程内容

学员奖学金激励

# 课程设置

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/d509210f20c075750ce853c4ee8ed6b3dad1873a360eb39948c27aa139ff8050.jpg)


定制学习方案

根据学员基础，定制个性化培训方案

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/7e11bca193e454b17b12bc2dc76eddee5ce386bc06bfeb095267fec9df03b186.jpg)


算法及编程基础培训

根据方案，开展基础培训

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/032b249b94ce00f36ba26142f7c3337bdf48c032a3e479d32893c339e4d7f334.jpg)


刷题特训

导师精选题目，特训练习

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/eb715543aabc6bf6a6c3ca8c6a5cea6b8f5bfcba389353987598595cb085e00e.jpg)


全真模拟练习

竞赛限时全真模拟，体验竞赛氛围

# 课程亮点

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/28788bac9e03c9d59955b166828f51158a3bb5a066425beb397c8907dcee6a9d.jpg)


大牛授课

干货十足

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/45e0f782fe4107679b962f36c7129ddb68c5c6f6f1984b011fb3f4c73a19eebe.jpg)


全程伴学无限答疑

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/4d7d90700b8cca4afbb38b0295bf1dea7aa3e80645c1881d0e411f8b35fe1038.jpg)


绝密押题赛前助力

扫码立即报名>>>

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/bf59b763-691b-49fc-bc80-d1dbf7dd0c71/7fa754510b74f8542b489c9ae2e7d42c0121695d3730ac7e937a1853ac97d165.jpg)


将模型中给出的物理量与参数转化为算法可直接使用的输入，设置时间网格与初始状态，为数值积分做准备。

# (1) 数据文件

根据题述，问题一无外部数据文件，时间函数  $P(t)$  或  $(B(t),L(t),N(t),G(t),H(t))$  视为已知的解析表达式或可调用的时间函数，不涉及文件读取与清洗。

# (2) 初始条件与模型参数

1. 设定研究时间区间  $\mathcal{T} = [0,T]$ 。

2. 给定初始 SOC:

$$
s _ {0} = s (0), \quad 0 \leq s _ {0} \leq 1.
$$

3. 给定电池额定能量：

$$
E _ {\max} > 0.
$$

4. 初始能量由 SOC - 能量关系

$$
E (0) = E _ {\max} s (0)
$$

得到离散初值

$$
E _ {0} = E _ {\max } s _ {0}.
$$

5. 给定多因素模型中的功耗比例系数：

$$
k _ {\mathrm {s c r}}, k _ {\mathrm {c p u}}, k _ {\mathrm {n e t}}, k _ {\mathrm {g p s}}, k _ {\mathrm {b g}} > 0.
$$

6. 选择输入形式:

若采用基线模型，视总功耗轨迹  $P(t)$  为已知；

- 若采用多因素模型，视使用强度轨迹

$$
B (t), L (t), N (t), G (t), H (t)
$$

为已知，且满足

$$
0 \leq B (t), L (t), N (t), G (t), H (t) \leq 1.
$$

# (3) 算法初始参数设置

1. 选定时间步数  $N$ ，并令

$$
\Delta t = \frac {T}{N}, \quad t _ {n} = n \Delta t, n = 0, 1, \ldots , N.
$$

2. 设定误差容限  $\varepsilon > 0$ （例如相对误差或绝对误差容限），以及残差容限  $\varepsilon_{J} > 0$ （若采用残差判据）。

3. 选择积分方法  $\eta \in \{\mathrm{Trap},\mathrm{RK4}\}$

4. 初始化状态：

$$
s _ {0} \text {已 知}, E _ {0} = E _ {\max } s _ {0}.
$$

# 步骤 2：时间离散与中间变量构造

# - 步骤目的

在时间网格上构造所有连续变量的离散表示，并将模型中的关键公式转写为离散形式，为后续递推更新奠定基础。

# 数学-算法操作

# 1. SOC 与能量关系的离散化

连续关系

$$
s (t) = \frac {E (t)}{E _ {\max}}
$$

在离散时间点  $t_n$  上写为

$$
s _ {n} = \frac {E _ {n}}{E _ {\max}}, \quad E _ {n} = E _ {\max} s _ {n}, \quad n = 0, \ldots , N.
$$

在后续所有更新中只需显式更新  $s_n$ ， $E_n$  作为派生量由上述公式计算。

# 2. 功耗与能量变化的离散联系

能量微分方程

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t)
$$

在离散层面对应为

$$
\frac {E _ {n + 1} - E _ {n}}{\Delta t} \approx - P _ {n + 1 / 2},
$$

其中  $P_{n + 1 / 2}$  为  $[t_n,t_{n + 1}]$  上的总功耗代表值（例如取梯形平均值）。结合 $E_{n} = E_{\mathrm{max}}s_{n}$  ，可转化为SOC的差分形式

$$
\frac {s _ {n + 1} - s _ {n}}{\Delta t} \approx - \frac {1}{E _ {\mathrm {m a x}}} P _ {n + 1 / 2},
$$

这是后续所有数值积分公式的离散基础，对应模型中SOC基线微分方程和积分形式。

# 3. 多模块功耗分解的离散化

由连续功耗分解

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t),
$$

在离散点上得到

$$
P _ {n} = P _ {\mathrm {s c r}, n} + P _ {\mathrm {c p u}, n} + P _ {\mathrm {n e t}, n} + P _ {\mathrm {g p s}, n} + P _ {\mathrm {b g}, n}, \quad n = 0, \dots , N.
$$

# 4. 功耗-使用强度线性关系的离散化

对于多因素模型，将

$$
\begin{array}{l} P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t), \quad P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t), \quad P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t), \\ P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t), \quad P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t) \\ \end{array}
$$

离散为

$$
\begin{array}{l} P _ {\mathrm {s c r}, n} = k _ {\mathrm {s c r}} B _ {n}, \quad P _ {\mathrm {c p u}, n} = k _ {\mathrm {c p u}} L _ {n}, \quad P _ {\mathrm {n e t}, n} = k _ {\mathrm {n e t}} N _ {n}, \\ P _ {\mathrm {g p s}, n} = k _ {\mathrm {g p s}} G _ {n}, \quad P _ {\mathrm {b g}, n} = k _ {\mathrm {b g}} H _ {n}, \\ \end{array}
$$

并在每一步显式计算

$$
P _ {n} = k _ {\mathrm {s c r}} B _ {n} + k _ {\mathrm {c p u}} L _ {n} + k _ {\mathrm {n e t}} N _ {n} + k _ {\mathrm {g p s}} G _ {n} + k _ {\mathrm {b g}} H _ {n}.
$$

# 步骤3：基线SOC模型的数值积分（给定总功耗  $P(t)$ ）

# - 步骤目的

在仅已知总功耗轨迹  $P(t)$  的情形下，求解基线 SOC 动力学方程

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\mathrm {m a x}}}, \quad s (0) = s _ {0}
$$

的离散近似  $s_n$ ，并满足物理约束。

# 数学-算法操作

设

$$
f (t) = - \frac {P (t)}{E _ {\mathrm {m a x}}},
$$

则方程写为

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = f (t), \quad s (0) = s _ {0}.
$$

在离散时间点上：

# 1. 计算功耗样本

对每个  $n = 0,\dots ,N$  ，计算

$$
P _ {n} = P (t _ {n}), \quad f _ {n} = - \frac {P _ {n}}{E _ {\mathrm {m a x}}}.
$$

该步骤直接使用模型中的功耗- 能量关系和 SOC 微分方程。

# 2. 梯形积分法（若  $\eta = \mathrm{Trap}$ ）

在每个时间步  $[t_n, t_{n+1}]$  上，采用梯形法逼近积分

$$
s _ {n + 1} = s _ {n} + \int_ {t _ {n}} ^ {t _ {n + 1}} f (\tau) \mathrm {d} \tau \approx s _ {n} + \frac {\Delta t}{2} (f _ {n} + f _ {n + 1}).
$$

代入  $f_{n} = -P_{n} / E_{\max}$ , 得

$$
s _ {n + 1} \approx s _ {n} - \frac {\Delta t}{2 E _ {\max}} (P _ {n} + P _ {n + 1}).
$$

该更新公式是离散化的

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau
$$

在  $[t_n, t_{n+1}]$  上的局部实现。

# 3. 四阶 Runge-Kutta 法（若  $\eta = \mathrm{RK4}$ ）

若可在任意时刻计算  $P(t)$ , 则在每个步上定义

$$
\begin{array}{l} k _ {1} = f (t _ {n}) = - \frac {P (t _ {n})}{E _ {\mathrm {m a x}}}, \\ k _ {2} = f \left(t _ {n} + \frac {\Delta t}{2}\right) = - \frac {P \left(t _ {n} + \frac {\Delta t}{2}\right)}{E _ {\mathrm {m a x}}}, \\ k _ {3} = f \left(t _ {n} + \frac {\Delta t}{2}\right) = - \frac {P \left(t _ {n} + \frac {\Delta t}{2}\right)}{E _ {\mathrm {m a x}}}, \\ k _ {4} = f (t _ {n} + \Delta t) = - \frac {P (t _ {n} + \Delta t)}{E _ {\mathrm {m a x}}}, \\ \end{array}
$$

然后更新

$$
s _ {n + 1} = s _ {n} + \frac {\Delta t}{6} (k _ {1} + 2 k _ {2} + 2 k _ {3} + k _ {4}).
$$

若仅有离散  $P_{n}$ , 则可采用线性插值

$$
P (t _ {n} + \theta \Delta t) \approx (1 - \theta) P _ {n} + \theta P _ {n + 1}, \quad \theta \in [ 0, 1 ],
$$

用于计算  $k_{2}, k_{3}$  所需的中间功耗值。

# 4. 状态更新与能量计算

在每个时间步结束后，由更新得到的  $s_{n + 1}$  计算

$$
E _ {n + 1} = E _ {\max} s _ {n + 1}.
$$

这一步显式更新了决策变量  $s(t)$  的离散值和派生变量  $E(t)$ ，对应约束

$$
s (t) = \frac {E (t)}{E _ {\mathrm {m a x}}}.
$$

# 5. 基线约束的离散实现

将  $s_{n + 1}$  投影到  $[0,1]$ :

$$
s _ {n + 1} \leftarrow \min  \{1, \max  \{0, s _ {n + 1} \} \}.
$$

强制 SOC 单调不增（对应  $\frac{\mathrm{d}s(t)}{\mathrm{d}t} \leq 0$ ）：

$$
s _ {n + 1} \leftarrow \min  \{s _ {n}, s _ {n + 1} \}.
$$

若  $s_{n + 1} = 0$  ，则视电池能量用尽，可提前终止时间积分，保证离散 $E_{n} = E_{\mathrm{max}}s_{n}$  满足

$$
0 \leq E _ {n} \leq E _ {\max}.
$$

# 步骤 4: 多因素 SOC 模型的数值积分 (使用强度驱动)

# - 步骤目的

在给定使用强度轨迹  $B(t), L(t), N(t), G(t), H(t)$  的情形下，通过功耗分解

$$
P (t) = k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t)
$$

构造总功耗  $P(t)$ ，并代入 SOC 微分方程进行积分，得到多因素 SOC 轨迹  $s(t)$  及各子功耗轨迹。

# 数学-算法操作

对每个时间步  $n = 0,\dots ,N$

# 1. 读取或计算使用强度离散值

计算

$$
B _ {n} = B (t _ {n}), \quad L _ {n} = L (t _ {n}), \quad N _ {n} = N (t _ {n}), \quad G _ {n} = G (t _ {n}), \quad H _ {n} = H (t _ {n}).
$$

若数值误差使某些值略超出  $[0,1]$ ，则投影：

$$
B _ {n} \leftarrow \min  \{1, \max  \{0, B _ {n} \} \}, \quad \ldots , \quad H _ {n} \leftarrow \min  \{1, \max  \{0, H _ {n} \} \}.
$$

# 2. 根据线性子模型计算各模块功耗

利用模型中的线性关系

$$
\begin{array}{l} P _ {\mathrm {s c r}, n} = k _ {\mathrm {s c r}} B _ {n}, \\ P _ {\mathrm {c p u}, n} = k _ {\mathrm {c p u}} L _ {n}, \\ P _ {\mathrm {n e t}, n} = k _ {\mathrm {n e t}} N _ {n}, \\ P _ {\mathrm {g p s}, n} = k _ {\mathrm {g p s}} G _ {n}, \\ P _ {\mathrm {b g}, n} = k _ {\mathrm {b g}} H _ {n}, \\ \end{array}
$$

得到各子功耗的离散轨迹。因  $k_{\mathrm{c}} > 0$  且强度在  $[0,1]$ ，可确保

$$
P _ {\mathrm {s c r}, n}, P _ {\mathrm {c p u}, n}, P _ {\mathrm {n e t}, n}, P _ {\mathrm {g p s}, n}, P _ {\mathrm {b g}, n} \geq 0.
$$

# 3. 总功耗分解与合成

由能量守恒约束

# 数模美赛

# 转学术论文发表

前30名享600-2000元优惠报名即赠各类保奖班课程

# 服务内容

- 可转为EI会议/CPCI会议/高质量中英文期刊

- 免费提供论文方向评估及指导服务

# 发表周期

- 投稿后1个月左右录用

- 录用后2-7个月左右见刊

- 见刊后1-3个月左右检索

# 我们承诺

- 收费透明，含版面费，无任何二次收费

- 定金制，成功录用再补齐尾款，不录用全额退款

$$
P (t) = \sum_ {m \in \mathcal {M}} P _ {m} (t)
$$

得

$$
P _ {n} = P _ {\mathrm {s c r}, n} + P _ {\mathrm {c p u}, n} + P _ {\mathrm {n e t}, n} + P _ {\mathrm {g p s}, n} + P _ {\mathrm {b g}, n}.
$$

这是对模型中“功耗分解与使用模式映射”的离散实现。

# 4. SOC 方程右端构造

通过

$$
f _ {n} = - \frac {P _ {n}}{E _ {\mathrm {m a x}}}
$$

构造 SOC 微分方程的离散右端，等价于在连续方程

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{E _ {\mathrm {m a x}}} \big [ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t) \big ]
$$

上进行取样。

# 5. 时间积分更新 SOC

若采用梯形法，则在每个步  $[t_n, t_{n+1}]$  上

$$
s _ {n + 1} \approx s _ {n} - \frac {\Delta t}{2 E _ {\mathrm {m a x}}} (P _ {n} + P _ {n + 1}),
$$

其中  $P_{n + 1}$  按上述步骤在  $t_{n + 1}$  处计算。

若采用 RK4，则同样使用

$$
k _ {i} = - \frac {1}{E _ {\mathrm {m a x}}} P (\mathrm {相 应 阶 段 时 刻})
$$

的方式，在各阶段时刻通过线性关系计算所需的  $P$  值，然后更新

$$
s _ {n + 1} = s _ {n} + \frac {\Delta t}{6} (k _ {1} + 2 k _ {2} + 2 k _ {3} + k _ {4}).
$$

# 6. 更新能量与约束处理

使用

$$
E _ {n + 1} = E _ {\mathrm {m a x}} s _ {n + 1},
$$

并同基线模型一样对  $s_{n + 1}$  执行

$$
s _ {n + 1} \gets \min \{1, \max \{0, s _ {n + 1} \} \}, \quad s _ {n + 1} \gets \min \{s _ {n}, s _ {n + 1} \},
$$

保证

$$
0 \leq s _ {n + 1} \leq 1, \quad s _ {n + 1} \leq s _ {n}.
$$

# 步骤5：约束条件的系统性保证与残差计算

# - 步骤目的

综合保证离散解满足模型中列出的全部约束，并为收敛判据提供残差信息。

# 数学-算法操作

在完成所有时间步的积分后：

# 1. 能量范围与 SOC 范围

由

$$
E _ {n} = E _ {\max} s _ {n}, \quad 0 \leq s _ {n} \leq 1
$$

可直接得到

$$
0 \leq E _ {n} \leq E _ {\max }, \quad \forall n,
$$

即满足能量范围约束。

# 2. 放电单调性

通过每步的

$$
s _ {n + 1} \leftarrow \min  \left\{s _ {n}, s _ {n + 1} \right\}
$$

操作，可保证离散差商

$$
\frac {s _ {n + 1} - s _ {n}}{\Delta t} \leq 0,
$$

离散化地实现

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} \leq 0.
$$

# 3. 功耗非负与分解一致性

由

$$
P _ {\mathrm {s c r}, n} = k _ {\mathrm {s c r}} B _ {n}, \dots , P _ {\mathrm {b g}, n} = k _ {\mathrm {b g}} H _ {n}, \quad k. > 0, B _ {n}, \dots , H _ {n} \in [ 0, 1 ]
$$

可保证

$$
P _ {\mathrm {s c r}, n}, P _ {\mathrm {c p u}, n}, P _ {\mathrm {n e t}, n}, P _ {\mathrm {g p s}, n}, P _ {\mathrm {b g}, n} \geq 0,
$$

进而

$$
P _ {n} = \sum_ {m \in \mathcal {M}} P _ {m, n} \geq 0.
$$

若数值误差导致  $P_{m,n}$  或  $P_{n}$  极小负值，可强制

$$
P _ {m, n} \leftarrow \max  \{0, P _ {m, n} \}, \quad P _ {n} \leftarrow \sum_ {m} P _ {m, n}.
$$

# 4. 离散残差与目标泛函的数值近似

在每个时间步上计算离散残差

$$
r _ {n} = \frac {s _ {n + 1} - s _ {n}}{\Delta t} + \frac {1}{E _ {\mathrm {m a x}}} P _ {n + 1 / 2},
$$

其中  $P_{n+1/2}$  由插值或中点值给出。定义离散目标

$$
J _ {d} = \sum_ {n = 0} ^ {N - 1} r _ {n} ^ {2} \Delta t,
$$

则  $J_{d}$  逼近连续泛函  $J[s]$  。数值积分的精度越高， $J_{d}$  越接近零。

# 步骤 6: 收敛判据与终止条件

# - 步骤目的

确定何时结束时间步进及网格加密过程，保证数值解对连续模型的逼近达到预期精度。

# 数学-算法操作

# 1. 时间步进终止条件

在单次积分运行中，时间循环在以下任一条件满足时终止：

时间到达研究上界： $t_N = T$ ；

- 电池电量耗尽：某个  $n^{*}$  满足  $s_{n^{*}} = 0$  ，则对于所有  $n \geq n^{*}$  ，可令  $s_{n} = 0$  、  $E_{n} = 0$  并终止积分。

# 2. 时间离散精度收敛判据

为控制时间离散误差，可以采用网格加密比较法：

- 第  $k$  次运行选用步长  $\Delta t^{(k)}$ , 对应解记为  $\{s_n^{(k)}\}$ ;

- 第  $k + 1$  次运行选用更小步长（例如  $\Delta t^{(k + 1)} = \Delta t^{(k)} / 2$ ），得到  $\{s_n^{(k + 1)}\}$ ；

将细网格解插值到粗网格时间点，计算最大差异

$$
\delta^ {(k + 1)} = \max _ {n} | s _ {n} ^ {(k + 1)} - s _ {n} ^ {(k)} |;
$$

若

$$
\delta^ {(k + 1)} \leq \varepsilon ,
$$

则认为时间离散已收敛，可以停止继续加密网格。

# 3. 残差判据（可选）

使用步骤5中的离散残差  $r_n$  和目标  $J_{d}$  ，若满足

$$
J _ {d} \leq \varepsilon_ {J}
$$

或

$$
\max  _ {n} | r _ {n} | \leq \varepsilon_ {r},
$$

(其中  $\varepsilon_{r}$  为指定残差阈值), 则认为数值解在物理方程意义上已足够接近连续模型的精确解。

# 2.3 结果生成

数值求解完成后，可得到如下与【问题输出】对应的结果及其物理/几何含义：

# 1. SOC 连续时间演化方程（基线模型）

○ 方程形式：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\mathrm {m a x}}}, \quad s (0) = s _ {0},
$$

及其积分形式

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} P (\tau) \mathrm {d} \tau .
$$

。数值结果：算法给出在网格  $\{t_n\}$  上的近似值  $\{s_n\}$ ，并可通过分段线性插值构造近似连续轨迹  $\hat{s}(t)$ 。

。物理含义：该方程直接体现“累计功耗导致SOC线性下降”的能量守恒规律，  $E_{\mathrm{max}}$  决定在给定功耗下SOC下降的尺度。

# 2. 扩展 SOC 模型方程（多因素模型）

○ 方程形式：

$$
\begin{array}{l} \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{E _ {\max}} \left[ k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t) \right], \quad s (0) \\ = s _ {0}, \\ \end{array}
$$

及其积分形式

$$
s (t) = s _ {0} - \frac {1}{E _ {\mathrm {m a x}}} \int_ {0} ^ {t} \left[ k _ {\mathrm {s c r}} B (\tau) + k _ {\mathrm {c p u}} L (\tau) + k _ {\mathrm {n e t}} N (\tau) + k _ {\mathrm {g p s}} G (\tau) + k _ {\mathrm {b g}} H (\tau) \right] \mathrm {d} \tau .
$$

。数值结果：在时间网格上得到 SOC 轨迹  $\{s_{n}\}$ ，并同时得到各使用强度轨迹及其功耗贡献。

物理含义: 该方程明确将用户使用模式  $(B, L, N, G, H)$  映射到 SOC 衰减速率, 每一项  $k$ . 与对应强度的乘积表示该模块在单位时间内对 SOC 的贡献。

# 3. 功耗分解与使用模式映射关系

○ 功耗分解：

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t),
$$

数值上在网格上体现为

$$
P _ {n} = P _ {\mathrm {s c r}, n} + P _ {\mathrm {c p u}, n} + P _ {\mathrm {n e t}, n} + P _ {\mathrm {g p s}, n} + P _ {\mathrm {b g}, n}.
$$

○ 使用模式映射（线性关系）：

$$
\begin{array}{l} P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t), \\ P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t), \\ P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t), \\ P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t), \\ P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t), \\ \end{array}
$$

离散为

$$
\begin{array}{l} P _ {\mathrm {s c r}, n} = k _ {\mathrm {s c r}} B _ {n}, \quad P _ {\mathrm {c p u}, n} = k _ {\mathrm {c p u}} L _ {n}, \quad P _ {\mathrm {n e t}, n} = k _ {\mathrm {n e t}} N _ {n}, \quad P _ {\mathrm {g p s}, n} = k _ {\mathrm {g p s}} G _ {n}, \quad P _ {\mathrm {b g}, n} = k _ {\mathrm {b g}} \mathrm {a l p h a} \\ \mathbf {\Sigma} = k _ {\mathrm {b g}} H _ {n}. \\ \end{array}
$$

$\mathrm{O}$  数值结果：算法输出  $\{P_n\}$  以及各子功耗轨迹

$$
\{P _ {\mathrm {s c r}, n} \}, \{P _ {\mathrm {c p u}, n} \}, \{P _ {\mathrm {n e t}, n} \}, \{P _ {\mathrm {g p s}, n} \}, \{P _ {\mathrm {b g}, n} \},
$$

并可进一步通过

$$
\Delta E _ {\mathrm {s c r}} \approx \sum_ {n} P _ {\mathrm {s c r}, n} \Delta t, \quad \dots
$$

估计各模块累计能量消耗。

○ 物理含义：该分解将整体功耗拆分为由屏幕、CPU、网络、GPS和后台任务分别贡献的部分，并通过归一化强度  $(B,L,N,G,H)$  定量描述用户使用模式与能量消耗的映射。

# 4. 模型参数清单及其角色说明

$E_{\max}$  : 电池额定总能量, 出现在

$$
s (t) = \frac {E (t)}{E _ {\max}}, \quad \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{E _ {\max}}
$$

中，决定同一功耗下SOC变化的尺度。  $E_{\mathrm{max}}$  越大，在同样的功耗轨迹下SOC下降越慢。

○  $k_{\mathrm{scr}}$  : 屏幕在单位强度  $B(t)$  下的功耗系数, 出现在

$$
P _ {\mathrm {s c r}} (t) = k _ {\mathrm {s c r}} B (t)
$$

中， $k_{\mathrm{scr}}$  越大，屏幕亮度对总功耗与 SOC 衰减的影响越大。

○  $k_{\mathrm{cpu}}$  ：CPU在单位负载  $L(t)$  下的功耗系数，出现在

$$
P _ {\mathrm {c p u}} (t) = k _ {\mathrm {c p u}} L (t)
$$

中，反映CPU负载对电量消耗的敏感度。

○  $k_{\mathrm{net}}$  ：网络模块在单位活动强度  $N(t)$  下的功耗系数，出现在

$$
P _ {\mathrm {n e t}} (t) = k _ {\mathrm {n e t}} N (t)
$$

中，决定网络通信对SOC的贡献。

○  $k_{\mathrm{gps}}$  : GPS 在单位使用强度  $G(t)$  下的功耗系数, 出现在

$$
P _ {\mathrm {g p s}} (t) = k _ {\mathrm {g p s}} G (t)
$$

中，体现定位功能对电量消耗的影响。

○  $k_{\mathrm{bg}}$  ：后台任务在单位活动强度  $H(t)$  下的功耗系数，出现在

$$
P _ {\mathrm {b g}} (t) = k _ {\mathrm {b g}} H (t)
$$

中，量化后台进程和系统服务的隐性功耗。

。数值求解中，所有这些参数通过

$$
P (t) = k _ {\mathrm {s c r}} B (t) + k _ {\mathrm {c p u}} L (t) + k _ {\mathrm {n e t}} N (t) + k _ {\mathrm {g p s}} G (t) + k _ {\mathrm {b g}} H (t)
$$

进入SOC微分方程右端，从而直接决定  $\frac{\mathrm{d}s(t)}{\mathrm{d}t}$  的大小与变化趋势。参数越大，对应模块在相同强度下产生的功耗越高，SOC曲线下降越快。

通过上述结果，后续可在参数估计与验证阶段利用观测的  $s(t)$  与使用强度轨迹反推  $E_{\mathrm{max}}$  与各  $k$  的数值，使模型在实际设备上的预测能力得到校准。

# 问题二

# 1.3.3 决策变量

SOC轨迹  $s(t;s_0,k)$

对每个初始  $\mathrm{SOC} s_0 \in \mathcal{S}$  和场景  $k \in \mathcal{K}$ ,  $s(t; s_0, k)$  为在仅放电条件下的 SOC 百分比曲线, 是定义在  $t \in [0, \infty)$  上的绝对连续函数, 满足  $0 \leq s(t; s_0, k) \leq 100$ , 且在  $t \in [0, T_p(s_0, k)]$  内单调不增。

预测耗尽时间  $T_{p}(s_{0}, k)$

对每个  $(s_0, k)$ ,  $T_p(s_0, k) \geq 0$  为根据 SOC-功耗动力学预测的从  $t = 0$  到 SOC 下降到  $s_{\min}$  的时间，是标量决策变量。

- 耗尽时间预测区间  $T_{p}^{\min}(s_{0}, k)$  与  $T_{p}^{\max}(s_{0}, k)$ :

在给定功耗上下界轨迹  $P_{\mathrm{min}}^{(k)}(t)$  、  $P_{\mathrm{max}}^{(k)}(t)$  的情形下，  $T_{p}^{\mathrm{min}}(s_{0},k)$  与  $T_{p}^{\mathrm{max}}(s_{0},k)$  分别表示该  $(s_0,k)$  组合下耗尽时间的最悲观（最快耗尽）与最乐观（最慢耗尽）预测，满足  $0\leq T_p^{\mathrm{min}}\leq T_p^{\mathrm{max}}$  。

- 耗尽时间预测误差  $E_{T}(s_{0},k)$

定义为模型预测耗尽时间与观测/合理耗尽时间的差值，可正可负，是用于评价模型精度的标量决策变量。

- 预测不确定性  $\sigma_{T}(s_{0}, k)$

用以表征  $(s_0, k)$  组合下耗尽时间预测的区间宽度或等效标准差，满足  $\sigma_T(s_0, k) \geq 0$ 。

# 2026 美赛赛中保奖班

赠送3份美赛精品课

保M奖1v1

# 预售价7500元

原价8999

- 赛中不限课时指导+无限次数答疑

- 赠送价值399的美赛大班课，一个队伍送三份，优惠  $1000 +!$

• 试听课机制保障，老师均是O/F奖或国/研赛国一得主，你的老师由你检验

保H奖1v1

# 预售价3999元

原价4588

- 赛中不限课时指导+无限次数答疑

- 赠送价值399的美赛大班课，一个队伍送三份，优惠  $1000 +!$

- 试听课机制保障，老师均是F/M奖或国/研赛二等奖以上得主，你的老师由你检验

- 平均功率与功耗贡献  $\overline{P}_i(s_0,k)$  、  $\overline{P}(s_0,k)$  、  $\rho_i(s_0,k)$  ：

对每个  $(s_0,k)$  ，  $\overline{P}_i(s_0,k)\geq 0$  为功耗分量  $i$  在从  $t = 0$  到  $t = T_{p}(s_{0},k)$  期间的时间平均功率；  $\overline{P} (s_0,k) = \sum_{i\in \mathcal{I}}\overline{P}_i(s_0,k)$  为总平均功率；  $\rho_{i}(s_{0},k)\in [0,1]$  为分量  $i$  对总平均功率的贡献占比，满足  $\sum_{i}\rho_{i}(s_{0},k) = 1$  。

评价函数值  $J$

用于汇总所有  $(s_{0}, k)$  组合的耗尽时间预测误差（例如加权均方误差），是用来刻画整体拟合优劣的非负标量。

# 1.4. 模型的构建与推导

# 1.4.1 中间变量与子模型构建

# 5. 能量守恒与SOC动力学

物理上，电池储存的剩余能量  $E(t)$  随时间的变化由手机对外输出的瞬时功耗 $P^{(k)}(t)$  决定。在场景  $k$  下，若规定“电池向外输出能量为正”，则能量守恒给出

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P ^ {(k)} (t), \qquad t \geq 0.
$$

SOC 百分比  $s(t; s_0, k)$  定义为剩余能量相对于场景  $k$  下等效满电能量  $E_{\mathrm{max}}^{(k)}$  的百分比：

$$
s (t; s _ {0}, k) = 1 0 0 \frac {E (t)}{E _ {\mathrm {m a x}} ^ {(k)}}.
$$

对该关系随时间求导，并代入能量守恒方程，可得到SOC百分比的变化率

$$
\frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} = \frac {1 0 0}{E _ {\max} ^ {(k)}} \frac {\mathrm {d} E (t)}{\mathrm {d} t} = - \frac {1 0 0}{E _ {\max} ^ {(k)}} P ^ {(k)} (t) = - \kappa^ {(k)} P ^ {(k)} (t),
$$

其中

$$
\kappa^ {(k)} = \frac {1 0 0}{E _ {\mathrm {m a x}} ^ {(k)}} > 0
$$

为场景  $k$  下将功耗转换为 SOC 百分比下降速率的比例系数，它综合反映了电池容量、工作电压及环境温度  $T_{\mathrm{env}}^{(k)}$  等条件的影响。

结合初始条件  $s(0;s_0,k) = s_0$  ，可写出SOC的积分形式：

$$
s (t; s _ {0}, k) = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {t} P ^ {(k)} (\tau) \mathrm {d} \tau , \qquad t \geq 0.
$$

# 6. 耗尽时间（TTE）的定义

“耗尽时间”指 SOC 首次降至阈值  $s_{\mathrm{min}}$  的时刻。对固定  $(s_0, k)$ , 在假定 SOC 单调不增的前提下 (仅放电), 耗尽时间  $T_p(s_0, k)$  由条件

$$
s (T _ {p} (s _ {0}, k); s _ {0}, k) = s _ {\min }, \qquad s (t; s _ {0}, k) > s _ {\min }, \forall t \in [ 0, T _ {p} (s _ {0}, k))
$$

唯一确定。将 SOC 积分表达式代入上式得到能量平衡方程

$$
s _ {\min } = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P ^ {(k)} (\tau) d \tau .
$$

这表明，从初始SOC  $s_0$  降到阈值  $s_{\mathrm{min}}$  所对应的SOC百分比差值  $s_0 - s_{\mathrm{min}}$  ，等于在耗尽时间内功耗积分经比例系数  $\kappa^{(k)}$  放缩后的结果。

# 7. 功耗分解与各分量平均功率

为识别具体活动或功能模块对耗电的贡献，将总功耗分解为各功耗分量之和：

$$
P ^ {(k)} (t) = \sum_ {i \in \mathcal {I}} P _ {i} ^ {(k)} (t) = P _ {\mathrm {s c r}} ^ {(k)} (t) + P _ {\mathrm {c p u}} ^ {(k)} (t) + P _ {\mathrm {n e t}} ^ {(k)} (t) + P _ {\mathrm {g p s}} ^ {(k)} (t) + P _ {\mathrm {b g}} ^ {(k)} (t).
$$

在  $(s_0,k)$  组合下、从放电开始  $t = 0$  到预测耗尽时刻  $t = T_{p}(s_{0},k)$ ，定义功耗分量  $i$  的时间平均功率为

$$
\overline {{P}} _ {i} (s _ {0}, k) = \frac {1}{T _ {p} (s _ {0} , k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) \mathrm {d} t, \qquad i \in \mathcal {I},
$$

总平均功率为

$$
\overline {{P}} (s _ {0}, k) = \sum_ {i \in \mathcal {I}} \overline {{P}} _ {i} (s _ {0}, k).
$$

对应的累计能量消耗为

$$
E _ {i} (s _ {0}, k) = \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) d t = \overline {{P}} _ {i} (s _ {0}, k) T _ {p} (s _ {0}, k),
$$

$$
E _ {\mathbf {t o t}} (s _ {\mathbf {0}}, k) = \int_ {\mathbf {0}} ^ {T _ {p} (s _ {\mathbf {0}}, k)} P ^ {(k)} (t) \mathrm {d} t = \overline {{P}} (s _ {\mathbf {0}}, k) T _ {p} (s _ {\mathbf {0}}, k).
$$

与能量-SOC 平衡方程相对应，还应有

$$
E _ {\mathrm {t o t}} (s _ {0}, k) = \frac {E _ {\mathrm {m a x}} ^ {(k)}}{1 0 0} (s _ {0} - s _ {\mathrm {m i n}}).
$$

为量化各功耗分量对能量消耗（进而对耗尽时间缩短）的贡献，引入功耗贡献占比

$$
\rho_ {i} (s _ {0}, k) = \frac {\overline {{P}} _ {i} (s _ {0} , k)}{\overline {{P}} (s _ {0} , k)} = \frac {E _ {i} (s _ {0} , k)}{E _ {\mathrm {t o t}} (s _ {0} , k)}, \qquad i \in \mathcal {I},
$$

显然  $\rho_{i}(s_{0},k)\in [0,1]$  且  $\sum_{i\in \mathcal{I}}\rho_{i}(s_{0},k) = 1$  。在相同  $(s_0,k)$  下，  $\rho_{i}$  越大，说明该活动模块在总能量消耗中的占比越高，对耗尽时间缩短的贡献越大。

# 8. 功耗不确定性与耗尽时间预测区间

实际运行中，即使在同一场景  $k$  下，总功耗轨迹  $P^{(k)}(t)$  也会因网络状况、后台调度、温度波动等因素而呈现不确定性。为在模型中反映这种不确定性，可以给出总功耗的“名义轨迹”  $P^{(k)}(t)$ ，同时给出在物理上合理的上、下界轨迹  $P_{\mathrm{min}}^{(k)}(t)$  和  $P_{\mathrm{max}}^{(k)}(t)$ ，满足

$$
P _ {\min } ^ {(k)} (t) \leq P ^ {(k)} (t) \leq P _ {\max } ^ {(k)} (t), \quad \forall t \geq 0.
$$

对于固定  $(s_0,k)$  ，以  $P_{\mathrm{max}}^{(k)}(t)$  作为“最坏情况”（功耗最大），对应的耗尽时间 $T_{p}^{\mathrm{min}}(s_0,k)$  由

$$
s _ {\mathrm {m i n}} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\mathrm {m i n}} (s _ {0}, k)} P _ {\mathrm {m a x}} ^ {(k)} (\tau) \mathrm {d} \tau
$$

隐式确定；以  $P_{\mathrm{min}}^{(k)}(t)$  作为“最好情况”（功耗最小），对应的耗尽时间 $T_{p}^{\max}(s_{0},k)$  由

$$
s _ {\mathrm {m i n}} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\mathrm {m a x}} (s _ {0}, k)} P _ {\mathrm {m i n}} ^ {(k)} (\tau) \mathrm {d} \tau
$$

隐式确定，其中必有  $T_{p}^{\min}(s_{0},k)\leq T_{p}(s_{0},k)\leq T_{p}^{\max}(s_{0},k)$

为用单一标量概括耗尽时间预测的不确定性，可定义

$$
\sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max} (s _ {0} , k) - T _ {p} ^ {\min} (s _ {0} , k)}{2} \geq 0,
$$

将  $[T_p^{\mathrm{min}}, T_p^{\mathrm{max}}]$  视为围绕  $T_p$  的一条对称区间时， $\sigma_T$  可理解为“预测区间半宽度”，与标准差或置信区间半宽度具有类似解释。

# 9. 预测误差与模型表现描述指标

在每个  $(s_0,k)$  组合下，观测或认为合理的耗尽时间为  $T_{o}(s_{0},k)$ ，模型给出的点预测为  $T_{p}(s_{0},k)$ 。定义耗尽时间预测误差

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k),
$$

其正负号分别代表模型低估或高估续航时间。

为在不同  $(s_0,k)$  之间归纳模型表现，可利用阈值  $\varepsilon$  与  $\delta$  定义“拟合良好”的情形集合：

$$
\mathcal {G} = \{(s _ {0}, k) | | E _ {T} (s _ {0}, k) | \leq \varepsilon , \sigma_ {T} (s _ {0}, k) \leq \delta \},
$$

其补集  $\mathcal{B} = (\mathcal{S}\times \mathcal{K})\backslash \mathcal{G}$  即对应模型表现较差或不确定性较大的情形。

# 1.4.2 目标函数

从业务角度看，模型的“求解目标”是构建一个在各种  $(s_0, k)$  组合下能够较准确预测耗尽时间、并能解释耗尽时间差异的数学映射。为对整体预测精度进行定量评价，可以采用加权均方误差作为目标函数：

- 使用前述误差定义  $E_{T}(s_{0},k)$ ，对所有考虑的  $(s_0,k) \in \mathcal{S} \times \mathcal{K}$  组合，构造整体评价函数

$$
J = \sum_ {s _ {0} \in \mathcal {S}} \sum_ {k \in \mathcal {K}} w _ {s _ {0}, k} E _ {T} (s _ {0}, k) ^ {2},
$$

其中权重  $w_{S_0, k} \geq 0$  可用于体现某些初始电量或场景的重要性（例如对常用场景赋予更高权重）。

在模型标定或参数调整时，可以以“在给定约束条件下使  $J$  最小”为求解目标；在仅进行模型评估时，则将  $J$  视为模型总体偏差的量化指标，并结合  $\sigma_T(s_0, k)$  与贡献占比  $\rho_i(s_0, k)$  分析模型适用范围与主导耗电因素。

# 1.4.3 约束条件

# (1) SOC 动力学与能量守恒约束：

在每个场景  $k$  下, SOC 随时间的演化由总功耗决定, 满足能量守恒关系抽象出的 SOC 微分方程及初始条件:

$$
\frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} = - \kappa^ {(k)} P ^ {(k)} (t), \qquad s (0; s _ {0}, k) = s _ {0}.
$$

# (2) 总功耗与分量功耗的加和约束：

在任意时刻  $t$ , 总功耗等于各功耗分量之和:

$$
P ^ {(k)} (t) = \sum_ {i \in \mathcal {I}} P _ {i} ^ {(k)} (t), \quad \forall t \geq 0, \forall k \in \mathcal {K}.
$$

# (3) 功耗与 SOC 非负及单调性约束:

手机仅消耗电能，不向电池回馈能量，因而所有功耗非负；SOC 作为剩余能量比例，且在仅放电过程中单调不增：

$$
P _ {i} ^ {(k)} (t) \geq 0, \quad P ^ {(k)} (t) \geq 0, \quad \forall t \geq 0, \forall i \in \mathcal {I}, k \in \mathcal {K},
$$

$$
\mathbf {0} \leq s (t; s _ {\mathbf {0}}, k) \leq \mathbf {1 0 0}, \quad \frac {\mathrm {d} s (t ; s _ {\mathbf {0}} , k)}{\mathrm {d} t} \leq \mathbf {0}, \quad \forall t \in [ \mathbf {0}, T _ {p} (s _ {\mathbf {0}}, k) ], \forall (s _ {\mathbf {0}}, k).
$$

# (4) 耗尽时间定义约束：

对于每个  $(s_0,k)$  ，预测耗尽时间  $T_{p}(s_{0},k)$  需满足SOC首次达到阈值  $s_{\mathrm{min}}$  的条件：

$$
s (T _ {p} (s _ {0}, k); s _ {0}, k) = s _ {\min}, \qquad s (t; s _ {0}, k) > s _ {\min}, \forall t \in [ 0, T _ {p} (s _ {0}, k)),
$$

且时间本身必须非负：

$$
T _ {p} (s _ {0}, k) \geq 0.
$$

将SOC的积分形式代入可得到等价的积分约束：

$$
s _ {\min } = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P ^ {(k)} (\tau) \mathrm {d} \tau , \quad \forall (s _ {0}, k).
$$

# (5) 耗尽时间预测区间与不确定性约束：

使用总功耗上下界轨迹  $P_{\mathrm{min}}^{(k)}(t)$  、  $P_{\mathrm{max}}^{(k)}(t)$  以刻画功耗不确定性时，耗尽时间上下界应分别满足

$$
\begin{array}{l} s _ {\mathrm {m i n}} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\mathrm {m i n}} (s _ {0}, k)} P _ {\mathrm {m a x}} ^ {(k)} (\tau) \mathrm {d} \tau , \\ s _ {\min } = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\max } (s _ {0}, k)} P _ {\min } ^ {(k)} (\tau) d \tau , \\ \end{array}
$$

并有

$$
0 \leq T _ {p} ^ {\min } (s _ {0}, k) \leq T _ {p} ^ {\max } (s _ {0}, k).
$$

预测不确定性由区间半宽度定义:

$$
\sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max} (s _ {0} , k) - T _ {p} ^ {\min} (s _ {0} , k)}{2}, \qquad \sigma_ {T} (s _ {0}, k) \geq 0.
$$

# (6) 平均功率与功耗贡献占比约束：

对每个  $(s_0, k)$ , 平均功率与贡献占比需满足定义关系:

$$
\overline {{P}} _ {i} (s _ {0}, k) = \frac {1}{T _ {p} (s _ {0} , k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) d t, \qquad i \in \mathcal {I},
$$

$$
\overline {{P}} (s _ {\mathbf {0}}, k) = \sum_ {i \in \mathcal {I}} \overline {{P}} _ {i} (s _ {\mathbf {0}}, k),
$$

$$
\rho_ {i} (s _ {\mathbf {0}}, k) = \frac {\overline {{P}} _ {i} (s _ {\mathbf {0}} , k)}{\overline {{P}} (s _ {\mathbf {0}} , k)}, \qquad \mathbf {0} \leq \rho_ {i} (s _ {\mathbf {0}}, k) \leq \mathbf {1}, \quad \sum_ {i \in \mathcal {I}} \rho_ {i} (s _ {\mathbf {0}}, k) = \mathbf {1}.
$$

# (7) 预测误差定义与观测时间非负约束：

对每个  $(s_{0}, k)$ , 预测误差按照观测值与预测值之差定义, 观测耗尽时间为非负:

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k),
$$

$$
T _ {o} (s _ {\mathbf {0}}, k) \geq \mathbf {0}.
$$

# (8) 模型表现好/差的条件划分约束：

利用误差阈值  $\varepsilon$  与不确定性阈值  $\delta$ ，将  $(s_0, k)$  组合划分为“模型表现较好”和“易失准”两类；其集合定义为

$$
\mathcal {G} = \{(s _ {0}, k) \in \mathcal {S} \times \mathcal {K} | | E _ {T} (s _ {0}, k) | \leq \varepsilon , \sigma_ {T} (s _ {0}, k) \leq \delta \},
$$

$$
\mathcal {B} = (\mathcal {S} \times \mathcal {K}) \backslash \mathcal {G},
$$

其中  $\mathcal{G}$  对应模型在该情形下与观测行为吻合、且预测不确定性较小的区域， $\mathcal{B}$  则对应模型偏离或不确定性过大的区域。

# 1.5 模型汇总

综合上述构建，可将问题二形式化为如下标准数学模型：

- 在给定电池参数  $\{C, E_{\mathrm{max}}^{(k)}, s_{\mathrm{min}}\}$  、环境条件  $T_{\mathrm{env}}^{(k)}$  、各场景功耗轨迹  $P_{i}^{(k)}(t)$  、观测耗尽时间  $T_{o}(s_{0}, k)$  以及评价权重  $w_{s_{0}, k}$  的前提下，

- 决定 SOC 轨迹  $s(t; s_0, k)$  、预测耗尽时间  $T_p(s_0, k)$  、耗尽时间预测区间  $[T_p^{\min}(s_0, k), T_p^{\max}(s_0, k)]$  、不确定性指标  $\sigma_T(s_0, k)$  、误差  $E_T(s_0, k)$  、平均功率  $\overline{P}_i(s_0, k)$  、总平均功率  $\overline{P}(s_0, k)$  与功耗贡献占比  $\rho_i(s_0, k)$ ，使得

目标函数（整体拟合优度）

$$
\min  J = \sum_ {s _ {0} \in \mathcal {S}} \sum_ {k \in \mathcal {K}} w _ {s _ {0}, k} [ T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k) ] ^ {2}
$$

在以下约束条件下成立：

10. SOC 动力学与能量守恒：

$$
\frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} = - \kappa^ {(k)} P ^ {(k)} (t), \quad s (0; s _ {0}, k) = s _ {0}.
$$

11. 总功耗与各功耗分量的加和关系：

$$
P ^ {(k)} (t) = \sum_ {i \in \mathcal {I}} P _ {i} ^ {(k)} (t).
$$

12. 功耗非负性与 SOC 范围及单调性：

$$
P _ {i} ^ {(k)} (t) \geq 0, P ^ {(k)} (t) \geq 0, 0 \leq s (t; s _ {0}, k) \leq 1 0 0, \frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} \leq 0.
$$

13. 耗尽时间定义与积分平衡：

$$
s (T _ {p} (s _ {0}, k); s _ {0}, k) = s _ {\min }, \quad T _ {p} (s _ {0}, k) \geq 0,
$$

$$
s _ {\mathrm {m i n}} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P ^ {(k)} (\tau) \mathrm {d} \tau .
$$

14. 功耗不确定性引出的耗尽时间上下界与不确定性：

$$
s _ {\mathrm {m i n}} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\mathrm {m i n}} (s _ {0}, k)} P _ {\mathrm {m a x}} ^ {(k)} (\tau) \mathrm {d} \tau ,
$$

$$
s _ {\min } = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} ^ {\max } (s _ {0}, k)} P _ {\min } ^ {(k)} (\tau) d \tau ,
$$

$$
0 \leq T _ {p} ^ {\min } (s _ {0}, k) \leq T _ {p} ^ {\max } (s _ {0}, k), \quad \sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max } (s _ {0} , k) - T _ {p} ^ {\min } (s _ {0} , k)}{2} \geq 0.
$$

15. 平均功率与功耗贡献占比：

$$
\overline {{P}} _ {i} (s _ {0}, k) = \frac {1}{T _ {p} (s _ {0} , k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) d t,
$$

$$
\overline {{P}} (s _ {0}, k) = \sum_ {i \in \mathcal {I}} \overline {{P}} _ {i} (s _ {0}, k),
$$

$$
\rho_ {i} (s _ {0}, k) = \frac {\overline {{P}} _ {i} (s _ {0} , k)}{\overline {{P}} (s _ {0} , k)}, \quad 0 \leq \rho_ {i} (s _ {0}, k) \leq 1, \quad \sum_ {i \in \mathcal {I}} \rho_ {i} (s _ {0}, k) = 1.
$$

16. 预测误差与观测耗尽时间非负：

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k), \qquad T _ {o} (s _ {0}, k) \geq 0.
$$

17. 模型表现区间划分：

$$
\mathcal {G} = \{(s _ {0}, k) | | E _ {T} (s _ {0}, k) | \leq \varepsilon , \sigma_ {T} (s _ {0}, k) \leq \delta \}, \quad \mathcal {B} = (\mathcal {S} \times \mathcal {K}) \backslash \mathcal {G}.
$$

该模型以能量守恒为核心，将“使用场景  $\rightarrow$  功耗分量轨迹  $\rightarrow$  总功耗  $\rightarrow$  SOC 演化  $\rightarrow$  耗尽时间”的物理链条完整形式化；通过引入功耗分解、平均功率与贡献占比，给出了分析各活动和条件对耗尽时间影响强弱的定量指标；通过误差与不确定性约束以及评价函数  $J$ ，能够系统地比较  $T_{p}$  与  $T_{o}$ ，划分模型表现优劣情形，并为识别“导致快速耗电的主要活动/条件”以及“影响出乎意料地小的因素”提供统一的数学框架。

# 问题二的模型求解

# 2.1 算法设计

算法名称：

基于SOC数值积分与首达阈值事件检测的耗尽时间求解算法（Runge-Kutta+ 首达阈值搜索）。

基本原理概述：

在场景  $k$  下, SOC 演化由一阶常微分方程

$$
\frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} = - \kappa^ {(k)} P ^ {(k)} (t), \quad s (0; s _ {0}, k) = s _ {0}
$$

给出（对应模型“SOC动力学与能量守恒约束”）。

耗尽时间  $T_{p}(s_{0},k)$  是SOC轨迹首次满足

$$
s \left(T _ {p} \left(s _ {0}, k\right); s _ {0}, k\right) = s _ {\min }, \quad s (t; s _ {0}, k) > s _ {\min } \quad \left(0 \leq t <   T _ {p}\right)
$$

的“首达时间”。

解析上  $T_{p}$  由积分形式

$$
s (t; s _ {0}, k) = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {t} P ^ {(k)} (\tau) d \tau
$$

与

$$
s _ {\min} = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P ^ {(k)} (\tau) \mathrm {d} \tau
$$

隐式确定。由于  $P^{(k)}(t)$  一般为任意随时间变化的轨迹，无显式解析解，因此采用：

18. 用 Runge-Kutta 数值积分在离散时刻  $t_n$  上构造近似 SOC 轨迹  $s_n \approx s(t_n; s_0, k)$ ;

19. 在积分过程中监测何时出现  $s_n > s_{\min}$  且  $s_{n+1} \leq s_{\min}$  的“阈值跨越”；

20. 在跨起步区间  $[t_{n}, t_{n+1}]$  内，通过线性插值或基于

$$
g (T) = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T} P ^ {(k)} (\tau) d \tau - s _ {\min }
$$

的一维求根（如二分法）精细定位  $T_{p}(s_{0},k)$

同理，以  $P_{\mathrm{max}}^{(k)}(t)$  、  $P_{\mathrm{min}}^{(k)}(t)$  代替  $P^{(k)}(t)$  ，可得到  $T_{p}^{\mathrm{min}}(s_{0},k)$  、 $T_{p}^{\mathrm{max}}(s_{0},k)$  ，从而根据

$$
\sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max} (s _ {0} , k) - T _ {p} ^ {\min} (s _ {0} , k)}{2}
$$

量化不确定性。

之后，在  $[0, T_{p}(s_{0}, k)]$  上对各分量功耗  $P_{i}^{(k)}(t)$  积分，按

$$
\overline {{P}} _ {i} (s _ {0}, k) = \frac {1}{T _ {p} (s _ {0} , k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) d t
$$

$$
\rho_ {i} (s _ {\mathbf {0}}, k) = \frac {\overline {{P}} _ {i} (s _ {\mathbf {0}} , k)}{\overline {{P}} (s _ {\mathbf {0}} , k)}, \quad \overline {{P}} (s _ {\mathbf {0}}, k) = \sum_ {i \in \mathcal {I}} \overline {{P}} _ {i} (s _ {\mathbf {0}}, k)
$$

得到各功耗分量的平均功率和贡献占比，用于分析耗尽时间差异的驱动因素。

算法选择的必要性与模型特性结合：

- 模型核心是线性一阶 ODE 与时间积分约束,  $P^{(k)}(t)$  仅被假定为已知非负轨迹, 并不要求常数或简单解析形式。

因此解析地对

$$
s _ {0} - s _ {\min } = \kappa^ {(k)} \int_ {0} ^ {T _ {p} (s _ {0}, k)} P ^ {(k)} (\tau) \mathrm {d} \tau
$$

反解  $T_{p}$  在一般情形下不可行，必须采用数值积分与数值求根。

- 该问题不是高维组合优化，而是对每个  $(s_0, k)$  的一维时间演化和一维阈值搜索，结构简单但受约束：

○ SOC 必须满足  $0 \leq s(t; s_0, k) \leq 100$  且单调不增；

○ 功耗必须满足

$$
P ^ {(k)} (t) = \sum_ {i} P _ {i} ^ {(k)} (t) \geq 0;
$$

。耗尽时间必须满足首达阈值约束。Runge-Kutta数值积分天然适用于一维ODE，配合事件检测可严格实现“首达阈值”定义，因此是结构上最匹配的选择。

- 模型还需要基于同一 SOC 轨迹:

$\circ$  计算不确定性区间  $[T_{p}^{\min}, T_{p}^{\max}]$ ;

$\circ$  计算积分量  $\int_{0}^{T_{p}} P_{i}^{(k)}(t) \mathrm{d} t$ ;

$\circ$  计算误差  $E_{T}(s_{0},k)$  与总体评价函数

$$
J = \sum_ {s _ {0}, k} w _ {s _ {0}, k} E _ {T} (s _ {0}, k) ^ {2}.
$$

数值积分框架统一提供这些积分量，简化整体实现。

# 决策变量与搜索空间的具体编码：

对每个  $(s_0,k)$

$\circ$  用时间序列  $\{t_n\}_{n=0}^{N_k}$ 、 $t_n = n\Delta t$  以及对应的  $\{s_n\}$  编码 SOC 轨迹  $s(t; s_0, k)$ ；

首次满足  $s_n \leq s_{\min}$  的时间区间  $[t_{n-1}, t_n]$  对应耗尽时间  $T_p(s_0, k)$  的搜索空间；

同样，在  $P_{\max}^{(k)}, P_{\min}^{(k)}$  下得到  $T_p^{\min}(s_0, k), T_p^{\max}(s_0, k)$ 。

- 各功耗分量  $P_{i}^{(k)}(t)$  在离散时间节点上的取值  $P_{i}^{(k)}(t_{n})$  用于近似积分, 定义  $\overline{P}_{i}(s_{0}, k)$  与  $\rho_{i}(s_{0}, k)$  。

# 目标函数到适应度的转化：

- 对每个  $(s_{0}, k)$ , 利用

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k)
$$

作为局部误差度量。

- 全局上采用加权均方误差

$$
J = \sum_ {s _ {0} \in \mathcal {S}} \sum_ {k \in \mathcal {K}} w _ {s _ {0}, k} E _ {T} (s _ {0}, k) ^ {2}
$$

作为模型整体拟合优度指标。

在纯评估模式下， $J$  是输出评价量；在参数标定模式下（例如对  $\kappa^{(k)}$  的调节）， $J$  也可用作优化目标函数。

# 关键算法参数及记号：

时间离散与积分相关参数：

基本时间步长： $\Delta t > 0$ ；

$\mathrm{O}$  最大积分时间：  $T_{\mathrm{max}} > 0$  （保证  $T_{\mathrm{max}} \geq \max_{s_0, k} T_o(s_0, k)$ ）；

○ 对应最大步数:  $N_{\max} = \left\lfloor T_{\max} / \Delta t \right\rfloor$  。

事件检测与求根相关参数：

○ SOC 阈值时间定位误差容限:  $\varepsilon_{T} > 0$ ;

○ SOC 阈值函数误差容限:  $\varepsilon_{s} > 0$ ;

○ 二分法最大迭代次数:  $N_{\mathrm{root}} \in \mathbb{N}$  。

- 不确定性计算相关参数：

$\circ$  功耗上下界轨迹  $P_{\mathrm{min}}^{(k)}(t)$  、  $P_{\mathrm{max}}^{(k)}(t)$

以  $T_{p}^{\min}(s_{0},k)$  、  $T_{p}^{\max}(s_{0},k)$  定义的  $\sigma_T(s_0,k)$  。

模型评价与分类参数：

○ 误差阈值：  $\varepsilon >0$

$\mathrm{o}$  不确定性阈值：  $\delta > 0$

○ 误差权重:  $w_{s_0, k} \geq 0$  。

这些参数在步骤1中初始化，在后续各步骤中保持不变或作为迭代条件使用。

# 2.2 求解流程

# 步骤 1: 数据准备

步骤目的：

明确所有输入集合、初始条件与算法参数，确保后续数值积分和统计计算的基础一致。

21. 数据文件：

问题二给定“无”数据文件，因此不涉及文件读取与清洗。功耗轨迹  $P_{i}^{(k)}(t)$  、 $P^{(k)}(t)$  视为已知函数或已在内存中以离散时间序列形式提供。

22. 初始条件与模型参数：

○ 初始SOC集合：

$$
\mathcal {S} \subset (0, 1 0 0 ], \quad s _ {0} \in \mathcal {S},
$$

并对每个  $s_0$  设定

$$
s (0; s _ {0}, k) = s _ {0}.
$$

○ 使用场景集合：

$$
\begin{array}{c c} \mathcal {K}, & k \in \mathcal {K}, \end{array}
$$

每个场景给定：

$$
T _ {\mathrm {e n v}} ^ {(k)} = \text {常 数}, \quad E _ {\max } ^ {(k)}, \quad \kappa^ {(k)} = \frac {1 0 0}{E _ {\max } ^ {(k)}}.
$$

。耗尽阈值：

$$
S _ {\min }
$$

给定，一般取

0.

观测或合理耗尽时间：

$$
T _ {o} (s _ {0}, k) \geq 0, \quad \forall (s _ {0}, k) \in \mathcal {S} \times \mathcal {K}.
$$

23. 算法初始参数设置：

。选定时间步长  $\Delta t$ ，例如使功耗轨迹在每步内变化相对平缓；

设置最大积分时间  $T_{\mathrm{max}}$  与  $N_{\mathrm{max}}$

$$
N _ {\mathrm {m a x}} = \left\lfloor T _ {\mathrm {m a x}} / \Delta t \right\rfloor ;
$$

设置阈值搜索容限：

$$
\begin{array}{l} \varepsilon_ {T}, \\ \varepsilon_ {s}; \\ \end{array}
$$

设置二分法最大迭代次数  $N_{\mathrm{root}}$

设置误差阈值  $\varepsilon$  、不确定性阈值  $\delta$  与权重  $w_{s_0,k}$  。

# 步骤 2: 构建总功耗轨迹与 SOC 微分方程

步骤目的：

根据模型的功耗加和约束，构造每个场景  $k$  的总功耗  $P^{(k)}(t)$ ，并显式写出ODE右端项，为Runge-Kutta积分做准备。

# 24. 功耗轨迹构建与约束校正：

对每个场景  $k \in \mathcal{K}$  和每个分量  $i \in \mathcal{I}$ :

$\circ$  给定（或插值得到）  $P_{i}^{(k)}(t)$

若在个别时刻因噪声出现  $P_{i}^{(k)}(t) < 0$ ，则数值上投影到非负半轴：

$$
\tilde {P} _ {i} ^ {(k)} (t) = \max  \{P _ {i} ^ {(k)} (t), 0 \},
$$

以满足功耗非负约束。

构造总功耗：

$$
P ^ {(k)} (t) = \sum_ {i \in \mathcal {I}} \tilde {P} _ {i} ^ {(k)} (t),
$$

对所有  $t \geq 0$  满足模型约束

$$
P ^ {(k)} (t) \geq 0.
$$

# 25. SOC 微分方程构造：

对每个  $k$ , 根据模型的 SOC 动力学:

$$
\frac {\mathrm {d} s (t ; s _ {0} , k)}{\mathrm {d} t} = - \kappa^ {(k)} P ^ {(k)} (t), \qquad s (0; s _ {0}, k) = s _ {0}.
$$

该方程的右端函数为

$$
f ^ {(k)} (t) = \frac {\mathrm {d} s}{\mathrm {d} t} (t; s _ {0}, k) = - \kappa^ {(k)} P ^ {(k)} (t),
$$

# 步骤 3: 单场景单初始 SOC 的 SOC 数值积分

步骤目的：

在离散时间网格上近似求解 ODE，得到 SOC 轨迹  $s(t; s_0, k)$  的数值近似  $s_n$ ，为首达阈值检测与平均功率计算提供基础。

对每个组合  $(s_0,k)\in \mathcal{S}\times \mathcal{K}$

26. 初始化：

$$
t _ {0} = 0, \quad s _ {0} ^ {(k)} = s _ {0}.
$$

令步数索引  $n = 0$ , 并初始化累积积分

$$
I _ {0} ^ {(k)} = 0, \quad I _ {n} ^ {(k)} \approx \int_ {0} ^ {t _ {n}} P ^ {(k)} (\tau) \mathrm {d} \tau .
$$

27. Runge-Kutta 4 阶积分：

在  $n = 0,1,\ldots$  迭代，直至检测到  $s_n\leq s_{\mathrm{min}}$  或  $n\geq N_{\mathrm{max}}$  对给定  $t_n,s_n^{(k)}$  ，计算：

○ 第一阶段：

$$
k _ {1} = f ^ {(k)} (t _ {n}) = - \kappa^ {(k)} P ^ {(k)} (t _ {n});
$$

○ 第二阶段：

$$
t _ {n, 2} = t _ {n} + \Delta t / 2, k _ {2} = f ^ {(k)} (t _ {n, 2}) = - \kappa^ {(k)} P ^ {(k)} (t _ {n, 2});
$$

第三阶段：

$$
t _ {n, 3} = t _ {n} + \Delta t / 2, k _ {3} = f ^ {(k)} (t _ {n, 3}) = - \kappa^ {(k)} P ^ {(k)} (t _ {n, 3});
$$

第四阶段：

$$
t _ {n, 4} = t _ {n} + \Delta t, k _ {4} = f ^ {(k)} (t _ {n, 4}) = - \kappa^ {(k)} P ^ {(k)} (t _ {n, 4}).
$$

则SOC更新为

$$
s _ {n + 1} ^ {(k)} = s _ {n} ^ {(k)} + \frac {\Delta t}{6} (k _ {1} + 2 k _ {2} + 2 k _ {3} + k _ {4}).
$$

同时，用梯形法近似更新能量积分：

$$
I _ {n + 1} ^ {(k)} = I _ {n} ^ {(k)} + \frac {\Delta t}{2} \big (P ^ {(k)} (t _ {n}) + P ^ {(k)} (t _ {n + 1}) \big), \quad t _ {n + 1} = t _ {n} + \Delta t.
$$

28. SOC 约束修正与单调性保证：

若数值误差导致  $s_{n + 1}^{(k)} > 100$  ，则投影：

$$
s _ {n + 1} ^ {(k)} = \min  \{s _ {n + 1} ^ {(k)}, 1 0 0 \};
$$

$\circ$  若数值误差导致  $s_{n + 1}^{(k)} > s_n^{(k)}$  ，可强制

$$
s _ {n + 1} ^ {(k)} = \min \{s _ {n + 1} ^ {(k)}, s _ {n} ^ {(k)} \},
$$

以满足  $\frac{\mathrm{d}s}{\mathrm{d}t} \leq 0$  的单调性约束。

29. 终止条件（粗略耗尽检测）：

$\circ$  若  $s_{n+1}^{(k)} \leq s_{\min}$ , 且  $s_n^{(k)} > s_{\min}$ , 则在区间  $[t_n, t_{n+1}]$  内发生阈值跨越, 进入下一步骤的精细求解;

$\circ$  若  $n + 1 \geq N_{\max}$  仍未跨越阈值，则认为在  $[0, T_{\max}]$  内未耗尽，可将  $T_p(s_0, k)$  视为大于  $T_{\max}$  （按应用需求处理）。

该步骤数值实现模型中的 SOC 轨迹决策变量  $s(t; s_0, k)$ ，并保证其满足范围约束与单调性要求。

步骤 4: 首达阈值事件检测与  $T_{p}(s_{0}, k)$  精细求解

步骤目的：

在检测到阈值跨越的时间区间内精确求出耗尽时间  $T_{p}(s_{0},k)$  ，使得

$$
s (T _ {p} (s _ {0}, k); s _ {0}, k) = s _ {\min}
$$

在给定容限内成立，同时保证首达性约束。

对每个出现  $s_n^{(k)} > s_{\min} \geq s_{n+1}^{(k)}$  的  $(s_0, k)$

30. 线性插值初值：

假定  $s(t)$  在小区间  $[t_n, t_{n+1}]$  内近似线性，得到一阶近似：

$$
T _ {p} ^ {(0)} (s _ {0}, k) = t _ {n} + \frac {s _ {n} ^ {(k)} - s _ {\mathrm {m i n}}}{s _ {n} ^ {(k)} - s _ {n + 1} ^ {(k)}} \Delta t.
$$

# 31. 可选的一维求根 refinement (基于积分形式):

定义阈值函数（对应模型中的  $g(T)$ ）：

$$
g (T) = s _ {0} - \kappa^ {(k)} \int_ {0} ^ {T} P ^ {(k)} (\tau) d \tau - s _ {\min }
$$

它在  $[t_n, t_{n+1}]$  内严格单调递减，且

$$
g (t _ {n}) > 0, \quad g (t _ {n + 1}) \leq 0.
$$

采用二分法：

○ 初始化：

$$
T _ {\mathrm {L}} = t _ {n}, \quad T _ {\mathrm {R}} = t _ {n + 1}.
$$

对  $j = 1,2,\dots ,N_{\mathrm{root}}$

令

$$
T _ {\text {m i d}} = \frac {T _ {\mathrm {L}} + T _ {\mathrm {R}}}{2};
$$

用与步骤 3 一致的数值积分规则近似

$$
I \left(T _ {\text {m i d}}\right) \approx \int_ {0} ^ {T _ {\text {m i d}}} P ^ {(k)} (\tau) \mathrm {d} \tau ,
$$

并计算

$$
g \left(T _ {\mathrm {m i d}}\right) = s _ {0} - \kappa^ {(k)} I \left(T _ {\mathrm {m i d}}\right) - s _ {\min };
$$

若  $|g(T_{\mathrm{mid}})| \leq \varepsilon_s$  或  $T_{\mathrm{R}} - T_{\mathrm{L}} \leq \varepsilon_T$ ，则停止并令

$$
T _ {p} (s _ {0}, k) = T _ {\mathrm {m i d}};
$$

否则，根据  $g(T_{\mathrm{L}})$  与  $g(T_{\mathrm{mid}})$  同号与否更新区间端点，保持 $g(T_{\mathrm{L}})g(T_{\mathrm{R}})\leq 0$

若不进行 refinement, 可直接取

$$
T _ {p} (s _ {0}, k) \approx T _ {p} ^ {(0)} (s _ {0}, k),
$$

但通常推荐进行上述几步refinement以满足模型积分平衡约束的精度要求。

# 32. 首达性与时间非负检查：

$\circ$  确保  $T_{p}(s_{0}, k) \geq 0$  （由构造自  $t_{n} \geq 0$  自然满足）；

○ 利用 SOC 单调性, 可保证对所有  $t < T_{p}(s_{0}, k)$  有  $s(t; s_{0}, k) > s_{\min }$ , 从而满足

$$
s (t; s _ {0}, k) > s _ {\min },
$$

$$
\forall t \in [ 0, T _ {p} (s _ {0}, k)),
$$

实现首达定义。

至此，决策变量  $T_{p}(s_{0},k)$  已由 ODE 与阈值条件唯一确定。

# 步骤 5: 功耗不确定性下的耗尽时间区间与  $\sigma_{T}(s_{0}, k)$  计算

步骤目的：

在给定功耗上下界轨迹  $P_{\mathrm{max}}^{(k)}(t)$  、  $P_{\mathrm{min}}^{(k)}(t)$  的情况下，计算最悲观与最乐观的耗尽时间预测区间  $[T_p^{\mathrm{min}}, T_p^{\mathrm{max}}]$  及不确定性度量  $\sigma_T$  ，对模型输出可信度进行量化。

对每个  $(s_0,k)$

# 33. 最坏情况耗尽时间  $T_{p}^{\min}(s_{0}, k)$ :

$\circ$  将步骤2-4中的  $P^{(k)}(t)$  替换为  $P_{\max}^{(k)}(t)$

。以

$$
\frac {\mathrm {d} s}{\mathrm {d} t} = - \kappa^ {(k)} P _ {\max} ^ {(k)} (t), \quad s (0) = s _ {0}
$$

进行 Runge-Kutta 积分与阈值事件检测，得到

$$
s (T _ {p} ^ {\min } (s _ {0}, k); s _ {0}, k) = s _ {\min };
$$

。该情形下功耗最大，耗尽最快，对应“最坏”耗尽时间。

# 34. 最好情况耗尽时间  $T_{p}^{\max}(s_{0}, k)$ :

$\circ$  将 ODE 中的  $P^{(k)}(t)$  替换为  $P_{\min}^{(k)}(t)$ ;

。以

$$
\frac {\mathrm {d} s}{\mathrm {d} t} = - \kappa^ {(k)} P _ {\min} ^ {(k)} (t)
$$

重复同样的积分与阈值检测，得到

$$
s \left(T _ {p} ^ {\max } \left(s _ {0}, k\right); s _ {0}, k\right) = s _ {\min }.
$$

35. 区间一致性与不确定性计算：

由  $P_{\min}^{(k)}(t) \leq P^{(k)}(t) \leq P_{\max}^{(k)}(t)$  与 SOC 单调性, 可保证数值上

$$
0 \leq T _ {p} ^ {\min } (s _ {0}, k) \leq T _ {p} (s _ {0}, k) \leq T _ {p} ^ {\max } (s _ {0}, k).
$$

按模型定义不确定性：

$$
\sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max } (s _ {0} , k) - T _ {p} ^ {\min } (s _ {0} , k)}{2} \geq 0.
$$

步骤 6: 平均功率  $\bar{P}_{i}$  、总平均功率  $\bar{P}$  与功耗贡献  $\rho_{i}$  计算

步骤目的：

根据已求得的  $T_{p}(s_{0},k)$  与功耗轨迹  $P_{i}^{(k)}(t)$ ，计算各分量在整个放电过程中的平均功率与贡献占比，用于解释耗尽时间差异与识别主要耗电活动。

对每个  $(s_0,k)$

36. 时间网格与最后一个非整步处理：

○ 设  $T_{p}(s_{0}, k)$  所对应的积分区间为  $[0, T_{p}(s_{0}, k)]$ ;

$\circ$  若  $T_{p}(s_{0}, k)$  不是  $\Delta t$  的整数倍, 令

$$
N _ {p} = \left\lfloor \frac {T _ {p} (s _ {0} , k)}{\Delta t} \right\rfloor , \quad t _ {N _ {p}} \leq T _ {p} (s _ {0}, k) <   t _ {N _ {p} + 1};
$$

对  $[t_{N_p}, T_p(s_0, k)]$  的小区间，可采用线性插值近似功耗。

37. 分量累积能量与平均功率（数值近似模型中积分定义）：

利用梯形法近似

$$
E _ {i} (s _ {0}, k) = \int_ {0} ^ {T _ {p} (s _ {0}, k)} P _ {i} ^ {(k)} (t) \mathrm {d} t
$$

的数值版本：

。对全整步部分：

$$
E _ {i, \mathrm {i n t}} (s _ {0}, k) \approx \sum_ {n = 0} ^ {N _ {p} - 1} \frac {\Delta t}{2} \Bigl (P _ {i} ^ {(k)} (t _ {n}) + P _ {i} ^ {(k)} (t _ {n + 1}) \Bigr);
$$

$\mathrm{O}$  对末尾小区间  $[t_{N_p},T_p]$ , 令  $\Delta t_{\mathrm{last}} = T_p - t_{N_p}$ , 近似为

$$
E _ {i, \mathrm {l a s t}} (s _ {0}, k) \approx \frac {\Delta t _ {\mathrm {l a s t}}}{2} \Big (P _ {i} ^ {(k)} (t _ {N _ {p}}) + P _ {i} ^ {(k)} (T _ {p}) \Big),
$$

其中  $P_{i}^{(k)}(T_{p})$  由  $[t_{N_p},t_{N_p + 1}]$  内的线性插值得到。

则总能量近似为

$$
E _ {i} (s _ {0}, k) \approx E _ {i, \mathrm {i n t}} (s _ {0}, k) + E _ {i, \mathrm {l a s t}} (s _ {0}, k).
$$

平均功率定义为

$$
\overline {{P}} _ {i} (s _ {0}, k) = \frac {E _ {i} (s _ {0} , k)}{T _ {p} (s _ {0} , k)}.
$$

# 38. 总平均功率与贡献占比：

总平均功率：

$$
\overline {{P}} (s _ {0}, k) = \sum_ {i \in \mathcal {I}} \overline {{P}} _ {i} (s _ {0}, k).
$$

○ 各分量贡献占比：

$$
\rho_ {i} (s _ {0}, k) = \frac {\overline {{P}} _ {i} (s _ {0} , k)}{\overline {{P}} (s _ {0} , k)}, 0 \leq \rho_ {i} (s _ {0}, k) \leq 1, \sum_ {i \in \mathcal {I}} \rho_ {i} (s _ {0}, k) = 1.
$$

39. 能量-SOC一致性检查：

根据模型的能量平衡式：

$$
E _ {\mathrm {t o t}} (s _ {0}, k) = \sum_ {i \in \mathcal {I}} E _ {i} (s _ {0}, k) \approx \overline {{P}} (s _ {0}, k) T _ {p} (s _ {0}, k) \approx \frac {E _ {\mathrm {m a x}} ^ {(k)}}{1 0 0} (s _ {0} - s _ {\mathrm {m i n}}).
$$

通过比较左右两侧数值的一致性，可作为数值积分精度的检验。

# 步骤 7: 耗尽时间误差  $E_{T}$  、不确定性  $\sigma_{T}$  与整体评价函数  $J$  计算

步骤目的：

将数值预测耗尽时间与观测/合理耗尽时间对比，计算误差与整体评价指标，并为模型表现的好坏划分提供基础。

对每个  $(s_0,k)$

40. 点误差计算：

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k).
$$

可额外计算绝对误差与相对误差：

$$
\left| E _ {T} \left(s _ {0}, k\right) \right|, \quad e _ {\text {r e l}} \left(s _ {0}, k\right) = \frac {\left| E _ {T} \left(s _ {0} , k\right) \right|}{T _ {o} \left(s _ {0} , k\right)} \quad \left(T _ {o} \left(s _ {0}, k\right) > 0\right).
$$

41. 不确定性复述：

第5步已得

$$
\sigma_ {T} (s _ {0}, k) = \frac {T _ {p} ^ {\max } (s _ {0} , k) - T _ {p} ^ {\min } (s _ {0} , k)}{2}.
$$

该量与  $E_{T}$  一并用于评价单个  $(s_{0}, k)$  的预测质量。

42. 整体评价函数与统计汇总：

整体加权均方误差：

$$
J = \sum_ {s _ {0} \in \mathcal {S}} \sum_ {k \in \mathcal {K}} w _ {s _ {0}, k} E _ {T} (s _ {0}, k) ^ {2};
$$

在所有  $(s_0, k)$  上，可统计：

平均误差：

$$
\overline {{E}} _ {T} = \frac {1}{| \mathcal {S} | | \mathcal {K} |} \sum_ {s _ {0}, k} E _ {T} (s _ {0}, k);
$$

平均绝对误差、最大绝对误差等。

这些统计量用于量化模型在“不同初始电量-使用场景”组合下的整体预测水平。

# 步骤 8: 模型表现划分与耗电驱动因素识别与排序

步骤目的：

基于误差  $E_{T}$  、不确定性  $\sigma_{T}$  与功耗贡献  $\rho_{i}$ , 划分模型表现好/差的条件区间,并识别导致快速耗电的主要活动和影响较小的因素。

# 43. 模型表现好/差集合划分：

根据模型中集合定义：

$$
\mathcal {G} = \left\{\left(s _ {0}, k\right) \in \mathcal {S} \times \mathcal {K} \mid \left| E _ {T} \left(s _ {0}, k\right) \right| \leq \varepsilon , \right.
$$

$$
\sigma_ {T} (s _ {0}, k) \leq \delta \},
$$

$$
\mathcal {B} = (\mathcal {S} \times \mathcal {K}) \backslash \mathcal {G}.
$$

实现方式上，对每个  $(s_0, k)$  检查条件，将其标签为“表现良好”或“表现较差/不确定性大”。

# 44. 快速耗电情形下的主要驱动因素识别：

由能量平衡与平均功率定义，有近似关系

$$
T _ {p} (s _ {0}, k) \approx \frac {E _ {\operatorname* {m a x}} ^ {(k)}}{1 0 0} \frac {s _ {0} - s _ {\operatorname* {m i n}}}{\overline {{P}} (s _ {0} , k)},
$$

即耗尽时间与总平均功率成反比。

对于耗尽时间较短（ $T_{p}$ 较小）的情形，计算各分量贡献占比

$\rho_{i}(s_{0},k)$  ，对  $i\in \mathcal{I}$  按  $\rho_{i}$  从大到小排序：

$$
\rho_ {i _ {1}} (s _ {0}, k) \geq \rho_ {i _ {2}} (s _ {0}, k) \geq \dots .
$$

排名靠前的分量（如屏幕、CPU、网络等）即在该  $(s_0, k)$  下导致快速耗电的主导因素。

在场景层面，可对固定  $k$  、跨所有  $s_0 \in S$  取平均：

$$
\overline {{\rho}} _ {i} ^ {(k)} = \frac {1}{| \mathcal {S} |} \sum_ {s _ {0} \in \mathcal {S}} \rho_ {i} (s _ {0}, k),
$$

对  $\overline{\rho}_i^{(k)}$  排序，从而识别“在场景  $k$  中最主要的耗电活动”。

# 45. 对耗尽时间影响较小因素的识别：

。若某分量  $i$  在所有  $(s_0, k)$  上的贡献占比都较小，例如

$$
\rho_ {i} (s _ {0}, k) \leq \theta_ {\rho} \ll 1,
$$

且在将该分量的功耗轨迹  $P_{i}^{(k)}(t)$  在合理区间内缩放时，对  $T_{p}$  的变化

$$
\Delta T _ {p} (s _ {0}, k) = T _ {p} ^ {(\mathrm {调 整 后})} (s _ {0}, k) - T _ {p} (s _ {0}, k)
$$

始终较小，则可判定该因素对耗尽时间影响“出乎意料地小”。

。在实践中，可对每个分量  $i$  统计

$$
\max _ {s _ {0}, k} \rho_ {i} (s _ {0}, k), \quad \overline {{\rho}} _ {i} = \frac {1}{| \mathcal {S} | | \mathcal {K} |} \sum_ {s _ {0}, k} \rho_ {i} (s _ {0}, k),
$$

并对  $\overline{\rho}_i$  从小到大排序，识别影响弱的因素（如某些后台任务或低占比传感器等）。

# 46. 模型解释不同情形结果差异：

对每个  $(s_0,k)$  ，结合  $T_{p}(s_{0},k),E_{T}(s_{0},k),\sigma_{T}(s_{0},k)$  与  $\rho_{i}(s_{0},k)$

- 若  $(s_0, k) \in \mathcal{G}$  且若干  $\rho_i$  明显占优，则可以解释为“模型成功捕捉到了由这些主导功耗分量驱动的耗尽行为”；

若  $(s_0,k)\in \mathcal{B}$  ，则需要检查：

- 是否有某些分量功耗在模型中被低估或未建模（导致  $E_{T}$  偏差）；

- 是否功耗不确定性大（ $\sigma_T$  大）导致预测可信度下降；

- 是否环境条件（通过  $E_{\max}^{(k)}$  或  $\kappa^{(k)}$ ）估计偏差。

。通过对  $\mathcal{G}$  与  $\mathcal{B}$  在  $(s_{0}, k)$  空间中的分布进行分析, 可总结出 “在何种初始电量与使用场景下模型表现良好/较差” 的规律。

# 2.3 结果生成

求解结束后，应输出如下指标，并给出其物理含义：

# 47. 不同初始电量与使用场景下的耗尽时间预测  $T_{p}(s_{0}, k)$ :

输出: 对每个  $(s_{0}, k)$ , 给出标量  $T_{p}(s_{0}, k)$ ;

。含义: 在初始 SOC 为  $s_{0}$  、使用场景为  $k$  的条件下, 电池从  $s_{0}$  放电至阈值  $s_{\min }$  所需的时间, 刻画该 “初始电量 - 使用模式” 下的续航时长。

48. 耗尽时间预测与观测/合理行为的偏差  $E_{T}(s_{0},k)$  及统计量：

输出：

$$
E _ {T} (s _ {0}, k) = T _ {p} (s _ {0}, k) - T _ {o} (s _ {0}, k)
$$

及其在全部  $(s_0, k)$  上的统计指标如平均误差、最大绝对误差、均方误差  $J$  等；

○ 含义：反映模型在不同初始电量与场景下对实际耗尽时间的系统偏差与散布程度，是模型预测精度与可靠性的直接量度。

49. 耗尽时间预测不确定性度量  $\sigma_{T}(s_{0}, k)$ :

输出：对每个  $(s_0, k)$ ，给出

$$
\begin{array}{l} T _ {p} ^ {\min } (s _ {0}, k), \\ T _ {p} ^ {\max } (s _ {0}, k), \\ \sigma_ {T} (s _ {0}, k) \\ \end{array}
$$

或至少给出  $T_{p} \pm \sigma_{T}$  的预测区间；

• 含义:  $[T_{p}^{\min}, T_{p}^{\max}]$  表示在给定功耗上下界下“最快耗尽 - 最慢耗尽”的时间区间,  $\sigma_{T}$  为其半宽, 刻画预测的不确定性范围。

50. 模型在不同情形下表现好/差的条件划分：

输出：集合

$$
\begin{array}{c} \mathcal {G}, \\ \mathcal {B} \end{array}
$$

以及可视化或表格形式的归纳描述（例如对每个场景  $k$  列出在  $\mathcal{G}$  中的  $s_0$  区间比例）；

。含义：明确指出在哪些  $(s_{0}, k)$  组合下，模型既误差小（ $|E_{T}| \leq \varepsilon$ ）又不确定性低（ $\sigma_{T} \leq \delta$ ），从而给出模型的适用范围与“易失准”区域。

51. 各功耗驱动因素对耗尽时间的贡献分析：

输出: 对每个  $(s_{0}, k)$ , 给出

$$
\begin{array}{l} \overline {{P}} _ {i} (s _ {0}, k), \\ \overline {{P}} (s _ {0}, k), \\ \rho_ {i} (s _ {0}, k), \quad i \in \mathcal {I}; \\ \end{array}
$$

○ 含义：

-  $\overline{P}_{i}$  ：分量  $i$  在整个放电过程中的平均功率，反映其平均耗电强度；

-  $\overline{P}$  ：总平均功率，与  $T_{p}$  近似满足反比关系；

-  $\rho_{i}$  : 分量  $i$  在总能量消耗中的占比, 用于衡量该活动对耗尽时间缩短的相对贡献。

# 52. 导致快速耗电的主要活动或条件识别与排序：

输出：

- 对每个场景  $k$ , 给出各分量贡献占比的排序

$$
\begin{array}{c} {{\overline {{{{\rho}}}} _ {i} ^ {(k)}}} \\ {{\text {或}}} \\ {{\rho_ {i} (s _ {0}, k)}} \end{array}
$$

的从大到小排序；

可进一步输出在短耗尽时间样本子集中（例如  $T_{p}$  位于最小若干百分位）的排序结果；

○ 含义：识别在典型场景和低续航条件下，哪些活动（如高亮度屏幕、高CPU 负载、高频网络通信、持续 GPS 使用、繁重后台任务等）是导致电池快速耗尽的主导因素。

# 53. 对耗尽时间影响较小的因素识别：

输出：对每个功耗分量或环境条件，给出跨  $(s_0,k)$  的平均贡献  $\overline{\rho}_i$  及其排序，并标出那些始终贡献较低、对  $T_{p}$  变化影响有限的因素；

。含义: 这些因素即 “对模型影响出乎意料地小” 的部分, 在合理范围内的变化对续航时间影响相对弱, 可在优化或简化模型时作为次要因素处理。

# 54. 模型解释结果差异的定性与定量说明：

输出：

- 基于  $T_{p}(s_{0}, k) 、 E_{T}(s_{0}, k) 、 \sigma_{T}(s_{0}, k)$  与  $\rho_{i}(s_{0}, k)$  的综合报告或图表，说明不同初始电量与场景之间耗尽时间差异的来源；

- 对于模型表现较差的情形，输出可能的机制解释（例如未建模的峰值功耗、温度导致的有效容量变化不足等）；

• 含义: 从物理与使用行为角度解释为何某些情形下模型与观测一致  $(\mathcal{G})$ , 而在另一些情形下偏差显著  $(\mathcal{B})$ , 并将这些差异与具体功耗分量、环境条件和使用模式相联系, 为后续模型改进与能耗优化提供依据。

# 问题三

# 1.3.3 决策变量

- 在本问题中，狭义的“决策变量”不指人为优化控制量，而指在分析框架内需要求解或评估的模型输出与派生指标。它们包括：在给定  $(M_{k},\theta ,u(t))$  条件下，由SOC动力学与耗尽条件唯一确定的耗尽时间  $T_{e}(\theta ,u)$  以及各假设集合下的  $T_{e}^{(k)}$ ；在基准点邻域内定义的敏感度  $S_{T_e,\theta_i}$  与归一化敏感度  $\tilde{S}_{T_e,\theta_i}$ ；参数不确定性传播得到的耗尽时间方差或变化区间端点；在使用模式扰动约束下的最小/最大耗尽时间  $T_{e}^{\min},T_{e}^{\max}$ ；以及根据敏感度构造的参数重要性指标  $I_{\theta_i}$  与使用模式重要性指标  $I_{u_j}$ 。这些量均由模型方程隐式或显式确定，其数学性质通常为实数标量或有限维向量（如敏感度向量），取值范围由物理约束和不确定性设定决定。

# 1.4. 模型的构建与推导

# 1.4.1 中间变量与子模型构建

# 55. 能量守恒与 SOC 动力学抽象

业务原理：手机电池在放电过程中向各子系统输出电能，系统内不存在能量生成，故电池剩余能量的变化等于总功耗的负积累。

数学抽象：设  $E(t)$  为剩余能量， $P(t)$  为总功耗，则有

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t).
$$

SOC 定义为剩余能量相对于有效容量的比例：

$$
s (t) = \frac {E (t)}{C _ {\mathrm {e f f}}}.
$$

对  $s(t)$  求导并代入能量守恒，得到SOC的动力学方程：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = \frac {1}{C _ {\mathrm {e f f}}} \frac {\mathrm {d} E (t)}{\mathrm {d} t} = - \frac {P (t)}{C _ {\mathrm {e f f}}}.
$$

施加初始条件  $s\left(t_{0}\right)=s_{0}$ , 可写为积分形式:

$$
s (t) = s _ {0} - \frac {1}{C _ {\mathrm {e f f}}} \int_ {t _ {0}} ^ {t} P (\tau) \mathrm {d} \tau .
$$

# 56. 子系统功耗与使用模式子模型

业务原理：手机由屏幕、处理器、网络、GPS、后台任务等子系统构成，各子系统的瞬

时功耗由其使用强度（亮度、CPU 负载、网络活动等）决定，总功耗为各子系统功耗叠加。

数学抽象: 设  $u_{j}(t)$  为第  $j$  子系统的使用强度 (归一化比例),  $k_{j}$  为功耗-强度比例系数, 则

$$
P _ {j} (t) = k _ {j} u _ {j} (t), \qquad j \in \mathcal {J},
$$

并有功耗叠加关系

$$
P (t) = \sum_ {j \in \mathcal {J}} P _ {j} (t) = \sum_ {j \in \mathcal {J}} k _ {j} u _ {j} (t).
$$

约束  $0 \leq u_{j}(t) \leq 1$ , 反映使用强度的物理范围, 且  $k_{j} > 0$  体现“使用强度升高不会降低对应功耗”的单调性。

将上述功耗表达式代入 SOC 动力学方程，得到统一的 SOC 子模型：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\text {e f f}}} \sum_ {j \in \mathcal {J}} k _ {j} u _ {j} (t), \quad s \left(t _ {0}\right) = s _ {0}.
$$

3. 建模假设集合  $M_{k}$  对动力学的结构影响

业务原理：不同的物理机理假设会改变容量随温度的变化方式、功耗-强度关系的线性/非线性形式，以及SOC定义中采用的参考容量，这将导致SOC动力学方程的右端函数形式发生改变，进而影响耗尽时间预测。

数学抽象：记在假设集合  $M_{k}$  下，SOC动力学可统一写为

$$
\frac {\mathrm {d} s ^ {(k)} (t)}{\mathrm {d} t} = F _ {k} \left(t, s ^ {(k)} (t); \theta^ {(k)}, u ^ {(k)} (t)\right), \quad s ^ {(k)} \left(t _ {0}\right) = s _ {0},
$$

其中  $F_{k}$  是由  $M_{k}$  所确定的右端函数， $\theta^{(k)}$  为对应的参数向量， $u^{(k)}(t)$  为在该假设集合下使用的使用模式。基准假设集合  $M_{k_{0}}$  的情形可写为

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = F _ {k _ {0}} (t, s (t); \theta^ {\star}, u (t)).
$$

4. 耗尽时间  $T_{e}(\theta, u)$  的统一定义

业务原理：耗尽时间是从初始时刻开始，SOC 首次降为零的时间，用以刻画电量从当前状态放空所需时长。

数学抽象：在给定参数  $\theta$  与使用模式  $u(t)$  下，由SOC动力学生成的解  $s(t;\theta ,u)$  满足  $s(t_0) = s_0$  。耗尽时间定义为

$$
T _ {e} (\theta , u) = \inf  \{t \geq t _ {0} \mid s (t; \theta , u) = 0 \}.
$$

对于不同建模假设集合  $M_{k}$ , 对应的耗尽时间记为

$$
T _ {e} ^ {(k)} = T _ {e} \big (\theta^ {(k)}, u ^ {(k)} \big),
$$

从而将假设、参数与使用模式对续航预测的影响统一映射为对标量函数  $T_{e}$  的影响。

# 5. 使用模式波动的表示与 SOC 曲线族

业务原理：实际使用中，各子系统的使用模式围绕某一基准模式波动。需要在固定参数与假设集合下，通过引入使用模式扰动，获得一族 SOC 曲线，用于分析使用模式波动对电量下降过程及耗尽时间的影响。

数学抽象：设基准使用模式为  $\bar{u}_j(t)$ ，扰动为  $\delta u_j(t)$ ，则实际模式为

$$
u _ {j} (t) = \bar {u} _ {j} (t) + \delta u _ {j} (t), \qquad j \in \mathcal {J}.
$$

代入 SOC 动力学，在基准假设集合与基准参数下，有

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\mathrm {e f f}}} \sum_ {j \in \mathcal {J}} k _ {j} [ \bar {u} _ {j} (t) + \delta u _ {j} (t) ], \quad s (t _ {0}) = s _ {0}.
$$

对不同可行扰动轨迹  $\delta u(t) = \{\delta u_j(t)\}_{j\in J}$ ，可得到SOC曲线族

$$
s (t; \theta^ {\star}, \bar {u} + \delta u),
$$

以及对应的耗尽时间族

$$
T _ {e} \left(\theta^ {\star}, \bar {u} + \delta u\right).
$$

# 1.4.2 目标函数

本问题的核心目标是以统一的SOC－耗尽时间模型为基础，给出“建模假设改变－参数扰动－使用模式波动”对耗尽时间预测  $T_{e}$  及SOC曲线  $s(t)$  的定量影响刻画。形式上可将整个分析视为对标量函数  $T_{e}(\theta ,u)$  的敏感度与不确定性研究，其“目标函数”即为耗尽时间在各维度上的响应函数。

# 57. 建模假设改变的影响指标

在不同假设集合  $M_{k}$  下，比较耗尽时间与基准模型的相对变化：

$$
r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})}, \qquad k \in \mathcal {K}.
$$

该指标量化了“建模假设改变”对耗尽时间预测的相对影响。

# 58. 参数敏感度与归一化敏感度

在基准点  $(\theta^{\star}, \bar{u})$ ，耗尽时间对参数分量  $\theta_{i}$  的局部敏感度定义为

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \Big | _ {\theta = \theta^ {\star}}, \qquad i \in \mathcal {I} _ {\theta},
$$

归一化敏感度定义为

$$
\tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}},
$$

并以

$$
I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |
$$

作为参数  $\theta_{i}$  的重要性指标。

# 59. 参数不确定性到耗尽时间的方差传播

假定参数向量  $\theta$  在基准点附近的随机扰动较小，且  $T_{e}(\theta, \bar{u})$  可线性化，则在一阶近似下，有

$$
\operatorname {Var}[T_{e}(\theta ,\bar{u})]\approx \sum_{i\in \mathcal{I}_{\theta}}\left(\frac{\partial T_{e}}{\partial\theta_{i}}\right)^{2}\operatorname {Var}[\theta_{i}] + 2\sum_{\substack{i,j\in \mathcal{I}_{\theta}\\ i <   j}}\frac{\partial T_{e}}{\partial\theta_{i}}\frac{\partial T_{e}}{\partial\theta_{j}}\operatorname {Cov}(\theta_{i},\theta_{j}),
$$

其中偏导在  $\theta = \theta^{\star}$  处计算。该方程给出参数不确定性传播到耗尽时间预测方差的近似关系。

# 60. 使用模式波动对耗尽时间的线性化响应与重要性

将使用模式视为函数型参数，对基准模式小扰动  $\delta u_{j}(t)$  进行一阶线性化，形式上可写为

$$
\Delta T _ {e} \approx \sum_ {j \in \mathcal {J}} \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} \psi_ {j} (t) \delta u _ {j} (t) \mathrm {d} t,
$$

其中  $\psi_{j}(t)$  是针对使用模式的灵敏度核函数（由伴随方程或变分分析导出），反映不同时间段改变第  $j$  子系统使用强度对耗尽时间的边际贡献。

据此可定义使用模式分量的重要性指标，例如

$$
I _ {u _ {j}} = \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} | \psi_ {j} (t) | \mathrm {d} t, \qquad j \in \mathcal {J},
$$

用于排序各子系统使用模式波动对耗尽时间的相对影响。

# 61. 使用模式波动下耗尽时间范围

在给定扰动可行性约束下，所有允许的使用模式集合记为  $\mathcal{U}$ ，则耗尽时间的可能范围为

$$
T _ {e} ^ {\min } = \inf  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u), \qquad T _ {e} ^ {\max } = \sup  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u),
$$

从而给出

$$
T _ {e} ^ {\mathrm {m i n}} \leq T _ {e} (\theta^ {\star}, u) \leq T _ {e} ^ {\mathrm {m a x}},
$$

该不等式刻画了“日常使用波动”对耗尽时间预测不确定性的贡献范围。

# 1.4.3 约束条件

# (1) SOC 定义与取值范围约束：

业务逻辑：SOC是剩余能量相对于参考容量的归一化比例，物理上不应小于0或大于满电状态。

数学表达：

$$
s (t) = \frac {E (t)}{E _ {\max}}, \qquad 0 \leq s (t) \leq 1, \quad \forall t \geq t _ {0}.
$$

# (2) 耗尽时间定义与初始条件统一约束:

业务逻辑：耗尽时间用于比较不同假设、参数与使用模式下的续航表现，因此必须在统一初始条件下定义，并要求在耗尽前 SOC 始终为正。

数学表达：

$$
t _ {0} = 0, \qquad s (t _ {0}) = s _ {0},
$$

$$
T _ {e} (\theta , u) = \inf  \{t \geq t _ {\mathbf {0}} \mid s (t; \theta , u) = \mathbf {0} \},
$$

$$
s (t; \theta , u) > \mathbf {0}, \quad \forall t \in [ t _ {\mathbf {0}}, T _ {e} (\theta , u)).
$$

# (3) 能量守恒与功耗非负约束：

业务逻辑：电池不产生能量，只输出能量；各子系统的功耗与总功耗在放电阶段均应非负。

数学表达：

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t),
$$

$$
P (t) = \sum_ {j \in \mathcal {J}} P _ {j} (t) \geq \mathbf {0}, \quad P _ {j} (t) \geq \mathbf {0}, \quad j \in \mathcal {J}.
$$

# (4) 子系统功耗-使用强度关系与可行性约束：

业务逻辑：各子系统功耗与其使用强度成正比，使用强度为0-1的无量纲比例；围绕基准模式的扰动不得使使用强度超出物理范围。

数学表达：

$$
P _ {j} (t) = k _ {j} u _ {j} (t), \qquad k _ {j} > 0, \quad j \in \mathcal {J},
$$

$$
\mathbf {0} \leq u _ {j} (t) \leq \mathbf {1}, \quad \forall t, j \in \mathcal {J},
$$

$$
u _ {j} (t) = \bar {u} _ {j} (t) + \delta u _ {j} (t), \quad - \bar {u} _ {j} (t) \leq \delta u _ {j} (t) \leq 1 - \bar {u} _ {j} (t).
$$

# (5) 容量与温度工作范围约束：

业务逻辑：标称容量为正，有效容量不应超过标称容量；模型只在安全温度区间内有效，温度必须落在预先设定的工作范围内。

数学表达：

$$
E _ {\mathrm {m a x}} > 0, \qquad 0 <   C _ {\mathrm {e f f}} \leq E _ {\mathrm {m a x}},
$$

$$
T _ {\min } \leq T (t) \leq T _ {\max }, \quad \forall t.
$$

# (6) SOC 动力学统一约束：

业务逻辑：无论具体假设集合如何变化，SOC 演化均基于能量守恒与总功耗；在基准线性功耗模型下，SOC 满足一阶 ODE。

数学表达：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{C _ {\mathrm {e f f}}}, \qquad P (t) = \sum_ {j \in \mathcal {J}} k _ {j} u _ {j} (t).
$$

# (7) 参数敏感度可微性与归一化定义约束：

业务逻辑：为了使用局部敏感度度量参数对耗尽时间的影响，必须要求耗尽时间对参数可微，并使用归一化形式消除量纲影响，从而比较不同参数的重要性。

数学表达：

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \Big | _ {\theta = \theta^ {\star}},
$$

$$
\tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}}, \qquad I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |.
$$

# (8) 参数不确定性传播与耗尽时间方差约束：

业务逻辑：在参数存在不确定性的情况下，耗尽时间预测不再是确定值，需要考虑其方差或区间；一阶方差传播公式给出近似上界与结构。

数学表达：

$$
\mathrm {V a r} [ T _ {e} (\theta , \bar {u}) ] \approx \sum_ {i \in \mathcal {I} _ {\theta}} \left(\frac {\partial T _ {e}}{\partial \theta_ {i}}\right) ^ {2} \mathrm {V a r} [ \theta_ {i} ] + 2 \sum_ {\stackrel {i, j \in \mathcal {I} _ {\theta}} {i <   j}} \frac {\partial T _ {e}}{\partial \theta_ {i}} \frac {\partial T _ {e}}{\partial \theta_ {j}} \mathrm {C o v} (\theta_ {i}, \theta_ {j}),
$$

并定义相应的耗尽时间不确定性区间端点  $T_{e}^{\mathrm{low}}, T_{e}^{\mathrm{up}}$  满足

$$
T _ {e} ^ {\mathrm {l o w}} \leq T _ {e} (\theta , \bar {u}) \leq T _ {e} ^ {\mathrm {u p}}.
$$

# (9) 使用模式波动下耗尽时间范围与重要性约束：

业务逻辑：使用模式波动受物理与场景约束，其可能取值集合有限；在该集合上耗尽时间存在上下界，并可通过灵敏度核函数构造使用模式重要性指标。

数学表达：记可行使用模式集合为

$$
\begin{array}{l} \\ \mathbb {S S} \quad \backslash \text {m a t h c a l} \{\mathrm {U} \} \quad = \backslash \text {B i g l} \backslash \{\mathrm {u} (\mathrm {t}) \backslash \backslash \text {B i g m} | \backslash 0 \backslash \text {l e u} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} 1, \backslash - \backslash \text {b a r} \{\mathrm {u} \} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} \\ \backslash \text {d e l t a u} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} 1 - \backslash \text {b a r} \{\mathrm {u} \} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {B i g r} \}, \end{array}
$$

则

$$
T _ {e} ^ {\min } = \inf  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u), \qquad T _ {e} ^ {\max } = \sup  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u),
$$

$$
T _ {e} ^ {\mathrm {m i n}} \leq T _ {e} (\theta^ {\star}, u) \leq T _ {e} ^ {\mathrm {m a x}},
$$

并定义

$$
I _ {u _ {j}} = \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} | \psi_ {j} (t) | \mathrm {d} t, \qquad j \in \mathcal {J}.
$$

# (10) 建模假设比较的统一性与可比性约束：

业务逻辑：不同建模假设集合  $M_{k}$  的预测结果只有在初始条件与使用模式一致（或严格控制在同一可行集合）时才具有可比性。

数学表达：对所有  $k \in \mathcal{K}$ ，要求

$$
t _ {0} ^ {(k)} = t _ {0}, \qquad s ^ {(k)} (t _ {0}) = s _ {0},
$$

且在“假设改变”的纯比较场景中采用统一的使用模式

$$
u ^ {(k)} (t) \equiv \bar {u} (t), \quad \forall k \in \mathcal {K},
$$

从而

$$
T _ {e} ^ {(k)} = T _ {e} \big (\theta^ {(k)}, \bar {u} \big), r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})}.
$$

# 1.5 模型汇总

在上述推导基础上，可以将问题三的分析框架概括为以下标准数学模型块：

• 在给定建模假设集合  $M_{k}$  与参数向量  $\theta$  、使用模式  $u(t)$  条件下, SOC 动力学满足

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t), \qquad s (t) = \frac {E (t)}{E _ {\max}},
$$

$$
P (t) = \sum_ {j \in \mathcal {J}} k _ {j} u _ {j} (t), \quad \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\mathrm {e f f}}} \sum_ {j \in \mathcal {J}} k _ {j} u _ {j} (t), \quad s (t _ {0}) = s _ {0}.
$$

- 耗尽时间定义为

$$
T _ {e} (\theta , u) = \inf  \{t \geq t _ {0} \mid s (t; \theta , u) = 0 \},
$$

在各假设集合  $M_{k}$  下的结果为

$$
T _ {e} ^ {(k)} = T _ {e} \big (\theta^ {(k)}, u ^ {(k)} \big), \qquad r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} \left(\theta^ {\star} , \bar {u}\right)}{T _ {e} \left(\theta^ {\star} , \bar {u}\right)}.
$$

- 在基准点  $(\theta^{\star}, \bar{u})$  的邻域内，参数敏感度与归一化敏感度为

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \Big | _ {\theta = \theta^ {\star}}, \qquad \tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}}, \qquad I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |.
$$

- 参数不确定性传播到耗尽时间的方差近似为

$$
\mathrm{Var}[T_{e}(\theta ,\bar{u})]\approx \sum_{i\in \mathcal{I}_{\theta}}\left(\frac{\partial T_{e}}{\partial\theta_{i}}\right)^{2}\mathrm{Var}[\theta_{i}] + 2\sum_{\substack{i,j\in \mathcal{I}_{\theta}\\ i <   j}}\frac{\partial T_{e}}{\partial\theta_{i}}\frac{\partial T_{e}}{\partial\theta_{j}}\mathrm{Cov}(\theta_{i},\theta_{j}),
$$

由此可构造  $T_{e}(\theta, \bar{u})$  的变化区间或置信区间，用于评估模型在参数不确定性下的鲁棒性。

- 使用模式波动通过

$$
u _ {j} (t) = \bar {u} _ {j} (t) + \delta u _ {j} (t), \qquad - \bar {u} _ {j} (t) \leq \delta u _ {j} (t) \leq 1 - \bar {u} _ {j} (t),
$$

影响SOC曲线族

$$
s (t; \theta^ {\star}, \bar {u} + \delta u) = s _ {0} - \frac {1}{C _ {\mathrm {e f f}}} \int_ {t _ {0}} ^ {t} \sum_ {j \in \mathcal {J}} k _ {j} [ \bar {u} _ {j} (\tau) + \delta u _ {j} (\tau) ] \mathrm {d} \tau ,
$$

以及对应耗尽时间族  $T_{e}(\theta^{\star},\bar{u} +\delta u)$  。在一阶线性化下耗尽时间增量近似为

$$
\Delta T _ {e} \approx \sum_ {\bar {j} \in \mathcal {J}} \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} \psi_ {j} (t) \delta u _ {j} (t) \mathrm {d} t,
$$

并据此定义使用模式重要性指标  $I_{u_j}$  以及耗尽时间范围

$$
T _ {e} ^ {\mathrm {m i n}} \leq T _ {e} (\theta^ {\star}, u) \leq T _ {e} ^ {\mathrm {m a x}}, \qquad u \in \mathcal {U}.
$$

该模型在能量守恒与SOC动力学的统一框架下，将建模假设集合  $M_{k}$  、参数向量  $\theta$  与使用模式  $u(t)$  对耗尽时间  $T_{e}$  与SOC曲线  $s(t)$  的影响系统化地形式化为一组目标函数与约束条件。通过对  $T_{e}^{(k)}$  、  $S_{T_e,\theta_i}$  、  $\tilde{S}_{T_e,\theta_i}$  、  $I_{\theta_i}$  、  $I_{u_j}$  以及  $[T_e^{\mathrm{min}},T_e^{\mathrm{max}}]$  等量的求解与比较，可以定量回答问题三中关于“建模假设改变”“参数取值变化”和“使用模式波动”对续航预测影响幅度与关键影响因素排序的全部需求。

# 问题三的模型求解

# 2.1 算法设计

- 算法名称：基于直接灵敏度方程与一阶方差传播的 SOC 耗尽时间敏感度分析算法（数值积分内核采用 Runge-Kutta 方法，如 RK4）。

- 算法原理简述：在 SOC 动力学

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) u _ {j} (t), \qquad s (t _ {0}) = s _ {0}
$$

的基础上，通过数值积分得到  $s(t;\theta ,u)$  及耗尽时间

$$
T _ {e} (\theta , u) = \inf \{t \geq t _ {0} \mid s (t; \theta , u) = 0 \},
$$

再对参数  $\theta_{i}$  建立灵敏度变量

$$
z _ {i} (t) = \frac {\partial s (t)}{\partial \theta_ {i}},
$$

推导其满足的灵敏度方程，并与原方程同步积分。利用首达条件  $s(\theta, T_e) = 0$  的隐函数关系，将  $z_i(T_e)$  转换为

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e}}{\partial \theta_ {i}}
$$

的显式表达。由此得到局部敏感度  $S_{T_e, \theta_i}$  、归一化敏感度

$$
\tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}},
$$

以及重要性指标

$$
I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |.
$$

将敏感度向量代入模型中的一阶方差传播公式，得到  $\mathrm{Var}[T_e(\theta, \bar{u})]$  及对应不确定性区间。同时，通过对  $u_j(t)$  的参数化，将使用模式视为额外参数，采用同一灵敏度框架得到  $I_{u_j}$  以及在可行集合  $\mathcal{U}$  上的耗尽时间范围  $[T_e^{\min}, T_e^{\max}]$ 。

- 算法选择的必要性与与模型特性结合：

模型主体为一阶常微分方程，右端

$$
- \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) u _ {j} (t)
$$

在给定  $u(t)$  时为时间光滑、非刚性函数，适合采用显式 Runge-Kutta（如 RK4）进行高精度数值积分，可稳定追踪 SOC 曲线  $s(t)$  至  $s(t) = 0$ 。

$\circ$  目标函数  $T_{e}(\theta ,u)$  对参数  $\theta$  及使用模式  $u(t)$  在基准点邻域内假定可微（参见模型假设中的Fréchet可微性），适合采用直接灵敏度方程与隐函数定理进行解析梯度计算，避免纯有限差分在高维参数空间中的计算量和数值误差累积问题。

○ 建模假设集合  $M_{k}$  只改变SOC右端函数  $F_{k}$  的结构及参数向量 $\theta^{(k)}$  ，不改变“解ODE  $\rightarrow$  首达条件”的基本结构。采用统一的RK4+灵敏度ODE核心，可在不同  $M_{k}$  下复用相同求解框架，仅需替换  $F_{k}$  及其对  $\theta_{i}$  的偏导数。

$\mathrm{o}$  参数不确定性传播需要梯度  $\nabla_{\theta}T_{e}$  以构造

$$
\mathrm {V a r} [ T _ {e} (\theta , \bar {u}) ] \approx \sum_ {i} \left(\frac {\partial T _ {e}}{\partial \theta_ {i}}\right) ^ {2} \mathrm {V a r} [ \theta_ {i} ] + 2 \sum_ {i <   j} \frac {\partial T _ {e}}{\partial \theta_ {i}} \frac {\partial T _ {e}}{\partial \theta_ {j}} \mathrm {C o v} (\theta_ {i}, \theta_ {j}),
$$

直接灵敏度方程可以一次积分获得全部  $\frac{\partial T_e}{\partial\theta_i}$ ，降低多参数情形下的计算复杂度。

。使用模式波动通过

$$
u _ {j} (t) = \bar {u} _ {j} (t) + \delta u _ {j} (t),
$$

进入SOC动力学，与参数  $\theta_{i}$  类似，也可视作有限维参数化后的“广义参数”，灵敏度核函数  $\psi_{j}(t)$  与重要性指标

$$
I _ {u _ {j}} = \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} | \psi_ {j} (t) | d t
$$

可在同一框架下推导和数值近似。

- 决策变量的编码与搜索空间:

。决策变量为模型输出与派生指标，包括各  $M_{k}$  下的耗尽时间  $T_{e}^{(k)}$  与相对变化  $r_T^{(k)}$  ，参数敏感度  $S_{T_e,\theta_i}$  、归一化敏感度  $\tilde{S}_{T_e,\theta_i}$  、重要性指标  $I_{\theta_i},I_{u_j}$  ，耗尽时间不确定性区间端点  $T_{e}^{\mathrm{low}},T_{e}^{\mathrm{up}}$  ，以及使用模式波动下的范围  $[T_e^{\mathrm{min}},T_e^{\mathrm{max}}]$  等。它们均为标量或有限维向量，取值空间为实数域；不需要离散编码，仅需在数值实现中以实数组存储。

。对使用模式扰动  $\delta u_{j}(t)$ , 通过有限维参数化 (例如  $\delta u_{j}(t)$  在若干时间段内取常数, 或表示为基函数展开系数), 将函数空间  $\mathcal{U}$  映射到有限维系数空间; 搜索空间为满足

$$
- \bar {u} _ {j} (t) \leq \delta u _ {j} (t) \leq 1 - \bar {u} _ {j} (t)
$$

的系数集合。

- 目标函数到适应度函数的转化:

对建模假设比较，目标函数为

$$
T _ {e} ^ {(k)} = T _ {e} \big (\theta^ {(k)}, \bar {u} \big), r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})},
$$

数值实现中直接输出  $T_{e}^{(k)}$  和  $r_{T}^{(k)}$  即为评价指标，无需额外适应度变换。

对参数敏感度与重要性排序，目标函数为梯度分量

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \Big | _ {\theta = \theta^ {\star}}, \qquad \tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}}, \qquad I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |.
$$

在排序时将  $I_{\theta_i}$  或  $\left|\tilde{S}_{T_e,\theta_i}\right|$  直接视为“适应度”即可。

对使用模式重要性排序，目标函数为  $I_{u_j}$ ，可直接用于排序不同子系统的影响程度。

- 关键算法参数的定义：

。时间步长：记数值积分步长为  $\Delta t > 0$  ，在SOCODE与灵敏度ODE的RK4积分中统一使用。

。最大积分长度：记允许的最大积分时间为  $T_{\max}^{\text {num }}$ ，若在  $[t_0, T_{\max}^{\text {num }}]$  内未满足  $s(t) = 0$ ，则认为耗尽时间超出分析范围或需要调整步长。

。耗尽判据容差：记耗尽判据阈值为  $\varepsilon_{s} > 0$  ，当  $s(t)$  首次满足  $s(t) \leq \varepsilon_{s}$  且  $s(t)$  单调不增时，定义数值耗尽时间  $\hat{T}_{e}$  。

。收敛判据（时间逼近）：在末端插值或根求解时使用时间容差  $\varepsilon_{t} > 0$ ，当迭代逼近的时间满足相邻估计之差小于  $\varepsilon_{t}$  时停止。

参数不确定性：参数方差协方差矩阵记为  $\Sigma_{\theta} \in \mathbb{R}^{n_{\theta} \times n_{\theta}}$ ，分量为

$$
[ \Sigma_ {\theta} ] _ {i i} = \operatorname {V a r} [ \theta_ {i} ], \qquad [ \Sigma_ {\theta} ] _ {i j} = \operatorname {C o v} (\theta_ {i}, \theta_ {j}).
$$

$\circ$  使用模式参数化维数：若将  $u_{j}(t)$  用  $n_u$  个系数表示，则  $n_u$  为模式参数维度，用以确定灵敏度方程的规模。

。蒙特卡洛样本数（若用于检验线性近似）：记为  $N_{\mathrm{MC}}$  ，用于从参数不确定性分布抽样，数值验证方差传播结果。

# 2.2 求解流程

# 步骤1：数据准备与初始设置

- 步骤目的：根据问题输入与模型设定，明确所有必要的初始条件、参数与算法控制量，为后续 SOC 及灵敏度积分提供一致的起点。

数据文件：

○ 问题输入中给出“无数据文件”，因此本步骤不涉及外部数据文件读取，仅使用符号量与预先给定的基准轨迹  $\bar{u}_j(t)$ 、参数向量  $\theta^{\star}$  等。

- 初始条件与模型参数 (数学化表述):

○ 初始时刻：

$$
t _ {0} = 0.
$$

○ 初始SOC:

$$
s (t _ {0}) = s _ {0}, \qquad s _ {0} \in (0, 1 ].
$$

○ 容量参数：

$$
E _ {\max } > 0, \quad 0 <   C _ {\text {e f f}} \leq E _ {\max },
$$

在问题三中将  $C_{\mathrm{eff}}$  视为可调参数，用于敏感性与不确定性分析。

基准参数向量：

$$
\theta^ {\star} = (\theta_ {i} ^ {\star}) _ {i \in \mathcal {I} _ {\theta}},
$$

包含各  $k_{j}^{\star}$  、  $\alpha_{T}^{\star}$  等机理参数。

基准使用模式轨迹：

$$
\bar {u} _ {j} (t), \qquad 0 \leq \bar {u} _ {j} (t) \leq 1, \quad j \in \mathcal {J}.
$$

建模假设集合：

$$
\{M _ {k} \} _ {k \in \mathcal {K}},
$$

其中  $M_{k_0}$  为基准假设集合，满足模型约束中“假设比较的统一性与可比性”条件。

- 算法初始参数设置：

选择时间步长  $\Delta t$  、最大积分时长  $T_{\mathrm{max}}^{\mathrm{num}}$  、耗尽判据容差  $\varepsilon_{s}$  与时间容差  $\varepsilon_{t}$  。

明确参数不确定性结构  $\Sigma_{\theta}$ , 包括  $\operatorname{Var}[\theta_i]$  与  $\operatorname{Cov}(\theta_i, \theta_j)$ , 保证在方差传播公式中可用。

确定是否采用蒙特卡洛检验，并设定样本数  $N_{\mathrm{MC}}$  （如需要）。

- 算法操作（伪代码式数学描述）：

○ 初始化当前时间  $t^{(0)} = t_{0}$ , SOC 初值  $s^{(0)} = s_{0}$  。

对每个参数索引  $i \in \mathcal{I}_{\theta}$ , 初始化灵敏度变量

$$
z _ {i} ^ {(0)} = 0.
$$

# 步骤2：基准模型下SOC动力学数值积分

- 步骤目的：在基准假设集合  $M_{k_0}$  与基准参数向量  $\theta^{\star}$  、基准使用模式  $\bar{u}(t)$  条件下，数值求解 SOC 曲线  $s(t; \theta^{\star}, \bar{u})$  ，并据此确定基准耗尽时间  $T_e(\theta^{\star}, \bar{u})$  。

数学逻辑：

○ 在  $M_{k_0}$  下，SOC动力学为

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = F _ {k _ {0}} (t, s (t); \theta^ {\star}, \bar {u} (t)),
$$

其中在基准线性功耗模型中

$$
F _ {k _ {0}} (t, s (t); \theta^ {\star}, \bar {u} (t)) = - \frac {1}{C _ {\mathrm {e f f}} (\theta^ {\star})} \sum_ {j \in \mathcal {J}} k _ {j} (\theta^ {\star}) \bar {u} _ {j} (t).
$$

○ 积分初值为  $s\left(t_{0}\right)=s_{0}$ , 需保证在积分过程中满足 SOC 约束

$$
0 \leq s (t) \leq 1, \quad s (t) \text {单 调 不 增}.
$$

- 算法操作：

1. 令  $n = 0, t^{(n)} = t_0, s^{(n)} = s_0$ 。

2. 在每一步中计算功耗

$$
P ^ {(n)} = \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} \bar {u} _ {j} \big (t ^ {(n)} \big),
$$

并根据

$$
\frac {\mathrm {d} s}{\mathrm {d} t} = - \frac {P (t)}{C _ {\text {e f f}} ^ {\star}}
$$

计算右端

$$
f _ {s} ^ {(n)} = - \frac {P ^ {(n)}}{C _ {\mathrm {e f f}} ^ {\star}}.
$$

3. 使用 RK4 时间步进，在  $[t^{(n)}, t^{(n)} + \Delta t]$  上更新  $s^{(n+1)}$ ，即构造四个阶段斜率（记为  $k_{1}, k_{2}, k_{3}, k_{4}$ ）并按 RK4 权重线性组合得到

$$
s ^ {(n + 1)} = s ^ {(n)} + \mathrm {R K 4 \_ i n c r e m e n t} (f _ {s}, \Delta t),
$$

同时更新

$$
t ^ {(n + 1)} = t ^ {(n)} + \Delta t.
$$

4. 在每一步检查约束：

$$
s ^ {(n + 1)} \leq s ^ {(n)}, \quad 0 \leq s ^ {(n + 1)} \leq 1.
$$

若数值误差导致违反单调性或取值约束，可通过减小  $\Delta t$  或投影操作（如截断到[0,1]）修正，使解满足模型隐式约束。

5. 耗尽判据：若首次出现  $s^{(n + 1)} \leq \varepsilon_s$ ，则在区间  $[t^{(n)}, t^{(n + 1)}]$  内采用线性插值或局部根求解近似求得  $\hat{T}_e$  使

$$
s (\hat {T} _ {e}; \theta^ {\star}, \bar {u}) = 0.
$$

将  $\hat{T}_e$  作为基准耗尽时间  $T_{e}(\theta^{\star},\bar{u})$  的数值近似。

6. 若  $t^{(n + 1)} > T_{\max}^{\mathrm{num}}$  仍未满足耗尽条件，则认为耗尽时间超出分析范围，可调整  $T_{\max}^{\mathrm{num}}$  或判定该参数组合不可行。

约束保证：

使用模式约束：

$$
0 \leq \bar {u} _ {j} (t) \leq 1, \quad j \in \mathcal {J}
$$

在输入阶段已保证，积分过程中直接使用。

○ SOC 动力学约束通过 ODE 形式与积分方案显式执行, 非负功耗条件  $P_{j}(t) \geq 0$  由  $k_{j}^{\star} > 0$  与  $\bar{u}_{j}(t) \geq 0$  自然保证。

# 步骤3：灵敏度方程建立与同步积分

- 步骤目的：根据模型中灵敏度定义与SOC方程，对每个参数分量  $\theta_{i}$  建立灵敏度变量  $z_{i}(t) = \frac{\partial s(t)}{\partial\theta_{i}}$  的ODE，并与  $s(t)$  同步积分，获得  $z_{i}(T_{e})$ 。

数学逻辑：

○原SOCODE为

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) u _ {j} (t),
$$

对  $\theta_{i}$  求偏导得到

$$
\frac {\mathrm {d}}{\mathrm {d} t} \left(\frac {\partial s}{\partial \bar {\theta} _ {i}}\right) = \frac {\partial}{\partial \theta_ {i}} \left[ - \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) u _ {j} (t) \right].
$$

记

$$
z _ {i} (t) = \frac {\partial s (t)}{\partial \theta_ {i}},
$$

则灵敏度方程为

$$
\frac {\mathrm {d} z _ {i} (t)}{\mathrm {d} t} = \frac {\partial}{\partial \theta_ {i}} \left[ - \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) u _ {j} (t) \right], \qquad z _ {i} (t _ {0}) = 0.
$$

$\circ$  在基准点  $\theta = \theta^{\star}$  、  $u(t) = \bar{u} (t)$  处，将右端偏导数显式写出，用于数值计算。

- 算法操作：

7. 对每个  $i \in \mathcal{I}_{\theta}$ ，在步骤2的时间离散序列  $\{t^{(n)}\}$  上同时维护  $z_{i}^{(n)} \approx z_{i}(t^{(n)})$ 。

8. 在时刻  $t^{(n)}$ , 给定  $\theta^{\star}$  与  $\bar{u}(t^{(n)})$ , 计算

$$
g _ {i} ^ {(n)} = \frac {\partial}{\partial \theta_ {i}} \left[ - \frac {1}{C _ {\mathrm {e f f}} (\theta)} \sum_ {j \in \mathcal {J}} k _ {j} (\theta) \bar {u} _ {j} (t ^ {(n)}) \right] \Biggr | _ {\theta = \theta^ {\star}}.
$$

例如，若  $\theta_{i} = C_{\mathrm{eff}}$  ，则

$$
g _ {i} ^ {(n)} = - \left(- \frac {1}{C _ {\mathrm {e f f}} ^ {2}} \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} \bar {u} _ {j} (t ^ {(n)})\right) = \frac {1}{(C _ {\mathrm {e f f}} ^ {\star}) ^ {2}} \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} \bar {u} _ {j} (t ^ {(n)}),
$$

若  $\theta_{i} = k_{\ell}$  ，则

$$
g _ {i} ^ {(n)} = - \frac {1}{C _ {\mathrm {e f f}} ^ {\star}} \bar {u} _ {\ell} (t ^ {(n)}).
$$

9. 使用与  $s(t)$  相同的 RK4 步进公式更新  $z_{i}^{(n + 1)}$

$$
z _ {i} ^ {(n + 1)} = z _ {i} ^ {(n)} + \mathrm {R K 4 \_ i n c r e m e n t} (g _ {i}, \Delta t),
$$

其中 RK4 增量使用  $g_{i}^{(n)}$  及其在时间段内的中间估计。

10. 积分终止时刻与 SOC 相同，即当在步骤 2 判定  $s(t)$  耗尽时间为  $\hat{T}_e$  时，通过插值获得  $z_i(\hat{T}_e)$ ，或采用最后一时刻  $t^{(n+1)} \approx \hat{T}_e$  的值  $z_i^{(n+1)}$  作为  $z_i(\hat{T}_e)$  的近似。

约束保证：

○ 灵敏度方程为线性一阶 ODE，无额外约束，但需确保参数取值满足模型物理约束（如  $C_{\mathrm{eff}} > 0, k_j > 0$ ），否则右端偏导可能失去物理意义或出现奇异。

# 步骤4：局部敏感度  $S_{T_e,\theta_i}$  与归一化敏感度的计算

- 步骤目的：根据耗尽时间定义与灵敏度变量终值，将  $z_{i}(T_{e})$  映射为  $\frac{\partial T_e}{\partial \theta_i}$ ，并依照模型给定公式构造  $\tilde{S}_{T_e, \theta_i}$  与  $I_{\theta_i}$ 。

数学逻辑：

。耗尽时间定义为

$$
F (\theta , T _ {e}) = s (\theta , T _ {e}) = 0.
$$

对  $\theta_{i}$  求导得到隐函数关系

$$
\frac {\partial F}{\partial \theta_ {i}} + \frac {\partial F}{\partial t} \frac {\partial T _ {e}}{\partial \theta_ {i}} = 0.
$$

即

$$
\frac {\partial T _ {e}}{\partial \theta_ {i}} = - \frac {\frac {\partial s}{\partial \theta_ {i}} (\theta , T _ {e})}{\frac {\partial s}{\partial t} (\theta , T _ {e})} = - \frac {z _ {i} (T _ {e})}{\dot {s} (T _ {e})},
$$

其中

$$
\dot {s} (T _ {e}) = \frac {\partial s}{\partial t} (\theta , T _ {e}) = - \frac {1}{C _ {\mathrm {e f f}} ^ {\star}} \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} \bar {u} _ {j} (T _ {e})
$$

由SOCODE给出。

在基准点  $\theta = \theta^{\star}$  、  $u(t) = \bar{u} (t)$  ，局部敏感度定义为

$$
S _ {T _ {e}, \theta_ {i}} = \left. \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \right| _ {\theta = \theta^ {*}}.
$$

- 算法操作：

11. 从步骤2中得到耗尽时间近似  $\hat{T}_e \approx T_e(\theta^\star, \bar{u})$ 。

12. 在  $\hat{T}_{e}$  处计算

$$
\dot {s} (\hat {T} _ {e}) = - \frac {1}{C _ {\mathrm {e f f}} ^ {\star}} \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} \bar {u} _ {j} (\hat {T} _ {e}).
$$

13. 利用步骤 3 的结果  $z_{i}(\hat{T}_{e})$  计算

$$
S _ {T _ {e}, \theta_ {i}} \approx - \frac {z _ {i} (\hat {T} _ {e})}{\dot {s} (\hat {T} _ {e})}.
$$

14. 根据模型定义，计算归一化敏感度

$$
\tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}},
$$

以及参数重要性指标

$$
I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |.
$$

15. 若需要，根据  $I_{\theta_i}$  对参数索引  $i \in \mathcal{I}_{\theta}$  进行降序排序，从而获得关键影响因素排序。

约束保证与终止条件：

$\circ$  若  $\dot{s} (\hat{T}_e)$  的数值绝对值过小，则  $\frac{\partial T_e}{\partial\theta_i}$  的估计可能不稳定，应考虑减小时间步长  $\Delta t$  以提高  $\dot{s} (T_e)$  的精度，或采用局部时间细分。

$\mathrm{O}$  收敛判据：当改变  $\Delta t$  或耗尽时间插值策略后， $S_{T_e, \theta_i}$  的变化小于预设阈值时，认为局部敏感度结果收敛。

# 步骤5：参数不确定性到耗尽时间方差的传播

- 步骤目的：利用已计算的梯度向量  $S_{T_e, \theta}$  与参数方差协方差矩阵  $\Sigma_\theta$ ，按照模型中的一阶方差传播公式获得  $\operatorname{Var}[T_e(\theta, \bar{u})]$  及不确定性区间。

数学逻辑：

模型中给出的一阶方差传播公式为

$$
\operatorname {Var}[T_{e}(\theta ,\bar{u})]\approx \sum_{i\in \mathcal{I}_{\theta}}\left(\frac{\partial T_{e}}{\partial\theta_{i}}\right)^{2}\operatorname {Var}[\theta_{i}] + 2\sum_{\substack{i,j\in \mathcal{I}_{\theta}\\ i <   j}}\frac{\partial T_{e}}{\partial\theta_{i}}\frac{\partial T_{e}}{\partial\theta_{j}}\operatorname {Cov}(\theta_{i},\theta_{j}),
$$

其中偏导数即为  $S_{T_e,\theta_i}$ 。

。可记梯度向量为

$$
\nabla_ {\theta} T _ {e} = \left(S _ {T _ {e}, \theta_ {i}}\right) _ {i \in \mathcal {I} _ {\theta}},
$$

则上述公式可写为矩阵形式

$$
\operatorname {V a r} \left[ T _ {e} (\theta , \bar {u}) \right] \approx \left(\nabla_ {\theta} T _ {e}\right) ^ {\top} \Sigma_ {\theta} \left(\nabla_ {\theta} T _ {e}\right).
$$

- 算法操作：

16. 集中步骤 4 计算的所有  $S_{T_e, \theta_i}$  组成向量。

17. 根据已知的参数方差协方差矩阵  $\Sigma_{\theta}$ , 按模型公式计算

$$
\widehat {\mathrm {V a r}} [ T _ {e} (\theta , \bar {u}) ] = \sum_ {i} \left(S _ {T _ {e}, \theta_ {i}}\right) ^ {2} \mathrm {V a r} [ \theta_ {i} ] + 2 \sum_ {i <   j} S _ {T _ {e}, \theta_ {i}} S _ {T _ {e}, \theta_ {j}} \mathrm {C o v} (\theta_ {i}, \theta_ {j}).
$$

18. 根据所需置信水平，构造耗尽时间变化区间端点  $T_{e}^{\mathrm{low}}, T_{e}^{\mathrm{up}}$  ，例如采用对称区间

$$
\begin{array}{l} T _ {e} ^ {\mathrm {l o w}} = T _ {e} (\theta^ {\star}, \bar {u}) - \kappa \sqrt {\widehat {\mathrm {V a r}} [ T _ {e} (\theta , \bar {u}) ]}, \\ T _ {e} ^ {\mathrm {u p}} = T _ {e} (\theta^ {\star}, \bar {u}) + \kappa \sqrt {\widehat {\mathrm {V a r}} [ T _ {e} (\theta , \bar {u}) ]}, \\ \end{array}
$$

其中  $\kappa$  由置信度选择。

19. 如需验证线性近似, 可在参数分布上进行少量蒙特卡洛抽样: 从  $\theta$  的不确定性分布中生成  $\theta^{(m)}$ , 对每个样本重复步骤 2-4（仅 SOC 积分, 无需灵敏度），得到样本耗尽时间  $T_{e}^{(m)}$ , 估计样本方差并与方差传播结果对比。

- 收敛与终止条件:

。若随着增加  $N_{\mathrm{MC}}$  ，蒙特卡洛估计的  $\operatorname{Var}[T_e]$  与方差传播结果差异趋于稳定且在可接受范围内，则认为一阶方差传播近似有效。

。一旦得到稳定的  $\operatorname{Var}[T_e]$  与  $(T_e^{\mathrm{low}}, T_e^{\mathrm{up}})$ ，停止不确定性传播步骤。

# 步骤6：不同建模假设集合  $M_{k}$  下耗尽时间的对比求解

- 步骤目的：在统一初始条件与使用模式下，对每个建模假设集合  $M_{k}$  数值求解耗尽时间  $T_{e}^{(k)}$  ，并计算相对变化  $r_{T}^{(k)}$  ，从而量化建模假设改变对预测的影响。

数学逻辑：

○ 在假设集合  $M_{k}$  下, SOC 动力学为

$$
\frac {\mathrm {d} s ^ {(k)} (t)}{\mathrm {d} t} = F _ {k} \left(t, s ^ {(k)} (t); \theta^ {(k)}, \bar {u} (t)\right), \quad s ^ {(k)} \left(t _ {0}\right) = s _ {0},
$$

且使用模式统一为  $\bar{u}(t)$  以保证可比性。

。耗尽时间定义为

$$
T _ {e} ^ {(k)} = T _ {e} \big (\theta^ {(k)}, \bar {u} \big).
$$

○ 相对变化指标为

$$
r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})}.
$$

- 算法操作：

20. 对每个  $k \in \mathcal{K}$

- 设定对应假设集合  $M_{k}$  下的参数向量  $\theta^{(k)}$  ，确保满足物理约束（如容量－温度关系、功耗机理非负等）。

- 使用与步骤 2 相同的 RK4 积分核, 但将右端替换为  $F_{k}$ , 在  $t \in [t_{0}, \infty)$  上积分  $s^{(k)}(t)$ , 直至满足耗尽判据  $s^{(k)}(t) \leq \varepsilon_{s}$ , 求得数值耗尽时间  $\hat{T}_{e}^{(k)}$ 。

21. 利用基准耗尽时间  $T_{e}(\theta^{\star}, \bar{u})$  计算

$$
r _ {T} ^ {(k)} \approx \frac {\hat {T} _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})}.
$$

22. 将  $\hat{T}_e^{(k)}$  与  $r_T^{(k)}$  作为建模假设改变影响分析的结果存储。

约束保证：

对所有  $k \in \mathcal{K}$ , 保持

$$
t _ {0} ^ {(k)} = t _ {0}, \qquad s ^ {(k)} (t _ {0}) = s _ {0}, \qquad u ^ {(k)} (t) \equiv \bar {u} (t),
$$

确保跨模型比较满足模型的统一性与可比性约束。

# 步骤7：使用模式波动下SOC曲线族与耗尽时间范围的求解

- 步骤目的：在固定参数  $\theta^{\star}$  与基准假设集合  $M_{k_0}$  下，引入使用模式扰动  $\delta u_j(t)$ ，求解对应 SOC 曲线  $s(t; \theta^{\star}, \bar{u} + \delta u)$  与耗尽时间  $T_e(\theta^{\star}, \bar{u} + \delta u)$ ，并在可行集合  $\mathcal{U}$  上评估  $[T_e^{\min}, T_e^{\max}]$  以及使用模式重要性指标  $I_{u_j}$ 。

数学逻辑：

○ 实际使用模式为

$$
u _ {j} (t) = \bar {u} _ {j} (t) + \delta u _ {j} (t),
$$

且满足可行性约束

$$
0 \leq u _ {j} (t) \leq 1, \quad - \bar {u} _ {j} (t) \leq \delta u _ {j} (t) \leq 1 - \bar {u} _ {j} (t).
$$

在基准假设与参数下，SOC动力学为

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {1}{C _ {\text {e f f}} ^ {\star}} \sum_ {j \in \mathcal {J}} k _ {j} ^ {\star} [ \bar {u} _ {j} (t) + \delta u _ {j} (t) ], \qquad s (t _ {0}) = s _ {0}.
$$

对不同  $\delta u(t)$ , 得到 SOC 曲线族

$$
s (t; \theta^ {\star}, \bar {u} + \delta u),
$$

和耗尽时间族

$$
T _ {e} \left(\theta^ {\star}, \bar {u} + \delta u\right).
$$

。可行使用模式集合为

$$
\begin{array}{l} \mathbb {S S} \quad \backslash \text {m a t h c a l} \{\mathrm {U} \} \quad = \backslash \text {B i g l} \backslash \{\mathrm {u} (\mathrm {t}) \backslash , \backslash \text {B i g m} \backslash , \quad 0 \backslash \text {l e u} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} 1, \backslash ; \\ \backslash \text {b a r} \{\mathrm {u} \} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} \backslash \text {d e l t a u} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {l e} 1 - \backslash \text {b a r} \{\mathrm {u} \} _ {\mathrm {j}} (\mathrm {t}) \backslash \text {B i g r} \backslash \}, \quad \mathbb {S S} \end{array}
$$

耗尽时间范围为

$$
T _ {e} ^ {\min } = \inf  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u), \qquad T _ {e} ^ {\max } = \sup  _ {u \in \mathcal {U}} T _ {e} (\theta^ {\star}, u),
$$

并满足

$$
T _ {e} ^ {\min } \leq T _ {e} (\theta^ {\star}, u) \leq T _ {e} ^ {\max }, \qquad u \in \mathcal {U}.
$$

- 算法操作（离散化-灵敏度结合）：

23. 选择一组典型扰动模式  $\delta u^{(m)}(t)$ ， $m = 1, \dots, M_u$ ，满足可行性约束。例如：

- 固定某个子系统负载升高或降低一个比例；

在特定时间段内增加短时高负载。

24. 对于每个扰动实例  $\delta u^{(m)}(t)$

设定

$$
u _ {j} ^ {(m)} (t) = \bar {u} _ {j} (t) + \delta u _ {j} ^ {(m)} (t),
$$

并确认  $0 \leq u_{j}^{(m)}(t) \leq 1$ 。

- 使用与步骤 2 相同的 RK4 求解 SOC ODE, 但将  $\bar{u}_{j}(t)$  替换为  $u_{j}^{(m)}(t)$ , 得到曲线  $s^{(m)}(t)$ 。

判定耗尽时间  $T_{e}^{(m)} = T_{e}\left(\theta^{\star}, u^{(m)}\right)$ 。

25. 通过在一组代表性  $u^{(m)}$  上的  $T_{e}^{(m)}$  取最小与最大值, 构造数值近似

$$
T _ {e} ^ {\min } \approx \min  _ {m} T _ {e} ^ {(m)}, \qquad T _ {e} ^ {\max } \approx \max  _ {m} T _ {e} ^ {(m)}.
$$

26. 若使用模式被参数化为有限维系数（如  $u_{j}(t) = \beta_{j}\bar{u}_{j}(t)$  或基函数展开），可将这些系数视作广义参数，构建对应的灵敏度变量，类似步骤3-4，推导一阶线性化近似

$$
\Delta T _ {e} \approx \sum_ {j \in \mathcal {J}} \int_ {t _ {0}} ^ {T _ {e} \left(\theta^ {\star}, \bar {u}\right)} \psi_ {j} (t) \delta u _ {j} (t) d t,
$$

并据此定义使用模式重要性指标

$$
I _ {u _ {j}} = \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} | \psi_ {j} (t) |   \mathrm {d} t, \qquad j \in \mathcal {J}.
$$

约束保证与终止条件：

在生成扰动轨迹  $\delta u_{j}^{(m)}(t)$  时，显式检查并投影到可行区间

$$
- \bar {u} _ {j} (t) \leq \delta u _ {j} ^ {(m)} (t) \leq 1 - \bar {u} _ {j} (t).
$$

对每个  $m$  ，确保SOC积分解满足

$$
0 \leq s ^ {(m)} (t) \leq 1, \qquad s ^ {(m)} (t) \mathrm {单 调 不 增},
$$

若数值误差导致轻微违反，可通过缩小时间步长与截断操作进行修正。

。当增加扰动样本  $M_{u}$  后， $T_{e}^{\min}, T_{e}^{\max}$  的变化趋于稳定时，可认为耗尽时间范围估计收敛。

# 2.3 结果生成

- 不同建模假设集合  $M_{k}$  下的耗尽时间预测对比结果  $T_{e}^{(k)}$  及相对变化  $r_{T}^{(k)}$ :

输出  $\{T_e^{(k)}\}_{k\in \mathcal{K}}$  与

$$
r _ {T} ^ {(k)} = \frac {T _ {e} ^ {(k)} - T _ {e} (\theta^ {\star} , \bar {u})}{T _ {e} (\theta^ {\star} , \bar {u})},
$$

其中  $T_{e}^{(k)}$  表示在相应机理假设下从初始SOC  $s_0$  放电至耗尽的时间，具有时间的物理意义；  $r_T^{(k)}$  表示相对于基准假设预测耗尽时间的相对变化比例，反映建模假设改变对续航预测的影响幅度。

- 关键模型参数对耗尽时间的敏感度指标  $S_{T_e,\theta_i}$  与归一化敏感度  $\tilde{S}_{T_e,\theta_i}$ :

输出对每个参数分量的局部敏感度

$$
S _ {T _ {e}, \theta_ {i}} = \frac {\partial T _ {e} (\theta , \bar {u})}{\partial \theta_ {i}} \Big | _ {\theta = \theta^ {\star}},
$$

其物理含义为“参数  $\theta_{i}$  单位微小变化导致耗尽时间变化的方向与大小”。

输出归一化敏感度

$$
\tilde {S} _ {T _ {e}, \theta_ {i}} = \frac {\theta_ {i} ^ {\star}}{T _ {e} (\theta^ {\star} , \bar {u})} S _ {T _ {e}, \theta_ {i}},
$$

其为无量纲指标，描述参数相对变化（如百分比变化）对耗尽时间相对变化的影响强度，便于跨参数比较重要性。

- 参数不确定性传播到耗尽时间预测的变化范围或置信区间：

输出方差传播结果

$$
\mathrm {V a r} [ T _ {e} (\theta , \bar {u}) ] \approx \sum_ {i} \left(S _ {T _ {e}, \theta_ {i}}\right) ^ {2} \mathrm {V a r} [ \theta_ {i} ] + 2 \sum_ {i <   j} S _ {T _ {e}, \theta_ {i}} S _ {T _ {e}, \theta_ {j}} \mathrm {C o v} (\theta_ {i}, \theta_ {j}),
$$

以及对应的区间端点  $T_{e}^{\mathrm{low}}, T_{e}^{\mathrm{up}}$  。该区间在几何上刻画了耗尽时间在参数不确定性下的波动范围，其长度反映模型预测的稳健性与置信度。

- 使用模式波动对 SOC 曲线  $s(t)$  的影响展示：

对选定的扰动模式  $\delta u^{(m)}(t)$ , 输出对应的 SOC 曲线族

$$
s ^ {(m)} (t) = s \big (t; \theta^ {\star}, \bar {u} + \delta u ^ {(m)} \big),
$$

与基准曲线  $s(t; \theta^{\star}, \bar{u})$  对比。几何上，这是一组在  $[t_0, T_e]$  上的曲线，展示不同使用模式下 SOC 随时间下降的斜率差异与耗尽时刻的平移，直观反映使用模式波动对电量下降过程的影响。

- 使用模式波动对耗尽时间  $T_{e}$  的影响范围描述：

输出在可行使用模式集合  $\mathcal{U}$  中代表性样本的耗尽时间集合  $\{T_e^{(m)}\}$ ，并给出范围估计

$$
T _ {e} ^ {\min } \leq T _ {e} (\theta^ {\star}, u) \leq T _ {e} ^ {\max }, \quad u \in \mathcal {U},
$$

其中  $T_{e}^{\min}$  与  $T_{e}^{\max}$  分别表示在给定使用模式约束下最极端“耗尽最快”和“耗尽最慢”的可能续航时间，从统计或场景角度刻画“日常使用波动”对续航预测的不确定性贡献。

- 关键影响因素的重要性排序指标：

输出参数重要性指标

$$
I _ {\theta_ {i}} = | \tilde {S} _ {T _ {e}, \theta_ {i}} |
$$

与使用模式重要性指标

$$
I _ {u _ {j}} = \int_ {t _ {0}} ^ {T _ {e} (\theta^ {\star}, \bar {u})} | \psi_ {j} (t) | \mathrm {d} t,
$$

按  $I_{\theta_i}$  与  $I_{u_j}$  降序排列，得到容量参数  $C_{\mathrm{eff}}$  、功耗系数  $k_{j}$  、温度系数  $\alpha_{T}$  以及各子系统使用强度在影响耗尽时间上的相对重要性排序。物理上，这一排序给出“哪些物理参数或使用因子对续航预测最敏感”的量化结论，为模型简化、参数校准优先级以及用户使用建议等提供依据。

# 问题四

# 1.3.3 决策变量

- 用户行为配置  $u_{\mathrm{usr}}$

一个有限维向量

$$
u _ {\mathrm {u s r}} = \left(u _ {\mathrm {u s r}, k}\right) _ {k \in \mathcal {K}} \in \mathcal {U} _ {\mathrm {u s r}},
$$

各分量代表用户在一个分析时间窗口内的平均或恒定设置，例如归一化亮度级别、网络模式选择（以合适编码表示）、后台任务允许程度等。其物理意义是“在不改变应用组合的前提下，用户愿意做出的设置调整”。

- OS 电源管理策略  $\pi$

一个从状态空间到可行 OS 控制集合的映射

$$
\pi \colon x \mapsto u _ {\mathrm {o s}} = \pi (x), \quad \pi \in \Pi ,
$$

其中状态向量  $x$  可包含当前SOC、CPU负载、网络活动强度、温度等。  $\pi$  决定OS如何根据状态自动调节如CPU频率、后台调度、网络接口选择等，以实现省电目的。

- 在给定  $(u_{\mathrm{usr}}, \pi)$  的前提下，SOC 轨迹  $s(t)$  、耗尽时间  $T$  、跨设备耗尽时间  $T_d$  、行为优先级指标  $I_{\mathrm{usr}}^{(k)}$  及状态-建议映射  $\mathcal{A}$  均为模型的响应变量，由参数与决策变量通过后续动力学与能量平衡关系唯一确定。

# 1.4. 模型的构建与推导

# 1.4.1 中间变量与子模型构建

# 62.SOC 动力学与耗尽时间定义

- 从能量守恒出发，设  $E(t)$  为时刻  $t$  电池剩余可用能量，在仅放电阶段有

$$
\frac {\mathrm {d} E (t)}{\mathrm {d} t} = - P (t),
$$

其中  $P(t)$  是智能手机的总功耗。

- 在考虑老化后的有效容量  $C_{\mathrm{eff}} = \eta E_{\mathrm{max}}$  下, SOC 定义为

$$
s (t) = \frac {E (t)}{C _ {\mathrm {e f f}}}, 0 \leq s (t) \leq 1.
$$

对时间求导并代入能量守恒式得到 SOC 动力学

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{C _ {\mathrm {e f f}}}, \qquad s (0) = s _ {0}.
$$

- 令  $T$  为从  $t = 0$  放电到 SOC 首次降到阈值  $s_{\mathrm{min}}$  的时间，即

$$
s (T) = s _ {\min }, \quad s (t) > s _ {\min }, \forall t \in [ 0, T).
$$

将 SOC 微分方程在  $[0, T]$  上积分，得到

$$
s _ {\min } = s _ {0} - \frac {1}{C _ {\mathrm {e f f}}} \int_ {0} ^ {T} P (\tau) \mathrm {d} \tau ,
$$

从而得到耗尽时间必须满足的能量平衡条件

$$
\int_ {0} ^ {T} P (\tau) \mathrm {d} \tau = C _ {\text {e f f}} (s _ {0} - s _ {\min}).
$$

- 对于一般便携设备  $d \in \mathcal{D}$ , 若记其有效容量为  $C_{d}$ , 总功耗轨迹为  $P_{d}(t)$ , 类似地有

$$
\int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t = C _ {d} \left(s _ {0} - s _ {\min}\right),
$$

其中  $T_{d}$  为设备  $d$  的耗尽时间。该关系为跨设备缩放提供统一基础。

# 2. 功耗分解与行为/策略的作用

- 为区分不同行为与 OS 策略对功耗的影响，将总功耗分解为典型模块之和

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t),
$$

分别对应屏幕、处理器、网络、GPS与后台任务功耗。

- 每个分量功耗由当前状态  $x(t)$  、用户行为配置  $u_{\mathrm{usr}}$  和 OS 控制  $u_{\mathrm{os}}(t) = \pi(x(t))$  共同决定。抽象写为

$$
P _ {m} (t) = \Phi_ {m} (x (t), u _ {\mathrm {u s r}}, \pi (x (t))), \quad m \in \{\mathrm {s c r}, \mathrm {c p u}, \mathrm {n e t}, \mathrm {g p s}, \mathrm {b g} \},
$$

其中  $\Phi_{m}$  为已标定或可估计的模块功耗函数。对主要行为控制量（例如屏幕亮度  $B$  、后台任务强度  $H$ ）假定单调非减，即

$$
\frac {\partial P _ {\mathrm {s c r}} (t)}{\partial B} \geq 0, \quad \frac {\partial P _ {\mathrm {b g}} (t)}{\partial H} \geq 0.
$$

- 因此，总功耗可视为

$$
P (t) = P (t; x (t), u _ {\mathrm {u s r}}, \pi) = \sum_ {m} \Phi_ {m} (x (t), u _ {\mathrm {u s r}}, \pi (x (t))).
$$

在给定  $(u_{\mathrm{usr}},\pi)$  与状态演化规律的前提下，上式确定了能量平衡方程中的被积函数，从而确定耗尽时间  $T$ 。

# 6. 平均功耗近似与  $T$  的显式表达

- 精确解耗尽时间需利用上式求解积分方程。为便于行为比较与策略排序，引入时间平均功耗

$$
\bar {P} = \frac {1}{T} \int_ {0} ^ {T} P (\tau) d \tau .
$$

将其代入能量平衡式，有近似

$$
T \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}.
$$

- 这一近似说明：在有效容量固定时，平均功耗越低，耗尽时间越长；对相同控制策略  $(u_{\mathrm{usr}}, \pi)$ ，老化导致  $C_{\mathrm{eff}}$  随  $\eta$  缩放，将使  $T$  近似按同一比例缩放。

- 对一般设备  $d$ , 定义其平均功耗

$$
\bar {P} _ {d} = \frac {1}{T _ {d}} \int_ {0} ^ {T _ {d}} P _ {d} (t) d t,
$$

则有类似近似

$$
T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} _ {d}},
$$

这给出跨设备的基本缩放规律。

# 4. 行为影响量化与灵敏度子模型

- 为度量各类用户行为对耗尽时间的影响，将  $T$  视为行为配置和 OS 策略的函数

$$
T = T (u _ {\mathrm {u s r}}, \pi ; \eta , d),
$$

其中  $\eta$  、  $d$  为参数。

- 在基线配置  $(u_{\mathrm{usr}}^0,\pi^0)$  附近，对第  $k$  类行为分量  $u_{\mathrm{usr},k}$  的局部影响可用偏导数表示：

$$
S _ {T, u _ {k}} = \frac {\partial T}{\partial u _ {\mathrm {u s r} , k}} \bigg | _ {(u _ {\mathrm {u s r}} ^ {0}, \pi^ {0})},
$$

表示在其它条件不变时，行为  $k$  做小幅调整对耗尽时间的一阶影响。

- 为消除量纲差异并得到可比较的优先级指标，引入归一化灵敏度

$$
I _ {\mathrm {u s r}} ^ {(k)} = \left| \frac {u _ {\mathrm {u s r} , k} ^ {0}}{T _ {\mathrm {b a s e}}} \frac {\partial T}{\partial u _ {\mathrm {u s r} , k}} \right| _ {(u _ {\mathrm {u s r}} ^ {0}, \pi^ {0})} \bigg |,
$$

其中

$$
T _ {\mathrm {b a s e}} = T (u _ {\mathrm {u s r}} ^ {0}, \pi^ {0}; \eta , d)
$$

为基线配置下的耗尽时间。

$I_{\mathrm{usr}}^{(k)}$  可以理解为：“对行为  $k$  进行单位相对变化所导致的相对耗尽时间变化幅度”，从而成为行为排序的量化依据。

# 5. 老化函数  $T(\eta)$  与归一化续航  $R(\eta)$

- 在给定  $(u_{\mathrm{usr}}, \pi)$  和平均功耗  $\bar{P}$  的前提下，将有效容量写作  $C_{\mathrm{eff}} = \eta E_{\mathrm{max}}$ ，有

$$
T (\eta) \approx \frac {\eta E _ {\mathrm {m a x}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}.
$$

定义归一化续航

$$
R (\eta) = \frac {T (\eta)}{T (1)} \approx \eta ,
$$

表明在平均功耗对老化依赖较弱时，续航随容量保持率近似按比例衰减，可直接用于针对不同老化程度用户的策略调整。

# 6. 状态到建议的映射子模型

- 为将上述灵敏度和老化分析转化为实用建议，引入映射

$$
\mathcal {A} \colon (x (t), \eta , d) \mapsto (\mathcal {S} _ {\mathrm {r e c}}, [ \Delta T _ {\mathrm {m i n}}, \Delta T _ {\mathrm {m a x}} ]),
$$

其中：

○ 输入状态  $x(t)$  包含当前 SOC、负载、网络活动强度、环境温度等；

○  $S_{\mathrm{rec}}$  为推荐操作集合（例如“降低亮度”“关闭部分后台任务”“切换到Wi-Fi”等），可视为一组新的行为配置  $u_{\mathrm{usr}}$  与策略  $\pi$ ；

$\mathrm{[}\Delta T_{\mathrm{min}},\Delta T_{\mathrm{max}}\mathrm{]}$  为基于平均功耗近似和灵敏度分析给出的预期续航改善区间。

- 对给定候选操作集合  $\mathcal{S}_{\mathrm{cand}}$  中的每个操作  $a$  ，其对应配置记为  $(u_{\mathrm{usr}}^{(a)},\pi^{(a)})$  ，可通过

$$
\Delta T ^ {(a)} = T \Big (u _ {\mathrm {u s r}} ^ {(a)}, \pi^ {(a)}; \eta , d \Big) - T _ {\mathrm {b a s e}}
$$

计算预期耗尽时间增量，并在  $\mathcal{S}_{\mathrm{cand}}$  上选取具有最大或足够大的  $\Delta T^{(a)}$  的操作构成  $S_{\mathrm{rec}}$  ，从而实现“模型  $\rightarrow$  建议”的映射。

# 1.4.2 目标函数

在上述物理与功能关系基础上，本问题的核心优化目标是：在硬件与用户体验约束允许的范围内，通过调整用户行为配置  $u_{\mathrm{usr}}$  与设计OS策略  $\pi$ ，最大化在给定设备  $d$  与电池老化程度  $\eta$  下的续航提升，即耗尽时间相对于基线配置的增量。

用基线耗尽时间

$$
T _ {\text {b a s e}} = T \left(u _ {\text {u s r}} ^ {0}, \pi^ {0}; \eta , d\right)
$$

表示原始使用模式下的耗尽时间，定义策略前后耗尽时间增量为

$$
\Delta T (u _ {\mathrm {u s r}}, \pi ; \eta , d) = T (u _ {\mathrm {u s r}}, \pi ; \eta , d) - T _ {\mathrm {b a s e}}.
$$

则典型的优化目标可表述为

$$
\max_{u_{\mathbf{usr}}\in \mathcal{U}_{\mathbf{usr}},  \pi \in \Pi}\Delta T(u_{\mathbf{usr}},\pi ;\eta ,d),
$$

即在所有可行的用户行为与OS策略组合中寻找能够最大化续航提升的配置。

在具体应用中，可分别考虑：

- 用户侧优化子问题（固定OS策略  $\pi^0$ ）：

$$
\max  _ {u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}} \Delta T (u _ {\mathrm {u s r}}, \pi^ {0}; \eta , d),
$$

对应“在当前 OS 下，给用户什么设置建议最能提升续航”。

- OS 侧优化子问题（固定行为配置  $u_{\mathrm{usr}}^0$ ）：

$$
\max _ {\pi \in \Pi} \Delta T (u _ {\mathrm {u s r}} ^ {0}, \pi ; \eta , d),
$$

对应“在既定用户使用习惯下，如何设计 OS 策略以最大化续航”。

行为优先级指标  $I_{\mathrm{usr}}^{(k)}$  与老化函数  $T(\eta)$  、跨设备耗尽时间  $T_{d}$  以及状态-建议映射  $\mathcal{A}$ ，均作为上述优化问题的分析工具和输出指标。

# 1.4.3 约束条件

(1) SOC 定义与范围约束：

SOC 由剩余能量相对有效容量定义，其取值受物理上限与耗尽阈值限制：

$$
s (t) = \frac {E (t)}{C _ {\mathrm {e f f}}}, \qquad 0 \leq s _ {\mathrm {m i n}} \leq s (t) \leq 1, \quad \forall t \in [ 0, T ].
$$

(2) SOC 动力学与耗尽时间约束：

在仅放电、无充电回馈的前提下，SOC 随时间单调不增，且耗尽时间为首次达到阈值的时刻：

$$
\begin{array}{l} \frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{C _ {\mathrm {e f f}}} \leq 0, \quad \forall t \in [ 0, T ], \\ s (T) = s _ {\min }, \quad s (t) > s _ {\min }, \forall t \in [ \mathbf {0}, T). \\ \end{array}
$$

(3) 功耗加和性与模块非负约束：

总功耗等于各模块功耗之和，各模块功耗始终非负：

$$
\begin{array}{l} P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t), \\ P (t) \geq \mathbf {0}, \quad P _ {\mathrm {s c r}} (t), P _ {\mathrm {c p u}} (t), P _ {\mathrm {n e t}} (t), P _ {\mathrm {g p s}} (t), P _ {\mathrm {b g}} (t) \geq \mathbf {0}, \quad \forall t \in [ \mathbf {0}, T ]. \\ \end{array}
$$

(4) 行为与 OS 控制可行性约束：

用户与 OS 的控制选择必须落在各自可行集合内，且 OS 控制由策略函数生成：

$$
u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}, \quad \pi \in \Pi , \quad u _ {\mathrm {o s}} (t) = \pi (x (t)),
$$

其中可行集合  $\mathcal{U}_{\mathrm{usr}}$  、  $\Pi$  由硬件能力和系统设计限定，例如亮度上下限、合法的网络模式集合、允许的CPU频率档位等。

(5) 行为对功耗的单调非减性约束：

对关键用户行为（如亮度、后台任务强度），其增大不能降低对应模块功耗，形式化为

$$
\frac {\partial P _ {\mathrm {s c r}} (t)}{\partial B} \geq 0, \quad \frac {\partial P _ {\mathrm {b g}} (t)}{\partial H} \geq 0,
$$

并推广到其它直接受用户控制的模块，使得由模型生成的建议始终与“降低设置  $\Rightarrow$  降低功耗”这一直觉一致。

# (6) 电池老化与有效容量约束：

容量保持率  $\eta$  描述老化程度，有效容量由其与标称容量线性确定，且老化不会使容量增加：

$$
C _ {\mathrm {e f f}} = \eta E _ {\mathrm {m a x}}, \qquad 0 <   \eta \leq 1.
$$

# (7) 跨设备能量守恒与缩放约束：

对任一设备  $d \in \mathcal{D}$ ，从  $t = 0$  到耗尽时间  $T_{d}$  的累计能量消耗等于初始可用容量：

$$
\int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t = C _ {d} (s _ {0} - s _ {\min}), T _ {d} \geq 0.
$$

在平均功耗近似下，耗尽时间满足

$$
T _ {d} \approx \frac {C _ {d} \left(s _ {0} - s _ {\min}\right)}{\bar {P} _ {d}}, \quad \bar {P} _ {d} = \frac {1}{T _ {d}} \int_ {0} ^ {T _ {d}} P _ {d} (t) d t.
$$

# (8) 平均功耗-耗尽时间反比约束：

对手机本身，在平均功耗近似下，耗尽时间与平均功耗呈反比：

$$
T \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}, \quad \bar {P} = \frac {1}{T} \int_ {0} ^ {T} P (t) \mathrm {d} t.
$$

该约束用于将“功耗变化”转化为“耗尽时间变化”，从而构建  $\Delta T$  与  $I_{\mathrm{usr}}^{(k)}$  。

# (9) 基线与优化策略的能量一致性约束：

在相同初始 SOC 与有效容量下，基线配置与优化配置从开始到各自耗尽时刻消耗的总能量必须相同：

$$
\int_ {0} ^ {T _ {\mathrm {b a s e}}} P ^ {\mathrm {b a s e}} (t) \mathrm {d} t = \int_ {0} ^ {T _ {\mathrm {o p t}}} P ^ {\mathrm {o p t}} (t) \mathrm {d} t = C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}}),
$$

其中  $P^{\mathrm{base}}(t)$  、  $P^{\mathrm{opt}}(t)$  分别由  $(u_{\mathrm{usr}}^{0},\pi^{0})$  与  $(u_{\mathrm{usr}},\pi)$  决定。

# (10) 状态- 建议映射可行性约束：

映射  $\mathcal{A}$  输出的推荐操作集合必须对应某个可行组合  $(u_{\mathrm{usr}}, \pi)$ , 且在行为-功耗单调性与能量守恒约束下给出的预期续航改善区间是与模型一致的。形式化地, 对任一状态  $(x(t), \eta, d)$ ,

$$
\mathcal {A} (x (t), \eta , d) = (\mathcal {S} _ {\mathrm {r e c}}, [ \Delta T _ {\mathrm {m i n}}, \Delta T _ {\mathrm {m a x}} ]),
$$

且对每个推荐操作  $a \in S_{\mathrm{rec}}$ ，存在  $(u_{\mathrm{usr}}^{(a)}, \pi^{(a)})$  满足上述控制可行性与功耗单调性约束，使得

$$
\Delta T _ {\mathrm {m i n}} \leq T \Big (u _ {\mathrm {u s r}} ^ {(a)}, \pi^ {(a)}; \eta , d \Big) - T _ {\mathrm {b a s e}} \leq \Delta T _ {\mathrm {m a x}}.
$$

# 1.5 模型汇总

在上述推导基础上，本问题的模型可概括为以下标准形式：

- 目标函数（续航提升最大化）：

$$
\max  _ {u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}, \pi \in \Pi} \Delta T (u _ {\mathrm {u s r}}, \pi ; \eta , d) = T (u _ {\mathrm {u s r}}, \pi ; \eta , d) - T _ {\mathrm {b a s e}},
$$

其中  $T_{\mathrm{base}} = T(u_{\mathrm{usr}}^{0}, \pi^{0}; \eta, d)$ 。

# 主要约束条件：

1. SOC 定义与范围：

$$
s (t) = \frac {E (t)}{C _ {\mathrm {e f f}}}, \quad 0 \leq s _ {\min } \leq s (t) \leq 1.
$$

2. SOC 动力学与耗尽条件：

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t)}{C _ {\text {e f f}}} \leq 0, \quad s (T) = s _ {\min}.
$$

3. 功耗分解与非负：

$$
P (t) = P _ {\mathrm {s c r}} (t) + P _ {\mathrm {c p u}} (t) + P _ {\mathrm {n e t}} (t) + P _ {\mathrm {g p s}} (t) + P _ {\mathrm {b g}} (t) \geq 0,
$$

$$
P _ {\mathrm {s c r}} (t), P _ {\mathrm {c p u}} (t), P _ {\mathrm {n e t}} (t), P _ {\mathrm {g p s}} (t), P _ {\mathrm {b g}} (t) \geq 0.
$$

4. 控制可行性与OS策略：

$$
u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}, \quad \pi \in \Pi , \quad u _ {\mathrm {o s}} (t) = \pi (x (t)).
$$

5. 行为-功耗单调性：

$$
\frac {\partial P _ {\mathrm {s c r}} (t)}{\partial B} \geq 0, \quad \frac {\partial P _ {\mathrm {b g}} (t)}{\partial H} \geq 0.
$$

6. 老化与容量：

$$
C _ {\mathrm {e f f}} = \eta E _ {\mathrm {m a x}}, 0 <   \eta \leq 1.
$$

7. 跨设备能量守恒与缩放：

$$
\int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t = C _ {d} (s _ {0} - s _ {\min}), T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\min})}{\bar {P} _ {d}}.
$$

8. 平均功耗 - 耗尽时间反比：

$$
T \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}, \quad \bar {P} = \frac {1}{T} \int_ {0} ^ {T} P (t) \mathrm {d} t.
$$

9. 基线与优化配置能量一致性：

$$
\int_ {0} ^ {T _ {\text {b a s e}}} P ^ {\text {b a s e}} (t) \mathrm {d} t = \int_ {0} ^ {T _ {\text {o p t}}} P ^ {\text {o p t}} (t) \mathrm {d} t = C _ {\text {e f f}} \left(s _ {0} - s _ {\min}\right).
$$

10. 状态 - 建议映射可行性：

$$
\mathcal {A} (x (t), \eta , d) = (\mathcal {S} _ {\mathrm {r e c}}, [ \Delta T _ {\mathrm {m i n}}, \Delta T _ {\mathrm {m a x}} ]),
$$

且对每个  $a \in S_{\mathrm{rec}}$ ，存在可行  $(u_{\mathrm{usr}}^{(a)}, \pi^{(a)})$  使得其  $\Delta T$  落入给定区间。

# 在该模型框架下：

- 通过求解 SOC 动力学与能量平衡，可在不同用户行为与 OS 策略下获得耗尽时间  $T$ ，从而计算各候选操作的  $\Delta T$ ，实现“各用户行为的续航影响量化”；

- 通过归一化灵敏度  $I_{\mathrm{usr}}^{(k)}$  排序行为，可形成“用户行为优先级排序”；

- 通过在策略可行集合  $\Pi$  上求解最大化问题，可设计OS电源管理策略 $\pi$  并量化  $T_{\mathrm{opt}}$  与  $T_{\mathrm{base}}$  的比较；

- 通过引入容量保持率  $\eta$  并分析  $T(\eta)$  与  $R(\eta)$  的变化，可刻画电池老化对续航及建议的影响规律；

- 通过跨设备缩放关系  $T_{d} \approx C_{d}\left(s_{0}-s_{\min }\right) / \bar{P}_{d}$ , 可将手机上的建模与建议推广到其他便携设备;

- 最终借助映射  $\mathcal{A}$ , 可将模型输出转化为 “状态  $\rightarrow$  建议集合及预期  $\Delta T$  区间”的实用建议表, 从而系统性地回答问题四的全部需求。

# 问题四的模型求解

# 2.1 算法设计

# 63. 算法名称与原理概述

$\mathrm{O}$  算法名称：

基于 SOC 数值仿真与灵敏度驱动的约束优化与策略排序算法（仿真核为 Runge-Kutta ODE 积分）。

核心思想：

利用SOC-功耗连续时间模型

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t ; x (t) , u _ {\mathrm {u s r}} , \pi (x (t)))}{C _ {\mathrm {e f f}}}, \quad C _ {\mathrm {e f f}} = \eta E _ {\max },
$$

在给定用户行为  $u_{\mathrm{usr}}$  与OS策略  $\pi$  下，通过数值积分求得SOC轨迹  $s(t)$  与耗尽时间  $T$  （满足  $s(T) = s_{\min}$  且  $s(t) > s_{\min}, t \in [0,T)$ ），并计算平均功耗

$$
\bar {P} = \frac {1}{T} \int_ {0} ^ {T} P (t) d t.
$$

在此基础上：

- 通过对行为分量  $u_{\mathrm{usr}, k}$  的扰动, 利用有限差分或灵敏度方程近似

$$
\frac {\partial T}{\partial u _ {\mathrm {u s r} , k}},
$$

构造归一化灵敏度指标

$$
I _ {\mathrm {u s r}} ^ {(k)} = \left| \frac {u _ {\mathrm {u s r} , k} ^ {0}}{T _ {\mathrm {b a s e}}} \frac {\partial T}{\partial u _ {\mathrm {u s r} , k}} \right| _ {(u _ {\mathrm {u s r}} ^ {0}, \pi^ {0})} \Bigg |,
$$

用于量化和排序各行为对耗尽时间的影响。

- 将 OS 策略  $\pi$  与用户行为  $u_{\mathrm{usr}}$  用有限维参数向量  $\varphi$  表示，在可行集约束下求解

$$
\max  _ {\varphi \in \mathcal {F}} \Delta T (\varphi) = T (\varphi) - T _ {\text {b a s e}},
$$

形成联合节能优化。

- 利用老化关系  $C_{\mathrm{eff}} = \eta E_{\max}$  和平均功耗近似

$$
T (\eta) \approx \frac {\eta E _ {\mathrm {m a x}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}, \quad R (\eta) = \frac {T (\eta)}{T (1)},
$$

分析电池老化对续航及建议的影响。

- 对任意设备  $d$ , 利用

$$
\int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t = C _ {d} (s _ {0} - s _ {\min}), T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\min})}{\bar {P} _ {d}},
$$

构造跨设备的缩放规律。

- 通过离线扫描不同状态  $(x, \eta, d)$ , 收集在各状态下的最优或次优操作集合及其  $\Delta T$  区间, 构建查表式映射

$$
\mathcal {A} \colon (x, \eta , d) \mapsto \left(\mathcal {S} _ {\text {r e c}}, [ \Delta T _ {\min }, \Delta T _ {\max } ]\right) 。
$$

# 64. 模型特性与算法选择的必要性

# 非线性、约束与多目标特性

功耗模型

$$
P (t) = \sum_ {m} P _ {m} (t), \quad P _ {m} (t) = \Phi_ {m} (x (t), u _ {\mathrm {u s r}}, \pi (x (t)))
$$

一般为非线性函数，且受单调性约束

$$
\frac {\partial P _ {\mathrm {s c r}}}{\partial B} \geq 0, \quad \frac {\partial P _ {\mathrm {b g}}}{\partial H} \geq 0,
$$

同时必须满足控制可行性

$$
u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}, \quad \pi \in \Pi .
$$

目标函数

$$
\Delta T (u _ {\mathrm {u s r}}, \pi ; \eta , d) = T (u _ {\mathrm {u s r}}, \pi ; \eta , d) - T _ {\mathrm {b a s e}}
$$

是通过 ODE 解隐式给出的非线性函数，无法解析求导。这使得问题属于约束非线性规划，需借助数值仿真与数值梯度。

# ○ SOC 动力学的一维性与 Runge-Kutta 的高效性

SOC动力学

$$
\frac {\mathrm {d} s}{\mathrm {d} t} = - \frac {P (t)}{C _ {\mathrm {e f f}}}, \quad s (0) = s _ {0},
$$

维度低，且右端满足 Lipschitz 条件，适合采用四阶 Runge-Kutta（RK4）或梯形积分等显式/半隐式 ODE 方法。

RK4 在固定时间步长下具有较高精度，便于在外层优化中重复调用而保持计算成本可控。

# ○ 灵敏度驱动的策略排序必要性

行为空间  $\mathcal{U}_{\mathrm{usr}}$  及策略空间  $\Pi$  可维数较高, 若直接对所有组合做穷举仿真, 将导致计算量指数增长。灵敏度指标  $I_{\mathrm{usr}}^{(k)}$  能提供局部最“划算”的调整方向, 用于筛选有限个高潜力操作, 显著减少需要仿真的候选集合, 是构造实用建议表的关键。

# 平均功耗近似对跨设备推广的适用性

在假设平均功耗代表典型使用水平的前提下，关系

$$
T \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P}}, T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} _ {d}}
$$

将复杂的时间序列问题简化为容量与平均功耗的比例问题，极大方便了老化分析与跨设备缩放。该近似可由数值积分结果验证精度。

# 65. 决策变量编码与搜索空间

# 用户行为配置向量

$$
u _ {\mathrm {u s r}} = (u _ {\mathrm {u s r}, k}) _ {k \in \mathcal {K}} \in \mathcal {U} _ {\mathrm {u s r}},
$$

其中各分量可为：

- 亮度上限  $B$ ;

网络模式/接口选择编码N；

GPS 使用策略  $G$

后台任务强度上限  $H$  等。

在算法中  $u_{\mathrm{usr}}$  被视为在分析窗口内的恒定或分段常数。

# ○ OS 策略参数向量

$$
\varphi_ {o s} \in \mathbb {R} ^ {p}, \quad \pi = \pi_ {\varphi_ {o s}} \in \Pi ,
$$

例如：

CPU频率缩放系数；

- 屏幕自动熄灭超时时间；

- 后台同步间隔；

- 在不同 SOC 阈值下的限频/限网规则等。

通过对策略函数族  $\Pi$  做参数化，将无限维函数优化转化为有限维向量优化。

# • 联合参数向量

$$
\varphi = (u _ {\mathrm {u s r}}, \varphi_ {\mathrm {o s}}) \in \mathcal {F} \subset \mathbb {R} ^ {q},
$$

其中可行集  $\mathcal{F}$  由  $u_{\mathrm{usr}} \in \mathcal{U}_{\mathrm{usr}}$ 、 $\pi_{\varphi_{\mathrm{os}}} \in \Pi$ 、以及用户体验约束等共同确定。

# 目标到适应度的转化

对给定  $\varphi$  ，经仿真得到耗尽时间  $T(\varphi)$  ，定义：

适应度函数（用于最大化算法）

$$
F (\varphi) = T (\varphi),
$$

- 或等价的最小化目标

$$
J (\varphi) = - T (\varphi).
$$

在需要利用平均功耗近似时，可用

$$
T (\varphi) \approx \frac {C _ {\mathrm {e f f}} \left(s _ {0} - s _ {\min }\right)}{\bar {P} (\varphi)}
$$

的形式计算或验证。

# 66. 关键算法参数定义

。ODE仿真相关：

时间步长:  $\Delta t > 0$ ;

最大仿真时间：  $T_{\mathrm{max}} > 0$

- SOC 终止容差:  $\varepsilon_{s} > 0$  (当  $s(t) \leq s_{\min} + \varepsilon_{s}$  时停止积分);

最大时间步数:  $N_{\max} = T_{\max} / \Delta t$  。

○ 灵敏度与有限差分相关:

- 行为分量扰动幅度:  $\delta_{u, k} > 0$ ;

策略参数扰动幅度:  $\delta_{\varphi ,i} > 0$

用于近似偏导数

$$
\frac {\partial T}{\partial u _ {\mathrm {u s r} , k}}, \quad \frac {\partial T}{\partial \varphi_ {i}}.
$$

○ 非线性规划（SQP/内点法）相关：

最大迭代次数：  $K_{\mathrm{max}}$

目标改进阈值： $\varepsilon_T > 0$ （当相邻两次迭代的  $|T^{(k + 1)} - T^{(k)}| < \varepsilon_T$  时收敛）；

梯度范数阈值:  $\varepsilon_{g} > 0$ ;

约束可行性容差：  $\varepsilon_{c} > 0$

○ 状态-建议映射离线构建相关：

- 状态网格点数： $N_{x}$ （在SOC、负载、网络活动强度等维度上）；

- 容量保持率采样点数:  $N_{\eta}$ ;

设备采样数:  $N_{d}$ ;

- 每个状态下评估的候选操作数： $K_{\mathrm{cand}}$ ；

- 选入建议表的推荐操作数上限:  $K_{\mathrm{rec}}$ 。

# 2.2 求解流程

# 步骤 1: 数据准备与参数初始化

步骤目的：

在无外部数据文件的前提下，统一整理模型所需的初始条件、设备参数及算法运行参数，为后续SOC仿真与优化提供输入。

# 67. 初始条件与模型参数设置

设置时间原点：

$$
t _ {0} = 0.
$$

o 设定初始SOC:

$$
s (0) = s _ {0}, \quad 0 <   s _ {0} \leq 1.
$$

。设定耗尽阈值：

$$
s _ {\min } \in [ 0, 1), \quad \text {并 在 后 续 仿 真 中 检 测} s (t) \downarrow s _ {\min }.
$$

○ 给定新电池额定容量  $E_{\mathrm{max}}$  和容量保持率  $\eta$ , 计算有效容量:

$$
C _ {\mathrm {e f f}} = \eta E _ {\max}, \quad 0 <   \eta \leq 1.
$$

。对设备集合  $\mathcal{D}$  中每个设备  $d$  ，给定其电池容量  $C_d$  、初始SOC  $s_0$  、耗尽阈值  $s_{\min}$  。

以上设置直接对应模型约束

$$
s (t) = \frac {E (t)}{C _ {\mathrm {e f f}}}, 0 \leq s _ {\mathrm {m i n}} \leq s (t) \leq 1,
$$

以及老化约束

$$
C _ {\mathrm {e f f}} = \eta E _ {\mathrm {m a x}}.
$$

# 68. 基线行为与基线 OS 策略初始化

。设定基线用户行为配置：

$$
u _ {\mathrm {u s r}} ^ {0} = (u _ {\mathrm {u s r}, k} ^ {0}) _ {k \in \mathcal {K}} \in \mathcal {U} _ {\mathrm {u s r}},
$$

表示默认亮度、网络模式、后台开关等。

。设定基线OS策略：

$$
\pi^ {0} \in \Pi , \quad u _ {\mathrm {o s}} ^ {0} (t) = \pi^ {0} (x (t)),
$$

表示默认的CPU频率调度、后台调度等。

# 69. 算法参数初始化

选择 ODE 仿真步长  $\Delta t$ 、最大仿真时间  $T_{\mathrm{max}}$ ，并设定  $N_{\mathrm{max}} = T_{\mathrm{max}} / \Delta t$ 。

。设定SOC判停容差  $\varepsilon_{s}$  。

。为有限差分设定扰动：

$$
\delta_ {u, k}, \delta_ {\varphi , i} > 0.
$$

$\circ$  为优化算法设定:  $K_{\max}, \varepsilon_T, \varepsilon_g, \varepsilon_c$  。

○ 为状态 - 建议映射设定:  $N_{x}, N_{\eta}, N_{d}, K_{\text {cand}}, K_{\text {rec}}$  。

# 步骤 2: SOC 仿真核构建 (RK4 积分)

步骤目的：

实现对SOC动力学

$$
\frac {\mathrm {d} s (t)}{\mathrm {d} t} = - \frac {P (t ; x (t) , u _ {\mathrm {u s r}} , \pi (x (t)))}{C _ {\mathrm {e f f}}}, \quad s (0) = s _ {0}
$$

的数值积分，为所有策略评估提供统一仿真核。

# 70. 时间离散与状态初始化

构造离散时间序列：

$$
t _ {n} = t _ {0} + n \Delta t, \quad n = 0, 1, \dots , N _ {\max}.
$$

○ 初始化：

$s_{0} = s\left(t_{0}\right), \quad x_{0} = x\left(t_{0}\right)$  （包括  $s_{0}$ , 负载、温度等）.

# 71. 功耗分解与计算

对每个时间步  $t_n$ ，给定  $x_n, u_{\mathrm{usr}}$  和  $\pi$ ：

。根据策略求OS控制：

$$
u _ {\mathrm {o s}, n} = \pi (x _ {n}), \quad u _ {\mathrm {o s}, n} \in \mathcal {U} _ {\mathrm {o s}}.
$$

o 计算各模块功耗：

$$
P _ {m} (t _ {n}) = \Phi_ {m} \big (x _ {n}, u _ {\mathrm {u s r}}, u _ {\mathrm {o s}, n} \big), \quad m \in \{\mathrm {s c r}, \mathrm {c p u}, \mathrm {n e t}, \mathrm {g p s}, \mathrm {b g} \},
$$

并强制

$$
P _ {m} (t _ {n}) \geq 0.
$$

合成总功耗：

$$
P (t _ {n}) = \sum_ {m} P _ {m} (t _ {n}) \geq 0,
$$

满足功耗加和性约束。

# 72.RK4步进公式

将 SOC 右端函数记为

$$
f (t, s; x, u _ {\mathrm {u s r}}, \pi) = - \frac {P (t ; x , u _ {\mathrm {u s r}} , \pi (x))}{C _ {\mathrm {e f f}}}.
$$

在时间步  $t_{n}$  上，执行 RK4 更新：

计算中间斜率：

$$
\begin{array}{l} k _ {1} = f \left(t _ {n}, s _ {n}; x _ {n}, u _ {\mathrm {u s r}}, \pi\right), \\ k _ {2} = f \big (t _ {n} + \Delta t / 2, s _ {n} + \Delta t / 2 k _ {1}; x _ {n, 2}, u _ {\mathrm {u s r}}, \pi \big), \\ k _ {3} = f \big (t _ {n} + \Delta t / 2, s _ {n} + \Delta t / 2 k _ {2}; x _ {n, 3}, u _ {\mathrm {u s r}}, \pi \big), \\ k _ {4} = f \big (t _ {n} + \Delta t, s _ {n} + \Delta t k _ {3}; x _ {n, 4}, u _ {\mathrm {u s r}}, \pi \big), \\ \end{array}
$$

其中  $x_{n,2}, x_{n,3}, x_{n,4}$  为相应中间状态（可按需要更新负载、温度等）。

○ 更新SOC:

$$
s _ {n + 1} = s _ {n} + \frac {\Delta t}{6} (k _ {1} + 2 k _ {2} + 2 k _ {3} + k _ {4}).
$$

。为保持放电单调性（约束  $\mathrm{ds} / \mathrm{dt} \leq 0$ ），可对数值结果施加

$$
s _ {n + 1} \leftarrow \min  \{s _ {n + 1}, s _ {n} \}.
$$

# 73. 耗尽判定与平均功耗估算

若  $s_{n + 1}\leq s_{\min} + \varepsilon_s$  ，则令

$$
T = (n + 1) \Delta t,
$$

并终止积分，保证满足

$$
s (T) \approx s _ {\min }
$$

同时利用梯形公式近似能量积累：

$$
\int_ {0} ^ {T} P (t) \mathrm {d} t \approx \sum_ {i = 0} ^ {n} \frac {P (t _ {i}) + P (t _ {i + 1})}{2} \Delta t,
$$

据此计算平均功耗：

$$
\bar {P} = \frac {1}{T} \int_ {0} ^ {T} P (t) d t.
$$

。可检查能量守恒近似：

$$
\left| \int_ {0} ^ {T} P (t) d t - C _ {\mathrm {e f f}} \left(s _ {0} - s _ {\min}\right) \right| \leq \varepsilon_ {c},
$$

若误差过大，可减小  $\Delta t$  重新仿真。

该仿真核在后续所有步骤中复用，用于计算  $T$  、  $\bar{P}$  及跨设备  $T_{d}$  。

# 步骤3：基线配置下耗尽时间与平均功耗计算

步骤目的：

在基线行为  $u_{\mathrm{usr}}^0$  和基线策略  $\pi^0$  下，利用步骤2的仿真核求得基线耗尽时间  $T_{\mathrm{base}}$  与平均功耗  $\bar{P}_{\mathrm{base}}$ ，作为行为影响与策略优化的参照。

# 74. 输入配置

○ 固定：

$$
u _ {\mathrm {u s r}} = u _ {\mathrm {u s r}} ^ {0}, \quad \pi = \pi^ {0}.
$$

$\circ$  使用步骤1中的  $s_0,s_{\mathrm{min}},C_{\mathrm{eff}}$

# 75. 仿真与结果

调用步骤2的仿真核，得到：

$$
T _ {\mathrm {b a s e}} = T (u _ {\mathrm {u s r}} ^ {0}, \pi^ {0}; \eta , d),
$$

$$
\bar {P} _ {\mathrm {b a s e}} = \bar {P} (u _ {\mathrm {u s r}} ^ {0}, \pi^ {0}; \eta , d).
$$

。可利用平均功耗近似验证：

$$
T _ {\mathrm {b a s e}} \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} _ {\mathrm {b a s e}}}.
$$

# 步骤 4: 用户行为灵敏度计算与  $\Delta T$  估计

步骤目的：

利用有限差分近似  $\partial T / \partial u_{\mathrm{usr},k}$ ，计算各行为的灵敏度与续航改善量，为行为优先级排序提供量化依据。

# 76. 对每个行为分量构造扰动

对  $k \in \mathcal{K}$ , 定义单位基向量  $e_k$ , 并选择扰动幅度  $\delta_{u,k}$ , 构造扰动行为:

$$
u _ {\mathrm {u s r}} ^ {(k, +)} = u _ {\mathrm {u s r}} ^ {0} + \delta_ {u, k} e _ {k}.
$$

若  $u_{\mathrm{usr}}^{(k, + )}\notin \mathcal{U}_{\mathrm{usr}}$  ，则对其做投影：

$$
u _ {\mathrm {u s r}} ^ {(k, +)} \leftarrow \Pi_ {\mathcal {U} _ {\mathrm {u s r}}} \Big (u _ {\mathrm {u s r}} ^ {(k, +)} \Big),
$$

保证控制可行性约束。

# 77. 有限差分近似耗尽时间偏导数

对每个  $k$ , 固定  $\pi = \pi^{0}$ , 调用仿真核计算

$$
T ^ {(k, +)} = T \left(u _ {\mathrm {u s r}} ^ {(k, +)}, \pi^ {0}; \eta , d\right).
$$

。用前向差分近似：

$$
\left. \frac {\partial T}{\partial u _ {\mathrm {u s r} , k}} \right| _ {(u _ {\mathrm {u s r}} ^ {0}, \pi^ {0})} \approx \frac {T ^ {(k , +)} - T _ {\mathrm {b a s e}}}{\delta_ {u , k}}.
$$

# 78. 归一化灵敏度与小幅行为变化的  $\Delta T$

计算归一化指标：

$$
I _ {\mathrm {u s r}} ^ {(k)} = \left| \frac {u _ {\mathrm {u s r} , k} ^ {0}}{T _ {\mathrm {b a s e}}} \frac {T ^ {(k , +)} - T _ {\mathrm {b a s e}}}{\delta_ {u , k}} \right|.
$$

。若为行为  $k$  预设一个实际可行的小幅变化  $\Delta u_{\mathrm{usr}, k}$  （如亮度降低 $10\%$ ），则用线性近似估计耗尽时间变化：

$$
\Delta T _ {\mathrm {l i n}} ^ {(k)} \approx \frac {\partial T}{\partial u _ {\mathrm {u s r} , k}} \bigg | _ {(u _ {\mathrm {u s r}} ^ {0}, \pi^ {0})} \Delta u _ {\mathrm {u s r}, k}.
$$

。若需要更精确估计，可构造实际调整后的行为向量

$$
u _ {\mathrm {u s r}} ^ {(k, \mathrm {o p t})} = u _ {\mathrm {u s r}} ^ {0} + \Delta u _ {\mathrm {u s r}, k} e _ {k},
$$

再次仿真得到

$$
T _ {\mathrm {o p t}} ^ {(k)} = T \left(u _ {\mathrm {u s r}} ^ {(k, \mathrm {o p t})}, \pi^ {0}; \eta , d\right),
$$

并计算真实耗尽时间增量：

$$
\Delta T ^ {(k)} = T _ {\mathrm {o p t}} ^ {(k)} - T _ {\mathrm {b a s e}}.
$$

# 步骤 5：用户行为优先级排序与候选建议生成

步骤目的：

基于  $I_{\mathrm{usr}}^{(k)}$  和  $\Delta T^{(k)}$  对行为进行排序，筛选出优先推荐的操作集合。

# 79. 排序规则

$\circ$  将行为集合  $\mathcal{K}$  按  $I_{\mathrm{usr}}^{(k)}$  从大到小排序, 得到序列

$$
k _ {(1)}, k _ {(2)}, \dots , k _ {(| \mathcal {K} |)},
$$

其中

$$
I _ {\mathrm {u s r}} ^ {(k _ {(1)})} \geq I _ {\mathrm {u s r}} ^ {(k _ {(2)})} \geq \dots .
$$

。若两行为的  $I_{\mathrm{usr}}^{(k)}$  接近，可用对应的  $\Delta T^{(k)}$  作为次级排序依据。

# 80. 生成候选用户侧建议

。对前  $K_{\mathrm{rec}}$  个行为  $k_{(j)}$  ，构造具体建议操作（例如“亮度从  $u_{\mathrm{usr}, k}^{0}$  降低为  $u_{\mathrm{usr}, k}^{0} - \Delta u_{\mathrm{usr}, k}$  ），记为操作  $a_{(j)}$  。

。利用步骤4的  $T_{\mathrm{opt}}^{(k_{(j)})}$  或线性近似，给出每个操作的耗尽时间改善区间：

$$
[ \Delta T _ {\min} ^ {(a _ {(j)})}, \Delta T _ {\max} ^ {(a _ {(j)})} ],
$$

例如以不同扰动幅度或模型不确定性上下界构造该区间。

。汇总形成用户侧候选建议集合

$$
\mathcal {S} _ {\mathrm {u s r}} ^ {\mathrm {c a n d}} = \left\{a _ {(j)} \right\} _ {j = 1} ^ {K _ {\mathrm {r e c}}}.
$$

该步骤直接生成“各用户行为的续航影响量化结果”和“用户行为优先级排序”所需的中间量。

# 步骤 6：OS 策略参数化与单独优化

步骤目的：

在固定用户行为  $u_{\mathrm{usr}}^{0}$  的条件下，通过优化 OS 策略参数  $\varphi_{\mathrm{os}}$  ，求解 OS 侧最优电源管理策略  $\pi^{\star}$  及其带来的  $T_{\mathrm{opt}}$  与  $\Delta T$  。

# 81. 策略参数化

○ 选定一族策略函数

$$
\pi_ {\varphi_ {0 s}} \colon x \mapsto u _ {0 s} (t),
$$

其中  $\varphi_{\mathrm{os}} \in \mathbb{R}^p$  。例如：

基于SOC的限频阈值向量；

- 不同负载区间下的 CPU 频率缩放系数；

网络接口切换规则参数等。

○ 给定基线参数  $\varphi_{\mathrm{os}}^{0}$ , 满足

$$
\pi_ {\varphi_ {\mathrm {o s}} ^ {0}} = \pi^ {0}.
$$

# 82. 优化问题形式化

○ 固定  $u_{\mathrm{usr}} = u_{\mathrm{usr}}^{0}$ , 定义目标:

$$
F (\varphi_ {\mathrm {o s}}) = T \left(u _ {\mathrm {u s r}} ^ {0}, \pi_ {\varphi_ {\mathrm {o s}}}; \eta , d\right).
$$

约束：

$$
\varphi_ {\mathrm {o s}} \in \mathcal {F} _ {\mathrm {o s}} \subset \mathbb {R} ^ {p}, \quad \pi_ {\varphi_ {\mathrm {o s}}} \in \Pi ,
$$

其中  $\mathcal{F}_{\mathrm{os}}$  包含：

- 控制可行性（对应  $\mathcal{U}_{\mathrm{os}}$  的边界）；

- 用户体验约束（如不超过某CPU降频比例）；

- 行为 - 功耗单调性不被破坏等。

# 83. 仿真驱动的迭代优化 (SQP/内点法)

采用约束非线性规划迭代（记第  $k$  次迭代参数为  $\varphi_{\mathrm{os}}^{(k)}$ ）：

# 步骤6.3.1：目标与约束评估

对给定  $\varphi_{\mathrm{os}}^{(k)}$

调用仿真核，计算

$$
T ^ {(k)} = F \Big (\varphi_ {\mathrm {o s}} ^ {(k)} \Big),
$$

并得到对应的  $\bar{P}^{(k)}$

- 检查控制轨迹  $u_{\mathrm{os}}(t) = \pi_{\varphi_{\mathrm{os}}^{(k)}}(x(t))$  是否满足  $u_{\mathrm{os}}(t) \in \mathcal{U}_{\mathrm{os}}$ , 以及功耗非负等约束。

# 步骤6.3.2：梯度近似

对每个参数分量  $i = 1, \dots, p$ ，构造扰动：

$$
\varphi_ {\mathsf {o s}} ^ {(k, + i)} = \varphi_ {\mathsf {o s}} ^ {(k)} + \delta_ {\varphi , i} e _ {i},
$$

投影到可行集  $\mathcal{F}_{\mathrm{os}}$  后仿真，得到

$$
T ^ {(k, + i)} = F \Big (\varphi_ {\mathrm {o s}} ^ {(k, + i)} \Big),
$$

进而用有限差分近似梯度：

$$
\frac {\partial F}{\partial \varphi_ {\mathrm {o s} , i}} \approx \frac {T ^ {(k , + i)} - T ^ {(k)}}{\delta_ {\varphi , i}}.
$$

# 步骤6.3.3：求解子问题并更新参数

将当前梯度与约束线性化或二次近似，构造 SQP / 内点法子问题，得到搜索方向  $d^{(k)}$  与步长  $\alpha^{(k)}$ ，更新：

$$
\varphi_ {\mathrm {o s}} ^ {(k + 1)} = \varphi_ {\mathrm {o s}} ^ {(k)} + \alpha^ {(k)} d ^ {(k)},
$$

并投影到  $\mathcal{F}_{\mathrm{os}}$  以保持可行性。

# 步骤6.3.4：收敛判据

若满足

$$
| T ^ {(k + 1)} - T ^ {(k)} | <   \varepsilon_ {T}, \| \nabla F (\varphi_ {\mathrm {o s}} ^ {(k + 1)}) \| <   \varepsilon_ {g}
$$

或  $k \geq K_{\max}$ , 则终止迭代, 得到近似最优参数  $\varphi_{0s}^{\star}$ , 对应策略

$$
\pi^ {\star} = \pi_ {\varphi_ {0 s} ^ {\star}},
$$

及最耗时时间

$$
T _ {\mathrm {o p t}} ^ {\mathrm {o s}} = F (\varphi_ {\mathrm {o s}} ^ {\star}).
$$

续航提升：

$$
\Delta T _ {\mathrm {o s}} = T _ {\mathrm {o p t}} ^ {\mathrm {o s}} - T _ {\mathrm {b a s e}}.
$$

# 步骤 7：用户行为与 OS 策略联合优化（可选）

步骤目的：

在允许OS与用户设置同时调整的情形下，构造联合参数向量  $\varphi = (u_{\mathrm{usr}},\varphi_{\mathrm{os}})$ ，在综合约束下最大化  $\Delta T$ ，用于构建最理想的省电策略上限。

# 84. 联合优化问题

决策变量：

$$
\varphi = \left(u _ {\mathrm {u s r}}, \varphi_ {\mathrm {o s}}\right) \in \mathcal {F}.
$$

目标函数：

$$
F (\varphi) = T \big (u _ {\mathrm {u s r}}, \pi_ {\varphi_ {\mathrm {o s}}}; \eta , d \big),
$$

或采用平均功耗近似：

$$
F (\varphi) \approx \frac {C _ {\mathrm {e f f}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} (\varphi)}.
$$

约束：

$$
u _ {\mathrm {u s r}} \in \mathcal {U} _ {\mathrm {u s r}}, \quad \pi_ {\varphi_ {\mathrm {o s}}} \in \Pi ,
$$

以及单调性与用户体验等附加约束。

# 85. 仿真与优化流程

联合优化可直接沿用步骤6的迭代结构，只是梯度向量扩展到对  $u_{\mathrm{usr}}$  和  $\varphi_{\mathrm{os}}$  的偏导，并在每次迭代中同时更新二者。所得最优  $\varphi^{\star}$  给出同时调整用户行为与OS策略的理论最优续航上限及对应的  $T_{\mathrm{opt}}$  、  $\Delta T$  。

# 步骤 8: 电池老化函数  $T(\eta)$  与归一化续航  $R(\eta)$  计算

步骤目的：

在固定策略  $(u_{\mathrm{usr}}, \pi)$  下，分析  $T$  随容量保持率  $\eta$  的变化，构建  $T(\eta)$  与  $R(\eta)$ ，为不同老化程度用户提供差异化建议。

# 86. 采样容量保持率

。选取一组容量保持率采样点：

$$
\{\eta_ {j} \} _ {j = 1} ^ {N \eta}, \quad 0 <   \eta_ {j} \leq 1.
$$

# 87. 仿真或缩放计算

两种实现方式：

# ○ 方式 A: 直接仿真

对每个  $\eta_{j}$

设置

$$
C _ {\mathrm {e f f}, j} = \eta_ {j} E _ {\max},
$$

- 固定策略  $(u_{\mathrm{usr}}, \pi)$ , 调用仿真核, 得到

$$
T (\eta_ {j}) = T \left(u _ {\mathrm {u s r}}, \pi ; \eta_ {j}, d\right).
$$

# ○ 方式 B: 平均功耗缩放近似

在  $\eta = 1$  时已得到

$$
T (1), \bar {P} (1),
$$

且根据模型假设2，功耗结构与控制－功耗关系不随  $\eta$  改变，可近似认为  $\bar{P} (\eta)\approx \bar{P} (1)$  。则

$$
T (\eta_ {j}) \approx \frac {\eta_ {j} E _ {\mathrm {m a x}} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} (1)} = \eta_ {j} T (1).
$$

# 88. 归一化续航函数

对每个  $\eta_{j}$ , 计算:

$$
R (\eta_ {j}) = \frac {T (\eta_ {j})}{T (1)}.
$$

。若采用平均功耗缩放，则有近似线性关系：

$$
R (\eta_ {j}) \approx \eta_ {j}.
$$

# 89. 电池老化下建议调整

。将之前得到的行为灵敏度  $I_{\mathrm{usr}}^{(k)}$  与  $T(\eta_j)$  结合，可针对不同  $\eta_j$  调整推荐操作的幅度和优先级，例如在  $\eta$  较低时，更倾向推荐带来较大绝对  $\Delta T$  的行为。

# 步骤 9: 跨设备耗尽时间  $T_{d}$  与缩放关系计算

步骤目的：

在统一 SOC - 功耗框架下，对一般设备  $d$  的耗尽时间进行预测，并建立与容量  $C_d$  、功耗特征  $P_d(t)$  之间的缩放规律，实现手机模型向其他便携设备的迁移。

# 90. 设备功耗轨迹与容量输入

对每个设备  $d \in \mathcal{D}$

○ 给定有效容量  $C_d$

$\circ$  给定在某一行为/策略配置下的功耗轨迹  $P_{d}(t)$ ，或其离散样本  $P_{d}(t_{n})$ 。

# 91. 能量守恒积分与  $T_{d}$  求解

○ 设初始 SOC 为  $s_{0}$ , 耗尽阈值为  $s_{\min}$ , 可用能量为

$$
E _ {d} ^ {\text {a v a i l}} = C _ {d} \left(s _ {0} - s _ {\min}\right).
$$

在时间序列上累积能量消耗:

$$
E _ {d} (t _ {n}) \approx \sum_ {i = 0} ^ {n - 1} \frac {P _ {d} (t _ {i}) + P _ {d} (t _ {i + 1})}{2} \Delta t.
$$

$\mathrm{O}$  找到最小的  $_n$  使

$$
E _ {d} (t _ {n}) \geq E _ {d} ^ {\mathrm {a v a i l}},
$$

则取

$$
T _ {d} \approx t _ {n},
$$

保证满足约束

$$
\int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t = C _ {d} \left(s _ {0} - s _ {\min }\right).
$$

# 92. 平均功耗与缩放关系

计算设备  $d$  的平均功耗：

$$
\bar {P} _ {d} = \frac {1}{T _ {d}} \int_ {0} ^ {T _ {d}} P _ {d} (t) \mathrm {d} t.
$$

验证近似：

$$
T _ {d} \approx \frac {C _ {d} (s _ {0} - s _ {\mathrm {m i n}})}{\bar {P} _ {d}}.
$$

$\mathrm{o}$  相对于参考设备  $d_{\mathrm{ref}}$  ，可得到缩放关系：

$$
\frac {T _ {d}}{T _ {d _ {\mathrm {r e f}}}} \approx \frac {C _ {d}}{C _ {d _ {\mathrm {r e f}}}} \frac {\bar {P} _ {d _ {\mathrm {r e f}}}}{\bar {P} _ {d}}.
$$

# 步骤 10: 状态- 建议映射  $\mathcal{A}$  的构建与在线使用

步骤目的：

利用前述仿真和优化结果，构建从状态  $(x, \eta, d)$  到推荐操作集合及预期续航改善区间的映射  $\mathcal{A}$ ，形成面向用户和 OS 设计者的实用建议表。

# 1. 状态空间离线采样

。在SOC- 负载- 网络活动- 温度- 老化- 设备空间上构造网格：

$$
\{x _ {i} \} _ {i = 1} ^ {N _ {x}}, \quad \{\eta_ {j} \} _ {j = 1} ^ {N _ {\eta}}, \quad \{d _ {\ell} \} _ {\ell = 1} ^ {N _ {d}}.
$$

# 2. 候选操作集合构造

在每个离线状态点  $(x_{i},\eta_{j},d_{\ell})$

- 以步骤5得到的行为优先级作为指导，从排名靠前的  $k$  中生成若干用户侧候选操作；

- 结合步骤 6/7 得到的 OS 策略优化方向，生成若干 OS 侧候选策略调整；

- 组合得到候选操作集合

$$
\mathcal {S} _ {\mathrm {c a n d}} (x _ {i}, \eta_ {j}, d _ {\ell}),
$$

控制在大小  $K_{\mathrm{cand}}$  内。

# 3. 离线仿真评估与推荐集合选取

对每个候选操作  $a \in S_{\mathrm{cand}}(x_i, \eta_j, d_\ell)$ :

。将其对应的控制配置记为

$$
(u _ {\mathrm {u s r}} ^ {(a)}, \pi^ {(a)}),
$$

并确保  $u_{\mathrm{usr}}^{(a)} \in \mathcal{U}_{\mathrm{usr}}, \pi^{(a)} \in \Pi$ 。

调用仿真核，在参数  $(\eta_j, d_\ell)$  下计算：

$$
T ^ {(a)} (x _ {i}, \eta_ {j}, d _ {\ell}) = T \Bigl (u _ {\mathrm {u s r}} ^ {(a)}, \pi^ {(a)}; \eta_ {j}, d _ {\ell} \Bigr),
$$

相应的基线耗尽时间为:

$$
T _ {\text {b a s e}} \left(x _ {i}, \eta_ {j}, d _ {\ell}\right) = T \left(u _ {\text {u s r}} ^ {0}, \pi^ {0}; \eta_ {j}, d _ {\ell}\right).
$$

计算预期续航改善：

$$
\Delta T ^ {(a)} (x _ {i}, \eta_ {j}, d _ {\ell}) = T ^ {(a)} (x _ {i}, \eta_ {j}, d _ {\ell}) - T _ {\mathrm {b a s e}} (x _ {i}, \eta_ {j}, d _ {\ell}).
$$

在  $\mathcal{S}_{\mathrm{cand}}$  内选取若干具有最大  $\Delta T^{(a)}$  且满足附加约束（如改动幅度不超过用户可接受范围）的操作，组成推荐集合：

$$
\mathcal {S} _ {\mathrm {r e c}} (x _ {i}, \eta_ {j}, d _ {\ell}) \subseteq \mathcal {S} _ {\mathrm {c a n d}} (x _ {i}, \eta_ {j}, d _ {\ell}).
$$

。以推荐集合中的  $\Delta T^{(a)}$  范围构造改善区间：

$$
\Delta T _ {\min } (x _ {i}, \eta_ {j}, d _ {\ell}) = \min  _ {a \in \mathcal {S} _ {\mathrm {r e c}}} \Delta T ^ {(a)} (x _ {i}, \eta_ {j}, d _ {\ell}),
$$

$$
\Delta T _ {\max } (x _ {i}, \eta_ {j}, d _ {\ell}) = \max  _ {a \in \mathcal {S} _ {\mathrm {r e c}}} \Delta T ^ {(a)} (x _ {i}, \eta_ {j}, d _ {\ell}).
$$

定义映射值:

$$
\mathcal {A} (x _ {i}, \eta_ {j}, d _ {\ell}) = \left(\mathcal {S} _ {\mathrm {r e c}} (x _ {i}, \eta_ {j}, d _ {\ell}), [ \Delta T _ {\mathrm {m i n}} (x _ {i}, \eta_ {j}, d _ {\ell}), \Delta T _ {\mathrm {m a x}} (x _ {i}, \eta_ {j}, d _ {\ell}) ]\right),
$$

满足模型中对  $\mathcal{A}$  的可行性约束。

# 4. 在线阶段使用

○ 实时测量当前状态  $(x(t),\eta ,d)$

。在离线网格上找到最近的状态点集合，或对多个邻近点的  $\mathcal{A}$  做插值；

输出对应的推荐操作集合和预期续航改善区间，作为面向终端用户或

OS 策略模块的直接决策依据。

# 2.3 结果生成

根据上述求解流程，最终可得到与【问题输出】相对应的结果形式如下：

# 1. 各用户行为的续航影响量化结果

对每个行为类别  $k \in \mathcal{K}$ , 输出:

基线耗尽时间  $T_{\mathrm{base}}$

在行为调整  $u_{\mathrm{usr}}^{(k,\mathrm{opt})}$  下的耗尽时间  $T_{\mathrm{opt}}^{(k)}$

绝对改善量

$$
\Delta T ^ {(k)} = T _ {\mathrm {o p t}} ^ {(k)} - T _ {\mathrm {b a s e}},
$$

相对改善比例

$$
\frac {\Delta T ^ {(k)}}{T _ {\mathrm {b a s e}}},
$$

归一化灵敏度指标  $I_{\mathrm{usr}}^{(k)}$ 。

○ 物理含义：衡量在给定初始SOC、老化程度和使用场景下，调整单一用户行为所能带来的续航延长效果。

# 2. 用户行为优先级排序

输出按  $I_{\mathrm{usr}}^{(k)}$  （及必要时  $\Delta T^{(k)}$  ）降序排列的行为列表：

$$
k _ {(1)}, k _ {(2)}, \dots , k _ {(| \mathcal {K} |)},
$$

以及对应的定量指标  $\left(I_{\mathrm{usr}}^{(k_{(j)})}, \Delta T^{(k_{(j)})}\right)$ 。

○ 物理含义：反映在当前条件下，哪些行为（如降低亮度、关闭后台任务、切换网络模式、关闭 GPS 等）对延长耗尽时间的贡献最大，从而形成“最值得优先调整的操作”列表。

# 3. 操作系统节能策略  $\pi$  的设计方案

输出OS策略最优参数  $\varphi_{\mathrm{os}}^{\star}$  与对应策略函数：

$$
\pi^ {\star} = \pi_ {\varphi_ {0 s} ^ {\star}},
$$

以及代表性场景下的：

优化前耗尽时间  $T_{\mathrm{base}}$

优化后耗尽时间  $T_{\mathrm{opt}}^{\mathrm{os}}$

续航提升

$$
\Delta T _ {\mathrm {o s}} = T _ {\mathrm {o p t}} ^ {\mathrm {o s}} - T _ {\mathrm {b a s e}},
$$

及相对提升  $\Delta T_{\mathrm{os}} / T_{\mathrm{base}}$  。

• 物理含义: 给出在不同状态  $x(t)$  下, OS 自动调节 CPU、网络、后台任务等策略的规则形式, 以及这些规则能带来的续航改进程度。

# 4. 电池老化对续航及建议的影响规律

输出在采样点  $\eta_{j}$  下的:

- 耗尽时间函数值  $T(\eta_{j})$ ;

归一化续航

$$
R (\eta_ {j}) = \frac {T (\eta_ {j})}{T (1)}.
$$

$\circ$  并可根据  $T(\eta_j)$  与行为灵敏度  $I_{\mathrm{usr}}^{(k)}$  ，给出不同  $\eta_j$  下推荐操作的调整幅度与优先级变化。

物理含义: 刻画老化导致的有效容量下降如何影响整体续航及各行为的边际收益, 为不同电池健康状态的用户提供差异化省电建议依据。

# 5. 跨设备推广关系

。对每个设备  $d \in \mathcal{D}$ , 输出:

耗尽时间  $T_{d}$

平均功耗  $\bar{P}_d$

与参考设备  $d_{\mathrm{ref}}$  的缩放关系：

$$
\frac {T _ {d}}{T _ {d _ {\mathrm {r e f}}}} \approx \frac {C _ {d}}{C _ {d _ {\mathrm {r e f}}}} \frac {\bar {P} _ {d _ {\mathrm {r e f}}}}{\bar {P} _ {d}}.
$$

○ 物理/几何含义：在统一 SOC - 功耗模型下，说明如何根据设备容量和功耗特征，将在智能手机上得到的行为与策略建议按比例迁移到其他便携设备（如平板、可穿戴设备等）。

# 6. 模型驱动的实用建议映射表

。通过映射

$$
\mathcal {A} (x, \eta , d) = (\mathcal {S} _ {\mathrm {r e c}} (x, \eta , d), [ \Delta T _ {\mathrm {m i n}} (x, \eta , d), \Delta T _ {\mathrm {m a x}} (x, \eta , d) ]),
$$

输出一张（或若干张）离散的建议表，其中每一行对应一个状态区间（如SOC范围、负载水平、网络活动强度、环境温度、老化程度和设备类型），并给出：

- 推荐操作集合  $S_{\mathrm{rec}}$  （如“降低亮度”“关闭部分后台任务”“切换到 Wi-Fi”“限制后台定位”等）；

对应的预期续航改善区间  $[\Delta T_{\mathrm{min}}, \Delta T_{\mathrm{max}}]$ 。

○ 物理含义：将抽象的 SOC - 功耗 - 行为模型转化为可直接用于终端用户交互界面和 OS 策略模块的“状态 - 操作 - 收益”映射，实现从模型到实用省电建议的完整闭环。