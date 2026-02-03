"""
PyBaMM <-> MCM 26A 的轻量“接口层”（可复制到主代码库里用）。

目标：
- 把“手机功耗分段（W）”快速转成 PyBaMM 的 Experiment；
- 一行代码得到 TTE（time-to-empty，放电到截止电压）。

注意：
- 这里的电芯参数/模型是“代表性”而不是你的真实手机电池；
  若要做绝对预测，需要接入真实参数并做标定。
"""

from __future__ import annotations

from typing import Iterable, Sequence


def _normalize_power_segments(
    segments: Iterable[Sequence[object]],
) -> list[tuple[str, float, float]]:
    """
    允许多种输入格式，统一成 (name, power_w, duration_s)：
    - (power_w, duration_s)
    - (name, power_w, duration_s)
    """
    out: list[tuple[str, float, float]] = []
    for seg in segments:
        if len(seg) == 2:
            name = ""
            p_w, dt_s = seg
        elif len(seg) == 3:
            name, p_w, dt_s = seg
        else:
            raise ValueError(f"bad segment format: {seg!r} (expected len=2 or len=3)")
        out.append((str(name), float(p_w), float(dt_s)))
    return out


def build_experiment_from_power_segments(
    segments: Iterable[Sequence[object]],
    *,
    cutoff_v: float = 3.2,
    final_power_w: float | None = None,
) -> "pybamm.Experiment":
    """
    将分段功率曲线转换成 PyBaMM Experiment。

    参数：
    - segments: [(name?, power_w, duration_s), ...]
    - cutoff_v: 截止电压（到达后实验终止）
    - final_power_w: 若给定，则在所有分段跑完后追加一段
      `Discharge at final_power_w W until cutoff_v V`，用于自动算 TTE。
    """
    import pybamm

    segs = _normalize_power_segments(segments)
    steps: list[str] = [f"Discharge at {p_w} W for {dt_s} seconds" for _, p_w, dt_s in segs]
    if final_power_w is not None:
        steps.append(f"Discharge at {float(final_power_w)} W until {float(cutoff_v)} V")
    return pybamm.Experiment(steps)


def simulate_tte_hours_from_power_segments(
    segments: Iterable[Sequence[object]],
    *,
    model_name: str = "SPM",
    parameter_set: str = "Chen2020",
    cutoff_v: float = 3.2,
    final_power_w: float | None = None,
) -> float:
    """
    用 PyBaMM 计算“分段功率用电”的 TTE（单位：小时）。

    - model_name: "SPM"（快）或 "DFN"（慢但更细）
    - parameter_set: 例如 "Chen2020"
    """
    import pybamm

    pybamm.telemetry.disable()

    model_name_upper = model_name.strip().upper()
    if model_name_upper == "SPM":
        model = pybamm.lithium_ion.SPM()
    elif model_name_upper == "DFN":
        model = pybamm.lithium_ion.DFN()
    else:
        raise ValueError(f"unsupported model_name={model_name!r} (use 'SPM' or 'DFN')")

    params = pybamm.ParameterValues(parameter_set)
    experiment = build_experiment_from_power_segments(
        segments,
        cutoff_v=cutoff_v,
        final_power_w=final_power_w,
    )

    sol = pybamm.Simulation(model, parameter_values=params, experiment=experiment).solve()
    return float(sol["Time [h]"].entries[-1])

