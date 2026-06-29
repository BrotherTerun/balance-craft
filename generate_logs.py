import json
import random
from datetime import datetime, timedelta


# ============================================================
# BalanceCraft universal pseudo-log generator
# ============================================================
#
# Универсальный формат события:
#
# {
#   "timestamp": "2026-05-07T18:24:11",
#   "entity_id": "060b926a-5c47-49d2-babc-5bf42d76c846",
#   "event_type": "flow_gain",
#   "attributes": {
#       "signal": "signal_alpha",
#       "channel": "channel_01",
#       "value": 150,
#       "observation_id": "obs_001"
#   }
# }
#
# Важно:
# - entity_id использует реальные players.id из БД;
# - поле всё равно называется entity_id, а не player_id;
# - event_type не содержит RPG-семантики вроде XP/gold/item;
# - attributes.value нужен pipeline для расчёта метрик;
# - observation_id нужен pipeline для разбиения на сессии/окна.
# ============================================================


RANDOM_SEED = 42

OUTPUT_FILE = "events.jsonl"

OBSERVATIONS_PER_ENTITY = 10

MIN_EVENTS_PER_OBSERVATION = 45
MAX_EVENTS_PER_OBSERVATION = 90


# Существующие players.id из БД
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


# Существующие items.id из БД.
# Пока используются только как нейтральные ссылки на каталог объектов.
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


# Существующие skills.id из БД.
# Пока используются только как нейтральные ссылки на каталог объектов.
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


SIGNALS = [
    "signal_alpha",
    "signal_beta",
    "signal_gamma",
    "signal_delta",
    "signal_epsilon"
]


CHANNELS = [
    "channel_01",
    "channel_02",
    "channel_03",
    "channel_04"
]


CONTEXTS = [
    "context_a",
    "context_b",
    "context_c",
    "context_d"
]


# Универсальные типы событий.
# Они не говорят, что именно происходит в игре.
#
# Но gain/reward/spend/loss нужны текущему pipeline,
# чтобы он мог отделить условный входящий и исходящий поток.
EVENT_TYPES_GAIN = [
    "flow_gain",
    "flow_reward",
    "state_gain",
    "conversion_gain"
]


EVENT_TYPES_SPEND = [
    "flow_spend",
    "flow_loss",
    "state_spend",
    "conversion_spend"
]


EVENT_TYPES_NEUTRAL = [
    "interaction_tick",
    "state_sample",
    "signal_probe",
    "object_reference"
]


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def choose_event_type(observation_index):
    """
    Создаёт лёгкую динамику:
    - в ранних наблюдениях больше входящего потока;
    - в поздних растёт доля исходящего потока;
    - часть событий нейтральная.
    """

    late_factor = observation_index / max(
        OBSERVATIONS_PER_ENTITY - 1,
        1
    )

    gain_weight = max(
        0.50 - late_factor * 0.18,
        0.25
    )

    spend_weight = min(
        0.16 + late_factor * 0.22,
        0.42
    )

    roll = random.random()

    if roll < gain_weight:
        return random.choice(EVENT_TYPES_GAIN)

    if roll < gain_weight + spend_weight:
        return random.choice(EVENT_TYPES_SPEND)

    return random.choice(EVENT_TYPES_NEUTRAL)


def generate_value(event_type, entity_index, observation_index):
    """
    Генерирует значение без прямой игровой семантики.
    """

    base = 70 + entity_index * 7
    trend = 1 + observation_index * 0.075
    noise = random.uniform(0.72, 1.38)

    event_type_lower = event_type.lower()

    if (
        "gain" in event_type_lower
        or "reward" in event_type_lower
    ):
        value = base * trend * noise

    elif (
        "spend" in event_type_lower
        or "loss" in event_type_lower
    ):
        value = base * (0.42 + observation_index * 0.045) * noise

    else:
        value = random.uniform(1, 12)

    return round(value, 3)


def maybe_add_catalog_reference(attributes):
    """
    Добавляет нейтральную ссылку на справочник объектов.

    Важно:
    - pipeline пока это не интерпретирует;
    - БД менять не нужно;
    - позже Binding Wizard сможет сказать:
      catalog_a -> items,
      catalog_b -> skills.
    """

    roll = random.random()

    if roll < 0.10:

        attributes["catalog_domain"] = "catalog_a"
        attributes["object_id"] = random.choice(ITEM_IDS)

    elif roll < 0.18:

        attributes["catalog_domain"] = "catalog_b"
        attributes["object_id"] = random.choice(SKILL_IDS)


def generate_event(
    entity_id,
    entity_index,
    observation_index,
    event_index,
    timestamp
):
    event_type = choose_event_type(
        observation_index
    )

    value = generate_value(
        event_type,
        entity_index,
        observation_index
    )

    observation_id = (
        f"obs_{observation_index + 1:03d}"
    )

    attributes = {
        "signal": random.choice(SIGNALS),
        "channel": random.choice(CHANNELS),
        "context": random.choice(CONTEXTS),
        "value": value,
        "observation_id": observation_id,
        "event_index": event_index,
        "weight": round(random.uniform(0.5, 1.5), 3)
    }

    if random.random() < 0.35:

        attributes["modifier"] = round(
            random.uniform(0.8, 1.25),
            3
        )

    if random.random() < 0.25:

        attributes["bucket"] = random.choice([
            "bucket_low",
            "bucket_mid",
            "bucket_high"
        ])

    maybe_add_catalog_reference(attributes)

    return {
        "timestamp": iso(timestamp),
        "entity_id": entity_id,
        "event_type": event_type,
        "attributes": attributes
    }


def generate_observation(
    entity_id,
    entity_index,
    observation_index,
    base_time
):
    """
    Одно окно наблюдения.

    Мы не называем его session на уровне лога.
    Уже pipeline интерпретирует observation_id как сессионный срез.
    """

    events = []

    start_time = (
        base_time
        + timedelta(days=observation_index)
        + timedelta(minutes=entity_index * 13)
    )

    current_time = start_time

    event_count = random.randint(
        MIN_EVENTS_PER_OBSERVATION,
        MAX_EVENTS_PER_OBSERVATION
    )

    for event_index in range(1, event_count + 1):

        current_time += timedelta(
            seconds=random.randint(20, 180)
        )

        events.append(
            generate_event(
                entity_id=entity_id,
                entity_index=entity_index,
                observation_index=observation_index,
                event_index=event_index,
                timestamp=current_time
            )
        )

    return events


def generate_logs(
    file_path=OUTPUT_FILE,
    observations_per_entity=OBSERVATIONS_PER_ENTITY
):
    random.seed(RANDOM_SEED)

    all_events = []

    base_time = datetime.now() - timedelta(
        days=observations_per_entity + 2
    )

    for entity_index, entity_id in enumerate(PLAYER_IDS, 1):

        for observation_index in range(observations_per_entity):

            all_events.extend(
                generate_observation(
                    entity_id=entity_id,
                    entity_index=entity_index,
                    observation_index=observation_index,
                    base_time=base_time
                )
            )

    all_events.sort(
        key=lambda event: event["timestamp"]
    )

    with open(file_path, "w", encoding="utf-8") as file:

        for event in all_events:

            file.write(
                json.dumps(
                    event,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(f"Сгенерировано событий: {len(all_events)}")
    print(f"Сущностей: {len(PLAYER_IDS)}")
    print(f"Окон наблюдения на сущность: {observations_per_entity}")
    print(f"Файл: {file_path}")


if __name__ == "__main__":

    generate_logs(
        OUTPUT_FILE
    )