#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 命令行入口：运行 MCM 2024 A 题仿真
#
# 已实现：
# - Model-0：bet-hedging 扫描（两态马尔可夫丰歉年）、季节资源对比、常值资源局部稳定
# - Model-1/2/3：三元系统（受益第三方 B_L/B_H/二者共存）在随机环境下的全动力学仿真
# - Q4：受益者入侵阈值（常值 R0）与随机环境入侵指数 λ
#
# 输出目录（默认）：MCM_Sim/24A/outputs/temp/run-<timestamp>/
# - runs.csv：每个策略一行的汇总指标（P_ext/P_host/mean/min/CV 等）
# - env_sequences.npz：配对对照用的共同随机环境序列（states 与 R）
# - config.json：本次运行的参数快照（含参考稳态 N_ref、阈值等）

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_BASE = THIS_DIR / "outputs" / "temp"
SRC_DIR = THIS_DIR / "src"
if str(SRC_DIR) not in sys.path:
    # 允许直接 `python MCM_Sim/24A/run_sim.py ...` 运行（无需安装包）
    sys.path.insert(0, str(SRC_DIR))

from mcm24a.environment import MarkovEnv
from mcm24a.beneficiary import (
    BHParams,
    BLParams,
    R0_BH_from_equilibrium,
    R0_BL_from_equilibrium,
    invasion_exponent_BH,
    invasion_exponent_BL,
)
from mcm24a.metrics import compute_metrics, geometric_mean_timeweighted, recovery_time_from_min
from mcm24a.model0 import Model0Params
from mcm24a.model1 import Model1Params
from mcm24a.model2 import Model2Params
from mcm24a.model3 import Model3Params
from mcm24a.plotting import (
    plot_bet_hedging_triptych,
    plot_grid_heatmap,
    plot_model0_trajectories_compare,
    plot_model0_trajectories_compare_timevarying,
    plot_triad_trajectories_compare,
    plot_tradeoff_scatter,
)
from mcm24a.simulate import (
    SimConfig,
    simulate_model0_piecewise,
    simulate_model0_timevarying,
    simulate_model1_piecewise,
    simulate_model2_piecewise,
    simulate_model3_piecewise,
    steady_state_model0,
)
from mcm24a.stability import stability_model0_constant


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _parse_csv_floats(s: str) -> list[float]:
    xs: list[float] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        xs.append(float(part))
    return xs


def _build_strategies(gammas: list[float], ws: list[float]) -> list[tuple[str, float, float, float | None]]:
    """统一生成策略列表，保证各命令输出字段一致。"""
    strategies: list[tuple[str, float, float, float | None]] = []

    # 固定性别比对照组
    strategies.append(("S_56", 1.0, 0.0, 0.56))
    strategies.append(("S_78", 1.0, 0.0, 0.78))
    strategies.append(("S_50", 1.0, 0.0, 0.50))

    # 可变策略族扫描网格：S_var(gamma, w)
    for g in gammas:
        for w in ws:
            strategies.append((f"S_var_g{g}_w{w}", float(g), float(w), None))

    return strategies


def _maybe_apply_harvest(params: Model0Params, args: argparse.Namespace) -> Model0Params:
    """把 CLI 里的捕捞/门控参数写入 Model0Params（默认不启用）。"""
    if not hasattr(args, "uA_const"):
        return params
    return replace(
        params,
        u_A_const=float(getattr(args, "uA_const")),
        u_A_max=float(getattr(args, "uA_max")),
        u_A_th=float(getattr(args, "uA_th")),
        u_A_k=float(getattr(args, "uA_k")),
    )


def cmd_bet_hedging(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    params = _maybe_apply_harvest(Model0Params(), args)

    env = MarkovEnv(
        R_L=float(args.R_L),
        R_H=float(args.R_L) * float(args.RH_over_RL),
        p_LH=float(args.p),
        p_HL=float(args.p),
    )

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )

    rng = np.random.default_rng(int(args.seed))
    # 配对对照（common random numbers）：先生成一批环境序列，所有策略共用
    env_states = np.vstack([env.sample_states(cfg.years, rng=rng) for _ in range(int(args.reps))])
    env_R = np.vstack([env.states_to_R(s) for s in env_states])
    np.savez_compressed(out_dir / "env_sequences.npz", states=env_states, R=env_R)

    # 共同参考稳态：用参考策略在 R_bar（平稳平均资源）下跑到稳态，定义 N_ref 与 N_q
    ref_gamma, ref_w = 1.0, 3.0
    R_bar = env.R_bar()

    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)
    y_ref = steady_state_model0(params=params, gamma=ref_gamma, w=ref_w, R_const=R_bar, y0=y0_guess)
    N_ref = float(np.sum(y_ref[1:5]))

    q = float(args.q)
    N_q = q * N_ref

    # 宿主阈值（H 已按 K_H 归一化；默认 K_H=1）
    H_safe = float(args.H_safe)
    burn_in = int(args.burn_in)
    rec_target_frac = float(getattr(args, "rec_target_frac", 0.8))
    rec_hold_years = float(getattr(args, "rec_hold_years", 1.0))
    H_ref = float(y_ref[0])
    N_target = rec_target_frac * N_ref
    H_target = rec_target_frac * H_ref

    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    rows = []
    for name, gamma, w, p_m_override in strategies:

        hit_ext = 0
        hit_host = 0
        mean_H = []
        mean_N = []
        min_H = []
        min_N = []
        cv_H = []
        cv_N = []
        gm_H = []
        gm_N = []
        trec_N = []
        trec_H = []
        for rep in range(env_R.shape[0]):
            t, y = simulate_model0_piecewise(
                params=params,
                gamma=gamma,
                w=w,
                p_m_override=p_m_override,
                R_series=env_R[rep],
                y0=y_ref,
                config=cfg,
            )
            m = compute_metrics(t, y, H_safe=H_safe, N_q=N_q, burn_in_years=burn_in)
            hit_ext += m.hit_N_q
            hit_host += m.hit_H_safe
            mean_H.append(m.mean_H)
            mean_N.append(m.mean_N)
            min_H.append(m.min_H)
            min_N.append(m.min_N)
            cv_H.append(m.cv_H)
            cv_N.append(m.cv_N)
            # bet-hedging：几何平均水平（更接近长期“典型状态”）
            H_series = y[:, 0]
            N_series = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
            gm_H.append(geometric_mean_timeweighted(t, H_series, burn_in_years=burn_in))
            gm_N.append(geometric_mean_timeweighted(t, N_series, burn_in_years=burn_in))
            # Q3：韧性（恢复时间）——从最坏低谷恢复到目标水平所需时间
            trec_N.append(
                recovery_time_from_min(
                    t,
                    N_series,
                    target=N_target,
                    burn_in_years=burn_in,
                    hold_years=rec_hold_years,
                )
            )
            trec_H.append(
                recovery_time_from_min(
                    t,
                    H_series,
                    target=H_target,
                    burn_in_years=burn_in,
                    hold_years=rec_hold_years,
                )
            )

        def _summ_rec(ts: list[float]) -> tuple[float, float, float, float]:
            arr = np.asarray(ts, dtype=float)
            finite = arr[np.isfinite(arr)]
            p_rec = float(finite.size) / float(arr.size) if arr.size else 0.0
            if finite.size == 0:
                return p_rec, float("inf"), float("inf"), float("inf")
            return (
                p_rec,
                float(np.median(finite)),
                float(np.quantile(finite, 0.10)),
                float(np.quantile(finite, 0.90)),
            )

        P_rec_N, median_T_rec_N, q10_T_rec_N, q90_T_rec_N = _summ_rec(trec_N)
        P_rec_H, median_T_rec_H, q10_T_rec_H, q90_T_rec_H = _summ_rec(trec_H)

        # “最坏低谷”的跨 rep 分布（尾部风险）：即使 P_ext=0，也能展示差异
        minH_arr = np.asarray(min_H, dtype=float)
        minN_arr = np.asarray(min_N, dtype=float)
        q10_min_H = float(np.quantile(minH_arr, 0.10)) if minH_arr.size else float("nan")
        q50_min_H = float(np.quantile(minH_arr, 0.50)) if minH_arr.size else float("nan")
        q90_min_H = float(np.quantile(minH_arr, 0.90)) if minH_arr.size else float("nan")
        q10_min_N = float(np.quantile(minN_arr, 0.10)) if minN_arr.size else float("nan")
        q50_min_N = float(np.quantile(minN_arr, 0.50)) if minN_arr.size else float("nan")
        q90_min_N = float(np.quantile(minN_arr, 0.90)) if minN_arr.size else float("nan")

        rows.append(
            {
                "strategy": name,
                "p_m_override": p_m_override if p_m_override is not None else np.nan,
                "gamma": gamma,
                "w": w,
                "R_L": env.R_L,
                "R_H": env.R_H,
                "p": env.p_LH,
                "years": cfg.years,
                "reps": int(args.reps),
                "H_safe": H_safe,
                "q": q,
                "N_ref": N_ref,
                "N_q": N_q,
                "burn_in": burn_in,
                "rec_target_frac": rec_target_frac,
                "rec_hold_years": rec_hold_years,
                "P_ext": hit_ext / int(args.reps),
                "P_host": hit_host / int(args.reps),
                "mean_H": float(np.mean(mean_H)),
                "min_H": float(np.mean(min_H)),
                "q10_min_H": q10_min_H,
                "median_min_H": q50_min_H,
                "q90_min_H": q90_min_H,
                "cv_H": float(np.mean(cv_H)),
                "geom_mean_H": float(np.mean(gm_H)) if gm_H else float("nan"),
                "mean_N": float(np.mean(mean_N)),
                "min_N": float(np.mean(min_N)),
                "q10_min_N": q10_min_N,
                "median_min_N": q50_min_N,
                "q90_min_N": q90_min_N,
                "cv_N": float(np.mean(cv_N)),
                "geom_mean_N": float(np.mean(gm_N)) if gm_N else float("nan"),
                "P_rec_N": P_rec_N,
                "median_T_rec_N": median_T_rec_N,
                "q10_T_rec_N": q10_T_rec_N,
                "q90_T_rec_N": q90_T_rec_N,
                "P_rec_H": P_rec_H,
                "median_T_rec_H": median_T_rec_H,
                "q10_T_rec_H": q10_T_rec_H,
                "q90_T_rec_H": q90_T_rec_H,
            }
        )

    df = pd.DataFrame(rows).sort_values(["P_ext", "P_host", "strategy"])
    df.to_csv(out_dir / "runs.csv", index=False)

    # 生成论文图（最小版本）：P_ext / P_host / mean_H 的 gamma×w 热图
    fig_dir = out_dir / "figures"
    subtitle = (
        f"R_H/R_L={env.R_H/env.R_L:.2g}, p={env.p_LH:.2g}, years={cfg.years}, reps={int(args.reps)}, "
        f"H_safe={H_safe}, q={q}"
    )
    plot_bet_hedging_triptych(
        df,
        gammas=gammas,
        ws=ws,
        out_path=fig_dir / "bet_hedging_triptych.png",
        subtitle=subtitle,
        annotate=True,
    )

    # 风险权衡散点图（论文更直观：直接展示帕累托前沿）
    plot_tradeoff_scatter(
        df,
        out_path=fig_dir / "pareto_tradeoff.png",
        x_col="P_host",
        y_col="P_ext",
        title="策略风险权衡：P_host vs P_ext（越靠左下越好）",
        annotate_top_k=6,
    )

    # Q3 补图：恢复概率与恢复时间热图（当 P_ext 全为 0 时，这两张更有信息量）
    df_plot = df.copy()
    for col in ["median_T_rec_N", "q10_T_rec_N", "q90_T_rec_N", "median_T_rec_H", "q10_T_rec_H", "q90_T_rec_H"]:
        if col in df_plot.columns:
            df_plot[col] = df_plot[col].replace([np.inf, -np.inf], float(cfg.years))
    if df_plot["p_m_override"].isna().any():
        plot_grid_heatmap(
            df_plot,
            value_col="P_rec_N",
            gammas=gammas,
            ws=ws,
            title="恢复成功率 P_rec_N（从最坏低谷回升到 target）",
            out_path=fig_dir / "P_rec_N.png",
            vmin=0.0,
            vmax=1.0,
            cmap="viridis",
            annotate=True,
        )
        plot_grid_heatmap(
            df_plot,
            value_col="median_T_rec_N",
            gammas=gammas,
            ws=ws,
            title=f"恢复时间 median_T_rec_N（inf 记为 {cfg.years} 年）",
            out_path=fig_dir / "median_T_rec_N.png",
            vmin=0.0,
            vmax=float(cfg.years),
            cmap="magma",
            annotate=True,
            fmt="{:.1f}",
        )

        # 尾部风险：跨 rep 的 “最坏低谷” 10% 分位数（用 N_q 做中心更直观）
        if "q10_min_N" in df_plot.columns:
            plot_grid_heatmap(
                df_plot,
                value_col="q10_min_N",
                gammas=gammas,
                ws=ws,
                title="尾部风险：q10_min_N（最坏低谷的 10% 分位数，越大越安全）",
                out_path=fig_dir / "q10_min_N.png",
                cmap="coolwarm",
                center=float(N_q),
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[float(N_q)],
            )

        if "q10_min_H" in df_plot.columns:
            plot_grid_heatmap(
                df_plot,
                value_col="q10_min_H",
                gammas=gammas,
                ws=ws,
                title="尾部风险：q10_min_H（宿主最低谷 10% 分位数，越大越安全）",
                out_path=fig_dir / "q10_min_H.png",
                cmap="coolwarm",
                center=float(H_safe),
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[float(H_safe)],
            )

        if "geom_mean_N" in df_plot.columns:
            plot_grid_heatmap(
                df_plot,
                value_col="geom_mean_N",
                gammas=gammas,
                ws=ws,
                title="几何平均：geom_mean_N（burn-in 后）",
                out_path=fig_dir / "geom_mean_N.png",
                robust=True,
                annotate=True,
                fmt="{:.2f}",
            )

        if "geom_mean_H" in df_plot.columns:
            plot_grid_heatmap(
                df_plot,
                value_col="geom_mean_H",
                gammas=gammas,
                ws=ws,
                title="几何平均：geom_mean_H（burn-in 后）",
                out_path=fig_dir / "geom_mean_H.png",
                robust=True,
                annotate=True,
                fmt="{:.2f}",
            )

    # 代表性轨迹图：挑一条“最坏年份连发最长”的环境序列，比较若干策略的动态差异
    def longest_low_run(states_1d: np.ndarray) -> int:
        best = 0
        cur = 0
        for s in states_1d.astype(int).tolist():
            if s == 0:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return int(best)

    low_runs = np.array([longest_low_run(env_states[i]) for i in range(env_states.shape[0])], dtype=int)
    rep_worst = int(np.argmax(low_runs))
    worst_len = int(low_runs[rep_worst])

    # 选 2 个 S_var（最好/最差）+ 2 个固定对照
    var = df[df["p_m_override"].isna()].copy()
    if not var.empty:
        var["_score"] = var["P_ext"].astype(float) + var["P_host"].astype(float)
        best_row = var.sort_values(["_score", "P_ext", "P_host"]).iloc[0]
        worst_row = var.sort_values(["_score", "P_ext", "P_host"], ascending=[False, False, False]).iloc[0]
        picked = [
            ("最优S_var", float(best_row["gamma"]), float(best_row["w"]), None),
            ("最差S_var", float(worst_row["gamma"]), float(worst_row["w"]), None),
            ("S_56", 1.0, 0.0, 0.56),
            ("S_78", 1.0, 0.0, 0.78),
        ]
    else:
        picked = [("S_56", 1.0, 0.0, 0.56), ("S_78", 1.0, 0.0, 0.78), ("S_50", 1.0, 0.0, 0.50)]

    ys = {}
    gamma_w_pm = {}
    t_ref = None
    for label, g, ww, pm in picked:
        t_i, y_i = simulate_model0_piecewise(
            params=params,
            gamma=float(g),
            w=float(ww),
            p_m_override=pm,
            R_series=env_R[rep_worst],
            y0=y_ref,
            config=cfg,
        )
        if t_ref is None:
            t_ref = t_i
        ys[label] = y_i
        gamma_w_pm[label] = (float(g), float(ww), pm)

    if t_ref is not None:
        title2 = (
            f"代表性环境序列对比（最坏连续歉年={worst_len}）\n"
            f"R_H/R_L={env.R_H/env.R_L:.2g}, p={env.p_LH:.2g}, years={cfg.years}, rep={rep_worst}"
        )
        plot_model0_trajectories_compare(
            t_ref,
            ys,
            R_series=env_R[rep_worst],
            gamma_w_pm=gamma_w_pm,
            out_path=fig_dir / "trajectories_compare.png",
            title=title2,
        )

    meta = {
        "model": "Model-0",
        "params": asdict(params),
        "env": asdict(env),
        "sim": asdict(cfg),
        "reference_strategy": {"gamma": ref_gamma, "w": ref_w, "R_bar": R_bar, "y_ref": y_ref.tolist()},
        "thresholds": {"H_safe": H_safe, "q": q, "N_ref": N_ref, "N_q": N_q},
        "grid": {"gammas": gammas, "ws": ws},
        "seed": int(args.seed),
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"已输出：{out_dir / 'runs.csv'}")


def cmd_seasonal(args: argparse.Namespace) -> None:
    """季节资源：R(t)=R0*(1 + A*sin(2πt/T)) 下比较策略（Model-0）。"""
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    params = _maybe_apply_harvest(Model0Params(), args)

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )

    R0 = float(args.R0)
    A = float(args.A)
    T = float(args.T)

    def R_of_t(t: float) -> float:
        return max(0.0, R0 * (1.0 + A * float(np.sin(2.0 * np.pi * t / T))))

    # 共同参考稳态（用平均资源 R0）
    ref_gamma, ref_w = 1.0, 3.0
    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)
    y_ref = steady_state_model0(params=params, gamma=ref_gamma, w=ref_w, R_const=R0, y0=y0_guess)
    N_ref = float(np.sum(y_ref[1:5]))

    q = float(args.q)
    N_q = q * N_ref
    H_safe = float(args.H_safe)
    burn_in = int(args.burn_in)
    rec_target_frac = float(getattr(args, "rec_target_frac", 0.8))
    rec_hold_years = float(getattr(args, "rec_hold_years", 1.0))
    H_ref = float(y_ref[0])
    N_target = rec_target_frac * N_ref
    H_target = rec_target_frac * H_ref

    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    rows = []
    trajectories = {}
    gamma_w_pm = {}
    t_ref = None
    for name, gamma, w, p_m_override in strategies:
        t, y = simulate_model0_timevarying(
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
            R_of_t=R_of_t,
            y0=y_ref,
            config=cfg,
        )
        m = compute_metrics(t, y, H_safe=H_safe, N_q=N_q, burn_in_years=int(args.burn_in))
        H_series = y[:, 0]
        N_series = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
        T_rec_N = recovery_time_from_min(
            t,
            N_series,
            target=N_target,
            burn_in_years=burn_in,
            hold_years=rec_hold_years,
        )
        T_rec_H = recovery_time_from_min(
            t,
            H_series,
            target=H_target,
            burn_in_years=burn_in,
            hold_years=rec_hold_years,
        )

        rows.append(
            {
                "strategy": name,
                "p_m_override": p_m_override if p_m_override is not None else np.nan,
                "gamma": gamma,
                "w": w,
                "env_type": "seasonal",
                "R0": R0,
                "A": A,
                "T": T,
                "years": cfg.years,
                "H_safe": H_safe,
                "q": q,
                "N_ref": N_ref,
                "N_q": N_q,
                "burn_in": burn_in,
                "rec_target_frac": rec_target_frac,
                "rec_hold_years": rec_hold_years,
                "hit_ext": int(m.hit_N_q),
                "hit_host": int(m.hit_H_safe),
                "mean_H": m.mean_H,
                "min_H": m.min_H,
                "cv_H": m.cv_H,
                "mean_N": m.mean_N,
                "min_N": m.min_N,
                "cv_N": m.cv_N,
                "T_rec_N": float(T_rec_N),
                "T_rec_H": float(T_rec_H),
            }
        )

        # 保存少量代表性轨迹：只保存固定对照 + S_var 中 gamma 最大/最小、w 最大/最小的组合
        keep = name in {"S_56", "S_78", "S_50"}
        keep = keep or (p_m_override is None and (gamma in {min(gammas), max(gammas)} and w in {min(ws), max(ws)}))
        if keep:
            trajectories[name] = y
            gamma_w_pm[name] = (gamma, w, p_m_override)
            if t_ref is None:
                t_ref = t

    df = pd.DataFrame(rows).sort_values(["hit_ext", "hit_host", "strategy"])
    df.to_csv(out_dir / "runs.csv", index=False)

    # 轨迹图（论文图）：R/H/N/p_m
    if t_ref is not None and trajectories:
        R_t = np.array([R_of_t(float(tt)) for tt in t_ref], dtype=float)
        title = f"季节资源对比：R0={R0}, A={A}, T={T}年，years={cfg.years}"
        plot_model0_trajectories_compare_timevarying(
            t_ref,
            trajectories,
            R_t=R_t,
            gamma_w_pm=gamma_w_pm,
            out_path=(out_dir / "figures" / "seasonal_trajectories.png"),
            title=title,
        )

    meta = {
        "task": "seasonal_model0",
        "params": asdict(params),
        "sim": asdict(cfg),
        "env": {"type": "seasonal", "R0": R0, "A": A, "T": T},
        "reference_strategy": {"gamma": ref_gamma, "w": ref_w, "y_ref": y_ref.tolist()},
        "thresholds": {"H_safe": H_safe, "q": q, "N_ref": N_ref, "N_q": N_q},
        "grid": {"gammas": gammas, "ws": ws},
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir / 'runs.csv'}")


def cmd_stability(args: argparse.Namespace) -> None:
    """常值资源下：输出平衡点 + Jacobian 特征值摘要（Model-0）。"""
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    params = _maybe_apply_harvest(Model0Params(), args)

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )
    R0 = float(args.R0)
    eps = float(args.eps)

    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)

    rows = []
    for name, gamma, w, p_m_override in strategies:
        y_star = steady_state_model0(
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
            R_const=R0,
            y0=y0_guess,
            years=cfg.years,
            config=cfg,
        )
        _, summ = stability_model0_constant(
            y_star[:6],
            R=R0,
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
            eps=eps,
        )

        rows.append(
            {
                "strategy": name,
                "p_m_override": p_m_override if p_m_override is not None else np.nan,
                "gamma": gamma,
                "w": w,
                "env_type": "constant",
                "R0": R0,
                "years": cfg.years,
                "H_star": float(y_star[0]),
                "N_star": float(np.sum(y_star[1:5])),
                "max_real": summ.max_real,
                "stable": summ.stable,
                "return_time": summ.return_time,
                "dominant_period": summ.dominant_period,
            }
        )

    df = pd.DataFrame(rows).sort_values(["stable", "max_real", "strategy"], ascending=[False, True, True])
    df.to_csv(out_dir / "runs.csv", index=False)

    # 可变策略热图：max_real（以 0 为中心）与 return_time（对数尺度更直观，这里先用线性）
    fig_dir = out_dir / "figures"
    if df["p_m_override"].isna().any():
        plot_grid_heatmap(
            df,
            value_col="max_real",
            gammas=gammas,
            ws=ws,
            title="局部稳定性：max_real（<0 稳定）",
            out_path=fig_dir / "max_real.png",
            cmap="coolwarm",
            center=0.0,
            robust=True,
            annotate=True,
            fmt="{:.3f}",
            contour_levels=[0.0],
        )

    meta = {
        "task": "stability_model0_constant",
        "params": asdict(params),
        "sim": asdict(cfg),
        "env": {"type": "constant", "R0": R0},
        "grid": {"gammas": gammas, "ws": ws},
        "eps": eps,
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir / 'runs.csv'}")


def cmd_triad_markov(args: argparse.Namespace) -> None:
    """三元系统全动力学：在随机环境下直接仿真 Model-1/2/3（含 B）。"""
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    base = _maybe_apply_harvest(Model0Params(), args)
    bl_params = BLParams()
    bh_params = BHParams()

    model_id = int(args.model)
    if model_id not in {1, 2, 3}:
        raise ValueError("--model 必须是 1/2/3")

    if model_id == 1:
        triad_params = Model1Params(base=base, bl=bl_params)
        sim_fn = simulate_model1_piecewise
        B_cols = [6]
    elif model_id == 2:
        triad_params = Model2Params(base=base, bh=bh_params)
        sim_fn = simulate_model2_piecewise
        B_cols = [6]
    else:
        triad_params = Model3Params(base=base, bl=bl_params, bh=bh_params)
        sim_fn = simulate_model3_piecewise
        B_cols = [6, 7]

    env = MarkovEnv(
        R_L=float(args.R_L),
        R_H=float(args.R_L) * float(args.RH_over_RL),
        p_LH=float(args.p),
        p_HL=float(args.p),
    )

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )

    rng = np.random.default_rng(int(args.seed))
    env_states = np.vstack([env.sample_states(cfg.years, rng=rng) for _ in range(int(args.reps))])
    env_R = np.vstack([env.states_to_R(s) for s in env_states])
    np.savez_compressed(out_dir / "env_sequences.npz", states=env_states, R=env_R)

    # 共同参考稳态：用 Model-0 在 R_bar 下的稳态作为初值（再叠加 B 的稀有入侵）
    ref_gamma, ref_w = 1.0, 3.0
    R_bar = env.R_bar()
    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)
    y_ref = steady_state_model0(params=base, gamma=ref_gamma, w=ref_w, R_const=R_bar, y0=y0_guess)
    N_ref = float(np.sum(y_ref[1:5]))

    q = float(args.q)
    N_q = q * N_ref
    H_safe = float(args.H_safe)
    burn_in = int(args.burn_in)
    rec_target_frac = float(getattr(args, "rec_target_frac", 0.8))
    rec_hold_years = float(getattr(args, "rec_hold_years", 1.0))
    H_ref = float(y_ref[0])
    N_target = rec_target_frac * N_ref
    H_target = rec_target_frac * H_ref

    B_init = float(args.B_init)
    B_th = float(args.B_th)
    # 爆发阈值：用于 max_B 指标（若未显式给出，则沿用 B_th）
    B_out_th_raw = getattr(args, "B_out_th", None)
    B_out_th = float(B_th if B_out_th_raw is None else B_out_th_raw)

    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    rows = []
    for name, gamma, w, p_m_override in strategies:
        hit_ext = 0
        hit_host = 0

        mean_H = []
        mean_N = []
        min_H = []
        min_N = []
        cv_H = []
        cv_N = []
        gm_H = []
        gm_N = []
        trec_N = []
        trec_H = []

        # B 指标
        mean_B1 = []
        max_B1 = []
        persist_B1 = 0
        outbreak_B1 = 0
        mean_B2 = []
        max_B2 = []
        persist_B2 = 0
        outbreak_B2 = 0

        for rep in range(env_R.shape[0]):
            if model_id == 1:
                y0 = np.concatenate([y_ref, np.array([B_init], dtype=float)])
            elif model_id == 2:
                y0 = np.concatenate([y_ref, np.array([B_init], dtype=float)])
            else:
                y0 = np.concatenate([y_ref, np.array([B_init, B_init], dtype=float)])

            t, y = sim_fn(
                params=triad_params,
                gamma=gamma,
                w=w,
                p_m_override=p_m_override,
                R_series=env_R[rep],
                y0=y0,
                config=cfg,
            )

            m = compute_metrics(t, y, H_safe=H_safe, N_q=N_q, burn_in_years=burn_in)
            hit_ext += m.hit_N_q
            hit_host += m.hit_H_safe
            mean_H.append(m.mean_H)
            mean_N.append(m.mean_N)
            min_H.append(m.min_H)
            min_N.append(m.min_N)
            cv_H.append(m.cv_H)
            cv_N.append(m.cv_N)

            H_series = y[:, 0]
            N_series = y[:, 1] + y[:, 2] + y[:, 3] + y[:, 4]
            gm_H.append(geometric_mean_timeweighted(t, H_series, burn_in_years=burn_in))
            gm_N.append(geometric_mean_timeweighted(t, N_series, burn_in_years=burn_in))
            trec_N.append(
                recovery_time_from_min(
                    t,
                    N_series,
                    target=N_target,
                    burn_in_years=burn_in,
                    hold_years=rec_hold_years,
                )
            )
            trec_H.append(
                recovery_time_from_min(
                    t,
                    H_series,
                    target=H_target,
                    burn_in_years=burn_in,
                    hold_years=rec_hold_years,
                )
            )

            mask = t >= float(burn_in)
            if not np.any(mask):
                mask = slice(None)

            B1 = y[:, B_cols[0]]
            B1_stat = B1[mask]
            mean_b1 = float(np.mean(B1_stat))
            mean_B1.append(mean_b1)
            max_B1.append(float(np.max(B1_stat)))
            persist_B1 += int(mean_b1 > B_th)
            outbreak_B1 += int(float(np.max(B1_stat)) > B_out_th)

            if len(B_cols) == 2:
                B2 = y[:, B_cols[1]]
                B2_stat = B2[mask]
                mean_b2 = float(np.mean(B2_stat))
                mean_B2.append(mean_b2)
                max_B2.append(float(np.max(B2_stat)))
                persist_B2 += int(mean_b2 > B_th)
                outbreak_B2 += int(float(np.max(B2_stat)) > B_out_th)

        def _summ_rec(ts: list[float]) -> tuple[float, float, float, float]:
            arr = np.asarray(ts, dtype=float)
            finite = arr[np.isfinite(arr)]
            p_rec = float(finite.size) / float(arr.size) if arr.size else 0.0
            if finite.size == 0:
                return p_rec, float("inf"), float("inf"), float("inf")
            return (
                p_rec,
                float(np.median(finite)),
                float(np.quantile(finite, 0.10)),
                float(np.quantile(finite, 0.90)),
            )

        P_rec_N, median_T_rec_N, q10_T_rec_N, q90_T_rec_N = _summ_rec(trec_N)
        P_rec_H, median_T_rec_H, q10_T_rec_H, q90_T_rec_H = _summ_rec(trec_H)

        minH_arr = np.asarray(min_H, dtype=float)
        minN_arr = np.asarray(min_N, dtype=float)
        q10_min_H = float(np.quantile(minH_arr, 0.10)) if minH_arr.size else float("nan")
        q50_min_H = float(np.quantile(minH_arr, 0.50)) if minH_arr.size else float("nan")
        q90_min_H = float(np.quantile(minH_arr, 0.90)) if minH_arr.size else float("nan")
        q10_min_N = float(np.quantile(minN_arr, 0.10)) if minN_arr.size else float("nan")
        q50_min_N = float(np.quantile(minN_arr, 0.50)) if minN_arr.size else float("nan")
        q90_min_N = float(np.quantile(minN_arr, 0.90)) if minN_arr.size else float("nan")

        row = {
            "model": model_id,
            "strategy": name,
            "p_m_override": p_m_override if p_m_override is not None else np.nan,
            "gamma": gamma,
            "w": w,
            "R_L": env.R_L,
            "R_H": env.R_H,
            "p": env.p_LH,
            "years": cfg.years,
            "reps": int(args.reps),
            "H_safe": H_safe,
            "q": q,
            "N_ref": N_ref,
            "N_q": N_q,
            "burn_in": burn_in,
            "rec_target_frac": rec_target_frac,
            "rec_hold_years": rec_hold_years,
            "B_init": B_init,
            "B_th": B_th,
            "B_out_th": B_out_th,
            "P_ext": hit_ext / int(args.reps),
            "P_host": hit_host / int(args.reps),
            "mean_H": float(np.mean(mean_H)),
            "min_H": float(np.mean(min_H)),
            "q10_min_H": q10_min_H,
            "median_min_H": q50_min_H,
            "q90_min_H": q90_min_H,
            "cv_H": float(np.mean(cv_H)),
            "geom_mean_H": float(np.mean(gm_H)) if gm_H else float("nan"),
            "mean_N": float(np.mean(mean_N)),
            "min_N": float(np.mean(min_N)),
            "q10_min_N": q10_min_N,
            "median_min_N": q50_min_N,
            "q90_min_N": q90_min_N,
            "cv_N": float(np.mean(cv_N)),
            "geom_mean_N": float(np.mean(gm_N)) if gm_N else float("nan"),
            "P_rec_N": P_rec_N,
            "median_T_rec_N": median_T_rec_N,
            "q10_T_rec_N": q10_T_rec_N,
            "q90_T_rec_N": q90_T_rec_N,
            "P_rec_H": P_rec_H,
            "median_T_rec_H": median_T_rec_H,
            "q10_T_rec_H": q10_T_rec_H,
            "q90_T_rec_H": q90_T_rec_H,
            "mean_B1": float(np.mean(mean_B1)),
            "max_B1": float(np.mean(max_B1)),
            "P_B1_persist": persist_B1 / int(args.reps),
            "P_B1_outbreak": outbreak_B1 / int(args.reps),
        }
        if model_id == 3:
            row.update(
                {
                    "mean_B2": float(np.mean(mean_B2)) if mean_B2 else float("nan"),
                    "max_B2": float(np.mean(max_B2)) if max_B2 else float("nan"),
                    "P_B2_persist": persist_B2 / int(args.reps),
                    "P_B2_outbreak": outbreak_B2 / int(args.reps),
                }
            )
        rows.append(row)

    df = pd.DataFrame(rows).sort_values(["P_ext", "P_host", "strategy"])
    df.to_csv(out_dir / "runs.csv", index=False)

    fig_dir = out_dir / "figures"
    if df["p_m_override"].isna().any():
        # 先输出“第三方”相关图
        plot_grid_heatmap(
            df,
            value_col="P_B1_persist",
            gammas=gammas,
            ws=ws,
            title="B1 持续概率（mean_B1 > 阈值）",
            out_path=fig_dir / "P_B1_persist.png",
            vmin=0.0,
            vmax=1.0,
            cmap="viridis",
            annotate=True,
        )
        if "P_B1_outbreak" in df.columns:
            plot_grid_heatmap(
                df,
                value_col="P_B1_outbreak",
                gammas=gammas,
                ws=ws,
                title="B1 爆发概率（max_B1 > 阈值）",
                out_path=fig_dir / "P_B1_outbreak.png",
                vmin=0.0,
                vmax=1.0,
                cmap="viridis",
                annotate=True,
            )
        plot_grid_heatmap(
            df,
            value_col="mean_B1",
            gammas=gammas,
            ws=ws,
            title="mean_B1（burn-in 后）",
            out_path=fig_dir / "mean_B1.png",
            robust=True,
            annotate=True,
        )
        if model_id == 3:
            plot_grid_heatmap(
                df,
                value_col="P_B2_persist",
                gammas=gammas,
                ws=ws,
                title="B2 持续概率（mean_B2 > 阈值）",
                out_path=fig_dir / "P_B2_persist.png",
                vmin=0.0,
                vmax=1.0,
                cmap="viridis",
                annotate=True,
            )
            if "P_B2_outbreak" in df.columns:
                plot_grid_heatmap(
                    df,
                    value_col="P_B2_outbreak",
                    gammas=gammas,
                    ws=ws,
                    title="B2 爆发概率（max_B2 > 阈值）",
                    out_path=fig_dir / "P_B2_outbreak.png",
                    vmin=0.0,
                    vmax=1.0,
                    cmap="viridis",
                    annotate=True,
                )
            plot_grid_heatmap(
                df,
                value_col="mean_B2",
                gammas=gammas,
                ws=ws,
                title="mean_B2（burn-in 后）",
                out_path=fig_dir / "mean_B2.png",
                robust=True,
                annotate=True,
            )

        # 再输出一些对 bet-hedging 也有价值的尾部/几何平均指标（避免全 0/全 1）
        if "q10_min_N" in df.columns:
            plot_grid_heatmap(
                df,
                value_col="q10_min_N",
                gammas=gammas,
                ws=ws,
                title="尾部风险：q10_min_N（最坏低谷 10% 分位数）",
                out_path=fig_dir / "q10_min_N.png",
                cmap="coolwarm",
                center=float(N_q),
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[float(N_q)],
            )

        if "q10_min_H" in df.columns:
            plot_grid_heatmap(
                df,
                value_col="q10_min_H",
                gammas=gammas,
                ws=ws,
                title="尾部风险：q10_min_H（宿主最低谷 10% 分位数）",
                out_path=fig_dir / "q10_min_H.png",
                cmap="coolwarm",
                center=float(H_safe),
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[float(H_safe)],
            )

        if "geom_mean_N" in df.columns:
            plot_grid_heatmap(
                df,
                value_col="geom_mean_N",
                gammas=gammas,
                ws=ws,
                title="几何平均：geom_mean_N（burn-in 后）",
                out_path=fig_dir / "geom_mean_N.png",
                robust=True,
                annotate=True,
                fmt="{:.2f}",
            )

        if "geom_mean_H" in df.columns:
            plot_grid_heatmap(
                df,
                value_col="geom_mean_H",
                gammas=gammas,
                ws=ws,
                title="几何平均：geom_mean_H（burn-in 后）",
                out_path=fig_dir / "geom_mean_H.png",
                robust=True,
                annotate=True,
                fmt="{:.2f}",
            )

    # 代表性轨迹：挑一条“最坏连续歉年最长”的环境序列，展示 B 的涌现
    def longest_low_run(states_1d: np.ndarray) -> int:
        best = 0
        cur = 0
        for s in states_1d.astype(int).tolist():
            if s == 0:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return int(best)

    low_runs = np.array([longest_low_run(env_states[i]) for i in range(env_states.shape[0])], dtype=int)
    rep_worst = int(np.argmax(low_runs))
    worst_len = int(low_runs[rep_worst])

    var = df[df["p_m_override"].isna()].copy()
    picked = []
    if not var.empty:
        # “对 B 最有利”的策略（mean_B1 最大）
        bestB = var.sort_values(["mean_B1", "P_B1_persist"], ascending=[False, False]).iloc[0]
        worstB = var.sort_values(["mean_B1", "P_B1_persist"], ascending=[True, True]).iloc[0]
        picked = [
            ("最利B_S_var", float(bestB["gamma"]), float(bestB["w"]), None),
            ("最不利B_S_var", float(worstB["gamma"]), float(worstB["w"]), None),
            ("S_56", 1.0, 0.0, 0.56),
            ("S_78", 1.0, 0.0, 0.78),
        ]
    else:
        picked = [("S_56", 1.0, 0.0, 0.56), ("S_78", 1.0, 0.0, 0.78)]

    ys = {}
    gamma_w_pm = {}
    t_ref = None
    for label, g, ww, pm in picked:
        if model_id == 1:
            y0 = np.concatenate([y_ref, np.array([B_init], dtype=float)])
        elif model_id == 2:
            y0 = np.concatenate([y_ref, np.array([B_init], dtype=float)])
        else:
            y0 = np.concatenate([y_ref, np.array([B_init, B_init], dtype=float)])

        t_i, y_i = sim_fn(
            params=triad_params,
            gamma=float(g),
            w=float(ww),
            p_m_override=pm,
            R_series=env_R[rep_worst],
            y0=y0,
            config=cfg,
        )
        if t_ref is None:
            t_ref = t_i
        ys[label] = y_i
        gamma_w_pm[label] = (float(g), float(ww), pm)

    if t_ref is not None:
        title2 = (
            f"三元系统代表性环境（最坏连续歉年={worst_len}）\n"
            f"model={model_id}, R_H/R_L={env.R_H/env.R_L:.2g}, p={env.p_LH:.2g}, years={cfg.years}, rep={rep_worst}"
        )
        plot_triad_trajectories_compare(
            t_ref,
            ys,
            R_series=env_R[rep_worst],
            gamma_w_pm=gamma_w_pm,
            out_path=fig_dir / "trajectories_triad.png",
            title=title2,
        )

    meta = {
        "task": "triad_markov_full_dynamics",
        "model": model_id,
        "base_params": asdict(base),
        "BL_params": asdict(bl_params),
        "BH_params": asdict(bh_params),
        "env": asdict(env),
        "sim": asdict(cfg),
        "reference_strategy": {"gamma": ref_gamma, "w": ref_w, "R_bar": R_bar, "y_ref": y_ref.tolist()},
        "thresholds": {"H_safe": H_safe, "q": q, "N_ref": N_ref, "N_q": N_q, "B_th": B_th},
        "grid": {"gammas": gammas, "ws": ws},
        "seed": int(args.seed),
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir / 'runs.csv'}")


def cmd_q4_constant(args: argparse.Namespace) -> None:
    """Q4：常值资源下的入侵阈值（R0 口径）。"""
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    params = _maybe_apply_harvest(Model0Params(), args)
    bl_params = BLParams()
    bh_params = BHParams()

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )

    R0 = float(args.R0)
    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)

    rows = []
    for name, gamma, w, p_m_override in strategies:
        y_star = steady_state_model0(
            params=params,
            gamma=gamma,
            w=w,
            p_m_override=p_m_override,
            R_const=R0,
            y0=y0_guess,
            years=cfg.years,
            config=cfg,
        )
        H_star = float(y_star[0])
        J_star = float(y_star[2])
        N_star = float(np.sum(y_star[1:5]))

        R0_BL = R0_BL_from_equilibrium(J_star, params=bl_params)
        R0_BH = R0_BH_from_equilibrium(H_star, J_star, params=bh_params)

        rows.append(
            {
                "strategy": name,
                "p_m_override": p_m_override if p_m_override is not None else np.nan,
                "gamma": gamma,
                "w": w,
                "env_type": "constant",
                "R0": R0,
                "years": cfg.years,
                "R0_BL": R0_BL,
                "R0_BH": R0_BH,
                "invade_BL": int(R0_BL > 1.0),
                "invade_BH": int(R0_BH > 1.0),
                "H_star": H_star,
                "J_star": J_star,
                "N_star": N_star,
            }
        )

    df = pd.DataFrame(rows).sort_values(["invade_BL", "invade_BH", "strategy"], ascending=[False, False, True])
    df.to_csv(out_dir / "runs.csv", index=False)

    # 可变策略热图：R0_BL 与 R0_BH
    fig_dir = out_dir / "figures"
    sub = df[df["p_m_override"].isna()].copy()
    if not sub.empty:
        for col in ["R0_BL", "R0_BH"]:
            vmax = float(np.nanmax(sub[col].to_numpy(dtype=float)))
            vmax = max(vmax, 1.0)
            plot_grid_heatmap(
                df,
                value_col=col,
                gammas=gammas,
                ws=ws,
                title=f"{col}（>1 可入侵）",
                out_path=fig_dir / f"{col}.png",
                vmin=0.0,
                vmax=vmax,
                cmap="coolwarm",
                center=1.0,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[1.0],
            )

    meta = {
        "task": "Q4_constant_threshold",
        "model": "Model-0（B 仅用于入侵阈值计算）",
        "params": asdict(params),
        "BL_params": asdict(bl_params),
        "BH_params": asdict(bh_params),
        "env": {"type": "constant", "R0": R0},
        "sim": asdict(cfg),
        "grid": {"gammas": gammas, "ws": ws},
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir / 'runs.csv'}")


def cmd_q4_markov(args: argparse.Namespace) -> None:
    """Q4：随机环境下的入侵指数（λ 口径，bet-hedging 扩展）。"""
    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / f"run-{_timestamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)

    params = _maybe_apply_harvest(Model0Params(), args)
    bl_params = BLParams()
    bh_params = BHParams()

    env = MarkovEnv(
        R_L=float(args.R_L),
        R_H=float(args.R_L) * float(args.RH_over_RL),
        p_LH=float(args.p),
        p_HL=float(args.p),
    )

    cfg = SimConfig(
        years=int(args.years),
        steps_per_year=int(args.steps_per_year),
        solver_method=args.solver,
        rtol=float(args.rtol),
        atol=float(args.atol),
    )

    rng = np.random.default_rng(int(args.seed))
    env_states = np.vstack([env.sample_states(cfg.years, rng=rng) for _ in range(int(args.reps))])
    env_R = np.vstack([env.states_to_R(s) for s in env_states])
    np.savez_compressed(out_dir / "env_sequences.npz", states=env_states, R=env_R)

    # 共同参考稳态：与 bet-hedging 命令保持一致
    ref_gamma, ref_w = 1.0, 3.0
    R_bar = env.R_bar()
    y0_guess = np.array([1.0, 0.3, 0.1, 0.05, 0.05, 0.5], dtype=float)
    y_ref = steady_state_model0(params=params, gamma=ref_gamma, w=ref_w, R_const=R_bar, y0=y0_guess)
    N_ref = float(np.sum(y_ref[1:5]))

    q = float(args.q)
    N_q = q * N_ref
    H_safe = float(args.H_safe)

    gammas = _parse_csv_floats(args.gammas)
    ws = _parse_csv_floats(args.ws)
    strategies = _build_strategies(gammas, ws)

    rows = []
    burn_in = int(args.burn_in)

    for name, gamma, w, p_m_override in strategies:
        hit_ext = 0
        hit_host = 0
        mean_H = []
        mean_N = []
        min_H = []
        min_N = []
        cv_H = []
        cv_N = []

        lamb_bl = []
        lamb_bh = []

        for rep in range(env_R.shape[0]):
            t, y = simulate_model0_piecewise(
                params=params,
                gamma=gamma,
                w=w,
                p_m_override=p_m_override,
                R_series=env_R[rep],
                y0=y_ref,
                config=cfg,
            )

            m = compute_metrics(t, y, H_safe=H_safe, N_q=N_q, burn_in_years=burn_in)
            hit_ext += m.hit_N_q
            hit_host += m.hit_H_safe
            mean_H.append(m.mean_H)
            mean_N.append(m.mean_N)
            min_H.append(m.min_H)
            min_N.append(m.min_N)
            cv_H.append(m.cv_H)
            cv_N.append(m.cv_N)

            lamb_bl.append(invasion_exponent_BL(t, y, params=bl_params, burn_in_years=burn_in))
            lamb_bh.append(invasion_exponent_BH(t, y, params=bh_params, burn_in_years=burn_in))

        lamb_bl_arr = np.asarray(lamb_bl, dtype=float)
        lamb_bh_arr = np.asarray(lamb_bh, dtype=float)

        rows.append(
            {
                "strategy": name,
                "p_m_override": p_m_override if p_m_override is not None else np.nan,
                "gamma": gamma,
                "w": w,
                "env_type": "markov",
                "R_L": env.R_L,
                "R_H": env.R_H,
                "p": env.p_LH,
                "years": cfg.years,
                "reps": int(args.reps),
                "H_safe": H_safe,
                "q": q,
                "N_ref": N_ref,
                "N_q": N_q,
                "P_ext": hit_ext / int(args.reps),
                "P_host": hit_host / int(args.reps),
                "mean_H": float(np.mean(mean_H)),
                "min_H": float(np.mean(min_H)),
                "cv_H": float(np.mean(cv_H)),
                "mean_N": float(np.mean(mean_N)),
                "min_N": float(np.mean(min_N)),
                "cv_N": float(np.mean(cv_N)),
                "lambda_BL": float(np.mean(lamb_bl_arr)),
                "P_lambda_BL_pos": float(np.mean(lamb_bl_arr > 0.0)),
                "lambda_BH": float(np.mean(lamb_bh_arr)),
                "P_lambda_BH_pos": float(np.mean(lamb_bh_arr > 0.0)),
            }
        )

    df = pd.DataFrame(rows).sort_values(["P_ext", "P_host", "strategy"])
    df.to_csv(out_dir / "runs.csv", index=False)

    # 可变策略热图：lambda_BL 与 lambda_BH（以 0 为中心的发散配色）
    fig_dir = out_dir / "figures"
    sub = df[df["p_m_override"].isna()].copy()
    if not sub.empty:
        for col in ["lambda_BL", "lambda_BH"]:
            vals = sub[col].to_numpy(dtype=float)
            vmin = float(np.nanmin(vals))
            vmax = float(np.nanmax(vals))

            # 若全为同号，用顺序配色更容易看出差异；若跨 0，用发散配色并以 0 为中心
            if vmin >= 0.0:
                cmap = "viridis"
                center = None
            elif vmax <= 0.0:
                cmap = "viridis_r"
                center = None
            else:
                cmap = "coolwarm"
                center = 0.0

            plot_grid_heatmap(
                df,
                value_col=col,
                gammas=gammas,
                ws=ws,
                title=f"{col}（>0 可入侵）",
                out_path=fig_dir / f"{col}.png",
                vmin=vmin,
                vmax=vmax,
                cmap=cmap,
                center=center,
                robust=True,
                annotate=True,
                fmt="{:.2f}",
                contour_levels=[0.0] if center == 0.0 else None,
            )

    meta = {
        "task": "Q4_markov_invasion_exponent",
        "model": "Model-0（B 仅用于入侵指数计算）",
        "params": asdict(params),
        "BL_params": asdict(bl_params),
        "BH_params": asdict(bh_params),
        "env": asdict(env),
        "sim": asdict(cfg),
        "reference_strategy": {"gamma": ref_gamma, "w": ref_w, "R_bar": R_bar, "y_ref": y_ref.tolist()},
        "thresholds": {"H_safe": H_safe, "q": q, "N_ref": N_ref, "N_q": N_q},
        "grid": {"gammas": gammas, "ws": ws},
        "seed": int(args.seed),
    }
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"已输出：{out_dir / 'runs.csv'}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MCM 2024 A 题仿真运行器（Model-0 bet-hedging / 季节 / 稳定性 + Q4 入侵 + 三元系统）。"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    bh = sub.add_parser("bet-hedging", help="随机环境（两态马尔可夫丰歉年）下的 bet-hedging 扫描（Model-0）。")
    bh.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    bh.add_argument("--seed", type=int, default=123, help="随机种子（用于生成共同环境序列）。")
    bh.add_argument("--years", type=int, default=200, help="仿真时长（年）。")
    bh.add_argument("--reps", type=int, default=100, help="环境序列条数（配对对照重复次数）。")
    bh.add_argument("--steps-per-year", type=int, default=12, help="每年采样点数（用于统计指标）。")
    bh.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    bh.add_argument("--rtol", type=float, default=1e-6)
    bh.add_argument("--atol", type=float, default=1e-9)

    bh.add_argument("--R-L", dest="R_L", type=float, default=1.0, help="低资源水平 R_L。")
    bh.add_argument("--RH-over-RL", dest="RH_over_RL", type=float, default=5.0, help="资源对比 R_H/R_L。")
    bh.add_argument("--p", type=float, default=0.5, help="马尔可夫切换概率（对称：p_LH=p_HL=p）。")

    bh.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    bh.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")

    bh.add_argument("--H-safe", dest="H_safe", type=float, default=0.3, help="宿主安全阈值 H_safe（H 已归一化）。")
    bh.add_argument("--q", type=float, default=0.05, help="准灭绝阈值比例：N_q=q*N_ref。")
    bh.add_argument("--burn-in", type=int, default=0, help="均值/CV 指标的 burn-in 年数（风险指标仍看全程）。")
    bh.add_argument("--rec-target-frac", dest="rec_target_frac", type=float, default=0.8, help="恢复目标比例：target=frac*ref。")
    bh.add_argument(
        "--rec-hold-years",
        dest="rec_hold_years",
        type=float,
        default=1.0,
        help="恢复判定的持续时间（年）：在该窗口内始终 >= target 才算恢复。",
    )

    # 人类捕捞/门控（可选）
    bh.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    bh.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    bh.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    bh.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")

    bh.set_defaults(func=cmd_bet_hedging)

    sea = sub.add_parser("seasonal", help="季节资源 R(t)=R0*(1+A*sin(2πt/T)) 下比较策略（Model-0）。")
    sea.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    sea.add_argument("--years", type=int, default=60, help="仿真时长（年）。")
    sea.add_argument("--steps-per-year", type=int, default=24, help="每年采样点数（用于轨迹图更平滑）。")
    sea.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    sea.add_argument("--rtol", type=float, default=1e-6)
    sea.add_argument("--atol", type=float, default=1e-9)
    sea.add_argument("--R0", type=float, default=2.0, help="平均资源水平 R0。")
    sea.add_argument("--A", type=float, default=0.5, help="季节振幅 A（0~1）。")
    sea.add_argument("--T", type=float, default=1.0, help="季节周期 T（年）。")
    sea.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    sea.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")
    sea.add_argument("--H-safe", dest="H_safe", type=float, default=0.3, help="宿主安全阈值 H_safe（H 已归一化）。")
    sea.add_argument("--q", type=float, default=0.05, help="准灭绝阈值比例：N_q=q*N_ref。")
    sea.add_argument("--burn-in", type=int, default=0, help="均值/CV 指标的 burn-in 年数。")
    sea.add_argument("--rec-target-frac", dest="rec_target_frac", type=float, default=0.8, help="恢复目标比例：target=frac*ref。")
    sea.add_argument("--rec-hold-years", dest="rec_hold_years", type=float, default=1.0, help="恢复判定的持续时间（年）。")
    sea.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    sea.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    sea.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    sea.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")
    sea.set_defaults(func=cmd_seasonal)

    stab = sub.add_parser("stability", help="常值资源下：平衡点 + Jacobian 特征值（局部稳定/回归时间）。")
    stab.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    stab.add_argument("--years", type=int, default=400, help="为接近稳态而积分的时长（年）。")
    stab.add_argument("--steps-per-year", type=int, default=12, help="每年采样点数（用于数值稳定）。")
    stab.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    stab.add_argument("--rtol", type=float, default=1e-6)
    stab.add_argument("--atol", type=float, default=1e-9)
    stab.add_argument("--R0", type=float, default=2.0, help="常值资源水平 R0。")
    stab.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    stab.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")
    stab.add_argument("--eps", type=float, default=1e-6, help="Jacobian 数值差分步长（相对尺度）。")
    stab.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    stab.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    stab.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    stab.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")
    stab.set_defaults(func=cmd_stability)

    tri = sub.add_parser("triad-markov", help="三元系统（Model-1/2/3）在随机环境下的全动力学仿真（含 B）。")
    tri.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    tri.add_argument("--model", type=int, default=1, help="选择模型：1=B_L；2=B_H；3=二者共存。")
    tri.add_argument("--seed", type=int, default=123, help="随机种子（用于生成共同环境序列）。")
    tri.add_argument("--years", type=int, default=200, help="仿真时长（年）。")
    tri.add_argument("--reps", type=int, default=100, help="环境序列条数（配对对照重复次数）。")
    tri.add_argument("--steps-per-year", type=int, default=12, help="每年采样点数（用于统计指标）。")
    tri.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    tri.add_argument("--rtol", type=float, default=1e-6)
    tri.add_argument("--atol", type=float, default=1e-9)
    tri.add_argument("--R-L", dest="R_L", type=float, default=1.0, help="低资源水平 R_L。")
    tri.add_argument("--RH-over-RL", dest="RH_over_RL", type=float, default=5.0, help="资源对比 R_H/R_L。")
    tri.add_argument("--p", type=float, default=0.5, help="马尔可夫切换概率（对称：p_LH=p_HL=p）。")
    tri.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    tri.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")
    tri.add_argument("--H-safe", dest="H_safe", type=float, default=0.3, help="宿主安全阈值 H_safe（H 已归一化）。")
    tri.add_argument("--q", type=float, default=0.05, help="准灭绝阈值比例：N_q=q*N_ref。")
    tri.add_argument("--burn-in", type=int, default=0, help="均值/CV 与恢复指标的 burn-in 年数。")
    tri.add_argument("--rec-target-frac", dest="rec_target_frac", type=float, default=0.8, help="恢复目标比例：target=frac*ref。")
    tri.add_argument("--rec-hold-years", dest="rec_hold_years", type=float, default=1.0, help="恢复判定的持续时间（年）。")
    tri.add_argument("--B-init", dest="B_init", type=float, default=1e-6, help="受益者初值（稀有入侵）。")
    tri.add_argument("--B-th", dest="B_th", type=float, default=1e-4, help="判定持续的阈值（burn-in 后 mean_B > B_th）。")
    tri.add_argument(
        "--B-out-th",
        dest="B_out_th",
        type=float,
        default=None,
        help="判定爆发的阈值（burn-in 后 max_B > B_out_th）。默认与 B_th 相同。",
    )
    tri.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    tri.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    tri.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    tri.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")
    tri.set_defaults(func=cmd_triad_markov)

    q4c = sub.add_parser("q4-constant", help="Q4：常值资源下计算 B_L/B_H 入侵阈值（R0 口径）。")
    q4c.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    q4c.add_argument("--years", type=int, default=400, help="为接近稳态而积分的时长（年）。")
    q4c.add_argument("--steps-per-year", type=int, default=12, help="每年采样点数（用于数值稳定）。")
    q4c.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    q4c.add_argument("--rtol", type=float, default=1e-6)
    q4c.add_argument("--atol", type=float, default=1e-9)
    q4c.add_argument("--R0", type=float, default=2.0, help="常值资源水平 R0。")
    q4c.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    q4c.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")
    q4c.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    q4c.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    q4c.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    q4c.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")
    q4c.set_defaults(func=cmd_q4_constant)

    q4m = sub.add_parser("q4-markov", help="Q4：随机环境下计算 B_L/B_H 入侵指数 λ（配对对照）。")
    q4m.add_argument("--out-dir", default="", help="输出目录（默认：MCM_Sim/24A/outputs/temp/run-<ts>）。")
    q4m.add_argument("--seed", type=int, default=123, help="随机种子（用于生成共同环境序列）。")
    q4m.add_argument("--years", type=int, default=200, help="仿真时长（年）。")
    q4m.add_argument("--reps", type=int, default=100, help="环境序列条数（配对对照重复次数）。")
    q4m.add_argument("--steps-per-year", type=int, default=12, help="每年采样点数（用于统计指标）。")
    q4m.add_argument("--solver", default="RK45", help="solve_ivp 方法（RK45/BDF/Radau/LSODA）。")
    q4m.add_argument("--rtol", type=float, default=1e-6)
    q4m.add_argument("--atol", type=float, default=1e-9)

    q4m.add_argument("--R-L", dest="R_L", type=float, default=1.0, help="低资源水平 R_L。")
    q4m.add_argument("--RH-over-RL", dest="RH_over_RL", type=float, default=5.0, help="资源对比 R_H/R_L。")
    q4m.add_argument("--p", type=float, default=0.5, help="马尔可夫切换概率（对称：p_LH=p_HL=p）。")

    q4m.add_argument("--gammas", default="0.5,1,2,4,8", help="gamma 扫描网格（逗号分隔）。")
    q4m.add_argument("--ws", default="0,1,3,5", help="记忆长度 w（年）扫描网格（逗号分隔）。")

    q4m.add_argument("--H-safe", dest="H_safe", type=float, default=0.3, help="宿主安全阈值 H_safe（H 已归一化）。")
    q4m.add_argument("--q", type=float, default=0.05, help="准灭绝阈值比例：N_q=q*N_ref。")
    q4m.add_argument("--burn-in", type=int, default=0, help="均值/CV 与 λ 指标的 burn-in 年数。")
    q4m.add_argument("--uA-const", dest="uA_const", type=float, default=0.0, help="恒定捕捞强度（年^-1）。")
    q4m.add_argument("--uA-max", dest="uA_max", type=float, default=0.0, help="门控捕捞最大增量（年^-1）。")
    q4m.add_argument("--uA-th", dest="uA_th", type=float, default=0.3, help="门控阈值（成体 A=M+F，归一化）。")
    q4m.add_argument("--uA-k", dest="uA_k", type=float, default=10.0, help="门控陡峭度（越大越接近 yes/no）。")

    q4m.set_defaults(func=cmd_q4_markov)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
