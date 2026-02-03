# English fragment (copy into paper)

To align with the problem statement that battery life can vary drastically under seemingly similar usage, we summarize typical smartphone behavior into five representative scenarios (S1–S5). We then compute the time-to-empty (TTE) under two stopping rules:
- **Model-0 (SOC threshold)** terminates when \(SOC \le SOC_{\min}\), implicitly assuming all remaining charge is accessible;
- **Model-1 (voltage cut-off)** terminates when the terminal voltage first drops below \(V_{\mathrm{cut}}\), capturing internal voltage drops (ohmic and polarization) and thus early shutdown under high load.

Table Q1-06: Five representative usage scenarios (common vocabulary)

| Scenario | Typical behavior |
|---|---|
| S1 Standby / light use | Screen off or low brightness, low throughput, few background tasks |
| S2 Browsing / social | Frequent page loads and app switching, more background apps |
| S3 Video / streaming | Relatively steady load but long duration, large buffering |
| S4 Gaming | High CPU/GPU utilization, higher temperature |
| S5 Navigation / calls | Cellular-heavy, GPS always on, strong weak-signal penalty |

Figure Q1-06: Radar-chart comparison of TTE across S1–S5. Each vertex corresponds to one scenario, and the radius indicates TTE (hours). The blue polygon is Model-0 (SOC threshold), and the orange polygon is Model-1 (voltage cut-off). Semi-transparent fills highlight the differences between the two stopping rules.

The gap between the two polygons is typically larger in high-load scenarios (e.g., gaming and navigation), indicating that voltage sag can trigger early shutdown before the battery is truly depleted—consistent with the “sudden drop” user experience.
