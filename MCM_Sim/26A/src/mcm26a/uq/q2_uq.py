"""Q2 不确定性量化（UQ）：对关键“功耗 + 电池”参数做采样，并传播到 TTE 分布。

定位：
- 赛题要求量化不确定性、做敏感性分析；
- 在缺少真实手机测量数据时，用“合理先验区间”演示方法，并在论文中明确说明可校准/可替换。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from mcm26a.battery.model3_aging import BatteryParams3Aging
from mcm26a.power.model0 import GPSParams0
from mcm26a.power.model1_stateful import (
    CPUParams1,
    DVFSParams1,
    InteractionParams1,
    LoadParams1,
    PoissonBackgroundParams1,
    PowerParams1Stateful,
    RRCParams1,
    ScreenParams1,
)


def _uniform(rng: random.Random, lo: float, hi: float) -> float:
    return lo + (hi - lo) * rng.random()


def _log_uniform(rng: random.Random, lo: float, hi: float) -> float:
    """对正参数的 log-uniform 抽样：更符合“尺度不确定性”的建模直觉（no7 建议）。"""

    lo = float(lo)
    hi = float(hi)
    if lo <= 0.0 or hi <= 0.0 or hi < lo:
        raise ValueError("log-uniform 需要 0 < lo <= hi")
    u = rng.random()
    return lo * ((hi / lo) ** u)


@dataclass(frozen=True)
class Q2UQSample:
    """Q2 抽样参数：尽量用“尺度因子”降低维度。"""

    # 电池（Model-3）不确定性
    batt_capacity_scale: float
    batt_r0_scale: float
    batt_r1_scale: float
    v_cut_V: float
    soc_min: float

    # 功耗（stateful）不确定性
    # 说明：默认我们把“电源转换效率/PMIC 损耗”吸收到功耗参数里；
    # 为对齐 no7 的“显式 η_PMIC”写法，这里额外引入一个等效效率因子：
    #   P_batt ≈ P_load / η_PMIC
    # 其中 η_PMIC<=1 表示能量转换损耗更大。
    # 若你已用真实手机数据完成端到端校准，可把 eta_pmic 固定为 1（或移除该维度）。
    eta_pmic: float
    base_scale: float
    screen_scale: float
    cpu_scale: float
    gpu_scale: float
    gps_scale: float
    background_base_scale: float

    rrc_state_scale: float
    rrc_data_scale: float
    rrc_tail_scale: float
    poor_signal_psi_scale: float

    bg_lambda_scale: float
    interaction_scale: float


def sample_q2_uq(rng: random.Random) -> Q2UQSample:
    """生成一组“无数据时的合理先验”抽样值。"""

    # 题面未给的阈值参数：用“基准值 + 区间/离散扫描”更稳健（no7/no6 建议）
    v_cut = _uniform(rng, 3.2, 3.4)
    soc_min = float(rng.choice([0.0, 0.03, 0.05, 0.10]))

    return Q2UQSample(
        batt_capacity_scale=_log_uniform(rng, 0.90, 1.10),
        batt_r0_scale=_log_uniform(rng, 0.80, 1.30),
        batt_r1_scale=_log_uniform(rng, 0.80, 1.30),
        v_cut_V=float(v_cut),
        soc_min=float(soc_min),
        # no7：η0（等效 η_PMIC）建议用更保守的 0.90~0.95
        eta_pmic=_uniform(rng, 0.90, 0.95),
        base_scale=_log_uniform(rng, 0.70, 1.30),
        screen_scale=_log_uniform(rng, 0.70, 1.30),
        cpu_scale=_log_uniform(rng, 0.60, 1.40),
        gpu_scale=_log_uniform(rng, 0.60, 1.40),
        gps_scale=_log_uniform(rng, 0.70, 1.30),
        background_base_scale=_log_uniform(rng, 0.70, 1.30),
        rrc_state_scale=_log_uniform(rng, 0.60, 1.60),
        rrc_data_scale=_log_uniform(rng, 0.60, 1.60),
        rrc_tail_scale=_log_uniform(rng, 0.70, 1.30),
        poor_signal_psi_scale=_log_uniform(rng, 0.90, 1.30),
        bg_lambda_scale=_log_uniform(rng, 0.50, 2.00),
        interaction_scale=_uniform(rng, 0.00, 1.60),
    )


def apply_q2_uq_sample(
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    s: Q2UQSample,
) -> tuple[PowerParams1Stateful, BatteryParams3Aging]:
    """把抽样值应用到参数集，得到一组“抽样后的功耗+电池参数”。"""

    # ---- 电池 ----
    batt = replace(
        base_batt,
        capacity_Ah_ref=float(base_batt.capacity_Ah_ref) * float(s.batt_capacity_scale),
        r0_ohm_ref=float(base_batt.r0_ohm_ref) * float(s.batt_r0_scale),
        r1_ohm_ref=float(base_batt.r1_ohm_ref) * float(s.batt_r1_scale),
        v_cut_V=float(s.v_cut_V),
        soc_min=float(s.soc_min),
    )

    # ---- 电源链效率（等效）：把“负载功耗”映射为“电池侧功耗” ----
    # eta<=0 属于非法输入，这里做最小保护，避免除 0。
    eta = max(float(s.eta_pmic), 1e-6)
    pmic_scale = 1.0 / eta

    # ---- 功耗：基础/屏幕/CPU/GPU/GPS ----
    screen = ScreenParams1(
        P0_W=float(base_power.screen.P0_W) * float(s.screen_scale) * pmic_scale,
        k_W_per_nit=float(base_power.screen.k_W_per_nit) * float(s.screen_scale) * pmic_scale,
        ref_nits=float(base_power.screen.ref_nits),
        gamma_b=float(base_power.screen.gamma_b),
        k_apl_W=float(base_power.screen.k_apl_W) * float(s.screen_scale) * pmic_scale,
        gamma_apl=float(base_power.screen.gamma_apl),
    )

    cpu0 = base_power.cpu
    cpu = CPUParams1(
        k_W=float(cpu0.k_W) * float(s.cpu_scale) * pmic_scale,
        gamma=float(cpu0.gamma),
        k_lit_W=(None if cpu0.k_lit_W is None else float(cpu0.k_lit_W) * float(s.cpu_scale) * pmic_scale),
        k_big_W=(None if cpu0.k_big_W is None else float(cpu0.k_big_W) * float(s.cpu_scale) * pmic_scale),
        gamma_lit=float(cpu0.gamma_lit),
        gamma_big=float(cpu0.gamma_big),
        u_switch=float(cpu0.u_switch),
    )

    gpu0 = base_power.gpu
    gpu = LoadParams1(k_W=float(gpu0.k_W) * float(s.gpu_scale) * pmic_scale, gamma=float(gpu0.gamma))

    gps = GPSParams0(P_W=float(base_power.gps.P_W) * float(s.gps_scale) * pmic_scale)

    bg_level = {k: float(v) * float(s.background_base_scale) * pmic_scale for k, v in base_power.background_level_W.items()}

    # ---- RRC ----
    tau_tail = {k: float(v) * float(s.rrc_tail_scale) for k, v in base_power.rrc.tau_tail_s.items()}
    p_state = {
        mode: {st: float(pw) * float(s.rrc_state_scale) * pmic_scale for st, pw in table.items()}
        for mode, table in base_power.rrc.p_state_W.items()
    }
    e_per_mb = {k: float(v) * float(s.rrc_data_scale) * pmic_scale for k, v in base_power.rrc.e_per_mb_J.items()}

    # 弱信号惩罚：保持 good=1，只缩放 poor（避免把所有信号都一起抬升）
    signal_psi = dict(base_power.rrc.signal_psi)
    if "poor" in signal_psi:
        signal_psi["poor"] = float(signal_psi["poor"]) * float(s.poor_signal_psi_scale)

    # 连续门控尾态（no7）：只缩放 τ（保持 u0/Δu/权重等结构不变）
    tail_gate = dict(base_power.rrc.tail_gate) if base_power.rrc.tail_gate else {}
    if tail_gate:
        for key in ["tau_low_s", "tau_high_s"]:
            if key in tail_gate and isinstance(tail_gate.get(key), dict):
                tail_gate[key] = {k: float(v) * float(s.rrc_tail_scale) for k, v in (tail_gate.get(key) or {}).items()}

    rrc = RRCParams1(
        tau_tail_s=tau_tail,
        p_state_W=p_state,
        e_per_mb_J=e_per_mb,
        signal_psi=signal_psi,
        throughput_MBps_by_activity=dict(base_power.rrc.throughput_MBps_by_activity),
        burst_rate_per_s_by_activity=dict(base_power.rrc.burst_rate_per_s_by_activity),
        burst_mb_by_activity=dict(base_power.rrc.burst_mb_by_activity),
        tail_gate=tail_gate,
    )

    # ---- 后台 Poisson ----
    bg_poisson = PoissonBackgroundParams1(
        lambda_per_s={k: float(v) * float(s.bg_lambda_scale) for k, v in base_power.background_poisson.lambda_per_s.items()},
        data_mb_per_wake=float(base_power.background_poisson.data_mb_per_wake),
        cpu_wake_W=float(base_power.background_poisson.cpu_wake_W) * pmic_scale,
        cpu_wake_duration_s=float(base_power.background_poisson.cpu_wake_duration_s),
    )

    # ---- 交互项 ----
    inter0 = base_power.interaction
    inter = InteractionParams1(
        beta_screen_net_W=float(inter0.beta_screen_net_W) * float(s.interaction_scale) * pmic_scale,
        beta_net_highcpu_W=float(inter0.beta_net_highcpu_W) * float(s.interaction_scale) * pmic_scale,
        beta_screen_highcpu_W=float(inter0.beta_screen_highcpu_W) * float(s.interaction_scale) * pmic_scale,
        cpu_high_threshold=float(inter0.cpu_high_threshold),
    )

    dvfs = DVFSParams1(
        throttle_temp_C=float(base_power.dvfs.throttle_temp_C),
        slope_per_C=float(base_power.dvfs.slope_per_C),
        min_scale=float(base_power.dvfs.min_scale),
        power_exponent=float(base_power.dvfs.power_exponent),
        backlog_enabled=bool(base_power.dvfs.backlog_enabled),
        backlog_tau_s=float(base_power.dvfs.backlog_tau_s),
    )

    power = PowerParams1Stateful(
        base_W=float(base_power.base_W) * float(s.base_scale) * pmic_scale,
        screen=screen,
        cpu=cpu,
        gpu=gpu,
        gps=gps,
        background_level_W=bg_level,
        rrc=rrc,
        background_poisson=bg_poisson,
        interaction=inter,
        dvfs=dvfs,
        screen_markov=base_power.screen_markov,
        signal_markov=base_power.signal_markov,
    )
    return power, batt
