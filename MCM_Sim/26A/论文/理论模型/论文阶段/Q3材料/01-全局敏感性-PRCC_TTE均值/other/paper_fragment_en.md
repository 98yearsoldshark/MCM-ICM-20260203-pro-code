<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.1 Parameter Sensitivity（Global） -->

## 7.1 Global Sensitivity to Parameter Values (PRCC)

To examine how our **time-to-empty (TTE)** predictions vary under plausible uncertainty in physical and usage-related parameters, we conducted a **global sensitivity analysis**. We sampled key parameters (battery capacity and resistance scaling, cut-off settings, SOH and aging-related resistance growth, PMIC efficiency, and component-level power scalings) from defensible prior ranges and simulated the continuous-time ODE model for each sample. For each parameter sample, we repeated the simulation under multiple random seeds to average out stochastic usage effects.

![Figure Q3-1. Global PRCC heatmap for mean TTE across scenarios.](../figure.png)

*Figure Q3-1* reports the **Partial Rank Correlation Coefficient (PRCC)** between each parameter and the **mean TTE**. PRCC measures the strength and direction of a parameter's monotonic influence on the output while controlling for the other parameters. A positive PRCC indicates that increasing the parameter tends to increase mean TTE, while a negative PRCC indicates the opposite. The heatmap shows that the most influential parameters are scenario-dependent: capacity/SOH dominates across most scenarios, while radio- and workload-related scalings become the primary drivers in network- or compute-intensive settings.
