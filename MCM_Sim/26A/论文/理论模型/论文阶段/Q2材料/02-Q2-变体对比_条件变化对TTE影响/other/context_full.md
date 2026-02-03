# 插入建议

- 建议插入位置：接在 `01-Q2-TTE矩阵_场景×SOC0` 之后，作为 **Q2.2** 小节（回答赛题第二问：哪些条件导致续航最大幅度缩短）。
- 用途：把“同一活动下仅改变少量条件”的对照做成图，避免只用文字描述。

# 可直接粘贴到论文的文本（中文）

## Q2.2 哪些活动/条件会最大幅度缩短续航？（scenario variants）

为识别**哪些活动或外部条件会造成电池续航的最大幅度缩短**，我们针对每个代表性场景构造一组 *scenario variants*：在保持核心活动不变（例如视频、导航）的前提下，仅改变少量条件（网络模式：Wi‑Fi vs 蜂窝；信号质量：good vs poor；亮度；环境温度：cold/hot 等），并重新运行连续时间仿真以比较 baseline 与各个变体的 TTE。

图 Q2-2 汇总了 $SOC_0=1.0$ 时的结果；误差棒表示由后台随机过程（例如后台唤醒、网络尾态触发）导致的 5%–95% 波动区间。

（在此插入图 Q2-2）

图 Q2-2：同一场景 baseline 与 variants 的 TTE 对比（$SOC_0=1.0$）。

从各场景对比可以看到，TTE 的最大降幅通常来自两类因素：（i）**网络相关压力**（例如弱信号、蜂窝网络模式下的持续数据传输），（ii）**环境极端**（低温户外、炎热夏季）。其物理机理在于：弱信号会显著抬升单位数据能耗并更易触发/延长 RRC 尾态；低温则会提高内阻 $R_0$，两者都会加速端电压下跌，从而更早触发欠压截止。相对地，一些单因子改动（例如在“算力主导”的游戏场景中做小幅亮度调整）对 TTE 的影响可能低于直觉预期，这一点我们在图 Q2-6 中给出可检验的“surprisingly little”口径。

（这是讲解内容，论文中可删除）  
这张图的重点不是“精确数值”，而是“条件排名”：弱信号/蜂窝网络/极端温度往往是最强的 TTE 缩短因素；它们对应模型里的 RRC 尾态、每 MB 能耗、以及电池内阻/欠压截止三条机理链路。后续用 drivers 矩阵（图 05）可以进一步回答“到底是哪一块在耗电”。

# 可直接粘贴到论文的文本（英文）

## Q2.2 Which conditions shorten TTE the most? (scenario variants)

To identify **which activities or external conditions produce the greatest reductions in battery life**, we construct a set of *scenario variants*. A variant keeps the same high-level activity (e.g., video, navigation) but changes a small number of conditions such as network mode (Wi‑Fi vs cellular), signal quality (good vs poor), brightness, and ambient temperature (cold/hot). We then re-simulate the continuous-time model and compare TTE under the baseline and each variant.

Figure Q2-2 summarizes the results for $SOC_0=1.0$. The error bars represent the 5%–95% range due to stochastic background processes.

(Insert Figure Q2-2 here.)

Figure Q2-2: Baseline vs variants (SOC0=1.0). Conditions such as weak signal, cellular transmission, and extreme temperature can significantly reduce TTE.

Across scenarios, the largest reductions are consistently associated with **network-related stressors** (e.g., switching from Wi‑Fi to cellular under poor signal) and **environmental extremes** (cold outdoor and hot summer). Mechanistically, weak signal increases the energy cost per delivered data (retransmissions and higher radio transmit power), while cold temperature increases internal resistance $R_0$, both of which accelerate voltage drop and trigger earlier undervoltage cutoff. In contrast, some single-factor changes (e.g., small screen brightness adjustments in already compute-dominated gaming) can alter TTE much less than expected, which we quantify more explicitly in Figure Q2-6.
