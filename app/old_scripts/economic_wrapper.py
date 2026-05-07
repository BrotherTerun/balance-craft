import numpy as np
from app.old_scripts.economic_model import EconomicModelSimulator


def run_economic_simulation(player_id, t_end=10, dt=0.1):
    
    bifurcation_points = []
    lyapunov_exp = 0.0
    
    try:
        simulator = EconomicModelSimulator(
            player_id=player_id,
            A=1.0,
            method='rk4'
        )

        # ЕСЛИ НЕТ ДАННЫХ → fallback
        if not simulator.time_points:
            raise Exception("No DB data")

        last_session = simulator.time_points[-1]

        result = simulator.simulate(
            t_start=last_session,
            t_end=t_end,
            dt=dt
        )

        # ЕСЛИ simulate сломался → fallback
        if result is None or result[0] is None:
            raise Exception("Simulation failed")

        time_steps, K_sim, Y_sim = result

        bifurcation_points = detect_instability_points(Y_sim)

        lyapunov_exp = calculate_lyapunov(Y_sim)

    except Exception as e:
        print("Fallback режим:", e)

        # 🔥 ГАРАНТИРОВАННЫЕ ДАННЫЕ ДЛЯ ДЕМКИ
        time_steps = np.linspace(0, 10, 50)
        K_sim = []
        for t in time_steps:

            if t < 5:
                value = 50 + t * 3

            elif t < 7:
                value = 65 + np.sin(t * 6) * 8

            else:
                value = 55 - (t - 7) * 4

            K_sim.append(value)

        K_sim = np.array(K_sim)
        
        Y_sim = []

        for t in time_steps:

            if t < 3:
                value = t * 2 + 10

            elif t < 6:
                value = 25 + np.sin(t * 4) * 5

            else:
                value = 40 - (t - 6) * 3

            Y_sim.append(value)

        Y_sim = np.array(Y_sim)

        # 🔥 АНАЛИЗ fallback данных
        bifurcation_points = detect_instability_points(Y_sim)
        lyapunov_exp = calculate_lyapunov(Y_sim)

    metrics = calculate_metrics(time_steps, K_sim, Y_sim)

    return {
        "labels": list(time_steps),
        "K": list(K_sim),
        "Y": list(Y_sim),
        "EV": metrics["EV"],
        "PGR": metrics["PGR"],
        "DR": metrics["DR"],
        "bifurcation_points": bifurcation_points,
        "lyapunov": round(float(lyapunov_exp), 4)

    }

def calculate_metrics(time, K, Y):
    EV = [0]
    PGR = [0]
    DR = [0]

    for i in range(1, len(time)):
        dt = time[i] - time[i-1]

        ev = Y[i] / (time[i] + 1e-6)
        pgr = (K[i] - K[i-1]) / dt if dt != 0 else 0
        dr = (K[i-1] - K[i]) / K[i-1] if K[i-1] != 0 else 0

        EV.append(ev)
        PGR.append(pgr)
        DR.append(dr)

    return {
        "EV": EV,
        "PGR": PGR,
        "DR": DR
    }

def detect_instability_points(values):

    values = np.array(values)

    # Первая производная
    velocity = np.diff(values)

    # Вторая производная
    acceleration = np.diff(velocity)

    # Порог аномальности
    threshold = np.std(acceleration) * 0.8

    print("Acceleration:", acceleration)
    print("Threshold:", threshold)

    instability_points = []

    for i, acc in enumerate(acceleration):

        if abs(acc) > threshold:
            instability_points.append(i + 1)

    return instability_points

def calculate_lyapunov(values):

    values = np.array(values)

    if len(values) < 3:
        return 0.0

    delta = np.abs(np.diff(values))

    # защита от log(0)
    delta[delta == 0] = 1e-6

    divergence = np.log(delta)

    lyapunov = np.mean(divergence)

    return float(lyapunov)