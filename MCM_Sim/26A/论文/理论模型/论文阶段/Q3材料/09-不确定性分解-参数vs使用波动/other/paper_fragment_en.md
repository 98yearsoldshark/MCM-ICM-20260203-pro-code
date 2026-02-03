<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.3 Fluctuations in Usage Patterns（Variance Decomposition） -->

## 7.3 Where Does “Unpredictability” Come From? Variance Decomposition

To distinguish variability caused by uncertain parameters (battery condition, calibration uncertainty, environment) from variability caused by usage fluctuations, we applied the **law of total variance** to our simulation outputs:
\[
\mathrm{Var}(TTE)=\mathrm{Var}\big(\mathbb{E}[TTE\mid \theta]\big)+\mathbb{E}\big[\mathrm{Var}(TTE\mid \theta)\big],
\]
where \(\theta\) denotes the set of “slow” parameters/states (capacity, resistances, SOH, and power scaling factors). The first term represents variability across parameter realizations, and the second term represents within-parameter variability induced by stochastic usage.

![Figure Q3-9. Variance decomposition of TTE: parameter/slow-state uncertainty vs. usage fluctuations.](../figure.png)

*Figure Q3-9* shows that, under wide priors, between-parameter uncertainty often dominates the total variance, while usage fluctuations can still contribute a measurable share, particularly in burst-heavy scenarios. Importantly, as the model becomes better calibrated (narrower priors), the relative contribution of usage fluctuations increases, aligning with the real-world perception that “two days of similar use” can still yield different battery outcomes.
