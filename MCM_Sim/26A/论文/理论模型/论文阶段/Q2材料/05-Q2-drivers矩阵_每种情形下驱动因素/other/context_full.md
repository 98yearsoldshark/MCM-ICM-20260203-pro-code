# 插入建议

- 建议插入位置：在图 01–04（TTE + 不确定性）之后，作为 **Q2.5** 小节主图，直接回答赛题 “identify the specific drivers of rapid battery drain in each case”。
- 用途：把“每种情形(in each case)”的 drivers 以矩阵形式一次性展示，减少逐场景口头解释的篇幅。

# 可直接粘贴到论文的文本（中文）

## Q2.5 快速耗电的驱动因素识别（逐场景）

为解释不同场景下 TTE 为何差异巨大，我们对功耗分解做“组件级反事实”分析：对每个场景，保持其余机制不变，依次把某一组件功耗“移除”（置零）（屏幕、CPU/GPU、网络、GPS、后台等），并比较 TTE 的变化：
\[
\Delta TTE = TTE_{(-\text{component})} - TTE_{(\text{baseline})}.
\]
若某组件的移除带来较大的正向 $\Delta TTE$，说明该组件是该场景下电量快速消耗的主要驱动；若 $\Delta TTE$ 接近 0，则说明其影响出乎意料地小（我们在图 Q2-6 进一步量化“surprisingly little”）。

图 Q2-5 给出了不同场景下各组件的平均 $\Delta TTE$ 矩阵。

（在此插入图 Q2-5）

图 Q2-5：逐场景的组件级 drivers（平均 $\Delta TTE$，单位：小时）。

该矩阵呈现清晰的“驱动指纹（driver signature）”。例如，在游戏场景中 **CPU/GPU 前台功耗**占主导，因此移除算力负载带来的 TTE 增益最大，而屏幕/网络的边际影响相对较小；在导航场景中 **屏幕 + 网络 + 计算**共同贡献，符合“地图渲染 + 持续定位/数据交换”的机理；在待机与混合使用中，**后台唤醒与系统基线功耗**成为关键驱动，因为它们在长时间尺度上持续存在，并反复触发短突发与网络尾态。

（这是讲解内容，论文中可删除）  
注意：该图是“理想化反事实”（把某模块功耗置零）用于归因/敏感性，而不是承诺手机可直接实现该动作；真正可执行建议可在 Q4 翻译为用户/系统可操作策略（例如降低亮度、限制后台、切换网络模式）。

# 可直接粘贴到论文的文本（英文）

## Q2.5 Identifying drivers of rapid battery drain (case-by-case)

To explain *why* TTE differs so dramatically across scenarios, we perform a component-level counterfactual analysis. For each scenario, we re-run the simulation while “removing” (zeroing) one power component at a time (screen, CPU/GPU, radio, GPS, background, etc.) and measure the change in TTE:
\[
\Delta TTE = TTE_{(-\text{component})} - TTE_{(\text{baseline})}.
\]
A large positive $\Delta TTE$ indicates that the removed component was a dominant driver of battery drain in that scenario; values near zero indicate surprisingly small influence.

(Insert Figure Q2-5 here.)

Figure Q2-5: Component-level drivers by scenario (mean ΔTTE, hours).

The matrix reveals distinct “driver signatures”. In gaming, **CPU/GPU front-end power** dominates, so removing compute load yields the largest TTE gains, while screen/network adjustments have comparatively minor effects. In navigation, a combination of **screen + radio + compute** contributes, consistent with simultaneous GPS/map rendering and continuous data exchange. In standby and mixed-day usage, **background wake-ups and baseline system power** become the main drivers because they persist over long horizons and repeatedly trigger short bursts and network tails.
