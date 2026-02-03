# English fragment (copy into paper)

## Q2.12 Evidence for early shutdown: remaining SOC at termination

A key reason that smartphone battery drain feels “unpredictable” is that shutdown is often triggered by **undervoltage protection** rather than true SOC depletion: the phone can power off while chemical charge remains. Our model explicitly captures this by using a cutoff-voltage termination boundary.

In the aging-state experiment, we record the SOC at the termination time. Figure Q2-12 shows the **remaining SOC at shutdown** as a function of SOH.

(Insert Figure Q2-12 here.)

Figure Q2-12: Early-shutdown evidence — SOC remaining at termination vs SOH.

The figure shows that under heavier loads and lower SOH, the system is more likely to hit the cutoff boundary earlier, leaving a larger fraction of SOC unused. This provides a mechanistic explanation for the common “battery drops suddenly” phenomenon: higher internal resistance and higher load amplify the $I R_0$ drop, pushing $V_{term}$ to $V_{cut}$ sooner even when SOC is not near zero.
