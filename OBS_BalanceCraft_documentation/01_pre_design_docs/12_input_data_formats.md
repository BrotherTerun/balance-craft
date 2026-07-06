# 12. Форматы входных данных

## Основной формат событий: JSONL

JSONL — основной формат BalanceCraft 1.5.

Одна строка = одно событие.

## Минимальное событие

```json
{
  "timestamp": "2026-07-01T15:10:22Z",
  "entity_id": "entity_001",
  "event_type": "resource_spent",
  "attributes": {
    "amount": 10,
    "resource_type": "soft_currency",
    "context": "upgrade"
  }
}
```

## Полное рекомендуемое событие

```json
{
  "timestamp": "2026-07-01T15:10:22Z",
  "entity_id": "entity_001",
  "entity_type": "actor",
  "observation_id": "run_001",
  "observation_type": "run",
  "event_type": "resource_spent",
  "build_id": "0.8.14-playtest",
  "schema_version": "1.0",
  "source_id": "local_playtest",
  "attributes": {
    "amount": 10,
    "resource_type": "soft_currency",
    "context": "upgrade",
    "operation_id": "upgrade_sword_01"
  }
}
```

## Обязательные поля

| Поле | Тип | Описание |
|---|---|---|
| `timestamp` | string ISO datetime | время события |
| `entity_id` | string | псевдонимная сущность |
| `event_type` | string | тип события |
| `attributes` | object | произвольные поля события |

## Желательные поля

| Поле | Тип | Описание |
|---|---|---|
| `entity_type` | string | тип сущности |
| `observation_id` | string | окно наблюдения |
| `observation_type` | string | тип окна наблюдения |
| `build_id` | string | версия игры/билда |
| `schema_version` | string | версия формата |
| `source_id` | string | источник логов |

## Правила `attributes`

`attributes` должен быть объектом.

Допустимые значения:

- number;
- string;
- boolean;
- null;
- простые массивы — P1;
- вложенные объекты — P1/P2, не обязательны для MVP.

Для MVP лучше держать `attributes` плоским.


## Рекомендуемый словарь событий

BalanceCraft не требует жёсткой платформенной схемы событий, но для демо, SDK Lite и документации нужен рекомендуемый словарь. Он помогает собирать данные так, чтобы основные проблемы баланса были проверяемыми.

| Event type | Назначение | Какие проблемы помогает искать |
|---|---|---|
| `resource_gained` | начисление ресурса или значения | дефицит, профицит, инфляция |
| `resource_spent` | расход ресурса или значения | дефицит, профицит, sink-механики |
| `stock_changed` | прямое изменение запаса или параметра | динамика запаса, плато, скачки |
| `operation_attempted` | попытка выполнить действие | доступность, давление стоимости |
| `operation_completed` | успешное выполнение действия | использование контента, интенсивность |
| `operation_blocked` | действие заблокировано требованием | bottleneck, недоступность операций |
| `reward_received` | получение награды или результата | pacing наград, эффективность времени |
| `upgrade_purchased` | покупка/улучшение/конверсия | эффективность конверсии, доминирующие стратегии |
| `content_used` | использование объекта, действия или опции | мёртвый контент, usage-срезы |
| `parameter_changed` | изменение параметра в тестовой сборке | связка параметров и What-if |

Словарь является рекомендацией, а не обязательным стандартом. Пользователь может использовать свои `event_type`, если затем свяжет их с переменными шаблонов через Binding Wizard.

## Поля для конверсии и ROI

Для шаблона “Эффективность конверсии” важно не смешивать несопоставимые единицы.

Простой вариант:

```json
{
  "cost": 120,
  "cost_type": "gold",
  "result": 18,
  "result_type": "damage"
}
```

Такой набор позволяет считать:

```text
result_per_cost = result / cost
cost_per_result = cost / result
```

Но он не позволяет честно считать строгий ROI, потому что золото и урон — разные единицы.

Если нужен нормализованный ROI, событие или parameter catalog должны содержать значения, приведённые к общей шкале:

```json
{
  "cost": 120,
  "cost_type": "gold",
  "result": 18,
  "result_type": "damage",
  "cost_value": 120,
  "result_value": 160,
  "value_unit": "designer_score"
}
```

`cost_value`, `result_value` и `value_unit` не обязательны для MVP, но без них система должна называть метрику “результат на единицу затрат”, а не “ROI”.

Альтернатива для будущей версии — value normalization profile внутри проекта. В этом случае raw-событие может не содержать `cost_value/result_value`, но проект хранит отдельное правило, как привести разные величины к общей шкале. Для версии 1.5 достаточно поддержать поля во входных данных и явно показывать предупреждение, если строгий ROI недоступен.

## Примеры событий

### Начисление ресурса

```json
{"timestamp":"2026-07-01T15:10:22Z","entity_id":"run_001_player","observation_id":"run_001","event_type":"resource_gained","attributes":{"amount":25,"resource_type":"gold","source":"quest_reward"}}
```

### Расход ресурса

```json
{"timestamp":"2026-07-01T15:11:05Z","entity_id":"run_001_player","observation_id":"run_001","event_type":"resource_spent","attributes":{"amount":10,"resource_type":"gold","sink":"upgrade"}}
```

### Попытка операции

```json
{"timestamp":"2026-07-01T15:12:00Z","entity_id":"upgrade_sword_01","observation_id":"run_001","event_type":"operation_attempted","attributes":{"operation_type":"upgrade","cost":120,"available_resource":80}}
```

### Блокировка операции

```json
{"timestamp":"2026-07-01T15:12:01Z","entity_id":"upgrade_sword_01","observation_id":"run_001","event_type":"operation_blocked","attributes":{"reason":"not_enough_resource","required":120,"available":80}}
```


### Получение награды

```json
{"timestamp":"2026-07-01T15:13:10Z","entity_id":"run_001_player","observation_id":"run_001","event_type":"reward_received","attributes":{"amount":25,"reward_type":"gold","source":"quest_reward"}}
```

### Использование контента

```json
{"timestamp":"2026-07-01T15:14:20Z","entity_id":"ability_fireball","observation_id":"run_001","event_type":"content_used","attributes":{"content_type":"ability","cost":15,"result":40,"context":"combat"}}
```

### Покупка апгрейда

```json
{"timestamp":"2026-07-01T15:15:00Z","entity_id":"upgrade_sword_01","observation_id":"run_001","event_type":"upgrade_purchased","attributes":{"cost":120,"result":18,"currency":"gold","upgrade_type":"weapon"}}
```

## Формат параметров: JSON

Параметры нужны для What-if и анализа причин.

```json
{
  "catalog_id": "upgrade_prices_v1",
  "build_id": "0.8.14-playtest",
  "schema_version": "1.0",
  "parameters": [
    {
      "entity_id": "upgrade_sword_01",
      "entity_type": "operation",
      "parameter_key": "cost_gold",
      "value": 120,
      "value_type": "number"
    }
  ]
}
```

## Формат параметров: CSV

```csv
entity_id,entity_type,parameter_key,value,value_type,build_id
upgrade_sword_01,operation,cost_gold,120,number,0.8.14-playtest
quest_01,reward,reward_gold,25,number,0.8.14-playtest
```

CSV-импорт параметров можно отложить на P1, но схема должна учитывать такую возможность.

## Ошибки импорта

| Ошибка | Что делать |
|---|---|
| строка не JSON | показать файл и номер строки |
| нет `timestamp` | событие невалидно |
| timestamp не парсится | событие невалидно |
| нет `entity_id` | событие невалидно |
| нет `event_type` | событие невалидно |
| `attributes` не object | событие невалидно |
| нет `observation_id` | можно импортировать, но создать auto observation |
| нет числовых полей | импортировать, но предупредить, что метрики ограничены |
| нет событий блокировки | bottleneck и недоступность операций не проверяются |
| нет usage-событий | мёртвый контент не проверяется |
| нет reward-событий с timestamp | pacing наград не проверяется |

## Политика частично битых файлов

MVP-вариант:

- если файл содержит битые строки, но есть валидные события, импорт продолжается;
- в отчёте показывается количество пропущенных строк;
- пользователь может открыть список ошибок.

## Отчёт импорта

Минимальные поля отчёта:

```text
source_files_count
read_lines
valid_events
invalid_events
imported_events
created_entities
created_observations
warnings
errors
```

## Версионирование

`schema_version` нужно поддерживать с первой версии формата.

Если версия неизвестна:

- импорт не должен падать;
- система должна предупредить пользователя;
- формат обрабатывается как best-effort.
