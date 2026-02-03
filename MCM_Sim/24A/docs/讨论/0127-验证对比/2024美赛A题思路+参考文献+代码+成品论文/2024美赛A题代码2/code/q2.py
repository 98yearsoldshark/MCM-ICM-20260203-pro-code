import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar

# 定义参数
b0 = 0.1     # 基础繁殖率
alpha = 5    # 性别比例偏离最优值时的适应度损失系数
S_m_opt = 0.5 # 假设最优雄性比例为0.5

# 定义适应度函数
def fitness(S_m, b0, alpha, S_m_opt):
    S_f = 1 - S_m
    return b0 * S_m * S_f - alpha * (S_m - S_m_opt)**2

# 寻找最大适应度对应的性别比例
result = minimize_scalar(lambda S_m: -fitness(S_m, b0, alpha, S_m_opt), bounds=(0, 1), method='bounded')

# 最优性别比例
optimal_S_m = result.x
optimal_fitness = fitness(optimal_S_m, b0, alpha, S_m_opt)

# 绘制适应度随性别比例变化的图
S_m_values = np.linspace(0, 1, 100)
fitness_values = [fitness(S_m, b0, alpha, S_m_opt) for S_m in S_m_values]

plt.figure(figsize=(8, 5))
plt.plot(S_m_values, fitness_values, label='Fitness')
plt.plot(optimal_S_m, optimal_fitness, 'ro', label='Optimal Sex Ratio')
plt.xlabel('Proportion of Males ($S_m$)')
plt.ylabel('Fitness ($F$)')
plt.title('Fitness as a Function of Sex Ratio')
plt.legend()
plt.show()

