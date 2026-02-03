#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 观测对照实验：用 AndroWatts aggregated.csv 验证手机侧功耗量级与 drivers。

输出：
- out_reports/q2/validation_open_data/：
  - per_case.csv：逐样本观测 vs 模型预测（平均功率 W）
  - metrics.csv：总体指标（相关性/误差）
- out_plots/q2/{paper|study}/observed_open_data/：
  - 01_total_power_scatter.png：总功耗散点图
  - 02_component_share_bar.png：组件占比对比

说明：
- 该验证只用于“公开测量数据的量级对照”，并不替代连续时间电池模型；
- AndroWatts 数据是聚合统计，且来源机型/固件固定，因此我们重点比较：
  1) 总功耗量级是否合理；
  2) 屏幕/CPU/GPU/网络等主要 drivers 的相对关系是否一致。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.observed.andro_watts import AndroWattsCase, build_cases, load_aggregated_csv
from mcm26a.power import PowerParams1Stateful, StatefulPowerModel1
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _mean(arr: list[float]) -> float:
    return float(np.mean(np.array(arr, dtype=float))) if arr else float("nan")


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if not np.any(m):
        return float("nan")
    return float(np.mean(np.abs(a[m] - b[m])))


def _mape_pct(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b) & (np.abs(a) > 1e-12)
    if not np.any(m):
        return float("nan")
    return float(np.mean(np.abs((b[m] - a[m]) / a[m])) * 100.0)


def _pearsonr(y_true: list[float], y_pred: list[float]) -> float:
    a = np.array(y_true, dtype=float)
    b = np.array(y_pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(np.sum(m)) < 3:
        return float("nan")
    aa = a[m] - float(np.mean(a[m]))
    bb = b[m] - float(np.mean(b[m]))
    denom = float(np.sqrt(np.sum(aa * aa) * np.sum(bb * bb)))
    if denom <= 1e-12:
        return float("nan")
    return float(np.sum(aa * bb) / denom)


def _simulate_mean_power(
    case: AndroWattsCase,
    *,
    power: PowerParams1Stateful,
    dt_s: float,
    n_seeds: int,
    seed0: int,
) -> dict[str, float]:
    """对单个 case 多随机种子平均，得到“平均功率分解（W）”。

说明：
- 这里直接在功耗模型层做积分平均，避免把短时验证强行耦合到电池端；
- battery_temp_C 传 None，使 dvfs_scale=1（避免把“温度-功耗反馈”混入手机侧功耗验证）。
"""

    dur = float(case.duration_s)
    if dur <= 0:
        return {k: float("nan") for k in ["base_w", "screen_w", "cpu_w", "gpu_w", "radio_w", "gps_w", "background_w", "interaction_w", "total_w"]}

    # 每个 seed 计算一次平均功率，再做均值
    avg_by_seed: dict[str, list[float]] = {
        "base_w": [],
        "screen_w": [],
        "cpu_w": [],
        "gpu_w": [],
        "radio_w": [],
        "gps_w": [],
        "background_w": [],
        "interaction_w": [],
        "total_w": [],
    }

    for k in range(int(n_seeds)):
        pm = StatefulPowerModel1(power, seed=int(seed0) + k)
        pm.reset()
        e = {k: 0.0 for k in avg_by_seed.keys()}
        t = 0.0
        while t < dur - 1e-12:
            dt = min(float(dt_s), dur - t)
            bd = pm.step(case.segment, dt_s=dt, battery_temp_C=None)
            e["base_w"] += float(bd.base_w) * dt
            e["screen_w"] += float(bd.screen_w) * dt
            e["cpu_w"] += float(bd.cpu_w) * dt
            e["gpu_w"] += float(bd.gpu_w) * dt
            e["radio_w"] += float(bd.radio_w) * dt
            e["gps_w"] += float(bd.gps_w) * dt
            e["background_w"] += float(bd.background_w) * dt
            e["interaction_w"] += float(bd.interaction_w) * dt
            e["total_w"] += float(bd.total_w) * dt
            t += dt

        for kk in avg_by_seed.keys():
            avg_by_seed[kk].append(float(e[kk]) / dur)

    return {k: _mean(vs) for k, vs in avg_by_seed.items()}


def _plot_total_scatter(rows: list[dict[str, float]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)
    obs = [float(r["obs_total_w"]) for r in rows]
    pred = [float(r["pred_total_w"]) for r in rows]

    a = np.array(obs, dtype=float)
    b = np.array(pred, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    a = a[m]
    b = b[m]

    fig, ax = plt.subplots(figsize=(6.8, 5.6))

    # 点数较多时直接 scatter 容易“糊成一团”，用 hexbin 更容易读出密度结构。
    hb = ax.hexbin(a, b, gridsize=34, cmap="Blues", mincnt=1, linewidths=0.0, alpha=0.95)
    cbar = fig.colorbar(hb, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label("样本密度（格内点数）")

    # 统一坐标范围（保持 1:1 线为 45°，更直观）
    hi = float(np.nanmax(np.array([np.nanmax(a) if a.size else 1.0, np.nanmax(b) if b.size else 1.0], dtype=float)))
    hi = 1.0 if (not np.isfinite(hi) or hi <= 0) else hi
    hi *= 1.02
    lo = 0.0
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")

    # 参考线：理想一致（y=x）+ 线性拟合（仅用于诊断偏差/比例误差）
    ax.plot([lo, hi], [lo, hi], color="#E45756", lw=1.6, linestyle="--", label="理想一致线 y=x")
    if a.size >= 3:
        A = np.column_stack([np.ones_like(a), a])
        b0, b1 = np.linalg.lstsq(A, b, rcond=None)[0].tolist()
        ax.plot([lo, hi], [b0 + b1 * lo, b0 + b1 * hi], color="#54A24B", lw=1.6, alpha=0.85, label=f"线性拟合 y={b0:.2f}+{b1:.2f}x")
    ax.set_xlabel("观测总功耗（W）")
    ax.set_ylabel("模型预测总功耗（W）")
    r = _pearsonr(obs, pred)
    mae = _mae(obs, pred)
    mape = _mape_pct(obs, pred)
    ax.set_title(f"AndroWatts 对照：总功耗观测 vs 预测{style.title_suffix}")
    ax.legend(frameon=False, loc="upper left")

    # 关键指标放在图内角落（paper 也可直接引用）
    ax.text(
        0.98,
        0.02,
        f"r={r:.2f}  MAE={mae:.2f}W  MAPE={mape:.1f}%",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.85", alpha=0.9),
    )

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：每个点是一条 AndroWatts 测试样本（约 30 秒）。\n"
            "我们将公开数据中的设备状态（亮度/频率/流量/温度）映射为模型输入段，并对功耗模型的随机过程做多种子平均。\n"
            f"指标：Pearson r={r:.2f}，MAE={mae:.2f}W，MAPE={mape:.1f}%。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_component_share(rows: list[dict[str, float]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    comps = ["screen", "cpu", "gpu", "radio", "gps", "background", "base", "other"]
    comp_zh = {
        "screen": "屏幕",
        "cpu": "CPU/TPU",
        "gpu": "GPU",
        "radio": "网络",
        "gps": "GPS",
        "background": "外设/后台",
        "base": "基础/系统",
        "other": "其它",
    }

    obs_total = np.array([float(r["obs_total_w"]) for r in rows], dtype=float)
    pred_total = np.array([float(r["pred_total_w"]) for r in rows], dtype=float)

    def share(prefix: str, total: np.ndarray) -> list[float]:
        out = []
        for c in comps:
            xs = np.array([float(r[f"{prefix}_{c}_w"]) for r in rows], dtype=float)
            out.append(float(np.nanmean(xs / np.maximum(total, 1e-12)) * 100.0))
        return out

    obs_share = share("obs", obs_total)
    pred_share = share("pred", pred_total)

    x = np.arange(len(comps))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.bar(x - w / 2, obs_share, width=w, color="#4C78A8", alpha=0.9, label="观测（AndroWatts）")
    ax.bar(x + w / 2, pred_share, width=w, color="#F58518", alpha=0.9, label="模型预测（均值）")
    ax.set_xticks(x)
    ax.set_xticklabels([comp_zh[c] for c in comps], rotation=15, ha="right")
    ax.set_ylabel("平均能耗占比（%）")
    ax.set_ylim(0, 100)
    ax.set_title(f"AndroWatts 对照：组件能耗占比（均值）{style.title_suffix}")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.15))

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.22, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：将 AndroWatts 的 power rails 按可解释规则聚合为“屏幕/CPU/GPU/网络/GPS/外设/基础/其它”。\n"
            "该图用于验证 drivers 叙事：主要耗电是否由屏幕、计算、网络等少数组件主导；以及模型的分解是否与公开测量一致。\n"
            "注意：AndroWatts 的 rail 命名与我们模型组件并非一一对应，因此“外设/后台/基础/其它”的聚合存在不可避免的不确定性。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 观测对照：AndroWatts aggregated.csv")
    ap.add_argument(
        "--data",
        default=str(SRC_DIR.parent / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"),
        help="aggregated.csv 路径",
    )
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON 路径（no7 升级 + AndroWatts 多目标校准版）",
    )
    ap.add_argument("--out-report-dir", default=str(SRC_DIR / "out_reports" / "q2" / "validation_open_data"))
    ap.add_argument("--out-plot-dir", default=str(SRC_DIR / "out_plots"))
    ap.add_argument("--mode", default="", help="只生成指定模式：paper 或 study；留空则两种模式都生成")
    ap.add_argument("--max-n", type=int, default=250, help="最多抽样多少条测试样本（0 表示全量 1000）")
    ap.add_argument("--seed", type=int, default=0, help="抽样随机种子")
    ap.add_argument("--seeds-per-case", type=int, default=20, help="每条样本做多少随机种子平均")
    ap.add_argument("--dt", type=float, default=1.0, help="功耗积分步长（秒）")
    ap.add_argument("--max-screen-nits", type=float, default=500.0, help="Brightness(0~100) 映射到的最大 nits")
    args = ap.parse_args()

    df = load_aggregated_csv(args.data)
    cases = build_cases(df, max_n=None if int(args.max_n) <= 0 else int(args.max_n), seed=int(args.seed), max_screen_nits=float(args.max_screen_nits))

    power = PowerParams1Stateful.from_json(args.power)

    out_report = ensure_dir(args.out_report_dir)
    out_plot_root = ensure_dir(args.out_plot_dir) / "q2"

    rows: list[dict[str, float]] = []
    for idx, c in enumerate(cases):
        pred = _simulate_mean_power(
            c,
            power=power,
            dt_s=float(args.dt),
            n_seeds=int(args.seeds_per_case),
            seed0=int(args.seed) * 10_000 + idx * 1000,
        )

        # 逐样本记录：观测（obs_）与预测（pred_）
        r: dict[str, float] = {
            "test_id": float(c.test_id),
            "duration_s": float(c.duration_s),
            "soc0": float(c.soc0) if c.soc0 is not None else float("nan"),
            "temp_c": float(c.temp_c) if c.temp_c is not None else float("nan"),
            "brightness_nits": float(c.segment.brightness_nits),
            "cpu_load": float(c.segment.cpu_load),
            "gpu_load": float(c.segment.gpu_load),
            "gps_on": 1.0 if bool(c.segment.gps_on) else 0.0,
        }

        obs = c.obs.as_dict()
        r.update({f"obs_{k}": float(v) for k, v in obs.items()})
        r.update(
            {
                "pred_base_w": float(pred["base_w"]),
                "pred_screen_w": float(pred["screen_w"]),
                "pred_cpu_w": float(pred["cpu_w"]),
                "pred_gpu_w": float(pred["gpu_w"]),
                "pred_radio_w": float(pred["radio_w"]),
                "pred_gps_w": float(pred["gps_w"]),
                "pred_background_w": float(pred["background_w"]),
                "pred_interaction_w": float(pred["interaction_w"]),
                "pred_other_w": 0.0,
                "pred_total_w": float(pred["total_w"]),
            }
        )
        rows.append(r)

    per_case_csv = out_report / "per_case.csv"
    with per_case_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # 汇总指标
    comps = [
        ("total", "obs_total_w", "pred_total_w"),
        ("screen", "obs_screen_w", "pred_screen_w"),
        ("cpu", "obs_cpu_w", "pred_cpu_w"),
        ("gpu", "obs_gpu_w", "pred_gpu_w"),
        ("radio", "obs_radio_w", "pred_radio_w"),
        ("gps", "obs_gps_w", "pred_gps_w"),
        ("background", "obs_background_w", "pred_background_w"),
        ("base", "obs_base_w", "pred_base_w"),
        ("other", "obs_other_w", "pred_other_w"),
    ]
    metric_rows: list[dict[str, float]] = []
    for name, ocol, pcol in comps:
        y_true = [float(r[ocol]) for r in rows]
        y_pred = [float(r[pcol]) for r in rows]
        metric_rows.append(
            {
                "component": name,
                "pearson_r": _pearsonr(y_true, y_pred),
                "mae_W": _mae(y_true, y_pred),
                "mape_pct": _mape_pct(y_true, y_pred),
                "obs_mean_W": float(np.nanmean(np.array(y_true, dtype=float))),
                "pred_mean_W": float(np.nanmean(np.array(y_pred, dtype=float))),
            }
        )

    metrics_csv = out_report / "metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["component", "pearson_r", "mae_W", "mape_pct", "obs_mean_W", "pred_mean_W"])
        w.writeheader()
        w.writerows(metric_rows)

    # 出图（paper/study 两套）
    modes: list[PlotMode] = ["paper", "study"] if not args.mode else [str(args.mode)]  # type: ignore[list-item]
    for mode in modes:
        out_plot = ensure_dir(out_plot_root / mode / "observed_open_data")
        fig1 = _plot_total_scatter(rows, mode=mode)
        savefig(fig1, out_plot / "01_total_power_scatter.png", mode=mode)

        fig2 = _plot_component_share(rows, mode=mode)
        savefig(fig2, out_plot / "02_component_share_bar.png", mode=mode)

    print("AndroWatts 验证完成：")
    print(f"- per-case: {per_case_csv}")
    print(f"- metrics : {metrics_csv}")
    print(f"- plots   : {out_plot_root}/{{paper|study}}/observed_open_data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
