# English fragment (copy into paper)

## Q2.5 Identifying drivers of rapid battery drain (case-by-case)

To explain *why* TTE differs so dramatically across scenarios, we perform a component-level counterfactual analysis. For each scenario, we re-run the simulation while “removing” (zeroing) one power component at a time (screen, CPU/GPU, radio, GPS, background, etc.) and measure the change in TTE:
\[
\Delta TTE = TTE_{(-\text{component})} - TTE_{(\text{baseline})}.
\]
A large positive $\Delta TTE$ indicates that the removed component was a dominant driver of battery drain in that scenario; values near zero indicate surprisingly small influence.

(Insert Figure Q2-5 here.)

Figure Q2-5: Component-level drivers by scenario (mean ΔTTE, hours).

The matrix reveals distinct “driver signatures”. In gaming, **CPU/GPU front-end power** dominates, so removing compute load yields the largest TTE gains, while screen/network adjustments have comparatively minor effects. In navigation, a combination of **screen + radio + compute** contributes, consistent with simultaneous GPS/map rendering and continuous data exchange. In standby and mixed-day usage, **background wake-ups and baseline system power** become the main drivers because they persist over long horizons and repeatedly trigger short bursts and network tails.
