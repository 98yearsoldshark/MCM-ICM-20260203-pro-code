# -*- coding: utf-8 -*-
# 环境相图脚本：把多组 bet-hedging 运行结果（runs.csv + config.json）汇总成“最优策略随环境变化”的相图。
#
# 目的（冲 Z 的加分点）：
# - 展示：环境相关性（p）与波动幅度（R_H/R_L）改变时，“更优的性别比调节策略参数”(gamma,w) 如何迁移。
# - 这能把 bet-hedging 从“单一情景的热图”升级为“环境条件下的适应性相图”。
#
# 说明：
# - 本脚本不重跑仿真，只读取已有 run 目录；
# - 推荐先用 run_sim.py 生成若干 run，例如：
#   python MCM_Sim/24A/run_sim.py bet-hedging --out-dir ... --RH-over-RL 5  --p 0.05 --q 0.2
#   python MCM_Sim/24A/run_sim.py bet-hedging --out-dir ... --RH-over-RL 10 --p 0.05 --q 0.2
#
# 用法示例：
#   python MCM_Sim/24A/scripts/make_env_phase.py \
#     --run-dirs MCM_Sim/24A/outputs/temp/Z_bet_p005_rh5_q02,MCM_Sim/24A/outputs/temp/Z_bet_p02_rh5_q02,...
#   输出默认写到：MCM_Sim/24A/outputs/temp/env_phase-<ts>/

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402

# 尝试启用中文字体（与 plotting.py 保持一致）
plt.rcParams["font.sans-serif"] = [
    "Heiti SC",
    "Songti SC",
    "PingFang SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _parse_paths_csv(s: str) -> list[Path]:
    out: list[Path] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(Path(part))
    return out


def _load_env(run_dir: Path) -> tuple[float, float]:
    """返回 (p, RH_over_RL)。"""
    cfg_path = run_dir / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(str(cfg_path))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    env = cfg.get("env", {})
    R_L = float(env.get("R_L"))
    R_H = float(env.get("R_H"))
    p = float(env.get("p_LH"))
    if R_L <= 0:
        raise ValueError(f"R_L 非法：{R_L}")
    return p, float(R_H / R_L)


def _pick_best_strategy(
    df: pd.DataFrame,
    *,
    host_max: float,
    objective: str,
) -> pd.Series:
    """从 runs.csv 选择一个“最优”S_var 策略（用于相图标注）。

    这里采用一个“生态约束 + 灯鱼目标”的口径：
    - 约束：P_host <= host_max（避免宿主频繁越界）
    - 目标：最大化 objective（默认 geom_mean_N；可用 q10_min_N 等尾部指标）
    """
    if "p_m_override" not in df.columns:
        raise KeyError("runs.csv 缺少列 p_m_override（无法区分 S_var 与固定对照）。")

    sub = df[df["p_m_override"].isna()].copy()
    if sub.empty:
        raise ValueError("该 runs.csv 未包含 S_var 网格。")

    if "P_host" not in sub.columns:
        raise KeyError("runs.csv 缺少列 P_host。")
    if objective not in sub.columns:
        raise KeyError(f"runs.csv 缺少列 {objective}。")

    sub = sub[sub["P_host"].astype(float) <= float(host_max)]
    if sub.empty:
        # 约束过严时退化为“无约束最优”，避免脚本崩掉
        sub = df[df["p_m_override"].isna()].copy()

    # 优先最大化 objective；同分时用尾部风险与概率做稳健 tie-break
    tie_cols = []
    for col in ["q10_min_N", "geom_mean_N", "P_ext", "P_host"]:
        if col in sub.columns:
            tie_cols.append(col)

    sort_cols = [objective] + tie_cols
    # objective/尾部指标越大越好；概率类越小越好
    ascend = [False] + [False] * len(tie_cols)
    for i, col in enumerate(tie_cols):
        if col in {"P_ext", "P_host"}:
            ascend[1 + i] = True

    sub = sub.sort_values(sort_cols, ascending=ascend)
    return sub.iloc[0]


def _plot_phase_heatmap(
    df_phase: pd.DataFrame,
    *,
    value_col: str,
    label_col: str,
    title: str,
    out_path: Path,
) -> None:
    """画 p × (R_H/R_L) 的相图热图，并在格子里标注 (gamma,w)。"""
    ps = sorted({float(x) for x in df_phase["p"].dropna().tolist()})
    rhs = sorted({float(x) for x in df_phase["RH_over_RL"].dropna().tolist()})

    mat = np.full((len(ps), len(rhs)), np.nan, dtype=float)
    labels = [["" for _ in rhs] for __ in ps]

    for _, r in df_phase.iterrows():
        i = ps.index(float(r["p"]))
        j = rhs.index(float(r["RH_over_RL"]))
        mat[i, j] = float(r[value_col])
        labels[i][j] = str(r[label_col])

    # 色条范围（只对有限值）
    finite = mat[np.isfinite(mat)]
    if finite.size == 0:
        vmin, vmax = 0.0, 1.0
    else:
        vmin, vmax = float(np.min(finite)), float(np.max(finite))
        if vmin == vmax:
            vmax = vmin + 1e-9

    norm = Normalize(vmin=vmin, vmax=vmax)
    fig, ax = plt.subplots(figsize=(7.6, 4.6), constrained_layout=True)
    im = ax.imshow(mat, origin="lower", aspect="auto", cmap="viridis", norm=norm)

    ax.set_title(title)
    ax.set_xlabel("R_H/R_L（波动幅度）")
    ax.set_ylabel("p（环境切换概率；越小相关性越强）")
    ax.set_xticks(np.arange(len(rhs)))
    ax.set_xticklabels([f"{x:g}" for x in rhs])
    ax.set_yticks(np.arange(len(ps)))
    ax.set_yticklabels([f"{x:g}" for x in ps])

    # 网格线
    ax.set_xticks(np.arange(len(rhs) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(ps) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.8, alpha=0.9)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(len(ps)):
        for j in range(len(rhs)):
            if not labels[i][j]:
                continue
            val = mat[i, j]
            color = "white" if np.isfinite(val) and float(norm(val)) >= 0.55 else "black"
            ax.text(j, i, labels[i][j], ha="center", va="center", fontsize=9, color=color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(value_col)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=260)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="从多个 bet-hedging run 目录生成环境相图（最优策略随环境变化）。")
    ap.add_argument(
        "--run-dirs",
        required=True,
        help="逗号分隔的 run 目录列表（每个目录需包含 runs.csv 与 config.json）。",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="输出目录（默认：MCM_Sim/24A/outputs/temp/env_phase-<ts>/）。",
    )
    ap.add_argument("--host-max", type=float, default=0.2, help="生态约束：P_host 的最大允许值。")
    ap.add_argument(
        "--objective",
        default="geom_mean_N",
        help="在约束下最大化的灯鱼指标（推荐 geom_mean_N 或 q10_min_N）。",
    )
    args = ap.parse_args()

    this_dir = Path(__file__).resolve().parents[1]  # MCM_Sim/24A
    default_out = this_dir / "outputs" / "temp" / f"env_phase-{_timestamp()}"
    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else default_out
    out_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = _parse_paths_csv(args.run_dirs)
    if not run_dirs:
        raise ValueError("--run-dirs 为空。")

    rows = []
    for rd in run_dirs:
        rd = rd.resolve()
        df = pd.read_csv(rd / "runs.csv")
        p, rh = _load_env(rd)
        best = _pick_best_strategy(df, host_max=float(args.host_max), objective=str(args.objective))

        rows.append(
            {
                "run_dir": str(rd),
                "p": float(p),
                "RH_over_RL": float(rh),
                "objective": str(args.objective),
                "host_max": float(args.host_max),
                "best_gamma": float(best["gamma"]),
                "best_w": float(best["w"]),
                "best_strategy": str(best.get("strategy", "")),
                "P_ext": float(best.get("P_ext", np.nan)),
                "P_host": float(best.get("P_host", np.nan)),
                "geom_mean_N": float(best.get("geom_mean_N", np.nan)),
                "q10_min_N": float(best.get("q10_min_N", np.nan)),
            }
        )

    phase = pd.DataFrame(rows).sort_values(["RH_over_RL", "p"])
    phase.to_csv(out_dir / "phase_table.csv", index=False)

    # 相图：颜色=best_gamma，标注=g,w
    phase = phase.assign(_label=phase.apply(lambda r: f"g={r['best_gamma']:g}\nw={r['best_w']:g}", axis=1))
    _plot_phase_heatmap(
        phase,
        value_col="best_gamma",
        label_col="_label",
        title=f"环境相图：在 P_host<= {float(args.host_max):g} 约束下最大化 {args.objective}",
        out_path=out_dir / "phase_best_gamma.png",
    )

    # 额外输出：颜色=geom_mean_N，标注同上（便于解释“为什么选它”）
    _plot_phase_heatmap(
        phase,
        value_col=str(args.objective) if str(args.objective) in phase.columns else "geom_mean_N",
        label_col="_label",
        title=f"环境相图：{args.objective}（格内标注最优 g,w）",
        out_path=out_dir / "phase_objective.png",
    )

    meta = {
        "run_dirs": [str(p) for p in run_dirs],
        "host_max": float(args.host_max),
        "objective": str(args.objective),
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir}")


if __name__ == "__main__":
    main()
