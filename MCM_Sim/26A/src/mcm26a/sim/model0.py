"""Model-0 端到端仿真：场景 -> 功耗 -> 能量/SOC -> TTE（耗尽时间）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerBreakdown, PowerParams0, compute_power_breakdown
from mcm26a.scenarios import Scenario
from mcm26a.utils import j_to_wh, seconds_to_hours, wh_to_j


@dataclass(frozen=True)
class SimResult0:
    """Model-0 仿真结果（面向分析/制表）。"""

    scenario_id: str
    variant: str | None
    soc0: float
    soc_min: float
    tte_s: float | None
    tte_h: float | None
    status: Literal["depleted", "not_depleted", "no_drain"]
    energy_capacity_Wh: float
    energy_used_Wh: float
    avg_power_W: float | None
    energy_components_Wh: dict[str, float]


def _accumulate_energy_components(components_j: dict[str, float], bd: PowerBreakdown, dt_s: float) -> None:
    # W*s = J
    components_j["base_j"] += bd.base_w * dt_s
    components_j["screen_j"] += bd.screen_w * dt_s
    components_j["cpu_j"] += bd.cpu_w * dt_s
    components_j["gpu_j"] += bd.gpu_w * dt_s
    components_j["radio_j"] += bd.radio_w * dt_s
    components_j["gps_j"] += bd.gps_w * dt_s
    components_j["background_j"] += bd.background_w * dt_s
    components_j["interaction_j"] += bd.interaction_w * dt_s
    components_j["other_j"] += bd.other_w * dt_s


def simulate_model0(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams0,
    soc0: float = 1.0,
    variant: str | None = None,
    max_cycles: int = 10_000,
) -> SimResult0:
    """在给定场景下计算 Model-0 的耗尽时间（TTE）。

    - 时间单位：秒（s）
    - 能量单位：焦耳（J）内部累计；对外输出 Wh
    """

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    e_max_j = wh_to_j(battery_params.energy_Wh)
    e_min_j = float(battery_params.soc_min) * e_max_j
    e_j = soc0 * e_max_j

    if e_j <= e_min_j:
        return SimResult0(
            scenario_id=scenario.scenario_id,
            variant=variant,
            soc0=soc0,
            soc_min=battery_params.soc_min,
            tte_s=0.0,
            tte_h=0.0,
            status="depleted",
            energy_capacity_Wh=battery_params.energy_Wh,
            energy_used_Wh=0.0,
            avg_power_W=0.0,
            energy_components_Wh={},
        )

    # 预计算一个 cycle 内每段的功耗与能耗（W 与 J）
    seg_powers: list[PowerBreakdown] = []
    seg_energy_j: list[float] = []
    for seg in scenario.schedule:
        bd = compute_power_breakdown(seg, power_params)
        seg_powers.append(bd)
        seg_energy_j.append(bd.total_w * float(seg.duration_s))

    e_cycle_j = sum(seg_energy_j)
    if e_cycle_j <= 0.0:
        # 场景没有耗电（或包含“充电”导致净能量不变/上升）
        return SimResult0(
            scenario_id=scenario.scenario_id,
            variant=variant,
            soc0=soc0,
            soc_min=battery_params.soc_min,
            tte_s=None,
            tte_h=None,
            status="no_drain",
            energy_capacity_Wh=battery_params.energy_Wh,
            energy_used_Wh=0.0,
            avg_power_W=0.0,
            energy_components_Wh={},
        )

    # 能量分解累计（J）
    comp_j = {
        "base_j": 0.0,
        "screen_j": 0.0,
        "cpu_j": 0.0,
        "gpu_j": 0.0,
        "radio_j": 0.0,
        "gps_j": 0.0,
        "background_j": 0.0,
        "interaction_j": 0.0,
        "other_j": 0.0,
    }

    t_s = 0.0

    # 若重复场景：先用“整周期”加速，避免待机场景循环次数过多。
    if scenario.repeat:
        e_avail_j = e_j - e_min_j
        n_full = int(e_avail_j // e_cycle_j)
        if n_full > 0:
            if n_full > max_cycles:
                n_full = max_cycles
            t_s += n_full * float(scenario.cycle_s)
            e_j -= n_full * e_cycle_j
            # 组件能耗也按周期线性累计
            for seg, bd in zip(scenario.schedule, seg_powers):
                _accumulate_energy_components(comp_j, bd, float(seg.duration_s) * n_full)

    # 在最后一个周期（或非重复场景的一次 schedule）里逐段推进直到耗尽或结束
    cycles_done = 0
    while True:
        cycles_done += 1
        if cycles_done > max_cycles and scenario.repeat:
            # 防止极端参数导致循环过久；这种情况下通常是 e_cycle_j 过小。
            break

        for seg, bd in zip(scenario.schedule, seg_powers):
            dt = float(seg.duration_s)
            p_total = bd.total_w
            if p_total <= 0.0:
                _accumulate_energy_components(comp_j, bd, dt)
                t_s += dt
                continue

            need = p_total * dt
            if e_j - need > e_min_j:
                # 整段未耗尽
                _accumulate_energy_components(comp_j, bd, dt)
                t_s += dt
                e_j -= need
                continue

            # 段内耗尽：解 (e_j - p*t = e_min) => t = (e_j - e_min)/p
            dt_partial = max(0.0, (e_j - e_min_j) / p_total)
            dt_partial = min(dt, dt_partial)
            _accumulate_energy_components(comp_j, bd, dt_partial)
            t_s += dt_partial
            e_j = e_min_j

            energy_used_wh = j_to_wh((soc0 * e_max_j) - e_j)
            energy_components_wh = {
                "base_Wh": j_to_wh(comp_j["base_j"]),
                "screen_Wh": j_to_wh(comp_j["screen_j"]),
                "cpu_Wh": j_to_wh(comp_j["cpu_j"]),
                "gpu_Wh": j_to_wh(comp_j["gpu_j"]),
                "radio_Wh": j_to_wh(comp_j["radio_j"]),
                "gps_Wh": j_to_wh(comp_j["gps_j"]),
                "background_Wh": j_to_wh(comp_j["background_j"]),
                "interaction_Wh": j_to_wh(comp_j["interaction_j"]),
                "other_Wh": j_to_wh(comp_j["other_j"]),
            }
            avg_power = None if t_s <= 0 else (wh_to_j(energy_used_wh) / t_s)
            return SimResult0(
                scenario_id=scenario.scenario_id,
                variant=variant,
                soc0=soc0,
                soc_min=battery_params.soc_min,
                tte_s=t_s,
                tte_h=seconds_to_hours(t_s),
                status="depleted",
                energy_capacity_Wh=battery_params.energy_Wh,
                energy_used_Wh=energy_used_wh,
                avg_power_W=avg_power,
                energy_components_Wh=energy_components_wh,
            )

        if not scenario.repeat:
            break

    # 未在 schedule 内耗尽（或被 max_cycles 截断）
    energy_used_wh = j_to_wh((soc0 * e_max_j) - e_j)
    energy_components_wh = {
        "base_Wh": j_to_wh(comp_j["base_j"]),
        "screen_Wh": j_to_wh(comp_j["screen_j"]),
        "cpu_Wh": j_to_wh(comp_j["cpu_j"]),
        "gpu_Wh": j_to_wh(comp_j["gpu_j"]),
        "radio_Wh": j_to_wh(comp_j["radio_j"]),
        "gps_Wh": j_to_wh(comp_j["gps_j"]),
        "background_Wh": j_to_wh(comp_j["background_j"]),
        "interaction_Wh": j_to_wh(comp_j["interaction_j"]),
        "other_Wh": j_to_wh(comp_j["other_j"]),
    }
    avg_power = None if t_s <= 0 else (wh_to_j(energy_used_wh) / t_s)
    return SimResult0(
        scenario_id=scenario.scenario_id,
        variant=variant,
        soc0=soc0,
        soc_min=battery_params.soc_min,
        tte_s=None,
        tte_h=None,
        status="not_depleted",
        energy_capacity_Wh=battery_params.energy_Wh,
        energy_used_Wh=energy_used_wh,
        avg_power_W=avg_power,
        energy_components_Wh=energy_components_wh,
    )
