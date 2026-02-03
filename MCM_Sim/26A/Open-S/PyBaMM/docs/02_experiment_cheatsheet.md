# 02 - Experiment 写法速查（最常用的 10 种）

PyBaMM 的 `Experiment([...])` 支持用“人类可读”的字符串描述充放电协议。下面是最常见/最稳的写法（建议从这些开始抄）。

## 时间终止（for ...）

- 恒流放电（C-rate）：
  - `Discharge at 1C for 1 hour`
  - `Discharge at C/2 for 30 minutes`
- 恒流放电（A）：
  - `Discharge at 2 A for 600 seconds`
- 恒功率放电（W）：
  - `Discharge at 3 W for 10 minutes`
- 静置：
  - `Rest for 15 minutes`

## 阈值终止（until ...）

- 放电到截止电压（关机逻辑）：
  - `Discharge at 1C until 3.2 V`
  - `Discharge at 3 W until 3.2 V`
- 充电到目标电压：
  - `Charge at C/2 until 4.2 V`

## CCCV（恒流恒压）

典型写法（两步）：

1. `Charge at C/2 until 4.2 V`
2. `Hold at 4.2 V until C/50`

## 组合（一个完整 cycle）

```python
import pybamm

experiment = pybamm.Experiment([
    "Discharge at 1C for 20 minutes",
    "Rest for 5 minutes",
    "Charge at C/2 until 4.1 V",
    "Hold at 4.1 V until C/50",
])
```

## 从“手机功耗曲线”到 Experiment

最简单可行的近似：把功耗曲线离散成分段常数功率（W），每段对应一条 step：

- `Discharge at 2 W for 60 seconds`
- `Discharge at 5 W for 120 seconds`
- `Discharge at 1 W for 300 seconds`
- 最后一段用 `until 3.2 V` 让仿真自然停止（得到 TTE）

见 `03_mcm26a_mapping.md` 与 `demos/demo_03_phone_like_power_profile.py`。

