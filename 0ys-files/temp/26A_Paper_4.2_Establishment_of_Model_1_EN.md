## 4.2 Establishment of Model 1: A Continuous-Time Mechanistic Model with Power–Battery Coupling

To satisfy the requirement of an explicit **continuous-time** formulation, we construct a mechanistic model that couples smartphone power demand with lithium-ion battery electrical response. Usage signals are mapped to an instantaneous power demand \(P(t)\). The battery terminal voltage \(V_{\mathrm{term}}(t)\) and current \(I(t)\) are then determined by combining an equivalent-circuit model with a power-closure condition, which in turn yields the continuous-time evolution of \(\mathrm{SOC}(t)\). This structure captures key nonlinearities: as SOC decreases and the effective internal resistance increases, maintaining the same power demand requires larger current, amplifying ohmic losses and accelerating terminal-voltage decline.

We use seconds (s) as the time unit throughout; hours are used in plots only for readability (\(1\text{ h}=3600\text{ s}\)).

---

### 4.2.1 State Variables, External Inputs, and Framework

We define the continuous state variables and external inputs following the “power demand \(\rightarrow\) battery response \(\rightarrow\) SOC evolution” chain.

**(1) Continuous state variables** are chosen as
\[
x(t)=\big[\mathrm{SOC}(t),\,v_1(t)\big]^\top,
\]
where \(\mathrm{SOC}(t)\in[0,1]\) is the state of charge and \(v_1(t)\) is a first-order polarization (RC) voltage capturing voltage lag and rebound (recovery effect) under load transients.

**(2) External inputs** are observable or scenario-defined signals \(u(t)\), including screen status and brightness, CPU/GPU load, radio mode and network activity, signal quality, GPS switch, and background level. For tractability and numerical integration, we approximate \(u(t)\) as **piecewise constant** over short intervals \([t_k,t_{k+1})\), so that \(u(t)\equiv u_k\) and the resulting power demand \(P(t)\) is also piecewise constant.

This setting can be viewed as a continuous-time dynamical system driven by piecewise-constant exogenous inputs, which is consistent with the fact that smartphone subsystems switch among discrete operating modes while battery states evolve continuously.

We consider the initial-value problem with
\[
\mathrm{SOC}(0)=\mathrm{SOC}_0\in(0,1],\qquad v_1(0)=0,
\]
where \(v_1(0)=0\) corresponds to a rested cell with relaxed polarization. Parameters are assumed to satisfy \(R_0(\cdot)>0\), \(R_1(\cdot)>0\), and \(C_1>0\).

---

### 4.2.2 Device Power Demand \(P(t)\)

To keep the model interpretable and calibratable, we decompose the device power demand into physically meaningful components:
\[
P(t)=P_{\mathrm{base}}+P_{\mathrm{screen}}(t)+P_{\mathrm{cpu}}(t)+P_{\mathrm{gpu}}(t)+P_{\mathrm{radio}}(t)+P_{\mathrm{gps}}(t)+P_{\mathrm{bg}}(t)+P_{\mathrm{int}}(t).
\qquad (4.2\text{-}1)
\]

Here \(P_{\mathrm{int}}(t)\) is an interaction term that can capture selected “synergy” effects among subsystems (e.g., weak-signal cellular transfer amplifying radio power and increasing compute overhead). When such coupling is not explicitly modeled, we may set \(P_{\mathrm{int}}(t)\equiv 0\).

Within each piecewise-constant interval, representative functional forms include:

1) **Baseline power**:
\[
P_{\mathrm{base}}=\text{const}.
\]

2) **Screen power** (gated by screen-on indicator, approximately linear in brightness in nits):
\[
P_{\mathrm{screen}}(t)=\mathbf{1}_{\{\mathrm{screen\_on}\}} \left(P_{s0}+k_s\,B_{\mathrm{nits}}(t)\right).
\]

3) **CPU/GPU power** (linear in load fractions):
\[
P_{\mathrm{cpu}}(t)=k_{\mathrm{cpu}}\,u_{\mathrm{cpu}}(t),\qquad
P_{\mathrm{gpu}}(t)=k_{\mathrm{gpu}}\,u_{\mathrm{gpu}}(t),
\]
with \(u_{\mathrm{cpu}},u_{\mathrm{gpu}}\in[0,1]\).

4) **Radio power** (mode–activity level with a multiplicative weak-signal penalty):
\[
P_{\mathrm{radio}}(t)=P_{\mathrm{tbl}}\big(\mathrm{mode}(t),\mathrm{act}(t)\big)\cdot m_{\mathrm{sig}}\big(\mathrm{signal}(t)\big),
\qquad (4.2\text{-}2)
\]
where \(m_{\mathrm{sig}}>1\) under poor signal quality. This term captures a key real-world driver: high drain in cellular/weak-signal conditions even with light user interaction.

5) **GPS and background power** (switch/level mappings):
\[
P_{\mathrm{gps}}(t)=\mathbf{1}_{\{\mathrm{gps\_on}\}}P_g,\qquad
P_{\mathrm{bg}}(t)=P_{\mathrm{bg}}(\mathrm{level}(t)).
\]

This decomposition preserves interpretability: each term has a clear physical meaning and can be calibrated or perturbed in later analyses.

---

### 4.2.3 Battery Equivalent Circuit: First-Order Thevenin Model

Let discharge current be \(I(t)\ge 0\) (positive for discharge). The terminal voltage is modeled as
\[
V_{\mathrm{term}}(t)=V_{\mathrm{OCV}}(\mathrm{SOC}(t)) - I(t)\,R_0(\mathrm{SOC}(t)) - v_1(t),
\qquad (4.2\text{-}3)
\]
where \(V_{\mathrm{OCV}}(\cdot)\) is the open-circuit voltage (OCV–SOC curve) and \(R_0(\cdot)\) is the ohmic resistance. The polarization branch is described by
\[
\frac{dv_1}{dt}=-\frac{1}{R_1(\mathrm{SOC}(t))\,C_1}\,v_1(t)+\frac{1}{C_1}\,I(t).
\qquad (4.2\text{-}4)
\]

The OCV curve \(V_{\mathrm{OCV}}(\cdot)\) can be represented by a monotone function (e.g., a piecewise-linear approximation), and \(R_0(\cdot),R_1(\cdot)\) may be constants or SOC-dependent functions to reflect stronger voltage drop at low SOC. The polarization state \(v_1(t)\) allows the model to reproduce voltage rebound during rest intervals while keeping \(\mathrm{SOC}(t)\) strictly decreasing during discharge.

---

### 4.2.4 Power Closure and Current Determination

On short time scales, the smartphone is approximated as imposing a power demand \(P(t)\) (a constant-power-load approximation). We impose power closure
\[
P(t)=V_{\mathrm{term}}(t)\,I(t).
\qquad (4.2\text{-}5)
\]

Substituting (4.2-3) into (4.2-5) yields a quadratic equation in \(I(t)\):
\[
R_0(\mathrm{SOC})I^2-\big(V_{\mathrm{OCV}}(\mathrm{SOC})-v_1\big)I+P(t)=0,
\qquad (4.2\text{-}6)
\]
with discriminant
\[
\Delta(t)=\big(V_{\mathrm{OCV}}(\mathrm{SOC}(t))-v_1(t)\big)^2-4R_0(\mathrm{SOC}(t))P(t).
\qquad (4.2\text{-}7)
\]

When \(\Delta(t)\ge 0\), the physically consistent root (satisfying \(I\to 0\) as \(P\to 0\)) is
\[
I(t)=\frac{\big(V_{\mathrm{OCV}}(\mathrm{SOC}(t))-v_1(t)\big)-\sqrt{\Delta(t)}}{2R_0(\mathrm{SOC}(t))}.
\qquad (4.2\text{-}8)
\]

Equations (4.2-3)–(4.2-8) form a coupled system of differential equations with an algebraic constraint. On the feasible domain \(\Delta(t)\ge 0\), the algebraic relation (4.2-8) expresses \(I(t)\) as a function of \(\mathrm{SOC}(t)\), \(v_1(t)\), and \(P(t)\), yielding an explicit ODE system in \(\mathrm{SOC}(t)\) and \(v_1(t)\).

This structure implies an instantaneous **maximum deliverable power**:
\[
P_{\max}(t)=\frac{\big(V_{\mathrm{OCV}}(\mathrm{SOC}(t))-v_1(t)\big)^2}{4R_0(\mathrm{SOC}(t))}.
\qquad (4.2\text{-}9)
\]
If \(P(t)>P_{\max}(t)\), then \(\Delta(t)<0\) and no real current solution exists, indicating that the demanded power is infeasible at the current SOC and internal resistance. As discharge proceeds, \(V_{\mathrm{OCV}}\) typically decreases and \(R_0\) may increase, shrinking \(P_{\max}(t)\) and making the system more susceptible to voltage collapse under load spikes.

---

### 4.2.5 Charge Conservation: SOC Dynamics (with Rate-Capacity Effect)

Let the nominal capacity be \(C_{\mathrm{Ah}}\) (Ah), i.e., \(Q=3600\,C_{\mathrm{Ah}}\) (coulombs). Coulomb counting gives
\[
\frac{d\,\mathrm{SOC}}{dt}=-\frac{I(t)}{Q}.
\qquad (4.2\text{-}10)
\]

To capture the empirical rate-capacity effect with minimal complexity, we apply a current-dependent acceleration factor:
\[
\frac{d\,\mathrm{SOC}}{dt}=-\frac{I(t)}{Q}\Big(1+k_{\mathrm{rate}}\,I(t)\Big),\qquad k_{\mathrm{rate}}\ge 0.
\qquad (4.2\text{-}11)
\]
This is equivalent to using an effective capacity \(Q_{\mathrm{eff}}(I)=Q/(1+k_{\mathrm{rate}}I)\), making SOC deplete faster under heavier discharge.

---

### 4.2.6 Summary: A Closed Continuous-Time System

Model 1 consists of (i) the interpretable power-demand function \(P(t)\) in (4.2-1)–(4.2-2), (ii) the battery equivalent circuit and polarization dynamics in (4.2-3)–(4.2-4), and (iii) the power-closure current solution and SOC dynamics in (4.2-5)–(4.2-11). Given external inputs \(u(t)\), the model determines \(I(t)\), \(V_{\mathrm{term}}(t)\), and \(\mathrm{SOC}(t)\) in continuous time, providing a mechanistic foundation for subsequent scenario construction and parameter estimation.
