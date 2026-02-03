# English fragment (copy into paper)

## Q2.2 Which conditions shorten TTE the most? (OAT condition toggles)

To identify **which conditions produce the greatest reductions in battery life**, we follow the “one-at-a-time (OAT)” protocol suggested in our theory notes: for each scenario, we keep the activity script fixed but toggle **one** condition $z$ at a time, while holding all other conditions at the baseline. We quantify the impact by
\[
Impact(z)=\frac{TTE(z)-TTE_0}{TTE_0},
\]
where $TTE_0$ is the baseline time-to-empty and negative values indicate shorter battery life.

The baseline is standardized to a constant room temperature ($T_{amb}=20^\circ$C) and we apply the same set of OAT toggles across all scenarios, so the x-axis has a unified meaning (no scenario-specific “variant names”). The tested conditions include: high brightness (forcing 500 nits during all screen-on segments), poor signal, switching to cellular (LTE), and cold/hot temperature as a **directional** contrast ($-15^\circ$C / $38^\circ$C).

Figure Q2-2 summarizes the results for $SOC_0=1.0$ in a matrix layout. Each cell reports the **relative change** $\Delta TTE/TTE_{baseline}$ (in %), so the largest reductions and the “surprisingly little” factors can be read directly.

(Insert Figure Q2-2 here.)

Figure Q2-2: Relative impact of condition variants on TTE (scenario × variant, $SOC_0=1.0$).

Across scenarios, the largest reductions are consistently associated with **network-related stressors** (e.g., switching to cellular, poor signal) and **low temperature**. Mechanistically, poor signal increases the energy per delivered data (higher TX power, retransmissions, and tail states), while low temperature increases internal resistance $R_0$, both accelerating terminal-voltage drop and triggering earlier undervoltage cutoff. In contrast, some single-factor changes can have surprisingly little impact when dominated by a larger power component (e.g., small brightness changes in compute-dominated gaming), which we quantify more explicitly in the “surprisingly little” section.
