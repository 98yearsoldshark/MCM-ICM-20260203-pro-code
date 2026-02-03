#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1-05：生成“功耗量级已锚定”的游戏场景轨迹候选图（不覆盖论文材料旧图）。

动机（面向赛题 Q1）：
- Q1 要求连续时间方程输出 SOC(t)，并能逐步纳入屏幕/CPU/网络/GPS/后台等影响因素。
- 仅靠“手写名义功耗”容易被质疑不贴近真实；更稳妥的做法是用公开测量数据锚定功耗量级。

本脚本做法：
- 电池侧：仍使用 Model-1（1RC ECM）的连续时间方程（保持 Q1 主线清晰）。
- 负载侧：使用 no7 升级版“状态化功耗模型”（PowerParams1Stateful + StatefulPowerModel1），
  其参数在本项目中已通过 AndroWatts 等公开数据做过量级校准（见对应 JSON 的 meta.notes_zh）。

输出策略：
- 默认将图片/CSV 写到 Q1材料/05/.../other/ 下（文件名含 candidate，不覆盖 figure.png）。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from mcm26a.battery import BatteryParams1ECM
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import load_scenarios_json, materialize_scenario
from mcm26a.sim import simulate_model1_ecm_trace
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig

import matplotlib.pyplot as plt


THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
ROOT_DIR = SRC_DIR.parent  # MCM_Sim/26A


def _write_csv(path: Path, *, header: list[str], rows_iter) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows_iter:
            w.writerow(row)


def _plot_trace(*, tr, batt: BatteryParams1ECM, title: str, mode: str, out_png: Path) -> None:
    style = apply_style(mode)  # sets rcParams

    t_h = np.asarray(tr.t_s, dtype=float) / 3600.0
    soc_pct = np.asarray(tr.soc, dtype=float) * 100.0
    v_term = np.asarray(tr.v_term_V, dtype=float)
    p = np.asarray(tr.p_W, dtype=float)
    p_max = np.asarray(tr.p_max_W, dtype=float)
    v1 = np.asarray(tr.v1_V, dtype=float)

    c_soc = "#4C78A8"
    c_v = "#E45756"
    c_p = PALETTE_SKIP_GRADIENT[2]
    c_v1 = PALETTE_SKIP_GRADIENT[0]

    nrows = 4 if style.annotate else 3
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10.0, 7.6 if style.annotate else 6.8), sharex=True)
    if nrows == 3:
        ax1, ax2, ax3 = axes
        ax4 = None
    else:
        ax1, ax2, ax3, ax4 = axes

    ax1.plot(t_h, soc_pct, color=c_soc, lw=2.0)
    ax1.set_ylabel("SOC（%）")
    ax1.set_title(f"{title}{style.title_suffix}")

    ax2.plot(t_h, v_term, color=c_v, lw=2.0)
    ax2.axhline(float(batt.v_cut_V), color="gray", ls="--", lw=1.0, alpha=0.75)
    ax2.set_ylabel("端电压 V_term（V）")

    ax3.plot(t_h, p, color=c_p, lw=2.0, label="P(t)")
    ax3.plot(t_h, p_max, color="gray", lw=1.6, ls="--", alpha=0.9, label="P_max(t)")
    ax3.set_ylabel("功率（W）")
    if ax4 is None:
        ax3.set_xlabel("时间（小时）")
    ax3.legend(frameon=False, loc="upper right")

    if ax4 is not None:
        ax4.plot(t_h, v1, color=c_v1, lw=2.0)
        ax4.set_ylabel("极化电压 v1（V）")
        ax4.set_xlabel("时间（小时）")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.01,
            0.02,
            "说明：本图使用“状态化功耗模型”生成 P(t)，并将其作为电池端连续时间 ECM 的功率输入，得到 SOC(t) 与 V_term(t)。\n"
            "功耗参数来自公开数据量级校准（见 power JSON 的 meta.notes_zh），因此该轨迹更贴近真实手机功耗范围。\n"
            f"轨迹状态={tr.status}，dt={float(tr.t_s[1]-tr.t_s[0]) if len(tr.t_s)>1 else float('nan'):.2f}s。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_png, mode=mode)  # type: ignore[arg-type]
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1-05：生成游戏场景轨迹候选图（stateful power，不覆盖旧图）")
    ap.add_argument(
        "--scenarios",
        default=str(SRC_DIR / "configs" / "scenarios_v0.json"),
        help="场景配置 JSON",
    )
    ap.add_argument(
        "--battery",
        default=str(SRC_DIR / "configs" / "phone_default_v1_ecm.json"),
        help="电池参数 JSON（Model-1: 1RC ECM）",
    )
    ap.add_argument(
        "--power-stateful",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="状态化功耗参数 JSON（no7/AndroWatts 校准版）",
    )
    ap.add_argument("--scenario-id", default="S3_gaming", help="场景 ID（默认 S3_gaming）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC（0~1）")
    ap.add_argument("--dt", type=float, default=2.0, help="积分步长（秒）")
    ap.add_argument("--seed", type=int, default=1, help="功耗随机过程随机种子（可复现）")
    ap.add_argument(
        "--out-dir",
        default=str(ROOT_DIR / "论文" / "理论模型" / "论文阶段" / "Q1材料" / "05-轨迹示例_游戏高负载" / "other"),
        help="输出目录（默认写入 Q1材料/05/.../other/）",
    )
    ap.add_argument("--mode", default="paper", choices=("paper", "study", "both"), help="输出模式：paper/study/both")
    args = ap.parse_args()

    raw = load_scenarios_json(Path(args.scenarios))
    sid = str(args.scenario_id)
    if sid not in raw.get("scenarios", {}):
        raise SystemExit(f"[ERROR] scenarios 中不存在 {sid!r}，可用：{list(raw.get('scenarios', {}).keys())}")
    sc = materialize_scenario(raw, sid)

    batt = BatteryParams1ECM.from_json(Path(args.battery))

    # 使用 stateful 功耗模型（no7 版），并通过 seed 固定随机过程。
    p_stateful = PowerParams1Stateful.from_json(Path(args.power_stateful))
    power_model = StatefulPowerModel1(p_stateful, seed=int(args.seed))

    # simulate_model1_ecm_trace 的签名仍要求 power_params: PowerParams0，但当 power_model!=None 时不会使用它。
    # 为保持接口稳定，这里传入一个“占位”的 PowerParams0。
    dummy_power = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    tr = simulate_model1_ecm_trace(
        sc,
        power_params=dummy_power,
        power_model=power_model,
        battery_params=batt,
        soc0=float(args.soc0),
        dt_s=float(args.dt),
    )

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 导出数据版本（候选）
    _write_csv(
        out_dir / "data_candidate_trace_stateful_power.csv",
        header=["t_s", "t_h", "soc", "v_term_V", "p_W", "p_max_W", "v1_V", "status", "scenario_id", "seed"],
        rows_iter=(
            [
                float(t),
                float(t) / 3600.0,
                float(s),
                float(v),
                float(p),
                float(pm),
                float(v1),
                str(tr.status),
                str(tr.scenario_id),
                int(args.seed),
            ]
            for t, s, v, p, pm, v1 in zip(tr.t_s, tr.soc, tr.v_term_V, tr.p_W, tr.p_max_W, tr.v1_V)
        ),
    )

    title = "Q1-05 候选轨迹：游戏（状态化功耗量级锚定）"

    modes = ("paper", "study") if str(args.mode) == "both" else (str(args.mode),)
    for mode in modes:
        out_png = out_dir / f"figure_candidate_trace_{sid}_stateful_seed{int(args.seed)}_{mode}.png"
        _plot_trace(tr=tr, batt=batt, title=title, mode=mode, out_png=out_png)

    print(f"[OK] Q1-05 候选轨迹图与数据已生成到：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
