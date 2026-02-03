# EKF（扩展卡尔曼滤波）用于 SOC 估计资料包

本目录目标：给下一位同学一套“能跑、能改、能接入项目”的 **SOC EKF** 资料包（基于 1RC/2RC ECM）。

你将得到：
- EKF 的最小实现（状态方程/观测方程/雅可比/更新公式）
- 一个合成数据 demo：用已知 ECM 生成 “真值电压”，加噪声后用 EKF 反推 SOC
- 第三方参考实现（已下载到 `third_party/`）
- 与 2026 MCM 赛题 A 的对应关系（写论文用）：`MCM26A_PROBLEM_CONTEXT.md`

---

## 1. 问题定义（典型场景）

输入（可测/可记录）：
- 电流 `I_k`（A，建议 1Hz~10Hz）
- 端电压 `V_k`（V）
- 采样周期 `Δt`

目标（不可直接测）：
- SOC（0~1）
- 极化支路状态 `V1/V2`（用于解释电压的动态滞后）

---

## 2. 1RC/2RC 的 EKF 写法（核心）

以 2RC 为例，状态向量：
- `x = [SOC, V1, V2]^T`

状态转移（离散化）：
- `SOC_k = SOC_{k-1} - (Δt/(3600*Q)) * I_{k-1}`
- `Vj_k = a_j * Vj_{k-1} + b_j * I_{k-1}`
  - `a_j = exp(-Δt/(Rj*Cj))`
  - `b_j = Rj*(1-a_j)`

观测方程（端电压）：
- `V_k = OCV(SOC_k) - I_k*R0 - V1_k - V2_k + v_k`

雅可比：
- `F = diag(1, a1, a2)`
- `H = [dOCV/dSOC, -1, -1]`

---

## 3. Demo（可直接跑）

- 运行：
  - `python3 MCM_Sim/26A/Load-Model/EKF/demo/demo_ekf_soc.py`

demo 会：
- 先用“真值参数”生成电流、SOC 真值、端电压真值
- 给电压加入测量噪声
- 用 EKF 估计 SOC 并画图（SOC 真值 vs 估计、端电压拟合情况）

---

## 3.1 把 EKF 接到你自己的数据（最小示例）

假设你有一个 CSV（至少包含时间/电流/电压），可以按以下方式读取并循环调用 EKF：

```python
import numpy as np
import pandas as pd

from ecm_core import ECM1RCParams, PiecewiseLinearOCV
from ekf_core import ekf_step_1rc

df = pd.read_csv("your_trace.csv")  # 你自己改列名
t = df["time_s"].to_numpy()
i = df["current_A"].to_numpy()      # 约定：放电为正
v = df["voltage_V"].to_numpy()
dt = float(np.median(np.diff(t)))

ocv = PiecewiseLinearOCV.from_points([...])  # 换成你的 OCV-SOC
params = ECM1RCParams(capacity_Ah=..., r0_ohm=..., r1_ohm=..., c1_F=..., ocv=ocv)

x = np.array([0.8, 0.0])                 # 初值：SOC, V1
P = np.diag([0.2**2, 0.1**2])
Q = np.diag([1e-7, 1e-5])
R = (0.02**2)                            # 例：电压噪声方差 (20mV)^2

soc_hat = [float(x[0])]
for k in range(1, len(t)):
    x, P, v_pred, res = ekf_step_1rc(x, P, I_A=float(i[k]), V_meas=float(v[k]), dt_s=dt, params=params, Q=Q, R=R)
    soc_hat.append(float(x[0]))
```

提示：
- 若你的电流符号与本目录相反，请先 `i = -i`
- `OCV` 与参数最好按 SOC/温度分段，否则只能算“名义 EKF”

--- 

## 4. 调参/踩坑清单（交接重点）

- `dOCV/dSOC`：EKF 非常敏感。OCV 曲线越平（导数越小），SOC 越难从电压中“纠正回来”，需要更依赖库伦计与更小的过程噪声。
- `Q`/`R`：不是越小越好。`R`（测量噪声）太小会导致估计抖动；`Q`（过程噪声）太大则 SOC 会漂。
- 初值：`SOC0` 错太多时，EKF 可能在 OCV 平台区难以收敛；可用“静置段电压→SOC”做初始化（如果数据里有静置）。
- 单位与符号：最常见错误是电流符号（放电正/负）和容量单位（mAh/Ah）。

---

## 5. 参考实现（已下载）

位于 `third_party/`：
- `Battery-Kalman/`：一个 Python EKF 示例（仓库较小，适合快速对照）
- `Battery_SOC_Estimation/`：MATLAB/Simulink + 参数辨识 + EKF（含中文说明与图片）

下载方式与版本号：见 `DOWNLOADS.md` 与 `THIRD_PARTY_VERSIONS.md`。
