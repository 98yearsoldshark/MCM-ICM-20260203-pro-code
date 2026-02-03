# English fragment (copy into paper)

## Q2.11 Battery history (aging) as an additional driver of TTE variation

The problem statement emphasizes that a battery’s behavior is influenced by its history. To demonstrate how aging alters time-to-empty, we combine (i) representative smartphone load levels from AndroWatts and (ii) an open battery aging state table (SOH + OCV curve families). We treat each aging state as a physically grounded perturbation to the effective capacity and internal resistance, then simulate TTE using the same continuous-time battery model.

Figure Q2-11 shows the predicted TTE as a function of SOH for three representative load levels (light/medium/heavy).

(Insert Figure Q2-11 here.)

Figure Q2-11: Aging effect on battery life — TTE vs SOH under representative loads.

As expected, reduced SOH yields a nearly monotonic reduction in TTE. In our experiments, moving from “new” to “end-of-life” states reduces TTE by roughly 30% across loads, while heavy load remains consistently the fastest-draining regime. This provides an interpretable mechanism-level explanation of why two phones with similar usage may still exhibit different remaining time-to-empty depending on their battery health.
