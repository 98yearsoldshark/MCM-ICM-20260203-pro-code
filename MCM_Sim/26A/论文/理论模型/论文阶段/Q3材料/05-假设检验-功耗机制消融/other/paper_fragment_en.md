<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.2 Assumption Checks（Mechanism Ablation） -->

## 7.2 Assumption Checks via Mechanism Ablation (Drivers vs. “Surprisingly Little”)

Q3 also asks how predictions vary when we change **modeling assumptions**. We tested the robustness of our conclusions by performing a structured **mechanism ablation** study: starting from the baseline continuous-time model, we remove one hypothesized power mechanism at a time (e.g., screen, CPU/GPU workload, GPS, radio state/tail effects, background wakeups, interaction bursts, etc.), recompute TTE under each scenario, and record the change \(\Delta\)TTE relative to baseline.

![Figure Q3-5. Mechanism ablation heatmap: change in TTE when removing one mechanism at a time.](../figure.png)

*Figure Q3-5* directly answers the prompt “Which activities produce the greatest reductions in battery life?” and “Which ones change the model surprisingly little?” Mechanisms whose removal yields the largest positive \(\Delta\)TTE are the dominant **drivers of rapid drain** for that scenario, while mechanisms that barely change TTE can be treated as second-order effects at the time scale of a single discharge (or safely simplified for faster simulation).
