# 09-不确定性分解-参数vs使用波动

## 这张图回答赛题 Q3 的哪一部分？
- **使用波动（fluctuations）** vs **参数取值不确定性（parameter values）**：谁更主导预测波动？
- 给出一个“可量化”的解释框架：总方差 = 参数间方差 + 参数内（随机过程）方差。

## 图源与生成位置
- 图文件源（论文版）：`MCM_Sim/26A/src/out_plots/q3/paper/fluctuation/21_variance_decomposition.png`
- 本目录内拷贝：`figure.png`

## 生成脚本与关联报表
- 数值报表：`MCM_Sim/26A/src/scripts/run_q3_report.py`
  - 分解结果：`MCM_Sim/26A/src/out_reports/q3/variance_decomposition.csv`
  - 依赖的全局采样：`MCM_Sim/26A/src/out_reports/q3/global_param_samples.csv` + `global_outputs.csv`
  - 依赖的 seed-only：`MCM_Sim/26A/src/out_reports/q3/fluctuation_only.csv`
- 出图脚本：`MCM_Sim/26A/src/scripts/make_q3_plots.py`

## 建议插入论文的位置（示例）
- 论文第 7 节（Q3）→ “7.3 使用波动：不确定性来源分解（law of total variance）”

## 写作要点（建议）
- 一句话提醒读者：这张图的结论依赖“参数先验范围”的宽窄；参数越不确定，蓝色占比越大。
- 可用它衔接到“观测数据锚定”的分解（见本目录 `11-观测数据分解-使用×老化×交互`），更贴题面。

## Sanity check（方向验证）
- 本目录额外提供两组 sanity check 的数据版本（用于证明分解逻辑方向正确）：
  - `sanity_default_vs_tight_N120_K6.csv`：对比 default vs tight 先验（tight=先验收窄），预期 `frac_param` 下降、`frac_usage` 上升；
  - `sanity_default_N60_K20.csv`：在 default 先验下把每个样本的 seed 重复 K 提升到 20，用于观察 `frac_usage` 估计是否更稳定。
- 对应脚本：`MCM_Sim/26A/src/scripts/run_q3_uncertainty_decomposition_sanity.py`

## 数据版本（便于复核/二次分析）

- `data.csv`：与 figure.png 对应的结构化数据版本（便于程序/AI 读取与核对）。
- `data_raw.csv`：可选，原始/更细粒度数据（仅部分图会提供）。
