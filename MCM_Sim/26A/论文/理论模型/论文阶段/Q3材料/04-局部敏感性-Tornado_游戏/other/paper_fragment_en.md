<!-- 建议放置：论文第 7 节（Sensitivity and Assumptions / Q3）→ 7.1 Parameter Sensitivity（Local / Tornado） -->

## 7.1 Local Sensitivity (Tornado Chart)

In addition to global PRCC (which captures ranking under wide priors), we computed a **local, dimensionless sensitivity** around the calibrated baseline parameter set. Each parameter was perturbed by a small relative amount while holding the others fixed, and we recomputed mean TTE. This provides an interpretable “engineering” view of which parameters matter most near the operating point.

![Figure Q3-4. Local (dimensionless) sensitivity tornado chart for a representative scenario (Gaming).](../figure.png)

*Figure Q3-4* shows that parameters associated with battery capacity/SOH and dominant high-load components drive the largest local changes in TTE, while some secondary mechanisms have comparatively small marginal impact. Together with the PRCC results, this supports a robust conclusion: our predictions are most sensitive to a small set of physically meaningful parameters, and the ranking changes with scenario intensity.
