import mysql.connector
import json
import os
from datetime import datetime
import uuid

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}

# Список существующих игроков
EXISTING_PLAYERS = {
    '060b926a-5c47-49d2-babc-5bf42d76c846',
    '3c82f97f-d8ab-486f-bb54-f670fed1e92d',
    '49869649-8675-4ae4-8266-fa630f31f7a4',
    '4ba22b77-2f43-4a38-9152-64e429b7e793',
    '5a4de605-9b83-417e-a1f0-af7aae947e7e',
    '63fa35c2-809e-42f5-9cb0-fd52c264a318',
    '6bbcdd2f-34c1-4467-b7c0-f2f10e69ec31',
    '70b69cb9-72c7-4b25-b644-16b850691e95',
    'bc6ed51f-009c-4e03-a134-0674bd77c9d0',
    'dc7c4411-4a2e-4be2-9f74-53ef35e99edf'
}


def import_events(file_path):
    """Импортирует события из JSONL-файла в базу данных"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Словарь для отслеживания активных сессий: player_id -> session_id
        active_sessions = {}

        with open(file_path, 'r') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Ошибка JSON в строке {line_num}: {e}")
                    print(f"Содержимое строки: {line}")
                    continue

                player_id = event.get('player_id')
                if not player_id:
                    print(f"Ошибка: Отсутствует player_id в строке {line_num}")
                    continue

                # Проверка существования игрока
                if player_id not in EXISTING_PLAYERS:
                    print(
                        f"Ошибка: Игрок с ID {player_id} не существует. Событие {event.get('id', 'без ID')} пропущено.")
                    continue

                # Обработка SESSION_START
                if event['event_type'] == 'SESSION_START':
                    # Создаем новую сессию
                    session_id = str(uuid.uuid4())

                    # Вставляем запись в sessions
                    query_session = """
                    INSERT INTO sessions (id, player_id, session_start)
                    VALUES (%s, %s, %s)
                    """
                    session_values = (
                        session_id,
                        player_id,
                        datetime.fromisoformat(event['timestamp'].rstrip('Z'))
                    )
                    cursor.execute(query_session, session_values)

                    # Сохраняем session_id для последующих событий
                    active_sessions[player_id] = session_id
                    print(f"Создана новая сессия: {session_id} для игрока {player_id}")

                # Для других событий проверяем активную сессию
                elif player_id in active_sessions:
                    session_id = active_sessions[player_id]
                else:
                    print(
                        f"Ошибка: Для игрока {player_id} нет активной сессии. Событие {event.get('id', 'без ID')} пропущено.")
                    continue

                # Вставляем ВСЕ события в таблицу events
                event_data = event.get('event_data', '{}')

                # Если event_data - строка, преобразуем в объект JSON
                if isinstance(event_data, str):
                    try:
                        event_data_obj = json.loads(event_data)
                    except json.JSONDecodeError:
                        event_data_obj = {}
                    event_data = json.dumps(event_data_obj)
                else:
                    event_data = json.dumps(event_data)

                query_event = """
                INSERT INTO events (id, session_id, timestamp, event_type, event_data)
                VALUES (%s, %s, %s, %s, %s)
                """
                event_values = (
                    event['id'],
                    session_id,
                    datetime.fromisoformat(event['timestamp'].rstrip('Z')),
                    event['event_type'],
                    event_data
                )
                cursor.execute(query_event, event_values)

                # Если это SESSION_END, закрываем сессию
                if event['event_type'] == 'SESSION_END':
                    query_update_session = """
                    UPDATE sessions 
                    SET session_end = %s 
                    WHERE id = %s
                    """
                    cursor.execute(query_update_session, (
                        datetime.fromisoformat(event['timestamp'].rstrip('Z')),
                        session_id
                    ))
                    # Удаляем сессию из активных
                    del active_sessions[player_id]
                    print(f"Сессия {session_id} завершена")

        conn.commit()
        print(f"Успешно импортировано событий")

        # Закрываем оставшиеся сессии (если не было SESSION_END)
        if active_sessions:
            print(f"Предупреждение: {len(active_sessions)} сессий остались открытыми")
            for player_id, session_id in active_sessions.items():
                print(f"Сессия {session_id} для игрока {player_id} не закрыта")

    except Exception as e:
        print(f"Ошибка импорта: {str(e)}")
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # Путь к файлу логов
    LOG_FILE = "events.jsonl"

    # Проверка существования файла
    if not os.path.exists(LOG_FILE):
        print(f"Файл {LOG_FILE} не найден!")
    else:
        import_events(LOG_FILE)