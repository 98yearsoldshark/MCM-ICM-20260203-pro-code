#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：生成“模型好/差边界”的诊断总表（只做汇总，不重新跑仿真）。

设计原则（按赛题 Q2 / no10 口径）：
- 赛题要求 “identify where the model performs well or poorly”，因此需要把我们已有的
  多条证据链（公开观测对照、UQ、数值稳定性）汇总成一张可引用的表。
- 避免“一键全跑大脚本”：本脚本只读取 out_reports/q2/ 下已有 CSV，生成 summary，
  便于排查（哪条证据链坏了就去跑对应 validate 脚本）。

输出：
- MCM_Sim/26A/src/out_reports/q2/diagnostics/
  - diagnostics_summary.csv
  - diagnostics_summary.md
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

from mcm26a.power import PowerParams1Stateful


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


def _q(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    arr = np.array(xs, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size <= 0:
        return float("nan")
    return float(np.quantile(arr, float(q)))


def _safe_float(x: object, default: float = float("nan")) -> float:
    try:
        v = float(x)
    except Exception:
        return float(default)
    return float(v)


def _append(rows: list[dict[str, object]], *, category: str, metric: str, value: float, unit: str, note_zh: str, source: str) -> None:
    rows.append(
        {
            "category": str(category),
            "metric": str(metric),
            "value": float(value) if np.isfinite(float(value)) else float("nan"),
            "unit": str(unit),
            "note_zh": str(note_zh),
            "source": str(source),
        }
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 诊断总表（汇总已生成的 out_reports/q2 产物）")
    ap.add_argument("--q2-reports", default=str(SRC_DIR / "out_reports" / "q2"), help="Q2 报表根目录（默认 out_reports/q2）")
    ap.add_argument("--out-dir", default=str(SRC_DIR / "out_reports" / "q2" / "diagnostics"), help="输出目录")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数（用于提取 e_per_mb_J 等可解释参数）",
    )
    ap.add_argument(
        "--open-data-metrics",
        default="validation_open_data_mo_v2/metrics.csv",
        help="AndroWatts 观测对照指标（相对 q2-reports 的路径）",
    )
    args = ap.parse_args()

    q2_reports = Path(args.q2_reports)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    power = PowerParams1Stateful.from_json(Path(args.power))
    e_wifi_good = float(power.rrc.e_per_mb("wifi", "good"))
    e_wifi_poor = float(power.rrc.e_per_mb("wifi", "poor"))

    rows: list[dict[str, object]] = []

    # -----------------------------
    # A) AndroWatts（短时功耗量级对照）
    # -----------------------------
    p_metrics = q2_reports / str(args.open_data_metrics)
    if p_metrics.exists():
        m = _read_csv(p_metrics)
        by_comp = {str(r.get("component", "")): r for r in m}
        total = by_comp.get("total", {})
        total_mape = _safe_float(total.get("mape_pct", float("nan")))
        total_r = _safe_float(total.get("pearson_r", float("nan")))
        obs_mean = _safe_float(total.get("obs_mean_W", float("nan")))
        pred_mean = _safe_float(total.get("pred_mean_W", float("nan")))
        bias_pct = float("nan")
        if np.isfinite(obs_mean) and abs(obs_mean) > 1e-12 and np.isfinite(pred_mean):
            bias_pct = (pred_mean - obs_mean) / obs_mean * 100.0

        _append(
            rows,
            category="observed_open_data",
            metric="total_mape_pct",
            value=total_mape,
            unit="%",
            note_zh="总功耗量级对照误差（越小越好；用于回答 Q2 的 observed/plausible 对照）。",
            source=str(p_metrics),
        )
        _append(
            rows,
            category="observed_open_data",
            metric="total_pearson_r",
            value=total_r,
            unit="-",
            note_zh="总功耗相关性（越接近 1 越好）。",
            source=str(p_metrics),
        )
        _append(
            rows,
            category="observed_open_data",
            metric="total_bias_pct",
            value=bias_pct,
            unit="%",
            note_zh="总功耗均值偏差（pred_mean-obs_mean）。正值表示整体偏高，负值表示整体偏低。",
            source=str(p_metrics),
        )

        # 找出组件级最弱项（mape 最大的前 3，过滤 nan）
        bad = []
        for comp, rr in by_comp.items():
            v = _safe_float(rr.get("mape_pct", float("nan")))
            if np.isfinite(v) and comp not in ("total", "other"):
                bad.append((v, comp))
        bad.sort(reverse=True)
        for rank, (v, comp) in enumerate(bad[:3], start=1):
            _append(
                rows,
                category="observed_open_data",
                metric=f"weak_component_mape_rank{rank}",
                value=float(v),
                unit="%",
                note_zh=f"组件级对照的薄弱项：{comp}（MAPE 越大越难分解/映射）。",
                source=str(p_metrics),
            )
    else:
        _append(
            rows,
            category="observed_open_data",
            metric="missing",
            value=float("nan"),
            unit="-",
            note_zh="未找到 AndroWatts 对照指标，请先运行 validate_q2_open_data.py。",
            source=str(p_metrics),
        )

    # -----------------------------
    # B) SmartphoneMeasurements（通信能耗量级 + 参数对照）
    # -----------------------------
    p_sm = q2_reports / "validation_smartphone_measurements" / "summary_by_group.csv"
    if p_sm.exists():
        sm = _read_csv(p_sm)
        # 只用 WiFi direct/router 的 TCP/UDP 组（role=client/server），计算整体分布
        jmb = [_safe_float(r.get("mean_j_per_mb", float("nan"))) for r in sm]
        jmb = [x for x in jmb if np.isfinite(x) and x > 0]
        _append(
            rows,
            category="observed_smartphone_measurements",
            metric="observed_j_per_mb_p50",
            value=_q(jmb, 0.50),
            unit="J/MB",
            note_zh="通信实测：单位数据能耗（J/MB）中位数（用于校验 e_per_mb_J 量级）。",
            source=str(p_sm),
        )
        _append(
            rows,
            category="observed_smartphone_measurements",
            metric="observed_j_per_mb_p95",
            value=_q(jmb, 0.95),
            unit="J/MB",
            note_zh="通信实测：单位数据能耗（J/MB）95% 分位（用于界定最差链路/协议）。",
            source=str(p_sm),
        )
        _append(
            rows,
            category="observed_smartphone_measurements",
            metric="model_e_per_mb_wifi_good",
            value=e_wifi_good,
            unit="J/MB",
            note_zh="模型参数：Wi‑Fi（good signal）每 MB 能耗（用于和实测 J/MB 对照）。",
            source=str(Path(args.power)),
        )
        _append(
            rows,
            category="observed_smartphone_measurements",
            metric="model_e_per_mb_wifi_poor",
            value=e_wifi_poor,
            unit="J/MB",
            note_zh="模型参数：Wi‑Fi（poor signal）每 MB 能耗（弱信号惩罚后）。",
            source=str(Path(args.power)),
        )
    else:
        _append(
            rows,
            category="observed_smartphone_measurements",
            metric="missing",
            value=float("nan"),
            unit="-",
            note_zh="未找到 SmartphoneMeasurements 汇总，请先运行 validate_q2_smartphone_measurements.py。",
            source=str(p_sm),
        )

    # -----------------------------
    # C) user_behavior（长时间/TTE 粗对齐）
    # -----------------------------
    p_users = q2_reports / "validation_user_behavior" / "users.csv"
    p_scn = q2_reports / "validation_user_behavior" / "scenario_tte_pred.csv"
    if p_users.exists() and p_scn.exists():
        users = _read_csv(p_users)
        obs_tte = [_safe_float(r.get("tte_est_h", float("nan"))) for r in users]
        obs_tte = [x for x in obs_tte if np.isfinite(x) and x > 0]

        scn = _read_csv(p_scn)
        for r in scn:
            sid = str(r.get("scenario_id", "?"))
            t = _safe_float(r.get("tte_mean_h", float("nan")))
            if not np.isfinite(t) or not obs_tte:
                continue
            # 该场景 TTE 在观测分布中的经验分位数（越低表示“更重度/更极端”）
            pct = float(np.mean([1.0 if x <= t else 0.0 for x in obs_tte]) * 100.0)
            _append(
                rows,
                category="observed_user_behavior",
                metric=f"scenario_percentile_in_obs::{sid}",
                value=pct,
                unit="%",
                note_zh="场景 TTE 在观测分布中的经验分位数（用于解释场景强度是否落在合理范围）。",
                source=str(p_scn),
            )

        _append(
            rows,
            category="observed_user_behavior",
            metric="obs_tte_p05",
            value=_q(obs_tte, 0.05),
            unit="h",
            note_zh="观测：等效 TTE 的 5% 分位（最重度用户端）。",
            source=str(p_users),
        )
        _append(
            rows,
            category="observed_user_behavior",
            metric="obs_tte_p50",
            value=_q(obs_tte, 0.50),
            unit="h",
            note_zh="观测：等效 TTE 的中位数。",
            source=str(p_users),
        )
        _append(
            rows,
            category="observed_user_behavior",
            metric="obs_tte_p95",
            value=_q(obs_tte, 0.95),
            unit="h",
            note_zh="观测：等效 TTE 的 95% 分位（最轻度用户端）。",
            source=str(p_users),
        )
    else:
        _append(
            rows,
            category="observed_user_behavior",
            metric="missing",
            value=float("nan"),
            unit="-",
            note_zh="未找到 user_behavior 对照产物，请先运行 validate_q2_user_behavior.py。",
            source=str(p_users),
        )

    # -----------------------------
    # D) “更像 TTE 真值”的 proxy-current 链条
    # -----------------------------
    p_proxy = q2_reports / "validation_tte_proxy_current" / "tte_proxy_current.csv"
    if p_proxy.exists():
        rr = _read_csv(p_proxy)
        pct = [_safe_float(r.get("tte_model_over_proxy_pct", float("nan"))) for r in rr]
        pct = [x for x in pct if np.isfinite(x)]
        _append(
            rows,
            category="observed_tte_proxy_current",
            metric="tte_model_over_proxy_p50",
            value=_q(pct, 0.50),
            unit="%",
            note_zh="模型 TTE / 代理常流上界 的中位数（越接近 100% 越一致；低于 100% 说明欠压/阈值提前终止）。",
            source=str(p_proxy),
        )
        _append(
            rows,
            category="observed_tte_proxy_current",
            metric="tte_model_over_proxy_p05",
            value=_q(pct, 0.05),
            unit="%",
            note_zh="模型 TTE / 代理上界 的 5% 分位（用于观察最极端“提前关机”程度）。",
            source=str(p_proxy),
        )
    else:
        _append(
            rows,
            category="observed_tte_proxy_current",
            metric="missing",
            value=float("nan"),
            unit="-",
            note_zh="未找到 proxy-current 对照产物，请先运行 validate_q2_tte_proxy_current.py。",
            source=str(p_proxy),
        )

    # -----------------------------
    # E) 数值稳定性（dt sweep）
    # -----------------------------
    p_dt = q2_reports / "numerical_stability" / "dt_sweep_summary.csv"
    if p_dt.exists():
        dt = _read_csv(p_dt)
        # 取最大相对误差（%）和是否有状态变化
        rel = [_safe_float(r.get("max_abs_rel_tte_pct", float("nan"))) for r in dt]
        rel = [x for x in rel if np.isfinite(x)]
        rel_p95 = [_safe_float(r.get("p95_abs_rel_tte_pct", float("nan"))) for r in dt]
        rel_p95 = [x for x in rel_p95 if np.isfinite(x)]
        n_changed = [_safe_float(r.get("n_status_changed", float("nan"))) for r in dt]
        n_changed = [x for x in n_changed if np.isfinite(x)]
        _append(
            rows,
            category="numerical_stability",
            metric="dt_sweep_max_abs_rel_tte_pct",
            value=max(rel) if rel else float("nan"),
            unit="%",
            note_zh="dt 扫描：TTE 最大相对误差（越小越好）。",
            source=str(p_dt),
        )
        _append(
            rows,
            category="numerical_stability",
            metric="dt_sweep_p95_abs_rel_tte_pct",
            value=max(rel_p95) if rel_p95 else float("nan"),
            unit="%",
            note_zh="dt 扫描：TTE 误差的 95% 分位（越小越好）。",
            source=str(p_dt),
        )
        _append(
            rows,
            category="numerical_stability",
            metric="dt_sweep_max_status_changed",
            value=max(n_changed) if n_changed else float("nan"),
            unit="count",
            note_zh="dt 扫描：终止原因是否变化（0 表示稳定）。",
            source=str(p_dt),
        )
    else:
        _append(
            rows,
            category="numerical_stability",
            metric="missing",
            value=float("nan"),
            unit="-",
            note_zh="未找到 dt 稳定性报表，请先运行 run_q2_numerical_stability.py。",
            source=str(p_dt),
        )

    # 写出 diagnostics_summary.csv
    out_csv = out_dir / "diagnostics_summary.csv"
    _write_csv(out_csv, rows, fieldnames=["category", "metric", "value", "unit", "note_zh", "source"])

    # 写出 diagnostics_summary.md（极简：只给“好/差边界”的结论模板，具体数值在 csv）
    md_lines: list[str] = []
    md_lines.append("# Q2 诊断总表（模型好/差边界）\n")
    md_lines.append("本文件由脚本自动汇总：只读取 `out_reports/q2/` 下已有产物，不重新跑仿真。\n")
    md_lines.append("## 快速结论（供写 Q2：where the model performs well or poorly）\n")
    md_lines.append("- 短时功耗量级（AndroWatts）：以 `total_mape_pct` 与 `total_bias_pct` 判断“功耗量级是否可信”。\n")
    md_lines.append("- 通信能耗量级（SmartphoneMeasurements）：以观测 `J/MB` 的分位数对照模型 `e_per_mb_J`。\n")
    md_lines.append("- 长时间/TTE 粗对齐（user_behavior）：用“场景 TTE 在观测分布中的分位数”说明场景强度落点。\n")
    md_lines.append("- 代理 TTE 链条（I_obs 恒流上界）：若 `tte_model_over_proxy_pct` 明显 <100%，说明欠压/阈值导致提前终止。\n")
    md_lines.append("- 数值稳定性（dt sweep）：若 `dt_sweep_max_rel_tte_err_pct` 很小且 `n_status_changed=0`，说明数值设置稳健。\n")

    out_md = out_dir / "diagnostics_summary.md"
    out_md.write_text("".join(md_lines), encoding="utf-8")

    print("已生成：")
    print(f"- {out_csv}")
    print(f"- {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
