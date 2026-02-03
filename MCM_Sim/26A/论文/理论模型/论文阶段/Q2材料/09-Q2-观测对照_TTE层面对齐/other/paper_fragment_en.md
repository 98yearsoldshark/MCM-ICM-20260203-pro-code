# English fragment (copy into paper)

## Q2.9 Comparison at the TTE level: an observed, reproducible proxy

Direct end-to-end discharge traces (from full battery to shutdown) are rarely available under an open license. To still provide a reproducible TTE-level comparison, we build an **observed TTE proxy** from SmartphoneMeasurements: Monsoon reports the mean power under controlled network tests, which we convert into an equivalent time-to-empty:
\[
TTE_{obs}^{equiv}=\frac{E_{batt}}{\bar{P}_{obs}}.
\]
Although this is not a full discharge experiment, it provides an open, documented, and repeatable reference point. We then construct a matching constant-condition scenario in our model and simulate until first termination.

Figure Q2-9 compares the model-predicted TTE against the observed proxy. Points above the dashed line indicate that the model predicts longer battery life than suggested by the measured mean power.

(Insert Figure Q2-9 here.)

Figure Q2-9: TTE-level comparison (SmartphoneMeasurements). x-axis: observed proxy TTE, y-axis: model TTE.

This comparison reveals that our model reproduces the qualitative ordering (baseline lasts longest; sustained network tests drain faster), while it tends to overestimate TTE under network-heavy settings. This identifies a clear improvement direction: the radio energy-per-data and/or tail-state power parameters likely remain conservative, especially under router/poor-signal regimes.
