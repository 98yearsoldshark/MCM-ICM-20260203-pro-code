# Demo / 示例（可直接运行）

本目录提供一些**可直接运行**的小脚本，用来：

- 快速确认数据是否完整（对照 `manifest.csv`）
- 演示如何读取常见格式（CSV / MAT）并做简单可视化

运行前提：
- Python 3
- 推荐依赖：`pandas`、`matplotlib`、`scipy`（本机环境通常已具备；若缺失请自行安装）

## 1) 完整性校验

```bash
python3 MCM_Sim/26A/data/calce-umd/examples/00_verify_integrity.py
```

常用参数：
- `--no-sha`：跳过 sha256（更快）
- `--report MCM_Sim/26A/data/calce-umd/INTEGRITY_REPORT.md`：输出一份 Markdown 报告

## 2) Storage 阻抗 CSV 快速可视化（Nyquist / Bode）

```bash
python3 MCM_Sim/26A/data/calce-umd/examples/01_plot_storage_impedance.py
```

可选参数：
- `--csv <path>`：指定某个 CSV 文件（默认自动挑选 1 个示例文件）
- `--out <png_path>`：指定输出图片路径（默认写到 `examples/_outputs/`）

## 3) Anomaly Dataset2（MAT）容量衰减曲线

```bash
python3 MCM_Sim/26A/data/calce-umd/examples/02_plot_anomaly_dataset2.py
```

可选参数：
- `--mat <path>`：指定 `Dataset2.mat`（默认使用 `extracted/anomaly/Dataset2/Dataset2.mat`）
- `--out <png_path>`：指定输出图片路径

## 输出目录

脚本默认会把图片写到：`examples/_outputs/`（不影响原始数据）。

