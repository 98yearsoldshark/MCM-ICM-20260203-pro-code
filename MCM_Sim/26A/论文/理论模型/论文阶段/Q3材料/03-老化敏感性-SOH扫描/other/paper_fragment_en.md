<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.1 Parameter Sensitivity（Aging / SOH） -->

## 7.1 Sensitivity to Battery Aging (SOH Scan)

Battery history affects both the usable capacity and the effective internal resistance. To quantify how aging changes our predictions, we performed an **SOH scan** by mapping battery health to (i) capacity loss and (ii) resistance growth, and then recomputing TTE under the same usage scenarios. This isolates the effect of the aging-related parameters while keeping the governing continuous-time model unchanged.

![Figure Q3-3. Mean TTE versus SOH (aging sensitivity scan).](../figure.png)

As shown in *Figure Q3-3*, TTE decreases as SOH declines, but the slope varies by scenario. High-load scenarios are more sensitive because increased resistance causes larger voltage sag, pushing the device closer to cut-off even before SOC becomes very low. This provides a physically grounded explanation for why older batteries exhibit more “early shutdown” behavior under bursty or high-power usage patterns.
