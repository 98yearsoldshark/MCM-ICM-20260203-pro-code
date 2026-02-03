"""
Demo 03：类“手机功耗”的分段功率（W）放电协议。

要点：
- 手机更像“功率负载”，因此这里用 W 控制更贴近现实；
- 将功耗曲线离散成分段常数功率，每段对应一个 Experiment step；
- 最后用 `until 3.2 V` 让仿真自然放到“关机”，得到 TTE。

产物：
- outputs/demo_03_phone_like_power_profile.png
- outputs/demo_03_phone_like_power_profile.csv
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

    # 用 “(场景名, 功率W, 持续秒)” 来描述一个简单手机使用过程
    segments = [
        ("Idle (screen off)", 1.0, 20 * 60),
        ("Social (screen on)", 2.5, 10 * 60),
        ("Video", 4.0, 15 * 60),
        ("Gaming (short burst)", 6.0, 5 * 60),
    ]

    steps: list[str] = []
    for _, p_w, dt_s in segments:
        steps.append(f"Discharge at {p_w} W for {dt_s} seconds")

    # 余下续航：假设回到中等负载，直至关机
    steps.append("Discharge at 2.5 W until 3.2 V")

    experiment = pybamm.Experiment(steps)

    sim = pybamm.Simulation(model, parameter_values=params, experiment=experiment)
    sol = sim.solve()

    t_h = sol["Time [h]"].entries
    v = sol["Terminal voltage [V]"].entries
    i_a = sol["Current [A]"].entries
    p_w = sol["Terminal power [W]"].entries

    out = outputs_dir()

    csv_path = out / "demo_03_phone_like_power_profile.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_h", "terminal_voltage_v", "current_a", "terminal_power_w"])
        w.writerows(zip(t_h, v, i_a, p_w))

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(7.0, 6.2), sharex=True)

    axes[0].plot(t_h, p_w, label="Terminal power [W]")
    axes[0].set_ylabel("P [W]")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="best")

    axes[1].plot(t_h, v, label="Terminal voltage [V]")
    axes[1].set_ylabel("V [V]")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="best")

    axes[2].plot(t_h, i_a, label="Current [A]")
    axes[2].set_xlabel("Time [h]")
    axes[2].set_ylabel("I [A]")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(loc="best")

    savefig(out / "demo_03_phone_like_power_profile.png")
    plt.close(fig)

    print(
        "demo_03_phone_like_power_profile: ok | "
        f"TTE={float(t_h[-1]):.3f} h | V_end={float(v[-1]):.3f} V | "
        f"wrote {csv_path.name}"
    )


if __name__ == "__main__":
    main()

