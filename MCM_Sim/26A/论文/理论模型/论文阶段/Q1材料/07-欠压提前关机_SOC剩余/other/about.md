# about

- 本图文件：`figure.png`
- 复制来源：`MCM_Sim/26A/src/out_plots/model1/paper/battery/07_soc_at_cutoff.png`
- 图意：不同场景下，当 \(V_{\mathrm{term}}\le V_{\mathrm{cut}}\) 触发关机时，仍可能剩余的 SOC（解释欠压提前关机）
- 生成脚本：`MCM_Sim/26A/src/scripts/make_model1_plots.py`（paper 模式）
- 复现命令（默认配置即可复现同类图）：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_model1_plots.py --mode paper
```

