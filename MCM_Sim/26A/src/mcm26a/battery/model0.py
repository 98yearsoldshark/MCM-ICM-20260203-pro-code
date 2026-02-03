"""Model-0 电池模型：用“可用能量/电量”做连续时间消耗（最简可解释基线）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcm26a.utils import wh_to_j


@dataclass(frozen=True)
class BatteryParams0:
    """Model-0 电池参数。

    说明：
    - Model-0 不显式刻画端电压与内阻，仅用“能量守恒”推进 SOC/剩余能量。
    - 为贴近真实手机的关机逻辑，可用 soc_min 近似关机阈值（后续 Model-1 用截止电压事件替代）。
    """

    energy_Wh: float
    soc_min: float = 0.0

    @property
    def energy_J(self) -> float:
        return wh_to_j(self.energy_Wh)

    @staticmethod
    def from_json(path: str | Path) -> "BatteryParams0":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        batt = obj.get("battery", obj)
        return BatteryParams0(
            energy_Wh=float(batt["energy_Wh"]),
            soc_min=float(batt.get("soc_min", 0.0)),
        )

