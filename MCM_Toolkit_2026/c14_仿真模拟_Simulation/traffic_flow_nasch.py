# -*- coding: utf-8 -*-
# 元胞自动机：Nagel–Schreckenberg (NaSch) 交通流模型
#
# 来源（资料目录）：
# - 0ys-files/temp/10-数学建模41+30种算法常用代码.../Matlab 41种常用算法代码（免调试）/元胞自动机代码可直接运行.../NaSchr.m
#
# 模型要点（单车道、环形道路）：
# 1) 加速：v <- min(v+1, vmax)
# 2) 避碰：v <- min(v, gap)  （gap 为前车距离-1）
# 3) 随机慢化：以概率 p，若 v>0 则 v <- v-1
# 4) 车辆前进：x <- (x+v) mod L
#
# 输出常用：基本图（Fundamental Diagram）——密度-流量曲线

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class NaSchParams:
    road_length: int = 1000
    vmax: int = 10
    p_brake: float = 0.6
    steps: int = 500
    burn_in: int = 100
    seed: Optional[int] = 0


def _simulate_one_density(
    density: float,
    *,
    params: NaSchParams,
    rng: np.random.Generator,
) -> Dict[str, float]:
    L = int(params.road_length)
    vmax = int(params.vmax)
    p = float(params.p_brake)
    steps = int(params.steps)
    burn_in = int(params.burn_in)
    if not (0.0 <= density <= 1.0):
        raise ValueError("density 必须在 [0,1]。")
    if L <= 0 or vmax < 0 or steps <= 0 or burn_in < 0:
        raise ValueError("参数不合法：road_length/vmax/steps/burn_in。")
    if burn_in >= steps:
        raise ValueError("burn_in 必须小于 steps。")

    # 初始化道路：用位置列表（比逐格遍历更高效）
    occ = rng.random(L) < float(density)
    pos = np.flatnonzero(occ).astype(int)
    n = int(pos.size)
    if n == 0:
        return {"density": 0.0, "flow": 0.0, "avg_speed": 0.0}
    vel = np.zeros(n, dtype=int)

    flow_sum = 0.0
    speed_sum = 0.0
    count = 0

    for t in range(steps):
        # 保持车辆按位置排序，便于算 gap
        order = np.argsort(pos)
        pos = pos[order]
        vel = vel[order]

        # gap：到前车的空格数（环形）
        next_pos = np.roll(pos, -1)
        gap = (next_pos - pos - 1) % L  # (n,)

        # 1) 加速
        vel = np.minimum(vel + 1, vmax)
        # 2) 避碰
        vel = np.minimum(vel, gap)
        # 3) 随机慢化
        rand_mask = (rng.random(n) < p) & (vel > 0)
        vel[rand_mask] -= 1

        # 4) 移动
        pos = (pos + vel) % L

        # 统计（跳过 burn-in）
        if t >= burn_in:
            # 单位时间内通过的“单元格数/道路长度”作为流量（等价于 mean_speed * density）
            flow_t = float(np.sum(vel) / L)
            avg_speed_t = float(np.mean(vel)) if n > 0 else 0.0
            flow_sum += flow_t
            speed_sum += avg_speed_t
            count += 1

    flow = flow_sum / max(1, count)
    avg_speed = speed_sum / max(1, count)
    return {"density": float(n) / float(L), "flow": float(flow), "avg_speed": float(avg_speed)}


def simulate_flow_density(
    densities: Sequence[float],
    *,
    params: Optional[NaSchParams] = None,
) -> Dict[str, Any]:
    """
    扫描多个密度，输出密度-流量曲线数据。

    Args:
        densities: list[float]，每个元素在 [0,1]
        params: NaSchParams

    Returns:
        dict:
            - density: ndarray
            - flow: ndarray
            - avg_speed: ndarray
            - params: dict
    """
    p = params or NaSchParams()
    rng = np.random.default_rng(p.seed)
    dens = [float(x) for x in densities]
    out_d = []
    out_f = []
    out_v = []
    for d in dens:
        r = _simulate_one_density(d, params=p, rng=rng)
        out_d.append(r["density"])
        out_f.append(r["flow"])
        out_v.append(r["avg_speed"])
    return {
        "density": np.asarray(out_d, dtype=float),
        "flow": np.asarray(out_f, dtype=float),
        "avg_speed": np.asarray(out_v, dtype=float),
        "params": {
            "road_length": int(p.road_length),
            "vmax": int(p.vmax),
            "p_brake": float(p.p_brake),
            "steps": int(p.steps),
            "burn_in": int(p.burn_in),
            "seed": None if p.seed is None else int(p.seed),
        },
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：NaSch 交通流仿真（密度-流量曲线）。

    Args:
        data: dict，可选字段：
            - densities: list[float]（若不提供则用 linspace 生成）
        params:
            - road_length, vmax, p_brake, steps, burn_in, seed
            - density_min（默认 0.02）, density_max（默认 0.98）, n_densities（默认 20）

    Returns:
        dict: simulate_flow_density() 的输出
    """
    params = params or {}
    p = NaSchParams(
        road_length=int(params.get("road_length", 1000)),
        vmax=int(params.get("vmax", 10)),
        p_brake=float(params.get("p_brake", 0.6)),
        steps=int(params.get("steps", 500)),
        burn_in=int(params.get("burn_in", 100)),
        seed=None if params.get("seed") is None else int(params.get("seed", 0)),
    )

    dens = None
    if isinstance(data, dict):
        dens = data.get("densities")
    if dens is None:
        dmin = float(params.get("density_min", 0.02))
        dmax = float(params.get("density_max", 0.98))
        n = int(params.get("n_densities", 20))
        dens = np.linspace(dmin, dmax, n).tolist()
    return simulate_flow_density(densities=dens, params=p)


if __name__ == "__main__":
    out = solve({}, {"road_length": 300, "steps": 300, "burn_in": 80, "vmax": 10, "p_brake": 0.6, "n_densities": 15, "seed": 0})
    print("density =", np.round(out["density"], 3).tolist())
    print("flow    =", np.round(out["flow"], 3).tolist())

