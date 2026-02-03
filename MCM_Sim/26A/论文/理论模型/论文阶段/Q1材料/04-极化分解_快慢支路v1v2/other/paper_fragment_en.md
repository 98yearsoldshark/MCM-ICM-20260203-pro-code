# English fragment (copy into paper)

To reproduce both the sharp transient spikes and the long relaxation tails observed in real voltage traces, we use a second-order Thevenin equivalent circuit model (2RC ECM). The polarization voltage is decomposed into a fast branch \(v_1(t)\) (seconds-scale response) and a slow branch \(v_2(t)\) (minutes-to-hours-scale recovery). Their superposition produces a multi-time-scale internal drop that cannot be captured by a single RC branch.

(Insert Figure Q1-04 here.)

Figure Q1-04: Decomposition of polarization voltage into the fast branch \(v_1\) and the slow branch \(v_2\) on a CALCE Incremental OCV test. The fast branch responds immediately to current steps (spike-like behavior), while the slow branch accumulates and relaxes gradually, explaining the curved recovery toward each plateau.

This decomposition provides a mechanistic interpretation of the "spike + rebound + slow recovery" structure in Q1 and supports the use of a continuous-time ODE system with multiple internal states.
