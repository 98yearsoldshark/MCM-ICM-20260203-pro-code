"""Model-3（老化）长期评估：在多次循环下追踪续航退化与寿命指标。

为什么需要这个模块：
- Model-0/1/2 更关注“单次续航（TTE）”；
- Model-3 引入老化后，我们可以比较不同策略在长期上的表现：
  同样的“省电策略”是否也能“延寿”？是否存在续航-温升-寿命权衡？
"""

from __future__ import annotations

from dataclasses import dataclass

from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0
from mcm26a.scenarios import Scenario
from mcm26a.sim import SimResult3, simulate_model3_aging


@dataclass(frozen=True)
class CycleSummary3:
    """一次循环（一次放电到 cutoff）后的摘要。"""

    cycle_index: int
    tte_h: float | None
    status: str
    temp_peak_C: float
    cap_loss_frac: float
    r0_growth_frac: float


def simulate_repeated_cycles_model3(
    scenario: Scenario,
    *,
    power_params: PowerParams0,
    battery_params: BatteryParams3Aging,
    n_cycles: int,
    soc0: float = 1.0,
    temp0_C: float | None = None,
    cap_loss0_frac: float = 0.0,
    r0_growth0_frac: float = 0.0,
    r1_growth0_frac: float = 0.0,
    dt_s: float = 2.0,
    cool_to_temp0_each_cycle: bool = True,
) -> tuple[SimResult3 | None, list[CycleSummary3]]:
    """重复运行多次“放电到 cutoff”循环，返回最后一次 SimResult3 与每次循环摘要。

    约定：
    - 每次循环都从 SOC=1 开始（相当于一次充满电后的使用）；
    - 老化状态在循环间累积；
    - 温度可选择是否在循环间回到 temp0（近似隔夜冷却）。
    """

    n = int(n_cycles)
    if n <= 0:
        return None, []

    cap_loss = float(cap_loss0_frac)
    r0_grow = float(r0_growth0_frac)
    r1_grow = float(r1_growth0_frac)

    t0 = float(battery_params.t0_C if temp0_C is None else temp0_C)
    last: SimResult3 | None = None
    summaries: list[CycleSummary3] = []

    for k in range(n):
        last = simulate_model3_aging(
            scenario,
            power_params=power_params,
            battery_params=battery_params,
            soc0=float(soc0),
            temp0_C=(t0 if cool_to_temp0_each_cycle else temp0_C),
            cap_loss0_frac=cap_loss,
            r0_growth0_frac=r0_grow,
            r1_growth0_frac=r1_grow,
            variant=f"cycle{k+1}",
            dt_s=float(dt_s),
        )

        cap_loss = float(last.cap_loss_end_frac)
        r0_grow = float(last.r0_growth_end_frac)
        r1_grow = float(last.r1_growth_end_frac)

        summaries.append(
            CycleSummary3(
                cycle_index=k + 1,
                tte_h=last.tte_h,
                status=last.status,
                temp_peak_C=float(last.temp_peak_C),
                cap_loss_frac=float(cap_loss),
                r0_growth_frac=float(r0_grow),
            )
        )

        # 若出现非正常状态，提前停止（避免输出误导）
        if last.status not in ("cutoff", "soc_min"):
            break

    return last, summaries

