# English fragment (copy into paper)

## Q2.10 Long-horizon plausibility: user-level daily energy statistics

To complement short-time laboratory measurements, we also compare our TTE predictions to a long-horizon, user-level dataset: **user\_behavior\_dataset.csv** reports average daily battery consumption (mAh/day) for a population of users. Because the dataset is aggregated by day rather than continuous traces, we convert the daily draw into a **daily-equivalent TTE**:
\[
TTE_{day}^{equiv} = \frac{C_{batt}}{\text{daily consumption}}\times 24\ \text{hours}.
\]
This enables a *plausible behavior* check at long time scales: whether our “mixed day” and “light standby” scenarios fall into reasonable **population percentiles**, rather than calibrating per-user SOC(t) trajectories.

Figure Q2-10 (main) combines two complementary views: the distribution of \(TTE_{day}^{equiv}\) (top) and the distribution of daily drain (mAh/day) (bottom). The top x-axis shows observed percentiles (0%–100%), and the legend reports each scenario’s empirical percentile (e.g., 12% indicates the lower 12% tail, i.e., heavier daily usage / shorter daily-equivalent TTE).

(Insert Figure Q2-10 here.)

Figure Q2-10: Long-horizon plausibility (daily) — population distributions vs scenario anchor points (with percentiles).

The scenario anchor points map to interpretable percentiles of real users: the “mixed day” corresponds to a heavier-than-typical day, while “light standby” is near the typical user level. The agreement in both the TTE domain and the drain domain provides a stronger plausibility argument that our daily scenarios are not arbitrarily chosen, even though the dataset does not provide continuous discharge trajectories.
