<!-- Optional version: if you decide to replace/supplement the main Figure Q3-11 with the v2 set, you may paste this block into the Q3 section. -->

## 7.3 Observed Anchoring (Enhanced): usage×aging decomposition by power quantiles and robustness

In real usage, “intensity” is not constant: it fluctuates across low/medium/high loads. Meanwhile, aging-induced resistance growth pushes high-load operation closer to the undervoltage boundary. To present the **usage×aging interaction** in a reviewer-friendly way, we split AndroWatts phone\_tests into terciles by observed total power (low/medium/high) and perform the same variance decomposition within each group for the balanced (phone\_test × battery\_state) design.

![Figure Q3-11(v2). Variance-source decomposition (overall + by observed-power terciles).](./figure_v2_variance_decomposition_power_bins.png)

Each stacked bar decomposes TTE variability into four components: **usage main effect (phone\_test)**, **aging main effect (battery\_state)**, their **interaction**, and **stochasticity (seed)**. Overall, usage remains the dominant driver; however, under higher intensity, aging-related effects become more important in both proportion and risk interpretation. This provides a quantitative explanation of “same usage but faster drain / sudden shutdown”: high loads operate closer to the undervoltage boundary, where resistance/OCV changes amplify transient sags and trigger earlier cut-off.

To avoid the critique “the sensitivity result only holds for this particular sample,” we perform cluster bootstrap over phone\_tests and report 95% confidence intervals for the decomposition fractions.

![Figure Q3-11(v2b). Sampling uncertainty of the observed-anchored decomposition (Bootstrap 95% CI).](./figure_v2_variance_decomposition_bootstrap_ci.png)

We further emphasize a risk-facing interaction: even if TTE appears close to a proportional scaling, the **headroom margin** shows a stronger aging penalty under high observed power, connecting more directly to the “sudden drain/undervoltage” mechanism.

![Figure Q3-11(v2c). new vs eol: aging penalty on headroom margin (and TTE) vs usage intensity.](./figure_v2_aging_penalty_margin_vs_obs_power.png)

For readability in the main text, we compress the original 24×6 cells into a 3×6 heatmap (power tercile × aging level) and print mean TTE values in each cell.

![Figure Q3-11(v2d). Mean TTE across power-quantile × aging-level (compressed heatmap).](./figure_v2_tte_heatmap_power_bins_vs_aging.png)

Finally, to strengthen generalization, we repeat the same experiment on Cell01/Cell02/Cell03 (within the same battery dataset) and obtain a similar decomposition structure.

![Figure Q3-11(v2e). Cross-cell robustness (Cell01/02/03) of the observed-anchored decomposition.](./figure_v2_variance_decomposition_cells_compare.png)
