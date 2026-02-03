"""Model-0 策略/反事实评估：比较不同“用户行为/系统策略”对 TTE 的提升。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm26a.battery import BatteryParams0
from mcm26a.power import PowerParams0
from mcm26a.scenarios import Scenario
from mcm26a.sim import SimResult0, simulate_model0


@dataclass(frozen=True)
class PolicyAction:
    """一个策略动作：对场景做可解释的变换。"""

    action_id: str
    title_zh: str
    description_zh: str
    apply: Callable[[Scenario], Scenario]


@dataclass(frozen=True)
class PolicyEffect0:
    """策略效果（相对 baseline）。"""

    action_id: str
    title_zh: str
    tte_h: float | None
    delta_tte_h: float | None
    delta_tte_pct: float | None


def evaluate_policies_model0(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams0,
    soc0: float,
    actions: list[PolicyAction],
) -> tuple[SimResult0, list[PolicyEffect0]]:
    """计算 baseline 以及每个 action 的 TTE 改善幅度。"""

    baseline = simulate_model0(
        scenario,
        power_params=power_params,
        battery_params=battery_params,
        soc0=soc0,
        variant=None,
    )

    effects: list[PolicyEffect0] = []
    for act in actions:
        sc2 = act.apply(scenario)
        res2 = simulate_model0(
            sc2,
            power_params=power_params,
            battery_params=battery_params,
            soc0=soc0,
            variant=act.action_id,
        )

        if baseline.tte_h is None or res2.tte_h is None:
            effects.append(
                PolicyEffect0(
                    action_id=act.action_id,
                    title_zh=act.title_zh,
                    tte_h=res2.tte_h,
                    delta_tte_h=None,
                    delta_tte_pct=None,
                )
            )
            continue

        delta_h = res2.tte_h - baseline.tte_h
        delta_pct = None if baseline.tte_h <= 0 else (delta_h / baseline.tte_h * 100.0)
        effects.append(
            PolicyEffect0(
                action_id=act.action_id,
                title_zh=act.title_zh,
                tte_h=res2.tte_h,
                delta_tte_h=delta_h,
                delta_tte_pct=delta_pct,
            )
        )

    # 默认按提升幅度从大到小排序（None 放最后）
    effects.sort(key=lambda e: (-1e18 if e.delta_tte_h is None else -e.delta_tte_h))
    return baseline, effects

