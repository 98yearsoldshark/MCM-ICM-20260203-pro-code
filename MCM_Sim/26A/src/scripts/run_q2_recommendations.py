#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：把数值结果自动汇总成“可执行建议”（recommendations）。

输入（由 scripts/run_q2_report.py 生成）：
- out_reports/q2/drivers_delta.csv
- out_reports/q2/component_drivers_matrix.csv
- out_reports/q2/mechanism_drivers_delta.csv
- out_reports/q2/param_sensitivity_overall.csv（可选）
- out_reports/q2/termination_stats.csv（可选）

输出：
- out_reports/q2/recommendations/
  - recommendations.md：面向论文写作的中文建议稿（可直接引用/再润色）
  - recommendations.csv：结构化表格，便于后续自动化筛选与画图
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

import numpy as np


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _fmt_h(x: float) -> str:
    if not np.isfinite(x):
        return "-"
    return f"{x:+.2f} h"


def _component_suggestion(component_id: str) -> str:
    m = {
        "no_screen": "降低屏幕亮度/缩短亮屏时长（自动亮度、深色模式、降低刷新率）",
        "no_radio": "优先 Wi-Fi、避免弱信号环境；合并网络请求，减少频繁小流量；必要时飞行模式",
        "no_background_total": "限制后台刷新与高频同步（省电模式、后台限制、推送合并）",
        "no_cpu_gpu": "降低计算负载（降低分辨率/帧率/画质，避免高负载长时间运行）",
        "no_gps": "减少定位消耗（关闭高精度定位/降低定位频率/离线地图）",
        "no_interaction": "避免“屏幕+网络+高CPU”同时峰值（任务串行/分批）",
        "no_base": "系统级与硬件级改进（减少系统常驻/唤醒；优化驱动与系统服务）",
    }
    return m.get(str(component_id), "（待补充：该组件对应的可执行建议）")


def _mechanism_suggestion(mech_id: str) -> str:
    m = {
        "no_rrc_tail": "减少“尾态”触发：合并网络请求、批量上传/下载，避免频繁小流量",
        "no_signal_penalty": "改善信号质量：在弱信号区减少联网活动/改用 Wi-Fi/离线内容",
        "no_bg_wake": "降低后台唤醒：限制后台同步频率、减少推送触发、延迟合并任务",
        "no_interaction": "降低协同放大：避免边刷视频边高负载计算；把任务拆分",
        "no_fg_bursts": "减少前台突发：把“多次小请求”改为“少次大请求”（缓存/预取）",
        "no_screen_markov": "减少误触发亮屏：关闭抬腕亮屏/双击唤醒（或提高触发阈值）",
        "no_signal_jitter": "减少信号频繁切换：尽量固定网络制式/避免边缘覆盖区域反复切换",
        "no_thermal_throttle": "改善散热/降低温升：散热设计、降低峰值功耗、限制持续高负载",
    }
    return m.get(str(mech_id), "（待补充：该机制对应的可执行建议）")


def _top_k(rows: list[dict[str, str]], *, key: str, k: int = 5) -> list[dict[str, str]]:
    def _v(r: dict[str, str]) -> float:
        try:
            return float(r.get(key, "nan"))
        except Exception:
            return float("nan")

    rs = [r for r in rows if np.isfinite(_v(r))]
    rs.sort(key=_v, reverse=True)
    return rs[: int(k)]


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 recommendations 汇总")
    ap.add_argument("--reports-dir", default=str(Path(__file__).resolve().parent.parent / "out_reports" / "q2"), help="run_q2_report.py 的输出目录")
    ap.add_argument("--soc0", type=float, default=1.0, help="敏感性/终止概率默认展示的 SOC0（小时）")
    ap.add_argument("--top-k", type=int, default=5, help="每个模块展示的 top-k")
    args = ap.parse_args()

    reports_dir = Path(args.reports_dir)
    out_dir = reports_dir / "recommendations"
    out_dir.mkdir(parents=True, exist_ok=True)

    drivers_path = reports_dir / "drivers_delta.csv"
    comp_mat_path = reports_dir / "component_drivers_matrix.csv"
    mech_path = reports_dir / "mechanism_drivers_delta.csv"
    sens_path = reports_dir / "param_sensitivity_overall.csv"
    term_path = reports_dir / "termination_stats.csv"

    drivers = _read_csv(drivers_path) if drivers_path.exists() else []
    comp_mat = _read_csv(comp_mat_path) if comp_mat_path.exists() else []
    mechs = _read_csv(mech_path) if mech_path.exists() else []
    sens = _read_csv(sens_path) if sens_path.exists() else []
    term = _read_csv(term_path) if term_path.exists() else []

    # 1) 总体策略动作：按 mean_delta_h 排序
    top_actions = _top_k(drivers, key="mean_delta_h", k=int(args.top_k))

    # 2) 按场景组件 drivers：每个场景取 top-3
    by_scenario: dict[str, list[dict[str, str]]] = {}
    for r in comp_mat:
        sid = str(r.get("scenario_id", "")).strip()
        if not sid:
            continue
        by_scenario.setdefault(sid, []).append(r)
    top_by_scenario: dict[str, list[dict[str, str]]] = {}
    for sid, rows in by_scenario.items():
        rows2 = [r for r in rows if np.isfinite(float(r.get("mean_delta_h", "nan")))]
        rows2.sort(key=lambda r: float(r.get("mean_delta_h", "nan")), reverse=True)
        top_by_scenario[sid] = rows2[:3]

    # 3) 机制 drivers：top-k
    top_mechs = _top_k(mechs, key="mean_delta_h", k=int(args.top_k))

    # 4) 参数敏感性：top-k（按 mean_abs_prcc），同一 soc0
    sens_soc0 = [r for r in sens if np.isfinite(float(r.get("mean_abs_prcc", "nan"))) and float(r.get("soc0", "nan")) == float(args.soc0)]
    sens_soc0.sort(key=lambda r: float(r.get("mean_abs_prcc", "nan")), reverse=True)
    top_params = sens_soc0[: int(args.top_k)]

    # 5) 终止概率：挑出 p_cutoff/p_insufficient_power 较大的场景（同一 soc0）
    risky = []
    for r in term:
        try:
            soc0 = float(r.get("soc0", "nan"))
            if soc0 != float(args.soc0):
                continue
            p_cut = float(r.get("p_cutoff", "nan"))
            p_ins = float(r.get("p_insufficient_power", "nan"))
        except Exception:
            continue
        if not (np.isfinite(p_cut) or np.isfinite(p_ins)):
            continue
        score = 0.7 * (p_cut if np.isfinite(p_cut) else 0.0) + 0.3 * (p_ins if np.isfinite(p_ins) else 0.0)
        risky.append((score, r))
    risky.sort(key=lambda kv: kv[0], reverse=True)
    top_risky = [r for _, r in risky[: int(args.top_k)]]

    # 结构化建议表（csv）
    rec_rows: list[dict[str, object]] = []

    for rank, a in enumerate(top_actions, 1):
        d = float(a.get("mean_delta_h", "nan"))
        rec_rows.append(
            {
                "level": "overall",
                "scenario_id": "*",
                "driver_type": "policy_action",
                "driver_id": a.get("action_id", ""),
                "driver_name_zh": a.get("title_zh", ""),
                "expected_delta_tte_h": d,
                "recommendation_zh": a.get("title_zh", ""),
                "evidence": f"drivers_delta.csv mean_delta_h={_fmt_h(d)}",
                "rank": rank,
            }
        )

    for sid, items in sorted(top_by_scenario.items()):
        for rank, r in enumerate(items, 1):
            cid = str(r.get("component_id", ""))
            d = float(r.get("mean_delta_h", "nan"))
            rec_rows.append(
                {
                    "level": "scenario",
                    "scenario_id": sid,
                    "driver_type": "component",
                    "driver_id": cid,
                    "driver_name_zh": r.get("title_zh", cid),
                    "expected_delta_tte_h": d,
                    "recommendation_zh": _component_suggestion(cid),
                    "evidence": f"component_drivers_matrix.csv mean_delta_h={_fmt_h(d)}",
                    "rank": rank,
                }
            )

    for rank, r in enumerate(top_mechs, 1):
        mid = str(r.get("mech_id", ""))
        d = float(r.get("mean_delta_h", "nan"))
        rec_rows.append(
            {
                "level": "overall",
                "scenario_id": "*",
                "driver_type": "mechanism",
                "driver_id": mid,
                "driver_name_zh": r.get("title_zh", mid),
                "expected_delta_tte_h": d,
                "recommendation_zh": _mechanism_suggestion(mid),
                "evidence": f"mechanism_drivers_delta.csv mean_delta_h={_fmt_h(d)}",
                "rank": rank,
            }
        )

    # markdown 建议稿
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = []
    md.append("# Q2 Recommendations（自动汇总）\n")
    md.append(f"- 生成时间：{now}\n")
    md.append(f"- 数据来源：`{reports_dir}`（由 `scripts/run_q2_report.py` 生成）\n")
    md.append("\n")

    md.append("## 1. 跨场景总体建议（策略动作层）\n")
    md.append("| 排名 | 建议（可执行） | 预期 ΔTTE（小时） | 证据 |\n")
    md.append("|---:|---|---:|---|\n")
    for i, a in enumerate(top_actions, 1):
        d = float(a.get("mean_delta_h", "nan"))
        md.append(f"| {i} | {a.get('title_zh','')} | {_fmt_h(d)} | drivers_delta.csv |\n")
    md.append("\n")

    md.append("## 2. 按场景建议（组件级 drivers → 可执行建议）\n")
    md.append("说明：组件级 drivers 是理想化反事实（把某组件功耗置零），用于识别“主因”，再映射为现实可操作建议。\n\n")
    for sid, items in sorted(top_by_scenario.items()):
        md.append(f"### {sid}\n")
        md.append("| 排名 | 主要 drivers（组件） | 预期 ΔTTE（小时） | 可执行建议 |\n")
        md.append("|---:|---|---:|---|\n")
        for i, r in enumerate(items, 1):
            cid = str(r.get("component_id", ""))
            d = float(r.get("mean_delta_h", "nan"))
            md.append(f"| {i} | {r.get('title_zh', cid)} | {_fmt_h(d)} | {_component_suggestion(cid)} |\n")
        md.append("\n")

    md.append("## 3. 机理层建议（机制 drivers）\n")
    md.append("| 排名 | 机制 drivers | 预期 ΔTTE（小时） | 含义/建议 |\n")
    md.append("|---:|---|---:|---|\n")
    for i, r in enumerate(top_mechs, 1):
        mid = str(r.get("mech_id", ""))
        d = float(r.get("mean_delta_h", "nan"))
        md.append(f"| {i} | {r.get('title_zh', mid)} | {_fmt_h(d)} | {_mechanism_suggestion(mid)} |\n")
    md.append("\n")

    if top_params:
        md.append("## 4. 参数不确定性 drivers（PRCC：谁主导 TTE 波动）\n")
        md.append(f"展示 SOC0={float(args.soc0):.2f} 的总体排名（按场景平均 |PRCC|）。\n\n")
        md.append("| 排名 | 参数 | 平均 |PRCC| |\n")
        md.append("|---:|---|---:|\n")
        for i, r in enumerate(top_params, 1):
            md.append(f"| {i} | {r.get('param_zh', r.get('param',''))} | {float(r.get('mean_abs_prcc','nan')):.2f} |\n")
        md.append("\n")

    if top_risky:
        md.append("## 5. 关机边界（终止概率）提示\n")
        md.append("说明：这不是“风险讨论”，而是用于回答赛题对“欠压截止/不可供电边界”的要求。\n\n")
        md.append("| 排名 | 场景 | p_cutoff | p_insufficient_power |\n")
        md.append("|---:|---|---:|---:|\n")
        for i, r in enumerate(top_risky, 1):
            md.append(
                f"| {i} | {r.get('scenario_id','')} | {float(r.get('p_cutoff','nan')):.2f} | {float(r.get('p_insufficient_power','nan')):.2f} |\n"
            )
        md.append("\n")

    md_path = out_dir / "recommendations.md"
    md_path.write_text("".join(md), encoding="utf-8")

    csv_path = out_dir / "recommendations.csv"
    _write_csv(
        csv_path,
        rec_rows,
        fieldnames=["level", "scenario_id", "driver_type", "driver_id", "driver_name_zh", "expected_delta_tte_h", "recommendation_zh", "evidence", "rank"],
    )

    print("Q2 recommendations 已生成：")
    print(f"- {md_path}")
    print(f"- {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

