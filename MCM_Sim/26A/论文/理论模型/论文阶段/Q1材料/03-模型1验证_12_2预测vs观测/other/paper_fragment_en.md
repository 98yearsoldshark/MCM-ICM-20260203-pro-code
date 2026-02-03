# English fragment (copy into paper)

To further test robustness, we evaluate the same 2RC ECM structure on another Incremental OCV run from the same cell (12_2). This run contains a more extreme under-voltage spike near the depletion boundary, making it a stringent stress test for spike entry and rebound dynamics.

(Insert Figure Q1-03 here.)

Figure Q1-03: CALCE Incremental OCV validation (12_2). Blue: measured terminal voltage; red: Model-1 prediction (2RC ECM). The horizontal dashed line is \(V_{\mathrm{cut}}=3.30\text{ V}\); the vertical dotted lines indicate the observed and predicted TTE defined by the first crossing of \(V_{\mathrm{cut}}\).

Despite the sharper spike, the model still matches the plateau levels and the recovery trend, achieving an overall RMSE of 12.05 mV (MAE 8.06 mV) and a TTE error of −103.1 s (−0.162%). This confirms that multi-time-scale polarization states are essential near the cut-off regime, where voltage is highly sensitive to internal drops.

Optional (appendix): `figure_zoom.png` provides a local zoom around the deepest spike to inspect the curvature of entry/rebound.
