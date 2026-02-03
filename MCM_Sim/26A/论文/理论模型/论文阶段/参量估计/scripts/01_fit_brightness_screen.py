#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01 亮度–屏幕功耗：从 AndroWatts（aggregated.csv）抽取并拟合参数。

输出位置：
- `MCM_Sim/26A/论文/理论模型/论文阶段/参量估计/01-亮度-屏幕功耗/`

说明：
- 用 AndroWatts 的 power-rails 聚合列（*_ENERGY_AVG_UWS）构造“观测屏幕功耗”；
- 以 `Brightness(0~100)` 映射到亮度 nits（默认 500 nits 上限）作为自变量；
- 给出可直接用于 Model-0/Model-1 的参数建议（线性亮度项为主，APL 作为可选增强）。
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from _common import PROJECT_DIR, ensure_dir, linear_fit_with_intercept, summarize_fit, to_repo_path, write_csv, write_text

from mcm26a.observed.andro_watts import load_aggregated_csv, observed_power_from_row
from mcm26a.viz.style import PALETTE_SKIP_GRADIENT, apply_style, savefig


def _apl_from_row(row: pd.Series) -> float:
    """APL（内容平均亮度）proxy：RGB 三通道均值 / 255。"""

    r = row.get("RedLvl", np.nan)
    g = row.get("GreenLvl", np.nan)
    b = row.get("BlueLvl", np.nan)
    try:
        r = float(r)
        g = float(g)
        b = float(b)
    except Exception:
        return float("nan")
    if not (np.isfinite(r) and np.isfinite(g) and np.isfinite(b)):
        return float("nan")
    return float(max(0.0, min(1.0, (r + g + b) / 3.0 / 255.0)))


def main() -> None:
    out_dir = Path(PROJECT_DIR) / "论文" / "理论模型" / "论文阶段" / "参量估计" / "01-亮度-屏幕功耗"
    ensure_dir(out_dir)

    # 1) 读数据（含 CPU_mid err 清洗 + 字段重命名）
    df = load_aggregated_csv(Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv")

    max_nits = 500.0
    rows = []
    for _, row in df.iterrows():
        b = row.get("Brightness", np.nan)
        try:
            b = float(b)
        except Exception:
            b = float("nan")
        if not np.isfinite(b):
            continue

        brightness_pct = float(max(0.0, min(100.0, b)))
        brightness_nits = float(max_nits) * brightness_pct / 100.0

        obs = observed_power_from_row(row)
        apl = _apl_from_row(row)

        rows.append(
            {
                "phone_test_id": int(row.get("ID", row.get("phone_test_id", -1)) or -1),
                "brightness_pct": brightness_pct,
                "brightness_nits": brightness_nits,
                "apl": apl,
                "obs_screen_w": float(obs.screen_w),
                "obs_total_w": float(obs.total_w),
            }
        )

    data = pd.DataFrame(rows)

    # 2) 过滤：只看屏幕亮的样本（否则屏幕功耗为 0/噪声）
    data = data[(data["brightness_nits"] > 1.0) & np.isfinite(data["obs_screen_w"])].copy()
    data = data[(data["obs_screen_w"] > 0.0) & (data["obs_screen_w"] < 2.0)].copy()

    x = data["brightness_nits"].to_numpy()
    y = data["obs_screen_w"].to_numpy()

    # 3) 拟合：线性亮度模型（对应 Model-0：P = P0 + k*nits）
    a0, k = linear_fit_with_intercept(x, y)
    y_hat = a0 + k * x
    summ = summarize_fit(y, y_hat)

    # 4) 可选：加入 APL 的线性项（对应 Model-1 的 APL 机制的“保守版本”）
    # y = a + b*brightness + c*apl
    apl = data["apl"].to_numpy()
    mask_apl = np.isfinite(apl)
    a1 = float("nan")
    b1 = float("nan")
    c1 = float("nan")
    summ_apl = None
    if int(mask_apl.sum()) >= 200:
        X = np.column_stack([np.ones(mask_apl.sum()), x[mask_apl], apl[mask_apl]])
        beta, *_ = np.linalg.lstsq(X, y[mask_apl], rcond=None)
        a1, b1, c1 = float(beta[0]), float(beta[1]), float(beta[2])
        y_hat2 = a1 + b1 * x[mask_apl] + c1 * apl[mask_apl]
        summ_apl = summarize_fit(y[mask_apl], y_hat2)

    # 5) 写出干净数据与拟合结果
    data_path = out_dir / "data.csv"
    data.to_csv(data_path, index=False, encoding="utf-8")

    src_path = Path(PROJECT_DIR) / "data" / "open_data" / "material" / "res_test" / "aggregated.csv"

    fit_rows = [
        {
            "model": "linear_brightness",
            "equation": "P_screen = P0 + k * brightness_nits",
            "n": summ.n,
            "P0_W": a0,
            "k_W_per_nit": k,
            "r2": summ.r2,
            "rmse_W": summ.rmse,
            "data_source": to_repo_path(src_path),
            "screen_power_cols": "Display_ENERGY_AVG_UWS + L22M_DISP_ENERGY_AVG_UWS (uW->W)",
            "brightness_mapping": f"Brightness(0~100) -> nits = {max_nits} * Brightness/100",
        }
    ]
    if summ_apl is not None:
        fit_rows.append(
            {
                "model": "linear_brightness_plus_apl",
                "equation": "P_screen = P0 + k*nits + k_apl*apl",
                "n": summ_apl.n,
                "P0_W": a1,
                "k_W_per_nit": b1,
                "k_apl_W": c1,
                "r2": summ_apl.r2,
                "rmse_W": summ_apl.rmse,
                "data_source": to_repo_path(src_path),
                "apl_mapping": "apl = mean(RedLvl,GreenLvl,BlueLvl)/255 (0~1)",
            }
        )

    write_csv(out_dir / "fit_results.csv", fit_rows)

    about = f"""# 01 亮度–屏幕功耗（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`{to_repo_path(src_path)}`
  - 屏幕功耗（观测）列：`Display_ENERGY_AVG_UWS` + `L22M_DISP_ENERGY_AVG_UWS`
    - 在本项目中解释为“平均功率（uW）”，并换算为 W（×1e-6）。
  - 亮度列：`Brightness`（0~100）
  - APL（内容平均亮度）proxy：`RougeMesuré/VertMesuré/BleuMesuré`（已在适配器中重命名为 `RedLvl/GreenLvl/BlueLvl`）

## 处理与拟合方法

1. 把 `Brightness` 映射到 nits：
   - `brightness_nits = {max_nits} * Brightness/100`
2. 仅保留 `brightness_nits>1` 且 `0<P_screen<2W` 的样本用于拟合（避免屏幕关闭/异常值干扰）。
3. 拟合两种模型：
   - 线性亮度（对应 Model-0）：`P = P0 + k*nits`
   - 线性亮度 + APL（对应 Model-1 的保守简化）：`P = P0 + k*nits + k_apl*apl`

## 产物说明

- `data.csv`：干净样本表（每行一条测试）
- `fit_results.csv`：拟合参数与误差（R2/RMSE）
- `figure_paper.png` / `figure_study.png`：论文版/学习版图
"""
    write_text(out_dir / "about.md", about)

    # 6) 出图
    # 为避免 1000 点散点过密：paper 版用分箱中位数 + IQR；study 版保留散点并标注拟合结果
    import matplotlib.pyplot as plt

    # 分箱（按 nits 分 12 桶）
    data2 = data.copy()
    data2["bin"] = pd.cut(data2["brightness_nits"], bins=12)
    grp = data2.groupby("bin", observed=True)
    b_mid = grp["brightness_nits"].median().to_numpy()
    y_med = grp["obs_screen_w"].median().to_numpy()
    y_q25 = grp["obs_screen_w"].quantile(0.25).to_numpy()
    y_q75 = grp["obs_screen_w"].quantile(0.75).to_numpy()

    for mode in ["paper", "study"]:
        style = apply_style(mode)
        fig, ax = plt.subplots(figsize=(6.8, 4.2))

        if mode == "paper":
            ax.fill_between(b_mid, y_q25, y_q75, color=PALETTE_SKIP_GRADIENT[1], alpha=0.25, linewidth=0)
            ax.plot(b_mid, y_med, color=PALETTE_SKIP_GRADIENT[0], linewidth=2.0, label="分箱中位数（IQR）")
        else:
            ax.scatter(
                data["brightness_nits"],
                data["obs_screen_w"],
                s=14,
                alpha=0.22,
                color=PALETTE_SKIP_GRADIENT[0],
                edgecolors="none",
                label="样本点",
            )

        xs = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), 200)
        ys = a0 + k * xs
        ax.plot(xs, ys, color=PALETTE_SKIP_GRADIENT[3], linewidth=2.2, label="线性拟合：P0+k*nits")

        ax.set_title(f"亮度–屏幕功耗关系（AndroWatts）{style.title_suffix}")
        ax.set_xlabel("屏幕亮度（nits）")
        ax.set_ylabel("屏幕功耗（W）")

        ax.legend(loc="best", frameon=False)

        if style.annotate:
            txt = (
                "拟合模型：P = P0 + k*nits\\n"
                f"样本数 n={summ.n}\\n"
                f"P0={a0:.3f} W, k={k:.6f} W/nit\\n"
                f"R²={summ.r2:.3f}, RMSE={summ.rmse:.3f} W\\n"
                f"亮度映射：Brightness(0~100)→{max_nits} nits"
            )
            ax.text(0.02, 0.98, txt, transform=ax.transAxes, va="top", ha="left", fontsize=9, bbox={"fc": "white", "ec": "none", "alpha": 0.75})

        savefig(fig, out_dir / f"figure_{mode}.png", mode=mode)
        plt.close(fig)


if __name__ == "__main__":
    main()
