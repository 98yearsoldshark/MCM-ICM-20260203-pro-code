# English fragment (copy into paper)

## Q2.8 Plausibility check for network drain: energy per delivered data

Network activity is a common source of “unexpected” battery drain because its energy cost depends strongly on signal quality, protocol overhead, and tail states. To anchor the magnitude of our radio model, we use **SmartphoneMeasurements** (Monsoon power monitor + iPerf throughput logs), which provides open measurements of mean power during controlled Wi‑Fi experiments.

We compute the **energy per delivered data** (J/MB) from the measured incremental power and throughput. Figure Q2-8 compares Wi‑Fi via router vs Wi‑Fi Direct.

(Insert Figure Q2-8 here.)

Figure Q2-8: Observed network energy per MB (J/MB) from SmartphoneMeasurements.

This empirical range directly informs the parameter $e_{per\_MB}$ in our continuous-time radio model, where the data-dependent power is modeled as $P_{data}=e_{per\_MB}\cdot \dot{D}$ (with $\dot{D}$ in MB/s). The observed spread also motivates treating network drain as both scenario-dependent and uncertain rather than a fixed additive constant.
