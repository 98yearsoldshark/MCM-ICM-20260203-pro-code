import numpy as np
import matplotlib.pyplot as plt

def lotka_volterra_with_gender(prey_birth_rate, prey_death_rate, predator_birth_rate, predator_death_rate,
                               initial_prey, initial_predator, dt, total_time, gender_ratio_birth_rate):
    time_steps = np.arange(0, total_time, dt)
    prey_population = np.zeros_like(time_steps, dtype=float)
    predator_population = np.zeros_like(time_steps, dtype=float)
    male_ratio = np.zeros_like(time_steps, dtype=float)

    prey_population[0] = initial_prey
    predator_population[0] = initial_predator
    male_ratio[0] = 0.5  # Initial gender ratio

    for i in range(1, len(time_steps)):
        prey_births = prey_birth_rate * prey_population[i-1] - prey_death_rate * prey_population[i-1] * predator_population[i-1]
        predator_deaths = predator_death_rate * prey_population[i-1] * predator_population[i-1] - predator_birth_rate * predator_population[i-1]

        prey_population[i] = prey_population[i-1] + dt * prey_births
        predator_population[i] = predator_population[i-1] + dt * predator_deaths

        # Update gender ratio based on environmental conditions
        gender_ratio_change = gender_ratio_birth_rate * prey_population[i-1]
        male_ratio[i] = male_ratio[i-1] + dt * gender_ratio_change

        # Keep gender ratio within bounds (0 to 1)
        male_ratio[i] = np.clip(male_ratio[i], 0, 1)

    return time_steps, prey_population, predator_population, male_ratio

# 模拟参数
prey_birth_rate = 0.1
prey_death_rate = 0.02
predator_birth_rate = 0.02
predator_death_rate = 0.1
initial_prey = 1000
initial_predator = 500
dt = 0.1
total_time = 100
gender_ratio_birth_rate = 0.01  # 可根据实际情况调整

# 运行模拟
time_steps, prey_population, predator_population, male_ratio = lotka_volterra_with_gender(
    prey_birth_rate, prey_death_rate, predator_birth_rate, predator_death_rate,
    initial_prey, initial_predator, dt, total_time, gender_ratio_birth_rate
)

# 绘制结果
plt.figure(figsize=(12, 8))

plt.subplot(3, 1, 1)
plt.plot(time_steps, prey_population, label='Prey')
plt.plot(time_steps, predator_population, label='Predator')
plt.xlabel('Time')
plt.ylabel('Population')
plt.legend()

plt.subplot(3, 1, 2)
plt.plot(time_steps, male_ratio, label='Male Ratio')
plt.xlabel('Time')
plt.ylabel('Male Ratio')
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(prey_population, predator_population)
plt.xlabel('Prey Population')
plt.ylabel('Predator Population')

plt.tight_layout()
plt.show()
