import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt

# 定义模型参数
r_H = 0.5     # 猎物的内在增长率
alpha_HL = 0.005 # 灯笼鱼捕食猎物的相互作用系数
alpha_HC = 0.005 # 竞争者捕食猎物的相互作用系数
alpha_CH = 0.005 # 竞争者对猎物的捕食压力系数

r_L = 0.1     # 灯笼鱼的内在增长率
d_L = 0.05    # 灯笼鱼的死亡率
alpha_LP = 0.005 # 寄生物捕食灯笼鱼的相互作用系数

r_P = 0.1     # 寄生物的内在增长率
d_P = 0.05    # 寄生物的死亡率
beta_PL = 0.005 # 寄生物对灯笼鱼的增殖率

r_C = 0.3     # 竞争者的内在增长率
d_C = 0.05    # 竞争者的死亡率

# 定义微分方程
def model(y, t, r_H, alpha_HL, alpha_HC, alpha_CH, r_L, d_L, alpha_LP, r_P, d_P, beta_PL, r_C, d_C, S_m, S_f):
    H, L, P, C = y
    dHdt = r_H * H - alpha_HL * H * L - alpha_HC * H * C
    dLdt = r_L * L * S_m * S_f - d_L * L - alpha_LP * L * P
    dPdt = r_P * P - d_P * P + beta_PL * P * L
    dCdt = r_C * C - d_C * C - alpha_CH * C * H
    return [dHdt, dLdt, dPdt, dCdt]

# 初始条件
H0 = 150     # 初始猎物数量
L0 = 50      # 初始灯笼鱼数量
P0 = 10      # 初始寄生物数量
C0 = 50      # 初始竞争者数量
y0 = [H0, L0, P0, C0]

# 时间网格
t = np.linspace(0, 300, 1000)

# 性别比例变化
S_m = 0.5     # 雄性比例
S_f = 0.5     # 雌性比例

# 求解微分方程
solution = odeint(model, y0, t, args=(r_H, alpha_HL, alpha_HC, alpha_CH, r_L, d_L, alpha_LP, r_P, d_P, beta_PL, r_C, d_C, S_m, S_f))
H, L, P, C = solution.T

# 绘制结果
plt.figure(figsize=(12, 8))
plt.subplot(2, 2, 1)
plt.plot(t, H, label='Prey')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Prey Population Dynamics')

plt.subplot(2, 2, 2)
plt.plot(t, L, label='Sea Lamprey')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Sea Lamprey Population Dynamics')

plt.subplot(2, 2, 3)
plt.plot(t, P, label='Parasites')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Parasites Population Dynamics')

plt.subplot(2, 2, 4)
plt.plot(t, C, label='Competitors')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.title('Competitors Population Dynamics')

plt.tight_layout()
plt.show()

