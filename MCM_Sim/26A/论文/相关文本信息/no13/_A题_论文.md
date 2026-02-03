# $ 题：智能手机电池耗电建模

摘要

智能手机电池续航能力受多种因素共同影响，其耗电行为在不同使用场景下表现出显著差异，给剩余使用时间的预测和能耗管理带来了挑战。为系统刻画这一过程，本文基于锂离子电池的物理特性，构建了一种连续时间的智能手机电池耗电数学模型，用以描述电池荷电状态（6WDWH RI &KDUJH 62&）随时间和使用行为变化的动态规律。该模型以能量守恒原理为基础，将电池放电过程表示为由设备功耗驱动的微分方程，从机理层面避免了单纯依赖经验拟合或离散回归方法的局限。

在建模过程中，本文将智能手机的总功耗分解为屏幕显示、处理器计算、网络通信以及后台任务等多个具有明确物理含义的功能模块，并通过连续时间框架功能模块，并通过连将其统一纳入62&演化方程中。为降低模型复杂度并保持可解释性，模型在短复杂度并保持可解时间尺度内假设电池有效容量和名义电压近似恒定，同时通过参数修正的方式间压近似恒定，同时通接反映电池老化与环境温度对放电行为的影响。相关参数通过实验测量数据与公为的影响。相关参数通过实验开规格信息进行标定，从而保证模型在实际应用中的合理性。模型在实际应用中模型在实际应用 的合理性。

基于所建立的模型，本文对不同初始电量和典型使用场景下的电量耗尽时间本文对不同初始电量和典型使用场景（7LPHWR(PSW\ 77(）进行了预测与分析。结果表明，在待机场景下，62& 随7(）进行了预测与分析。结果表明，在析。结果表明时间变化近似呈线性关系，而在视频播放等持续高负载场景中，62& 下降速率呈线性关系，而在视线性关系， 频播放等持续高负播放等持续高显著加快，模型能够较好地重现实测数据的变化趋势。通过数值模拟与有限差分模型能够较好地重现实测数据的变化趋实测数据的变方法求解模型，在多种复合使用场景下，预测得到的 77( 与实际观测结果保持解模型，在多种复 模型，在多种 合使用场景下，预测 用场景下，较高一致性。高一致性。

进一步的灵敏度分析显示，电池有效容量（包括由老化和温度引起的修正）进一步的灵敏度分析显示，敏度分析显是影响续航时间的最关键参数之一；在亮屏使用场景中，屏幕亮度对77(具有是影响续航时间的最关键参近似线性的影响，而在待机场景下其影响几乎可以忽略。相比之下，网络功耗的似线性的影响，而在待的影响，而在瞬时波动对整体62&演化的影响有限，其决定性因素在于长期平均负载水平而波动对整体 62非短时振荡。振荡。

在模型分析的基础上，本文将定量结果转化为对用户行为和操作系统能耗管理策略的实际建议。研究表明，减少持续高负载应用、在亮屏使用时合理降低屏幕亮度以及优化后台任务调度，是延长续航时间的有效手段。同时，该连续时间建模框架具有良好的通用性，通过调整功耗结构和电池参数，可推广应用于平板电脑、可穿戴设备等其他便携式电子系统的能耗分析与续航评估。总体而言，本文提出的模型在保持结构简洁的同时兼顾了预测能力与物理可解释性，为理解智能手机电池耗电机制及制定合理的节能策略提供了一种系统化的数学分析工具。

关键词：手机 电池 有限差分法

# 目录

# 1.问题重述. 3

1.1 问题背景 . 3

1.2 问题提出 3

# 2 模型假设及关键性符号说明. 4

2.1 模型假设. 4

2.2 关键符号说明..

# 3.建模与求解.. 6

 连续时间模型.

3.2 耗尽时间（Time-to-Empty）预测 ................................................. . 12

3.3 灵敏度与假设. ...... . 15

3.4. 建议 .. 19

3.4.1 面向用户的续航优化建议.的续航优化建议 . 19

3.4.2 面向操作系统的能耗管理策略建议向操作系统的能耗管 向操作系统的能耗 理策略建议 . 20

3.4.3 电池老化与温度影响的应对建议.3 电池老化与温度影响的应对建议 .. 20

# 4. 模型的优点、局限性与推广性...模型的优点、局限性的优点、局限性与推广性...... 21

4.1 模型的优点.模型的优 点. . 21

4.2 模型的缺点 ....模 型的缺点 ........ . 21

4.3 模型的推广与扩展.3 模型的推广与扩 . 21

# 5.总结（Conclusion）（Conclus Con .22

# 6.执行摘要（Executive Summary）要 .23

7.引用. 24

8.附录 .. 24

# 1.问题重述

# 1.1 问题背景

随着智能手机在日常生活中的高度普及，电池续航能力已成为影响用户体验的核心因素之一。尽管电池技术不断进步，用户在实际使用中仍常常感受到续航时间的不稳定性：在某些情况下，设备可以支撑一整天的使用，而在另一些情况下，即便电量充足，电池也可能在短时间内迅速耗尽。这种差异并不能简单地用³使用频繁´或³使用强度大´来解释。

智能手机的电量消耗受到多种因素的共同影响，包括屏幕亮度、处理器负载、网络连接方式、后台应用活动以及定位服务等。同时，环境因素（如温度变化）环境因素（如温环境因素（如和电池自身状态（如老化程度和历史充放电行为）也会改变电池的有效容量与放也会改变电池的有会改变电池的电特性。上述因素之间并非独立作用，而是通过复杂的动态过程共同决定电池电过复杂的动态过程量随时间的变化。

在实际应用中，用户和操作系统往往依赖经验性规则或简单的统计方法来预系统往往依赖经验性往往依赖经验测剩余续航时间，这类方法通常缺乏物理或机理层面的解释能力，难以在不同使通常缺乏物理或机理常缺乏物理或机 层面的解释能力，难面的解释能用场景下保持一致的预测精度。因此，构建一个能够反映智能手机电池真实放电测精度。因此，构建一个能够反映智能手能够反映智能机理的数学模型，对于理解电池耗电行为、预测剩余使用时间以及制定合理的省于理解电池耗电行为、预测剩余使用时、预测剩余使用电策略具有重要意义。意义。

# 1.2 问题提出1 .2 问 提出

基于上述背景，本问题要求建立一个连续时间的智能手机电池放电模型，用基于上述背景，本问题述背景，本以描述电池荷电状态（6WDWHRI&KDUJH 62&）随时间的演化过程。该模型应以锂述电池荷电状态离子电池为研究对象，在保证物理合理性的前提下，将不同使用行为（如屏幕使电池为研究用、计算负载、网络活动及后台任务等）对功耗的影响纳入统一的数学框架中。算负载

在模型构建完成后，需要利用该模型对不同初始电量和使用场景下的电量耗尽时间（7LPHWR(PSW\）进行预测，并分析导致电池快速消耗的关键驱动因素。同时，应通过改变模型参数和假设条件，对模型的敏感性和鲁棒性进行检验，以评估预测结果对使用模式变化和参数不确定性的依赖程度。

最后，问题要求将模型分析得到的结论转化为可操作的实际建议，既包括对普通手机用户的使用行为指导，也包括对操作系统层面电源管理策略的启示。此外，还需讨论电池老化对有效容量的影响，以及所提出建模框架在其他便携式电子设备中的潜在推广价值。

# 2 模型假设及关键性符号说明

# 2.1 模型假设

为在保证物理合理性的同时控制模型复杂度，本文在构建智能手机电池连续时间放电模型时，作出如下假设：

# 假设 ：电池类型与放电过程连续性

智能手机采用锂离子电池，其放电过程在研究时间尺度上可视为连续过程。电池荷电状态（62&）随时间平滑变化，可用连续时间微分方程进行描述，而非离散时间或经验性曲线拟合。

# 假设 ：有效容量恒定（短时间尺度内）

在单次使用周期内（如数小时至一天），电池的有效容量变化可以忽略不计。因的有效容量变化可此，在不显式讨论电池老化的情形下，假设电池的有效容量为常数；电池老化的设电池的有效容量影响在后续分析中通过参数调整单独讨论。讨论。

# 假设 ：功耗可分解为若干独立贡献项独立贡献

智能手机的总功耗可分解为多个功能模块的功耗叠加，包括但不限于屏幕显示、处理器计算、网络通信以及后台任务。各功耗项在连续时间模型中以功率或等效信以及后台任务。各功耗项在连续时间耗项在连续时电流的形式表示，并通过加和方式共同影响 62& 的变化率。，并通过加和方式并通过加 共同影响 的变

# 假设 ：名义电压近似恒定名

在中等荷电状态范围内，锂离子电池的端电压变化相对缓慢。为简化模型，本文锂离子电池的端假设电池工作电压在研究过程中近似为常数，用名义电压表征电能与电量之间的假设电池工作电压假设电池工作 在研究过程中近似为转换关系。

# 假设 ：使用行为在短时间片内保持稳定设 使用

用户使用行为（如屏幕亮度水平、是否播放视频、网络连接状态等）在短时间片使用行为（如屏内保持不变，并可用分段常数函数或缓慢变化函数描述。这一假设允许模型刻画持不变，并可³场景切换´对电池放电速率的影响。换 对

# 假设 ：环境与热效应的间接建模

环境温度及电池热效应对放电效率的影响不在主模型中显式建模，而是通过调整有效容量或等效功耗参数进行间接反映，从而避免引入额外的热动力学方程。

# 2.2 关键符号说明

为便于后续模型推导与结果分析，本文中使用的主要符号定义如下：

<table><tr><td>符号</td><td>含义</td><td>单位</td></tr><tr><td>t</td><td>时间变量</td><td>s</td></tr><tr><td>SOC(t)</td><td>电池在时刻t的荷电状态(State of Charge)</td><td>无量纲(0-1)</td></tr><tr><td>SOC0</td><td>初始荷电状态</td><td>无量纲</td></tr><tr><td>Qeff</td><td>电池有效容量</td><td>Ah</td></tr><tr><td>Vnom</td><td>电池名义工作电压</td><td>V</td></tr><tr><td>P(t)</td><td>智能手机在时刻t的总功耗</td><td>W</td></tr><tr><td>Pscr(t)</td><td>屏幕显示功耗</td><td>W</td></tr><tr><td>Pcpu(t)</td><td>处理器计算功耗</td><td>W</td></tr><tr><td>Pnet(t)</td><td>网络通信功耗</td><td>W</td></tr><tr><td>Pbg(t)</td><td>后台任务及系统维持功耗</td><td>W</td></tr><tr><td>I(t)</td><td>电池放电等效电流</td><td>A</td></tr><tr><td>Tempty</td><td>电池电量耗尽时间(Time-to-Empty)</td><td>S</td></tr></table>

# 3.建模与求解

#  连续时间模型

首先我们要先构建核心方程

第一小问的核心方程是从电池物理机理出发，建立一个连续时间的 62& 动力学模型：

将电池荷电状态 62& 视为随时间变化的连续变量，由 62& 定义：

$$
S O C (t) = \frac {Q (t)}{Q _ {\mathrm {e f f}} (t)}
$$

根据电荷守恒原理，

$$
\frac {d Q (t)}{d t} = - I (t)
$$

在这里我们可以引入电功率定义

$$
P (t) = V (t) I (t)
$$

将以上三个进行联立带入，就可以得到

$$
\frac {d S O C (t)}{d t} = - \frac {P (t)}{V _ {\mathrm {n o m}} Q _ {\mathrm {e f f}}}
$$

当然，这里是简化的写法，即认为 这两个量都为常数4法，即认为如果要进一步展开可以写成这样如果要进一步展如果要进一步 开可以写成这样开可以写

$$
\frac {d S O C}{d t} = - \frac {P _ {\mathrm {t o t}} (t)}{V _ {\mathrm {o c}} (S O C) Q _ {\mathrm {e f f}} (T , \mathrm {a g e})}
$$

开路电压 9RF62&：不必复杂，可用线性分段线性近似

$$
V _ {\mathrm {o c}} (S O C) = v _ {0} + v _ {1} S O C
$$

有效容量：用温度 $+$ 老化缩放

$$
Q _ {\text {e f f}} (T, \text {a g e}) = Q _ {0} \cdot \phi_ {T} (T) \cdot \phi_ {\text {a g e}} (\text {a g e})
$$

当然这些是为了进一步详细讨论而展开的，目前验证计算的时候我们只保留

$$
\frac {d S O C (t)}{d t} = - \frac {P (t)}{V _ {\mathrm {n o m}} Q _ {\mathrm {e f f}}}
$$

其中功率同样可以进行展开

$$
P _ {\text {t o t}} (t) = P _ {0} + P _ {\text {s c r}} (b (t), u _ {\text {o n}} (t)) + P _ {\text {c p u}} (\ell (t)) + P _ {\text {n e t}} (R (t), s (t)) + P _ {\text {g p s}} (u _ {\text {g p s}} (t)) + P _ {\text {b g}} (\lambda (t), \tau)
$$

具体带入这些参数表达式如下

$$
P _ {\text {s c r e e n}} (t) = u _ {\text {o n}} (t) \left(\alpha_ {0} + \alpha_ {1} b (t)\right)
$$

$$
P _ {\mathrm {c p u}} (t) = \beta_ {0} + \beta_ {1} l (t) ^ {\gamma}
$$

$$
P _ {\mathrm {n e t}} (t) = P _ {\mathrm {i d l e}} ^ {(m)} + \eta^ {(m)} R (t)
$$

$$
P _ {\mathrm {g p s}} (t) = u _ {\mathrm {g p s}} (t) \left(\delta_ {0} + \delta_ {1} f _ {\mathrm {l o c}} (t)\right)
$$

$$
P _ {\mathrm {b g}} (t) = P _ {\mathrm {b g , a c t}} u _ {\mathrm {b g}} (t)
$$

为方便验证，这里我们以最简单模型入手，即不进行其他工作只进行常规消耗，3不进行其他工作只 不进行其他工即

$$
P _ {\mathrm {t o t}} (t) = P _ {0}
$$

$$
\frac {d S O C}{d t} = - \frac {P _ {0}}{V _ {o c} Q _ {e f f}}
$$

这个时候，G4等于一个常数，那么 4（W）是一次函数

这里我们关掉了手机所有应用，并断开了网络，采集了手机的剩余电量和对应的这里我们关 ：掉了手机所有应用了手机所有应时间，为了防止时间，为了防止 $100 \%$ 电量的过充能，我们选择了电量 $80 \%$ 电量开始，采集数据，使用工具为安装 $QGURLG 6'.  DGE，采集 K 如下具为安装 $QGURL

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/5979c61e8e9eec61da986cf9b105819f4b7be1de1c3aac39c52a391c64d27a1b.jpg)


可以看到近似是一条直线，与我们预测的基本一致，将其还原为以秒为单位，对8预测的基本一致， 预测的基本一致其进行拟合求参数，合求参数，

即

$$
\frac {d S O C}{d t} = - \frac {P _ {0}}{V _ {o c} Q _ {e f f}} = k
$$

读出

$$
\mathrm {V n o m} = 3. 8 5 (\mathrm {V})
$$

$$
\mathrm {Q e f f A h} = 4. 5 (\mathrm {A h})
$$

可得到

$$
P _ {0} = - 0. 8 2
$$

带回模拟并计算偏差可以看到

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/97dab18440053732409773f7ecc2d9abbee32f7ac0bc9e8dce843420b9a79a05.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/bf84c72a54ead52d4d1a3b34a3082f0b4a671d5c098509bef84968ae334f3e98.jpg)



误差呈现波动的趋势



说明我们整体吻合，但是忽略了一些微扰，这些扰动约在千分之左右，基本上可以接受


证明基础模型无误后我们打开了视频播放软件，进行测试此时的功率可以简化为

$$
P (t) = P _ {\text {b a s e}} + P _ {\text {s c r e e n}} (t) + P _ {\text {c p u}} (t) + P _ {\text {n e t}} (t)
$$

这里我们同样采用先写出方程再根据数据近似解出参数的方法

$$
P _ {\text {s c r e e n}} (t) = u _ {\text {o n}} (t) \cdot (\alpha_ {0} + \alpha_ {1} b (t))
$$

$$
b (t) = b _ {0} \cdot u _ {\text {v i d e o}} (t)
$$

$$
l (t) = l _ {0} \cdot u _ {\text {v i d e o}} (t)
$$

$$
P _ {\mathrm {c p u}} (t) = \beta_ {0} + \beta_ {1} \cdot (l (t)) ^ {\gamma}
$$

$$
P _ {\mathrm {n e t}} (t) = P _ {\mathrm {n e t , i d l e}} + \eta R (t)
$$

解得参数，进行逆向模拟如图

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/424d378d1641d79797412d3f9885254e37a506f2caac0a7242e3f9fa136349b4.jpg)


# 睿森科研简介

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/e97d168cc8699917a100f8e992b4260c4848970ded54a97f50bc60bd3846f33b.jpg)


# 关于我们

睿森科研深耕论文辅导领域5年为广大学子提供专业化、个性化的论文咨询服务

坚持初心，砥砺前行

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/d4793a47442262bc1ea7f4beecacb4fc7b4f43c280ec717978bef606cec013a0.jpg)


国内学术能力提升领导品牌，师资雄厚

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/e948db7bbbfa80d4c5137a89687cdf6f058f77f2a569d834f2b0b07b207de531.jpg)


# 业务内容

科研论文、本硕博毕业论文辅导各类大学生竞赛辅导

科研论文，毕业论文辅导

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/04f9f2fc184cc017683a188643a4cc84a2bd6c82e67b432d57925a4232149c80.jpg)


大学生竞赛辅导

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/0551ae7f4b6fd663dea6dbef83f57db3eb4e7cdc721050144ccd791e234b5e46.jpg)


了解更多内容，请扫码咨询科研助理

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/115fb29ff24bef364511cce08204df6ce4e727de722b4e6bf1da4e6778550d18.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/4754d9841ba1f1b3cb265f7fac355c267d1adf205eb4d0973c43a827eceb5f95.jpg)


以下是解的的网络信号波动，符合视频加载时候的网络情况频加载时候的网络情 加载时候的网

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/53693bc683befa890d707133e3de4ba94e4b15e371baa3257498278d99228ad7.jpg)


其功率如下

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/d3fb208e3401cdd2631684a90e02b4d068130819eea3d3ca16e35e6259248dd2.jpg)



可以看到功率基本稳定，并且有因为网络有波动而出现的波动稳定，并且有因为 1 网络有波动而出现的 络有波动而出


# 3.2 耗尽时间（Time-to-Empty）预测耗 尽时 35m e-

第二小问的思路是在已建立的连续 62& 动力学模型基础上，将具体使用场景转第二小问的思路第二小问的思 是在已建立的连续是在已建化为随时间变化的功耗函数 3W，通过积分或数值求解微分方程得到 62& 随时化为随时间 ：变化的功耗函数 3间的演化，并确定 62& 首次降为零的时刻，从而得到耗尽时间（7LPHWR(PSW\）。间的演化 群，并确定 首其主要的思路为用有限分差法来进行模型演算要的思路为用有限

在上一问中我们得到了这个方程q一问中我们得

$$
\frac {d S O C (t)}{d t} = - \frac {P (t)}{V _ {\mathrm {n o m}} Q _ {\mathrm {e f f}}}
$$

由于在较复杂的情况下，62&W 没有解析解，所以要用到有限差分法首先对时间进行离散

$$
t _ {n} = n \Delta t
$$

62& 离散：

$$
S O C _ {n} = S O C (t _ {n})
$$

导数近似：

$$
\left. \frac {d S O C}{d t} \right| _ {t = t _ {n}} \approx \frac {S O C _ {n + 1} - S O C _ {n}}{\Delta t}
$$

带入62&的表达式即有

$$
S O C _ {n + 1} = S O C _ {n} - \frac {P _ {n} \Delta t}{d e n}
$$

我们即可以进行递推了

通过设定不同场景（如待机、视频、游戏、导航等）下的典型功耗结构，比较各场景对应的 77( 差异，并与实际测评数据或合理经验进行对照，评估模型的预验进行对照，评估 进行对照，评测偏差

那么我们不妨先计算之前的看视频时候的关机时间，经过分差法模拟，得到从的关机时间，经过的关机时间，$60 \%$ 电到关机时间为  分钟左右

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/963985cdade9625ed47c4c763895925bed967fa547132a30cde9ed4e9c15b6d2.jpg)


而拟合结果同样为  分钟

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/ec7258e96045f7e4900b675bb67e47d5ce5567f5108f1c0121014fe3b9497cac.jpg)


这说明我们有很强的一致性，预测十分精准

同样的，我们还模拟了更加复杂的情况，并且也更贴近生活：手机一开始正常防止，拿起来刷一个小时视频，再放下，直到自然关机再放下，直到自然关放下，直到自然 机

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/29f92c4a0d90765735ad599d3008b06dd5a6780bed23ffd624f757551c25f9dd.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/89339d2274c455ef3a888b0a2cfcac521d66e897b8f182272802bcbfe6e75d27.jpg)


误差在千分之三左右，虽然说由于网速震荡部分很难完全一致，但是只要频率相同，那么相位的影响是很有限的，最后模拟的结果来看，我们的结果只比真实结很有限的，最后模 拟的结果来看，我们 的结果来看，果慢了一分钟。我们发现如果要看视频的话，实际上对手机影响时间非常大，远们发现如果要看视频的话，实际上对手的话，实际上对高于待机状态，而对于网络连接使用的来说，虽然不同的相位网络高峰等等会有而对于网络连接使 而对于网络 用的来说，虽然不 的来说，虽然一部分影响，但是实际上反映到用电量上反而比较小响，但是实际上反 到用电量上反而比 用电量上反而

# 3.3 灵敏度与假设灵敏

灵敏度分析是在已经能算出 62&W 和 77( 的基础上，系统研究³模型假设参数使用模式的不确定性´会怎样影响 77( 与 62& 轨迹，并据此评估模型稳健性、找出最敏感的因素、说明哪些假设会导致预测偏差最大。它本质上是一个³敏感性分析 $^ +$ 假设检验（模型结构不确定性）´的任务。

灵敏度验证实际上就是把一部分参数变成变量然后去分析，例如做以下变化

$$
\frac {d S O C}{d t} = - \frac {P (t ; \theta , u)}{V (S O C) Q _ {\mathrm {e f f}} (T , a g e)}
$$

对每个关键参数做 $\div 1 0 \%$  $\pm 2 0 \% \ '$ 扰动，重新计算 77(，然后就可以得到灵敏度如下：

$$
S _ {\theta} = \frac {T T E (\theta (1 + \epsilon)) - T T E (\theta)}{T T E (\theta)} / \epsilon
$$

基于第 和第 小问的模型，我们可以直接调整参数来进行模拟参考第一问中的分析有

$$
\frac {d S O C (t)}{d t} = - \frac {P (t)}{V _ {\mathrm {n o m}} Q _ {\mathrm {e f f}}}
$$

可以看到 是一个十分值得探讨的量，他与电池本身性质有关，也与外部环境有关

在这里我们令其上下浮动 $40 \%$ ，放到第二问中的复合模型中进行分析，结果如下模型中进行分析， 型中进行分析

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/de75af0ab37a4ce10a35f995b1abd5d93c49456676e7ebf217994b4e4207515b.jpg)


单从时间角度来看，变化是比较线性的，只有单从时 群间角度来看，变化是 $- 4 0 \%$ 处的地方有比较显著的斜率变化

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/6f6277e139394ca1ce5bc41d6e07d0fda2422b0c7e3a16062ef246c21ce307b8.jpg)


# 大学生创新创业大赛

# 精品辅导

互联网+|挑战杯|创青春|三创赛等

# 我们的优势

·强大的师资力量

·多对一全程服务

·辅导前试听机制

·无限次在线答疑

·定制化课程内容

·学员奖学金激励

# 课程内容

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/37662919d21daa239e2fdd70a4516e35d29ab1312262590cb41d19c6814da1aa.jpg)


# 项目诊断

根据不同的项目，结合各方面背景，提供项目改进意见和项目方向规划。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/b440e2ff4943735268d7759d713c60c6adea1bce8abb4476ab4e315e1e629126.jpg)


# 参赛规划

依据学校、专业以及项目特点，制定参赛路线。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/6c14f19bdee40b860f6cf6f3b26c24ddb5bdb149b127b8a79db3e86caa502a56.jpg)


# 商业计划书修改

提供针对性的书写指导，并在完成后逐页提供修改意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/37bcc7ae9c7c1401d19881cb28eba74ced7577bc8ac298bb792cc164f32a654c.jpg)


# PPT指导与修改

提供针对性的制作指导，并在完成后提供逐页提供修改意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/e4aaa759b5228f154fc99a5300cbc2719ea3f742f1895a9585bf81f262d69109.jpg)


# 答辩指导与训练

对答辩进行训练，并提供针对性的指导意见。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/b7b373c7af496c102e53ae289fbd4b528216bdbe72aaa62382cf745580111df3.jpg)


# 全程无限次答疑

比赛中遇见的各个问题，在辅导期间全程免费答疑。

# 辅导成绩

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/6f85df3a9b161cf9d40c9aa9c51354696c6d4317c56add0b8c20190ed7da8b73.jpg)


互联网+省银以上10余项

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/49df9ef7ed641f8ddbc15f5d1edcf29cf55130097572387c3055dbe880b86f8b.jpg)


创青春省二以上10余项

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/86ec29b18d291e3a6704c141d0d41be9b5edc3e45a6a8f238ecfee2129a21a70.jpg)


三创赛国奖3项

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/d2c714b018448ba010b04315616213431a4193b049ce57959dc369fa347fc833.jpg)


睿森科研

# 新学期

# 科研论文新规划

试听机制

合同保障

全科覆盖

实力师资

# 雏鹰计划

·全过程辅导（到论文定稿）：

高质量中文/英文期刊、EI/CPCI会议

·辅导加发表一体化（到论文发表）：

一对一：高质量中文/英文期刊、EI/CPCI会议

双人团（两篇文章）：EI会议

·时间周期：定稿2-4个月，录用1个月内，见刊2-6个月，检索1-3个月

# 卓研计划

·全过程辅导（到论文定稿）：

SCI、EI源刊、中文核心、学报

·辅导加发表一体化（到论文发表）：

一对一：SCI、EI源刊

二人小班（共同完成一篇论文）：SCI、EI源刊

三人小班（共同完成一篇论文）：SCI、EI源刊

·时间周期：定稿3-6个月，录用2-8个月，见刊0.5-2个月，检索0.5-2个月

详情请扫描二维码咨询学术顾问

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/e6f5d8e7513e5e4731307aaa4f22bb5c5809639a9fd1458a3e377a7708d58133.jpg)


# 大学生学科类竞赛

# 保奖班

# 数学/英语/物理等

# 火热招生中

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/2edf4222f47b46831eb7fe0b762df56e6b40543b88e63e6aaa0aa4c69d4ec43a.jpg)


# 我们的优势

·强大的师资力量

·辅导前试听机制

·定制化课程内容

多对一全程服务

·无限次在线答疑

·学员奖学金激励

# 课程大纲

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/043d06a5a6d1fdccd09dcdf56a67bed62bbad9e16622f8e06e413f7882bbe84a.jpg)


基础知识讲解培训

依据相关竞赛大纲，逐点讲解

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/b3475aaeecef63d4758a74e4267732cb7db760cf6f276cd8bf215c5e0883a9d9.jpg)


竞赛考点难点分析

针对竞赛难点，重点突破

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/e9d43e256cc76fc5bfaef5756b9d59aaad5d8213ce5c509510f6595b9008297b.jpg)


真题选讲点评

结合历年真题，精选例题详解

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/6cf35880f4a0315dd80030964d6b73d257eb6b623ed8003bd130b656925b0642.jpg)


全真模拟练习

竞赛全真模拟，赛后详细解析

# 大学生计算机类竞赛保奖班

# ACM/蓝桥杯等

# 国奖导师带你冲！！

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/eda4d9e6251d0d48d9fa26bb44c9e236cbde82e38598de23341d4245d20c0d86.jpg)


# 我们的优势

·强大的师资力量

·多对一全程服务

·辅导前试听机制

·无限次在线答疑

·定制化课程内容

·学员奖学金激励

# 课程设置

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/693ecb08a45951933d45b344e8f0828c6c9209b6b0d665937cc85b54fb104755.jpg)


定制学习方案

根据学员基础，定制个性化培训方案

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/fd00be18ef7e658d0f25fdf9bd2aa85048a9b4ddccfddb188b621cbd89c0b1e0.jpg)


算法及编程基础培训

根据方案，开展基础培训

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/d8746800237db860fe61263b60c2a4f5157d9559c3bd847b6f0147f9eb7eff71.jpg)


刷题特训

导师精选题目，特训练习

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/b4fbfde8fd613ce45ce57996caa384e30096d3ebaa157458185002dca3879b8f.jpg)


全真模拟练习

竞赛限时全真模拟，体验竞赛氛围

# 课程亮点

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/90da1eb5532a0d6fb1c629b382640f66fa29acf72c3c4db43224aa4b933fdc29.jpg)


大牛授课干货十足

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/7546decbe0272cbdee979b5b86caca0cc637bc08fd4e7c485718c5c3e9ef02a1.jpg)


全程伴学无限答疑

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/de02b0d18bd0b61c1f1e39b78680d22ad3349b664e551c3f5546eccab5ab09be.jpg)


绝密押题赛前助力

扫码立即报名>>>>>>

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/f873144a11e22bf3adf614a4575113d7fc3fbbba636847e32828c465bb93d069.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/0f50fb1286b5fa8f79a8cfe204eff90a72be65f81e1db3712e2a38a518b4f7d4.jpg)


放在灵敏性这里，我们发现 $. 4 0 \%$ 这个地方的变化更加明显与其他地方显著不同，与其绘制具体的62& 曲线后，我们发现了原因，当电容太小的时候，在看视频这个了原因，当电容太了原因，当电容 小的时候，阶段就耗尽了电量，导致少了一个极端，故出现了明显的变化。一个极端，故出现了个极端，故出现 明显的变化。

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/9f5f3872f811e8206f98f8c7473e85db58f73d51e5f838619b37b2bcb6fc767a.jpg)


整体而言，电容实际上对时间有非常大的影响。

屏幕亮度也是一个可以考虑的影响因素，这是众多参数中少数对于我们使用者而言可以轻松调节的参数

调节亮度，对77(的影响如下，是十分平均的

![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/d7c69e92bfb1cd80763b2c046cb129e208fda8e1169faded683f729fcb35f61e.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-02-01/49cf317f-abdb-4a79-9e00-a9cd312529f4/78455ed7e68c1f3e735bd785c10b21f857f322629ff4c32b2197e9d60d17c4e4.jpg)



具体到曲线来看，亮度对待机段没有影响，这与我们的生活常识是一致的


# 3.4. 建议

基于前述连续时间电池耗电模型、参数标定结果以及灵敏度分析结论，本节将模型发现转化为可执行的用户层面与系统层面建议，并进一步讨论电池老化情形及模型的推广潜力。

# 3.4.1 面向用户的续航优化建议

模型表明，电池荷电状态的下降速率与总功耗 3WRWW成正比。因此，最有效的用户行为调整应聚焦于降低长期平均功耗，而非短时功耗波动。

# （）优先减少持续高负载使用场景

建议用户尽量减少长时间的视频播放、游戏或高强度多媒体应用，或通过降低视频分辨率、帧率等方式减小负载强度。模型仿真结果显示，在视频场景下，模型仿真结果显处理器与网络功耗长期维持在高水平，是导致剩余可用时间显著缩短的主要原因。是导致剩余可用时是导致剩余可

减少此类持续高负载行为可直接降低 与 的平均值，从而显著延长接降低  的平均值，从续航时间。

# （）在亮屏使用时降低屏幕亮度时

对于需要长时间亮屏操作的场景，降低屏幕亮度是一种稳定且可预测的省电需要长时间亮屏操需要长时间亮 作的场景，降低屏幕的场景，降低屏手段。模型中屏幕功耗与亮度呈近似线性关系，灵敏度分析表明，在亮屏状态下，。模型中屏幕功耗与亮度呈近似线性关亮度降低可有效延长77(；而在待机场景中，亮度对续航影响几乎可以忽略。因亮度降低可有效延长 ；而在待机场此，建议用户在保证可读性的前提下优先降低亮度，而非频繁切换其他设置。此，建议用户在保证可读性的前提保证可读

# （）避免在信号不稳定环境下进行高带宽网络活动避免在信

尽管模型结果显示网络功耗的短时波动对总体62&演化影响有限，但在信尽管模型结果号较差的环境中，高带宽任务会显著提高网络模块的平均功耗。建议用户在网络的环境条件稳定时集中完成下载、更新或流媒体任务，以降低长期平均网络负载。

# （）合理限制后台任务与定位功能

后台应用频繁唤醒处理器与网络模块，会在长期使用中累积额外功耗。建议用户限制不必要的后台刷新与自启动行为，并将定位权限调整为³仅在使用期间´或降低定位精度。该措施本质上是减少相关功耗项的启用时间比例，从而降低总功耗。

# 3.4.2 面向操作系统的能耗管理策略建议

相比用户个体行为调整，操作系统层面的统一调度策略在整体能耗控制中具有更高的潜在收益。基于模型结构，可提出以下系统级建议。

# （）基于 62&下降速率的自适应省电策略

操作系统可实时估计短时间窗口内的62&下降速率，作为功耗状态的反馈信号。当检测到电量下降过快时，系统可自动触发降低亮度、限制后台活动或推迟非关键任务。该策略直接来源于模型核心方程，具有明确的物理解释与实现可行性。

# （）后台任务的批处理与合并唤醒机制

模型结果表明，频繁的&38与网络模块唤醒会提高长期平均功耗。操作系醒会提高长期平均统可通过将零散的后台网络请求与同步任务进行批量调度，减少硬件模块的状态务进行批量调度，减切换次数，从而在不显著影响用户体验的前提下降低能耗。验的前提下降低能耗的前提下降低 。

# （）场景感知的功耗控制策略略

不同使用场景下，主导功耗来源存在显著差异。例如，在视频场景中，屏幕主导功耗来源存在 3显著差异。例如，著差异。例如与网络功耗占主导；在导航场景中，定位模块成为关键因素。操作系统可基于场导；在导航场景中，导；在导航场景中 1定位模块成为关键位模块成为关景识别结果，动态调整相应模块的功耗策略，实现更精细化的能耗管理。动态调整相应模块动态调整相应 的功耗策略，实现功耗策略，

# 3.4.3 电池老化与温度影响的应对建议4 .3 4温度影 响的

模型将电池老化与环境温度通过有效容量 引入 62&演化过程。分析结果模型 群将电池老化与环境温池老化与表明，随着电池老化或在不利温度条件下使用，即使用户行为保持不变，续航时，随着电池老化或间也会显著缩短。q会显著缩短。

因此，建议操作系统在检测到电池健康度下降或极端温度条件时，更早介入省电策略，并适当限制高功耗应用的运行。同时，向用户提供基于模型预测的续航衰减信息，有助于引导合理使用习惯。

# 4. 模型的优点、局限性与推广性

# 4.1 模型的优点

本文提出的智能手机电池放电模型基于连续时间框架，对电池荷电状态随时间的变化过程进行了明确而直观的刻画，具有较强的物理可解释性。通过将电池放电过程表示为由功耗驱动的微分方程，模型能够直接反映不同使用行为对电池消耗速率的影响，而非仅依赖经验性拟合。

本文模型采用模块化结构，将总功耗分解为屏幕显示、处理器负载、网络通信及后台任务等多个功能分量。这种结构不仅有助于识别导致电量快速下降的关键致电量快速下驱动因素，也使模型在分析不同使用场景时具有良好的灵活性和可扩展性。的灵活性和可扩展灵活性和可扩

模型参数均具有明确的物理或工程含义，可通过公开规格参数、文献数据或合通过公开规格参数理估计进行标定。这一特性使模型在缺乏大规模真实数据的情况下仍具有可操作大规模真实数据的情 模真实数据性，并能够支持灵敏度分析和不确定性讨论。相比纯数据驱动或黑箱方法，该模性讨论。相比纯数据性讨论。相比纯 驱动或型在预测结果的可解释性和稳健性方面具有明显优势。性方面具有明显优 。

# 4.2 模型的缺点点

尽管该模型在结构清晰性和可解释性方面具有优势，但仍存在一定局限性。在结构清晰性和可解 结构清晰性和 释性方面具有优势 释性方面具有

首先，为控制模型复杂度，本文在主模型中假设电池名义电压近似恒定，未显先，为控制模型复杂度，本文在主模型式刻画锂离子电池在极端荷电状态或高放电倍率下可能出现的非线性电压变化，式刻画锂离子电池在极端荷电状态或高这在高负载或低电量阶段可能引入一定误差。这在高负载或低电量阶段可能引入电量阶段

模型将环境温度、热效应及电池老化等因素通过参数调整进行间接反映，而未模型将环境温度、热效应境温度、热引入专门的热模型或寿命模型。这种简化在短时间尺度内是合理的，但在长时间专门的热模型或寿门的热模型连续使用或极端环境条件下，可能低估这些因素对电池放电行为的影响。这些变q使用或极端环化同样可以通过差分法进行表示，在后续工作中可以做进一步探讨。可以通

# 4.3 模型的推广与扩展

本文提出的建模框架具有良好的通用性，可推广应用于其他类型的便携式电子设备。例如，通过调整电池容量、电压参数及功耗分解结构，该模型可直接用于平板电脑、智能手表、可穿戴医疗设备等设备的续航分析与能耗评估。

在模型扩展方面，可进一步引入电池老化子模型，将有效容量或内阻设置为随充放电循环次数变化的动态变量，从而实现对长期使用过程中续航性能退化的预测。此外，结合温度相关参数或简化热模型，可提升模型在极端环境条件下的适用性。

从应用角度看，该模型还可作为操作系统级电源管理策略的理论基础。通过实时估计各功耗分量对 62& 变化的边际影响，系统可动态调整屏幕亮度、任务调度及网络连接策略，以在保证用户体验的前提下延长续航时间。这一扩展使模型不仅具有分析价值，也具备潜在的工程应用意义。

# 5.总结（Conclusion）

本文围绕智能手机电池续航行为，构建了一个基于连续时间的锂离子电池放电数学模型，用以刻画电池荷电状态随使用时间和使用场景变化的动态过程。模化的动型以物理和工程合理性为出发点，将智能手机的能量消耗分解为屏幕显示、处理分解为屏幕显器负载、网络通信及后台任务等多个功能模块，并通过微分方程形式统一描述其微分方程形式统一微分方程形式统对电池放电速率的影响。

在此基础上，本文利用所建立的模型对不同初始电量和典型使用场景下的电对不同初始电量和典同初始电量和量耗尽时间进行了预测与比较分析，识别了导致续航显著下降的关键使用行为，识别了导致续航显识别了导致续 著下降的并解释了不同场景下电池消耗差异的内在机理。通过灵敏度分析，进一步评估了异的内在机理。通过内在机理。 4 灵敏度分析，模型对参数变化和使用模式波动的响应特性，验证了模型在合理假设条件下的稳波动的响应特性，动的响应特性 验 1证了模型在合理假设了模型在合理定性与适用范围。

最后，本文将模型分析结果转化为对用户和系统层面的实际建议，讨论了电将模型分析结果转化将模型分析 为对用户和系统层为对用户和系统池老化对有效容量的影响，并探讨了该建模框架在其他便携式电子设备中的推广效容量的影响，并探讨了该建模框架在讨了该建模框架潜力。总体而言，本文所提出的模型在保持结构简洁的同时兼顾了预测能力与可总体而言，本文所提体而言，本文所 3出的模型在保持结的模型在保持解释性，为理解智能手机电池耗电机制及制定合理的节能策略提供了一种系统化释性，为理解智能手 4机电池耗电机制及制的分析工具。

# 6.执行摘要（Executive Summary）

本研究建立了一种连续时间的智能手机电池耗电模型，通过能量守恒原理刻画电池荷电状态（6WDWH RI &KDUJH 62&）随时间的变化规律。模型以

$$
\frac {d S O C (t)}{d t} = - \frac {P _ {\mathrm {t o t}} (t)}{V _ {\mathrm {n o m}} Q _ {\mathrm {e f f}}}
$$

为核心，其中总功耗 $P _ { \mathrm { t o t } } ( t )$ 被分解为屏幕、处理器、网络、定位与后台任务等多个可解释模块，而有效容量 则进一步考虑了温度与电池老化因素。模型参数通过实验数据进行校准，并在多种使用场景下对62&演化与剩余可用时间演化与剩余可（7LPHWR(PSW\ 77(）进行了验证。

# 主要发现如下：

（）持续高负载使用情景（如视频播放）是电量快速下降的主导因素，其通过）是电量快速下降的主显著提高处理器与网络功耗，使62&下降速率明显大于待机或轻度使用场景。&下降速率明显大于下降速率明显 待机或轻

（）屏幕亮度对续航时间具有近似线性的影响，但该影响仅在亮屏状态下显著，近似线性的影响，但似线性的影响， 4 该影响仅在亮屏在待机场景中几乎可以忽略，这与模型中屏幕功耗由³亮屏状态变量´控制的结构，这与模型中屏幕功这与模型中屏幕 1耗由高度一致。

（）灵敏度分析表明，有效容量析表明，有效容量表明，有 Qeff （包括温度与老化修正）是影响 77(的1（包括温度与老（包括温度与最敏感参数之一。这意味着即使用户行为保持不变，电池老化或极端环境温度也数之一。这意味着即 5使用户行为保持不变用户行为保持会显著缩短可用续航时间。相比之下，网络功耗的短时波动对整体62&变化的缩短可用续航时间短可用续航时 3相比之下，网络功比之下，网影响相对有限，其关键在于平均负载水平而非瞬时波动。响相对有限，其关 4键在于平均负载水平

# 基于模型结果，本研究提出以下建议：基于 ：，本

在用户层面，最有效的省电措施包括减少长时间高负载应用（如高清视频与在用 群户层面，最有效的省 面，最有游戏）、在亮屏使用时降低屏幕亮度，以及避免在信号不稳定环境下进行高带宽）、在亮屏使用时降网络活动。这些操作本质上等价于降低总功耗 q活动。这些 $P _ { \mathrm { t o t } } ( t )$ 的平均水平，从而直接延长续航时间。间

在操作系统层面，模型支持采用基于62&下降速率的自适应省电策略，通过实时监测电量变化趋势动态调整亮度、后台任务与网络调度；同时，后台任务的批处理与合并唤醒策略可有效减少 &38与无线模块的频繁状态切换，进一步降低能耗。此外，对于老化电池，系统应更早触发省电模式并加强温度管理，以补偿有效容量下降带来的续航损失。

总体而言，本研究提供了一种物理可解释、参数可校准且适用于多场景分析的电池耗电建模方法，不仅能够解释日常使用中电量消耗的差异性，也为用户行为优化和操作系统级能耗管理策略提供了定量依据。

# 7.引用



 6XQ - 7DQJ < <H - HW DO $ QRYHO FDSDFLW\ DQG LQLWLDO GLVFKDUJH HOHFWULF TXDQWLW\ HVWLPDWLRQPHWKRG IRU /L)H32 EDWWHU\ SDFN EDVHG RQ 2&9 FXUYH SDUWLDO UHFRQVWUXFWLRQ>-@ (QHUJ\  





 /LDR + +XDQJ % &XL < HW DO 5HVHDUFK RQ D IDVW GHWHFWLRQ PHWKRG RI VHOIGLVFKDUJH RIOLWKLXP EDWWHU\>-@ -RXUQDO RI (QHUJ\ 6WRUDJH   





 =HQJ / +X < /X & HW DO 3HUIRUPDQFH HYDOXDWLRQ RI OLWKLXP EDWWHU\ SDFN EDVHG RQ0$7/$% VLPXODWLRQ ZLWK OXPSHG SDUDPHWHU WKHUPDO PRGHO>-@ (QHUJ\ 6FLHQFH(QJLQHHULQJ   





 'LQJ 1 :DJQHU ' &KHQ ; HW DO &KDUDFWHUL]LQJ DQG PRGHOLQJ WKH LPSDFW RI ZLUHOHVV VLJQDODFW RI Z FWVWUHQJWK RQ VPDUWSKRQH EDWWHU\ GUDLQ>-@ $&0 6,*0(75,&6 3HUIRUPDQFH (YDOXDWLRQIRUPDQFH (YDOXD DQFH (YDO5HYLHZ   





 9LHW 9 4 7KDQJ + 0 &KRL ' - %DODQFLQJ SUHFLVLRQ DQG EDWWHU\ GUDLQ LQ DFWLYLW\ UHFRJQLWLRQQG EDWWHU\ DFWLWHU\ LQRQ PRELOH SKRQH>&@ ,((( WK ,QWHUQDWLRQDO &RQIHUHQFH RQ 3DUDOOHO DQG 'LVWULEXWHGO 3DUDO 36\VWHPV ,(((  





 2P 6 7XFNHU : ' %DWWHU\ DQG GDWD GUDLQ RI RYHUWKHWRS DSSOLFDWLRQV RQ ORZHQGDLQ DS Q RYHUWKHWRSVPDUWSKRQHV>&@ ,67$IULFD :HHN &RQIHUHQFH ,67$IULFD ,(((  3DJH  RI,6HHN , $IULFD IULFD 3DJH  RI 





 (OOLRWW - .RU $ 2PRWRVKR 2 $ (QHUJ\ FRQVXPSWLRQ LQ VPDUWSKRQHV DQ LQYHVWLJDWLRQ RIVKR FRQV QHUJ\ FRQ PSWLRQ VPDUWSKRQHV WLRQ VPDUWSKREDWWHU\ DQG HQHUJ\ FRQVXPSWLRQ RI PHGLD UHODWHG DSSOLFDWLRQV RQ DQGURLG VPDUWSKRQHV>-@PHG HODWHG RQ DWHG DSSOLFDWLRQ





 &KHQ 7 7DQJ + /LQ ; HW DO 6LOHQW %DWWHU\ 'UDLQLQJ $WWDFN DJDLQVW $QGURLG 6\VWHPV E\DO ; HQW 'UDLQLQJ W 'UDLQLQ6XEYHUWLQJ 'R]H 0RGH>&@ ,((( *OREDO &RPPXQLFDWLRQV &RQIHUHQFH */2%(&20EYHUWLQJ 0RGH> UWLQJ 0RGH  &  *ORED,(((  



# 8.附录附附录

程序 

```matlab
function P0 = estimate_P0_base_only()
clc; clear; close all;
```

$\% \ = = = = = = 1$ ) 固定文件路径 $= = = = = = = =$

```javascript
csvPath = 'E:\桌面\dg\sxjm3\第一问\数据\无其他载荷.csv';
```

$\% \% = = = = = = 2$ ) 电池参数 $= = = = = = = =$

```matlab
Vnom = 3.85; % V
```

```txt
QeffAh = 4.5; % Ah
```

```matlab
den = Vnom * QeffAh * 3600; % 62370
```

$\% \% = = = = = = 3$ ) 读数据 $= = = = = = = =$

```matlab
T = readableSample(csvPath);  
t_min = T.t_min;  
SOC = T.SOC;  
mask = isfinite(t_min) & isfinite(SOC);  
t_min = t_min mask);  
SOC = SOC(mask);
```

```matlab
\(\% \% = = = = = 4\) ）自动选连续段 \(= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   
dtm \(=\) diff(t_min);   
cut \(=\) find(abs(dtm-1)>1e-6);   
segStart \(=\) [1;cut+1];   
segEnd \(=\) [cut; numel(t_min)];   
segLen \(=\) segEnd - segStart + 1;   
[~,id] \(=\) max(segLen);   
s \(=\) segStart(id);   
e \(=\) segEnd(id);   
t_min \(=\) t_min(s:e);   
SOC \(=\) SOC(s:e);   
fprintf('Using segment:t_min from \(\% .0f\) to \(\% .0f\) (N=%d)\n',...   
t_min(1),t_min(end)，numel(t_min));
```

```matlab
\(\% \% = = = = = = 5\) ）方法A：逐分钟差分估计P0 \(= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   
dSOC \(\equiv\) SOC(1:end-1)-SOC(2:end);  
P_each \(\equiv\) den \* (dSOC/60);  
P0_med \(\equiv\) median(P_each, 'omitnan');  
P0_mean \(\equiv\) mean(P_each, 'omitnan');  
P0_std \(\equiv\) std(P_each, 'omitnan');
```

$\% \% = = = = = = 6$  ）方法B：线性回归估计P0  $= = = = = =$  t_sec  $\equiv$  t_min \*60;  
p  $\equiv$  polyfit(t_sec，SOC,1);  
b  $\equiv$  p(1)；  $\%$  dSOC/dt  
P0_reg  $\equiv$  -den \*b;

$\% \% = = = = = = 7$  ）输出结果  $= = = = = =$    
fprintf('n  $\equiv = = = =$  Estimated base-only power P0  $= = = = = \backslash n ^ { \prime }$  1   
fprintf('P0 (median)  $=$  %.4f W\n'，PO_med);   
fprintf('P0 (mean)  $=$  %.4f W (std %.4f)\n'，PO_mean，P0_std);

```matlab
fprintf('P0 (regression) = %.4f W\n', P0_reg);  
fprintf('===\n');  
P0 = P0_med;
```

$\% \% = = = = = = 8)$  SOC  $^+$  拟合线  $\equiv \equiv \equiv \equiv$    
figure;  
plot(t_min, SOC, 'LineWidth', 1.6); hold on;  
SOC_fit  $=$  polyval(p, t_sec);  
plot(t_min, SOC_fit,'--'，'LineWidth'，1.6);  
grid on;  
xlabel('Time (min)');  
ylabel('SOC');  
title('Base-only SOC and linear fit');  
legend('SOC data','Linear fit','Location','best');

%%  $= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 9)$  残差图（核心）  $= = = = = =$  residual  $=$  SOC-SOC_fit;

```matlab
figure;   
plot(t_min,residual,'LineWidth',1.6);   
grid on;   
xlabel('Time (min)');   
ylabel('Residual (SOC)');   
title('Residual of SOC after linear fit');
```


% 统计残差量级


```matlab
fprintf('\n=== Residual analysis===\n');  
fprintf('Residual mean = %.6e\n', mean(residual));  
fprintf('Residual std = %.6e\n', std(residual));  
fprintf('Max residual = %.6e\n', max(abs(residual)));  
fprintf('=== Residual analysis===\n');
```

$\% \% = = = = = = 10$  残差放大版（更容易看波动）  $= = = = = =$  figure; plot(t_min, residual \* 1e4, 'LineWidth', 1.6); grid on; xlabel('Time (min)'); ylabel('Residual  $\times 10^{\wedge}4^{\prime}$  ); title('Residual (magnified  $\times 10^{\wedge}4)^{\prime}$  );

```txt
end
```


程序 


```matlab
function tte(video_powersum_burstyNet_recordR_oneclick()
clc; clear; close all;
rng(0);
%% = Battery / Model Parameters = SOC0 = 0.60; % initial SOC (0~1)
Vnom = 3.85; % nominal battery voltage (V)
QeffAh = 4.5; % effective capacity (Ah)
%% = Time Grid = SOC0 = 1.0; % internal time step (s)
tmax = 24*3600; % max simulate time (s)
N = floor(tmax/dt) + 1;
t = (0:N-1)' * dt;
SOC = nan(N,1);
SOC(1) = SOC0;
%% = Video Window (scenario) = t(video_start = 5; % 0.5 h
t(video_end = 3.0*3600; % 3.0 h
u(video = double(t >= t(video_start & t < t(video_end); % 0/1
%% = Power Model: Pbase + Pscreen + Pcpu + Pnet = 1) Base
Pbase = 0.82; % W
% - - - - - 2) Screen -
b0 = 0.70; % 视频时平均亮度 (0~1)
b = b0 * u(video; % 非视频时段亮度=0
alpha0 = 0.80; % W
alpha1 = 2.20; % W
u_on = u(video; % 视频时亮屏
Pscreen = u_on .* (alpha0 + alpha1 .* b);
% - - - - - 3) CPU -
10 = 0.55; % 视频解码平均负载 (0~1)
l = 10 * u(video;
beta0 = 0.20; % W
beta1 = 2.50; % W
gamma = 1.60;
```

```txt
Pcpu = beta0 + beta1 .* (1.^gamma);
```

$\%$ 如果你希望“CPU只算视频相关”，用这一句替换上一句：

```matlab
% Pcpu = (beta0 * u(video) + beta1 .* (l.^gamma);
```

```txt
% ---- 4) Network (bursty streaming traffic) ----
```

$\%$ 目标：构造 $\mathsf { R } ( { \sf t } ) \in [ \Theta , 1 ]$ 的随机“突发流量”过程，并记录下来

```txt
[ R0 = 0.55; \% \text{基线吞吐强度（}0 \sim 1) ]
```

```txt
Rb = 0.35; % 突发增量（0~1）
```

```txt
p_on = 0.15; % 每秒进入突发的概率（越大越频繁）
```

```txt
p_off = 0.10; % 每秒退出突发的概率（越大越短促）
```

```txt
sigma = 0.03; % 小噪声
```

```matlab
R = zeros(size(t)); % √ 记录 R(t)
```

```txt
burst = 0; % 0/1 状态
```

for  $k = 1$  :numel(t)

```txt
if u(video(k) == 0
```

$\text{burst} = 0$

```txt
R(k) = 0;
```

```txt
continue;
```

```txt
end
```

```txt
% 两态 Markov: burst=0/1
```

if burst  $= = 0$

```txt
if rand() < p_on, burst = 1; end
```

```txt
else
```

```erlang
if rand() < p_off, burst = 0; end
```

```txt
end
```

```javascript
Rk = Rθ + burst*Rb + sigma*randn();
```

```matlab
R(k) = max(θ, min(1, Rk)); % clip to [0,1]
```

```txt
end
```

```matlab
Pnet_idle = 0.30; % W
```

```matlab
eta = 1.50; % W
```

```txt
Pnet = Pnet_idle + eta .* R;
```

```txt
% ✔ Total power
```

```txt
P = Pbase + Pscreen + Pcpu + Pnet;
```

```erlang
%% =============== Finite Difference Update==============
```

```matlab
den = Vnom * QeffAh * 3600; % (W*s) per SOC=1
```

```txt
tte = NaN;
```

```matlab
idx_empty = NaN;  
for n = 1:N-1  
dSOCdt = -P(n) / den;  
SOC(n+1) = SOC(n) + dt * dSOCdt;  
if SOC(n+1) <= 0  
frac = SOC(n) / (SOC(n) - SOC(n+1));  
tte = t(n) + frac*dt;  
idx_empty = n+1;  
SOC(n+1:end) = 0;  
break;  
end  
end  
% Truncate  
if ~isnan(idx_empty)  
t_out = t(1:idx_empty);  
SOC_out = SOC(1:idx_empty);  
P_out = P(1:idx_empty);  
Pscreen_out = Pscreen(1:idx_empty);  
Pcpu_out = Pcpu(1:idx_empty);  
Pnet_out = Pnet(1:idx_empty);  
R_out = R(1:idx_empty); % √ 截断后的 R(t)  
else  
t_out = t; SOC_out = SOC; P_out = P;  
Pscreen_out = Pcpu_out = Pcpu; Pnet_out = Pnet;  
R_out = R;  
end  
% Keep only integer minutes  
minute_mask = mod(t_out, 60) == 0;  
t分鐘 = t_out(minute_mask);  
SOC分鐘 = SOC_out(minute_mask);  
P_total_m = P_out(minute_mask);  
Pscreen_m = Pcscreen_out(minute_mask);  
Pcpu_m = Pcpu_out(minute_mask);  
Pnet_m = Pnet_out(minute_mask);  
R_m = R_out(minute_mask); % √ 整分钟 R(t)  
% Output Table (minute)  
TSOC = table(...  
t分鐘, t分鐘/60, t分鐘/3600, ...
```

# 数模美赛

# 转学术论文发表

前30名享600-2000元优惠报名即赠各类保奖班课程

# 服务内容

可转为EI会议/CPCI会议/高质量中英文期刊

·免费提供论文方向评估及指导服务

# 发表周期

·投稿后1个月左右录用

·录用后2-7个月左右见刊

·见刊后1-3个月左右检索

# 我们承诺

·收费透明，含版面费，无任何二次收费

定金制，成功录用再补齐尾款，不录用全额退款

SOC Minute, ..   
P_total_m, ...   
Pbase*ones(size(t Minute)), Pscreen_m, Pcpu_m, Pnet_m, ...   
R_m, ...   
'VariableNames',{'tsec','t_min','t_hour','SOC',..   
'P_total_W', 'P_base_W', 'PScreen_W', 'P_cpu_W', 'P_net_W', ...   
'R_net_0to1'});   
assignin('base', 'TSOC', TSOC);   
out_csv = fullfile(pwd, 'tte_soc Video_burstyNet_withR.csv');   
writetable(TSOC,out_csv);   
 $\% \% = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 14$    
fprintf('Power model:  $\mathsf{P}=$  Pbase  $^+$  Pscreen  $^+$  Pcpu  $^+$  Pnet (bursty net)\\n');   
fprintf('Video window  $=$  [%.2f,%.2f] hours\\n', t(video_start/3600,   
t(video_end/3600);   
if isnan(tte)   
fprintf('Battery not emptied within %.2f hours.\n', tmax/3600);   
else   
fprintf('TTE  $=$  %.4f hours (%.1f minutes)\n', tte/3600, tte/60);   
end   
fprintf('Saved minute-level table (with R) to: %s\n', out_csv);   
 $\% \% = = = = = = = = = = = = = = = = = = =$  Plots figure;   
plot(TSOC.t_min, TSOC.SOC, 'LineWidth', 2);   
grid on; xlabel('Time (minutes)'); ylabel('SOC');   
title('SOC(t) (sampled every minute)');   
figure;   
plot(TSOC.t_min, TSOC.P_total_W, 'LineWidth', 1.8); hold on;   
plot(TSOC.t_min, TSOC.P_base_W, '-', 'LineWidth', 1.2);   
plot(TSOC.t_min, TSOC.P.Screen_W, '-', 'LineWidth', 1.2);   
plot(TSOC.t_min, TSOC.P_cpu_W, '-', 'LineWidth', 1.2);   
plot(TSOC.t_min, TSOC.P_net_W, '-', 'LineWidth', 1.2);   
grid on; xlabel('Time (minutes)'); ylabel('Power (W)');   
legend('Total', 'Base', 'Screen', 'CPU', 'Net', 'Location', 'best');   
title('Power components (minute-sampled)');   
figure;   
plot(TSOC.t_min, TSOC.R_net_0to1,'LineWidth', 1.6);   
grid on; xlabel('Time (minutes)'); ylabel('R(t) (0~1)');

title('Network fluctuation R(t) (bursty, minute‐sampled)');

end

# 程序 

function tte_base_then_1hvideo_detailed_burstyNet_oneclick()

clc; clear; close all;

rng(2); $\%$ 固定随机性，便于复现实验

%% === === Battery / Model Parameters

$\mathsf { S 0 C } \theta \ = \ \theta . 6 \theta$ ; $\%$ initial SOC (0~1)

Vnom $= ~ 3 . 8 5$ ; $\%$ nominal battery voltage (V)

QeffAh $= ~ 4 . 5$ ; % effective capacity (Ah)

$\begin{array} { r l } { \% \% } &  { } = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = \end{array}$ Scenario Timing ===============

t_base_before = $3 0 ^ { \ast } 6 0$ ; $\% \ \%$ 先基础多久（秒）。若想“立刻看视频”，设为 0（秒）。若想 立刻看视 频

t_video_dur = ${ } ^ { 1 * 3 6 0 0 }$ ; % ✅ 视频时长 $^ { \prime = 1 }$ 小时（秒）

t_video_start $=$ t_base_before;ore;

t_video_end $=$ t_video_start_start $^ +$ t_video_dur;t_video_ t_video r;

%% == ========== Time Grid========== Time ========= T d

dt $= ~ 1 . 0$ ; % internal time step (s)time ernal ep

tmax $=$ 24*3600; % max simulate time (s)max 3mulate  te

N = floor(tmax/dt) + 1;floor(tmax/dt) r(tmax/dt

t = (0:N‐1)' * dt;(0:N * t;

SOC = nan(N,1);C = n(N,1);

SOC(1)1) $=$ SOC0;

%% ==== Video indicator ===

u_video $=$ double(t $> =$ t_video_start & t < t_video_end); % 0/1

%% == ===== Power Model ====

% ‐‐‐‐‐‐‐‐‐ Base (always on) ‐‐

Pbase = 0.82; % W

% ‐‐‐‐‐‐‐‐‐ Screen (only when video on)

$b \theta \ = \ 0 . 7 \theta$ ; $\%$ 视频时平均亮度（0~1）

$\ b \ = \ b \theta$ .* u_video; $\%$ 非视频时段亮度 ${ } = 0$

alpha0 $= ~ 8 . 8 \theta$ ; % W

alpha1 = 2.20; % W

u_on $=$ u_video; $\%$ 视频时亮屏

```txt
Pscreen = u_on .* (alpha0 + alpha1 .* b);
```

```txt
% ---- CPU
```

$\%$ 说明：你之前的写法 Pcpu $=$ beta0 $^ +$ beta1*(l^gamma)

$\%$ 这会导致“非视频时也有 beta0 的常耗”。如果你希望“CPU只算视频相关”，用下面的替代写法。

```txt
10 = 0.55; % 视频解码平均负载（0~1）
```

```txt
1 = 10 .* u(video;
```

```matlab
beta0 = 0.20; % W
```

```matlab
beta1 = 2.50; % W
```

gamma  $= 1.60$

$\%$ 版本 A：CPU 始终有 beta0（更像系统最低 CPU 开销）

```txt
Pcpu = beta0 + beta1 .* (1.^gamma);
```

$\%$ 版本 B：CPU只在视频时计入（更“视频相关”）

```matlab
% Pcpu = (beta0 .* u(video) + beta1 .* (l.^gamma);
```

```txt
% ----- Network (bursty streaming traffic) -----
```

$\%$ 构造 $\mathsf { R } ( \mathsf { t } ) \ \in \ [ \Theta , 1 ]$ 的两态突发过程，并记录突发过程，并记录发过程，并记录

```txt
R0 = 0.55; % 基线吞吐强度
```

```txt
Rb = 0.35; % 突发增量
```

```txt
p_on = 0.15; % 每秒进入突发概率
```

```txt
p_off = 0.10; % 每秒退出突发概率
```

```txt
sigma = 0.03; % 小噪声
```

```javascript
R = zeros(N,1);
```

$\text{burst} = 0$

for  $k = 1:N$

```txt
if u(video(k) == 0
```

$\text{burst} = 0;$

```txt
R(k) = 0;
```

```txt
continue;
```

```txt
end
```

if burst  $= = 0$

```txt
if rand() < p_on, burst = 1; end
```

```txt
else
```

```erlang
if rand() < p_off, burst = 0; end
```

```txt
end
```

```javascript
Rk = R0 + burst*Rb + sigma*randn();
```

```matlab
R(k) = max(0, min(1, Rk));
```

end

```matlab
Pnet_idle = 0.30; % W  
eta = 1.50; % W  
Pnet = Pnet_idle + eta .* R;  
% ---- Total power ----  
P = Pbase + Pscreen + Pcpu + Pnet;
```

```matlab
%% =============== Finite Difference Update (Explicit Euler) === den = Vnom * QeffAh * 3600; % (W*s) per SOC=1
```

tte  $=$  NaN;   
idx_empty  $\equiv$  NaN;   
for n  $= 1$  N-1   
SOC(n+1)  $=$  SOC(n)-  $(\mathsf{P}(\mathsf{n})\ast \mathsf{dt})$  /den;

```matlab
if SOC(n+1) <= 0  
frac = SOC(n) / (SOC(n) - SOC(n+1));  
tte = t(n) + frac*dt;  
idx_empty = n+1;  
SOC(n+1:end) = 0;  
break;  
end
```

```matlab
%% = Truncate  
if ~isnan(idx_empty)  
t_out = t(1:idx_empty);  
SOC_out = SOC(1:idx_empty);  
P_out = P(1:idx_empty);  
Pscreen_out = Pscreen(1:idx_empty);  
Pcpu_out = Pcpu(1:idx_empty);  
Pnet_out = Pnet(1:idx_empty);  
R_out = R(1:idx_empty);  
else  
t_out = t; SOC_out = SOC; P_out = P;  
Pscreen_out = Pcpu_out = Pcpu; Pnet_out = Pnet; R_out = R;  
end
```

```matlab
%% = Keep only integer minutes = minute_mask = mod(t_out, 60) == 0; t分鐘 = t_out(minute_mask);
```

```matlab
SOC_m = SOC_out(minute_mask);  
Ptot_m = P_out(minute_mask);  
Pscreen_m = Pscreen_out(minute_mask);  
Pcpu_m = Pccpu_out(minute_mask);  
Pnet_m = Pnet_out(minute_mask);  
R_m = R_out(minute_mask);  
u_m = u_video(1: numel(t_out));  
u_m = u_m(minute_mask);
```

```matlab
%% = Output Table =  
TSOC = table( ...  
t_minute, t_minute/60, t_minute/3600, ...  
SOC_m, ...  
Ptot_m, ...  
Pbase*ones(size(t_minute)), Pscreen_m, Pcpu_m, Pnet_m, ...  
R_m, u_m, ...  
'VariableNames', {'t(sec}', 't_min', 't_hour', ...  
'SOC', ...  
'P_total_W', ...  
'P_base_W', 'P_SCREEN_W', 'P_cpu_W', 'P_net_W', ...  
'R_net_0to1', 'u_video')}  
assignin('base', 'TSOC', TSOC);  
out_csv = fullfile(pwd, 'tte_base_then_1hvideoDetailed_withR1.csv');  
writetable(TSOC, out_csv);
```

```erlang
%% =============== Print==============  
fprintf('Scenario: base -> 1h videoDetailed) -> base\n');  
fprintf('Video window = [%.2f, %.2f] hours\n', t(video_start/3600, t(video_end/3600);
```

```matlab
if isnan(tte)  
fprintf('Battery not emptied within %.2f hours.\n', tmax/3600);  
else  
fprintf('TTE = %.4f hours (%1f minutes)\n', tte/3600, tte/60);  
end  
fprintf('Saved minute-level table to: %s\n', out_csv);
```

```matlab
\(\% \% = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = \text{一}\) Plots \(= - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
figure;
plot(TSOC.t_min, TSOC.SOC, 'LineWidth', 2);
grid on;xlabel('Time (minutes)');ylabel('SOC');
```

```javascript
title('SOC(t) sampled every minute');
```


figure;


```javascript
plot(TSOC.t_min, TSOC.P_total_W, 'LineWidth', 1.8); hold on; plot(TSOC.t_min, TSOC.P_base_W, '-', 'LineWidth', 1.2); plot(TSOC.t_min, TSOC.Pscreen_W, '-', 'LineWidth', 1.2); plot(TSOC.t_min, TSOC.P_cpu_W, '-', 'LineWidth', 1.2); plot(TSOC.t_min, TSOC.P_net_W, '-', 'LineWidth', 1.2); grid on;xlabel('Time (minutes)');ylabel('Power(W)'); legend('Total','Base','Screen','CPU','Net','Location','best'); title('Power components (minute-sampled)');
```


figure;


```matlab
plot(TSOC.t_min,TSOC.R_net_0to1,'LineWidth',1.6); grid on;xlabel('Time(minutes)');ylabel('R(t)(0~1)'); title('Network bursty fluctuation R(t)(minute-sampled)'); end
```


程序 


```matlab
function sa_QeffAh_oneclick()  
clc; clear; close all;
```

```erlang
%% = Baseline Settings (same as your model)
```


rng_base = 2; % 固定随机性：每个 Q 都用同一条随机 R(t)ng_base = 固定随机


```matlab
SOC0 = 0.60; % initial SOC (0~1)  
Vnom = 3.85; % nominal battery voltage (V)  
Q0 = 4.5; % baseline effective capacity (Ah)
```

$\%$  ---- time settings (DO NOT change) ----  
t_base_before = 30*60; % seconds  
t(video_dur = 1*3600; % seconds  
dt = 1.0; % seconds  
tmax = 24*3600; % seconds

```erlang
%% ---- Sensitivity sweep on QeffAh ----
```


$\%$ 你只需要改这行的范围/密度即可


```hcl
scale_list = [0.6 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4];  
Q_list = Q0 * scale_list;
```

```erlang
%% =----------------------- Pick some curves to plot =-----------------------
```


pick_scales $=$ [0.6 0.8 1.0 1.2 1.4]; $\%$ 画 SOC 对比曲线用（可改）


# 2026美赛赛中保奖班

赠送3份美赛精品课

保M奖1v1

# 预售价750元

原价8999

·赛中不限课时指导 $^ +$ 无限次数答疑

·赠送价值399的美赛大班课，一个队伍送三份，优惠$1 0 0 0 + !$

·试听课机制保障，老师均是O/F奖或国/研赛国一得主，你的老师由你检验

保H奖1v1

# 预售价3999元

原价4588

·赛中不限课时指导 $^ +$ 无限次数答疑

·赠送价值399的美赛大班课，一个队伍送三份，优惠$1 0 0 0 + !$

·试听课机制保障，老师均是F/M奖或国/研赛二等奖以上得主，你的老师由你检验

SOC_curves $=$ struct(); $\%$ 存曲线数据

labels $=$ {}; $\%$ legend 标签

```matlab
%% = Run sweep  
TTE_sec = nan(numel(Q_list),1);  
TTE_hour = nan(numel(Q_list),1);  
TTE_min = nan(numel(Q_list),1);  
for i = 1: numel(Q_list)  
QeffAh = Q_list(i);
```

$\%$ 为了“只分析QeffAh”，每次都用同一个随机序列

rng(rng_base);

```txt
out = run_single_sim(SOC0, Vnom, QeffAh, ... t_base_before, t_video_dur, dt, tmax);
```

```matlab
TTE_sec(i) = out.tte;  
TTE_hour(i) = out.tte/3600;  
TTE_min(i) = out.tte/60;
```

$\%$ 存几条 SOC曲线用来对比

if any(abs(scale_list(i) - pick_scales) < 1e-12)  
 $\% \checkmark$  字段名合法化：  $0\times 0\_ 8 / 0\times 1\_ 0 / 0\times 1\_ 2$   
key = printf('Qx%0.1f', scale_list(i));  
key = matlab.lang.makeValidName(strrep(key, '.', '')));

```matlab
SOC.curves.(key).t_min = out.TSOC.t_min;  
SOC.curves.(key).SOC = out.TSOC.SOC;  
SOC.curves.(key).Ptot = out.TSOC.P_total_W;  
labels{end+1} = printf('Q=%.2f Ah (x%.1f)', QeffAh, scale_list(i)); %#ok<AGROW>  
end  
end
```

```matlab
%% =============== Output table =============== Tout = table(Q_list(:), scale_list(:), TTE_hour(:), TTE_min(:), TTE(sec(:), ... 'VariableNames', {'QeffAh', 'Q_scale', 'TTE_hour', 'TTE_min', 'TTE(sec')}); disp(Tout);
```

```txt
out_csv = fullfile(pwd, 'SA_QeffAh_results.csv');  
writetable(Tout, out_csv);
```

```matlab
fprintf('Saved sensitivity results to: %s\n', out_csv);  
%% = Plott 1: TTE vs QeffAh = Plott 2: TTE vs QeffAh = Plott 3: TTE vs QeffAh, Tout.TTE_hour, '-o', 'LineWidth', 1.8);  
grid on;  
xlabel('Q{eff} (Ah)');  
ylabel('TTE (hours)');  
title('Sensitivity: TTE vs Effective Capacity Q{eff}')  
%% = Plott 2: Normalized sensitivity (elasticity-like)  
Plott 3: Compare SOC curves for selected Q  
xlabel('TOut.QeffAh', axis, 'LineWidth', 1.8);  
grid on;  
xlabel('Q{eff} (Ah)');  
ylabel('Approx. elasticity (ΔTTE/TTE0)/(ΔQ/Q0)');  
title('Sensitivity (approx): Elasticity of TTE w.r.t Q{eff}')  
xlabel('fieldnames(SOC-curves);')  
%为了让 legend 顺序与 labels 对齐，我们按 pick_scales 顺序画  
for ps = 1: numel(pick_scales)  
key = printf('Qx%0.1f', pick_scales(ps));  
key = matlab.lang.makeValidName(strrep(key, '.', '.'));  
if isfield(SOC-curves, key)  
plot(SOC-curves.(key).t_min, SOC-curves.(key).SOC, 'LineWidth', 1.8);  
end  
end
```

```matlab
xlabel('Time (minutes)');  
ylabel('SOC');  
title('SOC(t) comparison under different Q{'eff'}');  
legend(labels, 'Location', 'best');  
end
```

```erlang
%%  
function out = run_single_sim(SOC0, Vnom, QeffAh, t_base_before, t_video_dur, dt, tmax)
```

$\% = = = = =$  time grid  $= = = = =$  t(video_start  $\equiv$  t_base_before; t(video_end  $\equiv$  t(video_start + t(video_dur;

```txt
N = floor(tmax/dt) + 1;  
t = (0:N-1)' * dt;
```

```txt
u(video = double(t >= t(video_start & t < t(video_end);
```

$\mathrm{SOC} = \mathrm{nan}(N,1)$ $\mathrm{SOC}(1) = \mathrm{SOC0};$

$\% \% = = = = =$  Power Model (same as your script)  $= = = = =$ $\%$  Base Pbase  $= 0.82$

```matlab
% Screen  
b0 = 0.70;  
b = b0 .* u(video);  
alpha0 = 0.80;  
alpha1 = 2.20;  
Pscreen = u(video .* (alpha0 + alpha1 .* b));
```

$\%$  CPU (Version A)   
10  $= 0.55$    
1  $= 10$  .\* u(video;   
beta0  $= 0.20$    
beta1  $= 2.50$    
gamma  $= 1.60$    
Pcpu  $=$  beta0  $^+$  beta1.\* (1.^gamma);

```matlab
% Network (bursty Markov + noise)  
R0 = 0.55;
```

$\mathsf { R b } ~ = ~ \mathsf { 0 } . 3 5$ ;

p_on = 0.15;

$\mathsf { p \_ o f f } = \mathsf { \_ } 0 . 1 \mathsf { \_ }$

sigma $= ~ 8 . 6 3$ ;

$\textsf { R } =$ zeros(N,1);

burst $\qquad = \ 0$

for $\textsf { k } = \pmb { \bot } : \mathbb { N }$

if u_video(k) == 0

burst $\qquad = \ 0$

$\mathsf { R } ( \mathsf { k } ) \ = \ \mathsf { \Omega } \theta ;$

continue;

end

if burst $\scriptstyle = = \varnothing$

if rand() < p_on, burst = 1; end

else

if rand() < p_off, burst = 0; end

end

Rk = R0 + burst*Rb + sigma*randn();

R(k) = max(0, min(1, Rk));

end

Pnet_idle = 0.30;

etata $=$ 1.50;

Pnetnet $=$ Pnet_idle + eta .* R;Pnet_id Pnet_i eta

P = Pbase + Pscreen + Pcpu + Pnet;Pb 群e Pc screen +

%% ===== Finite difference update=== Finite = $= = = = = =$

den $=$ Vnom * QeffAh * 3600;nom *

tte $=$ NaN;

idx_empty $=$ NaN;

for $\mathsf {  ~ \mathsf {  ~ n ~ } ~ } = \mathsf {  ~ 1 : } \mathsf { N - 1 }$

SOC(n+1) = SOC(n) ‐ (P(n) * dt) / den;

if SOC(n+1) <= 0

frac $=$ SOC(n) / (SOC(n) ‐ SOC(n+1));

tte = t(n) + frac*dt;

idx_empty $= \ n { + } 1$

SOC(n+1:end) = 0;

break;   
end   
end   
% truncate   
if ~isnan(idx_empty)   
t_out = t(1:idx_empty);   
SOC_out = SOC(1:idx_empty);   
P_out = P(1:idx_empty);   
Pscreen_out = Pscreen(1:idx_empty);   
Pcpu_out = Pcpu(1:idx_empty);   
Pnet_out = Pnet(1:idx_empty);   
R_out = R(1:idx_empty);   
u_out = u(video(1:idx_empty);   
else   
t_out = t; SOC_out = SOC; P_out = P;   
Pscreen_out = Pscreen; Pcpu_out = Pcpu; Pnet_out = Pnet; R_out = R;   
u_out = u Video;   
end   
% minute sampling   
minute_mask  $=$  mod(t_out,60）  $= = 0$  .   
t_minute  $=$  t_out(minute_mask);   
TSOC  $=$  table( ...   
t_minute,..   
t_minute/60,..   
t_minute/3600,..   
SOC_out(minute_mask),...   
P_out(minute_mask),...   
Pbase*ones(size(t_minute)),...   
Pscreen_out(minute_mask),...   
Pcpu_out(minute_mask),...   
Pnet_out(minute_mask),...   
R_out(minute_mask),...   
u_out(minute_mask),...   
'VariableNames',{'t_min','t_minute','t_hour','SOC','P_total_W',... 'P_base_W','PScreen_W','P_cpu_W','P_net_W',... 'R_net_0to1','u_video'});

% 修正列名（上面为了避免写错，这里统一一下）

```python
TSOC.Properties variableNames =  
{ 't_sec', 't_min', 't_hour', 'SOC', 'P_total_W', ...  
'P_base_W', 'P.Screen_W', 'P_cpu_W', 'P_net_W', ...
```

```matlab
'R_net_0to1', 'u_video'};  
out.tte = tte;  
out.TSOC = TSOC;  
end
```


程序 


```matlab
function sa_b0_oneclick()
clc; clear; close all;
%% = Baseline Settings (same as your model)
>>> baseline Settings (same as your model)
>>> 
rng_base = 2; % 固定随机性: 每个 b0 都用同一条随机 R(t)
SOC0 = 0.60; % initial SOC (0~1)
Vnom = 3.85; % nominal battery voltage (V)
QeffAh = 4.5; % effective capacity (Ah)
% --- time settings (DO NOT change) ---
t_base_before = 30*60; % seconds
t_video_dur = 1*3600; % seconds
dt = 1.0; % seconds
tmax = 24*3600; % seconds
```

```erlang
%% ---- Sensitivity sweep on bθ (screen brightness)
```


% b0 $\in$ [0,1]，你可改密度


```txt
b0_list = [0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0];
```

```erlang
%% =----------------------- Pick some curves to plot =-----------------------
```


pick_b0 $=$ [0.1 0.4 0.7 1.0]; % 画 SOC 对比曲线用（可改）


```javascript
SOC_curves = struct();
```


labels = {};


```erlang
%% =============== Run sweep ===============
```


TTE_sec $=$ nan(numel(b0_list),1);


```txt
TTE_hour = nan(numel(bθ_list),1);
```


TTE_min $=$ nan(numel(b0_list),1);


```txt
for i = 1: numel(b0_list)
```


b0 = b0_list(i);


% 为了“只分析b0”，每次都用同一个随机序列

rng(rng_base);   
out  $=$  run_single_sim_b0(SOC0,Vnom,QeffAh,.. t_base_before,t(video_dur,dt,tmax,... b0);   
TTE(sec(i)  $=$  out.tte;   
TTE_hour(i)  $=$  out.tte/3600;   
TTE_min(i)  $=$  out.tte/60;

$\%$ 存几条 SOC曲线用来对比

```matlab
if any(abs(b0 - pick_b0) < 1e-12)  
key = printf('b0_%03d', round(b0*100)); % e.g. b0_070  
SOC.curves(key).t_min = out.TSOC.t_min;  
SOC.curves(key).SOC = out.TSOC.SOC;  
SOC.curves(key).Ptot = out.TSOC.P_total_W;  
labels{end+1} = printf('b0=%.2f', b0); %#ok<AGROW>  
end
```

```matlab
%% = Output table = Tout = table(b0_list(:), TTE_hour(:), TTE_min(:), TTE(sec(:), ... 'VariableNames', {'b0', 'TTE_hour', 'TTE_min', 'TTE(sec'})}; disp(Tout); out_csv = fullfile(pwd, 'SA_b0_results.csv'); writetable(Tout, out_csv); fprintf('Saved sensitivity results to: %s\n', out_csv);
```

```matlab
%% =============== Plot 1: TTE vs b0 =============== figure; plot(Tout.b0, Tout.TTE_hour, '-o', 'LineWidth', 1.8); grid on; xlabel('b_0 (brightness, 0~1)'); ylabel('TTE (hours)'); title('Sensitivity: TTE vs Screen Brightness b_0');
```

```txt
%% =============== Plot 2: SOC curves comparison =============== figure; hold on;
```

$\%$  保证 legend 顺序与 pick_b0 一致  
for j = 1: numel(pick_b0)

```matlab
key = printf('b0_%03d', round_pick_b0(j)*100));  
if isfield(SOC.curves, key)  
plot(SOC.curves.(key).t_min, SOC.curves.(key).SOC, 'LineWidth', 1.8);  
end  
end  
grid on;  
xlabel('Time (minutes)');  
ylabel('SOC');  
title('SOC(t) comparison under different b_0');  
legend labels, 'Location', 'best');  
end  
% function out = run_single_sim_b0(SOC0, Vnom, QeffAh, t_base_before, t_video_dur, dt, tmax, b0)  
% time grid  
t(video_start = t_base_before;  
t(video_end = t(video_start + t(video_dur;  
N = floor(tmax/dt) + 1;  
t = (0:N-1)' * dt;  
u(video = double(t >= t(video_start & t < t(video_end);  
SOC = nan(N,1);  
SOC(1) = SOC0;  
% Power Model (same as your detailed script; only b0 varies) === % Base  
Pbase = 0.82;  
% Screen (b0 is the parameter under test)  
b = b0 .* u(video;  
alpha0 = 0.80;  
alpha1 = 2.20;  
Pscreen = u(video .* (alpha0 + alpha1 .* b);  
% CPU (Version A)  
10 = 0.55;  
1 = 10.* u(video;  
beta0 = 0.20;
```

```lisp
beta1 = 2.50;  
gamma = 1.60;  
Pcpu = beta0 + beta1 .* (1.^gamma);
```


$\%$ Network (bursty Markov $^ +$ noise)


$\mathsf{R0} = 0.55;$

```txt
Rb = 0.35;
```

```txt
p_on = 0.15;
```

```txt
p_off = 0.10;
```

sigma  $= 0.03$

$R =$  zeros(N,1);

$\text{burst} = 0$

for  $k = 1:N$

```txt
if u(video(k) == 0
```

$\text{burst} = 0$

$\mathsf{R}(\mathsf{k}) = \mathsf{0};$

```txt
continue;
```

```txt
end
```

if burst  $= = 0$

```txt
if rand() < p_on, burst = 1; end
```

```txt
else
```

```erlang
if rand() < p_off, burst = 0; end
```

```txt
end
```

```javascript
Rk = R0 + burst*Rb + sigma*randn();
```

```matlab
R(k) = max(0, min(1, Rk));
```

```txt
end
```

```txt
Pnet_idle = 0.30;
```

eta  $= 1.50$

```txt
Pnet = Pnet_idle + eta .* R;
```

```txt
P = Pbase + Pscreen + Pcpu + Pnet;
```

%%  $= = = = =$  Finite difference update  $= = = = =$

```txt
den = Vnom * QeffAh * 3600;
```

```txt
tte = NaN;
```

```txt
idx_empty = NaN;
```

for  $n = 1:N - 1$

$\mathrm{SOC}(n + 1) = \mathrm{SOC}(n) - (P(n)*dt) / den;$

```matlab
if SOC(n+1) <= 0  
frac = SOC(n) / (SOC(n) - SOC(n+1));  
tte = t(n) + frac*dt;  
idx_empty = n+1;  
SOC(n+1:end) = 0;  
break;  
end  
end
```

```matlab
% truncate  
if ~isnan(idx_empty)  
t_out = t(1:idx_empty);  
SOC_out = SOC(1:idx_empty);  
P_out = P(1:idx_empty);  
else  
t_out = t; SOC_out = SOC; P_out = P;  
end
```

```matlab
% minute sampling  
minute_mask = mod(t_out, 60) == 0;  
t分鐘 = t_out(minute_mask);  
TSOC = table( ...  
t分鐘, ...  
t分鐘/60, ...  
t分鐘/3600, ...  
SOC_out(minute_mask), ...  
P_out(minute_mask), ...  
'VariableNames', {'t(sec', 't_min', 't_hour', 'SOC', 'P_total_W'}));  
out.tte = tte;  
out.TSOC = TSOC;  
end
```