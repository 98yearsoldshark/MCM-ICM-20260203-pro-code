"""Model-2 端到端仿真：场景 -> 功耗 -> 热-电耦合 ECM（含截止电压事件）-> TTE。

核心增量（相对 Model-1）：
- 引入集总热模型：温度随时间变化；
- 温度影响内阻与有效容量，从而影响端电压与续航。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from mcm26a.battery.model2_thermal import (
    BatteryParams2Thermal,
    ThermalECMState,
    solve_thermal_ecm_instantaneous,
    thermal_ecm_derivatives,
)
from mcm26a.power import PowerBreakdown, PowerParams0, compute_power_breakdown
from mcm26a.scenarios import Scenario
from mcm26a.utils import seconds_to_hours


@dataclass(frozen=True)
class SimResult2:
    """Model-2 仿真结果：包含温度终态/峰值，用于解释热效应。"""

    scenario_id: str
    variant: str | None
    soc0: float
    temp0_C: float
    tte_s: float | None
    tte_h: float | None
    status: Literal["cutoff", "soc_min", "not_depleted", "no_drain", "insufficient_power"]
    v_cut_V: float
    v_end_V: float | None
    soc_end: float
    temp_end_C: float
    temp_peak_C: float
    energy_used_Wh: float
    avg_power_W: float | None
    energy_components_Wh: dict[str, float]
    min_headroom_margin: float


@dataclass(frozen=True)
class TraceResult2:
    """Model-2 轨迹结果：用于画 SOC/V(t)/T(t)/功率随时间变化。"""

    scenario_id: str
    variant: str | None
    status: str
    t_s: list[float]
    soc: list[float]
    temp_C: list[float]
    v_term_V: list[float]
    p_W: list[float]


def _accumulate_energy_components(components_wh: dict[str, float], bd: PowerBreakdown, dt_s: float) -> None:
    # W*s -> Wh
    dt_h = dt_s / 3600.0
    components_wh["base_Wh"] += bd.base_w * dt_h
    components_wh["screen_Wh"] += bd.screen_w * dt_h
    components_wh["cpu_Wh"] += bd.cpu_w * dt_h
    components_wh["gpu_Wh"] += bd.gpu_w * dt_h
    components_wh["radio_Wh"] += bd.radio_w * dt_h
    components_wh["gps_Wh"] += bd.gps_w * dt_h
    components_wh["background_Wh"] += bd.background_w * dt_h
    components_wh["interaction_Wh"] += bd.interaction_w * dt_h
    components_wh["other_Wh"] += bd.other_w * dt_h


def _rk4_step(
    state: ThermalECMState,
    *,
    dt_s: float,
    p_W: float,
    ambient_temp_C: float,
    params: BatteryParams2Thermal,
) -> tuple[ThermalECMState, float]:
    """对 (SOC, v1, T) 做一次 RK4；返回 (new_state, v_term_end)。"""

    dt = float(dt_s)

    def f(s: ThermalECMState) -> tuple[float, float, float, float, bool]:
        d_soc, d_v1, d_t, out = thermal_ecm_derivatives(s, p_W=p_W, ambient_temp_C=ambient_temp_C, params=params)
        v_term = float("nan") if not out.discriminant_ok else float(out.V_term_V)
        return float(d_soc), float(d_v1), float(d_t), v_term, bool(out.discriminant_ok)

    k1_soc, k1_v1, k1_t, v1_term, ok1 = f(state)
    if not ok1:
        return state, float("nan")

    s2 = ThermalECMState(
        soc=state.soc + 0.5 * dt * k1_soc,
        v1_V=state.v1_V + 0.5 * dt * k1_v1,
        temp_C=state.temp_C + 0.5 * dt * k1_t,
    )
    k2_soc, k2_v1, k2_t, _, ok2 = f(s2)
    if not ok2:
        return state, float("nan")

    s3 = ThermalECMState(
        soc=state.soc + 0.5 * dt * k2_soc,
        v1_V=state.v1_V + 0.5 * dt * k2_v1,
        temp_C=state.temp_C + 0.5 * dt * k2_t,
    )
    k3_soc, k3_v1, k3_t, _, ok3 = f(s3)
    if not ok3:
        return state, float("nan")

    s4 = ThermalECMState(
        soc=state.soc + dt * k3_soc,
        v1_V=state.v1_V + dt * k3_v1,
        temp_C=state.temp_C + dt * k3_t,
    )
    k4_soc, k4_v1, k4_t, v4_term, ok4 = f(s4)
    if not ok4:
        return state, float("nan")

    new_soc = state.soc + (dt / 6.0) * (k1_soc + 2.0 * k2_soc + 2.0 * k3_soc + k4_soc)
    new_v1 = state.v1_V + (dt / 6.0) * (k1_v1 + 2.0 * k2_v1 + 2.0 * k3_v1 + k4_v1)
    new_t = state.temp_C + (dt / 6.0) * (k1_t + 2.0 * k2_t + 2.0 * k3_t + k4_t)

    # 数值钳制
    new_soc = min(1.0, max(0.0, float(new_soc)))
    new_t = params.clamp_temp_C(float(new_t))
    return ThermalECMState(soc=float(new_soc), v1_V=float(new_v1), temp_C=float(new_t)), float(v4_term)


def simulate_model2_thermal(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams2Thermal,
    soc0: float = 1.0,
    temp0_C: float | None = None,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 20_000_000,
) -> SimResult2:
    """计算 Model-2（热-电耦合 ECM）的 TTE：以截止电压为主要终止条件。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    t0 = float(battery_params.t0_C if temp0_C is None else temp0_C)
    state = ThermalECMState(soc=soc0, v1_V=0.0, temp_C=float(t0))
    t_s = 0.0
    temp_peak = float(state.temp_C)
    # 归一化“功率闭合裕量”：margin = disc/(V_eq^2)，越接近 0 越逼近电压崩塌边界。
    # 用于 Q3：即使没触发 Δ<0（insufficient_power），也能衡量“离失败有多近”。
    min_margin = float("inf")
    has_margin = False

    comp_wh = {
        "base_Wh": 0.0,
        "screen_Wh": 0.0,
        "cpu_Wh": 0.0,
        "gpu_Wh": 0.0,
        "radio_Wh": 0.0,
        "gps_Wh": 0.0,
        "background_Wh": 0.0,
        "interaction_Wh": 0.0,
        "other_Wh": 0.0,
    }

    # 若未提供动态功耗模型，则预计算每段功耗（常值）；否则每个 dt 动态计算。
    seg_powers: list[PowerBreakdown] | None = None
    if power_model is None:
        seg_powers = [compute_power_breakdown(seg, power_params) for seg in scenario.schedule]
        if all(bd.total_w <= 0.0 for bd in seg_powers):
            return SimResult2(
                scenario_id=scenario.scenario_id,
                variant=variant,
                soc0=soc0,
                temp0_C=float(state.temp_C),
                tte_s=None,
                tte_h=None,
                status="no_drain",
                v_cut_V=battery_params.v_cut_V,
                v_end_V=None,
                soc_end=state.soc,
                temp_end_C=float(state.temp_C),
                temp_peak_C=float(state.temp_C),
                energy_used_Wh=0.0,
                avg_power_W=0.0,
                energy_components_Wh={},
                min_headroom_margin=float("nan"),
            )
    else:
        power_model.reset()

    steps = 0
    while True:
        seg_iter = zip(scenario.schedule, seg_powers) if seg_powers is not None else ((s, None) for s in scenario.schedule)
        for seg, bd0 in seg_iter:
            seg_left = float(seg.duration_s)
            t_amb = float(getattr(seg, "ambient_temp_c", battery_params.t_ref_C))

            while seg_left > 0.0:
                steps += 1
                if steps > max_steps:
                    return SimResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        tte_s=None,
                        tte_h=None,
                        status="not_depleted",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=None,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                dt = min(float(dt_s), seg_left)

                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=float(state.temp_C))
                p_total = float(bd.total_w)

                # 记录“功率闭合裕量”（无量纲）：disc/(V_eq^2)
                ocv = float(battery_params.ocv.ocv_v(state.soc))
                v_eq = float(ocv - state.v1_V)
                v_eq2 = float(v_eq * v_eq)
                r0 = float(battery_params.effective_r0_ohm(soc=state.soc, temp_C=state.temp_C))
                if r0 > 0.0 and v_eq2 > 1e-12:
                    disc = float(v_eq2 - 4.0 * r0 * max(0.0, p_total))
                    margin = float(disc / v_eq2)
                    if math.isfinite(margin):
                        has_margin = True
                        min_margin = min(float(min_margin), float(margin))

                if state.soc <= float(battery_params.soc_min):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="soc_min",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                prev_state = state
                new_state, v_term_end = _rk4_step(
                    state,
                    dt_s=dt,
                    p_W=p_total,
                    ambient_temp_C=t_amb,
                    params=battery_params,
                )
                if math.isnan(v_term_end):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    if has_margin:
                        min_margin = min(float(min_margin), -1e-12)
                    return SimResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="insufficient_power",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else -1e-12,
                    )

                temp_peak = max(float(temp_peak), float(new_state.temp_C))

                if v_term_end <= float(battery_params.v_cut_V):
                    # 段内命中 cutoff：线性插值估计触发时刻
                    out_start = solve_thermal_ecm_instantaneous(prev_state, p_W=p_total, params=battery_params)
                    v_start = float("nan") if not out_start.discriminant_ok else float(out_start.V_term_V)
                    v_end = float(v_term_end)

                    if math.isnan(v_start) or v_start <= float(battery_params.v_cut_V):
                        frac = 0.0
                        dt_hit = 0.0
                    else:
                        denom = (v_start - v_end)
                        dt_hit = 0.0 if denom <= 1e-12 else dt * (v_start - float(battery_params.v_cut_V)) / denom
                        dt_hit = min(dt, max(0.0, float(dt_hit)))
                        frac = 0.0 if dt <= 1e-12 else (dt_hit / dt)

                    _accumulate_energy_components(comp_wh, bd, dt_hit)
                    t_s += dt_hit
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))

                    # 用线性插值估计命中时刻的 SOC/温度（dt 足够小则误差很小）
                    soc_hit = float(prev_state.soc + (new_state.soc - prev_state.soc) * frac)
                    t_hit = float(prev_state.temp_C + (new_state.temp_C - prev_state.temp_C) * frac)
                    temp_peak2 = max(float(temp_peak), t_hit)

                    return SimResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="cutoff",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=float(battery_params.v_cut_V),
                        soc_end=float(soc_hit),
                        temp_end_C=float(t_hit),
                        temp_peak_C=float(temp_peak2),
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                _accumulate_energy_components(comp_wh, bd, dt)
                t_s += dt
                seg_left -= dt
                state = new_state

        if not scenario.repeat:
            break

    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
    return SimResult2(
        scenario_id=scenario.scenario_id,
        variant=variant,
        soc0=soc0,
        temp0_C=float(t0),
        tte_s=None,
        tte_h=None,
        status="not_depleted",
        v_cut_V=battery_params.v_cut_V,
        v_end_V=None,
        soc_end=state.soc,
        temp_end_C=float(state.temp_C),
        temp_peak_C=float(temp_peak),
        energy_used_Wh=sum(comp_wh.values()),
        avg_power_W=avgp,
        energy_components_Wh=comp_wh,
        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
    )


def simulate_model2_thermal_trace(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams2Thermal,
    soc0: float = 1.0,
    temp0_C: float | None = None,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 2_000_000,
) -> TraceResult2:
    """生成 Model-2 轨迹（不保存图，只返回数组）。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    t0 = float(battery_params.t0_C if temp0_C is None else temp0_C)
    state = ThermalECMState(soc=soc0, v1_V=0.0, temp_C=float(t0))
    t_s = 0.0

    seg_powers: list[PowerBreakdown] | None = None
    if power_model is None:
        seg_powers = [compute_power_breakdown(seg, power_params) for seg in scenario.schedule]
    else:
        power_model.reset()

    ts = [0.0]
    socs = [float(state.soc)]
    temps = [float(state.temp_C)]
    v_terms = [float(battery_params.ocv.ocv_v(state.soc))]
    if seg_powers is not None:
        ps = [float(seg_powers[0].total_w) if seg_powers else 0.0]
    else:
        bd0 = power_model.step(scenario.schedule[0], dt_s=1e-9, battery_temp_C=float(state.temp_C))
        ps = [float(bd0.total_w)]

    steps = 0
    status: str = "running"

    while True:
        seg_iter = zip(scenario.schedule, seg_powers) if seg_powers is not None else ((s, None) for s in scenario.schedule)
        for seg, bd0 in seg_iter:
            seg_left = float(seg.duration_s)
            t_amb = float(getattr(seg, "ambient_temp_c", battery_params.t_ref_C))

            while seg_left > 0.0:
                steps += 1
                if steps > max_steps:
                    status = "max_steps"
                    return TraceResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        p_W=ps,
                    )

                dt = min(float(dt_s), seg_left)

                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=float(state.temp_C))
                p_total = float(bd.total_w)

                if state.soc <= float(battery_params.soc_min):
                    status = "soc_min"
                    return TraceResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        p_W=ps,
                    )

                new_state, v_term_end = _rk4_step(
                    state,
                    dt_s=dt,
                    p_W=p_total,
                    ambient_temp_C=t_amb,
                    params=battery_params,
                )
                if math.isnan(v_term_end):
                    status = "insufficient_power"
                    return TraceResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        p_W=ps,
                    )

                t_s += dt
                seg_left -= dt
                state = new_state

                ts.append(float(t_s))
                socs.append(float(state.soc))
                temps.append(float(state.temp_C))
                v_terms.append(float(v_term_end))
                ps.append(float(p_total))

                if v_term_end <= float(battery_params.v_cut_V):
                    status = "cutoff"
                    return TraceResult2(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        p_W=ps,
                    )

        if not scenario.repeat:
            break

    status = "completed"
    return TraceResult2(
        scenario_id=scenario.scenario_id,
        variant=variant,
        status=status,
        t_s=ts,
        soc=socs,
        temp_C=temps,
        v_term_V=v_terms,
        p_W=ps,
    )
