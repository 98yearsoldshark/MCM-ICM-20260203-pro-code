#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：多数据集实验（validation_multi_*）结果汇总脚本（只读汇总，不跑仿真）。

用途：
- 用户希望“多跑几个数据集，再汇总结果”；为避免“一键总脚本”难排查，
  本脚本只做**读取既有 CSV 结果**并生成汇总（md+csv）。

输入约定（root 目录结构）：
- open_data/metrics.csv
- smartphone_measurements/summary_by_group.csv
- tte_trace_smartphone_measurements/per_group_tte.csv
- master_table/tte_by_state.csv
- user_behavior/summary_by_class.csv
- user_behavior/scenario_tte_pred.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _to_float(x: object) -> float:
    try:
        v = float(x)  # type: ignore[arg-type]
    except Exception:
        return float("nan")
    return v


def _fmt(x: float, *, nd: int = 3) -> str:
    if not np.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(nd)}f}"


def _pct(x: float, *, nd: int = 1) -> str:
    if not np.isfinite(float(x)):
        return "nan"
    return f"{float(x) * 100.0:.{int(nd)}f}%"


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _summarize_open_data(metrics_csv: Path) -> dict[str, object]:
    rows = _read_csv(metrics_csv)
    by_comp = {r.get("component", ""): r for r in rows}
    total = by_comp.get("total", {})
    out = {
        "n_components": len(rows),
        "total_pearson_r": _to_float(total.get("pearson_r")),
        "total_mae_W": _to_float(total.get("mae_W")),
        "total_mape_pct": _to_float(total.get("mape_pct")),
        "total_obs_mean_W": _to_float(total.get("obs_mean_W")),
        "total_pred_mean_W": _to_float(total.get("pred_mean_W")),
        "radio_pearson_r": _to_float(by_comp.get("radio", {}).get("pearson_r")),
        "radio_obs_mean_W": _to_float(by_comp.get("radio", {}).get("obs_mean_W")),
        "radio_pred_mean_W": _to_float(by_comp.get("radio", {}).get("pred_mean_W")),
    }
    return out


def _summarize_smartphone_measurements(summary_csv: Path) -> dict[str, dict[str, float]]:
    rows = _read_csv(summary_csv)
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        key = f"{r.get('link','?')}/{r.get('proto','?')}/{r.get('role','?')}"
        out[key] = {
            "n": _to_float(r.get("n")),
            "p50_j_per_mb": _to_float(r.get("p50_j_per_mb")),
            "p05_j_per_mb": _to_float(r.get("p05_j_per_mb")),
            "p95_j_per_mb": _to_float(r.get("p95_j_per_mb")),
            "mean_j_per_mb": _to_float(r.get("mean_j_per_mb")),
        }
    return out


def _summarize_tte_trace(per_group_csv: Path) -> list[dict[str, object]]:
    rows = _read_csv(per_group_csv)
    out: list[dict[str, object]] = []
    for r in rows:
        p_obs = _to_float(r.get("obs_mean_power_W"))
        p_model = _to_float(r.get("avg_power_model_W"))
        t_obs = _to_float(r.get("tte_obs_equiv_h"))
        t_model = _to_float(r.get("tte_model_mean_h"))
        out.append(
            {
                "group_id": r.get("group_id", ""),
                "p_obs_W": p_obs,
                "p_model_W": p_model,
                "p_model_over_obs": (p_model / p_obs) if (np.isfinite(p_model) and np.isfinite(p_obs) and p_obs > 1e-12) else float("nan"),
                "tte_obs_h": t_obs,
                "tte_model_h": t_model,
                "tte_model_over_obs": (t_model / t_obs) if (np.isfinite(t_model) and np.isfinite(t_obs) and t_obs > 1e-12) else float("nan"),
            }
        )
    return out


def _summarize_master_table(tte_by_state_csv: Path) -> list[dict[str, object]]:
    rows = _read_csv(tte_by_state_csv)
    # 只做“new vs eol”的均值对比（论文/赛题口径关心趋势与量级）
    out: list[dict[str, object]] = []
    loads = sorted({r.get("load_label", "") for r in rows if r.get("load_label")})
    for load in loads:
        sub = [r for r in rows if r.get("load_label") == load]
        t_new = [_to_float(r.get("tte_h")) for r in sub if r.get("battery_state_label") == "new"]
        t_eol = [_to_float(r.get("tte_h")) for r in sub if r.get("battery_state_label") == "eol"]
        s_new = [_to_float(r.get("soc_end")) for r in sub if r.get("battery_state_label") == "new"]
        s_eol = [_to_float(r.get("soc_end")) for r in sub if r.get("battery_state_label") == "eol"]
        if not t_new or not t_eol:
            continue
        t_new_m = float(np.nanmean(np.array(t_new, dtype=float)))
        t_eol_m = float(np.nanmean(np.array(t_eol, dtype=float)))
        out.append(
            {
                "load_label": load,
                "tte_new_mean_h": t_new_m,
                "tte_eol_mean_h": t_eol_m,
                "tte_drop_frac": (t_new_m - t_eol_m) / t_new_m if (np.isfinite(t_new_m) and t_new_m > 1e-12) else float("nan"),
                "soc_end_new_mean": float(np.nanmean(np.array(s_new, dtype=float))) if s_new else float("nan"),
                "soc_end_eol_mean": float(np.nanmean(np.array(s_eol, dtype=float))) if s_eol else float("nan"),
            }
        )
    return out


def _summarize_user_behavior(summary_by_class_csv: Path, scenario_tte_pred_csv: Path) -> dict[str, object]:
    rows = _read_csv(summary_by_class_csv)
    cls = []
    for r in rows:
        cls.append(
            {
                "class": int(float(r.get("class", "nan"))),
                "n": int(float(r.get("n", "nan"))),
                "p50_h": _to_float(r.get("p50_h")),
                "p05_h": _to_float(r.get("p05_h")),
                "p95_h": _to_float(r.get("p95_h")),
                "mean_h": _to_float(r.get("mean_h")),
            }
        )
    cls.sort(key=lambda x: x["class"])

    sc = _read_csv(scenario_tte_pred_csv)
    scen = []
    for r in sc:
        scen.append(
            {
                "scenario_id": r.get("scenario_id", ""),
                "title_zh": r.get("title_zh", ""),
                "tte_mean_h": _to_float(r.get("tte_mean_h")),
                "tte_p05_h": _to_float(r.get("tte_p05_h")),
                "tte_p95_h": _to_float(r.get("tte_p95_h")),
            }
        )

    return {"classes": cls, "scenarios": scen}


def _write_summary_md(
    out_md: Path,
    *,
    root: Path,
    open_data: dict[str, object],
    sm_energy: dict[str, dict[str, float]],
    tte_trace: list[dict[str, object]],
    master_table: list[dict[str, object]],
    user_behavior: dict[str, object],
) -> None:
    lines: list[str] = []
    lines.append(f"# Q2 多数据集实验汇总（{root.name}）")
    lines.append("")
    lines.append("本汇总只读取既有 CSV 结果（不跑仿真），用于快速判断：模型哪里贴近真实、哪里偏差最大、下一步该改什么。")
    lines.append("")

    # 1) open_data
    lines.append("## 1) AndroWatts（open_data/aggregated.csv：短时功耗量级）")
    lines.append(
        "- 总功耗："
        f"r={_fmt(float(open_data['total_pearson_r']), nd=2)}，"
        f"MAE={_fmt(float(open_data['total_mae_W']), nd=2)}W，"
        f"MAPE={_fmt(float(open_data['total_mape_pct']), nd=1)}%"
        f"（obs均值={_fmt(float(open_data['total_obs_mean_W']), nd=2)}W，pred均值={_fmt(float(open_data['total_pred_mean_W']), nd=2)}W）"
    )
    lines.append(
        "- 网络组件（radio）相关性："
        f"r={_fmt(float(open_data['radio_pearson_r']), nd=2)}"
        f"（obs均值={_fmt(float(open_data['radio_obs_mean_W']), nd=3)}W，pred均值={_fmt(float(open_data['radio_pred_mean_W']), nd=3)}W）"
    )
    lines.append("")

    # 2) SmartphoneMeasurements
    lines.append("## 2) SmartphoneMeasurements（Monsoon+iPerf：通信单位能耗 J/MB）")
    pick_keys = [
        "router/tcp/client",
        "direct/tcp/client",
        "router/udp/client",
        "direct/udp/client",
        "router/tcp/server",
        "direct/tcp/server",
    ]
    lines.append("| 组 | p50(J/MB) | p05~p95(J/MB) | n |")
    lines.append("|---|---:|---:|---:|")
    for k in pick_keys:
        d = sm_energy.get(k)
        if not d:
            continue
        lines.append(f"| {k} | {_fmt(d['p50_j_per_mb'], nd=3)} | {_fmt(d['p05_j_per_mb'], nd=3)}~{_fmt(d['p95_j_per_mb'], nd=3)} | {int(d['n'])} |")
    lines.append("")

    # 3) TTE trace proxy
    lines.append("## 3) SmartphoneMeasurements（TTE 代理对照：E_batt/P_mean vs 模型仿真）")
    lines.append("| 组 | P_obs(W) | P_model(W) | P_model/P_obs | TTE_obs(h) | TTE_model(h) | TTE_model/TTE_obs |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in tte_trace:
        lines.append(
            f"| {r['group_id']} | {_fmt(float(r['p_obs_W']), nd=2)} | {_fmt(float(r['p_model_W']), nd=2)} | {_fmt(float(r['p_model_over_obs']), nd=2)} | "
            f"{_fmt(float(r['tte_obs_h']), nd=2)} | {_fmt(float(r['tte_model_h']), nd=2)} | {_fmt(float(r['tte_model_over_obs']), nd=2)} |"
        )
    lines.append("")

    # 4) Master table aging trend
    lines.append("## 4) AndroWatts × 电池老化状态表（TTE vs SOH：趋势与量级）")
    if master_table:
        lines.append("| 负载 | TTE_new(h) | TTE_eol(h) | 下降比例 | 终止SOC（new→eol） |")
        lines.append("|---|---:|---:|---:|---:|")
        for r in master_table:
            lines.append(
                f"| {r['load_label']} | {_fmt(float(r['tte_new_mean_h']), nd=2)} | {_fmt(float(r['tte_eol_mean_h']), nd=2)} | "
                f"{_pct(float(r['tte_drop_frac']), nd=1)} | {_fmt(float(r['soc_end_new_mean']), nd=3)}→{_fmt(float(r['soc_end_eol_mean']), nd=3)} |"
            )
    else:
        lines.append("- （缺少 master_table 结果文件，跳过）")
    lines.append("")

    # 5) user behavior
    lines.append("## 5) user_behavior_dataset（按日耗电→等效 TTE：长时间量级范围）")
    cls = user_behavior.get("classes", [])
    scen = user_behavior.get("scenarios", [])
    if cls:
        lines.append("| 类别 | n | p50(h) | p05~p95(h) |")
        lines.append("|---:|---:|---:|---:|")
        for r in cls:
            lines.append(f"| {r['class']} | {r['n']} | {_fmt(float(r['p50_h']), nd=1)} | {_fmt(float(r['p05_h']), nd=1)}~{_fmt(float(r['p95_h']), nd=1)} |")
    if scen:
        lines.append("")
        lines.append("模型代表性场景（用于叠加对照）：")
        lines.append("| scenario_id | 场景 | TTE_mean(h) |")
        lines.append("|---|---|---:|")
        for r in scen:
            lines.append(f"| {r['scenario_id']} | {r['title_zh']} | {_fmt(float(r['tte_mean_h']), nd=2)} |")
    lines.append("")

    # Conclusion / next steps
    lines.append("## 结论（当前偏差最大的位置）")
    lines.append(
        "- 短时总功耗量级（AndroWatts）整体匹配良好，但“网络组件（radio）”的相关性偏低，说明网络侧机理/映射仍需加强。"
    )
    lines.append(
        "- SmartphoneMeasurements 显示 Wi‑Fi 单位数据能耗 p50 往往在 0.4~0.9 J/MB（部分组更高），而当前模型配置里的 Wi‑Fi e_per_mb_J≈0.25 J/MB，"
        "这会直接导致：网络场景下平均功耗偏低 → TTE 明显偏长。"
    )
    lines.append("")
    lines.append("## 下一步建议（按性价比排序）")
    lines.append("- 先做“网络参数局部校准”：把 Wi‑Fi 的 e_per_mb_J 提升到观测中位数附近，并考虑区分 router/direct（或用信号质量参数映射）。")
    lines.append("- 再校准“baseline（无网络）”的功耗量级：屏幕全亮白底 + 系统基线功耗是否被低估。")
    lines.append("- 之后再用同一套校准参数回跑本目录下的 3) 对照表，检查 TTE_model/TTE_obs 是否收敛到 1 附近。")
    lines.append("")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_csv(out_csv: Path, *, tte_trace: list[dict[str, object]]) -> None:
    # 把最关键的“误差表”扁平化输出，便于做后续版本对比（diff）。
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["group_id", "p_obs_W", "p_model_W", "p_model_over_obs", "tte_obs_h", "tte_model_h", "tte_model_over_obs"]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in tte_trace:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> int:
    ap = argparse.ArgumentParser(description="Q2 多数据集实验（validation_multi_*）汇总（只读）")
    ap.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent / "out_reports" / "q2" / "validation_multi_260131_v1"),
        help="validation_multi_* 根目录（包含 open_data/、smartphone_measurements/ 等子目录）",
    )
    ap.add_argument("--out", default="", help="输出目录（默认与 --root 相同）")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = _ensure_dir(Path(args.out) if args.out else root)

    open_data = _summarize_open_data(root / "open_data" / "metrics.csv")
    sm_energy = _summarize_smartphone_measurements(root / "smartphone_measurements" / "summary_by_group.csv")
    tte_trace = _summarize_tte_trace(root / "tte_trace_smartphone_measurements" / "per_group_tte.csv")
    master_table = _summarize_master_table(root / "master_table" / "tte_by_state.csv")
    user_behavior = _summarize_user_behavior(
        root / "user_behavior" / "summary_by_class.csv",
        root / "user_behavior" / "scenario_tte_pred.csv",
    )

    out_md = out_dir / "summary.md"
    out_csv = out_dir / "tte_trace_key_metrics.csv"
    _write_summary_md(
        out_md,
        root=root,
        open_data=open_data,
        sm_energy=sm_energy,
        tte_trace=tte_trace,
        master_table=master_table,
        user_behavior=user_behavior,
    )
    _write_summary_csv(out_csv, tte_trace=tte_trace)

    print("已生成汇总：")
    print(f"- {out_md}")
    print(f"- {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

