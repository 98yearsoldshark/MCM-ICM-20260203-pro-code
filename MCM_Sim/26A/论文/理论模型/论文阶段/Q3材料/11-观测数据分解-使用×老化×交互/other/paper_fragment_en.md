<!-- Suggested placement: Section 7 (Sensitivity and Assumptions / Q3) → 7.3 Fluctuations + Aging (Observed Data Anchoring) -->

## 7.3 Anchoring Fluctuations with Observed Data (Usage × Aging × Interaction)

The problem statement emphasizes **realistic usage conditions** and **battery history/aging**. To connect our mechanistic sensitivity results to observed variability, we used two open datasets: (i) an observed distribution of smartphone “usage states” (aggregated power summaries) and (ii) an open battery health state table (SOH/OCV). We then performed a balanced simulation design over (usage state \(\times\) aging state), with repeated seeds inside each cell, and decomposed the total variance in TTE into four components: usage main effect, aging main effect, their interaction, and stochastic residual.

![Figure Q3-11. Variance decomposition with observed inputs: usage vs aging vs interaction vs stochasticity.](../figure.png)

*Figure Q3-11* shows that usage-state variability explains most TTE variation, while aging contributes a smaller but non-negligible portion and can interact with usage intensity (high-power states are more sensitive to resistance growth and undervoltage). This yields a data-anchored interpretation of “unpredictability”: day-to-day outcomes are driven primarily by switching among usage states, with aging modulating risk and shortening TTE under demanding conditions.

To make the interaction term (usage×aging) more “paper-readable” (and to avoid overly crowded high-dimensional plots), we include five enhanced evidence pieces from the same observed-anchoring report (no extra assumptions needed):

**(a) Decomposition by observed power-intensity quantiles (low/medium/high load)**: we split phone\_tests into terciles by observed total power and repeat the same decomposition within each group, showing that the importance of aging changes with usage intensity.

![Figure Q3-11a. Variance decomposition by observed power quantiles (overall + low/medium/high).](./figure_v2_variance_decomposition_power_bins.png)

**(b) Sampling uncertainty (Bootstrap 95\% CI)**: we perform cluster bootstrap over phone\_tests and report 95\% confidence intervals for the decomposition fractions. The main ordering (usage dominates, aging is second, interaction is smaller) remains stable under resampling.

![Figure Q3-11b. Sampling uncertainty of the observed-anchored decomposition (Bootstrap 95\% CI).](./figure_v2_variance_decomposition_bootstrap_ci.png)

**(c) Interaction is clearer in a risk metric: \(\Delta\)margin vs observed power (new vs eol)**: mean TTE often scales close to proportionally, which may make the interaction look small in TTE-mean space. However, the **headroom margin** (more directly tied to “sudden shutdown”) exhibits a stronger aging penalty under high power, visualizing the “high-load × resistance growth” mechanism.

![Figure Q3-11c. new vs eol: aging penalty on headroom margin (and TTE) versus usage intensity.](./figure_v2_aging_penalty_margin_vs_obs_power.png)

**(d) Low-dimensional summary heatmap (3×6): power-quantile × aging-level**: we compress the original 24×6 cells into a 3×6 heatmap (low/medium/high power × six aging levels) with values printed in each cell, so the trend can be read quickly in the main text.

![Figure Q3-11d. Mean TTE across power-quantile × aging-level (compressed heatmap).](./figure_v2_tte_heatmap_power_bins_vs_aging.png)

**(e) Cross-cell robustness (Cell01/02/03)**: to avoid the critique “the conclusion only holds for one cell,” we repeat the experiment on Cell01/02/03 under the same battery dataset and obtain similar decomposition structures. This strengthens generalizability and credibility (often suitable for an appendix or a small supporting figure).

![Figure Q3-11e. Cross-cell robustness of the observed-anchored variance decomposition.](./figure_v2_variance_decomposition_cells_compare.png)
