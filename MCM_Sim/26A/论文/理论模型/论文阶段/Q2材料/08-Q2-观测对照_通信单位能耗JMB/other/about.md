# 图 08：观测对照（通信单位能耗 J/MB）

## 对应赛题 Q2 的哪个要求？

- “Compare predictions to observed or plausible behavior”  
  这里对照的是“网络耗电的量级/参数可行性”，为后续 TTE 对照提供依据。

## 本文件夹包含

- `02_energy_per_mb_box.png`：论文版（paper）
- `02_energy_per_mb_box_study.png`：学习版（study）

## 图片来源（原始产物路径）

- paper：`MCM_Sim/26A/src/out_plots/q2/paper/observed_smartphone_measurements/02_energy_per_mb_box.png`
- study：`MCM_Sim/26A/src/out_plots/q2/study/observed_smartphone_measurements/02_energy_per_mb_box.png`

## 如何生成（脚本入口）

- `python MCM_Sim/26A/src/scripts/validate_q2_smartphone_measurements.py --mode paper`
- `python MCM_Sim/26A/src/scripts/validate_q2_smartphone_measurements.py --mode study`

## 关键输入（数据/配置）

- 数据压缩包：`MCM_Sim/26A/data/SmartphoneMeasurements/SmartphoneMeasurements.zip`
  - 仅使用其中的 Monsoon CSV（功耗）与 iPerf txt（吞吐），不依赖 xlsx。

（这是讲解内容，论文中可删除）  
该图给出的 J/MB 可以直接映射到我们功耗模型的参数 `e_per_mb_J`（每 MB 能量）。在论文中可以用一句话写出：$P_{data}=e_{per\\_MB}\\cdot\\dot{D}$（MB/s→W）。
## 目录结构（重构后）

- `../figure.png`：论文版图片（paper）
- `figure_study.png`：学习版图片（study，带更多标注；若不存在则表示该图未单独保留 study 版）
- `data.csv`：与 figure.png 对应的数据版本（便于程序/AI 读取与核对）
- `../paper_fragment_zh.md`：中文论文插入片段
- `paper_fragment_en.md`：英文论文插入片段
- `context_full.md`：拆分前的中英混合版本（仅作备份/追溯）
