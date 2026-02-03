# English fragment (copy into paper)

As an additional stress test, we evaluate Model-1 on a CALCE "Initial capacity" experiment (10_16) that contains a much deeper transient under-voltage spike. This case challenges the model's ability to represent the spike entry, the immediate rebound, and the subsequent relaxation toward the next plateau.

(Insert Figure Q1-08 here.)

Figure Q1-08: Additional validation on CALCE 10_16 (extreme spike). Blue: measured terminal voltage; red: Model-1 prediction (2RC ECM). The dashed line is \(V_{\mathrm{cut}}=3.30\text{ V}\); vertical dotted lines indicate observed/predicted TTE defined by the first crossing of \(V_{\mathrm{cut}}\).

The model achieves an overall RMSE of 25.44 mV (MAE 18.54 mV) and a TTE error of −90.9 s (−0.459%). Most residuals are concentrated around the most extreme transient, suggesting that further improvements could be obtained by introducing a current-dependent polarization model; nevertheless, the proposed continuous-time mechanism model preserves the overall trajectory and depletion timing.

Optional (appendix): `figure_zoom.png` provides a local zoom around the deepest spike.
