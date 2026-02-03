# Insertion Notes (delete in final paper)

- Suggested placement: Start of the Q2 ‘Time-to-Empty (TTE) predictions’ subsection, as the first overview figure.
- Purpose: Summarize mean TTE across multiple initial SOC levels and representative scenarios; serves as the entry point for later UQ/driver/validation figures.

# English Text (can be pasted)

## Q2.1 Time-to-Empty under different initial SOC levels and scenarios

Using our continuous-time SOC model, we estimate the time-to-empty (TTE) for several representative usage scenarios under multiple initial charge levels. We define TTE as the first time the system hits a shutdown boundary (e.g., undervoltage cutoff, SOC floor, or infeasible power demand).

To reflect both parameter uncertainty and stochastic background behavior, we perform Monte Carlo sampling for each (scenario, SOC0) setting and report the mean TTE (hours) in Fig. Q2-1. In the heatmap, the y-axis shows the initial SOC (SOC0) and the x-axis lists the scenarios.

(Insert Fig. Q2-1 here)

Fig. Q2-1. Mean time-to-empty (TTE, hours) by initial SOC × scenario.

At SOC0=1.0, our model predicts clear order-of-magnitude differences across activities: standby/light background ≈ 61.9 h, a typical mixed-use day ≈ 37.1 h, browsing/social media with frequent switching ≈ 10.5 h, video streaming ≈ 10.0 h, navigation (GPS+map) ≈ 7.5 h, and gaming (high CPU/GPU) ≈ 3.4 h. As SOC0 decreases, TTE shrinks approximately proportionally, but the scaling is not strictly linear because shutdown is often triggered by voltage dynamics (undervoltage cutoff) rather than SOC depletion alone.
