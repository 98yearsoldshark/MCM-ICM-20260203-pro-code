import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt

# 定义模型参数
r_P = 1.0     # 植物性浮游生物的内在增长率
K_P = 500     # 植物性浮游生物的环境承载能力
alpha_PH = 0.002 # 猎物捕食植物性浮游生物的相互作用系数

r_H = 0.5     # 猎物的内在增长率
K_H = 200     # 猎物的环境承载能力
alpha_HL = 0.005 # 灯笼鱼捕食猎物的相互作用系数

r_L = 0.1     # 灯笼鱼的内在增长率
d_L = 0.05    # 灯笼鱼的死亡率
S_m = 0.5     # 雄性比例
S_f = 0.5     # 雌性比例

# 定义微分方程
def model(y, t, r_P, K_P, alpha_PH, r_H, K_H, alpha_HL, r_L, d_L, S_m, S_f):
    P, H, L = y
    dPdt = r_P * P * (1 - P / K_P) - alpha_PH * P * H
    dHdt = r_H * H * (1 - H / K_H) - alpha_HL * H * L
    dLdt = r_L * L * S_m * S_f - d_L * L
    return [dPdt, dHdt, dLdt]

# 初始条件
P0 = 300     # 初始植物性浮游生物数量
H0 = 150     # 初始猎物数量
L0 = 50      # 初始灯笼鱼数量
y0 = [P0, H0, L0]

# 时间网格
t = np.linspace(0, 300, 1000)

# 求解微分方程
solution = odeint(model, y0, t, args=(r_P, K_P, alpha_PH, r_H, K_H, alpha_HL, r_L, d_L, S_m, S_f))
P, H, L = solution.T

# 绘制结果
plt.figure(figsize=(12, 5))
plt.subplot(1, 3, 1)
plt.plot(t, P, label='Phytoplankton')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Phytoplankton Dynamics')

plt.subplot(1, 3, 2)
plt.plot(t, H, label='Prey')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Prey Population Dynamics')

plt.subplot(1, 3, 3)
plt.plot(t, L, label='Sea Lamprey')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Sea Lamprey Population Dynamics')

plt.tight_layout()
plt.show()

