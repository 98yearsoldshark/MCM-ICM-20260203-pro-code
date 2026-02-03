# English fragment (copy into paper)

## Q2.7 Comparison to observed behavior: short-time power measurements (AndroWatts)

The problem statement allows using open datasets to validate parameter plausibility and model behavior. To ensure that our load-side mechanism model operates at a realistic power scale, we validate it against **AndroWatts** (Zenodo), an open dataset that reports aggregated power measurements under many controlled smartphone tests.

For each test case, we map the recorded device state (screen brightness, CPU/GPU load proxies, radio mode, etc.) into our model inputs and compute the predicted mean power. Figure Q2-7 compares observed versus predicted total power.

(Insert Figure Q2-7 here.)

Figure Q2-7: AndroWatts validation — observed vs predicted total power (hexbin density).

The comparison shows strong agreement in magnitude and ranking (e.g., Pearson $r\approx0.91$ and MAE $\approx0.29$ W on the sampled cases). This supports that our scenario-based TTE predictions are grounded in plausible load power levels. Deviations at the high-power tail indicate where the load-side mapping is less accurate, which informs where the model may perform poorly under extreme usage.
