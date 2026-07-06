# FILE: `03_design_docs/contracts/01_common_envelope.md`
# 01. Common envelope, errors, warnings and DTO rules

Дата: 2026-07-02  
Статус: proposed

## Общий envelope

Все публичные методы frontend/backend API возвращают envelope.

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": []
}
```

Optional diagnostic block:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": [],
  "meta": {
    "api_version": "1.5-draft",
    "request_id": "req_20260702_000001",
    "duration_ms": 42
  }
}
```

`meta` не обязателен для UI P0.

## Success envelope

```json
{
  "success": true,
  "data": {
    "project_id": 1
  },
  "warnings": [],
  "errors": []
}
```

## Partial success

Используется, когда операция выполнена, но есть ограничения.

Пример: импорт завершён, но часть строк пропущена.

```json
{
  "success": true,
  "data": {
    "import_run_id": 10,
    "read_lines": 1000,
    "valid_events": 980,
    "invalid_events": 20
  },
  "warnings": [
    {
      "code": "SOME_LINES_SKIPPED",
      "message": "20 строк не были импортированы из-за ошибок формата.",
      "hint": "Откройте отчёт импорта, чтобы увидеть файл и номера строк.",
      "details": {
        "invalid_events": 20
      }
    }
  ],
  "errors": []
}
```

## Error envelope

Используется, когда операция не может быть завершена.

```json
{
  "success": false,
  "data": null,
  "warnings": [],
  "errors": [
    {
      "code": "PROJECT_NOT_FOUND",
      "message": "Проект не найден.",
      "hint": "Проверьте список последних проектов или откройте проект заново.",
      "recoverable": true,
      "details": {
        "project_id": 99
      }
    }
  ]
}
```

## Error object

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `code` | string | да | стабильный технический код |
| `message` | string | да | человекочитаемое сообщение |
| `hint` | string/null | нет | что пользователь может сделать |
| `recoverable` | boolean | да | можно ли продолжить после действия пользователя |
| `details` | object/null | нет | технические детали без traceback |
| `field` | string/null | нет | поле input, если ошибка связана с формой |
| `severity` | string | нет | `error`, `critical` |

Backend не должен возвращать raw traceback в `message`.

## Warning object

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `code` | string | да | стабильный технический код |
| `message` | string | да | человекочитаемое предупреждение |
| `hint` | string/null | нет | что можно проверить |
| `details` | object/null | нет | дополнительные данные |
| `severity` | string | нет | `info`, `warning` |

## Empty state object

Empty state — не ошибка. Он возвращается в `data.empty_state` при `success: true`.

```json
{
  "success": true,
  "data": {
    "empty_state": {
      "code": "NO_IMPORTED_EVENTS",
      "title": "В проекте ещё нет событий",
      "message": "Импортируйте JSONL или откройте demo project.",
      "next_action": "open_import"
    }
  },
  "warnings": [],
  "errors": []
}
```

## Standard empty state codes

| Code | Когда использовать | Next action |
|---|---|---|
| `NO_PROJECTS` | нет проектов | `create_project` / `open_demo` |
| `NO_IMPORTED_EVENTS` | в проекте нет событий | `open_import` |
| `NO_DATA_PROFILE` | профиль ещё не построен | `build_profile` |
| `NO_NUMERIC_ATTRIBUTES` | нет числовых attributes | `open_data_map` |
| `NO_BINDINGS` | нет semantic bindings | `open_binding_wizard` |
| `NO_METRIC_RUNS` | нет расчётов | `run_metric_calculation` |
| `NO_DASHBOARD_DATA` | расчёт есть, но нет графиков | `check_binding` |
| `NO_PARAMETERS` | нет параметров для What-if | `open_parameter_import` |
| `SCENARIO_NOT_RUN` | сценарий создан, но не рассчитан | `run_scenario` |

## Standard error codes

| Code | Смысл |
|---|---|
| `VALIDATION_ERROR` | некорректный input payload |
| `PROJECT_NOT_FOUND` | проект не найден |
| `PROJECT_OPEN_FAILED` | проект не удалось открыть |
| `DATABASE_ERROR` | ошибка SQLite/DB layer |
| `FILE_NOT_FOUND` | файл не найден |
| `FILE_READ_ERROR` | файл нельзя прочитать |
| `JSON_PARSE_ERROR` | строка не является JSON |
| `INVALID_EVENT_SCHEMA` | событие не соответствует минимальной схеме |
| `IMPORT_FAILED` | импорт не завершён |
| `PROFILE_NOT_AVAILABLE` | нет данных для карты данных |
| `TEMPLATE_NOT_FOUND` | шаблон не найден |
| `BINDING_INVALID` | semantic binding некорректен |
| `METRIC_CALCULATION_FAILED` | расчёт метрик упал |
| `DASHBOARD_DATA_UNAVAILABLE` | нет данных для dashboard |
| `SCENARIO_INVALID` | сценарий некорректен |
| `SCENARIO_RUN_FAILED` | сценарий не рассчитан |
| `UNSUPPORTED_IN_VERSION` | фича не поддерживается в текущей версии |

## Standard warning codes

| Code | Смысл |
|---|---|
| `PARTIAL_IMPORT` | часть данных импортирована, часть пропущена |
| `MISSING_OPTIONAL_FIELD` | нет желательного поля вроде `build_id` |
| `AUTO_OBSERVATION_CREATED` | создано автоматическое observation |
| `MIXED_ATTRIBUTE_TYPES` | поле имеет разные типы значений |
| `NO_NUMERIC_VALUES` | нет числовых значений для метрики |
| `SAFE_DIV_NA` | знаменатель равен нулю/почти нулю |
| `LOW_SAMPLE_SIZE` | слишком мало точек |
| `UNCOMPARABLE_UNITS` | cost/result не в сопоставимых единицах |
| `COVERAGE_PARTIAL` | проблема покрыта частично |
| `IMPACT_ESTIMATE_ONLY` | What-if показывает только потенциальное влияние |
| `APPROX_RECALC` | сценарий приближённый |

## Status fields

Некоторые DTO используют `status`.

### Import run status

```text
created
running
completed
completed_with_warnings
failed
cancelled
```

### Metric run status

```text
queued
running
completed
completed_with_warnings
failed
```

### Metric value status

```text
ok
n/a
warning
error
```

### Analysis coverage status

```text
available
partially_available
missing_data
unsupported_in_version
```

### Scenario confidence status

```text
exact_recalc
approx_recalc
impact_estimate
insufficient_model
insufficient_data
```

## DTO hygiene rules

1. DTO должен быть serializable в JSON.
2. DTO не должен содержать Python objects, datetime objects без string serialization или raw exceptions.
3. Время передаётся как ISO 8601 UTC string; backend нормализует входные timestamp до UTC до сохранения и ответа.
4. UI-visible text передаётся отдельно от technical keys.
5. Числа, которые нельзя корректно посчитать, не заменяются нулём или единицей.
6. Для `N/A` используется `value: null` + `status: "n/a"` + warning.

## Example `N/A` metric value

```json
{
  "metric_key": "spend_income_ratio",
  "metric_label": "Доля расхода к доходу",
  "x_index": 4,
  "x_label": "run_004",
  "value": null,
  "status": "n/a",
  "warnings": [
    {
      "code": "SAFE_DIV_NA",
      "message": "Метрика не рассчитана: входящий поток равен нулю.",
      "details": {
        "denominator": 0
      }
    }
  ]
}
```
