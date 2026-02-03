# English fragment (copy into paper)

## Q2.4 Where does the model perform well or poorly? (uncertainty as a diagnostic)

Beyond reporting uncertainty intervals, we use the **width of the 90% credible band** ($p95-p05$) as a diagnostic of where our model is intrinsically more reliable. A narrower band indicates that, under the same scenario definition, the TTE outcome is robust to plausible parameter variations and stochastic background processes; a wider band indicates a scenario in which small changes can accumulate and substantially alter the remaining time-to-empty.

Figure Q2-4 ranks scenarios by their uncertainty width at $SOC_0=1.0$.

(Insert Figure Q2-4 here.)

Figure Q2-4: Ranking of uncertainty width (p95−p05) across scenarios (SOC0=1.0).

The ranking suggests that the model is most robust for **short, high-load** regimes (e.g., gaming and navigation), where TTE is dominated by sustained energy draw and voltage cutoff. In contrast, **standby and mixed-day** regimes show the largest uncertainty, as infrequent background wake-ups and bursty communication tails can accumulate over long horizons, amplifying variability.
