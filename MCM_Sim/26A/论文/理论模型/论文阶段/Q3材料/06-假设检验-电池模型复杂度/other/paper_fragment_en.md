<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.2 Assumption Checks（Model Complexity） -->

## 7.2 Assumption Checks: Battery Model Complexity (Model-1 vs. Model-2 vs. Model-3)

Another critical assumption is the level of physical detail required on the battery side. We therefore compared three nested continuous-time models under identical usage inputs: (i) an electrical ECM (Model-1), (ii) an electro-thermal model (Model-2), and (iii) an electro-thermal-aging model with health state (Model-3). This isolates the impact of adding thermal coupling and aging pathways.

![Figure Q3-6. Battery model complexity ablation: how TTE changes from Model-1 to Model-3.](../figure.png)

*Figure Q3-6* shows that model complexity can meaningfully change the predicted TTE and risk indicators in high-load scenarios. In particular, thermal coupling alters the effective resistance and voltage sag over time, while aging shifts both capacity and resistance, amplifying early cut-off behavior. Therefore, for realistic smartphone usage (bursts, sustained high load, temperature variation), these processes should be included rather than treated as negligible.
