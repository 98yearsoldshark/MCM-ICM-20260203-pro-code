# about

- 目的：为 Q1-06 雷达图提供“公开测量数据支持的量级”（sanity check），不替代连续时间机理模型。
- 数据源：AndroWatts（Zenodo，CC BY 4.0），见 `MCM_Sim/26A/data/open_data/README_zh.md`。
- 计算口径：P 取 open data 的 `*_ENERGY_AVG_UWS` 求和并换算为 W；满电 TTE≈E/P（E 取 phone 配置里的 energy_Wh）。
- 场景映射：使用 `--mapping v2` 将 open data 行粗分到 S1..S5，并在图中标注每类样本数 n。
  - v2 会输出 `mapping_diagnostics.csv`，给出每类关键强度指标的中位数，便于解释映射规则是否符合直觉。

复现命令：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_radar_with_opendata_support.py --mode both --lang en --mapping v2
```
