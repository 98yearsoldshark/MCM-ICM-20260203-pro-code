"""Model-1（二阶极化）端到端仿真：场景 -> 功耗 -> 2RC ECM 电池（含截止电压事件）-> TTE。

设计动机（用于 Q3“假设检验/结构消融”）：
- 1RC ECM 往往只能用单一时间常数描述极化/恢复；
- 2RC ECM 允许“快+慢”两条极化支路，通常能更好刻画：
  - 高负载突发后的快速回弹 + 随后较慢回升；
  - 不同时间尺度下的电压松弛（relaxation）。

注意：
- 该模块仅用于“电池端结构假设”的对照，不引入热/老化（这些已由 Model-2/3 覆盖）。
- 时间单位统一用秒（s）；TTE 以小时（h）返回便于论文。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from mcm26a.battery.model1_ecm2rc import BatteryParams1ECM2RC, ECM2RCState, ecm2rc_derivatives, solve_ecm2rc_instantaneous
from mcm26a.power import PowerBreakdown, PowerParams0, compute_power_breakdown
from mcm26a.scenarios import Scenario
from mcm26a.utils import seconds_to_hours


@dataclass(frozen=True)
class SimResult1_2RC:
    """Model-1（2RC ECM）仿真结果。"""

    scenario_id: str
    variant: str | None
    soc0: float
    tte_s: float | None
    tte_h: float | None
    status: Literal["cutoff", "soc_min", "not_depleted", "no_drain", "insufficient_power"]
    v_cut_V: float
    v_end_V: float | None
    soc_end: float
    energy_used_Wh: float
    avg_power_W: float | None
    energy_components_Wh: dict[str, float]
    # 归一化功率闭合裕量：min_t[disc/(V_eq^2)] = min_t[1 - P/Pmax]
    min_headroom_margin: float


@dataclass(frozen=True)
class TraceResult1_2RC:
    """Model-1（2RC ECM）轨迹结果：用于画 SOC/V(t)/极化状态等。"""

    scenario_id: str
    variant: str | None
    status: str
    t_s: list[float]
    soc: list[float]
    v1_V: list[float]
    v2_V: list[float]
    v_term_V: list[float]
    i_A: list[float]
    ocv_V: list[float]
    p_W: list[float]
    p_max_W: list[float]
    discriminant: list[float]


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


def _rk4_step(state: ECM2RCState, *, dt_s: float, p_W: float, params: BatteryParams1ECM2RC) -> tuple[ECM2RCState, float]:
    """对 (SOC, v1, v2) 做一次 RK4；返回 (new_state, v_term_end)。

数值稳定性说明：
- 2RC 可能存在较快的时间常数（tau_fast），若 dt 远大于 tau_fast 会导致显著数值误差；
- 为避免在 Q3 里“步长改变导致结构对照失真”，这里做一个轻量的自适应子步长：
  当 dt > 0.5 * min(tau1, tau2) 时自动拆成多个子步。
"""

    dt_total = float(dt_s)
    if dt_total <= 0.0:
        out0 = solve_ecm2rc_instantaneous(state, p_W=p_W, params=params)
        v0 = float("nan") if not out0.discriminant_ok else float(out0.V_term_V)
        return state, float(v0)

    # 根据当前 SOC 的最小时间常数估算子步长（避免 dt >> tau_fast）
    r1 = float(params.r1_ohm_at(state.soc))
    r2 = float(params.r2_ohm_at(state.soc))
    tau1 = float(r1 * float(params.c1_F))
    tau2 = float(r2 * float(params.c2_F))
    tau_min = min(tau1, tau2)
    n_sub = 1
    if tau_min > 1e-9 and dt_total > 0.5 * tau_min:
        n_sub = int(math.ceil(dt_total / (0.5 * tau_min)))
        n_sub = max(1, min(1000, n_sub))
    dt = float(dt_total / n_sub)

    def f(s: ECM2RCState) -> tuple[float, float, float, float, bool]:
        d_soc, d_v1, d_v2, out = ecm2rc_derivatives(s, p_W=p_W, params=params)
        v_term = float("nan") if not out.discriminant_ok else float(out.V_term_V)
        return float(d_soc), float(d_v1), float(d_v2), v_term, bool(out.discriminant_ok)

    def step_once(s: ECM2RCState) -> tuple[ECM2RCState, float]:
        k1_soc, k1_v1, k1_v2, _, ok1 = f(s)
        if not ok1:
            return s, float("nan")

        s2 = ECM2RCState(
            soc=s.soc + 0.5 * dt * k1_soc,
            v1_V=s.v1_V + 0.5 * dt * k1_v1,
            v2_V=s.v2_V + 0.5 * dt * k1_v2,
        )
        k2_soc, k2_v1, k2_v2, _, ok2 = f(s2)
        if not ok2:
            return s, float("nan")

        s3 = ECM2RCState(
            soc=s.soc + 0.5 * dt * k2_soc,
            v1_V=s.v1_V + 0.5 * dt * k2_v1,
            v2_V=s.v2_V + 0.5 * dt * k2_v2,
        )
        k3_soc, k3_v1, k3_v2, _, ok3 = f(s3)
        if not ok3:
            return s, float("nan")

        s4 = ECM2RCState(
            soc=s.soc + dt * k3_soc,
            v1_V=s.v1_V + dt * k3_v1,
            v2_V=s.v2_V + dt * k3_v2,
        )
        k4_soc, k4_v1, k4_v2, v4_term, ok4 = f(s4)
        if not ok4:
            return s, float("nan")

        new_soc = s.soc + (dt / 6.0) * (k1_soc + 2.0 * k2_soc + 2.0 * k3_soc + k4_soc)
        new_v1 = s.v1_V + (dt / 6.0) * (k1_v1 + 2.0 * k2_v1 + 2.0 * k3_v1 + k4_v1)
        new_v2 = s.v2_V + (dt / 6.0) * (k1_v2 + 2.0 * k2_v2 + 2.0 * k3_v2 + k4_v2)

        new_soc = min(1.0, max(0.0, float(new_soc)))
        return ECM2RCState(soc=float(new_soc), v1_V=float(new_v1), v2_V=float(new_v2)), float(v4_term)

    cur = state
    v_term_end = float("nan")
    for _ in range(int(n_sub)):
        nxt, v_term_end = step_once(cur)
        if math.isnan(v_term_end):
            # 子步内出现不可行域：向上层报告 NaN（由上层决定如何终止）
            return state, float("nan")
        cur = nxt
    return cur, float(v_term_end)


def simulate_model1_ecm2rc(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams1ECM2RC,
    soc0: float = 1.0,
    variant: str | None = None,
    dt_s: float = 1.0,
    max_steps: int = 20_000_000,
) -> SimResult1_2RC:
    """计算 Model-1（2RC ECM）的 TTE：以截止电压为主要终止条件。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    state = ECM2RCState(soc=soc0, v1_V=0.0, v2_V=0.0)
    t_s = 0.0

    # 归一化“功率闭合裕量”：margin = disc/(V_eq^2)，越接近 0 越逼近电压崩塌边界。
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

    seg_powers: list[PowerBreakdown] | None = None
    if power_model is None:
        seg_powers = [compute_power_breakdown(seg, power_params) for seg in scenario.schedule]
        if all(bd.total_w <= 0.0 for bd in seg_powers):
            return SimResult1_2RC(
                scenario_id=scenario.scenario_id,
                variant=variant,
                soc0=soc0,
                tte_s=None,
                tte_h=None,
                status="no_drain",
                v_cut_V=battery_params.v_cut_V,
                v_end_V=None,
                soc_end=state.soc,
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

            while seg_left > 0.0:
                steps += 1
                if steps > max_steps:
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        tte_s=None,
                        tte_h=None,
                        status="not_depleted",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                dt = min(float(dt_s), seg_left)
                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=None)
                p_total = float(bd.total_w)

                # 记录 margin = disc/(V_eq^2)
                ocv = float(battery_params.ocv.ocv_v(state.soc))
                v_eq = float(ocv - state.v1_V - state.v2_V)
                v_eq2 = float(v_eq * v_eq)
                r0 = float(battery_params.r0_ohm_at(state.soc))
                if r0 > 0.0 and v_eq2 > 1e-12:
                    disc = float(v_eq2 - 4.0 * r0 * max(0.0, p_total))
                    margin = float(disc / v_eq2)
                    if math.isfinite(margin):
                        has_margin = True
                        min_margin = min(float(min_margin), float(margin))

                if state.soc <= float(battery_params.soc_min):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="soc_min",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                prev_state = state
                new_state, v_term_end = _rk4_step(state, dt_s=dt, p_W=p_total, params=battery_params)
                if math.isnan(v_term_end):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    if has_margin:
                        min_margin = min(float(min_margin), -1e-12)
                    return SimResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="insufficient_power",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=None,
                        soc_end=state.soc,
                        energy_used_Wh=sum(comp_wh.values()),
                        avg_power_W=avgp,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else -1e-12,
                    )

                if v_term_end <= float(battery_params.v_cut_V):
                    out_start = solve_ecm2rc_instantaneous(prev_state, p_W=p_total, params=battery_params)
                    v_start = float("nan") if not out_start.discriminant_ok else float(out_start.V_term_V)
                    v_end = float(v_term_end)
                    if math.isnan(v_start) or v_start <= float(battery_params.v_cut_V):
                        dt_hit = 0.0
                    else:
                        denom = (v_start - v_end)
                        dt_hit = 0.0 if denom <= 1e-12 else dt * (v_start - float(battery_params.v_cut_V)) / denom
                        dt_hit = min(dt, max(0.0, float(dt_hit)))

                    _accumulate_energy_components(comp_wh, bd, dt_hit)
                    t_s += dt_hit
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        soc0=soc0,
                        tte_s=t_s,
                        tte_h=seconds_to_hours(t_s),
                        status="cutoff",
                        v_cut_V=battery_params.v_cut_V,
                        v_end_V=float(battery_params.v_cut_V),
                        soc_end=new_state.soc,
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
    return SimResult1_2RC(
        scenario_id=scenario.scenario_id,
        variant=variant,
        soc0=soc0,
        tte_s=None,
        tte_h=None,
        status="not_depleted",
        v_cut_V=battery_params.v_cut_V,
        v_end_V=None,
        soc_end=state.soc,
        energy_used_Wh=sum(comp_wh.values()),
        avg_power_W=avgp,
        energy_components_Wh=comp_wh,
        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
    )


def simulate_model1_ecm2rc_trace(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams1ECM2RC,
    soc0: float = 1.0,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 2_000_000,
) -> TraceResult1_2RC:
    """生成 Model-1（2RC ECM）的轨迹（不保存图，只返回数组）。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    state = ECM2RCState(soc=soc0, v1_V=0.0, v2_V=0.0)
    t_s = 0.0

    seg_powers: list[PowerBreakdown] | None = None
    if power_model is None:
        seg_powers = [compute_power_breakdown(seg, power_params) for seg in scenario.schedule]
    else:
        power_model.reset()

    # 起点
    out0 = solve_ecm2rc_instantaneous(state, p_W=float(seg_powers[0].total_w) if seg_powers else 0.0, params=battery_params)
    ts = [0.0]
    socs = [float(state.soc)]
    v1s = [float(state.v1_V)]
    v2s = [float(state.v2_V)]
    ocvs = [float(out0.OCV_V)]
    vs = [float(out0.V_term_V) if out0.discriminant_ok else float("nan")]
    is_ = [float(out0.I_A) if out0.discriminant_ok else float("nan")]
    ps = [float(seg_powers[0].total_w) if seg_powers else 0.0]
    pmax = [float(out0.p_max_W)]
    discs = [float(out0.discriminant)]

    steps = 0
    status: str = "running"

    while True:
        seg_iter = zip(scenario.schedule, seg_powers) if seg_powers is not None else ((s, None) for s in scenario.schedule)
        for seg, bd0 in seg_iter:
            seg_left = float(seg.duration_s)
            while seg_left > 0.0:
                steps += 1
                if steps > max_steps:
                    status = "max_steps"
                    return TraceResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        v2_V=v2s,
                        v_term_V=vs,
                        i_A=is_,
                        ocv_V=ocvs,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                dt = min(float(dt_s), seg_left)
                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=None)
                p_total = float(bd.total_w)

                if state.soc <= float(battery_params.soc_min):
                    status = "soc_min"
                    return TraceResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        v2_V=v2s,
                        v_term_V=vs,
                        i_A=is_,
                        ocv_V=ocvs,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                prev_state = state
                new_state, v_term_end = _rk4_step(state, dt_s=dt, p_W=p_total, params=battery_params)
                if math.isnan(v_term_end):
                    status = "insufficient_power"
                    return TraceResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        v2_V=v2s,
                        v_term_V=vs,
                        i_A=is_,
                        ocv_V=ocvs,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                t_s += dt
                seg_left -= dt
                state = new_state

                out = solve_ecm2rc_instantaneous(state, p_W=p_total, params=battery_params)
                ts.append(float(t_s))
                socs.append(float(state.soc))
                v1s.append(float(state.v1_V))
                v2s.append(float(state.v2_V))
                ocvs.append(float(out.OCV_V))
                vs.append(float(out.V_term_V) if out.discriminant_ok else float("nan"))
                is_.append(float(out.I_A) if out.discriminant_ok else float("nan"))
                ps.append(float(p_total))
                pmax.append(float(out.p_max_W))
                discs.append(float(out.discriminant))

                if float(out.V_term_V) <= float(battery_params.v_cut_V):
                    status = "cutoff"
                    return TraceResult1_2RC(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        v2_V=v2s,
                        v_term_V=vs,
                        i_A=is_,
                        ocv_V=ocvs,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

        if not scenario.repeat:
            break

    status = "not_depleted"
    return TraceResult1_2RC(
        scenario_id=scenario.scenario_id,
        variant=variant,
        status=status,
        t_s=ts,
        soc=socs,
        v1_V=v1s,
        v2_V=v2s,
        v_term_V=vs,
        i_A=is_,
        ocv_V=ocvs,
        p_W=ps,
        p_max_W=pmax,
        discriminant=discs,
    )
