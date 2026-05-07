import json
import uuid
from datetime import datetime, timedelta
import random

# Список существующих игроков
PLAYER_IDS = [
    "060b926a-5c47-49d2-babc-5bf42d76c846",
    "3c82f97f-d8ab-486f-bb54-f670fed1e92d",
    "49869649-8675-4ae4-8266-fa630f31f7a4",
    "4ba22b77-2f43-4a38-9152-64e429b7e793",
    "5a4de605-9b83-417e-a1f0-af7aae947e7e",
    "63fa35c2-809e-42f5-9cb0-fd52c264a318",
    "6bbcdd2f-34c1-4467-b7c0-f2f10e69ec31",
    "70b69cb9-72c7-4b25-b644-16b850691e95",
    "bc6ed51f-009c-4e03-a134-0674bd77c9d0",
    "dc7c4411-4a2e-4be2-9f74-53ef35e99edf"
]

ITEM_IDS = [
    "002c17a8-9e62-4909-a9e6-bec4816011bf",
    "17c7b5f5-0617-49e5-85db-cc0571b30b6e",
    "3cd9c068-5db9-4656-bc9a-2cf3b56e8846",
    "3e16e950-d1d2-471d-84ce-fa1157998cb6",
    "61975e02-7938-460f-8184-207c4f907f67",
    "740b1972-4e43-469f-851c-f8e09a6ac9e9",
    "9cca1326-94b9-4770-92a9-62beb6882df2",
    "a66b9c33-9fc1-424d-b8bf-0fb39d36502d",
    "d7a5ab2b-28fc-4068-af94-bccbef0d3e30",
    "f0a72897-8300-4b8e-80fd-cbe5f440b705"
]

SKILL_IDS = [
    "32ca8011-da15-4ac9-876d-d89b37aa133f",
    "4721a6e6-8d37-413e-8f80-93f7abda87ac",
    "4ff19b4a-75be-4d18-a423-3a06e1b624e4",
    "5ea7c163-d149-4bb6-b9ba-3a61c5fb2b23",
    "78419ef4-506a-40a0-b485-2ff91b55ebae",
    "9e608efa-81fc-4d71-b816-306529bd5381",
    "a89c05c9-e587-42bd-a355-41965546cd9f",
    "ac2b0ca1-8c2b-46a1-b765-666ea47c8534",
    "b4e238fe-fbdb-49cf-9419-67f3dbd6b565",
    "dfe41941-4374-475e-99a3-2007b4add44c"
]

# Типы событий
EVENT_TYPES = ["GAIN_XP", "SPEND_XP", "EQUIP_ITEM", "UNEQUIP_ITEM", "LEARN_SKILL"]


def generate_session(player_id, session_num):
    """Генерирует события для одной игровой сессии"""
    events = []

    # Начало сессии
    start_time = datetime.now() - timedelta(days=random.randint(1, 30))
    events.append({
        "id": f"event_{session_num}_001",
        "player_id": player_id,
        "timestamp": start_time.isoformat() + "Z",
        "event_type": "SESSION_START",
        "event_data": "{}"
    })

    # Генерация событий внутри сессии
    event_count = random.randint(500, 900)
    current_time = start_time
    for i in range(event_count):
        current_time += timedelta(minutes=random.randint(1, 20))
        event_type = random.choice(EVENT_TYPES)

        event_data = "{}"
        if event_type == "GAIN_XP":
            event_data = json.dumps({
                "amount": random.randint(50, 500),
                "source": random.choice(["quest", "combat", "exploration"])
            })
        elif event_type == "SPEND_XP":
            event_data = json.dumps({
                "amount": random.randint(20, 300),
                "purpose": "skill_upgrade"
            })
        elif event_type in ["EQUIP_ITEM", "UNEQUIP_ITEM"]:
            event_data = json.dumps({
                "item_id": random.choice(ITEM_IDS)
            })
        elif event_type == "LEARN_SKILL":
            event_data = json.dumps({
                "skill_id": random.choice(SKILL_IDS)
            })

        events.append({
            "id": f"event_{session_num}_{i + 2:03d}",
            "player_id": player_id,
            "timestamp": current_time.isoformat() + "Z",
            "event_type": event_type,
            "event_data": event_data
        })

    # Завершение сессии
    end_time = current_time + timedelta(minutes=random.randint(5, 30))
    events.append({
        "id": f"event_{session_num}_999",
        "player_id": player_id,
        "timestamp": end_time.isoformat() + "Z",
        "event_type": "SESSION_END",
        "event_data": "{}"
    })

    return events


def generate_logs(file_path, sessions_per_player=10):
    """Генерирует файл логов с тестовыми данными"""
    all_events = []

    # Генерация сессий для каждого игрока
    for player_id in PLAYER_IDS:
        for i in range(sessions_per_player):
            session_events = generate_session(player_id, len(all_events) + 1)
            all_events.extend(session_events)

    # Сохранение в файл
    with open(file_path, 'w') as file:
        for event in all_events:
            file.write(json.dumps(event) + "\n")

    print(f"Сгенерировано {len(all_events)} событий для {len(PLAYER_IDS)} игроков")


if __name__ == "__main__":
    generate_logs("events.jsonl")