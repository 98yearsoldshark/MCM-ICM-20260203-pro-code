#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q3：生成“16-生产需要的内容/敏感性分析”所需产物（局部敏感性 + Tornado + Top-3 解释）。

对应需求（来自 docx 模板）：
- 基于 9 个不确定参数，对 5 种典型场景（S1-S5）做局部敏感性分析；
- 对每个参数做 ±5% 扰动，计算 TTE 的变化率 ΔTTE(%)；
- 绘制 Tornado 图（ΔTTE(%)，默认输出 5 张：S1~S5；如只需要 S4 可自行取用）；
- 列表解释各场景下前三大敏感参数的物理影响逻辑。

说明（与现有工程对齐）：
- 续航预测仍来自连续时间机理模型（Model-3：热-电-老化），时间单位 s，报告用小时 h；
- 随机使用过程会引入噪声，因此每个设定用多随机种子重复仿真取均值；
- 这里的“9 个参数”选择为文档口径的可解释子集：
    η0（等效 PMIC 效率）、SOH、α_R（增阻强度）、hA（散热强度，hA=1/R_th）、
    k_b（屏幕尺度）、k_cpu（CPU尺度）、k_gpu（GPU尺度）、b_{q,m}（单位数据能耗）、τ_m（尾态时长）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

# Matplotlib 仅用于出图；保持风格干净（适合直接进论文/Word）。
import matplotlib.pyplot as plt

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q3_sensitivity import simulate_tte_replicates
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.uq.q2_uq import Q2UQSample, apply_q2_uq_sample
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


# 文档口径：S1-S5（这里映射到工程的 scenario_id）
DOC_SCENARIOS: list[tuple[str, str, str]] = [
    ("S1", "S0_standby", "待机/轻度"),
    ("S2", "S1b_browse", "浏览/社交"),
    ("S3", "S1_video", "视频/直播"),
    ("S4", "S3_gaming", "游戏"),
    ("S5", "S2_navigation", "导航/通话"),
]


def _delta_pct(y: float, y0: float) -> float:
    if not np.isfinite(float(y0)) or abs(float(y0)) <= 1e-12:
        return float("nan")
    return float((float(y) - float(y0)) / float(y0) * 100.0)


def _plot_tornado(*, rows: list[dict[str, object]], title: str, out_path: Path, top_k: int = 5) -> None:
    """Tornado：每个参数两根 bar（-5% 与 +5%），横轴为 ΔTTE(%)。

    按 docx 模板口径，默认只展示 Top-5（按 |ΔTTE| 排序），避免图面过满。
    """

    # 统一风格（含中文字体回退），避免中文在某些环境下显示为方块。
    style = apply_style("paper")

    # 按最大绝对影响排序（越大越靠上）
    rows_sorted = sorted(rows, key=lambda r: float(r.get("score_absmax_pct", float("nan"))), reverse=True)
    if int(top_k) > 0:
        rows_sorted = rows_sorted[: int(top_k)]

    # 颜色表（用户指定的 Skip Gradient 里挑 2 色）
    c_plus = PALETTE_SKIP_GRADIENT[0]  # purple
    c_minus = PALETTE_SKIP_GRADIENT[3]  # deep teal

    labels = [str(r["param_symbol"]) for r in rows_sorted][::-1]
    v_minus = [float(r["delta_minus_pct"]) for r in rows_sorted][::-1]
    v_plus = [float(r["delta_plus_pct"]) for r in rows_sorted][::-1]

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10.8, 4.4))
    ax.barh(y, v_minus, color=c_minus, alpha=0.88, label="-5%")
    ax.barh(y, v_plus, color=c_plus, alpha=0.88, label="+5%")
    ax.axvline(0.0, color="#333333", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("ΔTTE (%)")
    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.25)
    ax.legend(loc="lower right", frameon=False, ncols=2)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    savefig(fig, out_path, mode=style.mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q3：doc16 局部敏感性（9参数×S1-S5）")
    ap.add_argument(
        "--out-dir",
        default=str(
            SRC_DIR.parent
            / "论文"
            / "理论模型"
            / "论文阶段"
            / "Q3材料"
            / "16-生产需要的内容"
        ),
        help="输出目录（默认写到论文阶段/Q3材料/16-生产需要的内容）",
    )
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景 JSON 路径")
    ap.add_argument("--power", default=str(SRC_DIR / "configs" / "power_params_v1_stateful.json"), help="功耗参数 JSON")
    ap.add_argument("--phone", default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"), help="电池参数 JSON（Model-3）")
    ap.add_argument("--dt", type=float, default=10.0, help="积分步长 dt（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0")
    ap.add_argument("--replicates", type=int, default=40, help="每个设定的随机种子重复次数（越大越稳）")
    ap.add_argument("--seed", type=int, default=20260202, help="随机种子（可复现）")
    ap.add_argument("--eps", type=float, default=0.05, help="扰动比例（默认 ±5%）")

    # 文档中的 9 个参数里包含 SOH 与 α_R：为了让 α_R 有意义，基准 SOH 必须 < 1。
    ap.add_argument("--soh0", type=float, default=0.90, help="基准 SOH（0~1，默认 0.90）")
    ap.add_argument("--alpha-r0", type=float, default=1.50, help="基准 α_R（默认 1.50）")

    # η0（等效 PMIC 效率）是文档明确列出的参数：保持在 (0,1) 内更物理。
    ap.add_argument("--eta0", type=float, default=0.93, help="基准 η0（等效 PMIC 效率，默认 0.93）")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_scenarios_json(args.scenarios)
    base_power = PowerParams1Stateful.from_json(args.power)
    base_batt = BatteryParams3Aging.from_json(args.phone)
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    dt_s = float(args.dt)
    soc0 = float(args.soc0)
    eps = float(args.eps)
    if eps <= 0.0 or eps >= 0.25:
        raise ValueError("--eps 建议在 (0,0.25) 内（默认 0.05）")

    soh0 = float(args.soh0)
    alpha_r0 = float(args.alpha_r0)
    if not (0.0 < soh0 < 1.0):
        raise ValueError("--soh0 必须在 (0,1) 内（为了让 α_R 有意义且避免边界截断）")
    if alpha_r0 <= 0.0:
        raise ValueError("--alpha-r0 必须为正")

    eta0 = float(args.eta0)
    if not (0.0 < eta0 <= 1.0):
        raise ValueError("--eta0 必须在 (0,1] 内")

    rep = int(args.replicates)
    if rep <= 0:
        raise ValueError("--replicates 必须为正")

    # 固定种子序列，保证可复现且不同场景可共享同一组 seeds（减少噪声差异）
    seed_base = int(args.seed) * 1_000_000 + 22_000
    seeds = [seed_base + i for i in range(rep)]

    # 基准 Q2UQSample：只用于把“尺度因子/η0”应用到 power/battery 参数上。
    base_sample = Q2UQSample(
        batt_capacity_scale=1.0,
        batt_r0_scale=1.0,
        batt_r1_scale=1.0,
        v_cut_V=float(base_batt.v_cut_V),
        soc_min=float(base_batt.soc_min),
        eta_pmic=float(eta0),
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

    # 9 个参数：输出符号用于图/表
    params: list[dict[str, str]] = [
        {"param_id": "eta_pmic", "param_symbol": "η0"},
        {"param_id": "soh", "param_symbol": "SOH"},
        {"param_id": "alpha_r", "param_symbol": "α_R"},
        {"param_id": "hA", "param_symbol": "hA"},
        {"param_id": "screen_scale", "param_symbol": "k_b"},
        {"param_id": "cpu_scale", "param_symbol": "k_cpu"},
        {"param_id": "gpu_scale", "param_symbol": "k_gpu"},
        {"param_id": "rrc_data_scale", "param_symbol": "b_{q,m}"},
        {"param_id": "rrc_tail_scale", "param_symbol": "τ_m"},
    ]

    def _simulate_mean_tte_h(*, sc_id: str, sample: Q2UQSample, batt_override: BatteryParams3Aging | None, soh: float, alpha_r: float) -> float:
        p, b = apply_q2_uq_sample(base_power, base_batt, sample)
        if batt_override is not None:
            b = batt_override
        cap_loss0 = float(1.0 - float(soh))
        r0_growth0 = float(max(0.0, float(alpha_r)) * cap_loss0)
        st = simulate_tte_replicates(
            materialize_scenario(raw, sc_id),
            power=p,
            batt=b,
            power0_dummy=power0_dummy,
            dt_s=dt_s,
            soc0=soc0,
            seeds=seeds,
            battery_model="model3",
            cap_loss0_frac=cap_loss0,
            r0_growth0_frac=r0_growth0,
            r1_growth0_frac=0.0,
        )
        return float(st["tte_mean_h"])

    # -----------------------------
    # 1) 计算：S1-S5 × 9 参数 × ±5%
    # -----------------------------
    all_rows: list[dict[str, object]] = []
    for s_code, sc_id, s_label in DOC_SCENARIOS:
        # 基准：用于 ΔTTE(%)
        y0 = _simulate_mean_tte_h(sc_id=sc_id, sample=base_sample, batt_override=None, soh=soh0, alpha_r=alpha_r0)

        # hA 的“基准值”来自电池参数（hA=1/R_th）。为了避免与其它参数混杂，基准 hA 基于 base_sample 应用后的电池。
        _p_tmp, _b_tmp = apply_q2_uq_sample(base_power, base_batt, base_sample)
        hA0 = 1.0 / float(_b_tmp.r_th_K_per_W)

        for p in params:
            pid = str(p["param_id"])
            sym = str(p["param_symbol"])

            # 默认：不改 health/thermal
            soh_minus = soh0
            soh_plus = soh0
            alpha_minus = alpha_r0
            alpha_plus = alpha_r0
            batt_minus = None
            batt_plus = None
            s_minus = base_sample
            s_plus = base_sample

            if pid == "soh":
                soh_minus = max(1e-6, min(0.999, soh0 * (1.0 - eps)))
                soh_plus = max(1e-6, min(0.999, soh0 * (1.0 + eps)))
            elif pid == "alpha_r":
                alpha_minus = max(1e-9, alpha_r0 * (1.0 - eps))
                alpha_plus = max(1e-9, alpha_r0 * (1.0 + eps))
            elif pid == "hA":
                hA_minus = hA0 * (1.0 - eps)
                hA_plus = hA0 * (1.0 + eps)
                # hA = 1/R_th -> R_th = 1/hA
                rth_minus = 1.0 / float(hA_minus)
                rth_plus = 1.0 / float(hA_plus)
                batt_minus = replace(_b_tmp, r_th_K_per_W=float(rth_minus))
                batt_plus = replace(_b_tmp, r_th_K_per_W=float(rth_plus))
            else:
                # Q2UQSample 中的乘性参数
                v0 = float(getattr(base_sample, pid))
                v_minus = float(v0 * (1.0 - eps))
                v_plus = float(v0 * (1.0 + eps))
                # η0 需要保持在 (0,1]
                if pid == "eta_pmic":
                    v_minus = max(1e-6, min(1.0, v_minus))
                    v_plus = max(1e-6, min(1.0, v_plus))
                s_minus = replace(base_sample, **{pid: float(v_minus)})
                s_plus = replace(base_sample, **{pid: float(v_plus)})

            y_minus = _simulate_mean_tte_h(sc_id=sc_id, sample=s_minus, batt_override=batt_minus, soh=soh_minus, alpha_r=alpha_minus)
            y_plus = _simulate_mean_tte_h(sc_id=sc_id, sample=s_plus, batt_override=batt_plus, soh=soh_plus, alpha_r=alpha_plus)

            d_minus = _delta_pct(y_minus, y0)
            d_plus = _delta_pct(y_plus, y0)
            score = float(max(abs(d_minus), abs(d_plus))) if np.isfinite(d_minus) and np.isfinite(d_plus) else float("nan")

            all_rows.append(
                {
                    "scenario_code": s_code,
                    "scenario_id": sc_id,
                    "scenario_label_zh": s_label,
                    "dt_s": float(dt_s),
                    "soc0": float(soc0),
                    "replicates": int(rep),
                    "eps": float(eps),
                    "param_id": pid,
                    "param_symbol": sym,
                    "tte_base_h": float(y0),
                    "tte_minus_h": float(y_minus),
                    "tte_plus_h": float(y_plus),
                    "delta_minus_pct": float(d_minus),
                    "delta_plus_pct": float(d_plus),
                    "score_absmax_pct": float(score),
                    "soh0": float(soh0),
                    "alpha_r0": float(alpha_r0),
                    "eta0": float(eta0),
                    "hA0": float(hA0),
                }
            )

    # CSV 明细（可追溯/可复算）
    csv_path = out_dir / "local_sensitivity_s1_s5_9params.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fields = list(all_rows[0].keys()) if all_rows else []
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    # -----------------------------
    # 2) Tornado 图（每个场景 1 张）
    # -----------------------------
    for s_code, sc_id, s_label in DOC_SCENARIOS:
        rows = [r for r in all_rows if str(r.get("scenario_id")) == sc_id]
        if not rows:
            continue
        y0 = float(rows[0]["tte_base_h"])
        title = f"局部敏感性 Tornado（{s_code}：{s_label}，±5% 扰动；基准 TTE={y0:.2f} h）"
        _plot_tornado(rows=rows, title=title, out_path=out_dir / f"tornado_{s_code}_{sc_id}.png", top_k=5)

    # -----------------------------
    # 3) Top-3 汇总表 + 物理解释（Markdown）
    # -----------------------------
    # 解释模板（按参数给出一句话，写作时可再扩写）
    param_explain: dict[str, str] = {
        "η0": "等效效率缩放：P_batt≈P_device/η0。η0↑→电池侧功率↓→电流↓→TTE↑（低负载下常呈“整体倍率”主导）。",
        "SOH": "健康度：SOH↓同时带来有效容量↓与内阻上升（更易触发欠压截止），因此会缩短 TTE，且在高负载更敏感。",
        "α_R": "增阻强度：在给定 SOH<1 时，α_R↑→R0 增长更快→压降更大→更早触发欠压/不可行事件→TTE↓。",
        "hA": "散热强度（hA=1/R_th）：hA↓→温升更高→等效内阻/有效容量更不利→高负载场景更易提前关机。",
        "k_b": "屏幕尺度：亮屏持续或亮度较高时，屏幕项是稳定“底盘功耗”，对 TTE 有直接线性影响。",
        "k_cpu": "CPU尺度：CPU 负载↑会显著抬升功耗与电流，进而放大压降与热效应，缩短 TTE（尤其在交互/计算密集场景）。",
        "k_gpu": "GPU尺度：图形渲染/游戏/视频解码等场景中 GPU 项占比高，尺度变化会显著改变平均功耗与峰值压降。",
        "b_{q,m}": "单位吞吐能耗：网络有吞吐时，b_{q,m}↑→每 MB 能量↑→网络能耗↑→TTE↓（对流媒体/加载型场景更敏感）。",
        "τ_m": "尾态时间常数：突发结束后“拖尾功耗”积分与 τ_m 成正比；高频 burst（社交/导航）场景对 τ_m 更敏感。",
    }

    md_path = out_dir / "敏感性分析_产物.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Q3 7.1 局部敏感性分析（S1–S5，9 参数，±5% 扰动）\n\n")
        f.write("本目录产物用于填充 `敏感性分析.docx` 模板中的“7.1 敏感性分析”内容。\n\n")
        f.write("## 方法\n\n")
        f.write("对每个参数 $\\theta_j$ 在基准点附近做对称扰动 $\\varepsilon=0.05$：\n\n")
        f.write("- $TTE(\\theta_j(1+\\varepsilon))$ 与 $TTE(\\theta_j(1-\\varepsilon))$；\n")
        f.write("- 以相对变化率作为 Tornado 条形长度：\n\n")
        f.write("$$\\Delta TTE(\\%)=\\frac{TTE(\\theta_j(1\\pm\\varepsilon))-TTE(\\theta_j)}{TTE(\\theta_j)}\\times 100\\%.$$\n\n")
        f.write("为降低随机使用过程噪声，每个设定使用多随机种子重复仿真并取均值（见 CSV 明细）。\n\n")
        f.write("## Tornado 图（ΔTTE% / Top-5）\n\n")
        for s_code, sc_id, s_label in DOC_SCENARIOS:
            fig_name = f"tornado_{s_code}_{sc_id}.png"
            p = out_dir / fig_name
            if p.exists():
                f.write(f"### {s_code} {s_label}\n\n")
                f.write(f"![{s_code} {s_label} Tornado]({fig_name})\n\n")

        f.write("## 各场景 Top-3 敏感参数（物理解释）\n\n")
        f.write("| 场景 | Top-1 | Top-2 | Top-3 |\n")
        f.write("|---|---|---|---|\n")
        for s_code, sc_id, s_label in DOC_SCENARIOS:
            rows = [r for r in all_rows if str(r.get("scenario_id")) == sc_id]
            rows_sorted = sorted(rows, key=lambda r: float(r.get("score_absmax_pct", float("nan"))), reverse=True)
            top3 = rows_sorted[:3]
            if len(top3) < 3:
                continue
            f.write(
                f"| {s_code} {s_label} | {top3[0]['param_symbol']} | {top3[1]['param_symbol']} | {top3[2]['param_symbol']} |\n"
            )

        f.write("\n")
        for s_code, sc_id, s_label in DOC_SCENARIOS:
            rows = [r for r in all_rows if str(r.get("scenario_id")) == sc_id]
            rows_sorted = sorted(rows, key=lambda r: float(r.get("score_absmax_pct", float("nan"))), reverse=True)
            top3 = rows_sorted[:3]
            if len(top3) < 3:
                continue
            f.write(f"### {s_code} {s_label}\n\n")
            for r in top3:
                sym = str(r["param_symbol"])
                f.write(f"- **{sym}**：{param_explain.get(sym, '（待补充解释）')}\n")
            f.write("\n")

        f.write("## 各场景 Top-5 数值表（便于填充 Word 模板）\n\n")
        for s_code, sc_id, s_label in DOC_SCENARIOS:
            rows = [r for r in all_rows if str(r.get("scenario_id")) == sc_id]
            rows_sorted = sorted(rows, key=lambda r: float(r.get("score_absmax_pct", float("nan"))), reverse=True)
            top5 = rows_sorted[:5]
            if not top5:
                continue
            f.write(f"### {s_code} {s_label}\n\n")
            f.write("| 参数 | ΔTTE(-5%) | ΔTTE(+5%) | max|ΔTTE| |\n")
            f.write("|---|---:|---:|---:|\n")
            for r in top5:
                sym = str(r["param_symbol"])
                dm = float(r["delta_minus_pct"])
                dp = float(r["delta_plus_pct"])
                scv = float(r["score_absmax_pct"])
                f.write(f"| {sym} | {dm:+.2f}% | {dp:+.2f}% | {scv:.2f}% |\n")
            f.write("\n")

        f.write("## 产物清单\n\n")
        f.write(f"- 明细数据：`{csv_path.name}`（S1–S5 × 9 参数 × ±5%）\n")
        f.write("- Tornado 图：`tornado_S1_*.png` ~ `tornado_S5_*.png`\n")
        f.write("- 本说明文档：`敏感性分析_产物.md`\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
