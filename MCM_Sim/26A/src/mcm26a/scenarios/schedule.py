"""场景定义：分段常值（piecewise-constant）schedule 及其变体解析。

目标：
- 用配置文件描述“使用场景”，作为外生输入驱动功耗模型与电池模型。
- 先支撑 Model-0 跑通：重复的 schedule + 简单字段（屏幕/亮度/负载/网络/GPS/后台）。
- 为后续 Model-1/2/3 升级预留空间（可扩展字段，不与具体功耗/电池实现耦合）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Segment:
    """一个时间段内输入保持常值。"""

    duration_s: float
    ambient_temp_c: float
    screen_on: bool
    brightness_nits: float
    activity: str
    cpu_load: float
    gpu_load: float
    radio_mode: str
    signal_quality: str
    net_activity: str
    gps_on: bool
    background_level: str
    # 网络平均吞吐（MB/s）。若提供（非 NaN），则视为“观测/外生给定”的连续输入，
    # 会覆盖功耗参数中的 throughput_MBps_by_activity，并自动关闭“网络突发 Poisson”生成项，
    # 避免把“已观测到的平均吞吐”再叠加一次突发流量导致双重计数。
    #
    # 设计动机：
    # - no7/no10 建议把 q(t) 作为连续输入；但赛题允许数据有限，我们在代码里用
    #   (net_activity -> throughput) 的离散近似先跑通。
    # - 当有公开数据（如 AndroWatts aggregated.csv 给出某段的总流量）时，
    #   用该字段可显著提升“观测→模型输入”的映射精度（尤其是网络功耗对照）。
    net_throughput_MBps: float = float("nan")
    # 屏幕内容平均亮度（APL, Average Picture Level），范围建议 [0,1]。
    # - 允许缺省：当未提供或为 NaN 时，由功耗模型根据 activity 做经验映射；
    # - 该字段用于 no7 升级（屏幕功耗非线性/与内容相关）。
    screen_apl: float = float("nan")


@dataclass(frozen=True)
class Scenario:
    """分段常值场景；若 repeat=True，则按周期循环重复。"""

    scenario_id: str
    title_zh: str
    description_zh: str
    repeat: bool
    cycle_s: float
    schedule: tuple[Segment, ...]

    def inputs_at(self, t_s: float) -> Segment:
        """返回时刻 t_s 所在段的输入（用于仿真/功耗计算）。

        注意：该函数只负责“查段”，不做任何物理计算。
        """

        if t_s < 0:
            raise ValueError("t_s must be non-negative")
        if self.repeat and self.cycle_s > 0:
            t_s = t_s % self.cycle_s

        acc = 0.0
        for seg in self.schedule:
            acc += seg.duration_s
            if t_s <= acc:
                return seg

        # 若未命中，说明 cycle_s 与 schedule 总时长不一致（或浮点误差）。
        # 兜底返回最后一段，避免仿真直接崩溃；同时提醒调用者应修正配置。
        return self.schedule[-1]


def load_scenarios_json(path: str | Path) -> dict[str, Any]:
    """加载场景 JSON 原始对象（不做强制校验）。"""

    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def materialize_scenario(
    raw: dict[str, Any],
    scenario_id: str,
    *,
    variant: str | None = None,
) -> Scenario:
    """从 `scenarios_v0.json` 的原始对象生成可用的 Scenario。

    variant 规则：
    - 若 variant 指定且存在：
      - `overrides`：对整个场景字段统一覆写（会作用到每个 schedule 段）
      - `segment_overrides`：对指定段（0-based 段索引）覆写字段
    """

    defaults = dict(raw.get("defaults", {}))
    scenarios = raw.get("scenarios", {})
    if scenario_id not in scenarios:
        raise KeyError(f"unknown scenario_id: {scenario_id!r}")

    spec = dict(scenarios[scenario_id])
    schedule = [dict(seg) for seg in spec.get("schedule", [])]
    if not schedule:
        raise ValueError(f"scenario {scenario_id!r} has empty schedule")

    # 变体覆写（可选）
    global_overrides: dict[str, Any] = {}
    seg_overrides: dict[int, dict[str, Any]] = {}
    if variant:
        variants = spec.get("variants", {})
        if variant not in variants:
            raise KeyError(f"unknown variant {variant!r} for scenario {scenario_id!r}")
        v = dict(variants[variant])

        global_overrides = dict(v.get("overrides", {}))

        raw_seg_overrides = v.get("segment_overrides", {})
        if raw_seg_overrides:
            for k, overrides in raw_seg_overrides.items():
                idx = int(k)
                if not (0 <= idx < len(schedule)):
                    raise IndexError(f"segment_overrides index out of range: {idx}")
                seg_overrides[idx] = dict(overrides)

    segs: list[Segment] = []
    for i, seg in enumerate(schedule):
        merged = dict(defaults)
        merged.update(seg)
        # global_overrides 应覆盖每一段的同名字段（而不是仅覆盖 defaults）。
        merged.update(global_overrides)
        # 段内覆写优先级最高。
        merged.update(seg_overrides.get(i, {}))
        segs.append(
            Segment(
                duration_s=float(merged["duration_s"]),
                ambient_temp_c=float(merged.get("ambient_temp_c", defaults.get("ambient_temp_c", 23.0))),
                screen_on=bool(merged["screen_on"]),
                brightness_nits=float(merged["brightness_nits"]),
                activity=str(merged["activity"]),
                cpu_load=float(merged["cpu_load"]),
                gpu_load=float(merged["gpu_load"]),
                radio_mode=str(merged["radio_mode"]),
                signal_quality=str(merged["signal_quality"]),
                net_activity=str(merged["net_activity"]),
                net_throughput_MBps=float(merged.get("net_throughput_MBps", float("nan"))),
                gps_on=bool(merged["gps_on"]),
                background_level=str(merged["background_level"]),
                screen_apl=float(merged.get("screen_apl", float("nan"))),
            )
        )

    cycle_s = float(spec.get("cycle_s", sum(s.duration_s for s in segs)))
    return Scenario(
        scenario_id=scenario_id,
        title_zh=str(spec.get("title_zh", "")),
        description_zh=str(spec.get("description_zh", "")),
        repeat=bool(spec.get("repeat", False)),
        cycle_s=cycle_s,
        schedule=tuple(segs),
    )
