<!-- source: MinerU_markdown_3745533.3745748_20260126145107_2015678871962271744.md; mode: auto->bishe ; lines: 268-307 -->

# 3.1 Using analytic mathematics to determine solution stability

This study is based on the Lotka-Volterra model to simulate the stability of the ecosystem of lampreys (prey) and their predators under different sex ratios. The following is the analysis and explanation of the modeling process.

3.1.1 Model establishment. First, the parameters of the Lotka-Volterra model were defined. Through an iterative loop, the code simulated the dynamics of the ecosystem under different male ratios. These parameters represent the following ecological interactions:

(1) Natural growth rate of prey (alpha): It is the growth rate of the lamprey population. Here, it is set as a function of the male ratio (ii), subtracting a constant (0.15). Such a setting may imply that an increase in the male ratio will lead to an increase in the natural growth rate.

(2) Probability of prey being predated (beta): It remains constant, representing the rate at which predators consume prey.

(3) Natural mortality rate of predators (gamma): It remains constant.

(4) Predation success rate (delta): It describes the increased survival rate of predators due to preying on the prey.

The Lotka - Volterra equations are defined by the following pair of differential equations:

$$
\frac {d x}{d t} = \alpha x - \beta x y \tag {8}
$$

$$
\frac {d y}{d t} = \delta x y - \lambda y \tag {9}
$$

Among them,  $\mathbf{x}$  represents the number of prey (lampreys),  $\mathbf{y}$  represents the number of predators, and  $t$  represents time. This set of equations describes the changes in the numbers of prey and predators over time.

3.1.2 Simulation process. The ode45 numerical solver was used to simulate the changes in the populations of prey and predators under different sex ratios. In each iteration, initial conditions were set for both the prey and predators, and their population trajectories were simulated.

3.1.3 Stability analysis. ① By calculating the Jacobian matrix  $J$  and its eigenvalues, the code analyzed the stability of the system at the end of the simulation. The Jacobian matrix  $J$  represents the dynamic behavior of the system near a certain fixed point and is defined as:

$$
J = \left[ \begin{array}{c c} \alpha - \beta y & - \beta x \\ \delta y & \delta - \gamma \end{array} \right] \tag {10}
$$

At the final simulation state when  $t = 50$ , the Jacobian matrix is calculated using the numbers of prey  $x$  and predators  $y$  at the last time - point. The real parts of the eigenvalues represent the stability of the system near this point.

If the real parts of all eigenvalues are less than 0, the system is stable; if there are positive eigenvalues, the system is unstable.

② Solve for the stable and unstable points of the phase - trajectory curves of the nonlinear differential equations. In the phase plane, stable and unstable points are the key features of the trajectories. Stable points are usually the attractors of the trajectories, while unstable points are the repellers of the trajectories.

