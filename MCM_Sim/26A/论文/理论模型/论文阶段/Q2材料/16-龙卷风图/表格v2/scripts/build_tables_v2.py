#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Q2「表格v2」：

1) 表 7-1：不确定参数集合（与代码中的 Q2UQSample 抽样口径一致）
2) 表 9-1：TTE 汇总（含区间与风险概率），由既有仿真报表自动汇总

输入数据（来自项目现有产物，不重新跑仿真）：
- Q2 仿真报表：MCM_Sim/26A/src/out_reports/q2/
  - tte_samples.csv
  - termination_stats.csv
  - param_sensitivity.csv
- 场景定义：MCM_Sim/26A/src/configs/scenarios_v0.json
- 参量估计汇总（用于“来源/锚定”描述，不强行改写 UQ 抽样口径）：
  - MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/参数估计汇总表.csv

输出目录：
- MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/15-补数据/表格v2/
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _find_project_dir(start: Path) -> Path:
    """向上寻找包含 src/mcm26a 的 26A 项目根目录。"""

    start = Path(start).resolve()
    for p in [start] + list(start.parents):
        if (p / "src" / "mcm26a").exists():
            return p
    raise FileNotFoundError("未找到包含 src/mcm26a 的项目根目录（26A）")


def _md_table(df: pd.DataFrame) -> str:
    """最小依赖的 Markdown 表格渲染器。"""

    cols = df.columns.tolist()

    def esc(x: object) -> str:
        s = "" if x is None else str(x)
        s = s.replace("|", "\\|").replace("\n", "<br>")
        return s

    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(esc(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _load_scenario_titles(path: Path) -> dict[str, str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    sc = obj.get("scenarios", {}) or {}
    out: dict[str, str] = {}
    for sid, v in sc.items():
        out[str(sid)] = str(v.get("title_zh", sid))
    return out


def _build_table_7_1(
    *,
    out_dir: Path,
    param_labels: dict[str, str],
    power_cfg_path: Path,
    phone_cfg_path: Path,
    param_est_csv: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """表 7-1：不确定参数集合（v2）。"""

    power = json.loads(power_cfg_path.read_text(encoding="utf-8"))
    phone = json.loads(phone_cfg_path.read_text(encoding="utf-8"))

    # 读取参量估计（用于“来源/锚定”文字，避免写成拍脑袋）
    est_df = pd.read_csv(param_est_csv)
    est_map = {str(r["parameter_key"]): float(r["value"]) for _, r in est_df.iterrows()}

    # 与代码 sample_q2_uq() 一致的先验（见：src/mcm26a/uq/q2_uq.py）
    priors = {
        "batt_capacity_scale": {"dist": "logU", "lo": 0.90, "hi": 1.10, "unit": "-", "nominal": 1.00},
        "batt_r0_scale": {"dist": "logU", "lo": 0.80, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "batt_r1_scale": {"dist": "logU", "lo": 0.80, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "v_cut_V": {"dist": "U", "lo": 3.20, "hi": 3.40, "unit": "V", "nominal": float(phone["battery"]["ecm"]["V_cut_V"])},
        "soc_min": {"dist": "choice", "choices": [0.00, 0.03, 0.05, 0.10], "unit": "-", "nominal": float(phone["battery"]["soc_min"])},
        "eta_pmic": {"dist": "U", "lo": 0.90, "hi": 0.95, "unit": "-", "nominal": 0.925},
        "base_scale": {"dist": "logU", "lo": 0.70, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "screen_scale": {"dist": "logU", "lo": 0.70, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "cpu_scale": {"dist": "logU", "lo": 0.60, "hi": 1.40, "unit": "-", "nominal": 1.00},
        "gpu_scale": {"dist": "logU", "lo": 0.60, "hi": 1.40, "unit": "-", "nominal": 1.00},
        "gps_scale": {"dist": "logU", "lo": 0.70, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "background_base_scale": {"dist": "logU", "lo": 0.70, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "rrc_state_scale": {"dist": "logU", "lo": 0.60, "hi": 1.60, "unit": "-", "nominal": 1.00},
        "rrc_data_scale": {"dist": "logU", "lo": 0.60, "hi": 1.60, "unit": "-", "nominal": 1.00},
        "rrc_tail_scale": {"dist": "logU", "lo": 0.70, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "poor_signal_psi_scale": {"dist": "logU", "lo": 0.90, "hi": 1.30, "unit": "-", "nominal": 1.00},
        "bg_lambda_scale": {"dist": "logU", "lo": 0.50, "hi": 2.00, "unit": "-", "nominal": 1.00},
        "interaction_scale": {"dist": "U", "lo": 0.00, "hi": 1.60, "unit": "-", "nominal": 0.80},
    }

    # 写一份“可直接用于论文”的表（更短、更像评委会看的版本）
    # 列：参数/含义/单位/标称值/先验范围/数据依据
    desc = {
        "batt_capacity_scale": "容量缩放（等效 SOH/标称容量差异）",
        "batt_r0_scale": "欧姆内阻 R0 缩放（欠压提前关机关键驱动）",
        "batt_r1_scale": "极化支路 R1 缩放（尖峰后回升/恢复形状）",
        "v_cut_V": "欠压截止阈值 V_cut",
        "soc_min": "最小 SOC（保护余量/0% 标定差异）",
        "eta_pmic": "等效 PMIC 效率 η_PMIC（P_batt≈P_load/η）",
        "base_scale": "基础功耗缩放（系统常开/轻载）",
        "screen_scale": "屏幕功耗缩放（亮度模型整体尺度）",
        "cpu_scale": "CPU 功耗缩放（同类任务效率差异）",
        "gpu_scale": "GPU 功耗缩放（图形负载效率差异）",
        "gps_scale": "GPS 功耗缩放（定位模块差异）",
        "background_base_scale": "后台基线功耗缩放（常驻服务/维护）",
        "rrc_state_scale": "网络状态功耗缩放（IDLE/CONN/TAIL）",
        "rrc_data_scale": "单位数据能耗缩放（J/MB）",
        "rrc_tail_scale": "尾态时间尺度缩放（τ 或 τ_low/τ_high）",
        "poor_signal_psi_scale": "弱信号惩罚缩放（ψ_poor）",
        "bg_lambda_scale": "后台唤醒频率缩放（Poisson λ）",
        "interaction_scale": "交互项缩放（协同耗电项）",
    }

    # 用参量估计结果写几条“锚定句”，用于表内的来源列
    anchors = {
        "screen": "参量估计(AndroWatts)：P0≈{:.3f}W, k≈{:.2e}W/nit".format(
            est_map.get("power.screen.P0_W", float("nan")),
            est_map.get("power.screen.k_W_per_nit", float("nan")),
        ),
        "cpu_gpu": "参量估计(AndroWatts)：k_cpu≈{:.2f}W, k_gpu≈{:.3f}W".format(
            est_map.get("power.cpu.k_W", float("nan")),
            est_map.get("power.gpu.k_W", float("nan")),
        ),
        "wifi": "参量估计(AndroWatts)：e_wifi≈{:.3f}J/MB, τ_tail≈{:.1f}s".format(
            est_map.get("power.rrc.e_per_mb_J (wifi)", float("nan")),
            est_map.get("power.rrc.tau_tail_s (wifi)", float("nan")),
        ),
        "thermal": "参量估计(AndroWatts)：R_th≈{:.3f}K/W, C_th≈{:.1f}J/K（用于对照实验）".format(
            est_map.get("battery.thermal.R_th_K_per_W", float("nan")),
            est_map.get("battery.thermal.C_th_J_per_K", float("nan")),
        ),
    }

    def prior_str(p: dict) -> str:
        if p["dist"] == "choice":
            return "{" + ", ".join("{:.2f}".format(x) for x in p["choices"]) + "}"
        return "{}[{:.3g}, {:.3g}]".format(p["dist"], float(p["lo"]), float(p["hi"]))

    def source_str(param: str) -> str:
        if param in ("screen_scale",):
            return "基准配置 + " + anchors["screen"]
        if param in ("cpu_scale", "gpu_scale"):
            return "基准配置 + " + anchors["cpu_gpu"]
        if param in ("rrc_data_scale", "rrc_tail_scale", "rrc_state_scale", "poor_signal_psi_scale"):
            return "基准配置 + " + anchors["wifi"]
        if param in ("v_cut_V", "soc_min"):
            return "基准配置（阈值/保护余量，工程先验）"
        if param in ("batt_capacity_scale", "batt_r0_scale", "batt_r1_scale"):
            return "基准配置（电池差异/老化的尺度不确定性；可用 SOH 表进一步收窄）"
        if param in ("bg_lambda_scale", "interaction_scale", "background_base_scale"):
            return "基准配置（后台/交互机理项，工程先验；可用真实日志校准）"
        return "基准配置（工程先验）"

    paper_rows = []
    for param, p in priors.items():
        paper_rows.append(
            {
                "参数θ（代码字段）": param,
                "含义（单行）": desc.get(param, param),
                "单位": p["unit"],
                "标称值": p["nominal"],
                "先验/抽样": prior_str(p),
                "数据依据/来源": source_str(param),
            }
        )
    df_paper = pd.DataFrame(paper_rows)

    # 再写一份“数据版”（更适合复现/核对），额外包含“中文名”等字段
    data_rows = []
    for param, p in priors.items():
        r = dict(paper_rows[[x["参数θ（代码字段）"] for x in paper_rows].index(param)])
        r["param_zh"] = param_labels.get(param, "")
        data_rows.append(r)
    df_data = pd.DataFrame(data_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    df_paper.to_csv(out_dir / "表7-1_UQ参数先验_v2.csv", index=False, encoding="utf-8")
    (out_dir / "表7-1_UQ参数先验_v2.md").write_text(_md_table(df_paper), encoding="utf-8")

    # 额外保留一份“数据版”
    df_data.to_csv(out_dir / "表7-1_UQ参数先验_v2_data.csv", index=False, encoding="utf-8")
    return df_paper, df_data


def _build_table_7_1_legacy9(
    *,
    out_dir: Path,
    power_cfg_path: Path,
    phone_cfg_path: Path,
    param_est_csv: Path,
    battery_state_table_csv: Path,
    max_nits: float = 500.0,
) -> pd.DataFrame:
    """旧版“9 参数简表”的补全版（v2）。

说明：
- 该表更贴近早期论文的符号体系（SOH、η0、α_R、hA、k_b、k-big、k_gpu、τ_m、b_{q,m}）；
- 数值来自：参量估计（screen/网络/热）+ 基准配置（CPU/GPU/网络结构）+ 电池状态表（SOH 分布）；
- 用于写论文时“读者更容易看懂”的版本；严格复现请以表 7-1（Q2UQSample 口径）为准。
"""

    power = json.loads(power_cfg_path.read_text(encoding="utf-8"))
    phone = json.loads(phone_cfg_path.read_text(encoding="utf-8"))

    est_df = pd.read_csv(param_est_csv)
    est_map = {str(r["parameter_key"]): float(r["value"]) for _, r in est_df.iterrows()}

    bs = pd.read_csv(battery_state_table_csv)
    soh = pd.to_numeric(bs["SOH"], errors="coerce").dropna().to_numpy(dtype=float)
    soh = soh[np.isfinite(soh)]
    soh_p05 = float(np.quantile(soh, 0.05)) if soh.size else float("nan")
    soh_p50 = float(np.quantile(soh, 0.50)) if soh.size else float("nan")
    soh_p95 = float(np.quantile(soh, 0.95)) if soh.size else float("nan")

    # 屏幕：把 k_screen(W/nit) 转为对 b∈[0,1] 的系数（W/brightness_frac）
    k_screen = float(est_map.get("power.screen.k_W_per_nit", float("nan")))
    k_b = float(k_screen * float(max_nits)) if np.isfinite(k_screen) else float("nan")

    # 热：用参量估计的 R_th 反推 hA≈1/R_th（近似）
    r_th = float(est_map.get("battery.thermal.R_th_K_per_W", float("nan")))
    hA = float(1.0 / r_th) if (np.isfinite(r_th) and r_th > 1e-12) else float("nan")

    # CPU/GPU：取基准配置的系数
    cpu_big = float(power["cpu"]["k_big_W"])
    gpu_k = float(power["gpu"]["k_W"])

    # 网络：b_{q,m} 从 e_per_mb_J 换算（q 用 KB/s）
    e_wifi = float(power["rrc"]["e_per_mb_J"]["wifi"])
    e_lte = float(power["rrc"]["e_per_mb_J"]["lte"])
    e_5g = float(power["rrc"]["e_per_mb_J"]["5g"])
    b_wifi = e_wifi / 1000.0
    b_lte = e_lte / 1000.0
    b_5g = e_5g / 1000.0

    # τ_m：基准配置的 tau_tail_s（注意：no7 实际还启用了 tail_gate；这里给“简表口径”）
    tau_wifi = float(power["rrc"]["tau_tail_s"]["wifi"])
    tau_lte = float(power["rrc"]["tau_tail_s"]["lte"])
    tau_5g = float(power["rrc"]["tau_tail_s"]["5g"])

    # v_cut / soc_min
    v_cut0 = float(phone["battery"]["ecm"]["V_cut_V"])
    soc_min0 = float(phone["battery"]["soc_min"])

    rows = [
        {
            "参数θ（旧符号）": "SOH",
            "含义（单行）": "健康状态（容量保持率/老化因子）",
            "单位": "-",
            "标称值": soh_p50,
            "先验范围": "[{:.3f}, {:.3f}]".format(max(0.0, soh_p05), 1.0),
            "数据依据/来源": "电池状态表：MCM2026_battery_state_table.csv（P05/P50/P95≈{:.3f}/{:.3f}/{:.3f}）".format(soh_p05, soh_p50, soh_p95),
        },
        {
            "参数θ（旧符号）": "η0",
            "含义（单行）": "PMIC 等效效率常量（P_batt = P_load / η0）",
            "单位": "-",
            "标称值": 0.925,
            "先验范围": "[0.90, 0.95]",
            "数据依据/来源": "工程先验（与 Q2UQSample.eta_pmic 一致）",
        },
        {
            "参数θ（旧符号）": "α_R",
            "含义（单行）": "等效增阻尺度（吸收批次/温度/老化差异）",
            "单位": "-",
            "标称值": 1.0,
            "先验范围": "logU[0.80, 1.30]",
            "数据依据/来源": "与 Q2UQSample.batt_r0_scale/batt_r1_scale 同量级（尺度不确定性）",
        },
        {
            "参数θ（旧符号）": "hA",
            "含义（单行）": "等效散热系数（近似：hA≈1/R_th）",
            "单位": "W/°C",
            "标称值": hA,
            "先验范围": "logU[{:.3f}, {:.3f}]（±30%）".format(0.7 * hA, 1.3 * hA) if np.isfinite(hA) else "",
            "数据依据/来源": "参量估计(AndroWatts 温升)：R_th≈{:.3f}K/W → hA≈{:.3f}W/K（对照实验用）".format(r_th, hA),
        },
        {
            "参数θ（旧符号）": "k_b",
            "含义（单行）": "屏幕亮度系数（对 b∈[0,1]：P_screen≈P0+k_b·b）",
            "单位": "W",
            "标称值": k_b,
            "先验范围": "logU[{:.3f}, {:.3f}]（±30%）".format(0.7 * k_b, 1.3 * k_b) if np.isfinite(k_b) else "",
            "数据依据/来源": "参量估计：k_screen≈{:.2e}W/nit，按 max_nits={} 换算 k_b=k_screen*max_nits".format(k_screen, int(max_nits)),
        },
        {
            "参数θ（旧符号）": "k-big",
            "含义（单行）": "大核功耗系数（big cluster 尺度项）",
            "单位": "W",
            "标称值": cpu_big,
            "先验范围": "logU[{:.3f}, {:.3f}]（×0.6~1.4）".format(0.6 * cpu_big, 1.4 * cpu_big),
            "数据依据/来源": "基准功耗配置：power_params_v2_no7_awcal_mo_v2.json（CPU big.LITTLE）",
        },
        {
            "参数θ（旧符号）": "k_gpu",
            "含义（单行）": "GPU 功耗系数（尺度项）",
            "单位": "W",
            "标称值": gpu_k,
            "先验范围": "logU[{:.3f}, {:.3f}]（×0.6~1.4）".format(0.6 * gpu_k, 1.4 * gpu_k),
            "数据依据/来源": "基准功耗配置 + 参量估计(AndroWatts)量级对照",
        },
        {
            "参数θ（旧符号）": "τ_m",
            "含义（单行）": "网络尾态时间常数（简表口径；no7 实际用 tail_gate τ_low/τ_high）",
            "单位": "s",
            "标称值": "Wi-Fi:{:.1f}; LTE:{:.1f}; 5G:{:.1f}".format(tau_wifi, tau_lte, tau_5g),
            "先验范围": "Wi-Fi:[{:.1f},{:.1f}]; LTE:[{:.1f},{:.1f}]; 5G:[{:.1f},{:.1f}]".format(
                0.7 * tau_wifi,
                1.3 * tau_wifi,
                0.7 * tau_lte,
                1.3 * tau_lte,
                0.7 * tau_5g,
                1.3 * tau_5g,
            ),
            "数据依据/来源": "基准功耗配置（rrc.tau_tail_s）+ Q2UQSample.rrc_tail_scale",
        },
        {
            "参数θ（旧符号）": "b_{q,m}",
            "含义（单行）": "吞吐→功耗系数（q 用 KB/s）",
            "单位": "W/(KB/s)",
            "标称值": "Wi-Fi:{:.3e}; LTE:{:.3e}; 5G:{:.3e}".format(b_wifi, b_lte, b_5g),
            "先验范围": "Wi-Fi:[{:.3e},{:.3e}]; LTE:[{:.3e},{:.3e}]; 5G:[{:.3e},{:.3e}]".format(
                0.6 * b_wifi,
                1.6 * b_wifi,
                0.6 * b_lte,
                1.6 * b_lte,
                0.6 * b_5g,
                1.6 * b_5g,
            ),
            "数据依据/来源": "b=e/1000（由 e_per_mb_J 换算）+ Q2UQSample.rrc_data_scale；Wi-Fi e 的参量估计下界≈{:.3f}J/MB".format(
                float(est_map.get("power.rrc.e_per_mb_J (wifi)", float("nan")))
            ),
        },
    ]

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "表7-1_旧版符号9参数_补全_v2.csv", index=False, encoding="utf-8")
    (out_dir / "表7-1_旧版符号9参数_补全_v2.md").write_text(_md_table(df), encoding="utf-8")
    return df


def _build_table_9_1(
    *,
    out_dir: Path,
    tte_samples_path: Path,
    term_stats_path: Path,
    sens_path: Path,
    scenario_titles: dict[str, str],
) -> pd.DataFrame:
    """表 9-1：TTE 汇总（v2，基于既有 out_reports/q2）。"""

    samp = pd.read_csv(tte_samples_path)
    term = pd.read_csv(term_stats_path)
    sens = pd.read_csv(sens_path)

    # 只汇总“主场景（baseline）”：variant='-'
    samp = samp[samp["variant"] == "-"].copy()
    term = term[term["variant"] == "-"].copy()
    sens = sens[sens["variant"] == "-"].copy()

    soc0_list = sorted({float(x) for x in samp["soc0"].unique().tolist()})
    soc0_str = "{" + ",".join(["{:.0f}%".format(s * 100) for s in soc0_list]) + "}"

    rows = []
    for sid in sorted({str(x) for x in samp["scenario_id"].unique().tolist()}):
        title = scenario_titles.get(sid, sid)

        # --- TTE：点估（按模板：对每个 SOC0 取 median，再对 SOC0 等权平均）
        medians = []
        xs_all = []
        for soc0 in soc0_list:
            xs = samp[(samp["scenario_id"] == sid) & (samp["soc0"] == soc0)]["tte_h"].to_numpy(dtype=float)
            xs = xs[np.isfinite(xs)]
            if xs.size == 0:
                continue
            medians.append(float(np.quantile(xs, 0.50)))
            xs_all.append(xs)
        if not medians:
            continue
        tte_point = float(np.mean(np.array(medians, dtype=float)))

        all_x = np.concatenate(xs_all, axis=0)
        p025 = float(np.quantile(all_x, 0.025))
        p975 = float(np.quantile(all_x, 0.975))

        # --- 终止原因概率：按 SOC0 等权平均
        p_cutoff = []
        p_insuff = []
        for soc0 in soc0_list:
            r = term[(term["scenario_id"] == sid) & (term["soc0"] == soc0)]
            if r.empty:
                continue
            rr = r.iloc[0]
            p_cutoff.append(float(rr.get("p_cutoff", 0.0)))
            p_insuff.append(float(rr.get("p_insufficient_power", 0.0)))
        pr_cutoff = float(np.mean(np.array(p_cutoff, dtype=float))) if p_cutoff else float("nan")
        pr_insuff = float(np.mean(np.array(p_insuff, dtype=float))) if p_insuff else float("nan")

        # --- 主导不确定源：对每个 param 取 mean(|PRCC|) across SOC0，然后排序取 Top-2
        s0 = sens[sens["scenario_id"] == sid].copy()
        top2 = ""
        if not s0.empty:
            g = s0.groupby(["param", "param_zh"], dropna=False)["prcc"].apply(lambda x: float(np.mean(np.abs(np.array(x, dtype=float)))))
            g = g.reset_index().rename(columns={"prcc": "mean_abs_prcc"})
            g = g.sort_values("mean_abs_prcc", ascending=False)
            top = g.head(2)["param_zh"].tolist()
            top = [t for t in top if isinstance(t, str) and t.strip()]
            top2 = "、".join(top[:2])

        rows.append(
            {
                "场景": "{}（{}）".format(sid, title),
                "SOC0 集": soc0_str,
                "TTE 点估（h）": tte_point,
                "95% 区间（h）": "[{:.2f}, {:.2f}]".format(p025, p975),
                "Pr(V_term≤V_cut)": pr_cutoff,
                "Pr(Δ<0/不可行)": pr_insuff,
                "主导不确定源（Top-2）": top2,
            }
        )

    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "表9-1_TTE汇总_v2.csv", index=False, encoding="utf-8")

    # Markdown 版：把概率转成百分数更易读
    df_md = df.copy()
    for c in ["Pr(V_term≤V_cut)", "Pr(Δ<0/不可行)"]:
        df_md[c] = df_md[c].map(lambda x: "" if (x is None or not np.isfinite(float(x))) else "{:.1f}%".format(float(x) * 100.0))
    df_md["TTE 点估（h）"] = df_md["TTE 点估（h）"].map(lambda x: "{:.2f}".format(float(x)))
    (out_dir / "表9-1_TTE汇总_v2.md").write_text(_md_table(df_md), encoding="utf-8")
    return df


def main() -> int:
    project = _find_project_dir(Path(__file__).resolve())

    out_dir = project / "论文" / "理论模型" / "论文阶段" / "Q2材料" / "15-补数据" / "表格v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    src_dir = project / "src"
    q2_reports = src_dir / "out_reports" / "q2"

    # 输入
    tte_samples = q2_reports / "tte_samples.csv"
    term_stats = q2_reports / "termination_stats.csv"
    sens = q2_reports / "param_sensitivity.csv"
    scenarios_cfg = src_dir / "configs" / "scenarios_v0.json"
    power_cfg = src_dir / "configs" / "power_params_v2_no7_awcal_mo_v2.json"
    phone_cfg = src_dir / "configs" / "phone_default_v3_aging.json"
    param_est = project / "论文" / "理论模型" / "论文阶段" / "参量估计" / "参数估计汇总表.csv"
    batt_state = project / "data" / "MCM2026_battery_state_table" / "MCM2026_battery_state_table.csv"

    # 简单校验
    for p in [tte_samples, term_stats, sens, scenarios_cfg, power_cfg, phone_cfg, param_est, batt_state]:
        if not p.exists():
            raise FileNotFoundError(str(p))

    # 用 param_sensitivity.csv 提供 param->中文名映射（避免重复维护）
    sens_df = pd.read_csv(sens)
    labels = {}
    for _, r in sens_df.drop_duplicates(["param", "param_zh"]).iterrows():
        labels[str(r["param"])] = str(r.get("param_zh", "") or "")

    titles = _load_scenario_titles(scenarios_cfg)

    # 生成两张表
    _build_table_7_1(out_dir=out_dir, param_labels=labels, power_cfg_path=power_cfg, phone_cfg_path=phone_cfg, param_est_csv=param_est)
    _build_table_7_1_legacy9(
        out_dir=out_dir,
        power_cfg_path=power_cfg,
        phone_cfg_path=phone_cfg,
        param_est_csv=param_est,
        battery_state_table_csv=batt_state,
        max_nits=500.0,
    )
    _build_table_9_1(out_dir=out_dir, tte_samples_path=tte_samples, term_stats_path=term_stats, sens_path=sens, scenario_titles=titles)

    # 写来源说明
    (out_dir / "about.md").write_text(
        "# 表格v2 生成说明\n\n"
        "本目录由脚本自动生成，用于补全 Q2 写作中的两张关键表格：\n\n"
        "- 表 7-1：不确定参数集合（与代码 `Q2UQSample` 的抽样口径一致）\n"
        "- 表 9-1：TTE 汇总（点估 + 区间 + 风险概率 + Top-2 不确定源）\n\n"
        "## 输入来源\n\n"
        "- Q2 报表：`MCM_Sim/26A/src/out_reports/q2/`（已存在产物，不重新跑仿真）\n"
        "- 场景配置：`MCM_Sim/26A/src/configs/scenarios_v0.json`\n"
        "- 功耗/电池基准配置：\n"
        "  - `MCM_Sim/26A/src/configs/power_params_v2_no7_awcal_mo_v2.json`\n"
        "  - `MCM_Sim/26A/src/configs/phone_default_v3_aging.json`\n"
        "- 参量估计锚定（用于表内“数据依据/来源”的文字）：`MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/参数估计汇总表.csv`\n\n"
        "## 复现\n\n"
        "在仓库根目录运行：\n\n"
        "```bash\n"
        "python3 \"MCM_Sim/26A/论文/理论模型/论文阶段/Q2材料/15-补数据/表格v2/scripts/build_tables_v2.py\"\n"
        "```\n",
        encoding="utf-8",
    )

    print("[ok] 表格v2 已生成 ->", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
