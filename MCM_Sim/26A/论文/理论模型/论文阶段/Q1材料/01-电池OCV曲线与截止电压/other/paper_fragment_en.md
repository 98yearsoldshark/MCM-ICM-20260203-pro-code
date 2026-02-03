# English fragment (copy into paper)

To close the battery-side ODE system, we introduce the open-circuit voltage (OCV) as a monotonic mapping from the state of charge (SOC) to voltage. In practice, OCV is obtained experimentally; here we use a piecewise-linear approximation that preserves monotonicity and supports stable inversion (e.g., estimating the initial SOC from a rest voltage).

(Insert Figure Q1-01 here.)

Figure Q1-01: Piecewise-linear OCV-SOC curve used in Model-1. The red dashed line marks the conservative discharge cut-off voltage \(V_{\mathrm{cut}}=3.30\text{ V}\) adopted by the smartphone shutdown logic.

With this mapping, the terminal voltage is computed as \(V_{\mathrm{term}}=\mathrm{OCV}(\mathrm{SOC})-\Delta V\), where \(\Delta V\) aggregates instantaneous ohmic drop and polarization voltages. This provides the voltage-based stopping criterion required by Q1 and enables a physics-consistent definition of time-to-empty (TTE).
