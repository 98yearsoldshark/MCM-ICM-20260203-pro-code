# Q1 专用整理：PyBaMM 作为“连续时间机理基准（benchmark）”

本文件夹用于服务题面 **Q1 / Requirement 1：Continuous-Time Model** 的“机理可信度”部分：

- 你们主模型（通常是更轻量的 ECM/能量模型）负责跑完整策略与场景；
- PyBaMM（SPM/DFN 等）作为**连续时间电化学机理模型**，用于做少量对照实验：
  - 证明“功率负载下的电压/电流非线性”是真实存在的；
  - 解释为什么 `TTE` 对功率/负载并非严格线性；
  - 为论文里“简化到什么程度仍合理”提供支撑。

注意：PyBaMM 默认参数集（如 `Chen2020`）不等同于真实手机电池参数。Q1 阶段建议把它当作**趋势对照**，不要把绝对数值当作真值。

---

## Q1 最推荐复用的 demo（两张图就够）

1) 类手机分段功率剖面（功率控制更贴近手机）  
`demos/demo_03_phone_like_power_profile.py`

2) 扫功率得到 TTE 曲线（边际收益递减/非线性）  
`demos/demo_04_tte_vs_power.py`

这两个 demo 的产物默认写到：
- `MCM_Sim/26A/Open-S/PyBaMM/outputs/`

本 `0for_Q1/outputs/` 目录建议只放“论文 Q1 会引用的精选产物”（可从 `../outputs/` 复制过来）。

---

## 运行方式（可复现）

在本目录根下（`MCM_Sim/26A/Open-S/PyBaMM`）运行：

```bash
# 运行全部 demo（会生成 outputs/ 下的 png/csv）
python3 demos/run_all.py
```

如果你只想跑 Q1 相关两项：

```bash
python3 demos/demo_03_phone_like_power_profile.py
python3 demos/demo_04_tte_vs_power.py
```

---

## 把“精选输出”同步到本文件夹（推荐）

如果 `../outputs/` 已有结果，你可以用本脚本把 Q1 相关文件复制到 `0for_Q1/outputs/`：

```bash
python3 MCM_Sim/26A/Open-S/PyBaMM/0for_Q1/src/sync_q1_outputs.py
```

