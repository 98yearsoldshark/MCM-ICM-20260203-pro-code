#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q2：构造“可对齐 TTE”的观测证据链（SmartphoneMeasurements：Monsoon+iPerf）。

思路（对齐赛题 Requirements 2 的 “Compare predictions to observed or plausible behavior”）：
- SmartphoneMeasurements 给出：在严格控制条件（全亮度、白底、无第三方后台）下，
  不同通信活动的实测平均功耗（Monsoon，约 3 分钟）。
- 我们把“平均功耗”视为稳态近似，从而得到一个可复现的 TTE 观测代理：
    TTE_obs_equiv = E_batt / P_obs_mean
  其中 E_batt 取我们模型的名义电池能量（由 phone_default_v3_aging.json 给出）。
- 然后构造与实验条件一致的“常值场景段”，用我们的连续时间模型仿真到耗尽：
    TTE_model = first-hitting time of {V_term<=V_cut, SOC<=SOC_min, Δ<0}
- 对比 TTE_model 与 TTE_obs_equiv（并输出误差/比值）。

注意：
- 这是“观测可复现 + 口径明确”的 TTE 层面对照，但仍是代理：
  Monsoon 实验不是整机放电到关机，而是短时平均功耗测量 + 能量换算。

输出：
- out_reports/q2/validation_tte_trace_smartphone_measurements/per_group_tte.csv
- out_plots/q2/{paper|study}/observed_tte_trace_smartphone_measurements/01_tte_compare.png
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.battery import BatteryParams3Aging
from mcm26a.observed.smartphone_measurements import load_smartphone_measurements_zip
from mcm26a.power import PowerParams0, PowerParams1Stateful, StatefulPowerModel1
from mcm26a.scenarios import Scenario, Segment
from mcm26a.sim import simulate_model3_aging
from mcm26a.viz.style import PlotMode, apply_style, ensure_dir, savefig


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _parse_test_meta(test: str) -> tuple[str, str, str]:
    """返回 (role, proto, link)。与 validate_q2_smartphone_measurements.py 保持一致。"""

    t = str(test)
    if t == "smartphoneBaseline":
        return ("baseline", "none", "none")
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
    return (role, proto, link)


def _make_constant_scenario(
    *,
    scenario_id: str,
    title_zh: str,
    duration_s: float,
    screen_on: bool,
    brightness_nits: float,
    screen_apl: float,
    activity: str,
    cpu_load: float,
    gpu_load: float,
    radio_mode: str,
    signal_quality: str,
    net_activity: str,
    net_throughput_MBps: float,
    gps_on: bool,
    background_level: str,
    ambient_temp_c: float,
) -> Scenario:
    seg = Segment(
        duration_s=float(duration_s),
        ambient_temp_c=float(ambient_temp_c),
        screen_on=bool(screen_on),
        brightness_nits=float(brightness_nits),
        activity=str(activity),
        cpu_load=float(cpu_load),
        gpu_load=float(gpu_load),
        radio_mode=str(radio_mode),
        signal_quality=str(signal_quality),
        net_activity=str(net_activity),
        gps_on=bool(gps_on),
        background_level=str(background_level),
        net_throughput_MBps=float(net_throughput_MBps),
        screen_apl=float(screen_apl),
    )
    return Scenario(
        scenario_id=str(scenario_id),
        title_zh=str(title_zh),
        description_zh="由 SmartphoneMeasurements 的实验条件构造：常值段重复直到耗尽（用于 TTE 对照）。",
        repeat=True,
        cycle_s=float(duration_s),
        schedule=(seg,),
    )


def _simulate_tte_for_scenario(
    sc: Scenario,
    *,
    power1: PowerParams1Stateful,
    batt: BatteryParams3Aging,
    dt_s: float,
    soc0: float,
    seeds: int,
    seed0: int,
) -> dict[str, object]:
    power0_dummy = PowerParams0.from_json(SRC_DIR / "configs" / "power_params_v0.json")

    ttes: list[float] = []
    avgp: list[float] = []
    status: dict[str, int] = {}
    for k in range(int(seeds)):
        pm = StatefulPowerModel1(power1, seed=int(seed0) + k)
        r = simulate_model3_aging(sc, power_params=power0_dummy, power_model=pm, battery_params=batt, soc0=float(soc0), dt_s=float(dt_s))
        if r.tte_h is not None:
            ttes.append(float(r.tte_h))
        if r.avg_power_W is not None and np.isfinite(float(r.avg_power_W)):
            avgp.append(float(r.avg_power_W))
        status[str(r.status)] = int(status.get(str(r.status), 0)) + 1

    out = {
        "tte_model_mean_h": float(np.mean(np.array(ttes, dtype=float))) if ttes else float("nan"),
        "tte_model_p05_h": float(np.quantile(np.array(ttes, dtype=float), 0.05)) if len(ttes) >= 2 else (float(ttes[0]) if ttes else float("nan")),
        "tte_model_p95_h": float(np.quantile(np.array(ttes, dtype=float), 0.95)) if len(ttes) >= 2 else (float(ttes[0]) if ttes else float("nan")),
        "avg_power_model_W": float(np.mean(np.array(avgp, dtype=float))) if avgp else float("nan"),
        "n": int(len(ttes)),
        "p_cutoff": float(status.get("cutoff", 0)) / float(max(1, seeds)),
        "p_soc_min": float(status.get("soc_min", 0)) / float(max(1, seeds)),
        "p_insufficient_power": float(status.get("insufficient_power", 0)) / float(max(1, seeds)),
    }
    return out


def _plot_compare(rows: list[dict[str, object]], *, mode: PlotMode, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    style = apply_style(mode)
    xs = np.array([float(r["tte_obs_equiv_h"]) for r in rows], dtype=float)
    ys = np.array([float(r["tte_model_mean_h"]) for r in rows], dtype=float)
    ylo = np.array([float(r.get("tte_model_p05_h", float("nan"))) for r in rows], dtype=float)
    yhi = np.array([float(r.get("tte_model_p95_h", float("nan"))) for r in rows], dtype=float)
    labels = [str(r.get("label", r.get("group_id", ""))) for r in rows]
    links = [str(r.get("link", "other")) for r in rows]
    protos = [str(r.get("proto", "other")) for r in rows]

    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    # 颜色=链路；点形状=协议（与 validate_q2_smartphone_measurements.py 保持一致的编码方式）
    color = {"router": "#4C78A8", "direct": "#F58518", "baseline": "#54A24B", "none": "#54A24B", "other": "#999999"}
    marker = {"tcp": "o", "udp": "s", "none": "*", "baseline": "*", "other": "x"}

    for lk in ["router", "direct", "baseline", "none", "other"]:
        for pr in ["tcp", "udp", "none", "baseline", "other"]:
            idx = [i for i in range(len(xs)) if links[i] == lk and protos[i] == pr]
            if not idx:
                continue
            ax.scatter(
                xs[idx],
                ys[idx],
                s=44 if pr in ("none", "baseline") else 36,
                alpha=0.82,
                color=color.get(lk, "#999999"),
                marker=marker.get(pr, "o"),
                edgecolors="white",
                linewidths=0.6,
            )
            # 误差棒（模型侧 5%~95%），只在 paper 里淡化显示，避免太“学术图”挤满
            if pr not in ("none", "baseline") and np.isfinite(ylo[idx]).all() and np.isfinite(yhi[idx]).all():
                yerr = np.vstack([ys[idx] - ylo[idx], yhi[idx] - ys[idx]])
                ax.errorbar(xs[idx], ys[idx], yerr=yerr, fmt="none", ecolor=color.get(lk, "#999999"), alpha=0.25, lw=0.8)

    lo = float(np.nanmin(np.concatenate([xs, ys]))) if xs.size and ys.size else 0.0
    hi = float(np.nanmax(np.concatenate([xs, ys]))) if xs.size and ys.size else 1.0
    lo = max(0.0, lo * 0.95)
    hi = hi * 1.05
    ax.plot([lo, hi], [lo, hi], color="#333333", lw=1.2, linestyle="--", alpha=0.75)

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("观测 TTE（代理）：E_batt / P_obs_mean（小时）")
    ax.set_ylabel("模型 TTE（首次终止）：TTE_model（小时）")
    ax.set_title(f"Q2：TTE 层面对照（SmartphoneMeasurements）{style.title_suffix}")
    ax.grid(True, alpha=0.25)

    if style.annotate:
        for x, y, lab in zip(xs.tolist(), ys.tolist(), labels):
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            ax.text(x, y, lab, fontsize=8, ha="left", va="bottom", alpha=0.9)
        # 图例：颜色=链路、点形状=协议
        link_map_zh = {"router": "Wi‑Fi（路由器）", "direct": "Wi‑Fi Direct（直连）", "none": "Baseline", "baseline": "Baseline", "other": "其它"}
        proto_map_zh = {"tcp": "TCP", "udp": "UDP", "none": "Baseline", "baseline": "Baseline", "other": "其它"}
        import matplotlib.pyplot as _plt

        link_handles = [
            _plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=color[k], markersize=8, markeredgecolor="white")
            for k in ["router", "direct", "none"]
        ]
        leg1 = ax.legend(link_handles, [link_map_zh[k] for k in ["router", "direct", "none"]], frameon=False, loc="upper left", title="链路", title_fontsize=10)
        ax.add_artist(leg1)
        proto_handles = [
            _plt.Line2D([0], [0], marker=marker[k], color="none", markerfacecolor="#666666", markersize=8, markeredgecolor="white")
            for k in ["tcp", "udp"]
        ]
        ax.legend(proto_handles, [proto_map_zh[k] for k in ["tcp", "udp"]], frameon=False, loc="lower right", title="协议", title_fontsize=10)
        fig.tight_layout(rect=(0.0, 0.20, 1.0, 0.98))
        fig.text(
            0.02,
            0.02,
            "说明：观测侧来自 Monsoon 的短时平均功耗；我们用名义电池能量 E_batt 将其换算为等效 TTE。\n"
            "模型侧为连续时间仿真到首次终止（欠压/电量下限/不可供电）。因此若模型考虑欠压提前关机，可能出现 TTE_model < TTE_obs_equiv。",
            ha="left",
            va="bottom",
            fontsize=9,
        )
    else:
        fig.tight_layout()

    savefig(fig, out_path, mode=mode)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="MCM 2026 A - Q2 TTE trace proxy（SmartphoneMeasurements）")
    ap.add_argument(
        "--zip",
        default=str(SRC_DIR.parent / "data" / "SmartphoneMeasurements" / "SmartphoneMeasurements.zip"),
        help="SmartphoneMeasurements.zip 路径",
    )
    ap.add_argument("--out-reports", default=str(SRC_DIR / "out_reports" / "q2" / "validation_tte_trace_smartphone_measurements"))
    ap.add_argument("--out-plots", default=str(SRC_DIR / "out_plots" / "q2"))
    ap.add_argument("--mode", default="", help="paper 或 study；留空则两种模式都生成")
    ap.add_argument(
        "--power",
        default=str(SRC_DIR / "configs" / "power_params_v2_no7_awcal_mo_v2.json"),
        help="功耗参数 JSON（stateful）",
    )
    ap.add_argument(
        "--phone",
        default=str(SRC_DIR / "configs" / "phone_default_v3_aging.json"),
        help="电池参数 JSON（用于 E_batt 与仿真）",
    )
    ap.add_argument("--dt", type=float, default=10.0, help="仿真 dt（秒）")
    ap.add_argument("--soc0", type=float, default=1.0, help="初始 SOC0（默认 1.0）")
    ap.add_argument("--seeds", type=int, default=10, help="模型重复次数（不同随机种子）")
    ap.add_argument("--seed0", type=int, default=1, help="随机种子起点")
    ap.add_argument(
        "--granularity",
        default="group",
        choices=["group", "test"],
        help="输出粒度：group（少量代表性组，默认）或 test（每个 phone×test 一点，更适合终稿）",
    )
    ap.add_argument(
        "--wifi-e-per-mb-j",
        type=float,
        default=None,
        help="覆盖功耗参数 rrc.e_per_mb_J[wifi]（用于检验/校准网络能耗量级；不修改配置文件）",
    )

    # 场景映射参数（按 SmartphoneMeasurements README：全亮度/白底）
    ap.add_argument("--brightness-nits", type=float, default=500.0, help="实验条件：全亮度（以 nits 表示）")
    ap.add_argument("--screen-apl", type=float, default=1.0, help="实验条件：白底（APL≈1）")
    ap.add_argument(
        "--cpu-load-mode",
        default="linear",
        choices=["constant", "linear"],
        help="CPU 负载映射：constant（常数）或 linear（随吞吐线性增大，clamp 到 0~1）",
    )
    ap.add_argument("--cpu-load", type=float, default=0.25, help="constant 模式下的 CPU 负载（0~1）")
    ap.add_argument("--cpu-load-baseline", type=float, default=0.05, help="baseline（无吞吐）时的 CPU 负载（0~1）")
    ap.add_argument("--cpu-load-a", type=float, default=0.18, help="linear 模式：cpu_load = a + b*throughput_MBps")
    ap.add_argument("--cpu-load-b", type=float, default=0.03, help="linear 模式：cpu_load = a + b*throughput_MBps")
    ap.add_argument("--activity", default="video", help="场景 activity 标签（影响屏幕 APL 缺省/网络 burst 等；这里显式给 APL）")
    args = ap.parse_args()

    out_reports = ensure_dir(Path(args.out_reports))

    power1 = PowerParams1Stateful.from_json(Path(args.power))
    if args.wifi_e_per_mb_j is not None and np.isfinite(float(args.wifi_e_per_mb_j)) and float(args.wifi_e_per_mb_j) > 0:
        # 仅用于本次对照实验，不修改配置文件
        power1.rrc.e_per_mb_J["wifi"] = float(args.wifi_e_per_mb_j)
    batt = BatteryParams3Aging.from_json(Path(args.phone))
    # 使用名义电压换算能量（与 validate_q2_smartphone_measurements.py 保持一致口径）
    nominal_v = 3.7
    e_batt_Wh = float(batt.capacity_Ah_ref) * float(nominal_v)

    monsoon, iperf = load_smartphone_measurements_zip(Path(args.zip))
    ip_map = {(i.phone, i.test): i for i in iperf}

    # 汇总：只挑 WiFi/WiFiDirect（iPerf 有吞吐），并保留 baseline
    rows_raw: list[dict[str, object]] = []
    for m in monsoon:
        role, proto, link = _parse_test_meta(m.test)
        thr_mbps = float("nan")
        thr_MBps = float("nan")
        if (m.phone, m.test) in ip_map:
            thr_mbps = float(ip_map[(m.phone, m.test)].mean_mbps)
            thr_MBps = thr_mbps / 8.0
        rows_raw.append(
            {
                "phone": m.phone,
                "test": m.test,
                "role": role,
                "proto": proto,
                "link": link,
                "mean_power_W": float(m.mean_power_W),
                "throughput_mbps": float(thr_mbps),
                "throughput_MBps": float(thr_MBps),
            }
        )

    def _cpu_load_for(thr_MBps: float, *, is_baseline: bool) -> float:
        if is_baseline:
            return float(args.cpu_load_baseline)
        if str(args.cpu_load_mode) == "constant":
            return float(args.cpu_load)
        if not np.isfinite(thr_MBps) or thr_MBps <= 0:
            return float(args.cpu_load)
        v = float(args.cpu_load_a) + float(args.cpu_load_b) * float(thr_MBps)
        return float(min(1.0, max(0.0, v)))

    out_rows: list[dict[str, object]] = []

    if str(args.granularity) == "group":
        # 聚合到 group：baseline + (direct/router,tcp/udp,client/server)
        groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
        for r in rows_raw:
            role = str(r["role"])
            proto = str(r["proto"])
            link = str(r["link"])
            if role == "baseline":
                groups.setdefault(("baseline", "none", "none"), []).append(r)
                continue
            # 只保留 iPerf 相关（有吞吐）
            thr = float(r.get("throughput_MBps", float("nan")))
            if not np.isfinite(thr) or thr <= 0:
                continue
            if link not in ("router", "direct") or proto not in ("tcp", "udp") or role not in ("client", "server"):
                continue
            groups.setdefault((link, proto, role), []).append(r)

        # 少量代表性组（避免报表太长）：baseline + 3 个 iPerf 组
        pick = [
            ("baseline", "none", "none"),
            ("router", "tcp", "client"),
            ("direct", "tcp", "client"),
            ("router", "udp", "client"),
        ]

        for link, proto, role in pick:
            xs = groups.get((link, proto, role), [])
            if not xs:
                continue
            p_obs = np.array([float(r["mean_power_W"]) for r in xs], dtype=float)
            p_obs = p_obs[np.isfinite(p_obs)]
            thr = np.array([float(r.get("throughput_MBps", float("nan"))) for r in xs], dtype=float)
            thr = thr[np.isfinite(thr) & (thr > 0)]

            p_obs_mean = float(np.mean(p_obs)) if p_obs.size else float("nan")
            thr_med = float(np.median(thr)) if thr.size else float("nan")

            tte_obs = float("nan")
            if np.isfinite(p_obs_mean) and p_obs_mean > 1e-9:
                tte_obs = float(e_batt_Wh / p_obs_mean)

            cpu_load = _cpu_load_for(thr_med, is_baseline=(link == "baseline"))

            sc = _make_constant_scenario(
                scenario_id=f"SM_{link}_{proto}_{role}",
                title_zh=f"SmartphoneMeasurements：{link}/{proto}/{role}",
                duration_s=180.0,
                screen_on=True,
                brightness_nits=float(args.brightness_nits),
                screen_apl=float(args.screen_apl),
                activity=str(args.activity),
                cpu_load=float(cpu_load),
                gpu_load=0.0,
                radio_mode="wifi",
                signal_quality="good",
                net_activity=("idle" if link == "baseline" else "download"),
                net_throughput_MBps=(float("nan") if link == "baseline" else float(thr_med)),
                gps_on=False,
                background_level="low",
                ambient_temp_c=25.0,
            )

            sim = _simulate_tte_for_scenario(
                sc,
                power1=power1,
                batt=batt,
                dt_s=float(args.dt),
                soc0=float(args.soc0),
                seeds=int(args.seeds),
                seed0=int(args.seed0),
            )

            row = {
                "group_id": f"{link}/{proto}/{role}",
                "label": f"{link}/{proto}/{role}",
                "link": link,
                "proto": proto,
                "role": role,
                "obs_mean_power_W": float(p_obs_mean),
                "obs_throughput_MBps": float(thr_med) if np.isfinite(thr_med) else float("nan"),
                "E_batt_Wh_assumed": float(e_batt_Wh),
                "tte_obs_equiv_h": float(tte_obs) if np.isfinite(tte_obs) else float("nan"),
                "cpu_load_used": float(cpu_load),
            }
            row.update(sim)
            out_rows.append(row)

        out_csv = out_reports / "per_group_tte.csv"
        _write_csv(out_csv, out_rows, fieldnames=list(out_rows[0].keys()) if out_rows else [])

        modes = ["paper", "study"] if not args.mode else [str(args.mode)]
        for m in modes:
            out_plots = ensure_dir(Path(args.out_plots) / str(m) / "observed_tte_trace_smartphone_measurements")
            _plot_compare(out_rows, mode=m, out_path=out_plots / "01_tte_compare.png")  # type: ignore[arg-type]

        print("已生成：")
        print(f"- {out_csv}")
        print(f"- {Path(args.out_plots) / 'paper' / 'observed_tte_trace_smartphone_measurements' / '01_tte_compare.png'}")
        print(f"- {Path(args.out_plots) / 'study' / 'observed_tte_trace_smartphone_measurements' / '01_tte_compare.png'}")
        return 0

    # granularity=test：每个 phone×test 一点（更强的终稿口径）
    for r in rows_raw:
        role = str(r["role"])
        proto = str(r["proto"])
        link = str(r["link"])
        is_baseline = role == "baseline"
        thr = float(r.get("throughput_MBps", float("nan")))
        if (not is_baseline) and (not np.isfinite(thr) or thr <= 0):
            continue
        if (not is_baseline) and (link not in ("router", "direct") or proto not in ("tcp", "udp")):
            continue

        p_obs = float(r.get("mean_power_W", float("nan")))
        if not np.isfinite(p_obs) or p_obs <= 0:
            continue

        tte_obs = float(e_batt_Wh / p_obs) if p_obs > 1e-9 else float("nan")
        cpu_load = _cpu_load_for(thr, is_baseline=is_baseline)

        sc = _make_constant_scenario(
            scenario_id=f"SM_{link}_{proto}_{role}",
            title_zh=f"SmartphoneMeasurements：{link}/{proto}/{role}",
            duration_s=180.0,
            screen_on=True,
            brightness_nits=float(args.brightness_nits),
            screen_apl=float(args.screen_apl),
            activity=str(args.activity),
            cpu_load=float(cpu_load),
            gpu_load=0.0,
            radio_mode="wifi",
            signal_quality="good",
            net_activity=("idle" if is_baseline else "download"),
            net_throughput_MBps=(float("nan") if is_baseline else float(thr)),
            gps_on=False,
            background_level="low",
            ambient_temp_c=25.0,
        )

        sim = _simulate_tte_for_scenario(
            sc,
            power1=power1,
            batt=batt,
            dt_s=float(args.dt),
            soc0=float(args.soc0),
            seeds=int(args.seeds),
            seed0=int(args.seed0),
        )

        phone = str(r.get("phone", ""))
        test = str(r.get("test", ""))
        label = f"{phone}:{test}"

        row = {
            "phone": phone,
            "test": test,
            "group_id": f"{link}/{proto}/{role}",
            "label": label,
            "link": link,
            "proto": proto if not is_baseline else "none",
            "role": role,
            "obs_mean_power_W": float(p_obs),
            "obs_throughput_MBps": float(thr) if np.isfinite(thr) else float("nan"),
            "E_batt_Wh_assumed": float(e_batt_Wh),
            "tte_obs_equiv_h": float(tte_obs) if np.isfinite(tte_obs) else float("nan"),
            "cpu_load_used": float(cpu_load),
        }
        row.update(sim)
        out_rows.append(row)

    out_csv = out_reports / "per_test_tte.csv"
    _write_csv(out_csv, out_rows, fieldnames=list(out_rows[0].keys()) if out_rows else [])

    modes = ["paper", "study"] if not args.mode else [str(args.mode)]
    for m in modes:
        out_plots = ensure_dir(Path(args.out_plots) / str(m) / "observed_tte_trace_smartphone_measurements")
        _plot_compare(out_rows, mode=m, out_path=out_plots / "02_tte_compare_per_test.png")  # type: ignore[arg-type]

    print("已生成：")
    print(f"- {out_csv}")
    print(f"- {Path(args.out_plots) / 'paper' / 'observed_tte_trace_smartphone_measurements' / '02_tte_compare_per_test.png'}")
    print(f"- {Path(args.out_plots) / 'study' / 'observed_tte_trace_smartphone_measurements' / '02_tte_compare_per_test.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
