"""R0（欧姆内阻）粗估：从“休止->负载”的电压跳变估计瞬时内阻。

用途（对应本项目的“优化变差”问题）：
- 仅用低电流数据拟合 ECM 时，R0 在目标函数中几乎不可辨识，容易被拟合到极小（甚至触底到下界），
  从而在“高电流脉冲/动态负载”数据上严重低估压降，导致泛化性能变差；
- 因此我们用含电流脉冲/阶跃的数据先估计一个合理的 R0 先验，再在低电流数据上拟合 RC 松弛参数。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calce_channel import CalceChannelTimeSeries


@dataclass(frozen=True)
class R0Estimate:
    """R0 估计结果（用于打印/写入配置 meta）。"""

    r0_values_ohm: list[float]

    def summary(self) -> dict[str, float | int]:
        xs = np.array(self.r0_values_ohm, dtype=float)
        if len(xs) == 0:
            return {"n": 0}
        return {
            "n": int(len(xs)),
            "median_ohm": float(np.median(xs)),
            "p10_ohm": float(np.quantile(xs, 0.10)),
            "p90_ohm": float(np.quantile(xs, 0.90)),
            "mean_ohm": float(np.mean(xs)),
        }


def estimate_r0_from_rest_load_transitions(
    ts: CalceChannelTimeSeries,
    *,
    rest_i_thresh_A: float = 0.02,
    load_i_thresh_A: float = 0.2,
    n_rest: int = 20,
    n_load: int = 20,
    min_gap: int = 200,
) -> R0Estimate:
    """从“休止->负载”与“负载->休止”的电压跳变估计 R0。

设计：
- 以电流阈值划分 rest/load：
  - rest：|I| <= rest_i_thresh_A
  - load：|I| >= load_i_thresh_A
- 对每个“边界点”：
  - rest 窗：边界前 n_rest 个点取电压中位数
  - load 窗：边界后 n_load 个点取电压中位数、负载电流中位数
  - R0 = |V_rest - V_load| / |I_load|

注意：
- 这只是“欧姆瞬时项”的粗估，会混入少量极化（RC）影响，因此应理解为 R0 的上界/近似。
"""

    i = np.asarray(ts.i_A, dtype=float)
    v = np.asarray(ts.v_V, dtype=float)
    if len(i) < (n_rest + n_load + 5):
        return R0Estimate(r0_values_ohm=[])

    rest = np.abs(i) <= float(rest_i_thresh_A)
    load = np.abs(i) >= float(load_i_thresh_A)

    # 找边界：rest->load 与 load->rest
    events: list[int] = []
    for k in range(1, len(i)):
        if rest[k - 1] and load[k]:
            events.append(k)
        elif load[k - 1] and rest[k]:
            events.append(k)

    # 去近邻重复（避免同一段边缘被多次计入）
    filtered: list[int] = []
    last = -10**18
    for e in events:
        if e - last >= int(min_gap):
            filtered.append(e)
            last = e

    r0_list: list[float] = []
    for k in filtered:
        a0 = max(0, k - int(n_rest))
        a1 = k
        b0 = k
        b1 = min(len(i), k + int(n_load))
        if (a1 - a0) < int(n_rest) or (b1 - b0) < int(n_load):
            continue

        # 窗内必须满足 rest/load 条件，避免跨段污染
        if not np.all(rest[a0:a1]):
            continue
        if not np.all(load[b0:b1]):
            continue

        v_rest = float(np.median(v[a0:a1]))
        v_load = float(np.median(v[b0:b1]))
        i_load = float(np.median(i[b0:b1]))
        if not np.isfinite(i_load) or abs(i_load) <= 1e-9:
            continue

        r0 = abs(v_rest - v_load) / abs(i_load)
        if np.isfinite(r0) and r0 > 0:
            r0_list.append(float(r0))

    return R0Estimate(r0_values_ohm=r0_list)

