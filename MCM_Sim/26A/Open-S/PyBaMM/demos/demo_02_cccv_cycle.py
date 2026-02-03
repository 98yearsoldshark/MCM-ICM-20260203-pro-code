"""
Demo 02：CCCV 充放电循环（演示 Experiment 的常用写法）。

产物：
- outputs/demo_02_cccv_cycle.png
- outputs/demo_02_cccv_cycle.csv
"""

from __future__ import annotations

import csv

from _demo_utils import disable_pybamm_telemetry, outputs_dir, savefig


def main() -> None:
    disable_pybamm_telemetry()

    import matplotlib.pyplot as plt
    import pybamm

    model = pybamm.lithium_ion.SPM()
    params = pybamm.ParameterValues("Chen2020")

    experiment = pybamm.Experiment(
        [
            "Discharge at 1C for 20 minutes",
            "Rest for 5 minutes",
            "Charge at C/2 until 4.1 V",
            "Hold at 4.1 V until C/50",
        ]
    )

    sim = pybamm.Simulation(model, parameter_values=params, experiment=experiment)
    sol = sim.solve()

    t_h = sol["Time [h]"].entries
    v = sol["Terminal voltage [V]"].entries
    i_a = sol["Current [A]"].entries  # 放电为正，充电为负
    p_w = sol["Terminal power [W]"].entries

    out = outputs_dir()

    csv_path = out / "demo_02_cccv_cycle.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_h", "terminal_voltage_v", "current_a", "terminal_power_w"])
        w.writerows(zip(t_h, v, i_a, p_w))

    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(7.0, 5.0), sharex=True)
    ax1.plot(t_h, v, label="Terminal voltage [V]")
    ax1.set_ylabel("V [V]")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="best")

    ax2.plot(t_h, i_a, label="Current [A]")
    ax2.set_xlabel("Time [h]")
    ax2.set_ylabel("I [A]")
    ax2.grid(True, alpha=0.25)
    ax2.legend(loc="best")

    savefig(out / "demo_02_cccv_cycle.png")
    plt.close(fig)

    print(
        "demo_02_cccv_cycle: ok | "
        f"T_end={float(t_h[-1]):.3f} h | V_end={float(v[-1]):.3f} V | "
        f"wrote {csv_path.name}"
    )


if __name__ == "__main__":
    main()

