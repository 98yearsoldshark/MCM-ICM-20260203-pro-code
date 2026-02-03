# 02 负载–CPU/GPU功耗（参量估计）

## 数据来源

- AndroWatts（Zenodo, CC BY 4.0）
  - Zenodo Record：14314943；DOI：10.5281/zenodo.14314943
  - 文件：`MCM_Sim/26A/data/open_data/material/res_test/aggregated.csv`
  - CPU 频率：`CPU_LITTLE_FREQ_KHz/CPU_MID_FREQ_KHz/CPU_BIG_FREQ_KHz`
  - GPU 频率：`GPU0_FREQ/GPU_1FREQ/GPU_MEM_AVG`（本拟合用前两者）
  - CPU 功耗 rail：CPU_BIG_ENERGY_AVG_UWS, CPU_MID_ENERGY_AVG_UWS, CPU_LITTLE_ENERGY_AVG_UWS, S9M_VDD_CPUCL0_M_ENERGY_AVG_UWS, TPU_ENERGY_AVG_UWS
  - GPU 功耗 rail：GPU3D_ENERGY_AVG_UWS, GPU_ENERGY_AVG_UWS

## 负载 proxy（可解释口径）

公开数据中没有“真实任务负载”，但存在 CPU/GPU 频率。我们采用可复现的 proxy：

- CPU：
  - 归一化后按簇加权：`load = 0.60*big + 0.30*mid + 0.10*little`（并裁剪到 0~1）
- GPU：
  - `load = max(gpu0, gpu1)` 归一化（裁剪到 0~1）

## 拟合模型

主模型（用于回填 Model-0 参数）：
- `P = k * load`（过原点拟合）

诊断模型（用于论文讨论“超线性/非线性”可能性）：
- `P = k * load^gamma`

## 产物

- `data.csv`：干净样本表（含 cpu_load/gpu_load 与观测功耗）
- `fit_results.csv`：参数与误差（R2/RMSE）
- `figure_paper.png`/`figure_study.png`：论文版/学习版图
