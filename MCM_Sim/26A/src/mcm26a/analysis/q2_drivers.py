"""Q2 drivers 工具：把“策略动作 drivers”扩展到“机制/组件 drivers”。

设计目标（对齐赛题 Q2）：
- 识别导致续航快速下降的具体 drivers，并给出“surprisingly little”的证据；
- drivers 不仅限于用户策略动作（如降亮度），也包括模型内部机制（如 RRC 尾态）
  与组件耗能（如屏幕/CPU/无线/后台）。

实现原则：
- 通过修改参数实现“消融/对照”，尽量保持随机数消耗一致（CRN，共同随机数），降低方差；
- 不追求“真实手机一定能做到”的反事实，只追求“边际影响”可解释、可复现、可写进论文。
"""

from __future__ import annotations

from dataclasses import replace

from mcm26a.power.model1_stateful import DVFSParams1, InteractionParams1, PoissonBackgroundParams1, PowerParams1Stateful, RRCParams1


def mechanism_driver_specs() -> list[tuple[str, str]]:
    """机制 drivers 列表：逐项“去掉机制”观察 ΔTTE。

    说明：
    - 这些 drivers 更贴近题面中的 interplay / unpredictable behavior；
    - 某些机制在某些场景影响接近 0，可作为“surprisingly little”的证据。
    """

    return [
        ("no_rrc_tail", "去掉 RRC 尾态能量"),
        ("no_tail_gate", "关闭连续尾态门控（回退固定 tail）"),
        ("no_signal_penalty", "去掉弱信号惩罚"),
        ("no_bg_wake", "去掉后台唤醒脉冲"),
        ("no_interaction", "去掉交互项（协同作用）"),
        ("no_fg_bursts", "去掉前台网络突发（仅保留平稳吞吐）"),
        ("no_screen_markov", "去掉待机随机亮屏"),
        ("no_signal_jitter", "去掉蜂窝信号抖动"),
        ("no_thermal_throttle", "去掉热节流（简化温度-功耗反馈）"),
        ("no_backlog", "关闭 backlog（仅保留瞬时功耗缩放）"),
    ]


def component_driver_specs() -> list[tuple[str, str]]:
    """组件 drivers 列表：把某个组件的“功耗贡献”置零，观察 ΔTTE。

    说明：
    - 这是“解释差异/找 drivers”的直接证据链：哪个组件被移除后 ΔTTE 最大，就越可能是快速掉电主因；
    - 这里的“置零”是理想化反事实，用于敏感性/归因，不等同于真实手机可实现策略。
    """

    return [
        ("no_base", "去掉基础功耗"),
        ("no_screen", "去掉屏幕功耗"),
        ("no_cpu_gpu", "去掉 CPU/GPU 前台功耗"),
        ("no_radio", "去掉无线功耗（状态+数据）"),
        ("no_gps", "去掉 GPS 功耗"),
        ("no_background_total", "去掉后台功耗（基线+唤醒）"),
        ("no_interaction", "去掉交互项（协同作用）"),
    ]


def power_mechanism_variant(p: PowerParams1Stateful, *, mech_id: str) -> PowerParams1Stateful:
    """构造“机制消融/对照”的功耗参数（尽量保持随机数消耗一致）。"""

    if mech_id == "no_rrc_tail":
        tau = {k: 0.0 for k in p.rrc.tau_tail_s.keys()}
        p_state = {}
        for mode, table in p.rrc.p_state_W.items():
            idle = float(table.get("IDLE", 0.0))
            p_state[mode] = dict(table)
            p_state[mode]["TAIL"] = idle
        rrc = replace(p.rrc, tau_tail_s=tau, p_state_W=p_state)
        return replace(p, rrc=rrc)

    if mech_id == "no_tail_gate":
        # 关闭连续门控尾态：回退到固定 tail_left_s（仍保留 burst/吞吐等随机性）
        rrc = replace(p.rrc, tail_gate={})
        return replace(p, rrc=rrc)

    if mech_id == "no_signal_penalty":
        psi = dict(p.rrc.signal_psi)
        psi["poor"] = 1.0
        rrc = replace(p.rrc, signal_psi=psi)
        return replace(p, rrc=rrc)

    if mech_id == "no_bg_wake":
        # 保持 lambda 不变，但把每次唤醒的“能量与数据注入”置零（保留随机数流，便于 CRN）。
        bg = replace(p.background_poisson, data_mb_per_wake=0.0, cpu_wake_W=0.0)
        return replace(p, background_poisson=bg)

    if mech_id == "no_interaction":
        inter = replace(p.interaction, beta_screen_net_W=0.0, beta_net_highcpu_W=0.0, beta_screen_highcpu_W=0.0)
        return replace(p, interaction=inter)

    if mech_id == "no_fg_bursts":
        burst_mb = {k: 0.0 for k in p.rrc.burst_mb_by_activity.keys()}
        rrc = replace(p.rrc, burst_mb_by_activity=burst_mb)
        return replace(p, rrc=rrc)

    if mech_id == "no_screen_markov":
        scr = replace(
            p.screen_markov,
            off_to_on_rate_per_s_by_activity={k: 0.0 for k in p.screen_markov.off_to_on_rate_per_s_by_activity.keys()},
            on_to_off_rate_per_s_by_activity={k: 0.0 for k in p.screen_markov.on_to_off_rate_per_s_by_activity.keys()},
        )
        return replace(p, screen_markov=scr)

    if mech_id == "no_signal_jitter":
        # 保留 enabled_radio_modes，但把转移率置 0（仍消耗随机数，但不会切换状态）。
        rates = {}
        for base, cfg in p.signal_markov.rates_by_base.items():
            rates[str(base)] = {"good_to_poor": 0.0, "poor_to_good": 0.0}
        sig = replace(p.signal_markov, rates_by_base=rates)
        return replace(p, signal_markov=sig)

    if mech_id == "no_thermal_throttle":
        # 把“热节流”关闭：scale 恒为 1（保守做法：不改其它功耗项）。
        dvfs = replace(p.dvfs, throttle_temp_C=1e9, slope_per_C=0.0, min_scale=1.0)
        return replace(p, dvfs=dvfs)

    if mech_id == "no_backlog":
        dvfs = replace(p.dvfs, backlog_enabled=False)
        return replace(p, dvfs=dvfs)

    raise ValueError(f"unknown mech_id: {mech_id!r}")


def power_component_variant(p: PowerParams1Stateful, *, comp_id: str) -> PowerParams1Stateful:
    """构造“组件级对照”功耗参数：把某个组件功耗贡献置零。"""

    if comp_id == "no_base":
        return replace(p, base_W=0.0)

    if comp_id == "no_screen":
        scr = replace(p.screen, P0_W=0.0, k_W_per_nit=0.0, k_apl_W=0.0)
        return replace(p, screen=scr)

    if comp_id == "no_cpu_gpu":
        cpu = replace(p.cpu, k_W=0.0, k_lit_W=(0.0 if p.cpu.k_lit_W is not None else None), k_big_W=(0.0 if p.cpu.k_big_W is not None else None))
        gpu = replace(p.gpu, k_W=0.0)
        return replace(p, cpu=cpu, gpu=gpu)

    if comp_id == "no_radio":
        # 注意：保留吞吐/尾态/弱信号等“状态变化”，只把无线子系统的功率贡献置零，
        # 从而与 energy_components_Wh 中的 radio_Wh 对齐，并保持 CRN。
        p_state = {mode: {st: 0.0 for st in table.keys()} for mode, table in p.rrc.p_state_W.items()}
        e_per_mb = {k: 0.0 for k in p.rrc.e_per_mb_J.keys()}
        rrc = RRCParams1(
            tau_tail_s=dict(p.rrc.tau_tail_s),
            p_state_W=p_state,
            e_per_mb_J=e_per_mb,
            signal_psi=dict(p.rrc.signal_psi),
            throughput_MBps_by_activity=dict(p.rrc.throughput_MBps_by_activity),
            burst_rate_per_s_by_activity=dict(p.rrc.burst_rate_per_s_by_activity),
            burst_mb_by_activity=dict(p.rrc.burst_mb_by_activity),
            tail_gate=dict(p.rrc.tail_gate),
        )
        return replace(p, rrc=rrc)

    if comp_id == "no_gps":
        gps = replace(p.gps, P_W=0.0)
        return replace(p, gps=gps)

    if comp_id == "no_background_total":
        # 1) 基线后台功耗置零；2) Poisson 唤醒仍采样（lambda 保持），但不注入数据与能量（保持 CRN）。
        bg_level = {k: 0.0 for k in p.background_level_W.keys()}
        bg = PoissonBackgroundParams1(
            lambda_per_s=dict(p.background_poisson.lambda_per_s),
            data_mb_per_wake=0.0,
            cpu_wake_W=0.0,
            cpu_wake_duration_s=float(p.background_poisson.cpu_wake_duration_s),
        )
        return replace(p, background_level_W=bg_level, background_poisson=bg)

    if comp_id == "no_interaction":
        inter = InteractionParams1(
            beta_screen_net_W=0.0,
            beta_net_highcpu_W=0.0,
            beta_screen_highcpu_W=0.0,
            cpu_high_threshold=float(p.interaction.cpu_high_threshold),
        )
        return replace(p, interaction=inter)

    raise ValueError(f"unknown comp_id: {comp_id!r}")
