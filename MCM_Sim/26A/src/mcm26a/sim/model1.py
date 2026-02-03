"""Model-1 端到端仿真：场景 -> 功耗 -> ECM 电池（含截止电压事件）-> TTE。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from mcm26a.battery.model1_ecm import BatteryParams1ECM, ECMState, ecm_derivatives
from mcm26a.battery.model1_ecm import solve_ecm_instantaneous
from mcm26a.power import PowerBreakdown, PowerParams0, compute_power_breakdown
from mcm26a.scenarios import Scenario
from mcm26a.utils import seconds_to_hours


@dataclass(frozen=True)
class SimResult1:
    """Model-1 仿真结果（用于与 Model-0 对比，以及论文展示）。"""

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
    min_headroom_margin: float


@dataclass(frozen=True)
class TraceResult1:
    """Model-1 轨迹结果：用于画 SOC/V(t)/功率随时间变化。"""

    scenario_id: str
    variant: str | None
    status: str
    t_s: list[float]
    soc: list[float]
    v1_V: list[float]
    i_A: list[float]
    ocv_V: list[float]
    v_term_V: list[float]
    p_W: list[float]
    p_max_W: list[float]
    discriminant: list[float]


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


def _rk4_step(state: ECMState, *, dt_s: float, p_W: float, params: BatteryParams1ECM) -> tuple[ECMState, float]:
    """对 (SOC, v1) 做一次 RK4；返回 (new_state, v_term_end)。"""

    dt = float(dt_s)

    def f(s: ECMState) -> tuple[float, float, float, bool]:
        d_soc, d_v1, out = ecm_derivatives(s, p_W=p_W, params=params)
        v_term = float("nan") if not out.discriminant_ok else float(out.V_term_V)
        return d_soc, d_v1, v_term, out.discriminant_ok

    k1_soc, k1_v1, v1_term, ok1 = f(state)
    if not ok1:
        return state, float("nan")

    s2 = ECMState(soc=state.soc + 0.5 * dt * k1_soc, v1_V=state.v1_V + 0.5 * dt * k1_v1)
    k2_soc, k2_v1, _, ok2 = f(s2)
    if not ok2:
        return state, float("nan")

    s3 = ECMState(soc=state.soc + 0.5 * dt * k2_soc, v1_V=state.v1_V + 0.5 * dt * k2_v1)
    k3_soc, k3_v1, _, ok3 = f(s3)
    if not ok3:
        return state, float("nan")

    s4 = ECMState(soc=state.soc + dt * k3_soc, v1_V=state.v1_V + dt * k3_v1)
    k4_soc, k4_v1, v4_term, ok4 = f(s4)
    if not ok4:
        return state, float("nan")

    new_soc = state.soc + (dt / 6.0) * (k1_soc + 2.0 * k2_soc + 2.0 * k3_soc + k4_soc)
    new_v1 = state.v1_V + (dt / 6.0) * (k1_v1 + 2.0 * k2_v1 + 2.0 * k3_v1 + k4_v1)

    # 数值上限制 SOC 在 [0,1]
    new_soc = min(1.0, max(0.0, float(new_soc)))
    return ECMState(soc=new_soc, v1_V=float(new_v1)), float(v4_term)


def simulate_model1_ecm(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams1ECM,
    soc0: float = 1.0,
    variant: str | None = None,
    dt_s: float = 1.0,
    max_steps: int = 20_000_000,
) -> SimResult1:
    """计算 Model-1（ECM）的 TTE：以截止电压为主要终止条件。"""

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    state = ECMState(soc=soc0, v1_V=0.0)
    t_s = 0.0
    # 归一化“功率闭合裕量”：margin = 1 - P/Pmax = disc/(V_eq^2)，越接近 0 越逼近电压崩塌边界。
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
        # 若总功耗为 0，直接返回
        if all(bd.total_w <= 0.0 for bd in seg_powers):
            return SimResult1(
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
        # 约定：power_model 具有 reset()/step()；参数由其内部持有。
        power_model.reset()

    steps = 0
    while True:
        seg_iter = zip(scenario.schedule, seg_powers) if seg_powers is not None else ((s, None) for s in scenario.schedule)
        for seg, bd0 in seg_iter:
            seg_left = float(seg.duration_s)

            # 段内用固定 dt 积分（为简洁起见，暂不自适应）
            while seg_left > 0.0:
                steps += 1
                if steps > max_steps:
                    return SimResult1(
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
                        avg_power_W=None,
                        energy_components_Wh=comp_wh,
                        min_headroom_margin=float(min_margin) if has_margin else float("nan"),
                    )

                dt = min(float(dt_s), seg_left)

                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=None)
                p_total = float(bd.total_w)

                # 记录“功率闭合裕量”（无量纲）：disc/(V_eq^2)
                # disc = (OCV - v1)^2 - 4*R0*P
                ocv = float(battery_params.ocv.ocv_v(state.soc))
                v_eq = float(ocv - state.v1_V)
                v_eq2 = float(v_eq * v_eq)
                r0 = float(battery_params.r0_ohm_at(state.soc))
                if r0 > 0.0 and v_eq2 > 1e-12:
                    disc = float(v_eq2 - 4.0 * r0 * max(0.0, p_total))
                    margin = float(disc / v_eq2)
                    if math.isfinite(margin):
                        has_margin = True
                        min_margin = min(float(min_margin), float(margin))

                # 终止条件：SOC 下限（兜底）
                if state.soc <= float(battery_params.soc_min):
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult1(
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

                # 对于 P=0 的段，SOC 不变，但 v1 会衰减（仍需积分）
                prev_state = state
                new_state, v_term_end = _rk4_step(state, dt_s=dt, p_W=p_total, params=battery_params)
                if math.isnan(v_term_end):
                    # 功率过大无法满足
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    # 已经失败：把裕量压到 <=0，便于后续敏感性分析把它识别为“电压崩塌边界”。
                    if has_margin:
                        min_margin = min(float(min_margin), -1e-12)
                    return SimResult1(
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

                # 判定是否触发截止电压
                if v_term_end <= float(battery_params.v_cut_V):
                    # 线性插值估计段内触发时刻（dt 足够小时效果很好）
                    # 用当前步的起点电压：用 solve_ecm_instantaneous 计算更一致（比 OCV-v1 近似更准确）。
                    out_start = solve_ecm_instantaneous(prev_state, p_W=p_total, params=battery_params)
                    v_start = float("nan") if not out_start.discriminant_ok else float(out_start.V_term_V)
                    v_end = v_term_end
                    if math.isnan(v_start) or v_start <= float(battery_params.v_cut_V):
                        dt_hit = 0.0
                    else:
                        denom = (v_start - v_end)
                        dt_hit = 0.0 if denom <= 1e-12 else dt * (v_start - float(battery_params.v_cut_V)) / denom
                        dt_hit = min(dt, max(0.0, dt_hit))

                    _accumulate_energy_components(comp_wh, bd, dt_hit)
                    t_s += dt_hit
                    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
                    return SimResult1(
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

                # 未触发，正常推进
                _accumulate_energy_components(comp_wh, bd, dt)
                t_s += dt
                seg_left -= dt
                state = new_state

        if not scenario.repeat:
            break

    avgp = None if t_s <= 0 else (sum(comp_wh.values()) / (t_s / 3600.0))
    return SimResult1(
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


def simulate_model1_ecm_trace(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    power_model: Any | None = None,
    battery_params: BatteryParams1ECM,
    soc0: float = 1.0,
    variant: str | None = None,
    dt_s: float = 2.0,
    max_steps: int = 2_000_000,
) -> TraceResult1:
    """生成 Model-1（ECM）的轨迹（不做图像保存，只返回数组）。

    约定：
    - 轨迹点记录在“步末”（t 增加 dt 后）的 SOC 与端电压 v_term。
    - 若触发 cutoff/soc_min，会在最后一个点结束。
    """

    soc0 = float(soc0)
    if soc0 < 0.0 or soc0 > 1.0:
        raise ValueError("soc0 must be within [0, 1]")

    state = ECMState(soc=soc0, v1_V=0.0)
    t_s = 0.0

    # 若未提供动态功耗模型，则预计算每段功耗（常值）；否则每个 dt 动态计算。
    seg_powers: list[PowerBreakdown] | None = None
    if power_model is None:
        seg_powers = [compute_power_breakdown(seg, power_params) for seg in scenario.schedule]
    else:
        power_model.reset()

    # 轨迹数组（含起点）
    if seg_powers is not None:
        p0 = float(seg_powers[0].total_w) if seg_powers else 0.0
    else:
        seg0 = scenario.schedule[0]
        # 这里需要一个“起点功率”用于画 t=0 的点，但不应真的推进显著时间。
        # 用极小 dt 近似 peek：Poisson(λ·dt) 基本为 0，且不会明显消耗尾态计时。
        bd0 = power_model.step(seg0, dt_s=1e-9, battery_temp_C=None)
        p0 = float(bd0.total_w)
    out0 = solve_ecm_instantaneous(state, p_W=p0, params=battery_params)

    ts = [0.0]
    socs = [float(state.soc)]
    v1s = [float(state.v1_V)]
    is_ = [float(out0.I_A) if out0.discriminant_ok else float("nan")]
    ocvs = [float(out0.OCV_V)]
    v_terms = [float(out0.V_term_V) if out0.discriminant_ok else float("nan")]
    ps = [float(p0)]
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
                    return TraceResult1(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        i_A=is_,
                        ocv_V=ocvs,
                        v_term_V=v_terms,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                dt = min(float(dt_s), seg_left)

                bd = bd0 if bd0 is not None else power_model.step(seg, dt_s=dt, battery_temp_C=None)
                p_total = float(bd.total_w)

                if state.soc <= float(battery_params.soc_min):
                    status = "soc_min"
                    return TraceResult1(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        i_A=is_,
                        ocv_V=ocvs,
                        v_term_V=v_terms,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                new_state, v_term_end = _rk4_step(state, dt_s=dt, p_W=p_total, params=battery_params)
                if math.isnan(v_term_end):
                    status = "insufficient_power"
                    return TraceResult1(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        i_A=is_,
                        ocv_V=ocvs,
                        v_term_V=v_terms,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

                t_s += dt
                seg_left -= dt
                state = new_state

                out = solve_ecm_instantaneous(state, p_W=p_total, params=battery_params)
                ts.append(float(t_s))
                socs.append(float(state.soc))
                v1s.append(float(state.v1_V))
                is_.append(float(out.I_A) if out.discriminant_ok else float("nan"))
                ocvs.append(float(out.OCV_V))
                v_terms.append(float(v_term_end))
                ps.append(float(p_total))
                pmax.append(float(out.p_max_W))
                discs.append(float(out.discriminant))

                if v_term_end <= float(battery_params.v_cut_V):
                    status = "cutoff"
                    return TraceResult1(
                        scenario_id=scenario.scenario_id,
                        variant=variant,
                        status=status,
                        t_s=ts,
                        soc=socs,
                        v1_V=v1s,
                        i_A=is_,
                        ocv_V=ocvs,
                        v_term_V=v_terms,
                        p_W=ps,
                        p_max_W=pmax,
                        discriminant=discs,
                    )

        if not scenario.repeat:
            break

    status = "completed"
    return TraceResult1(
        scenario_id=scenario.scenario_id,
        variant=variant,
        status=status,
        t_s=ts,
        soc=socs,
        v1_V=v1s,
        i_A=is_,
        ocv_V=ocvs,
        v_term_V=v_terms,
        p_W=ps,
        p_max_W=pmax,
        discriminant=discs,
    )
