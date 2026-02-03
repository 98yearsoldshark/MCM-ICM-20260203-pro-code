# English fragment (copy into paper)

In real smartphones, shutdown is triggered by a cut-off terminal voltage \(V_{\mathrm{cut}}\) rather than by \(\mathrm{SOC}=0\). Because the terminal voltage equals \(\mathrm{OCV}(\mathrm{SOC})\) minus internal drops (ohmic drop and polarization), a high current draw can cause an early under-voltage event even when the battery still contains substantial charge. This explains the user-perceived "sudden battery drop" phenomenon.

(Insert Figure Q1-07 here.)

Figure Q1-07: Remaining SOC at shutdown under the same cut-off voltage \(V_{\mathrm{cut}}=3.30\text{ V}\) across representative usage scenarios. The dashed line indicates the minimum SOC threshold used by Model-0; the gap above this line quantifies "inaccessible charge" caused by under-voltage rather than true depletion.

This result motivates a voltage-based stopping criterion in Model-1 and highlights why a purely SOC-threshold model can systematically overestimate time-to-empty (TTE) under heavy workloads.
