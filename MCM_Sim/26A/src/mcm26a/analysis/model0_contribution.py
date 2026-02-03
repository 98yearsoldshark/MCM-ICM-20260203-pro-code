"""Model-0 贡献分解：把一次仿真的能量消耗按组件拆分（用于论文图表/解释）。"""

from __future__ import annotations

from dataclasses import dataclass

from mcm26a.sim import SimResult0


@dataclass(frozen=True)
class ComponentEnergy:
    """某个组件的能量消耗统计。"""

    name: str
    energy_Wh: float
    share_pct: float | None


def component_energies(res: SimResult0) -> list[ComponentEnergy]:
    """把 res.energy_components_Wh 转为排序后的列表（按能量降序）。"""

    total = float(res.energy_used_Wh)
    out: list[ComponentEnergy] = []
    for k, wh in res.energy_components_Wh.items():
        wh = float(wh)
        share = None if total <= 0 else (wh / total * 100.0)
        out.append(ComponentEnergy(name=str(k), energy_Wh=wh, share_pct=share))

    out.sort(key=lambda x: -x.energy_Wh)
    return out

