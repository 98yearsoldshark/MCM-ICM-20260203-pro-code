import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt

# 定义模型参数
b0 = 0.1     # 基础繁殖率
d = 0.05     # 自然死亡率
e = 0.02     # 捕食效率
c = 0.01     # 捕食对死亡率的减少效果
r = 0.1      # 资源的自然增长率
a = 0.02     # 捕食率

# 定义微分方程
def model(y, t, b0, d, e, c, r, a, Sm):
    N, R = y
    Sf = 1 - Sm
    dNdt = N * (b0 * Sm * Sf - d - e * R + c * e * R)
    dRdt = r * R - a * N * R
    return [dNdt, dRdt]

# 初始条件
N0 = 100     # 初始灯笼鱼数量
R0 = 500     # 初始资源数量
Sm = 0.5     # 初始雄性比例
y0 = [N0, R0]

# 时间网格
t = np.linspace(0, 200, 1000)

# 求解微分方程
solution = odeint(model, y0, t, args=(b0, d, e, c, r, a, Sm))
N, R = solution.T

# 绘制结果
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(t, N, label='Sea Lamprey Population')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Sea Lamprey Population Dynamics')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(t, R, label='Resource Population')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Resource Population Dynamics')
plt.legend()

plt.tight_layout()
plt.show()

