# 插入建议

- 建议插入位置：若你把“history/aging”作为 Q2 的扩展驱动因素，就放在 Q2 末尾（例如 Q2.11/Q2.12）；否则可移动到 Q4 或讨论章节中。
- 用途：用“电池历史（SOH）”解释同样使用强度下 TTE 的额外差异来源，提高模型解释力与现实贴近度。

# 可直接粘贴到论文的文本（中文）

## Q2.11 历史/老化作为 TTE 变化的额外驱动因素（TTE vs SOH）

赛题背景强调电池行为会受到其历史（history）的影响。为展示老化如何改变耗尽时间（TTE），我们将（i）AndroWatts 提供的代表性手机负载水平，以及（ii）公开电池老化状态表（SOH 与对应 OCV 曲线族）结合：将每个 SOH 状态视为对**有效容量**与**内阻**的物理扰动，并在同一连续时间电池模型框架下重新计算 TTE。

图 Q2-11 展示了在三种代表性负载（轻/中/重）下，TTE 随 SOH 的变化关系。

（在此插入图 Q2-11）

图 Q2-11：电池老化对续航的影响——不同负载下的 TTE vs SOH。

可以看到，SOH 下降会带来近似单调的 TTE 缩短；在我们的实验中，从“新电池”到“寿命末期”的 SOH 变化可导致约 30% 的续航降低，而重负载始终是最易耗尽的工况。这为“相同使用强度下，不同手机仍可能呈现不同续航”的现象提供了可解释、可量化的机理级说明。

（这是讲解内容，论文中可删除）  
这张图等于给了你一个“历史维度”的 TTE 解释：同样的使用强度下，SOH 越低续航越短，而且幅度是可量化的（约 30%）。它非常适合冲高奖，因为题面背景明确提到了 history/aging。  

# 可直接粘贴到论文的文本（英文）

## Q2.11 Battery history (aging) as an additional driver of TTE variation

The problem statement emphasizes that a battery’s behavior is influenced by its history. To demonstrate how aging alters time-to-empty, we combine (i) representative smartphone load levels from AndroWatts and (ii) an open battery aging state table (SOH + OCV curve families). We treat each aging state as a physically grounded perturbation to the effective capacity and internal resistance, then simulate TTE using the same continuous-time battery model.

Figure Q2-11 shows the predicted TTE as a function of SOH for three representative load levels (light/medium/heavy).

(Insert Figure Q2-11 here.)

Figure Q2-11: Aging effect on battery life — TTE vs SOH under representative loads.

As expected, reduced SOH yields a nearly monotonic reduction in TTE. In our experiments, moving from “new” to “end-of-life” states reduces TTE by roughly 30% across loads, while heavy load remains consistently the fastest-draining regime. This provides an interpretable mechanism-level explanation of why two phones with similar usage may still exhibit different remaining time-to-empty depending on their battery health.
