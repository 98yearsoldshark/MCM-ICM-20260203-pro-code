# English fragment (copy into paper)

## Q2.1 Time-to-Empty across scenarios and initial charge levels

Using the continuous-time SOC model developed in Section 4, we compute the **time-to-empty (TTE)** under a set of representative usage scenarios and multiple initial charge levels. Here, TTE is defined as the **first termination time** when any shutdown boundary is reached (Section 4.2.2): (i) undervoltage cutoff $V_{term}(t)\le V_{cut}$, (ii) energy depletion $SOC(t)\le SOC_{min}$, or (iii) power infeasibility $\Delta(t)<0$.

To reflect both parameter uncertainty and the inherent randomness of user/background activities, we use a Monte Carlo procedure: for each (scenario, $SOC_0$), we sample key uncertain parameters (e.g., $V_{cut}$, $\eta_{PMIC}$, scaling factors of component power) and simulate stochastic background wake-ups. Figure Q2-1 reports the **mean** TTE (hours) for each cell.

(Insert Figure Q2-1 here.)

Figure Q2-1: Mean TTE (hours) for different scenarios and initial charge levels.

Figure Q2-1 highlights two dominant patterns. First, usage scenarios create orders-of-magnitude differences: under full charge ($SOC_0=1.0$), the model predicts about **61.5 h** for standby/light background, **36.2 h** for a mixed “typical day”, **9.7 h** for video streaming, **7.2 h** for navigation (GPS + maps), and only **3.4 h** for gaming (high CPU/GPU). Second, decreasing initial charge shortens TTE approximately proportionally, but deviations from perfect linear scaling emerge because the shutdown event is triggered by voltage dynamics rather than SOC alone.
