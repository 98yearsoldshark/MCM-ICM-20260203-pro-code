"""Model-2（热-电耦合 ECM）策略/反事实评估：比较不同策略对 TTE 与温升的影响。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm26a.battery import BatteryParams2Thermal
from mcm26a.power import PowerParams0
from mcm26a.scenarios import Scenario
from mcm26a.sim import SimResult2, simulate_model2_thermal


@dataclass(frozen=True)
class PolicyEffect2:
    """策略效果（相对 baseline）：同时输出续航与温升变化。"""

    action_id: str
    title_zh: str
    tte_h: float | None
    delta_tte_h: float | None
    delta_tte_pct: float | None
    temp_peak_C: float | None
    delta_temp_peak_C: float | None
    status: str


@dataclass(frozen=True)
class PolicyAction2:
    """一个策略动作：对场景做可解释的变换。"""

    action_id: str
    title_zh: str
    description_zh: str
    apply: Callable[[Scenario], Scenario]


def evaluate_policies_model2(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams2Thermal,
    soc0: float,
    temp0_C: float | None,
    actions: list[PolicyAction2],
    dt_s: float = 2.0,
) -> tuple[SimResult2, list[PolicyEffect2]]:
    """计算 baseline 以及每个 action 的 TTE/温升改善幅度（Model-2）。"""

    baseline = simulate_model2_thermal(
        scenario,
        power_params=power_params,
        battery_params=battery_params,
        soc0=soc0,
        temp0_C=temp0_C,
        variant=None,
        dt_s=dt_s,
    )

    effects: list[PolicyEffect2] = []
    for act in actions:
        sc2 = act.apply(scenario)
        res2 = simulate_model2_thermal(
            sc2,
            power_params=power_params,
            battery_params=battery_params,
            soc0=soc0,
            temp0_C=temp0_C,
            variant=act.action_id,
            dt_s=dt_s,
        )

        if baseline.tte_h is None or res2.tte_h is None:
            effects.append(
                PolicyEffect2(
                    action_id=act.action_id,
                    title_zh=act.title_zh,
                    tte_h=res2.tte_h,
                    delta_tte_h=None,
                    delta_tte_pct=None,
                    temp_peak_C=res2.temp_peak_C,
                    delta_temp_peak_C=None,
                    status=res2.status,
                )
            )
            continue

        delta_h = res2.tte_h - baseline.tte_h
        delta_pct = None if baseline.tte_h <= 0 else (delta_h / baseline.tte_h * 100.0)

        # 温升差：负值表示“更凉”
        tp0 = float(baseline.temp_peak_C)
        tp2 = float(res2.temp_peak_C)
        d_tp = tp2 - tp0

        effects.append(
            PolicyEffect2(
                action_id=act.action_id,
                title_zh=act.title_zh,
                tte_h=res2.tte_h,
                delta_tte_h=delta_h,
                delta_tte_pct=delta_pct,
                temp_peak_C=res2.temp_peak_C,
                delta_temp_peak_C=d_tp,
                status=res2.status,
            )
        )

    # 优先按续航提升排序；提升为 None 的放最后
    effects.sort(key=lambda e: (-1e18 if e.delta_tte_h is None else -e.delta_tte_h))
    return baseline, effects

