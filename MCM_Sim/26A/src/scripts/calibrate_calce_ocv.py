#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口：仅用一份 CALCE 低电流 OCV 测试数据，生成 ECM/热/老化通用电池配置文件。

本脚本的定位：
- 解决“目前参数都是名义值”的可信度短板：先把 OCV-SOC 曲线用真实数据替换；
- 严格遵循“暂时只使用一个数据”的约束：只读取一个 xlsx。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SRC_DIR = THIS_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcm26a.calibration import fit_ocv_from_low_current_discharge, load_calce_low_current_ocv_xlsx


def _default_xlsx() -> Path:
    return (
        SRC_DIR.parent
        / "data"
        / "calce-umd"
        / "extracted"
        / "battery-data"
        / "SP"
        / "11_5_2015_low current OCV test_SP20-1.xlsx"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="用 CALCE 低电流 OCV 数据生成电池配置（Model-1/2/3 通用）")
    ap.add_argument("--xlsx", default=str(_default_xlsx()), help="输入 xlsx 路径（低电流 OCV 测试）")
    ap.add_argument(
        "--out",
        default=str(SRC_DIR / "configs" / "battery_calce_sp20_1.json"),
        help="输出配置 JSON 路径",
    )
    ap.add_argument("--discharge-step", type=int, default=3, help="放电所在的 Pgm step（默认 3）")
    ap.add_argument("--n-ocv-points", type=int, default=21, help="输出的 OCV 分段线性点数（含端点）")
    ap.add_argument("--soc-min", type=float, default=0.02, help="SOC 下限（兜底终止条件）")
    ap.add_argument("--v-cut", type=float, default=3.30, help="截止电压（V），用于 Model-1/2/3 cutoff 事件")
    args = ap.parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        print(f"[ERROR] 找不到 xlsx：{xlsx}", file=sys.stderr)
        return 2

    df = load_calce_low_current_ocv_xlsx(xlsx)
    fit = fit_ocv_from_low_current_discharge(
        df,
        discharge_step=int(args.discharge_step),
        n_points=int(args.n_ocv_points),
    )

    # 写入一个“通用电池配置”：battery + ecm + thermal + aging（默认老化系数为 0）
    cap_mAh = int(round(fit.capacity_Ah * 1000.0))
    nominal_v = float(fit.nominal_voltage_V)
    energy_Wh = float(fit.energy_Wh)

    out_cfg = {
        "meta": {
            "schema_version": "0.1.0",
            "source": "CALCE UMD battery-data / SP20-1 low current OCV test (25C)",
            "xlsx": str(xlsx),
            "notes_zh": "本配置由一份低电流放电数据拟合得到 OCV-SOC 曲线；R0/R1/C1/热/老化参数仍为名义值或占位，后续可继续校准。",
        },
        "battery": {
            "capacity_mAh": cap_mAh,
            "nominal_voltage_V": nominal_v,
            "energy_Wh": energy_Wh,
            "soc_min": float(args.soc_min),
            "soc0_default": 1.0,
            "ecm": {
                "V_cut_V": float(args.v_cut),
                # 先不自动写入 r0_est（低电流下不稳定），仍用名义值；你要用时可手动替换
                "R0_ohm": 0.08,
                "R1_ohm": 0.02,
                "C1_F": 2000.0,
                "ocv_curve": {
                    "type": "piecewise_linear",
                    "points": [[float(s), float(v)] for s, v in fit.ocv_points],
                },
            },
            "thermal": {
                "T_ref_C": 25.0,
                "T0_C": 25.0,
                "C_th_J_per_K": 250.0,
                "R_th_K_per_W": 2.5,
                "eta_device_heat": 0.95,
                "r0_temp_coeff_per_C": 0.015,
                "r1_temp_coeff_per_C": 0.015,
                "capacity_temp_coeff_per_C": 0.002,
                "min_temp_C": -10.0,
                "max_temp_C": 70.0,
            },
            "aging": {
                "cap_fade_per_Ah": 0.0,
                "r0_growth_per_Ah": 0.0,
                "r1_growth_per_Ah": 0.0,
                "aging_q10_cycle": 2.0,
                "cap_fade_per_day": 0.0,
                "r0_growth_per_day": 0.0,
                "aging_q10_calendar": 2.0,
                "soc_calendar_k": 0.0,
                "soc_calendar_ref": 0.5,
                "cap_loss_max_frac": 0.5,
                "r_growth_max_frac": 2.0,
            },
        },
    }

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[OK] 仅使用 1 份数据完成 OCV 拟合：", xlsx)
    print(f"[OK] capacity≈{fit.capacity_Ah:.4f}Ah  energy≈{fit.energy_Wh:.3f}Wh  nominal≈{fit.nominal_voltage_V:.3f}V")
    print(f"[OK] ocv points: {len(fit.ocv_points)}")
    print("[OK] saved config:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

