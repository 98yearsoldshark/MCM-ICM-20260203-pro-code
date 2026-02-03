#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Q2 单因素敏感性龙卷风图（Tornado Diagram, OAT）。

动机：
- 题面/论文第 7.1 更适合用“单因素敏感性（one-at-a-time）”来回答：哪些参数最敏感；
- 我们已有 PRCC/不确定性传播，但 Tornado 图更直观、也更贴近常见评分点；
- 本脚本只改变 1 个参数（其余保持基准），对 TTE 的影响用 “低值/高值” 两端展示。

输出（默认）：
- `src/out_reports/q2/param_tornado_oat.csv`：可复现数据表（每行一个参数）。
- 同步到论文材料目录（不覆盖旧文件，新增 back_ 前缀）：
  - `论文/.../Q2材料/16-龙卷风图/back_figure.png`
  - `论文/.../Q2材料/16-龙卷风图/other/back_figure_study.png`
  - `论文/.../Q2材料/16-龙卷风图/other/back_data.csv`
  - `论文/.../Q2材料/16-龙卷风图/other/back_about.md`
  - `论文/.../Q2材料/16-龙卷风图/back_paper_fragment_zh.md`

注意：
- 时间单位在仿真内部统一使用秒（s），图中输出以小时（h）呈现，便于写论文。
- 为降低随机过程噪声，采用“共同随机数（CRN）”：baseline 与每个扰动使用同一组随机种子。
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
REPO_DIR = SRC_DIR.parent.parent  # .../MCM_Sim

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.analysis.q3_sensitivity import q3_param_label_zh
from mcm26a.battery import BatteryParams3Aging
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model3_aging
from mcm26a.uq.q2_uq import Q2UQSample, apply_q2_uq_sample
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, PlotMode, apply_style, ensure_dir, savefig


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _backup_if_exists(path: Path, *, history_dir: Path) -> None:
    """备份同名文件，避免“覆盖=丢失历史”。"""

    if not path.exists() or path.is_dir():
        return
    _ensure_dir(history_dir)
    dst = history_dir / f"{_now_ts()}_{path.name}"
    k = 1
    while dst.exists():
        dst = history_dir / f"{_now_ts()}_{k}_{path.name}"
        k += 1
    shutil.move(str(path), str(dst))


def _baseline_sample(power1: PowerParams1Stateful, batt: BatteryParams3Aging, *, eta_pmic: float = 1.0) -> Q2UQSample:
    # 说明：baseline 的尺度因子全部取 1；阈值类参数取配置文件中的名义值，
    # 保证“扰动前”与当前主模型一致。
    return Q2UQSample(
        batt_capacity_scale=1.0,
        batt_r0_scale=1.0,
        batt_r1_scale=1.0,
        v_cut_V=float(batt.v_cut_V),
        soc_min=float(batt.soc_min),
        # eta_pmic=1 表示“已吸收在功耗参数中”；若你想显式建模 PMIC 损耗，可在参数集中设置 eta_pmic<1。
        eta_pmic=float(eta_pmic),
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


def _param_bounds(batt: BatteryParams3Aging) -> dict[str, tuple[float, float]]:
    # 与 mcm26a.uq.sample_q2_uq 的区间保持一致，便于“表格先验 ↔ 图像敏感性 ↔ 代码抽样”对齐。
    return {
        # battery
        "batt_capacity_scale": (0.90, 1.10),
        "batt_r0_scale": (0.80, 1.30),
        "batt_r1_scale": (0.80, 1.30),
        "v_cut_V": (3.2, 3.4),
        "soc_min": (0.0, 0.10),
        # power chain
        "eta_pmic": (0.90, 0.95),
        # power
        "base_scale": (0.70, 1.30),
        "screen_scale": (0.70, 1.30),
        "cpu_scale": (0.60, 1.40),
        "gpu_scale": (0.60, 1.40),
        "gps_scale": (0.70, 1.30),
        "background_base_scale": (0.70, 1.30),
        # radio
        "rrc_state_scale": (0.60, 1.60),
        "rrc_data_scale": (0.60, 1.60),
        "rrc_tail_scale": (0.70, 1.30),
        "poor_signal_psi_scale": (0.90, 1.30),
        # stochastic + interaction
        "bg_lambda_scale": (0.50, 2.00),
        "interaction_scale": (0.00, 1.60),
    }


def _load_q3_9params_baseline(q3_csv: Path, *, batt: BatteryParams3Aging) -> tuple[float, dict[str, float]]:
    """读取 Q3 '16-生产需要的内容' 的 9 参数基准与 eps（用于对齐口径）。

返回：
- eps：相对扰动幅度（例如 0.05 表示 ±5%）
- baseline：包含 soh/alpha_r/eta_pmic/hA 的基准值
"""

    if not q3_csv.exists():
        # 兜底：hA 用当前电池热阻换算，其它用经验默认值
        hA0 = 1.0 / max(float(batt.r_th_K_per_W), 1e-9)
        return 0.05, {"soh": 0.90, "alpha_r": 1.5, "eta_pmic": 0.93, "hA": float(hA0)}

    with q3_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"q3 9 参数 CSV 为空：{q3_csv}")
    r0 = rows[0]
    eps = float(r0.get("eps", "0.05"))
    # 这些列在生产 CSV 中是常量列（每行重复）
    soh0 = float(r0.get("soh0", "0.90"))
    alpha_r0 = float(r0.get("alpha_r0", "1.5"))
    eta0 = float(r0.get("eta0", "0.93"))
    hA0 = float(r0.get("hA0", str(1.0 / max(float(batt.r_th_K_per_W), 1e-9))))
    return float(eps), {"soh": soh0, "alpha_r": alpha_r0, "eta_pmic": eta0, "hA": hA0}


def _caploss_r0growth_from_soh_alpha(soh: float, alpha_r: float) -> tuple[float, float]:
    """把 (SOH, α_R) 映射为模型初始老化状态：cap_loss0 与 r0_growth0。"""

    soh = float(min(1.0, max(0.0, soh)))
    alpha_r = float(max(0.0, alpha_r))
    cap_loss0 = float(max(0.0, 1.0 - soh))
    r0_growth0 = float(alpha_r * (1.0 - soh))
    return cap_loss0, r0_growth0


def _replace_hA(batt: BatteryParams3Aging, *, hA: float) -> BatteryParams3Aging:
    """用 hA（W/K）替换电池热阻 r_th（K/W）：r_th ≈ 1/hA。"""

    hA = float(hA)
    hA = max(hA, 1e-9)
    return replace(batt, r_th_K_per_W=float(1.0 / hA))


def _scenario_ids(raw: dict[str, Any], *, scenario: str) -> list[str]:
    sids = list(raw.get("scenarios", {}).keys())
    if scenario.lower() in ("all", "*"):
        return sids
    if scenario not in raw.get("scenarios", {}):
        raise KeyError(f"scenarios.json 中不存在 scenario_id={scenario!r}")
    return [str(scenario)]


def _metric_mean_tte_h(
    raw: dict[str, Any],
    *,
    scenario_ids: list[str],
    power1: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    power0_dummy: PowerParams0,
    soc0: float,
    dt_s: float,
    n_seeds: int,
    seed0: int,
    cap_loss0_frac: float = 0.0,
    r0_growth0_frac: float = 0.0,
) -> float:
    """输出指标：平均 TTE（小时），对随机种子与场景取均值。"""

    xs: list[float] = []
    for s in range(int(n_seeds)):
        seed = int(seed0) + s
        for sid_idx, sid in enumerate(scenario_ids):
            sc = materialize_scenario(raw, sid)
            # CRN：对 baseline 与扰动使用同一 seed（并从同一起点 RNG 状态开始）
            sim_seed = seed * 10_000 + sid_idx
            pm = StatefulPowerModel1(power1, seed=sim_seed)
            r = simulate_model3_aging(
                sc,
                power_params=power0_dummy,
                power_model=pm,
                battery_params=batt,
                soc0=float(soc0),
                cap_loss0_frac=float(cap_loss0_frac),
                r0_growth0_frac=float(r0_growth0_frac),
                dt_s=float(dt_s),
            )
            if r.tte_h is not None and np.isfinite(float(r.tte_h)):
                xs.append(float(r.tte_h))

    return float(np.mean(np.array(xs, dtype=float))) if xs else float("nan")


def _plot_tornado(
    rows: list[dict[str, Any]],
    *,
    baseline_h: float,
    scenario_title_zh: str,
    soc0: float,
    mode: PlotMode,
) -> plt.Figure:
    style = apply_style(mode)

    # 配色：两端（低值/高值）使用用户给的 4 色表里的两种，避免“渐变”造成误读。
    color_low = PALETTE_SKIP_GRADIENT[0]   # #845ec2
    color_high = PALETTE_SKIP_GRADIENT[2]  # #00c2a8

    labels = [str(r["param_zh"]) for r in rows]
    y = np.arange(len(rows))

    # 动态高度：避免重叠；paper 更紧凑。
    h = max(4.2, 0.36 * len(rows) + 1.8) if mode == "paper" else max(4.8, 0.42 * len(rows) + 2.2)
    fig, ax = plt.subplots(figsize=(10.8, h))

    # 双端柱：从 baseline 指向 low/high 输出（经典 tornado 画法）
    for i, r in enumerate(rows):
        low_h = float(r["tte_low_h"])
        high_h = float(r["tte_high_h"])

        # low 端
        ax.barh(
            i,
            abs(low_h - baseline_h),
            left=min(low_h, baseline_h),
            height=0.72,
            color=color_low,
            alpha=0.88,
            edgecolor="none",
            label="参数取低值" if i == 0 else None,
        )
        # high 端
        ax.barh(
            i,
            abs(high_h - baseline_h),
            left=min(high_h, baseline_h),
            height=0.72,
            color=color_high,
            alpha=0.88,
            edgecolor="none",
            label="参数取高值" if i == 0 else None,
        )

        if style.annotate:
            low_v = r["low_value"]
            high_v = r["high_value"]
            # 端点标注：输出值 + 对应参数取值（括号）
            ax.text(
                low_h,
                i,
                f"{low_h:.2f}h（{low_v:g}）",
                va="center",
                ha=("right" if low_h < baseline_h else "left"),
                fontsize=9,
                color="#222222",
            )
            ax.text(
                high_h,
                i,
                f"{high_h:.2f}h（{high_v:g}）",
                va="center",
                ha=("left" if high_h > baseline_h else "right"),
                fontsize=9,
                color="#222222",
            )

    ax.axvline(float(baseline_h), color="#222222", lw=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("预测续航时间 TTE（小时）")
    ax.set_title(f"Q2：单因素敏感性龙卷风图（{scenario_title_zh}，SOC0={soc0:.0%}）{style.title_suffix}")
    ax.legend(loc="lower right", frameon=False)

    # 视觉留白
    vals = [float(r["tte_low_h"]) for r in rows] + [float(r["tte_high_h"]) for r in rows] + [float(baseline_h)]
    vmin = float(np.nanmin(np.array(vals, dtype=float)))
    vmax = float(np.nanmax(np.array(vals, dtype=float)))
    span = max(1e-6, vmax - vmin)
    ax.set_xlim(vmin - 0.08 * span, vmax + 0.08 * span)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：龙卷风图用于“单因素敏感性分析（OAT）”。\n"
            "- 竖线：基准参数下的平均 TTE。\n"
            "- 每行只改变 1 个参数：分别取其先验下界/上界，其余参数固定为基准；两端标注为 TTE（小时）与对应参数取值。\n"
            "- 横条越长：该参数对 TTE 越敏感；可直接用于回答题面“哪些因素影响最大/最小”。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 单因素敏感性 Tornado 图（OAT）")
    ap.add_argument("--scenarios", default=str(SRC_DIR / "configs" / "scenarios_v0.json"), help="场景配置 JSON 路径")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON 路径（stateful, Model-1 power）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（Model-3 battery）",
    )
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2"), help="CSV 输出目录（默认 out_reports/q2）")
    ap.add_argument(
        "--paper-dir",
        default=str(
            SRC_DIR.parent
            / "论文"
            / "理论模型"
            / "论文阶段"
            / "Q2材料"
            / "16-龙卷风图"
        ),
        help="论文材料目录（会写入 back_figure 等）",
    )
    ap.add_argument("--scenario", default="S4_mixed_day", help="用于 tornado 的场景（默认 S4_mixed_day；也可用 all）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1，默认 1.0）")
    ap.add_argument("--dt", type=float, default=5.0, help="积分步长（秒），默认 5.0")
    ap.add_argument("--seeds", type=int, default=30, help="随机种子数量（越大越稳），默认 30")
    ap.add_argument("--seed0", type=int, default=2026, help="随机种子起点，默认 2026")
    ap.add_argument("--top-k", type=int, default=10, help="只画影响最大的前 K 个参数（默认 10）")
    ap.add_argument("--include-eta", action="store_true", help="是否把 η_PMIC 也纳入 tornado（默认不纳入）")
    ap.add_argument(
        "--param-set",
        default="q3_9",
        choices=["auto_prcc_topk", "q3_9"],
        help="参数集合：q3_9=使用 Q3材料/16 的9参数（SOH/η0/α_R/hA/k_b/k_cpu/k_gpu/τ_m/b_{q,m}）；auto_prcc_topk=按PRCC挑选候选",
    )
    ap.add_argument(
        "--q3-9-csv",
        default=str(
            SRC_DIR.parent
            / "论文"
            / "理论模型"
            / "论文阶段"
            / "Q3材料"
            / "16-生产需要的内容"
            / "local_sensitivity_s1_s5_9params.csv"
        ),
        help="Q3 9 参数生产 CSV（用于读取 eps 与基准值）",
    )
    args = ap.parse_args()

    raw = load_scenarios_json(Path(args.scenarios))
    power1 = PowerParams1Stateful.from_json(Path(args.power))
    batt = BatteryParams3Aging.from_json(Path(args.phone))
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    sids = _scenario_ids(raw, scenario=str(args.scenario))
    title_zh = "全部场景平均" if str(args.scenario).lower() in ("all", "*") else str(raw["scenarios"][sids[0]].get("title_zh", sids[0]))

    # --- 参数集合与基准（用于对齐 Q3 生产口径的 9 参数） ---
    eps, q3_base = _load_q3_9params_baseline(Path(args.q3_9_csv), batt=batt)
    bounds = _param_bounds(batt)

    if str(args.param_set) == "q3_9":
        # 对齐 Q3材料/16 的“9 个生产参数”（符号口径）
        cand_names = [
            "soh",
            "eta_pmic",
            "alpha_r",
            "hA",
            "screen_scale",
            "cpu_scale",
            "gpu_scale",
            "rrc_tail_scale",
            "rrc_data_scale",
        ]
        symbol = {
            "soh": "SOH",
            "eta_pmic": "η0",
            "alpha_r": "α_R",
            "hA": "hA",
            "screen_scale": "k_b",
            "cpu_scale": "k_cpu",
            "gpu_scale": "k_gpu",
            "rrc_tail_scale": "τ_m",
            "rrc_data_scale": "b_{q,m}",
        }

        baseline = _baseline_sample(power1, batt, eta_pmic=float(q3_base.get("eta_pmic", 1.0)))
        base_soh = float(q3_base.get("soh", 1.0))
        base_alpha_r = float(q3_base.get("alpha_r", 1.0))
        base_hA = float(q3_base.get("hA", 1.0 / max(float(batt.r_th_K_per_W), 1e-9)))
        base_cap_loss0, base_r0_growth0 = _caploss_r0growth_from_soh_alpha(base_soh, base_alpha_r)
    else:
        # auto_prcc_topk：用 PRCC 总表挑候选（保持旧逻辑）
        baseline = _baseline_sample(power1, batt, eta_pmic=1.0)
        base_soh = 1.0
        base_alpha_r = 1.0
        base_hA = 1.0 / max(float(batt.r_th_K_per_W), 1e-9)
        base_cap_loss0, base_r0_growth0 = 0.0, 0.0

        # 优化：如果已有 PRCC 总表，则用其排序挑选候选参数，避免对“显然不敏感”的参数做 OAT 扫描。
        cand_names = [k for k in bounds.keys() if (k != "eta_pmic" or bool(args.include_eta))]
        if int(args.top_k) > 0:
            prcc_path = Path(args.out_reports) / "param_sensitivity_overall.csv"
            try:
                if prcc_path.exists():
                    with prcc_path.open("r", encoding="utf-8", newline="") as f:
                        prcc_rows = list(csv.DictReader(f))
                    prcc_rows = [r for r in prcc_rows if abs(float(r.get("soc0", "nan")) - float(args.soc0)) < 1e-9]
                    prcc_rows = [r for r in prcc_rows if str(r.get("param", "")) in cand_names]
                    prcc_rows.sort(key=lambda r: float(r.get("mean_abs_prcc", "nan")), reverse=True)
                    pick = [str(r.get("param", "")) for r in prcc_rows if r.get("param")]
                    pick = [p for p in pick if p]
                    pick = pick[: int(args.top_k)]
                    for must in ["v_cut_V", "soc_min"]:
                        if must in cand_names and must not in pick:
                            pick.append(must)
                    cand_names = pick
            except Exception:
                pass
        symbol = {k: q3_param_label_zh(k) for k in cand_names}

    # --- baseline：只算一次 ---
    p0, b_tmp = apply_q2_uq_sample(power1, batt, baseline)
    b0 = _replace_hA(b_tmp, hA=float(base_hA)) if str(args.param_set) == "q3_9" else b_tmp

    print(f"[tornado] scenario={args.scenario} (n={len(sids)}), soc0={float(args.soc0):.3f}, dt={float(args.dt)}s, seeds={int(args.seeds)}")
    print(f"[tornado] param_set={args.param_set}, eps={eps if str(args.param_set)=='q3_9' else 'n/a'}")
    print(f"[tornado] scanning params: {cand_names}")

    base_h = _metric_mean_tte_h(
        raw,
        scenario_ids=sids,
        power1=p0,
        batt=b0,
        power0_dummy=power0_dummy,
        soc0=float(args.soc0),
        dt_s=float(args.dt),
        n_seeds=int(args.seeds),
        seed0=int(args.seed0),
        cap_loss0_frac=float(base_cap_loss0),
        r0_growth0_frac=float(base_r0_growth0),
    )
    print(f"[tornado] baseline mean TTE = {base_h:.3f} h")

    # 单因素：逐参数跑 low/high
    rows: list[dict[str, Any]] = []
    for name in cand_names:
        name = str(name)

        # --- low/high 取值 ---
        if str(args.param_set) == "q3_9":
            base_val = {
                "soh": float(base_soh),
                "alpha_r": float(base_alpha_r),
                "hA": float(base_hA),
            }.get(name, float(asdict(baseline).get(name, 1.0)))
            lo = float(base_val) * (1.0 - float(eps))
            hi = float(base_val) * (1.0 + float(eps))
            if name == "soh":
                lo = float(min(1.0, max(0.0, lo)))
                hi = float(min(1.0, max(0.0, hi)))
            if name in ("eta_pmic", "alpha_r", "hA"):
                lo = float(max(1e-9, lo))
                hi = float(max(1e-9, hi))
        else:
            lo, hi = bounds[str(name)]
            base_val = float(asdict(baseline)[str(name)]) if str(name) in asdict(baseline) else float("nan")

        print(f"[tornado] {name}: low={lo}, high={hi} ...")

        # --- 构造 power/batt 与初始老化状态 ---
        cap_loss_low = float(base_cap_loss0)
        cap_loss_high = float(base_cap_loss0)
        r0g_low = float(base_r0_growth0)
        r0g_high = float(base_r0_growth0)
        batt_low = b0
        batt_high = b0

        if str(args.param_set) == "q3_9" and name == "soh":
            cap_loss_low, r0g_low = _caploss_r0growth_from_soh_alpha(float(lo), float(base_alpha_r))
            cap_loss_high, r0g_high = _caploss_r0growth_from_soh_alpha(float(hi), float(base_alpha_r))
            p_low, _ = apply_q2_uq_sample(power1, batt, baseline)
            p_high, _ = apply_q2_uq_sample(power1, batt, baseline)
        elif str(args.param_set) == "q3_9" and name == "alpha_r":
            cap_loss_low, r0g_low = _caploss_r0growth_from_soh_alpha(float(base_soh), float(lo))
            cap_loss_high, r0g_high = _caploss_r0growth_from_soh_alpha(float(base_soh), float(hi))
            p_low, _ = apply_q2_uq_sample(power1, batt, baseline)
            p_high, _ = apply_q2_uq_sample(power1, batt, baseline)
        elif str(args.param_set) == "q3_9" and name == "hA":
            batt_low = _replace_hA(b0, hA=float(lo))
            batt_high = _replace_hA(b0, hA=float(hi))
            p_low, _ = apply_q2_uq_sample(power1, batt, baseline)
            p_high, _ = apply_q2_uq_sample(power1, batt, baseline)
        else:
            if not hasattr(baseline, name):
                continue
            s_low = replace(baseline, **{name: float(lo)})
            s_high = replace(baseline, **{name: float(hi)})
            p_low, b_low = apply_q2_uq_sample(power1, batt, s_low)
            p_high, b_high = apply_q2_uq_sample(power1, batt, s_high)
            if str(args.param_set) == "q3_9":
                batt_low = _replace_hA(b_low, hA=float(base_hA))
                batt_high = _replace_hA(b_high, hA=float(base_hA))
            else:
                batt_low = b_low
                batt_high = b_high

        t_low = _metric_mean_tte_h(
            raw,
            scenario_ids=sids,
            power1=p_low,
            batt=batt_low,
            power0_dummy=power0_dummy,
            soc0=float(args.soc0),
            dt_s=float(args.dt),
            n_seeds=int(args.seeds),
            seed0=int(args.seed0),
            cap_loss0_frac=float(cap_loss_low),
            r0_growth0_frac=float(r0g_low),
        )
        t_high = _metric_mean_tte_h(
            raw,
            scenario_ids=sids,
            power1=p_high,
            batt=batt_high,
            power0_dummy=power0_dummy,
            soc0=float(args.soc0),
            dt_s=float(args.dt),
            n_seeds=int(args.seeds),
            seed0=int(args.seed0),
            cap_loss0_frac=float(cap_loss_high),
            r0_growth0_frac=float(r0g_high),
        )
        print(
            f"[tornado] {name}: TTE_low={t_low:.3f}h, TTE_high={t_high:.3f}h, span={abs(float(t_high)-float(t_low)):.3f}h"
        )

        rows.append(
            {
                "param": str(name),
                "param_zh": str(symbol.get(name, q3_param_label_zh(str(name)))),
                "baseline_value": float(base_val),
                "low_value": float(lo),
                "high_value": float(hi),
                "tte_base_h": float(base_h),
                "tte_low_h": float(t_low),
                "tte_high_h": float(t_high),
                "delta_low_h": float(t_low) - float(base_h),
                "delta_high_h": float(t_high) - float(base_h),
                "span_h": abs(float(t_high) - float(t_low)),
            }
        )

    # 排序 + 截断
    rows = [r for r in rows if np.isfinite(float(r.get("span_h", float("nan"))))]
    rows.sort(key=lambda r: float(r.get("span_h", 0.0)), reverse=True)
    if str(args.param_set) != "q3_9" and int(args.top_k) > 0:
        rows = rows[: int(args.top_k)]

    # 写 CSV（报表目录）
    out_reports = _ensure_dir(Path(args.out_reports))
    out_csv = out_reports / "param_tornado_oat.csv"
    _ensure_dir(out_csv.parent)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "param",
                "param_zh",
                "baseline_value",
                "low_value",
                "high_value",
                "tte_base_h",
                "tte_low_h",
                "tte_high_h",
                "delta_low_h",
                "delta_high_h",
                "span_h",
                "scenario",
                "soc0",
                "dt_s",
                "n_seeds",
                "seed0",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    **r,
                    "scenario": str(args.scenario),
                    "soc0": float(args.soc0),
                    "dt_s": float(args.dt),
                    "n_seeds": int(args.seeds),
                    "seed0": int(args.seed0),
                }
            )

    # 出图（paper/study）
    fig_paper = _plot_tornado(rows, baseline_h=float(base_h), scenario_title_zh=title_zh, soc0=float(args.soc0), mode="paper")
    fig_study = _plot_tornado(rows, baseline_h=float(base_h), scenario_title_zh=title_zh, soc0=float(args.soc0), mode="study")

    # 写入论文材料目录（back_ 前缀 + 历史备份）
    paper_dir = Path(args.paper_dir)
    other = _ensure_dir(paper_dir / "other")
    history = _ensure_dir(other / "_history")

    paper_png = paper_dir / "back_figure.png"
    study_png = other / "back_figure_study.png"
    data_csv = other / "back_data.csv"
    about_md = other / "back_about.md"
    frag_zh = paper_dir / "back_paper_fragment_zh.md"

    for p in [paper_png, study_png, data_csv, about_md, frag_zh]:
        if p.exists():
            _backup_if_exists(p, history_dir=history)

    # 保存图片
    savefig(fig_paper, paper_png, mode="paper")
    plt.close(fig_paper)
    savefig(fig_study, study_png, mode="study")
    plt.close(fig_study)

    # 同步数据（用与 out_reports 同源的行）
    with data_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["scenario", "soc0", "dt_s", "n_seeds", "seed0"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "scenario": str(args.scenario), "soc0": float(args.soc0), "dt_s": float(args.dt), "n_seeds": int(args.seeds), "seed0": int(args.seed0)})

    about_md.write_text(
        (
            "# back_about：Q2 单因素敏感性龙卷风图（OAT）\n\n"
            "## 这张图回答什么？\n"
            "用于回答题面/论文中“哪些建模参数最敏感（影响最大）”。我们采用单因素扰动（OAT）：一次只改变一个参数，比较输出 TTE 的变化幅度。\n\n"
            "## 输出定义\n"
            "- 输出：平均 TTE（小时）。对随机过程做多种子重复，并对所选场景集合取均值。\n\n"
            "## 参数集合与扰动方式\n"
            + (
                (
                    "- 参数集合：对齐 `Q3材料/16-生产需要的内容` 的 9 个参数符号：SOH、η0、α_R、hA、k_b、k_cpu、k_gpu、τ_m、b_{q,m}。\n"
                    f"- 扰动幅度：eps={eps:.3f}（即对基准值做 ±{eps * 100.0:.1f}% 相对扰动）。\n"
                    f"- 基准值来源：`{Path(args.q3_9_csv)}` 的常量列（soh0/alpha_r0/eta0/hA0）；其余尺度因子基准取 1。\n"
                    "- 映射：SOH/α_R -> 初始老化状态 cap_loss0=1-SOH、r0_growth0=α_R(1-SOH)；hA -> 热阻 r_th≈1/hA；\n"
                    "  k_b/k_cpu/k_gpu/τ_m/b_{q,m} 对应为 screen/cpu/gpu 与网络（tail/data）部分的尺度因子。\n"
                )
                if str(args.param_set) == "q3_9"
                else (
                    "- 参数集合：使用 `mcm26a/uq/q2_uq.py::sample_q2_uq()` 的尺度因子先验（便于与 UQ/PRCC 对齐）。\n"
                    "- low/high：取各参数的先验下界/上界，其余保持基准不变。\n"
                )
            )
            + "\n"
            "## 生成方式（可复现）\n"
            f"- 脚本：`MCM_Sim/26A/src/scripts/run_q2_param_tornado_oat.py`\n"
            f"- 参数：scenario={args.scenario}, soc0={float(args.soc0)}, dt={float(args.dt)}s, seeds={int(args.seeds)}, seed0={int(args.seed0)}, param_set={args.param_set}\n"
            f"- 报表数据：`MCM_Sim/26A/src/out_reports/q2/param_tornado_oat.csv`\n"
        ),
        encoding="utf-8",
    )

    frag_zh.write_text(
        (
            "### 7.1 单因素敏感性分析（龙卷风图）\n\n"
            "为识别“哪些参数对续航预测最敏感”，我们采用单因素敏感性分析（One-at-a-time, OAT）：\n"
            "在基准参数附近，分别将某一参数取其低值/高值（其余参数保持基准不变），比较输出 TTE 的变化。\n"
            "图中横条长度表示该参数导致的 TTE 变化幅度，越长则越敏感；竖线为基准 TTE。\n\n"
            "（图：Q2 单因素敏感性龙卷风图，见 `back_figure.png`）\n"
        ),
        encoding="utf-8",
    )

    print(f"wrote: {out_csv}")
    print(f"wrote: {paper_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
