"""升级功耗模型（面向 Q2）：用“状态机/连续门控 + 随机过程 + 交互项”刻画协同作用与不可预测性。

核心增量（相对 Model-0）：
- 网络：RRC 状态机（IDLE/CONNECTED/TAIL）+ 弱信号惩罚 + 吞吐驱动能耗；
- 后台：Poisson 唤醒事件（可随机采样），会注入短时数据与 CPU 额外能耗；
- 协同作用：屏幕×网络、网络×高 CPU 等交互项，以最小参数集实现“非简单叠加”。

约定：
- 时间单位统一用秒（s），功率单位瓦（W），能量单位焦耳（J）。
- 该模块输出的是“电池侧等效功率需求”（把 PMIC 效率等吸收到参数中），以便直接耦合电池模型。

按 no7 升级（更研究级、但仍保持可运行/可消融）：
- 屏幕：加入 APL（内容平均亮度）项，并允许亮度功耗超线性（γ_b>1）；
- CPU：加入 big.LITTLE + 超线性（γ>1），并支持“热节流 + backlog”闭环（限频→任务更久）；
- 网络：可选“连续门控尾态”（指数衰减的 tail state，τ 随强度变化），替代固定时长 tail。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from mcm26a.power.model0 import GPSParams0, PowerBreakdown
from mcm26a.scenarios import Segment

RRCState = Literal["IDLE", "CONNECTED", "TAIL"]


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def _sigmoid(z: float) -> float:
    """轻量 sigmoid（避免引入 scipy）。"""

    z = float(z)
    # 避免 exp 溢出
    if z >= 0:
        ez = float(np.exp(-z))
        return float(1.0 / (1.0 + ez))
    ez = float(np.exp(z))
    return float(ez / (1.0 + ez))


def _default_screen_apl_by_activity(activity: str) -> float:
    """当场景未显式提供 APL 时的经验映射（仅用于无数据阶段/示例场景）。

APL（Average Picture Level）解释：
- 取值 0~1，表示屏幕内容平均亮度（与内容/主题色相关，不等同于背光亮度）。
- 白底网页通常 APL 更高；暗色视频/深色游戏通常 APL 更低。
"""

    a = str(activity)
    table = {
        "standby": 0.0,
        "call": 0.15,
        "browse": 0.80,
        "video": 0.55,
        "navigation": 0.65,
        "gaming": 0.60,
        "game": 0.60,
    }
    return float(table.get(a, 0.60))


@dataclass(frozen=True)
class ScreenMarkovParams1:
    """屏幕状态随机性：两状态马尔可夫链（OFF/ON）。

    使用方式（设计选择）：
    - 若场景段 seg.screen_on==True：认为“用户强制在用屏幕”，直接强制 ON（不引入随机切换）。
    - 若 seg.screen_on==False：允许 OFF/ON 随机切换，用于刻画“待机时偶尔亮屏/解锁”的不可预测性。
    """

    off_to_on_rate_per_s_by_activity: dict[str, float]
    on_to_off_rate_per_s_by_activity: dict[str, float]
    wake_brightness_nits: float = 150.0

    def off_to_on_rate(self, activity: str) -> float:
        return max(0.0, float(self.off_to_on_rate_per_s_by_activity.get(activity, 0.0)))

    def on_to_off_rate(self, activity: str) -> float:
        return max(0.0, float(self.on_to_off_rate_per_s_by_activity.get(activity, 0.0)))


@dataclass(frozen=True)
class SignalMarkovParams1:
    """信号强弱抖动：两状态马尔可夫链（good/poor）。

    设计目标：
    - 让“同一场景同一参数”也能出现一定幅度的随机差异（题面强调不可预测性）。
    - 同时保持可解释：信号差会放大每 MB 能耗（重传/功放提升），并与 RRC 尾态协同。
    """

    enabled_radio_modes: tuple[str, ...] = ("lte", "5g")
    rates_by_base: dict[str, dict[str, float]] = field(default_factory=dict)

    def rates(self, base_quality: str) -> tuple[float, float]:
        """返回 (good->poor, poor->good) 的转移率（1/s）。"""

        base_quality = str(base_quality)
        cfg = self.rates_by_base.get(base_quality, {})
        gp = max(0.0, float(cfg.get("good_to_poor", 0.0)))
        pg = max(0.0, float(cfg.get("poor_to_good", 0.0)))
        return gp, pg


@dataclass(frozen=True)
class RRCParams1:
    """网络/RRC 参数。

    - tau_tail_s：不同网络制式的尾态持续时间
    - p_state_W：不同网络制式、不同状态下的“基带维持功耗”
    - e_per_mb_J：每 MB 传输消耗的能量（J/MB），乘以吞吐 MB/s 得到功率 W
    - signal_psi：弱信号惩罚系数（>=1），用于放大 e_per_mb_J（必要时也可同时放大 p_state）
    - throughput_MBps_by_activity：把场景字段 net_activity 映射为“平稳吞吐”（MB/s）
    - burst_rate_per_s_by_activity / burst_mb_by_activity：可选的“前台网络突发”模型（Poisson），用于刻画 RRC 尾态的协同放大：
      - N_burst ~ Poisson(rate * dt)
      - data_mb = throughput * dt + N_burst * burst_mb
    """

    tau_tail_s: dict[str, float]
    p_state_W: dict[str, dict[str, float]]
    e_per_mb_J: dict[str, float]
    signal_psi: dict[str, float]
    throughput_MBps_by_activity: dict[str, float]
    burst_rate_per_s_by_activity: dict[str, float] = field(default_factory=dict)
    burst_mb_by_activity: dict[str, float] = field(default_factory=dict)
    # no7：连续门控尾态（可选）。若 enabled，则用指数衰减 tail state 替代固定 tail_left_s。
    # 结构示例（在 JSON 的 rrc.tail_gate 中）：
    #   {"enabled": true, "tau_low_s": {"wifi":3,...}, "tau_high_s": {...},
    #    "u0":0.45, "delta_u":0.12, "omega_cpu":0.45, "omega_gpu":0.25, "d0_MBps":1.0, "tail_eps":0.01}
    tail_gate: dict[str, Any] = field(default_factory=dict)

    def tau_tail(self, radio_mode: str) -> float:
        return float(self.tau_tail_s.get(radio_mode, 0.0))

    def p_state(self, radio_mode: str, state: RRCState) -> float:
        table = self.p_state_W.get(radio_mode, {})
        return float(table.get(state, table.get("IDLE", 0.0)))

    def e_per_mb(self, radio_mode: str, signal_quality: str) -> float:
        e0 = float(self.e_per_mb_J.get(radio_mode, 0.0))
        psi = float(self.signal_psi.get(signal_quality, 1.0))
        return max(0.0, e0 * psi)

    def throughput_MBps(self, net_activity: str) -> float:
        return max(0.0, float(self.throughput_MBps_by_activity.get(net_activity, 0.0)))

    def burst_rate_per_s(self, net_activity: str) -> float:
        return max(0.0, float(self.burst_rate_per_s_by_activity.get(net_activity, 0.0)))

    def burst_mb(self, net_activity: str) -> float:
        return max(0.0, float(self.burst_mb_by_activity.get(net_activity, 0.0)))


@dataclass(frozen=True)
class ScreenParams1:
    """屏幕功耗（no7 升级版，保持向后兼容）。

P_screen = P0 + k * brightness * (brightness/ref_nits)^(gamma_b-1) + k_apl * apl^gamma_apl

说明：
- gamma_b=1 时退化为线性亮度模型（与旧版一致）；
- apl 为 [0,1] 的内容平均亮度（Average Picture Level）。
"""

    P0_W: float
    k_W_per_nit: float
    ref_nits: float = 500.0
    gamma_b: float = 1.0
    k_apl_W: float = 0.0
    gamma_apl: float = 1.0


@dataclass(frozen=True)
class LoadParams1:
    """通用负载功耗：P = k * load^gamma。"""

    k_W: float
    gamma: float = 1.0


@dataclass(frozen=True)
class CPUParams1:
    """CPU 功耗（no7 升级版）：

- 兼容旧版：若只提供 k_W，则 P = k_W * load^gamma；
- big.LITTLE：若提供 k_lit_W 与 k_big_W，则
    load_lit = min(load, u_switch)/u_switch
    load_big = max(0, load-u_switch)/(1-u_switch)
    P = k_lit_W*load_lit^gamma_lit + k_big_W*load_big^gamma_big
"""

    # 旧版/兜底：单一线性/超线性
    k_W: float = 0.0
    gamma: float = 1.0

    # big.LITTLE（可选）
    k_lit_W: float | None = None
    k_big_W: float | None = None
    gamma_lit: float = 1.3
    gamma_big: float = 1.5
    u_switch: float = 0.45

    def power_nominal_W(self, load01: float) -> float:
        u = _clamp01(load01)
        if self.k_lit_W is None or self.k_big_W is None:
            return max(0.0, float(self.k_W) * (u ** float(self.gamma)))

        us = float(self.u_switch)
        us = float(max(1e-6, min(0.999999, us)))
        u_lit_raw = min(u, us)
        u_big_raw = max(0.0, u - us)
        u_lit = u_lit_raw / us
        u_big = u_big_raw / (1.0 - us)
        return max(
            0.0,
            float(self.k_lit_W) * (u_lit ** float(self.gamma_lit)) + float(self.k_big_W) * (u_big ** float(self.gamma_big)),
        )


@dataclass(frozen=True)
class PoissonBackgroundParams1:
    """后台随机唤醒参数（Poisson）。

    对于每个 dt：
    - 采样 N ~ Poisson(lambda_per_s[level] * dt)
    - 每次唤醒注入 data_mb_per_wake 的小流量（会触发 RRC 状态机）
    - 并额外消耗 CPU_wake_W 持续 cpu_wake_duration_s 的能量（累积到 background_w）
    """

    lambda_per_s: dict[str, float]
    data_mb_per_wake: float
    cpu_wake_W: float
    cpu_wake_duration_s: float

    def rate(self, background_level: str) -> float:
        return max(0.0, float(self.lambda_per_s.get(background_level, 0.0)))


@dataclass(frozen=True)
class InteractionParams1:
    """协同/交互项参数（最小集合）。"""

    beta_screen_net_W: float
    beta_net_highcpu_W: float
    beta_screen_highcpu_W: float
    cpu_high_threshold: float


@dataclass(frozen=True)
class DVFSParams1:
    """极简热节流/限频（可选）。

    备注：
    - 真实手机通常通过 DVFS/thermal throttling 等机制实现“过热时降低频率/电压”；
    - 本模块支持两种层级：
      - 保守版：只缩放瞬时功耗（不会改变任务持续时间）；
      - no7 升级版：引入 backlog 状态，使“限频→任务更久”可被刻画，从而出现能耗/续航的反直觉效应。
    """

    throttle_temp_C: float
    slope_per_C: float
    min_scale: float
    # no7：功耗随频率/电压缩放的指数（典型 2~3）；=1 则退化为线性缩放
    power_exponent: float = 1.0
    # no7：backlog 闭环（限频→任务更久）
    backlog_enabled: bool = False
    backlog_tau_s: float = 30.0

    def scale(self, temp_C: float | None) -> float:
        if temp_C is None:
            return 1.0
        t = float(temp_C)
        if t <= float(self.throttle_temp_C):
            return 1.0
        s = 1.0 - float(self.slope_per_C) * (t - float(self.throttle_temp_C))
        return float(max(float(self.min_scale), min(1.0, s)))


@dataclass(frozen=True)
class PowerParams1Stateful:
    """面向 Q2 的升级功耗参数（单位：W、J、s）。"""

    base_W: float
    screen: ScreenParams1
    cpu: CPUParams1
    gpu: LoadParams1
    gps: GPSParams0
    background_level_W: dict[str, float]
    rrc: RRCParams1
    background_poisson: PoissonBackgroundParams1
    interaction: InteractionParams1
    dvfs: DVFSParams1
    screen_markov: ScreenMarkovParams1
    signal_markov: SignalMarkovParams1

    @staticmethod
    def from_json(path: str | Path) -> "PowerParams1Stateful":
        p = Path(path)
        obj: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        rrc = obj["rrc"]
        bg = obj["background_poisson"]
        inter = obj.get("interaction", {})
        dvfs = obj.get("dvfs", {})
        scr = obj.get("screen_markov", {})
        sig = obj.get("signal_markov", {})

        # ---- screen（兼容旧版：只含 P0_W/k_W_per_nit）----
        scr_obj = obj.get("screen", {}) or {}
        screen = ScreenParams1(
            P0_W=float(scr_obj.get("P0_W", 0.0)),
            k_W_per_nit=float(scr_obj.get("k_W_per_nit", 0.0)),
            ref_nits=float(scr_obj.get("ref_nits", 500.0)),
            gamma_b=float(scr_obj.get("gamma_b", 1.0)),
            k_apl_W=float(scr_obj.get("k_apl_W", 0.0)),
            gamma_apl=float(scr_obj.get("gamma_apl", 1.0)),
        )

        # ---- cpu（兼容旧版：k_W）----
        cpu_obj = obj.get("cpu", {}) or {}
        cpu = CPUParams1(
            k_W=float(cpu_obj.get("k_W", 0.0)),
            gamma=float(cpu_obj.get("gamma", 1.0)),
            k_lit_W=None if ("k_lit_W" not in cpu_obj) else float(cpu_obj.get("k_lit_W")),
            k_big_W=None if ("k_big_W" not in cpu_obj) else float(cpu_obj.get("k_big_W")),
            gamma_lit=float(cpu_obj.get("gamma_lit", 1.3)),
            gamma_big=float(cpu_obj.get("gamma_big", 1.5)),
            u_switch=float(cpu_obj.get("u_switch", 0.45)),
        )

        # ---- gpu（允许超线性）----
        gpu_obj = obj.get("gpu", {}) or {}
        gpu = LoadParams1(k_W=float(gpu_obj.get("k_W", 0.0)), gamma=float(gpu_obj.get("gamma", 1.0)))

        return PowerParams1Stateful(
            base_W=float(obj["base_W"]),
            screen=screen,
            cpu=cpu,
            gpu=gpu,
            gps=GPSParams0(P_W=float(obj["gps"]["P_W"])),
            background_level_W={str(k): float(v) for k, v in obj["background_level_W"].items()},
            rrc=RRCParams1(
                tau_tail_s={str(k): float(v) for k, v in rrc["tau_tail_s"].items()},
                p_state_W={
                    str(mode): {str(st): float(pw) for st, pw in table.items()} for mode, table in rrc["p_state_W"].items()
                },
                e_per_mb_J={str(k): float(v) for k, v in rrc["e_per_mb_J"].items()},
                signal_psi={str(k): float(v) for k, v in rrc["signal_psi"].items()},
                throughput_MBps_by_activity={
                    str(k): float(v) for k, v in rrc["throughput_MBps_by_activity"].items()
                },
                burst_rate_per_s_by_activity={
                    str(k): float(v) for k, v in rrc.get("burst_rate_per_s_by_activity", {}).items()
                },
                burst_mb_by_activity={str(k): float(v) for k, v in rrc.get("burst_mb_by_activity", {}).items()},
                tail_gate=dict(rrc.get("tail_gate", {}) or {}),
            ),
            background_poisson=PoissonBackgroundParams1(
                lambda_per_s={str(k): float(v) for k, v in bg["lambda_per_s"].items()},
                data_mb_per_wake=float(bg["data_mb_per_wake"]),
                cpu_wake_W=float(bg["cpu_wake_W"]),
                cpu_wake_duration_s=float(bg["cpu_wake_duration_s"]),
            ),
            interaction=InteractionParams1(
                beta_screen_net_W=float(inter.get("beta_screen_net_W", 0.0)),
                beta_net_highcpu_W=float(inter.get("beta_net_highcpu_W", 0.0)),
                beta_screen_highcpu_W=float(inter.get("beta_screen_highcpu_W", 0.0)),
                cpu_high_threshold=float(inter.get("cpu_high_threshold", 0.7)),
            ),
            dvfs=DVFSParams1(
                throttle_temp_C=float(dvfs.get("throttle_temp_C", 1e9)),
                slope_per_C=float(dvfs.get("slope_per_C", 0.0)),
                min_scale=float(dvfs.get("min_scale", 1.0)),
                power_exponent=float(dvfs.get("power_exponent", 1.0)),
                backlog_enabled=bool(dvfs.get("backlog_enabled", False)),
                backlog_tau_s=float(dvfs.get("backlog_tau_s", 30.0)),
            ),
            screen_markov=ScreenMarkovParams1(
                off_to_on_rate_per_s_by_activity={
                    str(k): float(v) for k, v in scr.get("off_to_on_rate_per_s_by_activity", {}).items()
                },
                on_to_off_rate_per_s_by_activity={
                    str(k): float(v) for k, v in scr.get("on_to_off_rate_per_s_by_activity", {}).items()
                },
                wake_brightness_nits=float(scr.get("wake_brightness_nits", 150.0)),
            ),
            signal_markov=SignalMarkovParams1(
                enabled_radio_modes=tuple(str(x) for x in sig.get("enabled_radio_modes", ["lte", "5g"])),
                rates_by_base={
                    str(base): {str(k): float(v) for k, v in rates.items()}
                    for base, rates in sig.get("rates_by_base", {}).items()
                },
            ),
        )


@dataclass
class PowerState1:
    """功耗模型内部状态（网络尾态计时等）。"""

    rrc_state: RRCState = "IDLE"
    tail_left_s: float = 0.0
    # no7：连续门控 tail state（0~1）。当启用 tail_gate 时用于指数衰减尾态。
    tail_x: float = 0.0
    # 信号当前状态（用于 signal jitter）；None 表示尚未初始化
    signal_quality: str | None = None
    signal_base: str | None = None
    # 屏幕当前状态（用于待机段随机亮屏）
    screen_on: bool = False
    # 上一步是否“外生强制亮屏”（seg.screen_on=True）。
    # 设计意图：场景 schedule 本身就包含 screen_on 的外生开关，
    # 当从“强制亮屏段”切到“场景标记为关屏段”时，应立刻回到 OFF 基线，
    # 再叠加随机亮屏（而不是把上一段的 ON 状态带入关屏段）。
    screen_forced: bool = False
    # no7：DVFS-backlog 闭环状态（单位：归一化 work）。>0 表示尚未完成的“工作量”积压。
    cpu_backlog: float = 0.0


class StatefulPowerModel1:
    """Stateful 功耗模型：按 dt 更新内部状态并输出功耗分解。"""

    def __init__(self, params: PowerParams1Stateful, *, seed: int = 0):
        self.params = params
        self._rng = np.random.default_rng(int(seed))
        self.state = PowerState1()

    def reset(self) -> None:
        self.state = PowerState1()

    def step(self, seg: Segment, *, dt_s: float, battery_temp_C: float | None = None) -> PowerBreakdown:
        """推进 dt，并返回该步的功耗分解。"""

        dt = float(dt_s)
        if dt <= 0.0:
            raise ValueError("dt_s must be > 0")

        # ---- 1) 基础/屏幕/前台 CPU/GPU/GPS ----
        base_w = float(self.params.base_W)

        # 屏幕：若场景强制点亮，则不引入随机切换；否则用 Markov 模型刻画“偶尔亮屏”
        activity_for_screen = str(getattr(seg, "activity", ""))
        forced = bool(seg.screen_on)
        if forced:
            self.state.screen_on = True
            self.state.screen_forced = True
            screen_on_eff = True
            brightness_eff = float(seg.brightness_nits)
        else:
            # 若上一段是“强制亮屏”，而当前段外生标记为关屏，
            # 则把屏幕状态重置为 OFF 作为新段基线（再叠加随机亮屏）。
            if bool(self.state.screen_forced):
                self.state.screen_on = False
            self.state.screen_forced = False

            # Markov：OFF<->ON
            lam_on = float(self.params.screen_markov.off_to_on_rate(activity_for_screen))
            lam_off = float(self.params.screen_markov.on_to_off_rate(activity_for_screen))
            if not bool(self.state.screen_on):
                p_on = 1.0 - float(np.exp(-lam_on * dt)) if lam_on > 0.0 else 0.0
                if float(self._rng.random()) < p_on:
                    self.state.screen_on = True
            else:
                p_off = 1.0 - float(np.exp(-lam_off * dt)) if lam_off > 0.0 else 0.0
                if float(self._rng.random()) < p_off:
                    self.state.screen_on = False

            screen_on_eff = bool(self.state.screen_on)
            brightness_eff = float(self.params.screen_markov.wake_brightness_nits) if screen_on_eff else 0.0

        screen_w = 0.0
        if screen_on_eff:
            # APL：优先使用场景显式输入；否则按 activity 做经验映射
            apl = float(getattr(seg, "screen_apl", float("nan")))
            if not np.isfinite(apl):
                apl = float(_default_screen_apl_by_activity(activity_for_screen))
            apl = _clamp01(apl)

            b = max(0.0, float(brightness_eff))
            ref = max(1e-6, float(self.params.screen.ref_nits))
            gb = max(0.1, float(self.params.screen.gamma_b))
            # 使 gamma_b=1 时严格退化为线性：P_bright = k*b
            bright_scale = (b / ref) ** (gb - 1.0) if b > 0.0 else 0.0
            p_bright = float(self.params.screen.k_W_per_nit) * b * bright_scale
            p_apl = float(self.params.screen.k_apl_W) * (apl ** max(0.1, float(self.params.screen.gamma_apl)))

            screen_w = float(self.params.screen.P0_W) + float(p_bright) + float(p_apl)
            screen_w = max(0.0, float(screen_w))

        # DVFS：温度 -> 频率缩放；功耗按 power_exponent 缩放（no7 建议），并可选 backlog 闭环
        dvfs_scale = float(self.params.dvfs.scale(battery_temp_C))
        dvfs_pow = float(dvfs_scale ** float(self.params.dvfs.power_exponent))

        cpu_load_in = _clamp01(float(seg.cpu_load))
        cpu_load_eff = cpu_load_in
        if bool(self.params.dvfs.backlog_enabled):
            # backlog 单位：归一化 work；cpu_load_in 表示在 f=1 下的“工作率”（work/s）
            f = max(1e-6, float(dvfs_scale))
            tau = max(1e-6, float(self.params.dvfs.backlog_tau_s))
            u_needed = cpu_load_in / f
            u_backlog = (float(self.state.cpu_backlog) / tau) / f
            u_util = min(1.0, max(float(u_needed), float(u_backlog)))
            service = f * u_util  # work/s
            self.state.cpu_backlog = max(0.0, float(self.state.cpu_backlog) + (cpu_load_in - service) * dt)
            cpu_load_eff = float(u_util)

        gpu_load_eff = _clamp01(float(seg.gpu_load))

        cpu_w = float(self.params.cpu.power_nominal_W(cpu_load_eff)) * dvfs_pow
        gpu_w = float(self.params.gpu.k_W) * (gpu_load_eff ** max(0.1, float(self.params.gpu.gamma))) * dvfs_pow
        cpu_w = max(0.0, float(cpu_w))
        gpu_w = max(0.0, float(gpu_w))
        gps_w = float(self.params.gps.P_W) if bool(seg.gps_on) else 0.0

        # ---- 2) 后台：基线 + Poisson 唤醒注入 ----
        bg_base_w = float(self.params.background_level_W.get(seg.background_level, 0.0))

        lam = float(self.params.background_poisson.rate(seg.background_level))
        n_wake = int(self._rng.poisson(lam * dt)) if lam > 0.0 else 0

        # 每次唤醒带来：少量数据 + CPU 额外能量
        data_bg_mb = float(n_wake) * float(self.params.background_poisson.data_mb_per_wake)
        e_cpu_bg_J = float(n_wake) * float(self.params.background_poisson.cpu_wake_W) * float(
            self.params.background_poisson.cpu_wake_duration_s
        )
        bg_extra_w = 0.0 if dt <= 0 else (e_cpu_bg_J / dt)
        background_w = max(0.0, bg_base_w + bg_extra_w)

        # ---- 3) 网络：RRC 状态机 + 吞吐驱动 ----
        mode = str(seg.radio_mode)

        # 信号抖动：仅对蜂窝类网络启用，Wi-Fi 默认不抖动（也可在配置中开启）
        base_sig = str(seg.signal_quality)
        if mode not in set(self.params.signal_markov.enabled_radio_modes):
            sig = base_sig
            self.state.signal_quality = sig
            self.state.signal_base = base_sig
        else:
            if self.state.signal_base != base_sig or self.state.signal_quality is None:
                # 基线改变或首次进入：重置到基线状态，避免跨段“串味”
                self.state.signal_base = base_sig
                self.state.signal_quality = base_sig

            gp, pg = self.params.signal_markov.rates(base_sig)
            cur = str(self.state.signal_quality)
            if cur == "good":
                p = 1.0 - float(np.exp(-gp * dt)) if gp > 0.0 else 0.0
                if float(self._rng.random()) < p:
                    cur = "poor"
            else:
                p = 1.0 - float(np.exp(-pg * dt)) if pg > 0.0 else 0.0
                if float(self._rng.random()) < p:
                    cur = "good"
            self.state.signal_quality = cur
            sig = cur

        activity = str(seg.net_activity)

        # 前台数据：两种入口（按“数据可得性优先”）
        #
        # (A) 若场景/观测已直接给出平均吞吐（net_throughput_MBps），则视为连续输入 q(t)，
        #     覆盖离散映射 (net_activity -> throughput)，并关闭 Poisson 突发生成项，避免双重计数。
        # (B) 否则使用离散映射 + Poisson 突发（用于刻画“网页/社交的短时 burst + 尾态放大”）。
        q_override = float(getattr(seg, "net_throughput_MBps", float("nan")))
        if np.isfinite(q_override):
            d_fg_base = max(0.0, float(q_override))
            burst_rate = 0.0
            burst_mb = 0.0
            n_burst = 0
        else:
            d_fg_base = float(self.params.rrc.throughput_MBps(activity))
            burst_rate = float(self.params.rrc.burst_rate_per_s(activity))
            burst_mb = float(self.params.rrc.burst_mb(activity))
            # 说明：即便 burst_mb=0，也保持采样，以便在做“消融/对比”时使用共同随机数（降低方差）。
            n_burst = int(self._rng.poisson(burst_rate * dt)) if burst_rate > 0.0 else 0

        data_fg_mb = d_fg_base * dt + float(n_burst) * float(burst_mb)
        d_fg = 0.0 if dt <= 0 else (data_fg_mb / dt)

        # 后台数据（Poisson 唤醒注入）
        d_bg = 0.0 if dt <= 0 else (data_bg_mb / dt)
        d_total = max(0.0, d_fg + d_bg)  # MB/s

        # 状态更新：
        # - 默认：固定时长 tail（与旧版一致）
        # - no7：连续门控 tail（指数衰减），并允许 τ 随强度变化
        gate = self.params.rrc.tail_gate or {}
        gate_enabled = bool(gate.get("enabled", False))
        if gate_enabled:
            # 强度 u：CPU/GPU + 网络强度的加权组合（权重不需要很精确；可在敏感性里说明稳健性）
            w_cpu = float(gate.get("omega_cpu", 0.45))
            w_gpu = float(gate.get("omega_gpu", 0.25))
            w_cpu = max(0.0, w_cpu)
            w_gpu = max(0.0, w_gpu)
            w_sum = w_cpu + w_gpu
            if w_sum > 1.0:
                # 若给定权重和>1，则归一化并把网络权重置 0（避免负权）
                w_cpu /= w_sum
                w_gpu /= w_sum
                w_net = 0.0
            else:
                w_net = 1.0 - w_sum

            d0 = max(1e-6, float(gate.get("d0_MBps", 1.0)))
            u_net = float(d_total) / (float(d_total) + d0)
            u = w_cpu * float(cpu_load_eff) + w_gpu * float(gpu_load_eff) + w_net * float(u_net)
            u = _clamp01(u)

            u0 = float(gate.get("u0", 0.45))
            du = float(gate.get("delta_u", 0.12))
            du = max(1e-6, du)
            g = _sigmoid((u - u0) / du)

            tau_low = float((gate.get("tau_low_s", {}) or {}).get(mode, self.params.rrc.tau_tail(mode)))
            tau_high = float((gate.get("tau_high_s", {}) or {}).get(mode, self.params.rrc.tau_tail(mode)))
            tau_low = max(1e-3, tau_low)
            tau_high = max(tau_low, tau_high)
            tau = tau_low + (tau_high - tau_low) * float(g)

            if d_total > 0.0:
                self.state.tail_x = 1.0
                self.state.rrc_state = "CONNECTED"
            else:
                decay = float(np.exp(-dt / tau)) if tau > 0 else 0.0
                self.state.tail_x = float(self.state.tail_x) * decay
                eps = float(gate.get("tail_eps", 0.01))
                self.state.rrc_state = "TAIL" if float(self.state.tail_x) > eps else "IDLE"

            p_idle = float(self.params.rrc.p_state(mode, "IDLE"))
            p_tail = float(self.params.rrc.p_state(mode, "TAIL"))
            p_conn = float(self.params.rrc.p_state(mode, "CONNECTED"))
            p_state = p_conn if self.state.rrc_state == "CONNECTED" else (p_idle + float(self.state.tail_x) * (p_tail - p_idle))
        else:
            # 固定 tail：有数据 => CONNECTED；无数据 => CONNECTED->TAIL->IDLE
            if d_total > 0.0:
                self.state.rrc_state = "CONNECTED"
                self.state.tail_left_s = float(self.params.rrc.tau_tail(mode))
            else:
                if self.state.rrc_state == "CONNECTED":
                    self.state.rrc_state = "TAIL"
                    self.state.tail_left_s = float(self.params.rrc.tau_tail(mode))
                elif self.state.rrc_state == "TAIL":
                    self.state.tail_left_s = float(self.state.tail_left_s) - dt
                    if self.state.tail_left_s <= 0.0:
                        self.state.rrc_state = "IDLE"
                        self.state.tail_left_s = 0.0

            p_state = float(self.params.rrc.p_state(mode, self.state.rrc_state))

        e_per_mb = float(self.params.rrc.e_per_mb(mode, sig))
        p_data = e_per_mb * d_total
        radio_w = max(0.0, p_state + p_data)

        # ---- 4) 交互项（协同作用） ----
        th = float(self.params.interaction.cpu_high_threshold)
        cpu_high = float(cpu_load_eff) > th
        net_active = self.state.rrc_state != "IDLE"
        interaction_w = 0.0
        if bool(screen_on_eff) and net_active:
            interaction_w += float(self.params.interaction.beta_screen_net_W)
        if net_active and cpu_high:
            interaction_w += float(self.params.interaction.beta_net_highcpu_W)
        if bool(screen_on_eff) and cpu_high:
            interaction_w += float(self.params.interaction.beta_screen_highcpu_W)

        return PowerBreakdown(
            base_w=float(base_w),
            screen_w=float(screen_w),
            cpu_w=float(cpu_w),
            gpu_w=float(gpu_w),
            radio_w=float(radio_w),
            gps_w=float(gps_w),
            background_w=float(background_w),
            interaction_w=float(interaction_w),
            other_w=0.0,
        )
