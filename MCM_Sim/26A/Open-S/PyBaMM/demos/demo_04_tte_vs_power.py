"""
Demo 04：扫功率（W）得到 TTE（time-to-empty，放电到截止电压）。

这个 demo 对 26A 题很有用：
- 你可以把“策略 -> 平均功耗降低多少 W”映射到“续航提升多少小时”；
- 也可以用它生成“边际收益递减”的曲线，为论文的策略讨论提供支撑。

产物：
- outputs/demo_04_tte_vs_power.png
- outputs/demo_04_tte_vs_power.csv
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

    cutoff_v = 3.2
    powers_w = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    rows: list[tuple[float, float]] = []
    for p in powers_w:
        exp = pybamm.Experiment([f"Discharge at {p} W until {cutoff_v} V"])
        sol = pybamm.Simulation(model, parameter_values=params, experiment=exp).solve()
        tte_h = float(sol["Time [h]"].entries[-1])
        rows.append((p, tte_h))

    out = outputs_dir()
    csv_path = out / "demo_04_tte_vs_power.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["power_w", "tte_h"])
        w.writerows(rows)

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.plot([r[0] for r in rows], [r[1] for r in rows], marker="o")
    ax.set_xlabel("Power [W]")
    ax.set_ylabel("TTE [h] (until cutoff voltage)")
    ax.grid(True, alpha=0.25)
    ax.set_title(f"TTE vs Power (cutoff={cutoff_v:.1f} V, model=SPM, params=Chen2020)")

    savefig(out / "demo_04_tte_vs_power.png")
    plt.close(fig)

    print(
        "demo_04_tte_vs_power: ok | "
        f"wrote {csv_path.name} | "
        f"power range [{powers_w[0]}, {powers_w[-1]}] W"
    )


if __name__ == "__main__":
    main()

