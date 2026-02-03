#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把“参数估计汇总表”回填为可直接用于仿真的配置文件（建议版）。

注意：
- 为了不破坏已有实验/默认配置，本脚本**不会修改** `src/configs/`；
- 只在论文目录下生成一份“建议版配置”，用于后续对照实验或作为校准初值。

输出：
- `.../参量估计/suggested_configs/power_params_v0_paramest_0202.json`
- `.../参量估计/suggested_configs/power_params_v1_stateful_paramest_0202.json`
- `.../参量估计/suggested_configs/phone_default_v2_thermal_paramest_0202.json`
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from _common import PROJECT_DIR, ensure_dir, to_repo_path, write_text


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_param(df: pd.DataFrame, key: str) -> float:
    sub = df[df["parameter_key"] == key]
    if sub.empty:
        raise KeyError(f"参数缺失：{key}")
    return float(sub.iloc[0]["value"])


def main() -> None:
    root = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计"
    out_dir = root / "suggested_configs"
    ensure_dir(out_dir)

    df = pd.read_csv(root / "参数估计汇总表.csv")

    p_screen_P0 = _get_param(df, "power.screen.P0_W")
    p_screen_k = _get_param(df, "power.screen.k_W_per_nit")
    k_cpu = _get_param(df, "power.cpu.k_W")
    k_gpu = _get_param(df, "power.gpu.k_W")
    tau_tail = _get_param(df, "power.rrc.tau_tail_s (wifi)")
    e_wifi = _get_param(df, "power.rrc.e_per_mb_J (wifi)")
    r_th = _get_param(df, "battery.thermal.R_th_K_per_W")
    c_th = _get_param(df, "battery.thermal.C_th_J_per_K")

    # --- power_params_v0 ---
    base0 = _load_json(Path(PROJECT_DIR) / "src" / "configs" / "power_params_v0.json")
    base0.setdefault("meta", {})
    base0["meta"]["notes_zh"] = (
        "参量估计建议版：基于 AndroWatts aggregated.csv 拟合得到屏幕/CPU/GPU 的线性系数，用作 Model-0 的可解释初值。"
    )
    base0["screen"]["P0_W"] = float(p_screen_P0)
    base0["screen"]["k_W_per_nit"] = float(p_screen_k)
    base0["cpu"]["k_W"] = float(k_cpu)
    base0["gpu"]["k_W"] = float(k_gpu)
    _save_json(out_dir / "power_params_v0_paramest_0202.json", base0)

    # --- power_params_v1_stateful ---
    base1 = _load_json(Path(PROJECT_DIR) / "src" / "configs" / "power_params_v1_stateful.json")
    base1.setdefault("meta", {})
    base1["meta"]["notes_zh"] = (
        "参量估计建议版：基于 AndroWatts aggregated.csv 的估计结果回填屏幕/CPU/GPU 线性系数，并用能量守恒反推的 τ_tail 与 e_wifi "
        "作为 Wi‑Fi RRC 的量级标定。建议与原配置做对照实验，而不是直接覆盖默认值。"
    )
    base1["screen"]["P0_W"] = float(p_screen_P0)
    base1["screen"]["k_W_per_nit"] = float(p_screen_k)
    base1["cpu"]["k_W"] = float(k_cpu)
    base1["gpu"]["k_W"] = float(k_gpu)
    base1["rrc"]["tau_tail_s"]["wifi"] = float(tau_tail)
    base1["rrc"]["e_per_mb_J"]["wifi"] = float(e_wifi)
    _save_json(out_dir / "power_params_v1_stateful_paramest_0202.json", base1)

    # --- phone_default_v2_thermal ---
    batt2 = _load_json(Path(PROJECT_DIR) / "src" / "configs" / "phone_default_v2_thermal.json")
    batt2.setdefault("meta", {})
    batt2["meta"]["notes_zh"] = (
        "参量估计建议版：由 AndroWatts 的温升统计量（DIFF_SOC_TEMP）反推一阶热模型量级，回填 R_th/C_th。"
        "注意该温度更像 SoC/局部节点短时动态，不一定等同电池整体热惯量；建议用于敏感性/对照实验。"
    )
    batt2["battery"]["thermal"]["R_th_K_per_W"] = float(r_th)
    batt2["battery"]["thermal"]["C_th_J_per_K"] = float(c_th)
    _save_json(out_dir / "phone_default_v2_thermal_paramest_0202.json", batt2)

    # README
    readme = f"""# suggested_configs（参量估计建议配置）

本目录由脚本自动生成：`scripts/10_generate_suggested_configs.py`

来源（估计结果）：
- `{to_repo_path(root / '参数估计汇总表.md')}`

生成的文件：
- `power_params_v0_paramest_0202.json`
  - 基于 `src/configs/power_params_v0.json`，回填：screen(P0,k)、cpu.k、gpu.k
- `power_params_v1_stateful_paramest_0202.json`
  - 基于 `src/configs/power_params_v1_stateful.json`，回填：screen/cpu/gpu + Wi‑Fi 的 `tau_tail_s` 与 `e_per_mb_J`
- `phone_default_v2_thermal_paramest_0202.json`
  - 基于 `src/configs/phone_default_v2_thermal.json`，回填：`R_th_K_per_W`、`C_th_J_per_K`

建议用法：
1) 作为对照实验（与原 config 并行跑），观察结果变化；  
2) 作为后续校准/随机搜索的初值或先验范围；  
3) 不建议直接覆盖 `src/configs/` 的默认文件（保留可复现基线）。  
"""
    write_text(out_dir / "README.md", readme)


if __name__ == "__main__":
    main()

