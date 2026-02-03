"""Model-3 端到端仿真：场景 -> 功耗 -> 热-电耦合 ECM + 老化 -> TTE。

Model-3 的关键输出不止 TTE：
- 容量衰减（cap_loss_frac）
- 内阻增长（r0/r1 growth）
- 温度轨迹（T_end/T_peak）

用于论文叙事：
1) Model-1/2 解释“为什么当下会更快关机”；Model-3 解释“为什么越用越快关机”。
2) 可把策略从“只省电”升级为“省电 + 降温 + 延寿”。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from mcm26a.battery.model3_aging import (
    AgingECMState,
    BatteryParams3Aging,
    aging_ecm_derivatives,
    solve_aging_ecm_instantaneous,
)
from mcm26a.power import PowerBreakdown, PowerParams0, compute_power_breakdown
from mcm26a.scenarios import Scenario
from mcm26a.utils import seconds_to_hours


@dataclass(frozen=True)
class SimResult3:
    """Model-3 仿真结果。"""

    scenario_id: str
    variant: str | None
    soc0: float
    temp0_C: float
    cap_loss0_frac: float
    r0_growth0_frac: float
    r1_growth0_frac: float
    tte_s: float | None
    tte_h: float | None
    status: Literal["cutoff", "soc_min", "not_depleted", "no_drain", "insufficient_power"]
    v_cut_V: float
    v_end_V: float | None
    soc_end: float
    temp_end_C: float
    temp_peak_C: float
    cap_loss_end_frac: float
    r0_growth_end_frac: float
    r1_growth_end_frac: float
    energy_used_Wh: float
    avg_power_W: float | None
    energy_components_Wh: dict[str, float]
    min_headroom_margin: float


@dataclass(frozen=True)
class TraceResult3:
    """Model-3 轨迹结果：用于画 SOC/V/T/老化随时间变化（此处只返回数组）。"""

    scenario_id: str
    variant: str | None
    status: str
    t_s: list[float]
    soc: list[float]
    temp_C: list[float]
    v_term_V: list[float]
    cap_loss_frac: list[float]
    r0_growth_frac: list[float]
    p_W: list[float]


def _accumulate_energy_components(components_wh: dict[str, float], bd: PowerBreakdown, dt_s: float) -> None:
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
    state: AgingECMState,
    *,
    dt_s: float,
    p_W: float,
    ambient_temp_C: float,
    params: BatteryParams3Aging,
) -> tuple[AgingECMState, float]:
    """对 (SOC, v1, T, cap_loss, r0_growth, r1_growth) 做 RK4；返回 (new_state, v_term_end)。"""

    dt = float(dt_s)

    def f(s: AgingECMState) -> tuple[float, float, float, float, float, float, float, bool]:
        d_soc, d_v1, d_t, d_cap, d_r0, d_r1, out = aging_ecm_derivatives(
            s, p_W=p_W, ambient_temp_C=ambient_temp_C, params=params
        )
        v_term = float("nan") if not out.discriminant_ok else float(out.V_term_V)
        return float(d_soc), float(d_v1), float(d_t), float(d_cap), float(d_r0), float(d_r1), v_term, bool(
            out.discriminant_ok
        )

    k1_soc, k1_v1, k1_t, k1_cap, k1_r0, k1_r1, v1_term, ok1 = f(state)
    if not ok1:
        return state, float("nan")

    s2 = AgingECMState(
        soc=state.soc + 0.5 * dt * k1_soc,
        v1_V=state.v1_V + 0.5 * dt * k1_v1,
        temp_C=state.temp_C + 0.5 * dt * k1_t,
        cap_loss_frac=state.cap_loss_frac + 0.5 * dt * k1_cap,
        r0_growth_frac=state.r0_growth_frac + 0.5 * dt * k1_r0,
        r1_growth_frac=state.r1_growth_frac + 0.5 * dt * k1_r1,
    )
    k2_soc, k2_v1, k2_t, k2_cap, k2_r0, k2_r1, _, ok2 = f(s2)
    if not ok2:
        return state, float("nan")

    s3 = AgingECMState(
        soc=state.soc + 0.5 * dt * k2_soc,
        v1_V=state.v1_V + 0.5 * dt * k2_v1,
        temp_C=state.temp_C + 0.5 * dt * k2_t,
        cap_loss_frac=state.cap_loss_frac + 0.5 * dt * k2_cap,
        r0_growth_frac=state.r0_growth_frac + 0.5 * dt * k2_r0,
        r1_growth_frac=state.r1_growth_frac + 0.5 * dt * k2_r1,
    )
    k3_soc, k3_v1, k3_t, k3_cap, k3_r0, k3_r1, _, ok3 = f(s3)
    if not ok3:
        return state, float("nan")

    s4 = AgingECMState(
        soc=state.soc + dt * k3_soc,
        v1_V=state.v1_V + dt * k3_v1,
        temp_C=state.temp_C + dt * k3_t,
        cap_loss_frac=state.cap_loss_frac + dt * k3_cap,
        r0_growth_frac=state.r0_growth_frac + dt * k3_r0,
        r1_growth_frac=state.r1_growth_frac + dt * k3_r1,
    )
    k4_soc, k4_v1, k4_t, k4_cap, k4_r0, k4_r1, v4_term, ok4 = f(s4)
    if not ok4:
        return state, float("nan")

    new_soc = state.soc + (dt / 6.0) * (k1_soc + 2.0 * k2_soc + 2.0 * k3_soc + k4_soc)
    new_v1 = state.v1_V + (dt / 6.0) * (k1_v1 + 2.0 * k2_v1 + 2.0 * k3_v1 + k4_v1)
    new_t = state.temp_C + (dt / 6.0) * (k1_t + 2.0 * k2_t + 2.0 * k3_t + k4_t)
    new_cap = state.cap_loss_frac + (dt / 6.0) * (k1_cap + 2.0 * k2_cap + 2.0 * k3_cap + k4_cap)
    new_r0 = state.r0_growth_frac + (dt / 6.0) * (k1_r0 + 2.0 * k2_r0 + 2.0 * k3_r0 + k4_r0)
    new_r1 = state.r1_growth_frac + (dt / 6.0) * (k1_r1 + 2.0 * k2_r1 + 2.0 * k3_r1 + k4_r1)

    new_soc = min(1.0, max(0.0, float(new_soc)))
    new_t = params.clamp_temp_C(float(new_t))
    new_cap = min(float(params.cap_loss_max_frac), max(0.0, float(new_cap)))
    new_r0 = min(float(params.r_growth_max_frac), max(0.0, float(new_r0)))
    new_r1 = min(float(params.r_growth_max_frac), max(0.0, float(new_r1)))

    return (
        AgingECMState(
            soc=float(new_soc),
            v1_V=float(new_v1),
            temp_C=float(new_t),
            cap_loss_frac=float(new_cap),
            r0_growth_frac=float(new_r0),
            r1_growth_frac=float(new_r1),
        ),
        float(v4_term),
    )


def simulate_model3_aging(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams3Aging,
    soc0: float = 1.0,
    temp0_C: float | None = None,
    cap_loss0_frac: float = 0.0,
    r0_growth0_frac: float = 0.0,
    r1_growth0_frac: float = 0.0,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 20_000_000,
) -> SimResult3:
    """计算 Model-3（热-电耦合 + 老化）的 TTE：以截止电压为主要终止条件。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    t0 = float(battery_params.t0_C if temp0_C is None else temp0_C)
    state = AgingECMState(
        soc=soc0,
        v1_V=0.0,
        temp_C=float(t0),
        cap_loss_frac=float(cap_loss0_frac),
        r0_growth_frac=float(r0_growth0_frac),
        r1_growth_frac=float(r1_growth0_frac),
    )
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
            return SimResult3(
                scenario_id=scenario.scenario_id,
                variant=variant,
                soc0=soc0,
                temp0_C=float(state.temp_C),
                cap_loss0_frac=float(cap_loss0_frac),
                r0_growth0_frac=float(r0_growth0_frac),
                r1_growth0_frac=float(r1_growth0_frac),
                tte_s=None,
                tte_h=None,
                status="no_drain",
                v_cut_V=battery_params.v_cut_V,
                v_end_V=None,
                soc_end=state.soc,
                temp_end_C=float(state.temp_C),
                temp_peak_C=float(state.temp_C),
                cap_loss_end_frac=float(state.cap_loss_frac),
                r0_growth_end_frac=float(state.r0_growth_frac),
                r1_growth_end_frac=float(state.r1_growth_frac),
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
                    return SimResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        cap_loss0_frac=float(cap_loss0_frac),
                        r0_growth0_frac=float(r0_growth0_frac),
                        r1_growth0_frac=float(r1_growth0_frac),
                        tte_s=None,
                        tte_h=None,
                        status="not_depleted",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        cap_loss_end_frac=float(state.cap_loss_frac),
                        r0_growth_end_frac=float(state.r0_growth_frac),
                        r1_growth_end_frac=float(state.r1_growth_frac),
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
                r0 = float(
                    battery_params.effective_r0_ohm(soc=state.soc, temp_C=state.temp_C, r0_growth_frac=state.r0_growth_frac)
                )
                if r0 > 0.0 and v_eq2 > 1e-12:
                    disc = float(v_eq2 - 4.0 * r0 * max(0.0, p_total))
                    margin = float(disc / v_eq2)
                    if math.isfinite(margin):
                        has_margin = True
                        min_margin = min(float(min_margin), float(margin))

                if state.soc <= float(battery_params.soc_min):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        cap_loss0_frac=float(cap_loss0_frac),
                        r0_growth0_frac=float(r0_growth0_frac),
                        r1_growth0_frac=float(r1_growth0_frac),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="soc_min",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        cap_loss_end_frac=float(state.cap_loss_frac),
                        r0_growth_end_frac=float(state.r0_growth_frac),
                        r1_growth_end_frac=float(state.r1_growth_frac),
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
                    return SimResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        cap_loss0_frac=float(cap_loss0_frac),
                        r0_growth0_frac=float(r0_growth0_frac),
                        r1_growth0_frac=float(r1_growth0_frac),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="insufficient_power",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        temp_end_C=float(state.temp_C),
                        temp_peak_C=float(temp_peak),
                        cap_loss_end_frac=float(state.cap_loss_frac),
                        r0_growth_end_frac=float(state.r0_growth_frac),
                        r1_growth_end_frac=float(state.r1_growth_frac),
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else -1e-12,
                    )

                temp_peak = max(float(temp_peak), float(new_state.temp_C))

                if v_term_end <= float(battery_params.v_cut_V):
                    out_start = solve_aging_ecm_instantaneous(prev_state, p_W=p_total, params=battery_params)
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

                    soc_hit = float(prev_state.soc + (new_state.soc - prev_state.soc) * frac)
                    t_hit = float(prev_state.temp_C + (new_state.temp_C - prev_state.temp_C) * frac)
                    cap_hit = float(prev_state.cap_loss_frac + (new_state.cap_loss_frac - prev_state.cap_loss_frac) * frac)
                    r0_hit = float(prev_state.r0_growth_frac + (new_state.r0_growth_frac - prev_state.r0_growth_frac) * frac)
                    r1_hit = float(prev_state.r1_growth_frac + (new_state.r1_growth_frac - prev_state.r1_growth_frac) * frac)
                    temp_peak2 = max(float(temp_peak), t_hit)

                    return SimResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        temp0_C=float(t0),
                        cap_loss0_frac=float(cap_loss0_frac),
                        r0_growth0_frac=float(r0_growth0_frac),
                        r1_growth0_frac=float(r1_growth0_frac),
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="cutoff",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=float(battery_params.v_cut_V),
                        soc_end=float(soc_hit),
                        temp_end_C=float(t_hit),
                        temp_peak_C=float(temp_peak2),
                        cap_loss_end_frac=float(cap_hit),
                        r0_growth_end_frac=float(r0_hit),
                        r1_growth_end_frac=float(r1_hit),
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
    return SimResult3(
        scenario_id=scenario.scenario_id,
        variant=variant,
        soc0=soc0,
        temp0_C=float(t0),
        cap_loss0_frac=float(cap_loss0_frac),
        r0_growth0_frac=float(r0_growth0_frac),
        r1_growth0_frac=float(r1_growth0_frac),
        tte_s=None,
        tte_h=None,
        status="not_depleted",
        v_cut_V=battery_params.v_cut_V,
        v_end_V=None,
        soc_end=state.soc,
        temp_end_C=float(state.temp_C),
        temp_peak_C=float(temp_peak),
        cap_loss_end_frac=float(state.cap_loss_frac),
        r0_growth_end_frac=float(state.r0_growth_frac),
        r1_growth_end_frac=float(state.r1_growth_frac),
        energy_used_Wh=sum(comp_wh.values()),
        avg_power_W=avgp,
        energy_components_Wh=comp_wh,
        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
    )


def simulate_model3_aging_trace(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams3Aging,
    soc0: float = 1.0,
    temp0_C: float | None = None,
    cap_loss0_frac: float = 0.0,
    r0_growth0_frac: float = 0.0,
    r1_growth0_frac: float = 0.0,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 2_000_000,
) -> TraceResult3:
    """生成 Model-3 轨迹（不保存图，只返回数组）。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    t0 = float(battery_params.t0_C if temp0_C is None else temp0_C)
    state = AgingECMState(
        soc=soc0,
        v1_V=0.0,
        temp_C=float(t0),
        cap_loss_frac=float(cap_loss0_frac),
        r0_growth_frac=float(r0_growth0_frac),
        r1_growth_frac=float(r1_growth0_frac),
    )
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
    cap_losses = [float(state.cap_loss_frac)]
    r0_grows = [float(state.r0_growth_frac)]
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
                    return TraceResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        cap_loss_frac=cap_losses,
                        r0_growth_frac=r0_grows,
                        p_W=ps,
                    )

                dt = min(float(dt_s), seg_left)

                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=float(state.temp_C))
                p_total = float(bd.total_w)
                if state.soc <= float(battery_params.soc_min):
                    status = "soc_min"
                    return TraceResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        cap_loss_frac=cap_losses,
                        r0_growth_frac=r0_grows,
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
                    return TraceResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        cap_loss_frac=cap_losses,
                        r0_growth_frac=r0_grows,
                        p_W=ps,
                    )

                t_s += dt
                seg_left -= dt
                state = new_state

                ts.append(float(t_s))
                socs.append(float(state.soc))
                temps.append(float(state.temp_C))
                v_terms.append(float(v_term_end))
                cap_losses.append(float(state.cap_loss_frac))
                r0_grows.append(float(state.r0_growth_frac))
                ps.append(float(p_total))

                if v_term_end <= float(battery_params.v_cut_V):
                    status = "cutoff"
                    return TraceResult3(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        temp_C=temps,
                        v_term_V=v_terms,
                        cap_loss_frac=cap_losses,
                        r0_growth_frac=r0_grows,
                        p_W=ps,
                    )

        if not scenario.repeat:
            break

    status = "completed"
    return TraceResult3(
        scenario_id=scenario.scenario_id,
        variant=variant,
        status=status,
        t_s=ts,
        soc=socs,
        temp_C=temps,
        v_term_V=v_terms,
        cap_loss_frac=cap_losses,
        r0_growth_frac=r0_grows,
        p_W=ps,
    )
