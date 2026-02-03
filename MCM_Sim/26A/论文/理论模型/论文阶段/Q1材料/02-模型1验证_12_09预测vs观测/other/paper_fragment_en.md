# English fragment (copy into paper)

We validate the battery-side continuous-time model using the CALCE (UMD) Incremental OCV experiment for the SP20-1 cell. This protocol alternates current pulses and rest periods, producing the characteristic "stepwise plateaus + sharp spikes + relaxation recovery" voltage pattern. Given the measured current \(I(t)\), we simulate the 2RC ECM in continuous time and compare the predicted terminal voltage \(V_{\mathrm{pred}}(t)\) against the measured \(V(t)\).

(Insert Figure Q1-02 here.)

Figure Q1-02: CALCE Incremental OCV validation (12_09). Blue: measured terminal voltage; red: Model-1 prediction (2RC ECM). The horizontal dashed line is the cut-off voltage \(V_{\mathrm{cut}}=3.30\text{ V}\); the vertical dotted lines indicate the observed and predicted time-to-empty (TTE) defined by the first crossing of \(V_{\mathrm{cut}}\).

On this run, the model achieves an overall voltage RMSE of 8.38 mV (MAE 6.44 mV) and a TTE error of +75.8 s (+0.106%). The agreement holds both on plateau levels (captured by \(\mathrm{OCV}(\mathrm{SOC})\) and the slow branch) and on pulse minima (dominated by the ohmic drop and the fast branch), indicating that the multi-time-scale internal states are necessary for reproducing realistic discharge dynamics.

Optional (appendix): `figure_zoom.png` provides a local zoom around the deepest spike to assess the spike entry/rebound shape.
