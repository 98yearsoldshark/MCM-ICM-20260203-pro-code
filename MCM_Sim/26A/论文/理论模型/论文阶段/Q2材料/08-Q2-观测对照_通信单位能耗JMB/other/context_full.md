# 插入建议

- 建议插入位置：Q2 的观测对照小节中，紧跟“功耗量级（AndroWatts）”之后，用于补强网络机理参数的量级合理性。
- 用途：用公开实测数据给出“网络每传 1MB 的能量成本”的量级，从而解释网络相关场景为何会大幅缩短 TTE。

# 可直接粘贴到论文的文本（中文）

## Q2.8 观测对照：通信单位能耗（J/MB）与网络耗电机理（SmartphoneMeasurements）

网络活动是手机续航“出乎意料地下降”的常见来源，因为其能量成本会随信号质量、协议开销以及尾态（tail states）显著变化。为使无线电（radio）子模型的参数量级有据可依，我们使用公开数据集 **SmartphoneMeasurements**（Monsoon 功耗测量 + iPerf 吞吐日志），其提供了受控 Wi‑Fi 传输实验下的平均功耗观测。

我们将“增量功耗”与吞吐率结合，计算**单位数据能耗**（J/MB）。图 Q2-8 对比了 Wi‑Fi 经路由器与 Wi‑Fi Direct 两种模式下的 J/MB 分布。

（在此插入图 Q2-8）

图 Q2-8：SmartphoneMeasurements 网络单位能耗（J/MB）观测分布（路由器 vs Wi‑Fi Direct）。

该观测区间可直接用于约束连续时间无线电模型中的参数 $e_{per\_MB}$。在本文模型中，数据相关功耗可写为
\[
P_{data}=e_{per\_MB}\cdot \dot{D},
\]
其中 $\dot{D}$ 为数据速率（MB/s）。同时，图 Q2-8 中的离散度也支持将网络耗电视为**场景相关且具有不确定性**的机制，而非一个固定可加常数。

（这是讲解内容，论文中可删除）  
这张图的价值是：你把“网络每传 1MB 要花多少能量”从公开实测里拿到了量级，从而让网络模型更像机理模型而不是拍脑袋常数。它也解释了为什么 weak signal / router 这种条件会让 TTE 大幅缩短（单位数据能耗更高 + 尾态更容易被触发）。  

# 可直接粘贴到论文的文本（英文）

## Q2.8 Plausibility check for network drain: energy per delivered data

Network activity is a common source of “unexpected” battery drain because its energy cost depends strongly on signal quality, protocol overhead, and tail states. To anchor the magnitude of our radio model, we use **SmartphoneMeasurements** (Monsoon power monitor + iPerf throughput logs), which provides open measurements of mean power during controlled Wi‑Fi experiments.

We compute the **energy per delivered data** (J/MB) from the measured incremental power and throughput. Figure Q2-8 compares Wi‑Fi via router vs Wi‑Fi Direct.

(Insert Figure Q2-8 here.)

Figure Q2-8: Observed network energy per MB (J/MB) from SmartphoneMeasurements.

This empirical range directly informs the parameter $e_{per\_MB}$ in our continuous-time radio model, where the data-dependent power is modeled as $P_{data}=e_{per\_MB}\cdot \dot{D}$ (with $\dot{D}$ in MB/s). The observed spread also motivates treating network drain as both scenario-dependent and uncertain rather than a fixed additive constant.
