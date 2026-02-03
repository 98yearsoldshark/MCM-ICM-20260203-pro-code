# English fragment (copy into paper)

## Q2.14 Mechanistic explanation via trajectories (gaming)

Figure Q2-14 shows a representative trajectory under gaming (high CPU/GPU load) at $SOC_0=1.0$.

(Insert Figure Q2-14 here.)

Figure Q2-14: Example trajectories under gaming (SOC, terminal voltage, temperature, and total power).

Compared with standby, the SOC declines much faster because the sustained compute load dominates the power draw. The temperature rises quickly and reaches a higher steady level, reflecting the coupling between electrical losses and thermal dynamics. Importantly, the terminal voltage approaches the cutoff threshold much earlier, so shutdown is governed by the undervoltage boundary rather than gradual exhaustion. This illustrates why small increases in high-load power (e.g., due to background/network interaction) can cause disproportionate reductions in TTE.
