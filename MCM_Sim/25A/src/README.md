# MCM Sim (25A) - Wear Forward Simulation

目标：正向生成“磨损热力图”。给定人流/材料/几何/接触模型 -> 输出磨损深度场（heatmap）及统计指标。

本目录是一个可复用的“事件逻辑 -> 物理磨损”仿真骨架：同样可以替换几何与接触分布，迁移到“扶手磨损”“地砖磨损”等类似问题。

## 目录结构

- `mcm_sim/`：核心仿真代码（矩形表面 + 接触核 + 人流模型 + 磨损累计）。
- `configs/`：配置文件（JSON）。
- `scripts/`：可直接运行的示例脚本。
- `runs/`：默认输出目录（每次运行生成一个时间戳子目录，包含 png/npy/json）。

## 快速运行

在项目根目录已存在的虚拟环境 `.venv` 下运行：

```bash
.venv/bin/python MCM_Sim/25A/src/scripts/run_stair_demo.py
```

运行结束后在 `MCM_Sim/25A/src/runs/` 下会生成类似：

- `stair_demo_YYYYMMDD_HHMMSS/`
  - `config.used.json`：本次运行实际使用的配置快照
  - `metrics.json`：关键指标（最大磨损、体积损失等）
  - `wear_depth_final.npy`：最终磨损深度（mm，二维数组）
  - `wear_heatmap_final.png`：最终热力图
  - `snapshots/`：过程快照（按 `save_every_days` 输出）

## 如何迁移到其他主题（例如扶手磨损）

核心思路不变：

1. 将磨损对象抽象为一个 2D 参数面（长度 x 周向/宽度），对应一个 2D 网格。
2. 定义“事件”：一个人触碰/摩擦一次（或在单位时间内发生若干次触碰）。
3. 用接触核（pressure / 摩擦距离分布）把事件映射为对网格的增量磨损。
4. 用到达过程（Poisson/非齐次 Poisson + 周期性）生成长期事件序列，累计得到磨损形貌。

本骨架已经把 (3)(4) 的最小可用版本实现出来；你只需要换配置（几何尺寸/接触分布/人流强度）即可得到新的热力图。

