<!-- Suggested placement: Section 7 (Sensitivity and Assumptions / Q3) -> 7.1 Global parameter sensitivity -->

## 7.1 Global Sensitivity of Parameter Values (PRCC)

To address Q3 ("How do your predictions vary when you change parameter values?"), we sample key parameters (battery capacity and health state SOH, component-level power scaling factors, wireless/background mechanisms, etc.) within reasonable prior ranges, and run our continuous-time ODE model to obtain the **mean time-to-empty (TTE)** for each sample. To reduce noise from stochastic usage processes, we repeat simulations with multiple random seeds per parameter sample and average the outcomes. To avoid mixing in quantities treated as fixed in our modeling scope (e.g., safety thresholds and already-calibrated constants), those fixed items are removed from the x-axis of the PRCC plot.

![Fig. Q3-1: Global sensitivity PRCC heatmap for mean TTE across scenarios.](figure.png)

Fig. Q3-1 reports the **PRCC (Partial Rank Correlation Coefficient)** between each parameter and the **mean TTE** (cell values are PRCC in \([-1,1]\)). PRCC measures the strength and direction of a parameter's monotonic effect on the output **after controlling for other parameters**: a positive PRCC indicates that increasing the parameter tends to increase TTE, while a negative PRCC indicates that increasing the parameter tends to decrease TTE. The results show clear scenario dependence: capacity/SOH dominate in most scenarios, while in network- or compute-intensive scenarios, power scaling factors related to wireless and load become the primary drivers of TTE variation.

