# back_about：Q2 单因素敏感性龙卷风图（OAT）

## 这张图回答什么？
用于回答题面/论文中“哪些建模参数最敏感（影响最大）”。我们采用单因素扰动（OAT）：一次只改变一个参数，比较输出 TTE 的变化幅度。

## 输出定义
- 输出：平均 TTE（小时）。对随机过程做多种子重复（CRN），并对所选场景集合取均值。
- 场景：`S4_mixed_day（混合使用/标准一天）`，SOC0=100%，dt=5s，seeds=30。

## 参数集合与扰动方式（对齐 Q3 的 9 参数）
本图 y 轴使用与 `Q3材料/16-生产需要的内容` 一致的 9 个参数符号：
SOH、η0、α_R、hA、k_b、k_cpu、k_gpu、τ_m、b_{q,m}。

- 扰动幅度：eps=0.05（即对基准值做 ±5% 相对扰动）。
- 基准值来源：`MCM_Sim/26A/论文/理论模型/论文阶段/Q3材料/16-生产需要的内容/local_sensitivity_s1_s5_9params.csv`
  - 读取常量列：`soh0=0.9`、`alpha_r0=1.5`、`eta0=0.93`、`hA0=0.4`；
  - 其余尺度因子（k_b/k_cpu/k_gpu/τ_m/b_{q,m}）的基准值取 1。
- 映射关系：
  - SOH/α_R -> 初始老化状态：`cap_loss0=1-SOH`，`r0_growth0=α_R(1-SOH)`；
  - hA -> 电池热阻：`r_th≈1/hA`；
  - k_b/k_cpu/k_gpu/τ_m/b_{q,m} -> 功耗/无线子模型的尺度因子（对应 screen/cpu/gpu 与 RRC tail/data）。

## 生成方式（可复现）
- 脚本：`MCM_Sim/26A/src/scripts/run_q2_param_tornado_oat.py`
- 参数：`--param-set q3_9 --scenario S4_mixed_day --soc0 1.0 --dt 5 --seeds 30 --seed0 2026`
- 报表数据：`MCM_Sim/26A/src/out_reports/q2/param_tornado_oat.csv`

