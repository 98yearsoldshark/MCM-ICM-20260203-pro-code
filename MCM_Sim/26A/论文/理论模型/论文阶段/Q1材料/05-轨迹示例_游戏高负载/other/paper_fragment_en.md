# English fragment (copy into paper)

After parameterizing the battery-side model, we simulate the continuous-time evolution of the state variables under a representative smartphone workload. Figure Q1-05 illustrates a "Gaming" trace: SOC decreases as energy is consumed, the terminal voltage gradually drops due to both SOC decline and polarization, and the device shuts down once \(V_{\mathrm{term}}\) reaches the cut-off voltage \(V_{\mathrm{cut}}\).

(Insert Figure Q1-05 here.)

Figure Q1-05: Example continuous-time trajectory under a high CPU/GPU workload (gaming). From top to bottom: SOC(t), terminal voltage \(V_{\mathrm{term}}(t)\) with the cut-off line, and the admissible power budget \(P_{\max}(t)\) (headroom constraint). The coupled evolution provides a mechanistic time-to-empty (TTE) estimate.

This trajectory view connects the differential equations to user-visible outcomes and will be reused in Q2 to explain which factors drive rapid battery drain.
