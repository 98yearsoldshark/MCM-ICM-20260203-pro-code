#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总参量估计结果到一张表（csv+md）。

输入：各子目录下的 `fit_results.csv`（由 01/02/03/04/05 脚本生成）
输出：
- `.../参量估计/参数估计汇总表.csv`
- `.../参量估计/参数估计汇总表.md`
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR, write_csv, write_text


def _p(path: Path) -> str:
    return str(path).replace(str(PROJECT_DIR), "MCM_Sim/26A")


def _p_str(s: str) -> str:
    s = str(s or "")
    return s.replace(str(PROJECT_DIR), "MCM_Sim/26A")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    root = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计"

    # 01 屏幕
    df01 = _read_csv(root / "01-亮度-屏幕功耗" / "fit_results.csv")
    row01 = df01[df01["model"] == "linear_brightness"].head(1)

    # 02 CPU/GPU
    df02 = _read_csv(root / "02-负载-CPU_GPU功耗" / "fit_results.csv")
    row02_cpu = df02[(df02["component"] == "CPU") & (df02["model"] == "linear_through_origin")].head(1)
    row02_gpu = df02[(df02["component"] == "GPU") & (df02["model"] == "linear_through_origin")].head(1)

    # 03 tail（AndroWatts 能量守恒反推：单一 τ_est）
    df03 = _read_csv(root / "03-网络回落曲线" / "fit_results.csv")
    row03 = df03[df03["model"] == "energy_balance_with_tail"].head(1)

    # 04 吞吐-功耗（作为“交叉验证”保留，不作为主口径的网络参数来源）
    df04 = _read_csv(root / "04-吞吐-功耗关系" / "fit_results.csv")
    row04 = df04[df04["model"] == "linear_wifi_throughput"].head(1)

    # 05 热参数
    df05 = _read_csv(root / "05-温度-时间曲线" / "fit_results.csv")
    row05 = df05[df05["model"] == "first_order_thermal_from_deltaT"].head(1)

    out_rows: list[dict[str, object]] = []

    # --- Screen（Model-0/1 都会用到）
    if not row01.empty:
        r = row01.iloc[0].to_dict()
        out_rows += [
            {
                "parameter_key": "power.screen.P0_W",
                "symbol": "P0,screen",
                "value": float(r["P0_W"]),
                "unit": "W",
                "source_fit": "01-亮度-屏幕功耗/fit_results.csv (linear_brightness)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "Model-0/1 屏幕亮度项截距（屏幕点亮时的基准功耗）",
            },
            {
                "parameter_key": "power.screen.k_W_per_nit",
                "symbol": "k_screen",
                "value": float(r["k_W_per_nit"]),
                "unit": "W/nit",
                "source_fit": "01-亮度-屏幕功耗/fit_results.csv (linear_brightness)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "Model-0/1 屏幕亮度线性系数（nits->W）",
            },
        ]

    # --- CPU/GPU（Model-0 直接用；Model-1 可作为 k 的初值/量级）
    if not row02_cpu.empty:
        r = row02_cpu.iloc[0].to_dict()
        out_rows.append(
            {
                "parameter_key": "power.cpu.k_W",
                "symbol": "k_cpu",
                "value": float(r["k_W"]),
                "unit": "W",
                "source_fit": "02-负载-CPU_GPU功耗/fit_results.csv (CPU linear_through_origin)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "CPU 负载功耗系数（P=k*load）",
            }
        )
    if not row02_gpu.empty:
        r = row02_gpu.iloc[0].to_dict()
        out_rows.append(
            {
                "parameter_key": "power.gpu.k_W",
                "symbol": "k_gpu",
                "value": float(r["k_W"]),
                "unit": "W",
                "source_fit": "02-负载-CPU_GPU功耗/fit_results.csv (GPU linear_through_origin)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "GPU 负载功耗系数（P=k*load）",
            }
        )

    # --- Network（Wi-Fi：主口径来自 03 的能量模型；04 作为交叉验证写进 notes）
    if not row03.empty:
        r = row03.iloc[0].to_dict()
        e_alt = None
        p_idle_alt = None
        if not row04.empty:
            r4 = row04.iloc[0].to_dict()
            e_alt = float(r4.get("e_per_mb_J", float("nan")))
            p_idle_alt = float(r4.get("P_idle_W", float("nan")))

        note_extra = ""
        if e_alt is not None and np.isfinite(e_alt) and p_idle_alt is not None and np.isfinite(p_idle_alt):
            note_extra = f"（交叉验证：功率回归得到 P_idle≈{p_idle_alt:.3f}W, e≈{e_alt:.3f}J/MB）"

        out_rows += [
            {
                "parameter_key": "power.rrc.p_idle_W (wifi)",
                "symbol": "P_idle,wifi",
                "value": float(r["P_idle_W"]),
                "unit": "W",
                "source_fit": "03-网络回落曲线/fit_results.csv (energy_balance_with_tail)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "Wi-Fi 维持功耗（能量守恒估计）" + note_extra,
            },
            {
                "parameter_key": "power.rrc.e_per_mb_J (wifi)",
                "symbol": "e_wifi",
                "value": float(r["e_per_mb_J"]),
                "unit": "J/MB",
                "source_fit": "03-网络回落曲线/fit_results.csv (energy_balance_with_tail)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "Wi-Fi 每 MB 传输能耗（能量守恒估计）" + note_extra,
            },
            {
                "parameter_key": "power.rrc.E_tail_J (wifi)",
                "symbol": "E_tail",
                "value": float(r["E_tail_J"]),
                "unit": "J",
                "source_fit": "03-网络回落曲线/fit_results.csv (energy_balance_with_tail)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "尾态/连接维护等常量能量开销（用于解释短时测试的平均功耗抬升）",
            },
        ]

    # --- Network tail（主结果：基于 AndroWatts 的能量反推）
    if not row03.empty:
        r = row03.iloc[0].to_dict()
        out_rows.append(
            {
                "parameter_key": "power.rrc.tau_tail_s (wifi)",
                "symbol": "tau_tail",
                "value": float(r["tau_tail_s_est"]),
                "unit": "s",
                "source_fit": "03-网络回落曲线/fit_results.csv (energy_balance_with_tail)",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "网络尾态等效时间常数：τ=E_tail/(P_conn-P_idle)",
            }
        )

    # --- Thermal（Model-2）
    if not row05.empty:
        r = row05.iloc[0].to_dict()
        out_rows += [
            {
                "parameter_key": "battery.thermal.R_th_K_per_W",
                "symbol": "R_th",
                "value": float(r["R_th_K_per_W_est"]),
                "unit": "K/W",
                "source_fit": "05-温度-时间曲线/fit_results.csv",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "由温升反推（需假设 eta_device_heat）；用于 Model-2 集总热模型",
            },
            {
                "parameter_key": "battery.thermal.C_th_J_per_K",
                "symbol": "C_th",
                "value": float(r["C_th_J_per_K_est"]),
                "unit": "J/K",
                "source_fit": "05-温度-时间曲线/fit_results.csv",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "由 τ=R_th*C_th 得到；用于 Model-2 集总热模型",
            },
            {
                "parameter_key": "battery.thermal.tau_s",
                "symbol": "tau",
                "value": float(r["tau_s"]),
                "unit": "s",
                "source_fit": "05-温度-时间曲线/fit_results.csv",
                "data_source": _p_str(str(r.get("data_source", ""))),
                "notes": "热时间常数（直接拟合得到）",
            },
        ]

    # 写出 csv
    out_csv = root / "参数估计汇总表.csv"
    write_csv(out_csv, out_rows)

    # 写 md（便于直接粘贴到论文）
    df_out = pd.DataFrame(out_rows)
    md_lines = ["# 参数估计汇总表", "", "| 参数键 | 符号 | 数值 | 单位 | 数据来源 | 说明 |", "|---|---:|---:|---|---|---|"]
    for _, r in df_out.iterrows():
        v_raw = r.get("value", "")
        try:
            v = float(v_raw)
            v_str = f"{v:.6g}" if np.isfinite(v) else "nan"
        except Exception:
            v_str = str(v_raw)
        md_lines.append(
            "| "
            + " | ".join(
                [
                    str(r.get("parameter_key", "")),
                    str(r.get("symbol", "")),
                    v_str,
                    str(r.get("unit", "")),
                    str(r.get("data_source", "")),
                    str(r.get("notes", "")),
                ]
            )
            + " |"
        )
    md_lines += [
        "",
        "## 来源与复现",
        "",
        "- 详细数据来源/处理方法见各子目录 `about.md`。",
        "- 建议复现顺序：先运行 `scripts/00_run_all.py` 生成所有子任务产物，再生成本汇总表。",
    ]
    write_text(root / "参数估计汇总表.md", "\n".join(md_lines) + "\n")


if __name__ == "__main__":
    main()
