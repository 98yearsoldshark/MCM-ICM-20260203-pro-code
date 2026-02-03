<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.3 Fluctuations in Usage Patterns（Stochastic） -->

## 7.3 Fluctuations in Usage Patterns: Stochastic Variability at Fixed Parameters

Even with the same average user behavior, smartphones exhibit random micro-events such as background wakeups, intermittent network tail activity, and interaction bursts. To quantify this source of variability, we fixed all parameters and scenario settings and reran the simulation multiple times with different random seeds. To avoid misinterpretation across scenarios with different mean TTE (hours), we report the distribution of **relative deviations** \(\Delta\)TTE(\%) from the mean.

![Figure Q3-8. Distribution of stochastic usage-induced variability in TTE (shown as ΔTTE%).](../figure.png)

*Figure Q3-8* shows that stochastic usage effects can produce non-negligible dispersion in predicted TTE, especially in scenarios where burstiness and state-dependent mechanisms (e.g., radio tail, interaction bursts) are prominent. This provides a quantitative explanation for the prompt’s “unpredictability” claim: even under the same high-level scenario, micro-level usage fluctuations can shift the time-to-empty by minutes.
