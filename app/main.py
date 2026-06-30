import sys
import os

# QWebEngine render stability for Windows / some GPU drivers.
# Keep hardware acceleration enabled for smooth UI animations, but disable the
# out-of-process canvas raster path that can flicker under fixed modal scrolls.
# Must be set before importing QtWebEngine classes.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join([
    "--disable-webgl",
    "--disable-webgl2",
    "--disable-accelerated-2d-canvas",
    "--disable-features=CanvasOopRasterization"
])

import sys
import json
import mysql.connector
import uuid
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot, QUrl, Signal, Qt
from PySide6.QtWidgets import QFileDialog

try:
    from backend.pipeline import run_pipeline
    from backend.progression_model import analyze_player, analyze_project_player
    from backend.what_if_analysis import build_what_if_controls, apply_what_if_scenario
except ImportError:
    # Fallback для запуска отдельных скриптов из backend/ или IDE.
    from pipeline import run_pipeline
    from progression_model import analyze_player, analyze_project_player
    from what_if_analysis import build_what_if_controls, apply_what_if_scenario


# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}

PROJECTS_FILE_NAME = "projects.json"


def get_documents_dir():
    """
    Возвращает реальный путь к пользовательской библиотеке 'Документы'
    через настройки Windows, а не через буквальную папку Documents.
    """

    if os.name == "nt":

        try:
            import winreg

            registry_path = (
                r"Software\Microsoft\Windows\CurrentVersion"
                r"\Explorer\User Shell Folders"
            )

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                registry_path
            ) as key:

                value, _ = winreg.QueryValueEx(
                    key,
                    "Personal"
                )

                return os.path.normpath(
                    os.path.expandvars(value)
                )

        except Exception as e:

            print(
                "[PROJECTS] Не удалось получить путь к Документам "
                "через Windows Registry:",
                e
            )

    return os.path.join(
        os.path.expanduser("~"),
        "Documents"
    )


def app_data_dir():

    path = os.path.join(
        get_documents_dir(),
        "BalanceCraft"
    )

    os.makedirs(path, exist_ok=True)

    return path


def projects_file_path():
    return os.path.join(
        app_data_dir(),
        PROJECTS_FILE_NAME
    )


def load_projects():
    path = projects_file_path()

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as e:
        print("[PROJECTS] Ошибка чтения projects.json:", e)
        return []


def save_projects(projects):
    path = projects_file_path()

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            projects,
            file,
            ensure_ascii=False,
            indent=4
        )

def update_project_import_result(project_id, folder_path, result):

    if not project_id:
        return None

    projects = load_projects()

    for project in projects:

        if project.get("id") != project_id:
            continue

        project["data_source_path"] = folder_path
        project["last_opened"] = datetime.now().isoformat(
            timespec="seconds"
        )

        if result.get("success"):

            project["last_import"] = datetime.now().isoformat(
                timespec="seconds"
            )

            project["import_status"] = "success"
            project["needs_binding"] = True

            project["last_import_result"] = {
                "source_files_count": result.get(
                    "source_files_count",
                    0
                ),
                "validated_events": result.get(
                    "validated_events",
                    0
                ),
                "imported_events": result.get(
                    "imported_events",
                    0
                ),
                "processed_sessions": result.get(
                    "processed_sessions",
                    0
                ),
                "selected_template": result.get(
                    "selected_template",
                    ""
                )
            }

        else:

            project["import_status"] = "error"

            project["last_import_result"] = {
                "error_code": result.get(
                    "error_code",
                    ""
                ),
                "message": result.get(
                    "message",
                    ""
                ),
                "details": result.get(
                    "details",
                    ""
                )
            }

        save_projects(projects)

        return project

    return None


ANALYSIS_TEMPLATES = [
    {
        "id": "progression_decay",
        "name": "Прогрессия с затуханием",
        "description": "Анализ роста силы игрока, скорости прогрессии и признаков снижения эффективности развития.",
        "variables": [
            {
                "key": "flow_in",
                "name": "Входящий поток прогрессии",
                "description": "Числовые события, увеличивающие прогрессию игрока.",
                "required": True
            },
            {
                "key": "flow_out",
                "name": "Расход / потери прогрессии",
                "description": "Числовые события, уменьшающие доступный ресурс или отражающие потери.",
                "required": True
            },
            {
                "key": "duration",
                "name": "Длительность окна анализа",
                "description": "Временной интервал, по которому нормализуются метрики.",
                "required": True
            },
            {
                "key": "engagement",
                "name": "Активность игрока",
                "description": "Количество действий или иной показатель вовлечённости.",
                "required": False
            }
        ],
        "metrics": [
            {
                "key": "Y_EXP_VELOCITY",
                "name": "Скорость прогрессии",
                "formula": "sum(flow_in) / duration"
            },
            {
                "key": "K_POWER_SCORE",
                "name": "Условная сила игрока",
                "formula": "max(sum(flow_in) - sum(flow_out), 0)"
            },
            {
                "key": "S_UNSPENT_RESOURCES",
                "name": "Доля неиспользованных ресурсов",
                "formula": "(sum(flow_in) - sum(flow_out)) / sum(flow_in)"
            },
            {
                "key": "D_PROGRESSION_DECAY",
                "name": "Снижение эффективности прогрессии",
                "formula": "sum(flow_out) / duration"
            },
            {
                "key": "A_PROGRESSION_ROI",
                "name": "Эффективность вложений в прогрессию",
                "formula": "net_progress / sum(flow_out)"
            }
        ]
    },
    {
        "id": "resource_flow",
        "name": "Потоки ресурсов",
        "description": "Анализ баланса приходящих и расходуемых ресурсов в рамках выбранного окна наблюдения.",
        "variables": [
            {
                "key": "resource_income",
                "name": "Доход ресурса",
                "description": "События, увеличивающие запас ресурса.",
                "required": True
            },
            {
                "key": "resource_spend",
                "name": "Расход ресурса",
                "description": "События, уменьшающие запас ресурса.",
                "required": True
            },
            {
                "key": "duration",
                "name": "Длительность окна анализа",
                "description": "Период агрегации ресурсного потока.",
                "required": True
            }
        ],
        "metrics": [
            {
                "key": "RF_RESOURCE_FLOW",
                "name": "Чистый ресурсный поток",
                "formula": "sum(resource_income) - sum(resource_spend)"
            },
            {
                "key": "SSR_SPEND_SHARE",
                "name": "Доля расхода",
                "formula": "sum(resource_spend) / sum(resource_income)"
            },
            {
                "key": "RI_RESOURCE_INFLATION",
                "name": "Темп накопления ресурса",
                "formula": "net_resource / sum(resource_income)"
            }
        ]
    },
    {
        "id": "resource_conversion",
        "name": "Конверсия ресурсов в силу",
        "description": "Оценка эффективности превращения затрат в рост силы, уровня или другого целевого показателя.",
        "variables": [
            {
                "key": "resource_cost",
                "name": "Стоимость действия",
                "description": "Ресурсы, затраченные на улучшения или прогрессию.",
                "required": True
            },
            {
                "key": "power_gain",
                "name": "Прирост силы",
                "description": "Изменение целевого показателя силы или эффективности.",
                "required": True
            },
            {
                "key": "action_count",
                "name": "Количество действий",
                "description": "Число улучшений, покупок, апгрейдов или других действий.",
                "required": False
            }
        ],
        "metrics": [
            {
                "key": "PE_PROGRESSION_EFFICIENCY",
                "name": "Эффективность прогрессии",
                "formula": "sum(power_gain) / count(action_count)"
            },
            {
                "key": "ROI_RESOURCE_TO_POWER",
                "name": "ROI ресурсов в силу",
                "formula": "sum(power_gain) / sum(resource_cost)"
            },
            {
                "key": "POWER_COST",
                "name": "Стоимость единицы силы",
                "formula": "sum(resource_cost) / max(sum(power_gain), 1)"
            }
        ]
    },
    {
        "id": "engagement_resource",
        "name": "Вовлечённость как ресурс",
        "description": "Анализ активности игрока, интенсивности действий и эффективности времени.",
        "variables": [
            {
                "key": "action_count",
                "name": "Количество действий",
                "description": "События активности игрока в рамках окна анализа.",
                "required": True
            },
            {
                "key": "reward",
                "name": "Полученная награда",
                "description": "Ресурс или прогресс, полученный за активность.",
                "required": True
            },
            {
                "key": "duration",
                "name": "Длительность окна анализа",
                "description": "Время, за которое совершались действия.",
                "required": True
            }
        ],
        "metrics": [
            {
                "key": "APM_ACTIONS_PER_MINUTE",
                "name": "Интенсивность действий",
                "formula": "count(action_count) / duration"
            },
            {
                "key": "TIME_EFFICIENCY",
                "name": "Эффективность времени",
                "formula": "sum(reward) / duration"
            },
            {
                "key": "GRIND_FACTOR",
                "name": "Гринд-фактор",
                "formula": "count(action_count) / max(sum(reward), 1)"
            }
        ]
    }
]


BINDING_TABLES = {
    "players": {
        "label": "Игроки",
        "fields": {
            "id": "Идентификатор игрока",
            "name": "Имя игрока",
            "total_xp": "Накопленный ресурс игрока"
        }
    },
    "sessions": {
        "label": "Сессии / окна наблюдения",
        "fields": {
            "id": "Идентификатор сессии",
            "player_id": "Игрок сессии",
            "session_start": "Начало сессии",
            "session_end": "Завершение сессии",
            "avg_apm": "Средняя активность в минуту"
        }
    },
    "events": {
        "label": "Сырые события",
        "fields": {
            "timestamp": "Время события",
            "event_type": "Тип события",
            "event_data": "Атрибуты события"
        }
    },
    "items": {
        "label": "Справочник предметов",
        "fields": {
            "id": "Идентификатор предмета",
            "name": "Название предмета",
            "gear_score": "Сила предмета"
        }
    },
    "skills": {
        "label": "Справочник навыков",
        "fields": {
            "id": "Идентификатор навыка",
            "name": "Название навыка",
            "skill_score": "Сила навыка"
        }
    }
}


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


def detect_value_type(value):

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, (int, float)):
        return "number"

    if value is None:
        return "null"

    return "string"


def add_sample(stats, value):

    if value is None:
        return

    text = str(value)

    if len(text) > 60:
        text = text[:57] + "..."

    if text not in stats["samples"] and len(stats["samples"]) < 6:
        stats["samples"].append(text)


def build_binding_candidates_from_db(limit=3000):

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("SELECT COUNT(*) AS cnt FROM events")
        events_count = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("SELECT COUNT(*) AS cnt FROM sessions")
        sessions_count = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("SELECT COUNT(*) AS cnt FROM players")
        players_count = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("""
            SELECT event_type, COUNT(*) AS cnt
            FROM events
            GROUP BY event_type
            ORDER BY cnt DESC, event_type
        """)

        event_types = [
            {
                "value": row["event_type"],
                "count": int(row["cnt"] or 0)
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT event_type, event_data
            FROM events
            ORDER BY timestamp
            LIMIT %s
        """, (limit,))

        attribute_stats = {}

        for row in cursor.fetchall():

            event_data = parse_event_data(row.get("event_data"))

            for key, value in event_data.items():

                if key not in attribute_stats:

                    attribute_stats[key] = {
                        "key": key,
                        "path": f"events.event_data.{key}",
                        "count": 0,
                        "types": {},
                        "samples": [],
                        "numeric_count": 0
                    }

                stats = attribute_stats[key]
                value_type = detect_value_type(value)

                stats["count"] += 1
                stats["types"][value_type] = stats["types"].get(value_type, 0) + 1

                if value_type == "number":
                    stats["numeric_count"] += 1

                add_sample(stats, value)

        attribute_fields = []

        for stats in attribute_stats.values():

            dominant_type = max(
                stats["types"],
                key=stats["types"].get
            ) if stats["types"] else "unknown"

            attribute_fields.append({
                "key": stats["key"],
                "path": stats["path"],
                "count": stats["count"],
                "data_type": dominant_type,
                "is_numeric": stats["numeric_count"] > 0,
                "samples": stats["samples"]
            })

        attribute_fields.sort(
            key=lambda item: (-item["count"], item["key"])
        )

        cursor.execute("""
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME IN ('players', 'sessions', 'events', 'items', 'skills')
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """)

        table_fields = []

        for row in cursor.fetchall():

            table_name = row["TABLE_NAME"]
            column_name = row["COLUMN_NAME"]

            table_info = BINDING_TABLES.get(table_name, {})
            field_labels = table_info.get("fields", {})

            data_type = str(row["DATA_TYPE"]).lower()

            excluded_data_types = {
                "datetime",
                "timestamp",
                "date",
                "time",
                "json",
                "jsonl"
            }

            if (
                data_type in excluded_data_types
                or "json" in data_type
                or "id" in column_name.lower()
            ):
                continue

            is_numeric = data_type in {
                "int",
                "bigint",
                "smallint",
                "tinyint",
                "mediumint",
                "decimal",
                "float",
                "double"
            }

            table_fields.append({
                "table": table_name,
                "field": column_name,
                "path": f"{table_name}.{column_name}",
                "table_label": table_info.get("label", table_name),
                "label": field_labels.get(column_name, column_name),
                "data_type": data_type,
                "is_numeric": is_numeric
            })

        return {
            "success": True,
            "summary": {
                "events_count": events_count,
                "sessions_count": sessions_count,
                "players_count": players_count
            },
            "event_types": event_types,
            "attribute_fields": attribute_fields,
            "table_fields": table_fields,
            "templates": ANALYSIS_TEMPLATES
        }

    finally:
        cursor.close()
        conn.close()



def get_project_by_id(project_id):

    for project in load_projects():
        if project.get("id") == project_id:
            return project

    return None


def get_template_by_id(template_id):

    for template in ANALYSIS_TEMPLATES:
        if template.get("id") == template_id:
            return template

    return ANALYSIS_TEMPLATES[0]


def to_float(value, default=0.0):

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_sum(value):

    if isinstance(value, list):
        return sum(to_float(item) for item in value)

    return to_float(value)


def safe_count(value):

    if isinstance(value, list):
        return len(value)

    return to_float(value)


def safe_max(*values):

    if len(values) == 1 and isinstance(values[0], list):
        values = values[0]

    prepared = [to_float(item) for item in values]

    if not prepared:
        return 0.0

    return max(prepared)


def safe_min(*values):

    if len(values) == 1 and isinstance(values[0], list):
        values = values[0]

    prepared = [to_float(item) for item in values]

    if not prepared:
        return 0.0

    return min(prepared)


class FormulaEvaluationError(Exception):
    pass


def eval_formula_node(node, context):
    """
    Безопасный небольшой evaluator формул Binding Wizard.
    Поддерживает только числа, имена переменных, арифметику и функции
    sum/count/max/min/abs. Произвольный Python-код не исполняется.
    """

    import ast
    import operator

    binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }

    unary_ops = {
        ast.UAdd: lambda value: value,
        ast.USub: lambda value: -value
    }

    functions = {
        "sum": safe_sum,
        "count": safe_count,
        "max": safe_max,
        "min": safe_min,
        "abs": abs
    }

    if isinstance(node, ast.Expression):
        return eval_formula_node(node.body, context)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaEvaluationError("В формулах допустимы только числовые константы.")

    if isinstance(node, ast.Name):
        if node.id not in context:
            return 0.0
        return context[node.id]

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in binary_ops:
            raise FormulaEvaluationError("Недопустимая арифметическая операция.")

        left = eval_formula_node(node.left, context)
        right = eval_formula_node(node.right, context)

        # Если переменная-список участвует в обычной арифметике,
        # используем её сумму: так формулы вида net_resource / income
        # не ломаются при привязке к event_data.value.
        if isinstance(left, list):
            left = safe_sum(left)
        if isinstance(right, list):
            right = safe_sum(right)

        if op_type is ast.Div and to_float(right) == 0:
            return 0.0

        return binary_ops[op_type](to_float(left), to_float(right))

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in unary_ops:
            raise FormulaEvaluationError("Недопустимая унарная операция.")
        value = eval_formula_node(node.operand, context)
        if isinstance(value, list):
            value = safe_sum(value)
        return unary_ops[op_type](to_float(value))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaEvaluationError("Недопустимый вызов функции.")

        function_name = node.func.id

        if function_name not in functions:
            raise FormulaEvaluationError(f"Функция {function_name} не поддерживается.")

        args = [
            eval_formula_node(arg, context)
            for arg in node.args
        ]

        return functions[function_name](*args)

    raise FormulaEvaluationError("Недопустимое выражение в формуле.")


def evaluate_formula(expression, context):

    import ast
    import math

    if not expression or not str(expression).strip():
        return 0.0

    try:
        tree = ast.parse(str(expression), mode="eval")
        value = eval_formula_node(tree, context)

        if isinstance(value, list):
            value = safe_sum(value)

        value = to_float(value)

        if math.isnan(value) or math.isinf(value):
            return 0.0

        return value

    except Exception as e:
        print("[FORMULA] Ошибка расчёта формулы:", expression, e)
        return 0.0



def normalize_semantic_binding(binding):
    """
    Универсальный формат семантической привязки.

    Старый формат был строкой: "events.event_data.value".
    Новый формат хранит источник и, если источник относится к event_data,
    список типов событий, из которых нужно брать значение.
    """

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


def event_matches_scope(event, binding):
    binding_spec = normalize_semantic_binding(binding)
    event_types = set(binding_spec.get("event_types") or [])

    if not event_types:
        # Совместимость со старыми проектами: если фильтр типов событий ещё
        # не задан, берём все события. Новый UI не позволит сохранить
        # events.event_data.* без явного выбора event_type.
        return True

    return str(event.get("event_type") or "") in event_types


def should_event_match_variable(event_type, variable_key):

    event_type = str(event_type or "").lower()
    variable_key = str(variable_key or "").lower()

    income_markers = [
        "in", "income", "gain", "reward", "flow_in", "power_gain"
    ]

    spend_markers = [
        "out", "spend", "cost", "loss", "purchase", "flow_out", "resource_cost"
    ]

    event_is_income = (
        "gain" in event_type
        or "income" in event_type
        or "reward" in event_type
    )

    event_is_spend = (
        "spend" in event_type
        or "cost" in event_type
        or "purchase" in event_type
        or "loss" in event_type
    )

    if any(marker in variable_key for marker in spend_markers):
        return event_is_spend

    if any(marker in variable_key for marker in income_markers):
        return event_is_income

    return True


def read_path_from_event(event, path):

    if path.startswith("events.event_data."):
        key = path.replace("events.event_data.", "", 1)
        data = parse_event_data(event.get("event_data"))
        return data.get(key)

    if path == "events.event_type":
        return event.get("event_type")

    if path == "events.timestamp":
        return event.get("timestamp")

    return None


def collect_binding_value(variable_key, binding, session, events, duration_minutes):

    binding_spec = normalize_semantic_binding(binding)
    path = binding_spec.get("source", "")

    if not path:
        return []

    path = str(path)

    if path == "computed.duration_minutes":
        return duration_minutes

    if path == "computed.action_count":
        return len(events)

    if path == "sessions.avg_apm":
        return to_float(session.get("avg_apm"))

    if path == "sessions.session_start":
        return session.get("session_start")

    if path == "sessions.session_end":
        return session.get("session_end")

    if path.startswith("events."):
        values = []

        for event in events:
            if not event_matches_scope(event, binding_spec):
                continue

            value = read_path_from_event(event, path)

            if value is not None:
                values.append(value)

        return values

    # Справочники items/skills пока могут участвовать в мастере как
    # доступные поля, но в историческом пересчёте без связи с конкретным
    # событием/игроком возвращаем 0, чтобы формула не падала.
    return 0.0



def build_formula_context(template, semantic_bindings, session, events):

    start_time = session.get("session_start")
    end_time = session.get("session_end")

    if start_time and end_time:
        duration_minutes = max(
            (end_time - start_time).total_seconds() / 60,
            1
        )
    else:
        duration_minutes = 1

    context = {
        "duration": duration_minutes,
        "action_count": len(events)
    }

    for variable in template.get("variables", []):
        key = variable.get("key")
        binding = semantic_bindings.get(key, "")

        context[key] = collect_binding_value(
            key,
            binding,
            session,
            events,
            duration_minutes
        )

    # Универсальные производные переменные для формул пресетов.
    context["net_resource"] = (
        safe_sum(context.get("resource_income"))
        - safe_sum(context.get("resource_spend"))
    )

    context["net_progress"] = (
        safe_sum(context.get("flow_in"))
        - safe_sum(context.get("flow_out"))
    )

    return context


def get_sessions_for_recalculation(cursor):

    cursor.execute("""
        SELECT
            s.id,
            s.player_id,
            s.session_start,
            s.session_end,
            s.avg_apm
        FROM sessions s
        ORDER BY s.player_id, s.session_start
    """)

    return cursor.fetchall()


def get_session_events(cursor, session_id):

    cursor.execute("""
        SELECT
            id,
            session_id,
            timestamp,
            event_type,
            event_data
        FROM events
        WHERE session_id = %s
        ORDER BY timestamp
    """, (session_id,))

    return cursor.fetchall()


def recalculate_session_metrics(binding_config):

    template_id = binding_config.get("selected_template") or "progression_decay"
    template = get_template_by_id(template_id)

    semantic_bindings = binding_config.get("semantic_bindings") or {}
    formula_config = binding_config.get("formula_config") or {}

    if not formula_config:
        formula_config = {
            metric.get("key"): metric.get("formula", "0")
            for metric in template.get("metrics", [])
        }

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        sessions = get_sessions_for_recalculation(cursor)

        processed_sessions = 0
        written_metrics = 0

        for session in sessions:
            session_id = session["id"]
            player_id = session["player_id"]
            events = get_session_events(cursor, session_id)

            context = build_formula_context(
                template,
                semantic_bindings,
                session,
                events
            )

            cursor.execute(
                "DELETE FROM session_metrics WHERE session_id = %s",
                (session_id,)
            )

            for metric_name, expression in formula_config.items():
                metric_value = evaluate_formula(expression, context)

                cursor.execute("""
                    INSERT INTO session_metrics
                    (id, session_id, player_id, metric_name, metric_value)
                    VALUES (UUID(), %s, %s, %s, %s)
                """, (
                    session_id,
                    player_id,
                    metric_name,
                    metric_value
                ))

                written_metrics += 1

            processed_sessions += 1

        conn.commit()

        return {
            "success": True,
            "processed_sessions": processed_sessions,
            "written_metrics": written_metrics,
            "selected_template": template_id
        }

    except Exception as e:
        conn.rollback()
        print("[BINDING] Ошибка перерасчёта метрик:", e)
        return {
            "success": False,
            "processed_sessions": 0,
            "written_metrics": 0,
            "selected_template": template_id,
            "message": "Не удалось пересчитать метрики",
            "details": str(e)
        }

    finally:
        cursor.close()
        conn.close()



def normalize_binding_for_storage(raw_binding):
    binding = normalize_semantic_binding(raw_binding)
    source = binding.get("source", "")

    if not str(source).startswith("events.event_data."):
        binding["event_types"] = []

    return binding


def build_clean_binding_config(template_id, payload):
    """
    Собирает конфигурацию мастера строго по выбранному шаблону.

    UI хранит черновики формул/названий/привязок между переключениями
    шаблонов, поэтому в payload могут оставаться метрики старого шаблона.
    На backend дополнительно отсекаем всё лишнее, чтобы в session_metrics
    и на графики попадали только метрики текущего selected_template.
    """

    template = get_template_by_id(template_id)

    raw_bindings = payload.get("semantic_bindings") or {}
    raw_formulas = payload.get("formula_config") or {}
    raw_labels = payload.get("metric_labels") or {}

    clean_bindings = {}

    for variable in template.get("variables", []):
        variable_key = variable.get("key")

        if not variable_key:
            continue

        clean_bindings[variable_key] = normalize_binding_for_storage(
            raw_bindings.get(
                variable_key,
                ""
            )
        )

    clean_formulas = {}
    clean_labels = {}

    for metric in template.get("metrics", []):
        metric_key = metric.get("key")

        if not metric_key:
            continue

        clean_formulas[metric_key] = raw_formulas.get(
            metric_key,
            metric.get("formula", "0")
        )

        clean_labels[metric_key] = raw_labels.get(
            metric_key,
            metric.get("name", metric_key)
        )

    return {
        "selected_template": template_id,
        "semantic_bindings": clean_bindings,
        "formula_config": clean_formulas,
        "metric_labels": clean_labels,
        "saved_at": datetime.now().isoformat(timespec="seconds")
    }


def save_project_binding_config(project_id, payload):

    projects = load_projects()

    for project in projects:
        if project.get("id") != project_id:
            continue

        template_id = payload.get("selected_template") or project.get("selected_template") or "progression_decay"

        binding_config = build_clean_binding_config(
            template_id,
            payload
        )

        recalculation_result = recalculate_session_metrics(binding_config)

        if not recalculation_result.get("success"):
            return {
                "success": False,
                "message": "Не удалось сохранить семантическое связывание",
                "details": recalculation_result.get("details", "Ошибка перерасчёта метрик"),
                "recalculation_result": recalculation_result
            }

        project["selected_template"] = template_id
        project["semantic_bindings"] = binding_config["semantic_bindings"]
        project["formula_config"] = binding_config["formula_config"]
        project["metric_labels"] = binding_config["metric_labels"]
        project["binding_config"] = binding_config
        project["needs_binding"] = False
        project["metrics_status"] = "custom_calculated"
        project["last_recalculation_result"] = recalculation_result
        project["last_opened"] = datetime.now().isoformat(timespec="seconds")

        save_projects(projects)

        return {
            "success": True,
            "message": "Семантическое связывание сохранено",
            "project": project,
            "recalculation_result": recalculation_result
        }

    return {
        "success": False,
        "message": "Проект не найден",
        "details": project_id
    }


class LogStream:

    def __init__(self, callback):
        self.callback = callback

    def write(self, message):

        if message.strip():
            self.callback(message)

    def flush(self):
        pass

class Backend(QObject):
    
    @Slot(result=str)
    def getPlayers(self):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT player_id
            FROM sessions
        """)

        result = cursor.fetchall()

        return json.dumps(result)


    @Slot(str, result=str)
    def analyzePlayer(self, player_id):
        """
        Legacy-анализ для совместимости со старым UI.
        Новый dashboard должен использовать analyzeProjectPlayer().
        """

        print("Запуск legacy-анализа из Python")

        result = analyze_player(player_id=player_id)

        return json.dumps(
            result,
            ensure_ascii=False
        )


    @Slot(str, str, result=str)
    def analyzeProjectPlayer(self, project_id, player_id):
        """
        Динамический анализ игрока с учётом выбранного шаблона проекта
        и реально рассчитанных session_metrics.
        """

        print(
            f"[ANALYSIS] Запуск анализа проекта {project_id} "
            f"для игрока {player_id}"
        )

        project = get_project_by_id(project_id)

        if not project:
            return json.dumps(
                {
                    "success": False,
                    "message": "Проект не найден",
                    "details": project_id,
                    "labels": [],
                    "datasets": [],
                    "lyapunov": 0,
                    "bifurcation_points": []
                },
                ensure_ascii=False
            )

        result = analyze_project_player(
            project=project,
            player_id=player_id
        )

        return json.dumps(
            result,
            ensure_ascii=False
        )

    @Slot(str, result=str)
    def getWhatIfControls(self, project_id):
        """
        Подготавливает контролы What-if анализа по semantic_bindings
        текущего проекта. На этом этапе БД только читается, прогноз ещё
        не строится и исторические данные не изменяются.
        """

        project = get_project_by_id(project_id)

        if not project:
            return json.dumps(
                {
                    "success": False,
                    "message": "Проект не найден",
                    "controls": []
                },
                ensure_ascii=False
            )

        try:
            result = build_what_if_controls(project)

            return json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception as e:
            print("[WHAT-IF] Ошибка подготовки контролов:", e)

            return json.dumps(
                {
                    "success": False,
                    "message": "Не удалось подготовить параметры What-if анализа",
                    "details": str(e),
                    "controls": []
                },
                ensure_ascii=False
            )


    @Slot(str, str, str, result=str)
    def applyWhatIfScenario(self, project_id, player_id, scenario_json):
        """
        Строит what-if прогноз продолжения графиков на будущие сессии.
        Исторические данные и БД не изменяются: сценарий считается только
        в памяти по текущим настройкам UI и semantic_bindings проекта.
        """

        project = get_project_by_id(project_id)

        if not project:
            return json.dumps(
                {
                    "success": False,
                    "message": "Проект не найден",
                    "scenario_datasets": []
                },
                ensure_ascii=False
            )

        try:
            scenario_config = json.loads(scenario_json) if scenario_json else {}
        except json.JSONDecodeError:
            scenario_config = {}

        try:
            result = apply_what_if_scenario(
                project=project,
                player_id=player_id,
                raw_config=scenario_config
            )

            return json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception as e:
            print("[WHAT-IF] Ошибка построения сценария:", e)

            return json.dumps(
                {
                    "success": False,
                    "message": "Не удалось построить What-if сценарий",
                    "details": str(e),
                    "scenario_datasets": []
                },
                ensure_ascii=False
            )



    @Slot(result=str)
    def selectFolder(self):

        folder = QFileDialog.getExistingDirectory(
            None,
            "Выберите источник данных"
        )

        return folder

    @Slot(str, str, result=str)
    def processPipeline(self, project_id, folder_path):

        result = run_pipeline(folder_path)

        updated_project = update_project_import_result(
            project_id,
            folder_path,
            result
        )

        if updated_project:
            result["updated_project"] = updated_project

        return json.dumps(
            result,
            ensure_ascii=False
        )


    @Slot(result=str)
    def getAnalysisTemplates(self):

        return json.dumps(
            ANALYSIS_TEMPLATES,
            ensure_ascii=False
        )


    @Slot(str, result=str)
    def getBindingCandidates(self, project_id):

        try:

            result = build_binding_candidates_from_db()
            result["project_id"] = project_id

            return json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception as e:

            print("[BINDING] Ошибка получения кандидатов:", e)

            return json.dumps(
                {
                    "success": False,
                    "message": "Не удалось получить данные для семантического связывания",
                    "details": str(e),
                    "event_types": [],
                    "attribute_fields": [],
                    "table_fields": [],
                    "templates": ANALYSIS_TEMPLATES
                },
                ensure_ascii=False
            )


    @Slot(str, str, result=str)
    def saveProjectBindingConfig(self, project_id, payload_json):

        try:
            payload = json.loads(payload_json or "{}")

            result = save_project_binding_config(
                project_id,
                payload
            )

            return json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception as e:
            print("[BINDING] Ошибка сохранения настройки:", e)

            return json.dumps(
                {
                    "success": False,
                    "message": "Не удалось сохранить семантическое связывание",
                    "details": str(e)
                },
                ensure_ascii=False
            )


    @Slot(result=str)
    def getProjects(self):

        projects = load_projects()

        projects.sort(
            key=lambda p: p.get("last_opened", ""),
            reverse=True
        )

        return json.dumps(
            projects,
            ensure_ascii=False
        )


    @Slot(str, result=str)
    def createProject(self, name):

        name = name.strip()

        if not name:
            name = "Новый проект"

        projects = load_projects()

        project = {
            "id": str(uuid.uuid4()),
            "name": name,
            "database": DB_CONFIG["database"],
            "data_source_path": "",
            "last_opened": datetime.now().isoformat(timespec="seconds"),
            "selected_template": "progression_decay",
            "semantic_bindings": {},
            "metric_labels": {
                "EV": "Скорость получения опыта",
                "PGR": "Темп роста силы",
                "DR": "Деградация прогрессии",
                "K": "Сила игрока",
                "Y": "Скорость прогрессии"
            },
            "last_player_id": None,
            "last_import": None,
            "import_status": "not_imported",
            "needs_binding": True,
            "last_import_result": None,
            "formula_config": {}
        }

        projects.append(project)

        save_projects(projects)

        print(f"[PROJECTS] Создан проект: {name}")

        return json.dumps(
            project,
            ensure_ascii=False
        )


    @Slot(str, result=str)
    def openProject(self, project_id):

        projects = load_projects()

        for project in projects:

            if project.get("id") == project_id:

                project["last_opened"] = datetime.now().isoformat(
                    timespec="seconds"
                )

                save_projects(projects)

                print(
                    f"[PROJECTS] Открыт проект: {project.get('name')}"
                )

                return json.dumps(
                    project,
                    ensure_ascii=False
                )

        print("[PROJECTS] Проект не найден:", project_id)

        return json.dumps(
            {},
            ensure_ascii=False
        )


    @Slot(str, str, result=bool)
    def updateProjectSource(self, project_id, folder_path):

        projects = load_projects()

        for project in projects:

            if project.get("id") == project_id:

                project["data_source_path"] = folder_path
                project["last_opened"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                project["import_status"] = "not_imported"
                project["needs_binding"] = True
                project["last_import_result"] = None

                save_projects(projects)

                print(
                    f"[PROJECTS] Источник данных обновлён: {folder_path}"
                )

                return True

        print("[PROJECTS] Не удалось обновить источник данных")

        return False


    @Slot(str, str, result=bool)
    def updateProjectTemplate(self, project_id, template_id):

        projects = load_projects()

        for project in projects:

            if project.get("id") == project_id:

                project["selected_template"] = template_id
                project["last_opened"] = datetime.now().isoformat(
                    timespec="seconds"
                )

                save_projects(projects)

                print(
                    f"[PROJECTS] Шаблон анализа обновлён: {template_id}"
                )

                return True

        return False

    logSignal = Signal(str)

    def emitLog(self, message):

        self.logSignal.emit(message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BalanceCraft")
        self.resize(1400, 850)
        self.setMinimumSize(980, 620)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.channel = QWebChannel()
        self.backend = Backend()
        sys.stdout = LogStream(self.backend.emitLog)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "ui", "index.html")
        self.browser.load(QUrl.fromLocalFile(html_path))


if __name__ == "__main__":
    try:
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_UseSoftwareOpenGL,
            True
        )
    except Exception as e:
        print("[UI] Software OpenGL attribute was not applied:", e)

    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())
