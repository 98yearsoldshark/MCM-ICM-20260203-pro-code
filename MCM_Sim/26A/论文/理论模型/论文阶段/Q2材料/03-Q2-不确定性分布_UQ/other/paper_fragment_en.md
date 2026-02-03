# English fragment (copy into paper)

## Q2.3 Quantifying uncertainty in TTE predictions

Real smartphone battery behavior is uncertain because (i) several parameters are not fixed constants in practice (e.g., cutoff voltage policy, PMIC efficiency, effective capacity), and (ii) user/background activities introduce randomness even under the same “scenario label”. To quantify this uncertainty without violating the problem requirement of a continuous-time mechanism model, we propagate uncertainty through the ODE simulation using Monte Carlo sampling.

Figure Q2-3 shows the resulting **TTE distributions** for $SOC_0=1.0$ across scenarios. Each violin summarizes the simulated TTE samples; the red bar denotes the median, and the annotated bracket indicates the 5%–95% interval.

(Insert Figure Q2-3 here.)

Figure Q2-3: Distribution of TTE (SOC0=1.0) under Monte Carlo uncertainty propagation.

Two observations are noteworthy. First, scenarios dominated by sustained high load (e.g., gaming) exhibit relatively tight distributions: TTE is mainly determined by deterministic energy draw. Second, low-power long-duration scenarios (standby and mixed day) exhibit much wider spreads because rare background wake-ups and intermittent network tails accumulate over long horizons, making the remaining time-to-empty inherently more variable.
