import os
import json
import uuid
import traceback
from datetime import datetime
from collections import defaultdict

import mysql.connector


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "2256",
    "database": "monitor_rpg_model"
}


REQUIRED_TABLES = {
    "players",
    "sessions",
    "events",
    "session_metrics"
}


class PipelineError(Exception):

    def __init__(self, code, message, details=None):
        super().__init__(message)

        self.code = code
        self.message = message
        self.details = details or ""


class DatabaseConnectionError(PipelineError):
    pass


class DatabaseSchemaError(PipelineError):
    pass


class SourceNotFoundError(PipelineError):
    pass


class InvalidSourceFormatError(PipelineError):
    pass


def parse_timestamp(value):

    if not isinstance(value, str) or not value.strip():

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            "Поле timestamp отсутствует или не является строкой."
        )

    try:
        return datetime.fromisoformat(
            value.replace("Z", "")
        )

    except ValueError:

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            f"Некорректный timestamp: {value}"
        )


def connect_database():

    try:
        conn = mysql.connector.connect(**DB_CONFIG)

        if not conn.is_connected():

            raise DatabaseConnectionError(
                "database_not_connected",
                "Нет подключения к базе данных",
                "MySQL-соединение не было установлено."
            )

        return conn

    except mysql.connector.Error as e:

        raise DatabaseConnectionError(
            "database_not_connected",
            "Нет подключения к базе данных",
            str(e)
        )


def get_table_names(conn):

    cursor = conn.cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
    """)

    tables = {
        row[0]
        for row in cursor.fetchall()
    }

    cursor.close()

    return tables


def check_database_schema(conn):

    tables = get_table_names(conn)

    missing = REQUIRED_TABLES - tables

    if missing:

        raise DatabaseSchemaError(
            "database_schema_error",
            "База данных не подготовлена",
            "Отсутствуют таблицы: " + ", ".join(sorted(missing))
        )

    print("[DB] Подключение к базе данных успешно")
    print("[DB] Структура БД проверена")


def get_columns_meta(conn, table_name):

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COLUMN_NAME,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            DATA_TYPE,
            EXTRA
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
    """, (table_name,))

    rows = cursor.fetchall()

    cursor.close()

    return {
        row["COLUMN_NAME"]: row
        for row in rows
    }


def default_value_for_column(meta):

    data_type = str(meta.get("DATA_TYPE", "")).lower()

    if data_type in {
        "int",
        "bigint",
        "smallint",
        "tinyint",
        "mediumint",
        "decimal",
        "float",
        "double"
    }:
        return 0

    if data_type in {
        "datetime",
        "timestamp",
        "date"
    }:
        return datetime.now()

    if data_type == "json":
        return "{}"

    return ""


def insert_dynamic(cursor, table_name, meta, values):

    prepared = {}

    for column_name, column_meta in meta.items():

        extra = str(column_meta.get("EXTRA", "")).lower()

        if "auto_increment" in extra:
            continue

        if column_name in values:
            prepared[column_name] = values[column_name]
            continue

        is_required = (
            column_meta.get("IS_NULLABLE") == "NO"
            and column_meta.get("COLUMN_DEFAULT") is None
        )

        if is_required:
            prepared[column_name] = default_value_for_column(column_meta)

    columns = list(prepared.keys())

    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{c}`" for c in columns)

    query = f"""
        INSERT INTO `{table_name}`
        ({column_sql})
        VALUES ({placeholders})
    """

    cursor.execute(
        query,
        [prepared[c] for c in columns]
    )


def find_jsonl_files(logs_path):

    if not logs_path or not os.path.isdir(logs_path):

        raise SourceNotFoundError(
            "source_not_found",
            "Не найден источник данных",
            "Выбранная директория не существует."
        )

    files = []

    for root, _, filenames in os.walk(logs_path):

        for filename in filenames:

            if filename.lower().endswith(".jsonl"):

                files.append(
                    os.path.join(root, filename)
                )

    files.sort()

    if not files:

        raise SourceNotFoundError(
            "source_not_found",
            "Не найден источник данных",
            "В выбранной директории не найдено файлов .jsonl."
        )

    print(f"[SOURCE] Найдено .jsonl файлов: {len(files)}")

    for file_path in files:
        print(f"[SOURCE] {file_path}")

    return files


def normalize_event(raw_event, file_path, line_number):

    if not isinstance(raw_event, dict):

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            f"{file_path}, строка {line_number}: событие не является JSON-объектом."
        )

    required_fields = [
        "timestamp",
        "entity_id",
        "event_type",
        "attributes"
    ]

    for field in required_fields:

        if field not in raw_event:

            raise InvalidSourceFormatError(
                "invalid_source_format",
                "Неверный формат исходных данных",
                f"{file_path}, строка {line_number}: отсутствует поле {field}."
            )

    timestamp = parse_timestamp(raw_event["timestamp"])

    entity_id = raw_event["entity_id"]
    event_type = raw_event["event_type"]
    attributes = raw_event["attributes"]

    if not isinstance(entity_id, str) or not entity_id.strip():

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            f"{file_path}, строка {line_number}: entity_id должен быть строкой."
        )

    if not isinstance(event_type, str) or not event_type.strip():

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            f"{file_path}, строка {line_number}: event_type должен быть строкой."
        )

    if not isinstance(attributes, dict):

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            f"{file_path}, строка {line_number}: attributes должен быть объектом."
        )

    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "entity_id": entity_id.strip(),
        "event_type": event_type.strip(),
        "attributes": attributes,
        "source_file": file_path,
        "line_number": line_number
    }


def load_source_events(files):

    events = []

    for file_path in files:

        with open(file_path, "r", encoding="utf-8") as file:

            for line_number, line in enumerate(file, 1):

                line = line.strip()

                if not line:
                    continue

                try:
                    raw_event = json.loads(line)

                except json.JSONDecodeError as e:

                    raise InvalidSourceFormatError(
                        "invalid_source_format",
                        "Неверный формат исходных данных",
                        f"{file_path}, строка {line_number}: ошибка JSON: {e}"
                    )

                events.append(
                    normalize_event(
                        raw_event,
                        file_path,
                        line_number
                    )
                )

    if not events:

        raise InvalidSourceFormatError(
            "invalid_source_format",
            "Неверный формат исходных данных",
            "В найденных .jsonl-файлах нет событий."
        )

    events.sort(
        key=lambda event: event["timestamp"]
    )

    print(f"[SOURCE] Валидировано событий: {len(events)}")

    return events


def ensure_player(cursor, players_meta, entity_id):

    if "id" not in players_meta:
        return

    cursor.execute(
        "SELECT COUNT(*) FROM players WHERE id = %s",
        (entity_id,)
    )

    exists = cursor.fetchone()[0] > 0

    if exists:
        return

    values = {
        "id": entity_id
    }

    if "name" in players_meta:
        values["name"] = entity_id

    if "total_xp" in players_meta:
        values["total_xp"] = 0

    if "level" in players_meta:
        values["level"] = 1

    insert_dynamic(
        cursor,
        "players",
        players_meta,
        values
    )

    print(f"[IMPORT] Создана сущность игрока: {entity_id}")


def create_session(cursor, sessions_meta, entity_id, entity_events):

    session_id = str(uuid.uuid4())

    start_time = entity_events[0]["timestamp"]
    end_time = entity_events[-1]["timestamp"]

    values = {}

    if "id" in sessions_meta:
        values["id"] = session_id

    if "player_id" in sessions_meta:
        values["player_id"] = entity_id

    if "entity_id" in sessions_meta:
        values["entity_id"] = entity_id

    if "session_start" in sessions_meta:
        values["session_start"] = start_time

    if "start_time" in sessions_meta:
        values["start_time"] = start_time

    if "session_end" in sessions_meta:
        values["session_end"] = end_time

    if "end_time" in sessions_meta:
        values["end_time"] = end_time

    if "avg_apm" in sessions_meta:
        duration_minutes = max(
            (end_time - start_time).total_seconds() / 60,
            1
        )

        values["avg_apm"] = len(entity_events) / duration_minutes

    insert_dynamic(
        cursor,
        "sessions",
        sessions_meta,
        values
    )

    print(
        f"[IMPORT] Создана сессия {session_id} "
        f"для сущности {entity_id}"
    )

    return session_id


def insert_event(cursor, events_meta, event, session_id):

    attributes_json = json.dumps(
        event["attributes"],
        ensure_ascii=False
    )

    values = {}

    if "id" in events_meta:
        values["id"] = event["id"]

    if "session_id" in events_meta:
        values["session_id"] = session_id

    if "player_id" in events_meta:
        values["player_id"] = event["entity_id"]

    if "entity_id" in events_meta:
        values["entity_id"] = event["entity_id"]

    if "timestamp" in events_meta:
        values["timestamp"] = event["timestamp"]

    if "event_type" in events_meta:
        values["event_type"] = event["event_type"]

    if "event_data" in events_meta:
        values["event_data"] = attributes_json

    if "attributes" in events_meta:
        values["attributes"] = attributes_json

    if "source_file" in events_meta:
        values["source_file"] = event["source_file"]

    insert_dynamic(
        cursor,
        "events",
        events_meta,
        values
    )


def get_numeric_value(event):

    attributes = event.get("attributes", {})

    value = attributes.get("value", 0)

    try:
        return float(value)

    except (TypeError, ValueError):
        return 0.0


def calculate_metrics_for_template(entity_events, template_id):

    start_time = entity_events[0]["timestamp"]
    end_time = entity_events[-1]["timestamp"]

    duration_minutes = max(
        (end_time - start_time).total_seconds() / 60,
        1
    )

    actions = len(entity_events)

    gain = 0.0
    spend = 0.0

    for event in entity_events:

        event_type = event["event_type"].lower()
        value = get_numeric_value(event)

        if (
            "gain" in event_type
            or "income" in event_type
            or "reward" in event_type
        ):
            gain += max(value, 0)

        elif (
            "spend" in event_type
            or "cost" in event_type
            or "purchase" in event_type
            or "loss" in event_type
        ):
            spend += abs(value)

    net = gain - spend

    # Базовые метрики сохраняем всегда,
    # чтобы существующий график K(t)/Y(t)/EV/PGR/DR не ломался.
    metrics = {
        "Y_EXP_VELOCITY": gain / duration_minutes,
        "K_POWER_SCORE": max(net, 0),
        "L_SESSION_ENGAGEMENT": actions,
        "S_UNSPENT_RESOURCES": net / gain if gain > 0 else 0,
        "D_PROGRESSION_DECAY": spend / duration_minutes,
        "A_PROGRESSION_ROI": net / spend if spend > 0 else 0,
        "SPEND_XP_TOTAL": spend
    }

    if template_id == "resource_flow":

        metrics.update({
            "RF_RESOURCE_FLOW": net,
            "SSR_SPEND_SHARE": spend / gain if gain > 0 else 0,
            "RI_RESOURCE_INFLATION": net / gain if gain > 0 else 0
        })

    elif template_id == "resource_conversion":

        metrics.update({
            "PE_PROGRESSION_EFFICIENCY": net / actions if actions > 0 else 0,
            "ROI_RESOURCE_TO_POWER": net / spend if spend > 0 else 0,
            "POWER_COST": spend / max(net, 1)
        })

    elif template_id == "engagement_resource":

        metrics.update({
            "APM_ACTIONS_PER_MINUTE": actions / duration_minutes,
            "TIME_EFFICIENCY": gain / duration_minutes,
            "GRIND_FACTOR": actions / gain if gain > 0 else 0
        })

    return metrics


def insert_metric(
    cursor,
    session_metrics_meta,
    session_id,
    entity_id,
    metric_name,
    metric_value
):

    values = {}

    if "id" in session_metrics_meta:
        values["id"] = str(uuid.uuid4())

    if "session_id" in session_metrics_meta:
        values["session_id"] = session_id

    if "player_id" in session_metrics_meta:
        values["player_id"] = entity_id

    if "entity_id" in session_metrics_meta:
        values["entity_id"] = entity_id

    if "metric_name" in session_metrics_meta:
        values["metric_name"] = metric_name

    if "name" in session_metrics_meta:
        values["name"] = metric_name

    if "metric_value" in session_metrics_meta:
        values["metric_value"] = metric_value

    if "value" in session_metrics_meta:
        values["value"] = metric_value

    insert_dynamic(
        cursor,
        "session_metrics",
        session_metrics_meta,
        values
    )


def get_observation_id(event):

    attributes = event.get("attributes", {})

    observation_id = attributes.get("observation_id")

    if isinstance(observation_id, str) and observation_id.strip():

        return observation_id.strip()

    # Fallback: если observation_id нет,
    # группируем события хотя бы по дате.
    return event["timestamp"].date().isoformat()

def import_and_calculate(conn, events, template_id):

    players_meta = get_columns_meta(conn, "players")
    sessions_meta = get_columns_meta(conn, "sessions")
    events_meta = get_columns_meta(conn, "events")
    session_metrics_meta = get_columns_meta(conn, "session_metrics")

    grouped = defaultdict(list)

    for event in events:

        group_key = (
            event["entity_id"],
            get_observation_id(event)
        )

        grouped[group_key].append(event)
    
    cursor = conn.cursor()

    imported_events = 0
    processed_sessions = 0

    try:
        for (entity_id, observation_id), entity_events in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0],
                item[1][0]["timestamp"]
            )
        ):

            ensure_player(
                cursor,
                players_meta,
                entity_id
            )

            session_id = create_session(
                cursor,
                sessions_meta,
                entity_id,
                entity_events
            )

            print(
                f"[IMPORT] Observation {observation_id} "
                f"mapped to session {session_id}"
            )

            for event in entity_events:

                insert_event(
                    cursor,
                    events_meta,
                    event,
                    session_id
                )

                imported_events += 1

            metrics = calculate_metrics_for_template(
                entity_events,
                template_id
            )

            for metric_name, metric_value in metrics.items():

                insert_metric(
                    cursor,
                    session_metrics_meta,
                    session_id,
                    entity_id,
                    metric_name,
                    metric_value
                )

            processed_sessions += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()

    return {
        "imported_events": imported_events,
        "processed_sessions": processed_sessions
    }


def run_pipeline(logs_path, template_id="progression_decay"):

    print("\n========== PIPELINE START ==========")

    conn = None

    try:
        print("[PIPELINE] Проверка подключения к БД")

        conn = connect_database()

        check_database_schema(conn)

        print("[PIPELINE] Поиск источников данных")

        source_files = find_jsonl_files(logs_path)

        print("[PIPELINE] Проверка формата событий")

        events = load_source_events(source_files)

        print("[PIPELINE] Импорт событий и расчёт метрик")

        import_result = import_and_calculate(
            conn,
            events,
            template_id
        )

        result = {
            "success": True,
            "message": "Импорт и расчёт метрик завершены",
            "database_connected": True,
            "source_files": source_files,
            "source_files_count": len(source_files),
            "validated_events": len(events),
            "imported_events": import_result["imported_events"],
            "processed_sessions": import_result["processed_sessions"],
            "selected_template": template_id,
            "needs_binding_wizard": True
        }

        print("[OK] Импортировано событий:", result["imported_events"])
        print("[OK] Обработано сессий:", result["processed_sessions"])

        print("\n========== PIPELINE COMPLETE ==========\n")

        return result

    except PipelineError as e:

        print("\n========== PIPELINE ERROR ==========")
        print(e.message)
        print(e.details)
        print("=====================================\n")

        return {
            "success": False,
            "error_code": e.code,
            "message": e.message,
            "details": e.details
        }

    except Exception as e:

        print("\n========== PIPELINE ERROR ==========")
        print("Непредвиденная ошибка pipeline:")
        print(e)

        traceback.print_exc()

        print("=====================================\n")

        return {
            "success": False,
            "error_code": "unexpected_pipeline_error",
            "message": "Непредвиденная ошибка pipeline",
            "details": str(e)
        }

    finally:

        if conn is not None and conn.is_connected():
            conn.close()