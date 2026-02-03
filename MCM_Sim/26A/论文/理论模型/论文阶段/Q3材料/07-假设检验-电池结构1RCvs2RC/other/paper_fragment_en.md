<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.2 Assumption Checks（Structure: 1RC vs 2RC） -->

## 7.2 Assumption Checks: Polarization Structure (1RC vs. 2RC)

Our baseline battery ECM uses a single polarization branch (1RC) to capture transient voltage drop and recovery. A common alternative is a two-time-scale structure (2RC), which separates “fast” and “slow” polarization dynamics. Since this is a structural modeling choice, we tested its impact by projecting the same calibrated resistance curves into a 2RC form and comparing predicted TTE under identical usage inputs.

![Figure Q3-7. Structural ablation: 1RC versus 2RC polarization and the resulting change in TTE.](../figure.png)

*Figure Q3-7* indicates how sensitive the predicted TTE is to this structural assumption. If the difference is small, 1RC provides a parsimonious approximation for TTE prediction; if the difference is notable in burst-heavy scenarios, the structure itself should be treated as an additional source of model uncertainty (and 2RC should be preferred for higher-fidelity voltage dynamics).
