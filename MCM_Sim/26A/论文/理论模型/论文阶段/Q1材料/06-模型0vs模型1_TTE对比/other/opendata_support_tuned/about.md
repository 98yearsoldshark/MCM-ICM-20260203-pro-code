# about

- 图中黑色虚线：AndroWatts 开源测量数据推得的“满电 TTE≈E/P”量级支撑（不是逐时刻真值轨迹）。
- 为减少系统偏差，我们对“门控 + 优先级”分类阈值做了可复现的随机搜索，使其更贴近模型预测（目标曲线：model1）。
- 关键输出：
  - `tuned_params.json`：最佳阈值（可复现）
  - `tuning_top20.csv`：前 20 组候选（便于复核）
  - `mapping_diagnostics.csv`：每类强度指标中位数（证明规则与直觉一致）
- 注意：若 AndroWatts 数据集本身缺少“深度待机”等场景覆盖，则 S1 仍可能无法与模型完全一致。

复现命令示例：

```bash
PYTHONPATH=MCM_Sim/26A/src python MCM_Sim/26A/src/scripts/tune_q1_opendata_mapping_to_model.py --lang en --mode both
```
