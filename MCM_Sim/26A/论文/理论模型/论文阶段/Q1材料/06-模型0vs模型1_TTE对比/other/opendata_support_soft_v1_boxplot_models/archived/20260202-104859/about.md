# about

- 灰色箱线：AndroWatts 开源测量推得的 TTE≈E/P 量级分布（软分类映射）。
- 蓝/橘小箱线：Model-0/Model-1 的轻量不确定性采样（UQ-lite），用于展示“预测不确定性”。
- 复现命令示例：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_q1_tte_boxplot_models_vs_opendata_soft.py --lang en --mode both
```
