"""Model-3（热-电耦合 + 老化）策略/反事实评估：比较策略对续航、温升与老化的影响。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0
from mcm26a.scenarios import Scenario
from mcm26a.sim import SimResult3, simulate_model3_aging


@dataclass(frozen=True)
class PolicyEffect3:
    """策略效果（相对 baseline）：同时输出续航/温升/老化变化。"""

    action_id: str
    title_zh: str
    tte_h: float | None
    delta_tte_h: float | None
    delta_tte_pct: float | None
    temp_peak_C: float | None
    delta_temp_peak_C: float | None
    cap_loss_end_frac: float | None
    delta_cap_loss_frac: float | None
    r0_growth_end_frac: float | None
    delta_r0_growth_frac: float | None
    status: str


@dataclass(frozen=True)
class PolicyAction3:
    """一个策略动作：对场景做可解释的变换。"""

    action_id: str
    title_zh: str
    description_zh: str
    apply: Callable[[Scenario], Scenario]


def evaluate_policies_model3(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams3Aging,
    soc0: float,
    temp0_C: float | None,
    cap_loss0_frac: float,
    r0_growth0_frac: float,
    r1_growth0_frac: float,
    actions: list[PolicyAction3],
    dt_s: float = 2.0,
) -> tuple[SimResult3, list[PolicyEffect3]]:
    """计算 baseline 以及每个 action 的影响（Model-3）。"""

    baseline = simulate_model3_aging(
        scenario,
        power_params=power_params,
        battery_params=battery_params,
        soc0=soc0,
        temp0_C=temp0_C,
        cap_loss0_frac=cap_loss0_frac,
        r0_growth0_frac=r0_growth0_frac,
        r1_growth0_frac=r1_growth0_frac,
        variant=None,
        dt_s=dt_s,
    )

    effects: list[PolicyEffect3] = []
    for act in actions:
        sc2 = act.apply(scenario)
        res2 = simulate_model3_aging(
            sc2,
            power_params=power_params,
            battery_params=battery_params,
            soc0=soc0,
            temp0_C=temp0_C,
            cap_loss0_frac=cap_loss0_frac,
            r0_growth0_frac=r0_growth0_frac,
            r1_growth0_frac=r1_growth0_frac,
            variant=act.action_id,
            dt_s=dt_s,
        )

        if baseline.tte_h is None or res2.tte_h is None:
            effects.append(
                PolicyEffect3(
                    action_id=act.action_id,
                    title_zh=act.title_zh,
                    tte_h=res2.tte_h,
                    delta_tte_h=None,
                    delta_tte_pct=None,
                    temp_peak_C=res2.temp_peak_C,
                    delta_temp_peak_C=None,
                    cap_loss_end_frac=res2.cap_loss_end_frac,
                    delta_cap_loss_frac=None,
                    r0_growth_end_frac=res2.r0_growth_end_frac,
                    delta_r0_growth_frac=None,
                    status=res2.status,
                )
            )
            continue

        delta_h = res2.tte_h - baseline.tte_h
        delta_pct = None if baseline.tte_h <= 0 else (delta_h / baseline.tte_h * 100.0)

        dtp = float(res2.temp_peak_C) - float(baseline.temp_peak_C)
        dcap = float(res2.cap_loss_end_frac) - float(baseline.cap_loss_end_frac)
        dr0 = float(res2.r0_growth_end_frac) - float(baseline.r0_growth_end_frac)

        effects.append(
            PolicyEffect3(
                action_id=act.action_id,
                title_zh=act.title_zh,
                tte_h=res2.tte_h,
                delta_tte_h=delta_h,
                delta_tte_pct=delta_pct,
                temp_peak_C=res2.temp_peak_C,
                delta_temp_peak_C=dtp,
                cap_loss_end_frac=res2.cap_loss_end_frac,
                delta_cap_loss_frac=dcap,
                r0_growth_end_frac=res2.r0_growth_end_frac,
                delta_r0_growth_frac=dr0,
                status=res2.status,
            )
        )

    # 排序：优先看续航提升，其次看“降温”（负更好），再看“减缓老化”（负更好）
    def _key(e: PolicyEffect3) -> tuple[float, float, float]:
        dtte = -1e18 if e.delta_tte_h is None else float(e.delta_tte_h)
        dtemp = 1e18 if e.delta_temp_peak_C is None else -float(e.delta_temp_peak_C)
        dcap = 1e18 if e.delta_cap_loss_frac is None else -float(e.delta_cap_loss_frac)
        return (dtte, dtemp, dcap)

    effects.sort(key=_key, reverse=True)
    return baseline, effects

