import numpy as np
import mysql.connector

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}

def load_player_sessions(player_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        sm.session_id,
        s.session_start,
        MAX(CASE WHEN sm.metric_name = 'K_POWER_SCORE' THEN sm.metric_value END) AS K,
        MAX(CASE WHEN sm.metric_name = 'Y_EXP_VELOCITY' THEN sm.metric_value END) AS Y,
        MAX(CASE WHEN sm.metric_name = 'L_SESSION_ENGAGEMENT' THEN sm.metric_value END) AS L
    FROM session_metrics sm
    JOIN sessions s ON sm.session_id = s.id
    WHERE s.player_id = %s
    GROUP BY sm.session_id
    ORDER BY s.session_start
    """

    cursor.execute(query, (player_id,))
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data

def build_time_axis(sessions):
    return list(range(len(sessions)))

def calc_ev(Y):
    return list(Y)

def calc_pgr(K, dt=1):
    pgr = [0]
    for i in range(1, len(K)):
        pgr.append((K[i] - K[i-1]) / dt)
    return pgr

def calc_dr(K):
    dr = [0]
    for i in range(1, len(K)):
        if K[i-1] == 0:
            dr.append(0)
        else:
            dr.append((K[i-1] - K[i]) / K[i-1])
    return dr

def calculate_lyapunov(Y, epsilon=1e-5):

    Y = np.array(Y)

    Y1 = Y
    Y2 = Y + epsilon

    divergences = []

    for i in range(len(Y)):
        d = abs(Y2[i] - Y1[i])
        if d == 0:
            d = epsilon
        divergences.append(np.log(d / epsilon))

        # добавляем накопление ошибки
        Y2[i:] += d * 0.01

    return float(np.mean(divergences))

def detect_bifurcations(values):

    values = np.array(values)

    if len(values) < 5:
        return []

    velocity = np.diff(values)

    acceleration = np.diff(velocity)

    threshold = np.std(acceleration) * 1.5

    bif_points = []

    for i, acc in enumerate(acceleration):

        if abs(acc) > threshold:
            bif_points.append(i + 1)

    return bif_points

def analyze_player(player_id):
    try:
        sessions = load_player_sessions(player_id)

        K = [float(s["K"] or 0) for s in sessions]
        Y = [float(s["Y"] or 0) for s in sessions]

        time = build_time_axis(sessions)

        EV = calc_ev(Y)
        PGR = calc_pgr(K)
        DR = calc_dr(K)

        lyap = calculate_lyapunov(Y)
        bif = detect_bifurcations(PGR)

        return {
            "labels": time,
            "K": K,
            "Y": Y,
            "EV": EV,
            "PGR": PGR,
            "DR": DR,
            "lyapunov": lyap,
            "bifurcation_points": bif
        }

    except Exception as e:
        print("ANALYSIS ERROR:", e)
        return {
            "labels": [],
            "K": [],
            "Y": [],
            "EV": [],
            "PGR": [],
            "DR": [],
            "lyapunov": 0,
            "bifurcation_points": []
        }