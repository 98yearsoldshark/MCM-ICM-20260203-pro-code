#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2 观测对照（通信功耗/吞吐）：解析 SmartphoneMeasurements.zip（Monsoon + iPerf）。

输出：
- out_reports/q2/validation_smartphone_measurements/
  - per_test.csv：每个 phone×test 的平均功耗、吞吐、单位数据能耗（J/MB）与等效 TTE（小时）
  - summary_by_group.csv：按（direct/router、tcp/udp、client/server）聚合统计
- out_plots/q2/{paper|study}/observed_smartphone_measurements/
  - 01_delta_power_vs_throughput.png：吞吐 vs 额外功耗（相对 baseline）
  - 02_energy_per_mb_box.png：单位数据能耗（J/MB）对比（Direct vs Router）

说明：
- 该数据集实验时长约 3 分钟；我们把其“平均功耗”当作若该活动持续进行的稳态近似。
- 本脚本不依赖 xlsx（蓝牙/LTE 吞吐表），只使用 iPerf 的 txt（WiFi/WiFi Direct 相关）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.smartphone_measurements import IperfSummary, MonsoonSummary, load_smartphone_measurements_zip
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


@dataclass(frozen=True)
class _TestMeta:
    role: str  # client/server/other
    proto: str  # tcp/udp/other
    link: str  # direct/router/other


def _parse_test_name(test: str) -> _TestMeta:
    t = str(test)
    if t == "smartphoneBaseline":
        return _TestMeta(role="baseline", proto="none", link="none")
    if "Client" in t:
        role = "client"
    elif "Server" in t:
        role = "server"
    else:
        role = "other"

    if "Tcp" in t or "TCP" in t:
        proto = "tcp"
    elif "Udp" in t or "UDP" in t:
        proto = "udp"
    else:
        proto = "other"

    if "Direct" in t:
        link = "direct"
    elif "Router" in t:
        link = "router"
    else:
        link = "other"

    return _TestMeta(role=role, proto=proto, link=link)


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _plot_delta_power_scatter(rows: list[dict[str, object]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    xs = np.array([float(r.get("throughput_mbps", float("nan"))) for r in rows], dtype=float)
    ys = np.array([float(r.get("delta_power_w", float("nan"))) for r in rows], dtype=float)
    links = [str(r.get("link", "other")) for r in rows]
    protos = [str(r.get("proto", "other")) for r in rows]

    m = np.isfinite(xs) & np.isfinite(ys) & (xs > 0)
    xs = xs[m]
    ys = ys[m]
    links = [links[i] for i, ok in enumerate(m.tolist()) if ok]
    protos = [protos[i] for i, ok in enumerate(m.tolist()) if ok]

    fig, ax = plt.subplots(figsize=(9.6, 4.8))

    color = {"router": "#4C78A8", "direct": "#F58518", "other": "#54A24B"}
    marker = {"tcp": "o", "udp": "s", "other": "x"}

    # 分组绘制（更清爽，也便于做图例）
    links_u = ["router", "direct", "other"]
    protos_u = ["tcp", "udp"]
    for lk in links_u:
        for pr in protos_u:
            idx = [i for i in range(len(xs)) if links[i] == lk and protos[i] == pr]
            if not idx:
                continue
            ax.scatter(
                xs[idx],
                ys[idx],
                s=36,
                alpha=0.78,
                color=color.get(lk, "#999999"),
                marker=marker.get(pr, "o"),
                edgecolors="white",
                linewidths=0.6,
            )
    # 兜底：proto/label 解析失败的点
    idx_other = [i for i in range(len(xs)) if protos[i] not in protos_u]
    if idx_other:
        ax.scatter(
            xs[idx_other],
            ys[idx_other],
            s=32,
            alpha=0.60,
            color="#999999",
            marker=marker["other"],
        )

    ax.set_xlabel("吞吐（Mbps，iPerf）")
    ax.set_ylabel("额外功耗 ΔP（W，相对 Baseline）")
    ax.set_title(f"通信实测：吞吐 vs 额外功耗（Monsoon+iPerf）{style.title_suffix}")
    ax.grid(True, alpha=0.25)

    # 两套图例：颜色=链路，形状=协议（避免在一个 legend 里“看不懂编码”）
    link_map_zh = {"router": "Wi‑Fi（路由器）", "direct": "Wi‑Fi Direct（直连）", "other": "其它/未知"}
    link_handles = [plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=color[k], markersize=8) for k in links_u]
    leg1 = ax.legend(link_handles, [link_map_zh[k] for k in links_u], frameon=False, loc="upper left", title="链路类型", title_fontsize=10)
    ax.add_artist(leg1)

    proto_map_zh = {"tcp": "TCP", "udp": "UDP"}
    proto_handles = [plt.Line2D([0], [0], marker=marker[k], color="#333333", markerfacecolor="#333333", markersize=7, linestyle="none") for k in protos_u]
    ax.legend(proto_handles, [proto_map_zh[k] for k in protos_u], frameon=False, loc="lower right", title="协议", title_fontsize=10)

    # 学习版：给出每类链路的“趋势拟合线”（仅用于观察量级与趋势，不把它当成机理模型）
    if style.annotate:
        for lk in ["router", "direct"]:
            idx = [i for i in range(len(xs)) if links[i] == lk and protos[i] in protos_u]
            if len(idx) < 3:
                continue
            x = np.array(xs[idx], dtype=float)
            y = np.array(ys[idx], dtype=float)
            A = np.column_stack([np.ones_like(x), x])
            b0, b1 = np.linalg.lstsq(A, y, rcond=None)[0].tolist()
            xx = np.linspace(float(np.min(x)), float(np.max(x)), 100)
            yy = b0 + b1 * xx
            ax.plot(xx, yy, color=color.get(lk, "#999999"), lw=1.4, alpha=0.65, linestyle="--")

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：颜色表示链路（路由器 Wi‑Fi / Wi‑Fi Direct），点形状表示协议（TCP/UDP）。\n"
            "ΔP 以同机型 Baseline 的平均功耗为参照，用于剔除机型/屏幕等固定差异，聚焦通信活动的增量耗电。\n"
            "虚线为分组最小二乘拟合，仅用于展示趋势（不作为机理模型假设）。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def _plot_energy_per_mb_box(rows: list[dict[str, object]], *, mode: PlotMode):
    import matplotlib.pyplot as plt

    style = apply_style(mode)

    by_link: dict[str, list[float]] = {"router": [], "direct": [], "other": []}
    for r in rows:
        try:
            e = float(r.get("energy_per_mb_j", float("nan")))
        except Exception:
            continue
        if not np.isfinite(e) or e <= 0:
            continue
        by_link.setdefault(str(r.get("link", "other")), []).append(float(e))

    labels = ["router", "direct"]
    data = [by_link.get(k, []) for k in labels]
    if not any(data):
        raise ValueError("没有可用 energy_per_mb_j（请检查 iPerf 日志是否匹配）")

    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    # matplotlib>=3.9: labels->tick_labels；为兼容旧版本做 try/except
    try:
        ax.boxplot(data, tick_labels=["WiFi（Router）", "WiFi Direct"], showfliers=False)
    except TypeError:
        ax.boxplot(data, labels=["WiFi（Router）", "WiFi Direct"], showfliers=False)
    ax.set_ylabel("单位数据能耗（J/MB）")
    ax.set_title(f"通信实测：单位数据能耗对比{style.title_suffix}")
    ax.grid(True, axis="y", alpha=0.25)

    if style.annotate:
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：单位数据能耗 e≈ΔP/(吞吐 MB/s)。\n"
            "该指标可用于校验模型中的“e_per_mb_J”量级，并解释为何某些网络模式更耗电。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()
    return fig


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 通信观测对照（SmartphoneMeasurements）")
    ap.add_argument(
        "--zip",
        default=str(SRC_DIR.parent / "data" / "SmartphoneMeasurements" / "SmartphoneMeasurements.zip"),
        help="SmartphoneMeasurements.zip 路径",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON 路径（用于等效 TTE 换算）",
    )
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "validation_smartphone_measurements"))
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"))
    ap.add_argument("--mode", default="paper", help="paper 或 study")
    ap.add_argument("--nominal-v", type=float, default=3.7, help="等效能量换算用的标称电压（V）")
    args = ap.parse_args()

    mode: PlotMode = str(args.mode)
    out_reports = ensure_dir(Path(args.out_reports))
    out_plots = ensure_dir(Path(args.out_plots) / str(mode) / "observed_smartphone_measurements")

    batt = BatteryParams3Aging.from_json(Path(args.phone))
    energy_Wh = float(batt.capacity_Ah_ref) * float(args.nominal_v)

    monsoon, iperf = load_smartphone_measurements_zip(Path(args.zip))
    iperf_map: dict[tuple[str, str], IperfSummary] = {(i.phone, i.test): i for i in iperf}

    baseline_power: dict[str, float] = {}
    for m in monsoon:
        if m.test == "smartphoneBaseline" and np.isfinite(m.mean_power_W):
            baseline_power[m.phone] = float(m.mean_power_W)

    rows: list[dict[str, object]] = []
    for m in monsoon:
        base = float(baseline_power.get(m.phone, float("nan")))
        meta = _parse_test_name(m.test)
        ip = iperf_map.get((m.phone, m.test))
        thr_mbps = float(ip.mean_mbps) if ip is not None else float("nan")
        thr_MBps = float("nan") if (not np.isfinite(thr_mbps)) else float(thr_mbps / 8.0)
        dp = float("nan") if (not np.isfinite(base)) else float(m.mean_power_W - base)
        e_per_mb = float("nan")
        if np.isfinite(dp) and np.isfinite(thr_MBps) and thr_MBps > 1e-9:
            e_per_mb = float(dp / thr_MBps)

        tte_h = float("nan") if (not np.isfinite(m.mean_power_W) or m.mean_power_W <= 0) else float(energy_Wh / m.mean_power_W)

        rows.append(
            {
                "phone": m.phone,
                "test": m.test,
                "role": meta.role,
                "proto": meta.proto,
                "link": meta.link,
                "mean_power_w": float(m.mean_power_W),
                "baseline_power_w": base,
                "delta_power_w": dp,
                "throughput_mbps": thr_mbps,
                "throughput_MBps": thr_MBps,
                "energy_per_mb_j": e_per_mb,
                "duration_s": float(m.duration_s),
                "tte_equiv_h": tte_h,
            }
        )

    _write_csv(
        out_reports / "per_test.csv",
        rows,
        fieldnames=[
            "phone",
            "test",
            "role",
            "proto",
            "link",
            "mean_power_w",
            "baseline_power_w",
            "delta_power_w",
            "throughput_mbps",
            "throughput_MBps",
            "energy_per_mb_j",
            "duration_s",
            "tte_equiv_h",
        ],
    )

    # 聚合统计：按 link/proto/role
    by_group: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        e = float(r.get("energy_per_mb_j", float("nan")))
        if not np.isfinite(e) or e <= 0:
            continue
        k = (str(r.get("link", "other")), str(r.get("proto", "other")), str(r.get("role", "other")))
        by_group.setdefault(k, []).append(e)

    summary = []
    for (link, proto, role), xs in sorted(by_group.items()):
        summary.append(
            {
                "link": link,
                "proto": proto,
                "role": role,
                "n": int(len(xs)),
                "mean_j_per_mb": float(np.mean(np.array(xs, dtype=float))) if xs else float("nan"),
                "p05_j_per_mb": float(np.quantile(np.array(xs, dtype=float), 0.05)) if xs else float("nan"),
                "p50_j_per_mb": float(np.quantile(np.array(xs, dtype=float), 0.50)) if xs else float("nan"),
                "p95_j_per_mb": float(np.quantile(np.array(xs, dtype=float), 0.95)) if xs else float("nan"),
            }
        )
    _write_csv(out_reports / "summary_by_group.csv", summary, fieldnames=["link", "proto", "role", "n", "mean_j_per_mb", "p05_j_per_mb", "p50_j_per_mb", "p95_j_per_mb"])

    # 画图（只针对有吞吐的样本）
    rows_with_thr = [r for r in rows if np.isfinite(float(r.get("throughput_mbps", float("nan"))))]

    fig1 = _plot_delta_power_scatter(rows_with_thr, mode=mode)
    savefig(fig1, out_plots / "01_delta_power_vs_throughput.png", mode=mode)
    import matplotlib.pyplot as plt

    plt.close(fig1)

    fig2 = _plot_energy_per_mb_box(rows_with_thr, mode=mode)
    savefig(fig2, out_plots / "02_energy_per_mb_box.png", mode=mode)
    plt.close(fig2)

    print("Q2 SmartphoneMeasurements 对照已生成：")
    print(f"- reports: {out_reports}")
    print(f"- plots:   {out_plots}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
