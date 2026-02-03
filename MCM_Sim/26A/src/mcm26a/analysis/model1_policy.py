"""Model-1（ECM）策略/反事实评估：比较不同“用户行为/系统策略”对 TTE 的提升。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm26a.battery import BatteryParams1ECM
from mcm26a.power import PowerParams0
from mcm26a.scenarios import Scenario
from mcm26a.sim import SimResult1, simulate_model1_ecm


@dataclass(frozen=True)
class PolicyEffect1:
    """策略效果（相对 baseline）。"""

    action_id: str
    title_zh: str
    tte_h: float | None
    delta_tte_h: float | None
    delta_tte_pct: float | None
    status: str


@dataclass(frozen=True)
class PolicyAction1:
    """一个策略动作：对场景做可解释的变换。"""

    action_id: str
    title_zh: str
    description_zh: str
    apply: Callable[[Scenario], Scenario]


def evaluate_policies_model1(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams1ECM,
    soc0: float,
    actions: list[PolicyAction1],
    dt_s: float = 1.0,
) -> tuple[SimResult1, list[PolicyEffect1]]:
    """计算 baseline 以及每个 action 的 TTE 改善幅度（Model-1/ECM）。"""

    baseline = simulate_model1_ecm(
        scenario,
        power_params=power_params,
        battery_params=battery_params,
        soc0=soc0,
        variant=None,
        dt_s=dt_s,
    )

    effects: list[PolicyEffect1] = []
    for act in actions:
        sc2 = act.apply(scenario)
        res2 = simulate_model1_ecm(
            sc2,
            power_params=power_params,
            battery_params=battery_params,
            soc0=soc0,
            variant=act.action_id,
            dt_s=dt_s,
        )

        if baseline.tte_h is None or res2.tte_h is None:
            effects.append(
                PolicyEffect1(
                    action_id=act.action_id,
                    title_zh=act.title_zh,
                    tte_h=res2.tte_h,
                    delta_tte_h=None,
                    delta_tte_pct=None,
                    status=res2.status,
                )
            )
            continue

        delta_h = res2.tte_h - baseline.tte_h
        delta_pct = None if baseline.tte_h <= 0 else (delta_h / baseline.tte_h * 100.0)
        effects.append(
            PolicyEffect1(
                action_id=act.action_id,
                title_zh=act.title_zh,
                tte_h=res2.tte_h,
                delta_tte_h=delta_h,
                delta_tte_pct=delta_pct,
                status=res2.status,
            )
        )

    effects.sort(key=lambda e: (-1e18 if e.delta_tte_h is None else -e.delta_tte_h))
    return baseline, effects

