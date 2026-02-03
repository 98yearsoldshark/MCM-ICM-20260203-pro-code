<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.1 Parameter Sensitivity（Risk / Voltage Collapse） -->

## 7.1 Global Sensitivity of “Sudden Shutdown” Risk (Voltage Headroom)

Mean TTE alone does not fully explain the user experience of **rapid, seemingly unpredictable drain**. In practice, phones often terminate early due to **voltage sag**: under a bursty load, the terminal voltage can cross the cut-off threshold even when SOC is not extremely low. To quantify this mechanism in a continuous manner, we track a normalized **minimum voltage headroom margin** over each discharge trajectory. A margin close to zero indicates that the system is approaching the voltage-collapse boundary (i.e., extremely sensitive to small increases in load or internal resistance).

![Figure Q3-2. Global PRCC heatmap for minimum voltage headroom margin (risk metric).](../figure.png)

*Figure Q3-2* shows the PRCC sensitivity of the headroom margin. Parameters that increase effective internal resistance (e.g., \(R_0\) scaling and aging-induced resistance growth) systematically reduce the margin, increasing the likelihood of early termination under burst loads. This figure supports a key modeling insight for Q3: **risk-related outputs can be far more sensitive than mean TTE**, especially in high-power scenarios.
