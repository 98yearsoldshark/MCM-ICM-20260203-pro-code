# 插入建议

- 建议插入位置：紧跟图 03（TTE 分布）之后，作为 **Q2.4** 小节的总结图。
- 用途：把“模型哪里更稳健/哪里更不稳定”用量化指标表达，直接对应赛题 “identify where the model performs well or poorly”。

# 可直接粘贴到论文的文本（中文）

## Q2.4 模型在哪些情形下更可靠或更不可靠？（用不确定性做诊断）

在给出不确定性区间之外，我们进一步用 **90% 区间宽度** $p95-p05$ 作为“模型好/差边界”的诊断指标：在同一场景定义下，若 $p95-p05$ 较小，说明 TTE 对合理的参数变化与随机后台过程更稳健；反之，若 $p95-p05$ 较大，则意味着小扰动会在长时间尺度上累积并显著改变剩余可用时间，此时模型预测更不稳定、也更依赖未观测因素。

图 Q2-4 给出 $SOC_0=1.0$ 时各场景按不确定性宽度的排序。

（在此插入图 Q2-4）

图 Q2-4：不确定性宽度排名（$p95-p05$，$SOC_0=1.0$）。

排序结果表明：短时高负载场景（例如游戏、导航）通常更稳健，因为 TTE 主要由持续能量消耗与欠压截止控制；而待机/混合使用等长时场景不确定性最大，因为稀疏的后台唤醒与突发通信尾态会在长时间尺度上累积并放大波动。

（这是讲解内容，论文中可删除）  
赛题并没有规定“好/差”必须用什么指标衡量；用 **不确定性宽度** 来表述是很强的“满分口径”：你不是空口说“模型在 XX 场景更差”，而是用 $p95-p05$ 量化出来。随后再接 07/08/09/10 的观测对照图，就形成完整证据链。

# 可直接粘贴到论文的文本（英文）

## Q2.4 Where does the model perform well or poorly? (uncertainty as a diagnostic)

Beyond reporting uncertainty intervals, we use the **width of the 90% credible band** ($p95-p05$) as a diagnostic of where our model is intrinsically more reliable. A narrower band indicates that, under the same scenario definition, the TTE outcome is robust to plausible parameter variations and stochastic background processes; a wider band indicates a scenario in which small changes can accumulate and substantially alter the remaining time-to-empty.

Figure Q2-4 ranks scenarios by their uncertainty width at $SOC_0=1.0$.

(Insert Figure Q2-4 here.)

Figure Q2-4: Ranking of uncertainty width (p95−p05) across scenarios (SOC0=1.0).

The ranking suggests that the model is most robust for **short, high-load** regimes (e.g., gaming and navigation), where TTE is dominated by sustained energy draw and voltage cutoff. In contrast, **standby and mixed-day** regimes show the largest uncertainty, as infrequent background wake-ups and bursty communication tails can accumulate over long horizons, amplifying variability.
