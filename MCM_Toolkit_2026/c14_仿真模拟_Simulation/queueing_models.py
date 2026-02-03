# -*- coding: utf-8 -*-
# 排队论模型（Simulation-based）
#
# 来源（资料目录）：
# - 0ys-files/temp/10-数学建模41+30种算法常用代码.../Matlab 41种常用算法代码（免调试）/排队论算法代码.txt
#
# 本文件提供两个常见的“可直接用”的仿真模型：
# 1) M/M/c/K：泊松到达 + 指数服务 + c 个服务台 + 系统容量 K（含服务中）
# 2) 有限源“修理工模型”（Machine Repairman）：m 台机器、s 个修理工；机器故障间隔/修理时间均为指数分布
#
# 说明：
# - 竞赛中排队论常见需求是“给定参数 -> 估计平均等待/排队长度/利用率/阻塞概率”
# - 这里用事件驱动仿真（event-driven），避免过多依赖与 GUI

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class MMcKParams:
    """M/M/c/K 模型参数。"""

    lambda_rate: float  # 到达率 λ（单位时间到达数）
    mu_rate: float  # 服务率 μ（单位时间完成数），单个服务台
    servers: int = 1  # c
    capacity: Optional[int] = None  # K：系统容量（含服务中）；None 表示无限容量
    horizon: float = 1000.0  # 仿真时长 T
    seed: Optional[int] = 0


def simulate_mmck(params: MMcKParams) -> Dict[str, Any]:
    """
    事件驱动仿真：M/M/c/K。

    Returns:
        dict:
            - L, Lq: 时间平均系统人数/排队人数
            - W, Wq: Little 定律估计的平均逗留/等待时间
            - util: 平均利用率（忙碌服务台数 / c）
            - lambda_eff: 有效到达率（被接纳的到达 / T）
            - arrivals/accepted/blocked/departures
            - blocking_prob
    """
    lam = float(params.lambda_rate)
    mu = float(params.mu_rate)
    c = int(params.servers)
    K = None if params.capacity is None else int(params.capacity)
    T = float(params.horizon)
    if lam <= 0 or mu <= 0:
        raise ValueError("lambda_rate 与 mu_rate 必须为正数。")
    if c <= 0:
        raise ValueError("servers 必须为正整数。")
    if T <= 0:
        raise ValueError("horizon 必须为正数。")
    if K is not None and K < 0:
        raise ValueError("capacity 必须为 None 或非负整数。")
    if K is not None and K > 0 and K < c:
        # 允许 K<c（代表最多容纳 K 个，可能导致部分服务台永远空闲），但提醒下
        pass

    rng = np.random.default_rng(params.seed)

    # 事件时间（绝对时间）
    next_arrival = float(rng.exponential(1.0 / lam))
    depart_times = np.full(c, np.inf, dtype=float)  # 每个服务台的下一次完成时刻；inf 表示空闲

    n_sys = 0  # 系统内人数（含服务中 + 等待）
    arrivals = 0
    accepted = 0
    blocked = 0
    departures = 0

    area_L = 0.0
    area_Lq = 0.0
    area_busy = 0.0
    prev_t = 0.0

    def busy_servers() -> int:
        return int(np.sum(np.isfinite(depart_times)))

    while True:
        t_dep = float(np.min(depart_times))
        t_next = min(next_arrival, t_dep)
        if t_next > T:
            dt = T - prev_t
            if dt > 0:
                b = busy_servers()
                area_L += n_sys * dt
                area_Lq += max(n_sys - c, 0) * dt
                area_busy += b * dt
            break

        dt = t_next - prev_t
        if dt > 0:
            b = busy_servers()
            area_L += n_sys * dt
            area_Lq += max(n_sys - c, 0) * dt
            area_busy += b * dt

        prev_t = t_next

        if next_arrival <= t_dep:
            # 到达事件
            arrivals += 1
            next_arrival = float(prev_t + rng.exponential(1.0 / lam))

            if K is not None and n_sys >= K:
                blocked += 1
                continue

            accepted += 1
            n_sys += 1

            b = busy_servers()
            if b < c:
                idle = np.where(~np.isfinite(depart_times))[0]
                idx = int(idle[0])
                depart_times[idx] = float(prev_t + rng.exponential(1.0 / mu))

        else:
            # 离开事件
            departures += 1
            idx = int(np.argmin(depart_times))
            depart_times[idx] = np.inf
            n_sys = max(0, n_sys - 1)

            # 若仍有等待，则该服务台立刻接下一位
            if n_sys >= c:
                depart_times[idx] = float(prev_t + rng.exponential(1.0 / mu))

    L = area_L / T
    Lq = area_Lq / T
    util = area_busy / (float(c) * T)
    lambda_eff = accepted / T
    W = float("inf") if lambda_eff <= 0 else L / lambda_eff
    Wq = float("inf") if lambda_eff <= 0 else Lq / lambda_eff
    blocking_prob = 0.0 if arrivals == 0 else blocked / arrivals

    return {
        "L": float(L),
        "Lq": float(Lq),
        "W": float(W),
        "Wq": float(Wq),
        "util": float(util),
        "lambda_eff": float(lambda_eff),
        "arrivals": int(arrivals),
        "accepted": int(accepted),
        "blocked": int(blocked),
        "departures": int(departures),
        "blocking_prob": float(blocking_prob),
    }


@dataclass
class RepairmanParams:
    """有限源修理工模型参数（Machine Repairman）。"""

    repairmen: int  # s
    machines: int  # m
    mean_uptime: float  # 机器“正常运行”到故障的平均时间（指数分布均值）
    mean_repair: float  # 修理时间均值（指数分布均值）
    horizon: float = 1000.0
    seed: Optional[int] = 0


def simulate_machine_repairman(params: RepairmanParams) -> Dict[str, Any]:
    """
    事件驱动仿真：有限源修理工模型（m 台机器，s 个修理工）。

    过程：
    - 每台机器独立：运行一段指数时间后故障 -> 进入修理队列 -> 修好后再进入运行
    - 系统内“顾客”数量 L：当前故障机器数（含修理中 + 等待）

    Returns:
        dict:
            - L, Lq: 时间平均故障数/等待故障数（>s 的部分）
            - W, Wq: Little 定律估计的平均逗留/等待时间（基于有效到达率：故障到达/T）
            - util: 修理工平均利用率
            - arrivals: 故障到达数
            - p_state: 长度 m+1 的状态概率（P(L=i)）
    """
    s = int(params.repairmen)
    m = int(params.machines)
    up = float(params.mean_uptime)
    rep = float(params.mean_repair)
    T = float(params.horizon)
    if s <= 0 or m <= 0:
        raise ValueError("repairmen 与 machines 必须为正整数。")
    if s > m:
        # 允许（修理工多于机器），但实际利用率会偏低
        pass
    if up <= 0 or rep <= 0 or T <= 0:
        raise ValueError("mean_uptime/mean_repair/horizon 必须为正数。")

    rng = np.random.default_rng(params.seed)

    # arrive_times：当前“运行中机器”的下一次故障时刻（绝对时间），长度 = m - L
    arrive_times = np.sort(rng.exponential(up, size=m).astype(float))
    # leave_times：当前“修理中”的完成时刻，长度 = min(L,s)
    leave_times: list[float] = []

    L = 0  # 系统内（故障）数量
    arrivals = 0

    area_L = 0.0
    area_Lq = 0.0
    area_busy = 0.0
    state_area = np.zeros(m + 1, dtype=float)
    prev_t = 0.0

    def busy() -> int:
        return min(L, s)

    while True:
        t_arr = float(arrive_times[0]) if arrive_times.size > 0 else float("inf")
        t_dep = float(leave_times[0]) if leave_times else float("inf")
        t_next = min(t_arr, t_dep)

        if t_next > T:
            dt = T - prev_t
            if dt > 0:
                area_L += L * dt
                area_Lq += max(L - s, 0) * dt
                area_busy += busy() * dt
                state_area[L] += dt
            break

        dt = t_next - prev_t
        if dt > 0:
            area_L += L * dt
            area_Lq += max(L - s, 0) * dt
            area_busy += busy() * dt
            state_area[L] += dt

        prev_t = t_next

        if t_next == t_arr:
            # 机器故障到达
            arrivals += 1
            arrive_times = arrive_times[1:]
            L += 1
            if L <= s:
                leave_times.append(float(prev_t + rng.exponential(rep)))
                leave_times.sort()
        else:
            # 修理完成离开
            leave_times.pop(0)
            # 该机器恢复运行，安排下一次故障
            next_fail = float(prev_t + rng.exponential(up))
            arrive_times = np.sort(np.append(arrive_times, next_fail))

            L = max(0, L - 1)
            # 若仍有等待故障机器，则空闲修理工立刻开始下一台
            if L >= s and len(leave_times) < s:
                leave_times.append(float(prev_t + rng.exponential(rep)))
                leave_times.sort()

        if L > m:
            # 理论上不应发生；兜底防错
            raise RuntimeError("L>m：状态不一致，仿真逻辑可能出错。")

    L_avg = area_L / T
    Lq_avg = area_Lq / T
    util = area_busy / (float(s) * T)
    lambda_eff = arrivals / T
    W = float("inf") if lambda_eff <= 0 else L_avg / lambda_eff
    Wq = float("inf") if lambda_eff <= 0 else Lq_avg / lambda_eff
    p_state = state_area / T

    return {
        "L": float(L_avg),
        "Lq": float(Lq_avg),
        "W": float(W),
        "Wq": float(Wq),
        "util": float(util),
        "lambda_eff": float(lambda_eff),
        "arrivals": int(arrivals),
        "p_state": p_state,
    }


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：排队论仿真模型。

    Args:
        data: dict，包含：
            - model: "mmck" 或 "repairman"
            对应字段：
            1) mmck:
               - lambda_rate, mu_rate, servers, capacity(optional), horizon(optional)
            2) repairman:
               - repairmen, machines, mean_uptime, mean_repair, horizon(optional)
        params: 额外参数：
            - seed: int（随机种子）

    Returns:
        dict: simulate_mmck 或 simulate_machine_repairman 的输出
    """
    params = params or {}
    if not isinstance(data, dict) or "model" not in data:
        raise TypeError("data 必须为 dict，且包含 model。")

    model = str(data["model"]).strip().lower()
    seed = None if params.get("seed") is None else int(params.get("seed", 0))

    if model == "mmck":
        p = MMcKParams(
            lambda_rate=float(data["lambda_rate"]),
            mu_rate=float(data["mu_rate"]),
            servers=int(data.get("servers", 1)),
            capacity=None if data.get("capacity") is None else int(data.get("capacity")),
            horizon=float(data.get("horizon", 1000.0)),
            seed=seed,
        )
        return simulate_mmck(p)

    if model in {"repairman", "machine_repairman"}:
        p = RepairmanParams(
            repairmen=int(data["repairmen"]),
            machines=int(data["machines"]),
            mean_uptime=float(data["mean_uptime"]),
            mean_repair=float(data["mean_repair"]),
            horizon=float(data.get("horizon", 1000.0)),
            seed=seed,
        )
        return simulate_machine_repairman(p)

    raise ValueError("model 必须为 'mmck' 或 'repairman'。")


if __name__ == "__main__":
    # Demo 1：M/M/1/K
    out1 = solve(
        {"model": "mmck", "lambda_rate": 8.0, "mu_rate": 10.0, "servers": 1, "capacity": 20, "horizon": 2000.0},
        {"seed": 0},
    )
    print("[M/M/1/20] L=%.3f Lq=%.3f W=%.3f Wq=%.3f util=%.3f block=%.4f" % (out1["L"], out1["Lq"], out1["W"], out1["Wq"], out1["util"], out1["blocking_prob"]))

    # Demo 2：有限源修理工模型（m 台机器，s 个修理工）
    out2 = solve(
        {"model": "repairman", "repairmen": 2, "machines": 10, "mean_uptime": 1.0, "mean_repair": 0.4, "horizon": 2000.0},
        {"seed": 0},
    )
    print("[Repairman] L=%.3f Lq=%.3f W=%.3f Wq=%.3f util=%.3f" % (out2["L"], out2["Lq"], out2["W"], out2["Wq"], out2["util"]))

