"""Q3：敏感性与假设检验（局部/全局/消融/老化扫描）。

本模块聚焦赛题第 3 问（Sensitivity and Assumptions）：
- 参数值：在合理先验区间内扰动关键参数，观察 TTE/欠压概率等输出如何变化；
- 建模假设：通过结构消融（ablation）检验某些机制是否“必要/可忽略”；
- 使用波动：对同一参数下的随机过程（后台唤醒、信号抖动、亮屏偶发等）做重复仿真，量化不可预测性。

工程约定：
- 时间单位统一用秒（s），但最终报告常用小时（h）展示；
- 为稳定性：敏感性计算通常对同一参数样本做多次随机种子重复并取平均；
- 本模块只做“计算”，不负责画图或写文件（由 scripts/ 与 viz/ 调用）。
"""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Iterable, Literal

import numpy as np

from mcm26a.analysis.sensitivity import prcc, spearman_corr
from mcm26a.analysis.stats import quantile
from mcm26a.analysis.q2_drivers import mechanism_driver_specs, power_mechanism_variant
from mcm26a.battery.model1_ecm import BatteryParams1ECM
from mcm26a.battery.model1_ecm2rc import BatteryParams1ECM2RC
from mcm26a.battery.model2_thermal import BatteryParams2Thermal
from mcm26a.battery.model3_aging import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Scenario
from mcm26a.sim import simulate_model1_ecm, simulate_model2_thermal, simulate_model3_aging
from mcm26a.sim.model1_2rc import simulate_model1_ecm2rc
from mcm26a.utils import PiecewiseLinearCurve
from mcm26a.uq.q2_uq import Q2UQSample, apply_q2_uq_sample


BatteryModelName = Literal["model1", "model1_2rc", "model2", "model3"]


def q3_param_names() -> list[str]:
    """全局敏感性（PRCC/Spearman）使用的参数列顺序。

说明：
- 这里沿用 Q2 的“尺度因子”抽样设计，优点是维度低、可解释、与现有代码完全对齐；
- 若后续引入更多可辨识参数，可在此处追加并同步更新采样函数与可视化映射。
"""

    return [
        # battery
        "batt_capacity_scale",
        "batt_r0_scale",
        "batt_r1_scale",
        "v_cut_V",
        "soc_min",
        # aging state/assumption (no7)
        "soh",
        "alpha_r",
        # power chain (effective)
        "eta_pmic",
        # power (basic)
        "base_scale",
        "screen_scale",
        "cpu_scale",
        "gpu_scale",
        "gps_scale",
        "background_base_scale",
        # radio
        "rrc_state_scale",
        "rrc_data_scale",
        "rrc_tail_scale",
        "poor_signal_psi_scale",
        # stochastic + interaction
        "bg_lambda_scale",
        "interaction_scale",
    ]


def q3_param_label_zh(name: str) -> str:
    """参数名 -> 中文短标签（用于画图/表格）。"""

    m = {
        # 电池端
        "batt_capacity_scale": "容量",
        "batt_r0_scale": "R0",
        "batt_r1_scale": "R1",
        "v_cut_V": "V_cut",
        "soc_min": "SOC_min",
        "soh": "SOH",
        "alpha_r": "α_R",
        # 电源链
        "eta_pmic": "η_PMIC",
        # 负载功耗
        "base_scale": "基础",
        "screen_scale": "屏幕",
        "cpu_scale": "CPU",
        "gpu_scale": "GPU",
        "gps_scale": "GPS",
        "background_base_scale": "后台基线",
        # 无线与随机过程
        "rrc_state_scale": "无线状态",
        "rrc_data_scale": "无线数据",
        "rrc_tail_scale": "尾态时长",
        "poor_signal_psi_scale": "弱信号惩罚",
        "bg_lambda_scale": "后台唤醒频率",
        "interaction_scale": "交互项",
    }
    return m.get(str(name), str(name))


def q3_param_label_en(name: str) -> str:
    """参数名 -> 英文短标签（用于画图/表格）。"""

    m = {
        # battery side
        "batt_capacity_scale": "Capacity",
        "batt_r0_scale": "R0",
        "batt_r1_scale": "R1",
        "v_cut_V": "V_cut",
        "soc_min": "SOC_min",
        "soh": "SOH",
        "alpha_r": "alpha_R",
        # power chain
        "eta_pmic": "eta_PMIC",
        # load power
        "base_scale": "P_base",
        "screen_scale": "Screen",
        "cpu_scale": "CPU",
        "gpu_scale": "GPU",
        "gps_scale": "GPS",
        "background_base_scale": "BG base",
        # radio + stochastic
        "rrc_state_scale": "RRC state",
        "rrc_data_scale": "RRC data",
        "rrc_tail_scale": "Tail time",
        "poor_signal_psi_scale": "Poor-signal penalty",
        "bg_lambda_scale": "BG wake rate",
        "interaction_scale": "Interaction",
    }
    return m.get(str(name), str(name))


def sample_q3_uq(rng: random.Random, *, prior_mode: Literal["default", "tight"] = "default") -> Q2UQSample:
    """Q3 的先验抽样（以 no7 的建议范围为主）。

注：
- 复用 Q2UQSample 结构，避免“两个不一致的参数空间”；
- 若未来需要与 Q2 完全一致，可改为直接调用 sample_q2_uq。

prior_mode：
- default：较宽先验（偏“未充分标定/跨设备”），用于展示参数不确定性可能主导；
- tight：较窄先验（偏“已标定到某一设备/同一机型”），用于 sanity check：
  若先验收窄，参数项应下降、使用波动项的相对占比应上升（符合直觉）。
"""

    def _u(lo: float, hi: float) -> float:
        return lo + (hi - lo) * rng.random()

    def _logu(lo: float, hi: float) -> float:
        """对正参数的 log-uniform 抽样：更符合“尺度不确定性”的建模直觉（no7 建议）。"""

        lo = float(lo)
        hi = float(hi)
        if lo <= 0.0 or hi <= 0.0 or hi < lo:
            raise ValueError("log-uniform 需要 0 < lo <= hi")
        u = rng.random()
        return lo * ((hi / lo) ** u)

    mode = str(prior_mode)
    if mode not in ("default", "tight"):
        raise ValueError(f"unknown prior_mode: {prior_mode!r}")

    if mode == "tight":
        # “已标定到单一设备/同一机型”的更窄先验（用于稳定性/方向验证，不代表唯一正确范围）
        v_cut = _u(3.27, 3.33)
        soc_min = float(rng.choice([0.03, 0.05]))
        batt_capacity = _logu(0.97, 1.03)
        batt_r0 = _logu(0.95, 1.05)
        batt_r1 = _logu(0.95, 1.05)
        eta_pmic = _u(0.92, 0.95)
        base = _logu(0.90, 1.10)
        screen = _logu(0.90, 1.10)
        cpu = _logu(0.90, 1.10)
        gpu = _logu(0.90, 1.10)
        gps = _logu(0.90, 1.10)
        bg_base = _logu(0.90, 1.10)
        rrc_state = _logu(0.90, 1.10)
        rrc_data = _logu(0.90, 1.10)
        rrc_tail = _logu(0.90, 1.10)
        poor_sig = _logu(0.95, 1.05)
        bg_lambda = _logu(0.80, 1.25)
        inter = _u(0.00, 1.00)
    else:
        v_cut = _u(3.2, 3.4)
        soc_min = float(rng.choice([0.0, 0.03, 0.05, 0.10]))
        batt_capacity = _logu(0.90, 1.10)
        batt_r0 = _logu(0.80, 1.30)
        batt_r1 = _logu(0.80, 1.30)
        # no7 建议：η0（等效 η_PMIC）用更保守的 0.90~0.95 先验（也可在论文中说明可替换为实测）
        eta_pmic = _u(0.90, 0.95)
        base = _logu(0.70, 1.30)
        screen = _logu(0.70, 1.30)
        cpu = _logu(0.60, 1.40)
        gpu = _logu(0.60, 1.40)
        gps = _logu(0.70, 1.30)
        bg_base = _logu(0.70, 1.30)
        rrc_state = _logu(0.60, 1.60)
        rrc_data = _logu(0.60, 1.60)
        rrc_tail = _logu(0.70, 1.30)
        poor_sig = _logu(0.90, 1.30)
        bg_lambda = _logu(0.50, 2.00)
        inter = _u(0.00, 1.60)

    return Q2UQSample(
        batt_capacity_scale=float(batt_capacity),
        batt_r0_scale=float(batt_r0),
        batt_r1_scale=float(batt_r1),
        v_cut_V=float(v_cut),
        soc_min=float(soc_min),
        eta_pmic=float(eta_pmic),
        base_scale=float(base),
        screen_scale=float(screen),
        cpu_scale=float(cpu),
        gpu_scale=float(gpu),
        gps_scale=float(gps),
        background_base_scale=float(bg_base),
        rrc_state_scale=float(rrc_state),
        rrc_data_scale=float(rrc_data),
        rrc_tail_scale=float(rrc_tail),
        poor_signal_psi_scale=float(poor_sig),
        bg_lambda_scale=float(bg_lambda),
        interaction_scale=float(inter),
    )


def sample_to_row(sample: Q2UQSample, *, soh: float, alpha_r: float) -> dict[str, float]:
    """把抽样对象转为“参数表的一行”（用于 PRCC/Spearman）。"""

    return {
        "batt_capacity_scale": float(sample.batt_capacity_scale),
        "batt_r0_scale": float(sample.batt_r0_scale),
        "batt_r1_scale": float(sample.batt_r1_scale),
        "v_cut_V": float(sample.v_cut_V),
        "soc_min": float(sample.soc_min),
        "soh": float(soh),
        "alpha_r": float(alpha_r),
        "eta_pmic": float(sample.eta_pmic),
        "base_scale": float(sample.base_scale),
        "screen_scale": float(sample.screen_scale),
        "cpu_scale": float(sample.cpu_scale),
        "gpu_scale": float(sample.gpu_scale),
        "gps_scale": float(sample.gps_scale),
        "background_base_scale": float(sample.background_base_scale),
        "rrc_state_scale": float(sample.rrc_state_scale),
        "rrc_data_scale": float(sample.rrc_data_scale),
        "rrc_tail_scale": float(sample.rrc_tail_scale),
        "poor_signal_psi_scale": float(sample.poor_signal_psi_scale),
        "bg_lambda_scale": float(sample.bg_lambda_scale),
        "interaction_scale": float(sample.interaction_scale),
    }


def _as_batt1_from_batt3(b: BatteryParams3Aging) -> BatteryParams1ECM:
    """把 Model-3 电池参数投影到 Model-1（去掉温度/老化）。"""

    return BatteryParams1ECM(
        capacity_Ah=float(b.capacity_Ah_ref),
        soc_min=float(b.soc_min),
        v_cut_V=float(b.v_cut_V),
        r0_ohm=float(b.r0_ohm_ref),
        r1_ohm=float(b.r1_ohm_ref),
        c1_F=float(b.c1_F),
        ocv=b.ocv,
        r0_curve=b.r0_curve_ref,
        r1_curve=b.r1_curve_ref,
    )


def _scale_curve(curve: PiecewiseLinearCurve, scale: float) -> PiecewiseLinearCurve:
    """把一条分段线性曲线按比例缩放 y 值（用于把总 R1 分解到快/慢支路）。"""

    s = float(scale)
    return PiecewiseLinearCurve(points=tuple((float(x), float(y) * s) for x, y in curve.points))


def _as_batt1_2rc_from_batt3(
    b: BatteryParams3Aging,
    *,
    r_split_fast: float = 0.45,
    tau_fast_ratio: float = 0.20,
    tau_slow_ratio: float = 5.0,
) -> BatteryParams1ECM2RC:
    """把 Model-3 电池参数投影到 Model-1（二阶极化 2RC）。

设计原则（用于 Q3“建模假设”对照）：
- 保持 OCV(SOC)、R0(SOC) 不变；
- 把“单一极化支路 R1||C1”拆成“快+慢”两条支路：
  - R1_fast + R2_slow = R1_total（同 SOC 下的等效极化电阻保持一致）；
  - 时间常数用 tau_fast/tau_slow 相对原 tau_base 做拉开（体现双时间尺度恢复）。
"""

    r_split_fast = float(r_split_fast)
    if not (0.0 < r_split_fast < 1.0):
        raise ValueError("r_split_fast 必须在 (0,1) 内")
    tau_fast_ratio = float(tau_fast_ratio)
    tau_slow_ratio = float(tau_slow_ratio)
    if tau_fast_ratio <= 0.0 or tau_slow_ratio <= 0.0:
        raise ValueError("tau_*_ratio 必须为正")

    r1_total = float(b.r1_ohm_ref)
    r1_fast = max(1e-12, r1_total * r_split_fast)
    r2_slow = max(1e-12, r1_total * (1.0 - r_split_fast))
    tau_base = float(b.r1_ohm_ref) * float(b.c1_F)
    tau_fast = max(1e-6, tau_base * tau_fast_ratio)
    tau_slow = max(1e-6, tau_base * tau_slow_ratio)
    c1_fast = float(tau_fast / r1_fast)
    c2_slow = float(tau_slow / r2_slow)

    r1_curve = _scale_curve(b.r1_curve_ref, r_split_fast) if b.r1_curve_ref is not None else None
    r2_curve = _scale_curve(b.r1_curve_ref, 1.0 - r_split_fast) if b.r1_curve_ref is not None else None

    return BatteryParams1ECM2RC(
        capacity_Ah=float(b.capacity_Ah_ref),
        soc_min=float(b.soc_min),
        v_cut_V=float(b.v_cut_V),
        r0_ohm=float(b.r0_ohm_ref),
        r1_ohm=float(r1_fast),
        c1_F=float(c1_fast),
        r2_ohm=float(r2_slow),
        c2_F=float(c2_slow),
        ocv=b.ocv,
        r0_curve=b.r0_curve_ref,
        r1_curve=r1_curve,
        r2_curve=r2_curve,
        # Q3 结构对照默认不启用其它“可解释增强项”，以免把对照变成“多机制混杂”
        rate_capacity_k_per_A=0.0,
        hyst_M_V=0.0,
        hyst_gamma=0.0,
        hyst_i_thresh_A=0.05,
        hyst_M_curve=None,
        hyst_relax_tau_s=0.0,
        diff_M_V=0.0,
        diff_gamma=0.0,
        diff_i_thresh_A=0.5,
        diff_soc_thresh=0.1,
        diff_v_thresh_V=0.0,
        diff_gate_soc_sigma=0.0,
        diff_gate_v_sigma_V=0.0,
        diff_gate_i_sigma_A=0.0,
        diff_relax_tau_s=0.0,
        diff_relax_tau_init_s=0.0,
        diff_relax_z_thresh=0.0,
        diff_relax_tau_mid_s=0.0,
        diff_relax_z_thresh_mid=0.0,
        diff_relax_tau_fast_s=0.0,
        diff_relax_v_thresh_V=0.0,
        diff_M_curve=None,
        diff_R_ohm=0.0,
        diff_R_curve=None,
    )


def _as_batt2_from_batt3(b: BatteryParams3Aging) -> BatteryParams2Thermal:
    """把 Model-3 电池参数投影到 Model-2（去掉老化）。"""

    return BatteryParams2Thermal(
        capacity_Ah_ref=float(b.capacity_Ah_ref),
        soc_min=float(b.soc_min),
        v_cut_V=float(b.v_cut_V),
        r0_ohm_ref=float(b.r0_ohm_ref),
        r1_ohm_ref=float(b.r1_ohm_ref),
        c1_F=float(b.c1_F),
        ocv=b.ocv,
        t_ref_C=float(b.t_ref_C),
        t0_C=float(b.t0_C),
        c_th_J_per_K=float(b.c_th_J_per_K),
        r_th_K_per_W=float(b.r_th_K_per_W),
        eta_device_heat=float(b.eta_device_heat),
        r0_temp_coeff_per_C=float(b.r0_temp_coeff_per_C),
        r1_temp_coeff_per_C=float(b.r1_temp_coeff_per_C),
        capacity_temp_coeff_per_C=float(b.capacity_temp_coeff_per_C),
        temp_min_C=float(b.temp_min_C),
        temp_max_C=float(b.temp_max_C),
        r0_curve_ref=b.r0_curve_ref,
        r1_curve_ref=b.r1_curve_ref,
    )


def simulate_tte_replicates(
    scenario: Scenario,
    *,
    power: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: Iterable[int],
    battery_model: BatteryModelName = "model3",
    cap_loss0_frac: float = 0.0,
    r0_growth0_frac: float = 0.0,
    r1_growth0_frac: float = 0.0,
) -> dict[str, object]:
    """在同一参数下做多次随机种子重复，返回统计量（TTE/终止原因）。"""

    tte_h_list: list[float] = []
    margin_list: list[float] = []
    temp_peak_list: list[float] = []
    temp_end_list: list[float] = []
    statuses: list[str] = []
    runs: list[dict[str, object]] = []

    for seed in seeds:
        pm = StatefulPowerModel1(power, seed=int(seed))

        if battery_model == "model3":
            res = simulate_model3_aging(
                scenario,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=batt,
                soc0=float(soc0),
                cap_loss0_frac=float(cap_loss0_frac),
                r0_growth0_frac=float(r0_growth0_frac),
                r1_growth0_frac=float(r1_growth0_frac),
                dt_s=float(dt_s),
            )
            tte_h = res.tte_h
            status = str(res.status)
            margin = float(res.min_headroom_margin)
            temp_peak = float(res.temp_peak_C)
            temp_end = float(res.temp_end_C)
        elif battery_model == "model2":
            b2 = _as_batt2_from_batt3(batt)
            res2 = simulate_model2_thermal(
                scenario,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=b2,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            tte_h = res2.tte_h
            status = str(res2.status)
            margin = float(res2.min_headroom_margin)
            temp_peak = float(res2.temp_peak_C)
            temp_end = float(res2.temp_end_C)
        elif battery_model == "model1":
            b1 = _as_batt1_from_batt3(batt)
            res1 = simulate_model1_ecm(
                scenario,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=b1,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            tte_h = res1.tte_h
            status = str(res1.status)
            margin = float(res1.min_headroom_margin)
            temp_peak = float(getattr(batt, "t0_C", float("nan")))
            temp_end = float(getattr(batt, "t0_C", float("nan")))
        elif battery_model == "model1_2rc":
            b2rc = _as_batt1_2rc_from_batt3(batt)
            res2rc = simulate_model1_ecm2rc(
                scenario,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=b2rc,
                soc0=float(soc0),
                dt_s=float(dt_s),
            )
            tte_h = res2rc.tte_h
            status = str(res2rc.status)
            margin = float(res2rc.min_headroom_margin)
            temp_peak = float(getattr(batt, "t0_C", float("nan")))
            temp_end = float(getattr(batt, "t0_C", float("nan")))
        else:
            raise ValueError(f"unknown battery_model: {battery_model!r}")

        runs.append(
            {
                "seed": int(seed),
                "tte_h": None if tte_h is None else float(tte_h),
                "status": str(status),
                "min_headroom_margin": float(margin),
            }
        )

        if tte_h is not None and np.isfinite(float(tte_h)):
            tte_h_list.append(float(tte_h))
        if np.isfinite(float(margin)):
            margin_list.append(float(margin))
        if np.isfinite(float(temp_peak)):
            temp_peak_list.append(float(temp_peak))
        if np.isfinite(float(temp_end)):
            temp_end_list.append(float(temp_end))
        statuses.append(status)

    n = len(statuses)
    if n <= 0:
        raise ValueError("seeds 不能为空")

    mean_h = float(np.mean(np.array(tte_h_list, dtype=float))) if tte_h_list else float("nan")
    std_h = float(np.std(np.array(tte_h_list, dtype=float))) if tte_h_list else float("nan")
    cv = float("nan") if not np.isfinite(mean_h) or abs(mean_h) <= 1e-12 else float(std_h / mean_h)

    margin_mean = float(np.mean(np.array(margin_list, dtype=float))) if margin_list else float("nan")
    margin_std = float(np.std(np.array(margin_list, dtype=float))) if margin_list else float("nan")

    temp_peak_mean = float(np.mean(np.array(temp_peak_list, dtype=float))) if temp_peak_list else float("nan")
    temp_peak_std = float(np.std(np.array(temp_peak_list, dtype=float))) if temp_peak_list else float("nan")
    temp_end_mean = float(np.mean(np.array(temp_end_list, dtype=float))) if temp_end_list else float("nan")

    counts: dict[str, int] = {}
    for st in statuses:
        counts[st] = int(counts.get(st, 0) + 1)

    return {
        "n": int(n),
        "n_valid_tte": int(len(tte_h_list)),
        "tte_mean_h": float(mean_h),
        "tte_std_h": float(std_h),
        "tte_cv": float(cv),
        "tte_p05_h": float(quantile(tte_h_list, 0.05)) if tte_h_list else float("nan"),
        "tte_p50_h": float(quantile(tte_h_list, 0.50)) if tte_h_list else float("nan"),
        "tte_p95_h": float(quantile(tte_h_list, 0.95)) if tte_h_list else float("nan"),
        "min_headroom_margin_mean": float(margin_mean),
        "min_headroom_margin_std": float(margin_std),
        "min_headroom_margin_p05": float(quantile(margin_list, 0.05)) if margin_list else float("nan"),
        "min_headroom_margin_p50": float(quantile(margin_list, 0.50)) if margin_list else float("nan"),
        "min_headroom_margin_p95": float(quantile(margin_list, 0.95)) if margin_list else float("nan"),
        "temp_peak_C_mean": float(temp_peak_mean),
        "temp_peak_C_std": float(temp_peak_std),
        "temp_peak_C_p95": float(quantile(temp_peak_list, 0.95)) if temp_peak_list else float("nan"),
        "temp_end_C_mean": float(temp_end_mean),
        "p_cutoff": float(counts.get("cutoff", 0)) / n,
        "p_soc_min": float(counts.get("soc_min", 0)) / n,
        "p_insufficient_power": float(counts.get("insufficient_power", 0)) / n,
        "runs": list(runs),
        "statuses": list(statuses),
        "tte_h_list": list(tte_h_list),
    }


def compute_global_sensitivity(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    n_samples: int,
    seeds_per_sample: int,
    seed: int,
    battery_model: BatteryModelName = "model3",
    prior_mode: Literal["default", "tight"] = "default",
) -> dict[str, object]:
    """全局敏感性：采样 + PRCC/Spearman（输出含 tte_mean_h / p_cutoff / min_headroom_margin 等）。"""

    rng = random.Random(int(seed))
    rng_aging = random.Random(int(seed) + 99991)  # 与功耗/电池参数采样解耦，便于复现实验

    def _logu(lo: float, hi: float) -> float:
        lo = float(lo)
        hi = float(hi)
        if lo <= 0.0 or hi <= 0.0 or hi < lo:
            raise ValueError("log-uniform 需要 0 < lo <= hi")
        u = rng_aging.random()
        return lo * ((hi / lo) ** u)

    # X：参数列
    x_cols: dict[str, list[float]] = {k: [] for k in q3_param_names()}
    # y：输出列（每个样本对 seeds 平均）
    y_tte: list[float] = []
    y_tte_std: list[float] = []
    y_tte_cv: list[float] = []
    y_tte_spread: list[float] = []
    y_pcut: list[float] = []
    y_pinsuf: list[float] = []
    y_min_margin: list[float] = []

    # 便于追溯：保存每个样本的输出
    param_rows: list[dict[str, float]] = []
    per_sample_rows: list[dict[str, float]] = []

    mode = str(prior_mode)
    if mode not in ("default", "tight"):
        raise ValueError(f"unknown prior_mode: {prior_mode!r}")

    for i in range(int(n_samples)):
        s = sample_q3_uq(rng, prior_mode=prior_mode)
        p_i, b_i = apply_q2_uq_sample(base_power, base_batt, s)

        # 老化/健康状态：作为“慢变量假设”并入全局敏感性（no7 建议）
        if mode == "tight":
            # “已标定/同机型”的更窄老化先验：用于 sanity check
            soh = float(rng_aging.uniform(0.90, 1.0))
            alpha_r = float(_logu(0.5, 1.5))
        else:
            soh = float(rng_aging.uniform(0.7, 1.0))
            alpha_r = float(_logu(0.1, 3.0))
        cap_loss0 = float(max(0.0, 1.0 - soh))
        r0_growth0 = float(max(0.0, alpha_r) * (1.0 - soh))

        # 固定每个样本内的 seeds（CRN 思想）：减少比较噪声
        seeds = [int(seed) * 1_000_000 + i * 10_000 + j for j in range(int(seeds_per_sample))]
        stats = simulate_tte_replicates(
            scenario,
            power=p_i,
            batt=b_i,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model=battery_model,
            cap_loss0_frac=cap_loss0,
            r0_growth0_frac=r0_growth0,
            r1_growth0_frac=0.0,
        )

        row = sample_to_row(s, soh=soh, alpha_r=alpha_r)
        param_rows.append({"sample_idx": float(i), **{k: float(row[k]) for k in q3_param_names()}})
        for k in q3_param_names():
            x_cols[k].append(float(row[k]))

        tte_mean_h = float(stats["tte_mean_h"])
        tte_std_h = float(stats["tte_std_h"])
        tte_cv = float(stats["tte_cv"])
        tte_spread = float(stats["tte_p95_h"]) - float(stats["tte_p05_h"])
        p_cutoff = float(stats["p_cutoff"])
        p_insuf = float(stats["p_insufficient_power"])
        min_margin = float(stats["min_headroom_margin_mean"])
        y_tte.append(tte_mean_h)
        y_tte_std.append(tte_std_h)
        y_tte_cv.append(tte_cv)
        y_tte_spread.append(tte_spread)
        y_pcut.append(p_cutoff)
        y_pinsuf.append(p_insuf)
        y_min_margin.append(min_margin)

        per_sample_rows.append(
            {
                "sample_idx": float(i),
                "tte_mean_h": float(tte_mean_h),
                "tte_std_h": float(tte_std_h),
                "tte_cv": float(tte_cv),
                "tte_spread_h": float(tte_spread),
                "p_cutoff": float(p_cutoff),
                "p_insufficient_power": float(p_insuf),
                "min_headroom_margin": float(min_margin),
            }
        )

    # --- Spearman / PRCC（分别对 tte_mean_h 与 p_cutoff） ---
    spearman_tte = {k: float("nan") for k in q3_param_names()}
    spearman_tte_std = {k: float("nan") for k in q3_param_names()}
    spearman_tte_cv = {k: float("nan") for k in q3_param_names()}
    spearman_tte_spread = {k: float("nan") for k in q3_param_names()}
    spearman_pcut = {k: float("nan") for k in q3_param_names()}
    spearman_pinsuf = {k: float("nan") for k in q3_param_names()}
    spearman_min_margin = {k: float("nan") for k in q3_param_names()}

    for k in q3_param_names():
        try:
            spearman_tte[k] = float(spearman_corr(x_cols[k], y_tte))
        except Exception:
            spearman_tte[k] = float("nan")
        try:
            spearman_tte_std[k] = float(spearman_corr(x_cols[k], y_tte_std))
        except Exception:
            spearman_tte_std[k] = float("nan")
        try:
            spearman_tte_cv[k] = float(spearman_corr(x_cols[k], y_tte_cv))
        except Exception:
            spearman_tte_cv[k] = float("nan")
        try:
            spearman_tte_spread[k] = float(spearman_corr(x_cols[k], y_tte_spread))
        except Exception:
            spearman_tte_spread[k] = float("nan")
        try:
            spearman_pcut[k] = float(spearman_corr(x_cols[k], y_pcut))
        except Exception:
            spearman_pcut[k] = float("nan")
        try:
            spearman_pinsuf[k] = float(spearman_corr(x_cols[k], y_pinsuf))
        except Exception:
            spearman_pinsuf[k] = float("nan")
        try:
            spearman_min_margin[k] = float(spearman_corr(x_cols[k], y_min_margin))
        except Exception:
            spearman_min_margin[k] = float("nan")

    prcc_tte = prcc(x_cols, y_tte)
    prcc_tte_std = prcc(x_cols, y_tte_std)
    prcc_tte_cv = prcc(x_cols, y_tte_cv)
    prcc_tte_spread = prcc(x_cols, y_tte_spread)
    prcc_pcut = prcc(x_cols, y_pcut)
    prcc_pinsuf = prcc(x_cols, y_pinsuf)
    prcc_min_margin = prcc(x_cols, y_min_margin)

    return {
        "x_cols": x_cols,
        "y_tte": y_tte,
        "y_tte_std": y_tte_std,
        "y_tte_cv": y_tte_cv,
        "y_tte_spread_h": y_tte_spread,
        "y_p_cutoff": y_pcut,
        "y_p_insufficient_power": y_pinsuf,
        "y_min_headroom_margin": y_min_margin,
        "spearman_tte": spearman_tte,
        "spearman_tte_std": spearman_tte_std,
        "spearman_tte_cv": spearman_tte_cv,
        "spearman_tte_spread_h": spearman_tte_spread,
        "spearman_p_cutoff": spearman_pcut,
        "spearman_p_insufficient_power": spearman_pinsuf,
        "spearman_min_headroom_margin": spearman_min_margin,
        "prcc_tte": prcc_tte,
        "prcc_tte_std": prcc_tte_std,
        "prcc_tte_cv": prcc_tte_cv,
        "prcc_tte_spread_h": prcc_tte_spread,
        "prcc_p_cutoff": prcc_pcut,
        "prcc_p_insufficient_power": prcc_pinsuf,
        "prcc_min_headroom_margin": prcc_min_margin,
        "param_rows": param_rows,
        "per_sample_rows": per_sample_rows,
    }


def compute_local_sensitivity(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: list[int],
    eps: float = 0.05,
    v_cut_delta_V: float = 0.05,
    battery_model: BatteryModelName = "model3",
) -> list[dict[str, object]]:
    """局部敏感性：对每个参数做 ± 扰动并计算归一化敏感度（dimensionless）。"""

    if eps <= 0:
        raise ValueError("eps must be positive")

    # 以“基准样本”定义局部扰动中心：所有尺度因子=1，仅 v_cut/soc_min 使用 base_batt。
    base_sample = Q2UQSample(
        batt_capacity_scale=1.0,
        batt_r0_scale=1.0,
        batt_r1_scale=1.0,
        v_cut_V=float(base_batt.v_cut_V),
        soc_min=float(base_batt.soc_min),
        eta_pmic=1.0,
        base_scale=1.0,
        screen_scale=1.0,
        cpu_scale=1.0,
        gpu_scale=1.0,
        gps_scale=1.0,
        background_base_scale=1.0,
        rrc_state_scale=1.0,
        rrc_data_scale=1.0,
        rrc_tail_scale=1.0,
        poor_signal_psi_scale=1.0,
        bg_lambda_scale=1.0,
        interaction_scale=1.0,
    )

    p0, b0 = apply_q2_uq_sample(base_power, base_batt, base_sample)
    base_stats = simulate_tte_replicates(
        scenario,
        power=p0,
        batt=b0,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model=battery_model,
    )
    y0 = float(base_stats["tte_mean_h"])

    rows: list[dict[str, object]] = []

    def _sens_dimless(theta0: float, y_plus: float, y_minus: float, *, delta: float) -> float:
        if not np.isfinite(y0) or abs(y0) <= 1e-12:
            return float("nan")
        if abs(delta) <= 1e-12:
            return float("nan")
        return float(theta0 / y0 * (y_plus - y_minus) / (2.0 * delta))

    # --- 1) 乘性参数：用 ±eps 比例扰动 ---
    mult_params = [
        "batt_capacity_scale",
        "batt_r0_scale",
        "batt_r1_scale",
        "eta_pmic",
        "base_scale",
        "screen_scale",
        "cpu_scale",
        "gpu_scale",
        "gps_scale",
        "background_base_scale",
        "rrc_state_scale",
        "rrc_data_scale",
        "rrc_tail_scale",
        "poor_signal_psi_scale",
        "bg_lambda_scale",
        "interaction_scale",
    ]
    for name in mult_params:
        s_minus = replace(base_sample, **{name: float(getattr(base_sample, name)) * (1.0 - float(eps))})
        s_plus = replace(base_sample, **{name: float(getattr(base_sample, name)) * (1.0 + float(eps))})

        p_m, b_m = apply_q2_uq_sample(base_power, base_batt, s_minus)
        p_p, b_p = apply_q2_uq_sample(base_power, base_batt, s_plus)

        st_m = simulate_tte_replicates(
            scenario,
            power=p_m,
            batt=b_m,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model=battery_model,
        )
        st_p = simulate_tte_replicates(
            scenario,
            power=p_p,
            batt=b_p,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model=battery_model,
        )
        y_m = float(st_m["tte_mean_h"])
        y_p = float(st_p["tte_mean_h"])
        theta0 = float(getattr(base_sample, name))
        delta = float(theta0 * eps)
        rows.append(
            {
                "param": str(name),
                "param_zh": q3_param_label_zh(name),
                "theta0": float(theta0),
                "theta_minus": float(getattr(s_minus, name)),
                "theta_plus": float(getattr(s_plus, name)),
                "y0_tte_mean_h": float(y0),
                "y_minus_tte_mean_h": float(y_m),
                "y_plus_tte_mean_h": float(y_p),
                "sens_dimless": _sens_dimless(theta0, y_p, y_m, delta=delta),
                "eps": float(eps),
                "type": "multiplicative",
            }
        )

    # --- 2) v_cut：加性扰动（±v_cut_delta_V） ---
    vc0 = float(base_sample.v_cut_V)
    s_minus = replace(base_sample, v_cut_V=float(vc0 - v_cut_delta_V))
    s_plus = replace(base_sample, v_cut_V=float(vc0 + v_cut_delta_V))
    p_m, b_m = apply_q2_uq_sample(base_power, base_batt, s_minus)
    p_p, b_p = apply_q2_uq_sample(base_power, base_batt, s_plus)
    st_m = simulate_tte_replicates(
        scenario,
        power=p_m,
        batt=b_m,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model=battery_model,
    )
    st_p = simulate_tte_replicates(
        scenario,
        power=p_p,
        batt=b_p,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model=battery_model,
    )
    y_m = float(st_m["tte_mean_h"])
    y_p = float(st_p["tte_mean_h"])
    rows.append(
        {
            "param": "v_cut_V",
            "param_zh": q3_param_label_zh("v_cut_V"),
            "theta0": float(vc0),
            "theta_minus": float(vc0 - v_cut_delta_V),
            "theta_plus": float(vc0 + v_cut_delta_V),
            "y0_tte_mean_h": float(y0),
            "y_minus_tte_mean_h": float(y_m),
            "y_plus_tte_mean_h": float(y_p),
            "sens_dimless": _sens_dimless(vc0, y_p, y_m, delta=float(v_cut_delta_V)),
            "eps": float(v_cut_delta_V),
            "type": "additive",
        }
    )

    # SOC_min 是离散阈值，更适合“扫描”而不是局部导数；此处不放入 rows，避免误导。
    return rows


def compute_aging_scan(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: list[int],
    soh_list: list[float],
    alpha_r: float = 1.0,
) -> list[dict[str, object]]:
    """老化敏感性：扫描 SOH（容量衰减 + 内阻增长），输出 TTE/终止概率。"""

    rows: list[dict[str, object]] = []
    for soh in soh_list:
        soh = float(soh)
        soh = min(1.0, max(0.0, soh))
        cap_loss0 = float(1.0 - soh)
        r0_growth0 = float(max(0.0, alpha_r) * (1.0 - soh))

        stats = simulate_tte_replicates(
            scenario,
            power=base_power,
            batt=base_batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model="model3",
            cap_loss0_frac=cap_loss0,
            r0_growth0_frac=r0_growth0,
            r1_growth0_frac=0.0,
        )
        rows.append(
            {
                "soh": float(soh),
                "cap_loss0_frac": float(cap_loss0),
                "r0_growth0_frac": float(r0_growth0),
                "alpha_r": float(alpha_r),
                "tte_mean_h": float(stats["tte_mean_h"]),
                "tte_p05_h": float(stats["tte_p05_h"]),
                "tte_p50_h": float(stats["tte_p50_h"]),
                "tte_p95_h": float(stats["tte_p95_h"]),
                "min_headroom_margin_mean": float(stats["min_headroom_margin_mean"]),
                "p_cutoff": float(stats["p_cutoff"]),
                "p_insufficient_power": float(stats["p_insufficient_power"]),
            }
        )
    return rows


def compute_mechanism_ablation(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: list[int],
) -> list[dict[str, object]]:
    """结构消融：逐项移除功耗侧机制（RRC 尾态/弱信号/后台唤醒/交互项…）并比较 ΔTTE。"""

    baseline = simulate_tte_replicates(
        scenario,
        power=base_power,
        batt=base_batt,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model="model3",
    )
    y0 = float(baseline["tte_mean_h"])
    m0 = float(baseline["min_headroom_margin_mean"])

    rows: list[dict[str, object]] = []
    for mech_id, mech_label in mechanism_driver_specs():
        p2 = power_mechanism_variant(base_power, mech_id=str(mech_id))
        st = simulate_tte_replicates(
            scenario,
            power=p2,
            batt=base_batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model="model3",
        )
        y2 = float(st["tte_mean_h"])
        m2 = float(st["min_headroom_margin_mean"])
        delta = float(y2 - y0)
        delta_pct = float("nan") if not np.isfinite(y0) or abs(y0) <= 1e-12 else float(delta / y0 * 100.0)
        rows.append(
            {
                "ablation_type": "mechanism",
                "ablation_id": str(mech_id),
                "ablation_label_zh": str(mech_label),
                "variant": str(getattr(scenario, "variant", "") or ""),
                "tte_base_h": float(y0),
                "tte_variant_h": float(y2),
                "delta_tte_h": float(delta),
                "delta_tte_pct": float(delta_pct),
                "min_headroom_margin_base": float(m0),
                "min_headroom_margin_variant": float(m2),
                "p_cutoff_base": float(baseline["p_cutoff"]),
                "p_cutoff_variant": float(st["p_cutoff"]),
                "p_insuf_base": float(baseline["p_insufficient_power"]),
                "p_insuf_variant": float(st["p_insufficient_power"]),
            }
        )
    return rows


def compute_battery_model_ablation(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: list[int],
) -> list[dict[str, object]]:
    """建模假设对照：Model-1/2/3 的差异（同一功耗输入下电池端复杂度的影响）。"""

    # 为避免把“功耗侧热节流（DVFS）”与“电池热模型”混在一起，
    # 这里固定关闭 DVFS：只比较电池端（温度/老化）对 TTE 的影响。
    p_fixed = power_mechanism_variant(base_power, mech_id="no_thermal_throttle")

    rows: list[dict[str, object]] = []
    base_stats = simulate_tte_replicates(
        scenario,
        power=p_fixed,
        batt=base_batt,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model="model3",
    )
    y_ref = float(base_stats["tte_mean_h"])
    m_ref = float(base_stats["min_headroom_margin_mean"])
    tpk_ref = float(base_stats.get("temp_peak_C_mean", float("nan")))
    tend_ref = float(base_stats.get("temp_end_C_mean", float("nan")))

    for model_name in ["model1", "model2", "model3"]:
        st = simulate_tte_replicates(
            scenario,
            power=p_fixed,
            batt=base_batt,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model=model_name,  # type: ignore[arg-type]
        )
        y = float(st["tte_mean_h"])
        m = float(st["min_headroom_margin_mean"])
        tpk = float(st.get("temp_peak_C_mean", float("nan")))
        tend = float(st.get("temp_end_C_mean", float("nan")))
        delta = float(y - y_ref)
        delta_pct = float("nan") if not np.isfinite(y_ref) or abs(y_ref) <= 1e-12 else float(delta / y_ref * 100.0)
        label = {"model1": "Model-1（无热/无老化）", "model2": "Model-2（热耦合）", "model3": "Model-3（热+老化）"}[
            model_name
        ]
        rows.append(
            {
                "ablation_type": "battery_model",
                "ablation_id": str(model_name),
                "ablation_label_zh": str(label),
                "variant": str(getattr(scenario, "variant", "") or ""),
                "tte_ref_model3_h": float(y_ref),
                "tte_h": float(y),
                "delta_vs_model3_h": float(delta),
                "delta_vs_model3_pct": float(delta_pct),
                "min_headroom_margin_ref": float(m_ref),
                "min_headroom_margin": float(m),
                "temp_peak_ref_C": float(tpk_ref),
                "temp_peak_C": float(tpk),
                "temp_end_ref_C": float(tend_ref),
                "temp_end_C": float(tend),
                "p_cutoff": float(st["p_cutoff"]),
                "p_insufficient_power": float(st["p_insufficient_power"]),
            }
        )
    return rows


def compute_battery_structure_ablation(
    scenario: Scenario,
    *,
    base_power: PowerParams1Stateful,
    base_batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    dt_s: float,
    soc0: float,
    seeds: list[int],
) -> list[dict[str, object]]:
    """电池端结构假设对照：1RC vs 2RC（快+慢极化支路）。

目的（赛题 Q3）：
- 检查“只用单一极化时间常数（1RC）”这一简化是否会显著改变 TTE/欠压风险预测；
- 若差异显著，可在论文中把 2RC 作为更真实的结构选择，或将其作为结构不确定性来源。
"""

    # 固定关闭功耗侧 DVFS：只比较电池端结构差异。
    p_fixed = power_mechanism_variant(base_power, mech_id="no_thermal_throttle")

    st_1rc = simulate_tte_replicates(
        scenario,
        power=p_fixed,
        batt=base_batt,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model="model1",
    )
    st_2rc = simulate_tte_replicates(
        scenario,
        power=p_fixed,
        batt=base_batt,
        power0_dummy=power0_dummy,
        dt_s=dt_s,
        soc0=soc0,
        seeds=seeds,
        battery_model="model1_2rc",
    )

    y0 = float(st_1rc["tte_mean_h"])
    y2 = float(st_2rc["tte_mean_h"])
    m0 = float(st_1rc["min_headroom_margin_mean"])
    m2 = float(st_2rc["min_headroom_margin_mean"])
    delta = float(y2 - y0)
    delta_pct = float("nan") if not np.isfinite(y0) or abs(y0) <= 1e-12 else float(delta / y0 * 100.0)

    return [
        {
            "ablation_type": "battery_structure",
            "ablation_id": "1rc_to_2rc",
            "ablation_label_zh": "Model-1：1RC -> 2RC 极化（快+慢）",
            "variant": str(getattr(scenario, "variant", "") or ""),
            "tte_base_h": float(y0),
            "tte_variant_h": float(y2),
            "delta_tte_h": float(delta),
            "delta_tte_pct": float(delta_pct),
            "min_headroom_margin_base": float(m0),
            "min_headroom_margin_variant": float(m2),
            "p_cutoff_base": float(st_1rc["p_cutoff"]),
            "p_cutoff_variant": float(st_2rc["p_cutoff"]),
            "p_insuf_base": float(st_1rc["p_insufficient_power"]),
            "p_insuf_variant": float(st_2rc["p_insufficient_power"]),
        }
    ]
