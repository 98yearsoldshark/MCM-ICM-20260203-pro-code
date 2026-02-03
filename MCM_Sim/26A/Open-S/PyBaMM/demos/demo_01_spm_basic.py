"""
Demo 01：最小放电仿真（SPM，1C 放电至截止电压）。

产物：
- outputs/demo_01_spm_basic.png
- outputs/demo_01_spm_basic.csv
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

    # 1C 放电直到电压到达阈值（近似“关机”）
    experiment = pybamm.Experiment(["Discharge at 1C until 3.2 V"])

    sim = pybamm.Simulation(model, parameter_values=params, experiment=experiment)
    sol = sim.solve()

    t_h = sol["Time [h]"].entries
    v = sol["Terminal voltage [V]"].entries
    i_a = sol["Current [A]"].entries
    q_ah = sol["Discharge capacity [A.h]"].entries
    qn_ah = float(params["Nominal cell capacity [A.h]"])
    soc = 1.0 - (q_ah / qn_ah)

    out = outputs_dir()

    # 保存 CSV（便于后续接入别的分析管线）
    csv_path = out / "demo_01_spm_basic.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_h", "terminal_voltage_v", "current_a", "discharge_capacity_ah", "soc"])
        w.writerows(zip(t_h, v, i_a, q_ah, soc))

    # 画图：电压 + SOC（双轴）
    fig, ax1 = plt.subplots(figsize=(7.0, 3.6))
    ax1.plot(t_h, v, label="Terminal voltage [V]")
    ax1.set_xlabel("Time [h]")
    ax1.set_ylabel("Terminal voltage [V]")
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(t_h, soc, color="C1", label="SOC [-]")
    ax2.set_ylabel("SOC [-]")

    lines = ax1.get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="best")

    savefig(out / "demo_01_spm_basic.png")
    plt.close(fig)

    print(
        "demo_01_spm_basic: ok | "
        f"TTE={float(t_h[-1]):.3f} h | V_end={float(v[-1]):.3f} V | "
        f"wrote {csv_path.name}"
    )


if __name__ == "__main__":
    main()

