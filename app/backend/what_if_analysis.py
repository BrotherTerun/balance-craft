"""
Подготовка источников и контролов для What-if анализа BalanceCraft.

P7.1 не строит прогноз и не изменяет базу данных. Модуль только читает
семантические привязки проекта и подбирает изменяемые параметры, которые
могут влиять на выбранные пользователем переменные шаблона.
"""

import json
import math
import random
import hashlib
from decimal import Decimal

import mysql.connector

try:
    from backend.progression_model import (
        analyze_project_player,
        get_project_metric_order,
        get_project_metric_labels,
        get_project_template_id,
        DEFAULT_METRIC_LABELS
    )
    from backend.stability_analysis import analyze_stability
    from backend.practical_insights import generate_practical_insights
except ImportError:
    from progression_model import (
        analyze_project_player,
        get_project_metric_order,
        get_project_metric_labels,
        get_project_template_id,
        DEFAULT_METRIC_LABELS
    )
    from stability_analysis import analyze_stability
    from practical_insights import generate_practical_insights


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "2256",
    "database": "monitor_rpg_model"
}


VARIABLE_LABELS = {
    "progression_decay": {
        "flow_in": "Входящий поток прогрессии",
        "flow_out": "Расход / потери прогрессии",
        "duration": "Длительность окна анализа",
        "engagement": "Активность игрока"
    },
    "resource_flow": {
        "resource_income": "Доход ресурса",
        "resource_spend": "Расход ресурса",
        "duration": "Длительность окна анализа"
    },
    "resource_conversion": {
        "resource_cost": "Стоимость действия",
        "power_gain": "Прирост силы",
        "action_count": "Количество действий"
    },
    "engagement_resource": {
        "action_count": "Количество действий",
        "reward": "Полученная награда",
        "duration": "Длительность окна анализа"
    }
}


TABLE_LABELS = {
    "items": "Предметы",
    "skills": "Навыки",
    "players": "Игроки",
    "sessions": "Сессии"
}


FIELD_LABELS = {
    "gear_score": "Сила предмета",
    "skill_score": "Сила навыка",
    "total_xp": "Накопленный ресурс игрока",
    "avg_apm": "Средняя активность в минуту"
}


NUMERIC_TYPES = {
    "int",
    "bigint",
    "smallint",
    "tinyint",
    "mediumint",
    "decimal",
    "float",
    "double"
}


def to_float(value, default=0.0):
    if isinstance(value, Decimal):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_template_id(project):
    if not project:
        return "progression_decay"

    return (
        project.get("selected_template")
        or project.get("binding_config", {}).get("selected_template")
        or project.get("binding_config", {}).get("template_id")
        or "progression_decay"
    )


def get_semantic_bindings(project):
    bindings = {}

    if not project:
        return bindings

    bindings.update(project.get("semantic_bindings") or {})

    binding_config = project.get("binding_config") or {}
    bindings.update(binding_config.get("semantic_bindings") or {})

    return bindings



def normalize_semantic_binding(binding):
    if not binding:
        return {
            "source": "",
            "event_types": [],
            "aggregation": "sum"
        }

    if isinstance(binding, str):
        return {
            "source": binding,
            "event_types": [],
            "aggregation": "sum"
        }

    if isinstance(binding, dict):
        event_types = binding.get("event_types") or binding.get("eventTypes") or []

        if not isinstance(event_types, list):
            event_types = []

        return {
            "source": str(binding.get("source") or binding.get("path") or ""),
            "event_types": [str(item) for item in event_types if item],
            "aggregation": str(binding.get("aggregation") or "sum")
        }

    return {
        "source": "",
        "event_types": [],
        "aggregation": "sum"
    }


def get_binding_source(binding):
    return normalize_semantic_binding(binding).get("source", "")


def get_binding_event_types(binding):
    return normalize_semantic_binding(binding).get("event_types", [])


def get_variable_label(template_id, variable_key):
    return (
        VARIABLE_LABELS
        .get(template_id, {})
        .get(variable_key, variable_key)
    )


def connect_database():
    return mysql.connector.connect(**DB_CONFIG)


def get_column_meta(cursor, table_name, field_name):
    cursor.execute(
        """
        SELECT
            COLUMN_NAME,
            DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, field_name)
    )

    return cursor.fetchone()


def table_has_column(cursor, table_name, field_name):
    return bool(get_column_meta(cursor, table_name, field_name))


def is_numeric_column(cursor, table_name, field_name):
    meta = get_column_meta(cursor, table_name, field_name)

    if not meta:
        return False

    return str(meta.get("DATA_TYPE", "")).lower() in NUMERIC_TYPES


def classify_source_path(source_path):
    source_path = str(source_path or "").strip()

    if not source_path:
        return {
            "kind": "missing",
            "table": "",
            "field": "",
            "attribute": ""
        }

    parts = source_path.split(".")

    if len(parts) >= 2 and parts[0] in {"items", "skills", "players", "sessions"}:
        return {
            "kind": "table_field",
            "table": parts[0],
            "field": parts[1],
            "attribute": ""
        }

    if source_path.startswith("events.event_data."):
        return {
            "kind": "event_signal",
            "table": "events",
            "field": "event_data",
            "attribute": source_path.replace("events.event_data.", "", 1)
        }

    if source_path.startswith("computed."):
        return {
            "kind": "computed_signal",
            "table": "computed",
            "field": source_path.replace("computed.", "", 1),
            "attribute": ""
        }

    return {
        "kind": "unknown",
        "table": "",
        "field": "",
        "attribute": ""
    }



FORMULA_FUNCTION_NAMES = {
    "sum", "count", "max", "min", "abs"
}


def event_matches_variable(event_type, variable_key):
    """
    Отделяет одно и то же числовое поле event_data.value по смыслу переменной.

    В пресетной настройке несколько переменных могут ссылаться на один путь
    events.event_data.value. Без фильтрации flow_in и flow_out получают одну и
    ту же среднюю базу, поэтому what-if прогноз почти не реагирует на ползунки.
    Здесь мы используем тип события как минимальный семантический фильтр.
    """

    event_type = str(event_type or "").lower()
    variable_key = str(variable_key or "").lower()

    income_like_variables = {
        "flow_in",
        "resource_income",
        "power_gain",
        "reward"
    }

    spend_like_variables = {
        "flow_out",
        "resource_spend",
        "resource_cost"
    }

    if variable_key in income_like_variables:
        return any(marker in event_type for marker in (
            "gain",
            "income",
            "reward",
            "earn",
            "loot",
            "equip",
            "learn",
            "upgrade",
            "power"
        ))

    if variable_key in spend_like_variables:
        return any(marker in event_type for marker in (
            "spend",
            "cost",
            "purchase",
            "buy",
            "loss",
            "decay",
            "out"
        ))

    return True


def extract_formula_names(expression):
    import ast

    if not expression or not str(expression).strip():
        return set()

    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError:
        return set()

    names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in FORMULA_FUNCTION_NAMES:
                names.add(node.id)

    return names


def get_formula_config(project):
    formulas = {}

    if not project:
        return formulas

    formulas.update(project.get("formula_config") or {})
    formulas.update((project.get("binding_config") or {}).get("formula_config") or {})

    return formulas


def get_formula_used_variables(project, bindings):
    """
    Возвращает переменные, реально встречающиеся в формулах выбранного шаблона.
    Если формулы не найдены или их не удалось разобрать, возвращаем все bindings,
    чтобы не сломать старые проекты.
    """

    formulas = get_formula_config(project)

    if not formulas:
        return set(bindings.keys())

    formula_names = set()

    for expression in formulas.values():
        formula_names.update(extract_formula_names(expression))

    used = set(bindings.keys()) & formula_names

    if not used:
        return set(bindings.keys())

    return used


def build_formula_unused_control(variable_key, variable_label, source_path):
    return {
        "type": "unsupported",
        "variable_key": variable_key,
        "variable_label": variable_label,
        "source_path": source_path,
        "source_kind": "formula_unused",
        "message": (
            "Переменная назначена в мастере семантики, но не используется "
            "в формулах выбранного шаблона. Её ползунок не влияет на прогноз."
        )
    }

def slider_limits(value):
    value = to_float(value)

    if value == 0:
        return {
            "min": -100,
            "max": 100,
            "step": 1
        }

    span = max(abs(value) * 2, 1)

    step = 1
    if abs(value) < 10:
        step = 0.1

    return {
        "min": round(value - span, 4),
        "max": round(value + span, 4),
        "step": step
    }


def build_entity_table_control(cursor, variable_key, variable_label, source_path, source_info):
    table_name = source_info["table"]
    field_name = source_info["field"]

    if not is_numeric_column(cursor, table_name, field_name):
        return {
            "type": "unsupported",
            "variable_key": variable_key,
            "variable_label": variable_label,
            "source_path": source_path,
            "source_kind": "table_field",
            "message": "Поле найдено, но не является числовым, поэтому не может быть использовано как what-if параметр."
        }

    name_column = "name" if table_has_column(cursor, table_name, "name") else None
    id_column = "id" if table_has_column(cursor, table_name, "id") else None

    if not id_column:
        return {
            "type": "unsupported",
            "variable_key": variable_key,
            "variable_label": variable_label,
            "source_path": source_path,
            "source_kind": "table_field",
            "message": "В таблице нет поля id, поэтому невозможно безопасно связать ползунок с сущностью."
        }

    display_column_sql = f"`{name_column}`" if name_column else f"`{id_column}`"

    cursor.execute(
        f"""
        SELECT
            `{id_column}` AS entity_id,
            {display_column_sql} AS entity_name,
            `{field_name}` AS value
        FROM `{table_name}`
        WHERE `{field_name}` IS NOT NULL
        ORDER BY `{field_name}` DESC, entity_name
        LIMIT 80
        """
    )

    rows = cursor.fetchall()
    entity_controls = []

    for row in rows:
        value = to_float(row.get("value"))
        limits = slider_limits(value)

        entity_controls.append({
            "control_id": f"{table_name}.{field_name}:{row.get('entity_id')}",
            "entity_id": str(row.get("entity_id")),
            "entity_name": str(row.get("entity_name") or row.get("entity_id")),
            "original_value": value,
            "current_value": value,
            "min": limits["min"],
            "max": limits["max"],
            "step": limits["step"]
        })

    return {
        "type": "entity_table",
        "variable_key": variable_key,
        "variable_label": variable_label,
        "source_path": source_path,
        "source_kind": "table_field",
        "table": table_name,
        "table_label": TABLE_LABELS.get(table_name, table_name),
        "field": field_name,
        "field_label": FIELD_LABELS.get(field_name, field_name),
        "mode": "entity_value_override",
        "description": (
            "Изменение значений отдельных сущностей справочника. "
            "База данных не изменяется: значения используются только для будущего сценарного прогноза."
        ),
        "controls": entity_controls
    }


def build_table_aggregate_control(cursor, variable_key, variable_label, source_path, source_info):
    table_name = source_info["table"]
    field_name = source_info["field"]

    if not is_numeric_column(cursor, table_name, field_name):
        return {
            "type": "unsupported",
            "variable_key": variable_key,
            "variable_label": variable_label,
            "source_path": source_path,
            "source_kind": "table_field",
            "message": "Поле найдено, но не является числовым."
        }

    cursor.execute(
        f"""
        SELECT AVG(`{field_name}`) AS avg_value,
               COUNT(*) AS rows_count
        FROM `{table_name}`
        WHERE `{field_name}` IS NOT NULL
        """
    )

    row = cursor.fetchone() or {}
    base_value = to_float(row.get("avg_value"))

    return build_multiplier_control(
        variable_key=variable_key,
        variable_label=variable_label,
        source_path=source_path,
        source_kind="table_field",
        base_value=base_value,
        base_label=f"Оценка мат. ожидания поля {table_name}.{field_name}",
        description=(
            "Агрегированный параметр таблицы. Используется как сценарное допущение, "
            "не изменяющее исторические данные и записи БД."
        ),
        details={
            "table": table_name,
            "field": field_name,
            "rows_count": int(row.get("rows_count") or 0)
        }
    )


def parse_event_data(value):
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}

    return {}



def estimate_expected_value(values, recency_weighted=True):
    """
    Оценивает математическое ожидание наблюдаемого сигнала по
    эмпирическому распределению временного ряда.

    Это не простое "среднее по всем событиям". Для прогноза используется
    сессионный ряд значений, а вероятности наблюдений задаются весами.
    Более свежие сессии получают больший вес, поскольку они лучше отражают
    текущее состояние баланса.
    """

    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None and math.isfinite(to_float(value))
    ]

    if not prepared:
        return 0.0

    if not recency_weighted or len(prepared) == 1:
        probability = 1.0 / len(prepared)
        return float(sum(value * probability for value in prepared))

    weights = list(range(1, len(prepared) + 1))
    weight_sum = float(sum(weights))

    return float(
        sum(value * weight / weight_sum for value, weight in zip(prepared, weights))
    )


def estimate_weighted_std(values, expected_value=None):
    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None and math.isfinite(to_float(value))
    ]

    if len(prepared) < 2:
        return 0.0

    mu = estimate_expected_value(prepared) if expected_value is None else to_float(expected_value)
    weights = list(range(1, len(prepared) + 1))
    weight_sum = float(sum(weights))
    variance = sum(
        weight * ((value - mu) ** 2)
        for value, weight in zip(prepared, weights)
    ) / weight_sum

    return float(math.sqrt(max(variance, 0.0)))


def build_delta_series(values):
    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None and math.isfinite(to_float(value))
    ]

    if len(prepared) < 2:
        return []

    return [
        prepared[index] - prepared[index - 1]
        for index in range(1, len(prepared))
    ]


def estimate_expected_delta(values):
    deltas = build_delta_series(values)

    if not deltas:
        return 0.0

    return estimate_expected_value(deltas)


def estimate_delta_std(values, expected_delta=None):
    """
    Оценивает стандартное отклонение случайных приращений ΔX_t.

    Именно эта величина используется в стохастической AR(1)-модели
    what-if прогноза как σ_{Δ,j}, а не разброс самих значений X_t.
    """

    deltas = build_delta_series(values)

    if len(deltas) < 2:
        return 0.0

    mu_delta = (
        estimate_expected_value(deltas)
        if expected_delta is None
        else to_float(expected_delta)
    )

    weights = list(range(1, len(deltas) + 1))
    weight_sum = float(sum(weights))

    variance = sum(
        weight * ((delta - mu_delta) ** 2)
        for delta, weight in zip(deltas, weights)
    ) / weight_sum

    return float(math.sqrt(max(variance, 0.0)))


def aggregate_values(values, aggregation='sum'):
    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None and math.isfinite(to_float(value))
    ]

    if not prepared:
        return 0.0

    aggregation = str(aggregation or 'sum').lower()

    if aggregation in {'mean', 'avg', 'average'}:
        return estimate_expected_value(prepared, recency_weighted=False)

    if aggregation == 'count':
        return float(len(prepared))

    if aggregation == 'min':
        return float(min(prepared))

    if aggregation == 'max':
        return float(max(prepared))

    return float(sum(prepared))


def get_event_signal_session_series(cursor, attribute_name, event_types=None, aggregation='sum', limit_sessions=120):
    scoped_event_types = set(event_types or [])

    cursor.execute(
        """
        SELECT
            s.id AS session_id,
            s.session_start,
            e.event_type,
            e.event_data
        FROM sessions s
        LEFT JOIN events e
            ON e.session_id = s.id
        ORDER BY s.session_start, e.timestamp
        """
    )

    sessions = []
    index_by_session = {}

    for row in cursor.fetchall():
        session_id = row.get('session_id')

        if session_id not in index_by_session:
            index_by_session[session_id] = len(sessions)
            sessions.append({
                'session_id': session_id,
                'values': []
            })

        if not row.get('event_type'):
            continue

        if scoped_event_types and str(row.get('event_type') or '') not in scoped_event_types:
            continue

        data = parse_event_data(row.get('event_data'))

        if attribute_name not in data:
            continue

        raw_value = data.get(attribute_name)

        try:
            sessions[index_by_session[session_id]]['values'].append(float(raw_value))
        except (TypeError, ValueError):
            continue

    series = [
        aggregate_values(session['values'], aggregation)
        for session in sessions
        if session.get('values')
    ]

    if limit_sessions and len(series) > limit_sessions:
        series = series[-limit_sessions:]

    return series


def estimate_series_profile(values):
    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None and math.isfinite(to_float(value))
    ]

    expected = estimate_expected_value(prepared)
    std = estimate_weighted_std(prepared, expected)
    expected_delta = estimate_expected_delta(prepared)
    delta_std = estimate_delta_std(prepared, expected_delta)

    return {
        'series': prepared,
        'expected_value': expected,
        'std': std,
        'expected_delta': expected_delta,
        'delta_std': delta_std,
        'samples_count': len(prepared),
        'last_value': prepared[-1] if prepared else expected
    }


def get_event_signal_expectation(cursor, attribute_name, event_types=None, aggregation='sum'):
    series = get_event_signal_session_series(
        cursor,
        attribute_name,
        event_types=event_types,
        aggregation=aggregation
    )

    return estimate_series_profile(series)


def get_computed_signal_series(cursor, field_name):
    if field_name == "duration_minutes":
        cursor.execute(
            """
            SELECT
                GREATEST(
                    TIMESTAMPDIFF(SECOND, session_start, session_end) / 60,
                    1
                ) AS value
            FROM sessions
            WHERE session_start IS NOT NULL
              AND session_end IS NOT NULL
            ORDER BY session_start
            """
        )

        return [to_float(row.get('value')) for row in cursor.fetchall()]

    if field_name == "action_count":
        cursor.execute(
            """
            SELECT COUNT(e.id) AS value
            FROM sessions s
            LEFT JOIN events e
                ON e.session_id = s.id
            GROUP BY s.id, s.session_start
            ORDER BY s.session_start
            """
        )

        return [to_float(row.get('value')) for row in cursor.fetchall()]

    return []


def get_computed_signal_expectation(cursor, field_name):
    return estimate_series_profile(
        get_computed_signal_series(cursor, field_name)
    )


def build_multiplier_control(variable_key, variable_label, source_path, source_kind, base_value, base_label, description, details=None):
    return {
        "type": "signal_multiplier",
        "variable_key": variable_key,
        "variable_label": variable_label,
        "source_path": source_path,
        "source_kind": source_kind,
        "mode": "multiplier",
        "base_value": to_float(base_value),
        "base_label": base_label,
        "min_percent": 0,
        "max_percent": 200,
        "step_percent": 5,
        "current_percent": 100,
        "description": description,
        "details": details or {}
    }



def build_event_signal_control(cursor, variable_key, variable_label, source_path, source_info, binding=None):
    attribute_name = source_info.get("attribute")
    event_types = get_binding_event_types(binding)
    binding_config = normalize_semantic_binding(binding)
    aggregation = binding_config.get("aggregation", "sum")
    profile = get_event_signal_expectation(
        cursor,
        attribute_name,
        event_types,
        aggregation
    )

    event_type_text = ", ".join(event_types) if event_types else "все события"

    control = build_multiplier_control(
        variable_key=variable_key,
        variable_label=variable_label,
        source_path=source_path,
        source_kind="event_signal",
        base_value=profile.get("expected_value", 0.0),
        base_label=f"Оценка мат. ожидания {source_path} по event_type: {event_type_text}",
        description=(
            "У этого сигнала нет справочника сущностей. Ползунок задаёт сценарное допущение: "
            "насколько изменится ожидаемый будущий поток относительно исторической оценки. "
            "Для events.event_data.* учитываются только типы событий, выбранные на 4 шаге мастера семантики."
        ),
        details={
            "attribute": attribute_name,
            "event_types": event_types,
            "aggregation": aggregation,
            "samples_count": profile.get("samples_count", 0),
            "expected_value": profile.get("expected_value", 0.0),
            "expected_delta": profile.get("expected_delta", 0.0),
            "std": profile.get("std", 0.0),
            "delta_std": profile.get("delta_std", 0.0),
            "forecast_series": profile.get("series", [])[-20:]
        }
    )

    control["forecast_profile"] = {
        "series": profile.get("series", [])[-20:],
        "expected_value": profile.get("expected_value", 0.0),
        "expected_delta": profile.get("expected_delta", 0.0),
        "std": profile.get("std", 0.0),
        "delta_std": profile.get("delta_std", 0.0),
        "samples_count": profile.get("samples_count", 0),
        "last_value": profile.get("last_value", profile.get("expected_value", 0.0))
    }

    return control



def build_computed_signal_control(cursor, variable_key, variable_label, source_path, source_info):
    field_name = source_info.get("field")
    profile = get_computed_signal_expectation(cursor, field_name)

    control = build_multiplier_control(
        variable_key=variable_key,
        variable_label=variable_label,
        source_path=source_path,
        source_kind="computed_signal",
        base_value=profile.get("expected_value", 0.0),
        base_label=f"Оценка мат. ожидания {source_path}",
        description=(
            "Расчётное поле не хранится как отдельная сущность. Ползунок меняет "
            "будущее допущение по этому параметру, не затрагивая историю."
        ),
        details={
            "field": field_name,
            "samples_count": profile.get("samples_count", 0),
            "expected_value": profile.get("expected_value", 0.0),
            "expected_delta": profile.get("expected_delta", 0.0),
            "std": profile.get("std", 0.0),
            "delta_std": profile.get("delta_std", 0.0),
            "forecast_series": profile.get("series", [])[-20:]
        }
    )

    control["forecast_profile"] = {
        "series": profile.get("series", [])[-20:],
        "expected_value": profile.get("expected_value", 0.0),
        "expected_delta": profile.get("expected_delta", 0.0),
        "std": profile.get("std", 0.0),
        "delta_std": profile.get("delta_std", 0.0),
        "samples_count": profile.get("samples_count", 0),
        "last_value": profile.get("last_value", profile.get("expected_value", 0.0))
    }

    return control


def build_missing_control(variable_key, variable_label):
    return {
        "type": "missing_source",
        "variable_key": variable_key,
        "variable_label": variable_label,
        "source_path": "",
        "source_kind": "missing",
        "message": "Для переменной не задан источник данных в мастере семантики."
    }


def build_unknown_control(variable_key, variable_label, source_path):
    return {
        "type": "unsupported",
        "variable_key": variable_key,
        "variable_label": variable_label,
        "source_path": source_path,
        "source_kind": "unknown",
        "message": "Источник пока не поддерживается в What-if анализе."
    }


def build_control_for_source(cursor, template_id, variable_key, source_path, binding=None):
    variable_label = get_variable_label(template_id, variable_key)
    source_info = classify_source_path(source_path)
    kind = source_info["kind"]

    if kind == "missing":
        return build_missing_control(variable_key, variable_label)

    if kind == "table_field":
        table_name = source_info["table"]

        if table_name in {"items", "skills"}:
            return build_entity_table_control(
                cursor,
                variable_key,
                variable_label,
                source_path,
                source_info
            )

        return build_table_aggregate_control(
            cursor,
            variable_key,
            variable_label,
            source_path,
            source_info
        )

    if kind == "event_signal":
        return build_event_signal_control(
            cursor,
            variable_key,
            variable_label,
            source_path,
            source_info,
            binding
        )

    if kind == "computed_signal":
        return build_computed_signal_control(
            cursor,
            variable_key,
            variable_label,
            source_path,
            source_info
        )

    return build_unknown_control(
        variable_key,
        variable_label,
        source_path
    )


def count_entity_controls(controls):
    count = 0

    for control in controls:
        count += len(control.get("controls") or [])

    return count


def build_what_if_controls(project):
    """
    Возвращает список контролов What-if, построенных по фактическим
    semantic_bindings текущего проекта.
    """

    if not project:
        return {
            "success": False,
            "message": "Проект не найден",
            "template_id": "",
            "controls": []
        }

    template_id = get_template_id(project)
    bindings = get_semantic_bindings(project)

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        controls = []
        used_variables = get_formula_used_variables(project, bindings)

        for variable_key, binding in bindings.items():
            source_path = get_binding_source(binding)

            if variable_key not in used_variables:
                controls.append(
                    build_formula_unused_control(
                        variable_key,
                        get_variable_label(template_id, variable_key),
                        source_path
                    )
                )
                continue

            controls.append(
                build_control_for_source(
                    cursor,
                    template_id,
                    variable_key,
                    source_path,
                    binding
                )
            )

        editable_controls = [
            control
            for control in controls
            if control.get("type") in {"entity_table", "signal_multiplier"}
        ]

        return {
            "success": True,
            "project_id": project.get("id", ""),
            "template_id": template_id,
            "selected_template": template_id,
            "controls": controls,
            "summary": {
                "variables_count": len(bindings),
                "editable_sources_count": len(editable_controls),
                "entity_controls_count": count_entity_controls(controls),
                "uses_entity_tables": any(c.get("type") == "entity_table" for c in controls),
                "uses_assumptions": any(c.get("type") == "signal_multiplier" for c in controls)
            },
            "message": "Источники What-if анализа подготовлены"
        }

    finally:
        cursor.close()
        conn.close()


# ===== P7.2: сценарное прогнозирование =====

SCENARIO_DATASET_PREFIX = "__what_if__"
DEFAULT_FORECAST_HORIZON = 5
MAX_FORECAST_HORIZON = 10
EPSILON = 1e-9


def clamp_horizon(value):
    try:
        horizon = int(value)
    except (TypeError, ValueError):
        horizon = DEFAULT_FORECAST_HORIZON

    return max(1, min(horizon, MAX_FORECAST_HORIZON))


def safe_div(left, right):
    left = to_float(left)
    right = to_float(right)

    if abs(right) <= EPSILON:
        return 0.0

    return left / right


def normalize_scenario_config(raw_config):
    if isinstance(raw_config, str):
        try:
            raw_config = json.loads(raw_config)
        except json.JSONDecodeError:
            raw_config = {}

    if not isinstance(raw_config, dict):
        raw_config = {}

    return {
        "horizon": clamp_horizon(raw_config.get("horizon", DEFAULT_FORECAST_HORIZON)),
        "controls": raw_config.get("controls") if isinstance(raw_config.get("controls"), list) else []
    }


def payload_index_by_control_id(scenario_config):
    indexed = {}

    for control in scenario_config.get("controls") or []:
        if not isinstance(control, dict):
            continue

        control_id = control.get("control_id")

        if control_id:
            indexed[str(control_id)] = control

        if control.get("type") == "entity_table":
            for value_row in control.get("values") or []:
                row_id = value_row.get("control_id")
                if row_id:
                    indexed[str(row_id)] = value_row

    return indexed


def get_payload_signal_percent(payload_index, control):
    candidates = [
        f"signal:{control.get('variable_key')}",
        control.get("control_id"),
        control.get("variable_key")
    ]

    for key in candidates:
        if not key:
            continue

        payload = payload_index.get(str(key))

        if not payload:
            continue

        for field in ("percent", "current_percent", "value"):
            if field in payload:
                return to_float(payload.get(field), control.get("current_percent", 100))

    return to_float(control.get("current_percent", 100), 100)


def get_payload_entity_value(payload_index, row):
    payload = payload_index.get(str(row.get("control_id")))

    if not payload:
        return to_float(row.get("original_value"))

    for field in ("value", "current_value", "new_value"):
        if field in payload:
            return to_float(payload.get(field), row.get("original_value"))

    return to_float(row.get("original_value"))



def mean_tail(values, window=3):
    prepared = [
        to_float(value)
        for value in (values or [])
        if value is not None
    ]

    if not prepared:
        return 0.0

    tail = prepared[-min(window, len(prepared)):]
    return estimate_expected_value(tail) if tail else 0.0


def control_base_map(controls):
    result = {}

    for control in controls:
        variable_key = control.get("variable_key")
        if not variable_key:
            continue

        if control.get("type") == "signal_multiplier":
            result[variable_key] = to_float(control.get("base_value"))
            continue

        if control.get("type") == "entity_table":
            values = [
                to_float(row.get("original_value"))
                for row in (control.get("controls") or [])
            ]
            result[variable_key] = estimate_expected_value(values, recency_weighted=False) if values else 0.0

    return result


def derive_forecast_base_context(template_id, historical_values, controls):
    """
    Строит базовые будущие переменные из последних исторических метрик.

    Это нужно, чтобы режим 100% был похож на продолжение текущей динамики,
    а не на пересчёт от общей средней event_data.value по всей базе. Особенно
    важно для progression_decay, где flow_in и flow_out в пресете часто
    привязаны к одному и тому же пути events.event_data.value.
    """

    bases = control_base_map(controls)

    if template_id == "progression_decay":
        duration = max(to_float(bases.get("duration"), 1.0), 1.0)

        recent_y = mean_tail(historical_values.get("Y_EXP_VELOCITY"), 3)
        recent_decay = mean_tail(historical_values.get("D_PROGRESSION_DECAY"), 3)

        if abs(recent_y) > EPSILON:
            bases["flow_in"] = max(recent_y * duration, 0.0)

        if abs(recent_decay) > EPSILON:
            bases["flow_out"] = max(recent_decay * duration, 0.0)

    return bases


def deterministic_normal_sample(seed_key, step_index):
    """
    Возвращает воспроизводимую псевдослучайную величину Z ~ N(0, 1).

    Для дипломной демонстрации важно, чтобы один и тот же сценарий давал
    один и тот же график, поэтому генератор детерминированно сидируется
    именем переменной и номером будущей сессии. Математически это остаётся
    реализацией нормальной случайной компоненты Z_{j,h}.
    """

    material = f"{seed_key}:{step_index}".encode("utf-8", errors="ignore")
    digest = hashlib.sha256(material).digest()
    seed = int.from_bytes(digest[:8], "big", signed=False)

    return float(random.Random(seed).gauss(0.0, 1.0))


def build_expected_forecast_series(base_value, percent, horizon, profile=None, seed_key=""):
    """
    Строит future series по стохастической AR(1)-модели:

        X~_{j,T+h} = μ*_j + ρ_j (X~_{j,T+h-1} - μ*_j)
                    + σ*_{Δ,j} sqrt(1 - ρ_j^2) Z_{j,h},
        Z_{j,h} ~ N(0, 1).

    Здесь μ*_j = m_j * E[X_j] — сценарное математическое ожидание,
    σ*_{Δ,j} = |m_j| * σ_{Δ,j} — сценарный разброс случайных приращений,
    ρ_j задаёт инерцию ряда. При |ρ_j| < 1 процесс сходится к
    стационарному нормальному распределению вокруг μ*_j.
    """

    horizon = clamp_horizon(horizon)
    profile = profile or {}

    mu_hat = to_float(profile.get('expected_value'), base_value)
    last_value = to_float(profile.get('last_value'), mu_hat)

    modifier = to_float(percent, 100.0) / 100.0
    mu_star = mu_hat * modifier

    sigma_delta = max(to_float(profile.get('delta_std'), 0.0), 0.0)

    # Если исторических приращений слишком мало или они полностью нулевые,
    # используем небольшой резервный разброс от масштаба самой величины.
    # Иначе процесс опять станет детерминированной прямой.
    if sigma_delta <= EPSILON:
        sigma_delta = max(abs(mu_hat) * 0.03, abs(last_value) * 0.03, 0.01)

    sigma_delta_star = abs(modifier) * sigma_delta

    rho = to_float(profile.get('rho'), 0.68)
    rho = max(min(rho, 0.95), -0.95)
    stochastic_scale = sigma_delta_star * math.sqrt(max(1.0 - rho ** 2, 0.0))

    values = []
    previous = last_value
    non_negative = bool(profile.get('non_negative', True))

    for step in range(horizon):
        z_value = deterministic_normal_sample(seed_key or 'what_if', step)
        next_value = (
            mu_star
            + rho * (previous - mu_star)
            + stochastic_scale * z_value
        )

        if non_negative:
            next_value = max(next_value, 0.0)

        values.append(float(next_value))
        previous = next_value

    return values


def get_control_profile(control):
    profile = control.get('forecast_profile') or {}

    if profile:
        return profile

    return {
        'series': [],
        'expected_value': to_float(control.get('base_value')),
        'expected_delta': 0.0,
        'std': 0.0,
        'delta_std': 0.0,
        'samples_count': 0,
        'last_value': to_float(control.get('base_value')),
        'non_negative': True
    }



def build_scenario_variable_context(project, scenario_config, historical_values=None, template_id=None):
    """
    Собирает будущие значения переменных выбранного шаблона.

    P7.2 statistical hotfix:
    вместо одной константы для всего горизонта функция строит по каждой
    переменной прогнозный временной ряд. Для событийных и computed-сигналов
    базой служит оценка мат. ожидания сессионного ряда, ожидаемое изменение
    между сессиями и оценка разброса. Для справочников items/skills значение
    остаётся сценарным коэффициентом к текущей исторической базе.
    """

    controls_result = build_what_if_controls(project)
    controls = controls_result.get("controls") or []
    payload_index = payload_index_by_control_id(scenario_config)
    horizon = clamp_horizon(scenario_config.get("horizon", DEFAULT_FORECAST_HORIZON))

    context = {}
    context_series = {}
    applied_controls = []
    forecast_base_context = derive_forecast_base_context(
        template_id or get_template_id(project),
        historical_values or {},
        controls
    )

    for control in controls:
        control_type = control.get("type")
        variable_key = control.get("variable_key")

        if not variable_key:
            continue

        if control_type == "signal_multiplier":
            percent = get_payload_signal_percent(payload_index, control)
            base_value = to_float(
                forecast_base_context.get(variable_key, control.get("base_value"))
            )

            profile = dict(get_control_profile(control))
            profile["expected_value"] = base_value
            profile["last_value"] = base_value if abs(to_float(profile.get("last_value"))) <= EPSILON else profile.get("last_value")

            profile["non_negative"] = True
            profile["rho"] = 0.68

            scenario_values = build_expected_forecast_series(
                base_value=base_value,
                percent=percent,
                horizon=horizon,
                profile=profile,
                seed_key=f"{variable_key}:{control.get('source_path', '')}"
            )
            scenario_value = scenario_values[0] if scenario_values else base_value * percent / 100.0

            context[variable_key] = scenario_value
            context_series[variable_key] = scenario_values
            applied_controls.append({
                "variable_key": variable_key,
                "variable_label": control.get("variable_label", variable_key),
                "source_path": control.get("source_path", ""),
                "type": "signal_multiplier",
                "base_value": base_value,
                "percent": percent,
                "scenario_value": scenario_value,
                "scenario_series": scenario_values,
                "expected_delta": profile.get("expected_delta", 0.0),
                "std": profile.get("std", 0.0),
                "delta_std": profile.get("delta_std", 0.0),
                "rho": profile.get("rho", 0.68)
            })

        elif control_type == "entity_table":
            rows = control.get("controls") or []
            values = [
                get_payload_entity_value(payload_index, row)
                for row in rows
            ]

            raw_scenario_expectation = estimate_expected_value(values, recency_weighted=False) if values else 0.0
            original_values = [to_float(row.get("original_value")) for row in rows]
            original_expectation = estimate_expected_value(original_values, recency_weighted=False) if original_values else 0.0

            if variable_key in forecast_base_context and abs(original_expectation) > EPSILON:
                scenario_value = forecast_base_context[variable_key] * safe_div(raw_scenario_expectation, original_expectation)
            else:
                scenario_value = raw_scenario_expectation

            scenario_values = [scenario_value for _ in range(horizon)]
            context[variable_key] = scenario_value
            context_series[variable_key] = scenario_values
            applied_controls.append({
                "variable_key": variable_key,
                "variable_label": control.get("variable_label", variable_key),
                "source_path": control.get("source_path", ""),
                "type": "entity_table",
                "table": control.get("table", ""),
                "field": control.get("field", ""),
                "original_expectation": original_expectation,
                "scenario_value": scenario_value,
                "raw_scenario_expectation": raw_scenario_expectation,
                "entities_count": len(values)
            })

    return context, context_series, applied_controls, controls_result


def get_last_value(values, default=0.0):
    if not values:
        return default

    return to_float(values[-1], default)


def calculate_future_point(template_id, context, previous_values):
    """
    Рассчитывает одну будущую точку метрик выбранного шаблона.

    Это не полноценный цифровой двойник игры, а прикладной прогноз по
    агрегированным переменным Binding Wizard. История не меняется, БД не
    меняется, будущие точки строятся только в памяти.
    """

    if template_id == "progression_decay":
        flow_in = max(to_float(context.get("flow_in")), 0.0)
        flow_out = max(to_float(context.get("flow_out")), 0.0)
        duration = max(to_float(context.get("duration"), 1.0), 1.0)

        previous_k = get_last_value(previous_values.get("K_POWER_SCORE"), 0.0)
        net_progress = flow_in - flow_out
        next_k = max(previous_k + net_progress, 0.0)

        return {
            "Y_EXP_VELOCITY": safe_div(flow_in, duration),
            "K_POWER_SCORE": next_k,
            "S_UNSPENT_RESOURCES": safe_div(net_progress, flow_in),
            "D_PROGRESSION_DECAY": safe_div(flow_out, duration),
            "A_PROGRESSION_ROI": safe_div(next_k - previous_k, flow_out)
        }

    if template_id == "resource_flow":
        income = max(to_float(context.get("resource_income")), 0.0)
        spend = max(to_float(context.get("resource_spend")), 0.0)
        net_resource = income - spend

        return {
            "RF_RESOURCE_FLOW": net_resource,
            "SSR_SPEND_SHARE": safe_div(spend, income),
            "RI_RESOURCE_INFLATION": safe_div(net_resource, income)
        }

    if template_id == "resource_conversion":
        resource_cost = max(to_float(context.get("resource_cost")), 0.0)
        power_gain = max(to_float(context.get("power_gain")), 0.0)
        action_count = max(to_float(context.get("action_count")), 1.0)

        return {
            "PE_PROGRESSION_EFFICIENCY": safe_div(power_gain, action_count),
            "ROI_RESOURCE_TO_POWER": safe_div(power_gain, resource_cost),
            "POWER_COST": safe_div(resource_cost, max(power_gain, 1.0))
        }

    if template_id == "engagement_resource":
        action_count = max(to_float(context.get("action_count")), 0.0)
        reward = max(to_float(context.get("reward")), 0.0)
        duration = max(to_float(context.get("duration"), 1.0), 1.0)

        return {
            "APM_ACTIONS_PER_MINUTE": safe_div(action_count, duration),
            "TIME_EFFICIENCY": safe_div(reward, duration),
            "GRIND_FACTOR": safe_div(action_count, max(reward, 1.0))
        }

    return {}



def forecast_metric_values(template_id, metric_order, context, historical_values, horizon, context_series=None):
    previous_values = {
        metric_key: list(historical_values.get(metric_key, []) or [])
        for metric_key in metric_order
    }

    future_values = {
        metric_key: []
        for metric_key in metric_order
    }

    context_series = context_series or {}

    for step in range(horizon):
        step_context = dict(context)

        for variable_key, values in context_series.items():
            if step < len(values):
                step_context[variable_key] = values[step]

        point = calculate_future_point(template_id, step_context, previous_values)

        for metric_key in metric_order:
            value = to_float(point.get(metric_key, 0.0))
            future_values[metric_key].append(value)
            previous_values.setdefault(metric_key, []).append(value)

    return future_values


def build_historical_values_from_analysis(analysis_result, metric_order):
    values = {metric_key: [] for metric_key in metric_order}

    datasets = analysis_result.get("datasets") or []

    for dataset in datasets:
        metric_key = dataset.get("metric_key")

        if metric_key not in values:
            continue

        values[metric_key] = [
            to_float(value)
            for value in dataset.get("data") or []
        ]

    return values


def build_scenario_datasets(metric_order, metric_labels, historical_values, future_values, historical_length):
    datasets = []
    prefix_length = max(historical_length - 1, 0)

    for metric_key in metric_order:
        history = historical_values.get(metric_key, []) or []
        future = future_values.get(metric_key, []) or []

        if not future:
            continue

        anchor = get_last_value(history, 0.0) if history else None
        data = [None] * prefix_length

        if anchor is not None:
            data.append(anchor)

        data.extend(future)

        datasets.append({
            "label": f"{metric_labels.get(metric_key, DEFAULT_METRIC_LABELS.get(metric_key, metric_key))} · сценарий",
            "metric_key": metric_key,
            "data": data,
            "yAxisID": "y",
            "borderWidth": 2,
            "borderDash": [8, 6],
            "pointRadius": 2,
            "scenario": True,
            "scenario_id": f"{SCENARIO_DATASET_PREFIX}{metric_key}"
        })

    return datasets


def build_scenario_summary_insights(history_values, future_values, metric_order, metric_labels):
    insights = []

    for metric_key in metric_order[:3]:
        history = history_values.get(metric_key, []) or []
        future = future_values.get(metric_key, []) or []

        if not history or not future:
            continue

        history_tail = history[-min(3, len(history)):]
        history_mean = estimate_expected_value(history_tail) if history_tail else 0.0
        future_mean = estimate_expected_value(future) if future else 0.0
        scale = max(abs(history_mean), 1.0)
        relative_change = (future_mean - history_mean) / scale

        if abs(relative_change) < 0.10:
            continue

        level = "info"
        if abs(relative_change) >= 0.35:
            level = "warning"

        direction = "выше" if relative_change > 0 else "ниже"
        percent = abs(relative_change) * 100

        insights.append({
            "level": level,
            "category": "what_if_compare",
            "title": f"Сценарий меняет метрику «{metric_labels.get(metric_key, metric_key)}»",
            "text": f"Среднее прогнозное значение становится примерно на {percent:.1f}% {direction}, чем в последних исторических сессиях.",
            "recommendation": "Сравните пунктирную линию со сплошной исторической динамикой и оцените, соответствует ли изменение ожидаемому направлению баланса.",
            "metric_keys": [metric_key],
            "evidence": f"Историческая база: {history_mean:.3f}; прогноз: {future_mean:.3f}."
        })

    return insights[:3]


def apply_what_if_scenario(project, player_id, raw_config):
    """
    Строит продолжение текущих графиков пунктирными линиями на будущие
    сессии. Исторические данные и БД не изменяются.
    """

    if not project:
        return {
            "success": False,
            "message": "Проект не найден"
        }

    scenario_config = normalize_scenario_config(raw_config)
    horizon = scenario_config["horizon"]

    template_id = get_project_template_id(project)
    metric_order = get_project_metric_order(project)
    metric_labels = get_project_metric_labels(project)

    analysis_result = analyze_project_player(project, player_id)

    if not analysis_result.get("success", False):
        return {
            "success": False,
            "message": "Не удалось получить исторические данные для прогноза",
            "details": analysis_result.get("message") or analysis_result.get("details") or ""
        }

    historical_labels = analysis_result.get("labels") or []
    historical_length = len(historical_labels)
    historical_values = build_historical_values_from_analysis(analysis_result, metric_order)

    variable_context, variable_context_series, applied_controls, controls_result = build_scenario_variable_context(
        project,
        scenario_config,
        historical_values=historical_values,
        template_id=template_id
    )

    if not variable_context:
        return {
            "success": False,
            "message": "Нет доступных изменяемых параметров для сценарного прогноза",
            "details": "Проверьте настройки мастера семантики и источники переменных шаблона."
        }

    future_values = forecast_metric_values(
        template_id=template_id,
        metric_order=metric_order,
        context=variable_context,
        historical_values=historical_values,
        horizon=horizon,
        context_series=variable_context_series
    )

    scenario_datasets = build_scenario_datasets(
        metric_order=metric_order,
        metric_labels=metric_labels,
        historical_values=historical_values,
        future_values=future_values,
        historical_length=historical_length
    )

    future_labels = list(range(historical_length, historical_length + horizon))
    combined_labels = list(historical_labels) + future_labels

    stability = analyze_stability(
        values_by_metric=future_values,
        metric_order=metric_order
    )

    scenario_insights = generate_practical_insights(
        template_id=template_id,
        values_by_metric=future_values,
        metric_order=metric_order,
        metric_labels=metric_labels,
        stability=stability,
        analysis_scope="what_if_scenario"
    )

    comparison_insights = build_scenario_summary_insights(
        history_values=historical_values,
        future_values=future_values,
        metric_order=metric_order,
        metric_labels=metric_labels
    )

    return {
        "success": True,
        "mode": "what_if_forecast",
        "project_id": project.get("id", ""),
        "player_id": player_id,
        "template_id": template_id,
        "horizon": horizon,
        "labels": combined_labels,
        "historical_length": historical_length,
        "future_labels": future_labels,
        "scenario_datasets": scenario_datasets,
        "scenario_values_by_metric": future_values,
        "variable_context": variable_context,
        "variable_context_series": variable_context_series,
        "applied_controls": applied_controls,
        "controls_summary": controls_result.get("summary", {}),
        "stability": stability,
        "scenario_insights": comparison_insights + scenario_insights,
        "message": "Сценарный прогноз построен"
    }
