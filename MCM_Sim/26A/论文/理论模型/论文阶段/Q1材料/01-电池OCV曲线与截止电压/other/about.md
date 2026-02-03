# about

- 本图文件：`figure.png`
- 复制来源：`MCM_Sim/26A/src/out_plots/model1/paper/battery/06_ocv_curve.png`
- 图意：Model-1 采用的 OCV-SOC 分段线性曲线（并在同图标注截止电压 \(V_{\mathrm{cut}}=3.30\text{ V}\)）
- 生成脚本：`MCM_Sim/26A/src/scripts/make_model1_plots.py`（paper 模式）
- 复现命令（默认配置即可复现同类图）：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/make_model1_plots.py --mode paper
```

- 备注：
  - 图内坐标轴为中文（便于队内讨论）。
  - 图题/解读：中文见 `../paper_fragment_zh.md`，英文见 `paper_fragment_en.md`。
  - 数据版本：`data.csv`（由 `MCM_Sim/26A/src/scripts/export_q1_paper_material_data.py` 导出）。
