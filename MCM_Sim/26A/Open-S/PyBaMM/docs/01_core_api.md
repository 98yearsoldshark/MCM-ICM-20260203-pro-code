# 01 - 核心 API 速览（Model / Parameters / Experiment / Simulation / Solver / Solution）

PyBaMM 常见的最小工作流如下（你只要理解 6 个对象就够开始干活）：

```python
import pybamm

# 1) Model：选择模型复杂度（SPM/DFN/...）
model = pybamm.lithium_ion.SPM()

# 2) ParameterValues：选择/修改参数集（材料、几何、容量、OCV 等）
params = pybamm.ParameterValues("Chen2020")

# 3) Experiment：定义实验协议（电流/功率/电压控制 + 时间/阈值终止）
experiment = pybamm.Experiment([
    "Discharge at 1C until 3.2 V",
])

# 4) Solver（可选）：不指定则使用默认求解器
# solver = pybamm.CasadiSolver(mode="safe")  # 例

# 5) Simulation：把 model/params/experiment/solver 组装起来
sim = pybamm.Simulation(model, parameter_values=params, experiment=experiment)

# 6) Solution：solve() 的结果，能取出任意变量时间序列
sol = sim.solve()
t_h = sol["Time [h]"].entries
v = sol["Terminal voltage [V]"].entries
```

## 变量名怎么找？

你可以先用 demo 跑出 `Solution`，然后：

```python
# Solution 本身不是 dict；变量名在底层 model 里
names = list(sol.all_models[0].variables.keys())
print(names[:50])

# 取数组（与 Time 对齐）
sol["Current [A]"].entries
```

常用变量（本交接包 demo 中也会用）：
- `Time [h]`
- `Terminal voltage [V]`
- `Current [A]`
- `Power [W]` / `Terminal power [W]`
- `Discharge capacity [A.h]`

## 参数怎么改？

常见做法：

```python
params = pybamm.ParameterValues("Chen2020")
params.update({
    # 例：修改环境温度（不同模型/参数集的键名可能略有差异）
    "Ambient temperature [K]": 298.15,
})
```

提示：参数键名很多，建议在需要时再查；最稳的方式是先用 `params` 打印/搜索键。
