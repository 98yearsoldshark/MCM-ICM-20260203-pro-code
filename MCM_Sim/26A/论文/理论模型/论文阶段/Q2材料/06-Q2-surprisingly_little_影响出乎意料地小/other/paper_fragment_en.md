# English fragment (copy into paper)

## Q2.6 Factors that change TTE surprisingly little

While drivers identify the dominant causes of rapid battery drain, the problem statement also asks which factors change the model **surprisingly little**. To make this claim falsifiable, we define a quantitative “little-effect band” for each scenario:
\[
|\Delta TTE| \le \max\bigl(\tau_{abs},\; \tau_{rel}\cdot TTE_{baseline}\bigr),
\]
where we use a conservative absolute threshold (e.g., $\tau_{abs}=0.25$ h) and a relative threshold (e.g., $\tau_{rel}=2\%$). Components whose counterfactual removal yields $\Delta TTE$ within this band are classified as “surprisingly little”.

(Insert Figure Q2-6 here.)

Figure Q2-6: Big vs little effects by scenario ($\Delta$TTE). The dashed line indicates the per-scenario “little-effect band”.

The results show that “surprisingly little” is scenario-dependent: in compute-dominated gaming, screen/network adjustments often have negligible impact compared with CPU/GPU load, whereas in long-horizon standby, the dominant factors shift toward baseline/background activity and network tails.
