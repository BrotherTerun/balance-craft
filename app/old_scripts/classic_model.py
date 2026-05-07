import numpy as np
import matplotlib.pyplot as plt


def simulate_haavelmo_classical(
        K0=10.0,
        L0=5.0,
        A=1.0,
        alpha=0.6,
        s=0.25,
        delta=0.05,
        n=0.01,
        t_max=100,
        dt=0.1
):
    """
    Классическая модель Хаавельмо с экспоненциальным ростом труда L(t).
    Численное решение уравнений dK/dt и Y = A*K^α*L^(1–α).
    """
    steps = int(t_max / dt)
    t = np.linspace(0, t_max, steps)

    K = np.zeros(steps)
    L = np.zeros(steps)
    Y = np.zeros(steps)

    # Начальные условия
    K[0] = K0
    L[0] = L0
    Y[0] = A * K0 ** alpha * L0 ** (1 - alpha)

    for i in range(1, steps):
        # Рост труда
        L[i] = L[i - 1] * np.exp(n * dt)

        # Производственная функция
        Y[i - 1] = A * K[i - 1] ** alpha * L[i - 1] ** (1 - alpha)

        # Изменение капитала
        dK = s * Y[i - 1] - delta * K[i - 1]
        K[i] = K[i - 1] + dK * dt

    # Последнее значение выпуска
    Y[-1] = A * K[-1] ** alpha * L[-1] ** (1 - alpha)

    return t, K, L, Y


def plot_classical_results(t, K, L, Y):
    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    plt.plot(t, K, label='K(t) – Капитал', color='blue')
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 1, 2)
    plt.plot(t, L, label='L(t) – Труд', color='green')
    plt.grid(True)
    plt.legend()

    plt.subplot(3, 1, 3)
    plt.plot(t, Y, label='Y(t) – Выпуск', color='purple')
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.show()


# Пример запуска
if __name__ == "__main__":
    t, K, L, Y = simulate_haavelmo_classical()
    plot_classical_results(t, K, L, Y)
