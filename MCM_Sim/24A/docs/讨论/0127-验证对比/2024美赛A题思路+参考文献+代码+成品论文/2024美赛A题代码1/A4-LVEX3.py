import numpy as np
import matplotlib.pyplot as plt

def lotka_volterra_with_parasite(prey_birth_rate, prey_death_rate, predator_birth_rate, predator_death_rate,
                                 lamprey_birth_rate, lamprey_death_rate, initial_prey, initial_predator, initial_lamprey,
                                 parasite_birth_rate, parasite_death_rate, initial_parasite, dt, total_time, gender_ratio_birth_rate):
    time_steps = np.arange(0, total_time, dt)
    prey_population = np.zeros_like(time_steps, dtype=float)
    predator_population = np.zeros_like(time_steps, dtype=float)
    lamprey_population = np.zeros_like(time_steps, dtype=float)
    male_ratio = np.zeros_like(time_steps, dtype=float)
    parasite_population = np.zeros_like(time_steps, dtype=float)

    prey_population[0] = initial_prey
    predator_population[0] = initial_predator
    lamprey_population[0] = initial_lamprey
    male_ratio[0] = 0.5  # Initial gender ratio
    parasite_population[0] = initial_parasite

    for i in range(1, len(time_steps)):
        prey_births = prey_birth_rate * prey_population[i-1] - prey_death_rate * prey_population[i-1] * predator_population[i-1]
        predator_deaths = predator_death_rate * prey_population[i-1] * predator_population[i-1] - predator_birth_rate * predator_population[i-1]
        lamprey_births = lamprey_birth_rate * prey_population[i-1] * predator_population[i-1] - lamprey_death_rate * lamprey_population[i-1]

        prey_population[i] = prey_population[i-1] + dt * prey_births
        predator_population[i] = predator_population[i-1] + dt * predator_deaths
        lamprey_population[i] = lamprey_population[i-1] + dt * lamprey_births

        # Update gender ratio based on environmental conditions
        gender_ratio_change = gender_ratio_birth_rate * prey_population[i-1] * predator_population[i-1]
        male_ratio[i] = male_ratio[i-1] + dt * gender_ratio_change
        male_ratio[i] = np.clip(male_ratio[i], 0, 1)

        # Parasite dynamics
        parasite_births = parasite_birth_rate * male_ratio[i] * lamprey_population[i-1]
        parasite_deaths = parasite_death_rate * parasite_population[i-1]
        parasite_population[i] = parasite_population[i-1] + dt * (parasite_births - parasite_deaths)

    return time_steps, prey_population, predator_population, lamprey_population, male_ratio, parasite_population

# 模拟参数
prey_birth_rate = 0.1
prey_death_rate = 0.02
predator_birth_rate = 0.02
predator_death_rate = 0.1
lamprey_birth_rate = 0.01
lamprey_death_rate = 0.05
initial_prey = 1000
initial_predator = 500
initial_lamprey = 50
dt = 0.1
total_time = 100
gender_ratio_birth_rate = 0.001
parasite_birth_rate = 0.005
parasite_death_rate = 0.002
initial_parasite = 10

# 运行模拟
time_steps, prey_population, predator_population, lamprey_population, male_ratio, parasite_population = lotka_volterra_with_parasite(
    prey_birth_rate, prey_death_rate, predator_birth_rate, predator_death_rate,
    lamprey_birth_rate, lamprey_death_rate, initial_prey, initial_predator, initial_lamprey,
    parasite_birth_rate, parasite_death_rate, initial_parasite, dt, total_time, gender_ratio_birth_rate
)

# 绘制结果
plt.figure(figsize=(12, 12))

plt.subplot(5, 1, 1)
plt.plot(time_steps, prey_population, label='Prey')
plt.plot(time_steps, predator_population, label='Predator')
plt.xlabel('Time')
plt.ylabel('Population')
plt.legend()

plt.subplot(5, 1, 2)
plt.plot(time_steps, lamprey_population, label='Lamprey')
plt.xlabel('Time')
plt.ylabel('Population')
plt.legend()

plt.subplot(5, 1, 3)
plt.plot(time_steps, male_ratio, label='Male Ratio')
plt.xlabel('Time')
plt.ylabel('Male Ratio')
plt.legend()

plt.subplot(5, 1, 4)
plt.plot(time_steps, parasite_population, label='Parasite')
plt.xlabel('Time')
plt.ylabel('Parasite Population')
plt.legend()

plt.subplot(5, 1, 5)
plt.plot(prey_population, predator_population)
plt.xlabel('Prey Population')
plt.ylabel('Predator Population')

plt.tight_layout()
plt.show()
