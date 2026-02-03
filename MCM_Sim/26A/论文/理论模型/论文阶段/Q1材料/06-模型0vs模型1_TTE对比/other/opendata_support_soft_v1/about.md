# about

- 本目录输出的是：AndroWatts 开源测量推得的‘功耗/续航量级支撑’，不是逐时刻真值轨迹。
- 场景划分采用软分类（模糊规则），目的是更贴近真实‘场景混合/边界不清晰’的使用特征。
- 图中径向误差棒：IQR（25%~75%）。
- 复现命令示例：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_radar_with_opendata_support_soft.py --lang en --mode both
```
