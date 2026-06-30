import mysql.connector

try:
    from backend.stability_analysis import (
        analyze_stability,
        analyze_single_series_stability
    )
    from backend.practical_insights import generate_practical_insights
except ImportError:
    from stability_analysis import (
        analyze_stability,
        analyze_single_series_stability
    )
    from practical_insights import generate_practical_insights

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}


# Служебное значение из UI: строить не отдельного игрока,
# а усреднённую траекторию по всем игрокам.
ALL_PLAYERS_ID = "__ALL_PLAYERS__"


TEMPLATE_METRICS = {
    "progression_decay": [
        "EV",
        "PGR",
        "DR"
    ],
    "resource_flow": [
        "RF_RESOURCE_FLOW",
        "SSR_SPEND_SHARE",
        "RI_RESOURCE_INFLATION"
    ],
    "resource_conversion": [
        "PE_PROGRESSION_EFFICIENCY",
        "ROI_RESOURCE_TO_POWER",
        "POWER_COST"
    ],
    "engagement_resource": [
        "APM_ACTIONS_PER_MINUTE",
        "TIME_EFFICIENCY",
        "GRIND_FACTOR"
    ]
}


DEFAULT_METRIC_LABELS = {
    "EV": "Скорость прогрессии",
    "PGR": "Темп роста силы",
    "DR": "Деградация прогрессии",
    # Legacy-названия оставлены только для чтения старых projects.json/session_metrics.
    "Y_EXP_VELOCITY": "Скорость прогрессии",
    "K_POWER_SCORE": "Условная сила игрока",
    "S_UNSPENT_RESOURCES": "Доля неиспользованных ресурсов",
    "D_PROGRESSION_DECAY": "Снижение эффективности прогрессии",
    "A_PROGRESSION_ROI": "Эффективность вложений в прогрессию",
    "RF_RESOURCE_FLOW": "Чистый ресурсный поток",
    "SSR_SPEND_SHARE": "Доля расхода",
    "RI_RESOURCE_INFLATION": "Изменение ресурса",
    "PE_PROGRESSION_EFFICIENCY": "Эффективность прогрессии",
    "ROI_RESOURCE_TO_POWER": "ROI ресурсов в силу",
    "POWER_COST": "Стоимость единицы силы",
    "APM_ACTIONS_PER_MINUTE": "Интенсивность действий",
    "TIME_EFFICIENCY": "Эффективность времени",
    "GRIND_FACTOR": "Гринд-фактор",
    "K": "K(t)",
    "Y": "Y(t)"
}


def get_project_template_id(project):
    if not project:
        return "progression_decay"

    return (
        project.get("selected_template")
        or project.get("binding_config", {}).get("template_id")
        or "progression_decay"
    )


def get_project_metric_labels(project):
    labels = {}

    if project:
        labels.update(project.get("metric_labels") or {})
        labels.update(project.get("binding_config", {}).get("metric_labels") or {})

    return labels


def get_project_metric_order(project):
    """
    Возвращает только метрики выбранного шаблона.

    Раньше при наличии formula_config мы брали все его ключи подряд.
    Из-за этого после переключения шаблона в графики попадали старые
    прогрессионные метрики из предыдущего состояния bindingDraft / projects.json.
    Теперь formula_config влияет на формулы, но не расширяет набор линий
    графика за пределы выбранного шаблона.
    """

    template_id = get_project_template_id(project)
    template_metrics = TEMPLATE_METRICS.get(
        template_id,
        TEMPLATE_METRICS["progression_decay"]
    )

    formula_config = {}

    if project:
        formula_config.update(project.get("formula_config") or {})
        formula_config.update(project.get("binding_config", {}).get("formula_config") or {})

    if formula_config:
        filtered_metrics = [
            metric_key
            for metric_key in template_metrics
            if metric_key in formula_config
        ]

        if filtered_metrics:
            return filtered_metrics

    return list(template_metrics)


def load_player_sessions(player_id):
    """
    Legacy-загрузка для старой прогрессионной визуализации.
    Оставлена как fallback для совместимости с предыдущим UI.
    """

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


def load_player_metric_rows(player_id):
    """
    Загружает все рассчитанные session_metrics игрока без привязки
    к конкретному шаблону. Выбор выводимых рядов выполняется уже
    на уровне project.selected_template / project.formula_config.
    """

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        s.id AS session_id,
        s.session_start,
        sm.metric_name,
        sm.metric_value
    FROM sessions s
    LEFT JOIN session_metrics sm
        ON sm.session_id = s.id
       AND sm.player_id = s.player_id
    WHERE s.player_id = %s
    ORDER BY s.session_start, sm.metric_name
    """

    cursor.execute(query, (player_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    sessions = []
    index_by_session = {}

    for row in rows:
        session_id = row["session_id"]

        if session_id not in index_by_session:
            index_by_session[session_id] = len(sessions)
            sessions.append({
                "session_id": session_id,
                "session_start": row.get("session_start"),
                "metrics": {}
            })

        metric_name = row.get("metric_name")

        if metric_name:
            sessions[index_by_session[session_id]]["metrics"][metric_name] = float(
                row.get("metric_value") or 0
            )

    return sessions



def load_all_players_metric_rows():
    """
    Загружает session_metrics всех игроков.

    Данные возвращаются сгруппированными по игрокам, чтобы затем
    построить среднюю траекторию по порядковому номеру сессии игрока:
    первая сессия всех игроков, вторая сессия всех игроков и т.д.
    Такой подход лучше подходит для геймдизайн-анализа прогрессии,
    чем смешивание всех сессий по календарному времени.
    """

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        s.player_id,
        s.id AS session_id,
        s.session_start,
        sm.metric_name,
        sm.metric_value
    FROM sessions s
    LEFT JOIN session_metrics sm
        ON sm.session_id = s.id
       AND sm.player_id = s.player_id
    ORDER BY s.player_id, s.session_start, sm.metric_name
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    players = {}
    index_by_player_session = {}

    for row in rows:
        player_id = row["player_id"]
        session_id = row["session_id"]

        if player_id not in players:
            players[player_id] = []
            index_by_player_session[player_id] = {}

        if session_id not in index_by_player_session[player_id]:
            index_by_player_session[player_id][session_id] = len(players[player_id])
            players[player_id].append({
                "session_id": session_id,
                "session_start": row.get("session_start"),
                "metrics": {}
            })

        metric_name = row.get("metric_name")

        if metric_name:
            session_index = index_by_player_session[player_id][session_id]
            players[player_id][session_index]["metrics"][metric_name] = float(
                row.get("metric_value") or 0
            )

    return players


def build_all_players_average_sessions(metric_order):
    """
    Строит усреднённый ряд по всем игрокам.

    Точка i на графике = среднее значение выбранной метрики на i-й
    сессии каждого игрока. Игроки, у которых нет i-й сессии, в этой
    точке не участвуют. Это сохраняет относительную логику прогрессии:
    сравниваются не календарные даты, а этапы прохождения игроком игры.
    """

    players = load_all_players_metric_rows()

    if not players:
        return []

    max_sessions = max(
        len(sessions)
        for sessions in players.values()
    )

    average_sessions = []

    for session_index in range(max_sessions):
        participant_sessions = [
            sessions[session_index]
            for sessions in players.values()
            if session_index < len(sessions)
        ]

        metrics = {}

        for metric_key in metric_order:
            values = [
                float(session["metrics"].get(metric_key, 0) or 0)
                for session in participant_sessions
            ]

            metrics[metric_key] = sum(values) / len(values) if values else 0.0

        average_sessions.append({
            "session_id": f"all_players_mean_{session_index}",
            "session_start": None,
            "players_count": len(participant_sessions),
            "metrics": metrics
        })

    return average_sessions


def build_time_axis(sessions):
    return list(range(len(sessions)))


def calc_ev(Y):
    return list(Y)


def calc_pgr(K, dt=1):
    pgr = [0]
    for i in range(1, len(K)):
        pgr.append((K[i] - K[i - 1]) / dt)
    return pgr


def calc_dr(K):
    dr = [0]
    for i in range(1, len(K)):
        if K[i - 1] == 0:
            dr.append(0)
        else:
            dr.append((K[i - 1] - K[i]) / K[i - 1])
    return dr


def calculate_lyapunov(values, epsilon=1e-5):
    """
    Совместимость со старым кодом.

    Реальный расчёт теперь вынесен в stability_analysis.py и основан
    на дискретной оценке расходимости близких состояний, а не на
    искусственно сдвинутой копии ряда.
    """

    result = analyze_single_series_stability(
        values,
        epsilon=epsilon
    )

    return result["lyapunov"] if result["lyapunov"] is not None else 0.0


def detect_bifurcations(values):
    """Совместимость со старым fallback-анализом."""

    result = analyze_single_series_stability(values)
    return result.get("bifurcation_points", [])

def choose_primary_series(metric_order, values_by_metric):
    preferred = [
        "EV",
        "PGR",
        "RF_RESOURCE_FLOW",
        "ROI_RESOURCE_TO_POWER",
        "TIME_EFFICIENCY",
        "APM_ACTIONS_PER_MINUTE"
    ]

    for key in preferred:
        if key in values_by_metric:
            return values_by_metric[key]

    for key in metric_order:
        if key in values_by_metric:
            return values_by_metric[key]

    return []


def make_dataset(metric_key, label, values, axis_index):
    axis_cycle = ["y", "y1", "y2"]

    return {
        "label": label,
        "metric_key": metric_key,
        "data": values,
        "yAxisID": axis_cycle[axis_index % len(axis_cycle)],
        "borderWidth": 2
    }


def analyze_project_player(project, player_id):
    """
    Новый динамический анализ.

    Возвращает не фиксированные K/Y/EV/PGR/DR, а набор datasets,
    соответствующий выбранному шаблону проекта и реально рассчитанным
    metric_name из session_metrics.
    """

    try:
        template_id = get_project_template_id(project)
        metric_order = get_project_metric_order(project)
        metric_labels = get_project_metric_labels(project)

        if player_id == ALL_PLAYERS_ID:
            sessions = build_all_players_average_sessions(metric_order)
            analysis_scope = "all_players_average"
        else:
            sessions = load_player_metric_rows(player_id)
            analysis_scope = "single_player"

        labels = build_time_axis(sessions)

        values_by_metric = {}

        for metric_key in metric_order:
            values_by_metric[metric_key] = [
                float(session["metrics"].get(metric_key, 0) or 0)
                for session in sessions
            ]

        datasets = []

        for index, metric_key in enumerate(metric_order):
            values = values_by_metric.get(metric_key, [])

            # Не скрываем полностью нулевые ряды: нулевая метрика тоже
            # может быть корректным результатом формулы.
            label = metric_labels.get(
                metric_key,
                DEFAULT_METRIC_LABELS.get(metric_key, metric_key)
            )

            datasets.append(
                make_dataset(metric_key, label, values, index)
            )

        stability = analyze_stability(
            values_by_metric=values_by_metric,
            metric_order=metric_order
        )

        lyapunov = stability.get("lyapunov")
        bifurcation_points = stability.get("bifurcation_points", [])

        practical_insights = generate_practical_insights(
            template_id=template_id,
            values_by_metric=values_by_metric,
            metric_order=metric_order,
            metric_labels=metric_labels,
            stability=stability,
            analysis_scope=analysis_scope
        )

        return {
            "success": True,
            "mode": "dynamic_template",
            "scope": analysis_scope,
            "template_id": template_id,
            "labels": labels,
            "datasets": datasets,
            "metric_order": metric_order,
            "metric_labels": metric_labels,
            "lyapunov": lyapunov,
            "bifurcation_points": bifurcation_points,
            "stability_status": stability.get("status", "unknown"),
            "stability_text": stability.get("text", "Состояние системы не определено"),
            "stability_details": {
                "sessions_count": stability.get("sessions_count", len(labels)),
                "metrics_count": stability.get("metrics_count", len(metric_order)),
                "scope": analysis_scope
            },
            "practical_insights": practical_insights,

            # Совместимость со старым UI/отладкой.
            "K": values_by_metric.get("K_POWER_SCORE", []),
            "Y": values_by_metric.get("Y_EXP_VELOCITY", []),
            "EV": values_by_metric.get("EV") or values_by_metric.get("Y_EXP_VELOCITY", []),
            "PGR": values_by_metric.get("PGR") or (calc_pgr(values_by_metric.get("K_POWER_SCORE", [])) if values_by_metric.get("K_POWER_SCORE") else []),
            "DR": values_by_metric.get("DR") or (calc_dr(values_by_metric.get("K_POWER_SCORE", [])) if values_by_metric.get("K_POWER_SCORE") else [])
        }

    except Exception as e:
        print("DYNAMIC ANALYSIS ERROR:", e)

        return {
            "success": False,
            "mode": "dynamic_template",
            "scope": "all_players_average" if player_id == ALL_PLAYERS_ID else "single_player",
            "template_id": get_project_template_id(project),
            "labels": [],
            "datasets": [],
            "metric_order": [],
            "metric_labels": {},
            "lyapunov": None,
            "bifurcation_points": [],
            "stability_status": "error",
            "stability_text": "Ошибка оценки устойчивости",
            "stability_details": {},
            "practical_insights": [],
            "message": "Ошибка динамического анализа",
            "details": str(e),
            "K": [],
            "Y": [],
            "EV": [],
            "PGR": [],
            "DR": []
        }


def analyze_player(player_id):
    """
    Старый анализ оставлен как legacy/fallback.
    """

    try:
        sessions = load_player_sessions(player_id)

        K = [float(s["K"] or 0) for s in sessions]
        Y = [float(s["Y"] or 0) for s in sessions]

        time = build_time_axis(sessions)

        EV = calc_ev(Y)
        PGR = calc_pgr(K)
        DR = calc_dr(K)

        stability = analyze_stability(
            values_by_metric={
                "Y_EXP_VELOCITY": Y,
                "K_POWER_SCORE": K
            },
            metric_order=[
                "Y_EXP_VELOCITY",
                "K_POWER_SCORE"
            ]
        )

        lyap = stability.get("lyapunov")
        bif = stability.get("bifurcation_points", [])

        values_by_metric = {
            "Y_EXP_VELOCITY": Y,
            "K_POWER_SCORE": K,
            "EV": EV,
            "PGR": PGR,
            "DR": DR
        }

        practical_insights = generate_practical_insights(
            template_id="progression_decay",
            values_by_metric=values_by_metric,
            metric_order=[
                "Y_EXP_VELOCITY",
                "K_POWER_SCORE",
                "EV",
                "PGR",
                "DR"
            ],
            metric_labels=DEFAULT_METRIC_LABELS,
            stability=stability,
            analysis_scope="single_player"
        )

        return {
            "success": True,
            "mode": "legacy_progression",
            "labels": time,
            "K": K,
            "Y": Y,
            "EV": EV,
            "PGR": PGR,
            "DR": DR,
            "datasets": [
                make_dataset("K_POWER_SCORE", "K(t)", K, 0),
                make_dataset("Y_EXP_VELOCITY", "Y(t)", Y, 1),
                make_dataset("EV", "EV", EV, 1),
                make_dataset("PGR", "PGR", PGR, 2),
                make_dataset("DR", "DR", DR, 2)
            ],
            "lyapunov": lyap,
            "bifurcation_points": bif,
            "stability_status": stability.get("status", "unknown"),
            "stability_text": stability.get("text", "Состояние системы не определено"),
            "stability_details": {
                "sessions_count": stability.get("sessions_count", len(time)),
                "metrics_count": stability.get("metrics_count", 2)
            },
            "practical_insights": practical_insights
        }

    except Exception as e:
        print("ANALYSIS ERROR:", e)
        return {
            "success": False,
            "mode": "legacy_progression",
            "labels": [],
            "K": [],
            "Y": [],
            "EV": [],
            "PGR": [],
            "DR": [],
            "datasets": [],
            "lyapunov": None,
            "bifurcation_points": [],
            "stability_status": "error",
            "stability_text": "Ошибка оценки устойчивости",
            "stability_details": {},
            "practical_insights": [],
            "message": "Ошибка анализа",
            "details": str(e)
        }
