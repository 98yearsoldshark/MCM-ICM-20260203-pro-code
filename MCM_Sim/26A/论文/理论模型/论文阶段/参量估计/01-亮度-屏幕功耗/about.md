# 01 亮度–屏幕功耗（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
  - 屏幕功耗（观测）列：`Display_ENERGY_AVG_UWS` + `L22M_DISP_ENERGY_AVG_UWS`
    - 在本项目中解释为“平均功率（uW）”，并换算为 W（×1e-6）。
  - 亮度列：`Brightness`（0~100）
  - APL（内容平均亮度）proxy：`RougeMesuré/VertMesuré/BleuMesuré`（已在适配器中重命名为 `RedLvl/GreenLvl/BlueLvl`）

## 处理与拟合方法

1. 把 `Brightness` 映射到 nits：
   - `brightness_nits = 500.0 * Brightness/100`
2. 仅保留 `brightness_nits>1` 且 `0<P_screen<2W` 的样本用于拟合（避免屏幕关闭/异常值干扰）。
3. 拟合两种模型：
   - 线性亮度（对应 Model-0）：`P = P0 + k*nits`
   - 线性亮度 + APL（对应 Model-1 的保守简化）：`P = P0 + k*nits + k_apl*apl`

## 产物说明

- `data.csv`：干净样本表（每行一条测试）
- `fit_results.csv`：拟合参数与误差（R2/RMSE）
- `figure_paper.png` / `figure_study.png`：论文版/学习版图
