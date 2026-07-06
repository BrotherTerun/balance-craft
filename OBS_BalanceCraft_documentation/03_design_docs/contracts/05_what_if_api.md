# FILE: `03_design_docs/contracts/05_what_if_api.md`
# 05. What-if API

Дата: 2026-07-02  
Статус: proposed

## Назначение

Файл описывает frontend/backend API для простого параметрического What-if BalanceCraft Desktop 1.5.

Важно: What-if в 1.5 не является полноценной симуляцией игры. Контракт должен явно показывать:

- какие параметры доступны;
- что именно пересчитывается;
- какой `confidence_status` у результата;
- какие ограничения есть у сценария;
- что raw events не изменяются.

---

# Common DTOs

## WhatIfControl

```json
{
  "parameter_key": "cost_gold",
  "parameter_label": "Стоимость в золоте",
  "entity_id": "upgrade_sword_01",
  "entity_label": "Sword Upgrade I",
  "entity_type": "operation",
  "current_value": 120,
  "value_type": "number",
  "unit": "gold",
  "allowed_override_modes": ["set", "delta", "multiplier"],
  "linked_templates": ["flow_balance", "conversion_efficiency"],
  "confidence_if_changed": "impact_estimate"
}
```

## ScenarioOverrideInput

```json
{
  "entity_id": "upgrade_sword_01",
  "parameter_key": "cost_gold",
  "override_mode": "multiplier",
  "scenario_value": null,
  "delta": null,
  "multiplier": 0.8
}
```

## ScenarioSummary

```json
{
  "scenario_id": 2,
  "project_id": 1,
  "name": "Upgrade cost -20%",
  "base_metric_run_id": 4,
  "status": "completed_with_warnings",
  "confidence_status": "approx_recalc",
  "overrides_count": 1,
  "created_at": "2026-07-02T13:00:00Z"
}
```

## ScenarioComparisonDataset

```json
{
  "metric_key": "net_flow",
  "metric_label": "Чистый поток",
  "labels": ["run_001", "run_002", "run_003"],
  "historical_data": [15, 20, -5],
  "scenario_data": [12, 18, 2],
  "delta_data": [-3, -2, 7],
  "delta_percent_data": [-20.0, -10.0, 140.0],
  "status": ["ok", "ok", "warning"],
  "confidence_status": "approx_recalc"
}
```

---

# `getWhatIfControls(payload)`

Приоритет: P0/P1  
Side effect: read-only

## Назначение

Вернуть список параметров, которые пользователь может менять в What-if panel, и объяснить ограничения.

## Request

```json
{
  "project_id": 1,
  "base_metric_run_id": 4,
  "options": {
    "template_key": null,
    "entity_type_filter": null,
    "include_unlinked_parameters": true
  }
}
```

## Response `data`

```json
{
  "base_metric_run": {
    "metric_run_id": 4,
    "template_key": "flow_balance",
    "template_name": "Баланс потоков"
  },
  "controls": [
    {
      "parameter_key": "cost_gold",
      "parameter_label": "Стоимость в золоте",
      "entity_id": "upgrade_sword_01",
      "entity_label": "Sword Upgrade I",
      "entity_type": "operation",
      "current_value": 120,
      "value_type": "number",
      "unit": "gold",
      "allowed_override_modes": ["set", "delta", "multiplier"],
      "linked_templates": ["flow_balance", "conversion_efficiency"],
      "confidence_if_changed": "impact_estimate"
    }
  ],
  "limitations": [
    {
      "code": "IMPACT_ESTIMATE_ONLY",
      "message": "Для части параметров нет правил точного пересчёта. Сценарий покажет оценку влияния."
    }
  ]
}
```

## Empty state

Если параметров нет:

```json
{
  "controls": [],
  "empty_state": {
    "code": "NO_PARAMETERS",
    "title": "Нет параметров для What-if",
    "message": "Импортируйте параметры или используйте demo project.",
    "next_action": "open_parameter_import"
  }
}
```

## Notes

В P0 допустимо получать параметры из demo seed или уже существующих `entity_parameters`. Полноценный import parameters может быть P1.

---

# `runScenario(payload)`

Приоритет: P0/P1  
Side effect: compute-write

## Назначение

Создать или обновить сценарий, применить parameter overrides к доступному уровню What-if и сохранить scenario results.

## Request

```json
{
  "project_id": 1,
  "scenario": {
    "scenario_id": null,
    "name": "Upgrade cost -20%",
    "description": "Проверяем снижение цены апгрейда меча.",
    "base_metric_run_id": 4,
    "overrides": [
      {
        "entity_id": "upgrade_sword_01",
        "parameter_key": "cost_gold",
        "override_mode": "multiplier",
        "multiplier": 0.8
      }
    ]
  },
  "options": {
    "run_level": "auto",
    "save_results": true
  }
}
```

## Override modes

| Mode | Смысл |
|---|---|
| `set` | заменить значение на `scenario_value` |
| `delta` | прибавить `delta` |
| `multiplier` | умножить на `multiplier` |

## Writes

- `scenarios`
- `scenario_overrides`
- `scenario_results`

Raw tables not changed:

- `events`
- `metric_values` historical values
- `entity_parameters` original values

## Response `data`

```json
{
  "scenario": {
    "scenario_id": 2,
    "project_id": 1,
    "name": "Upgrade cost -20%",
    "base_metric_run_id": 4,
    "status": "completed_with_warnings",
    "confidence_status": "approx_recalc",
    "overrides_count": 1
  },
  "result_summary": {
    "scenario_results_count": 50,
    "affected_metrics": ["net_flow", "spend_income_ratio"],
    "changed_points_count": 12,
    "na_values_count": 0
  },
  "limitations": [
    {
      "code": "APPROX_RECALC",
      "message": "Сценарий пересчитывает историю при прежней последовательности событий. Поведение игрока не моделируется."
    }
  ],
  "next_action": "open_scenario_result"
}
```

## Confidence status rules

| Status | Когда возвращать |
|---|---|
| `exact_recalc` | есть binding, формула пересчёта и все данные; sequence событий не меняется |
| `approx_recalc` | пересчёт частичный или использует допущения |
| `impact_estimate` | параметр связан с событиями/метриками, но нет формулы пересчёта |
| `insufficient_model` | нет dependency rule или связи parameter → metric |
| `insufficient_data` | не хватает событий, параметров или ряд слишком короткий |

## Errors

- `SCENARIO_INVALID`
- `SCENARIO_RUN_FAILED`
- `UNSUPPORTED_IN_VERSION`
- `METRIC_CALCULATION_FAILED`

## Warnings

- `IMPACT_ESTIMATE_ONLY`
- `APPROX_RECALC`
- `LOW_SAMPLE_SIZE`
- `UNCOMPARABLE_UNITS`

---

# `getScenarioResult(payload)`

Приоритет: P0/P1  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "scenario_id": 2,
  "options": {
    "metric_keys": null,
    "include_deltas": true,
    "include_insights": true
  }
}
```

## Response `data`

```json
{
  "scenario": {
    "scenario_id": 2,
    "project_id": 1,
    "name": "Upgrade cost -20%",
    "base_metric_run_id": 4,
    "status": "completed_with_warnings",
    "confidence_status": "approx_recalc"
  },
  "comparison": {
    "labels": ["run_001", "run_002", "run_003"],
    "datasets": [
      {
        "metric_key": "net_flow",
        "metric_label": "Чистый поток",
        "historical_data": [15, 20, -5],
        "scenario_data": [12, 18, 2],
        "delta_data": [-3, -2, 7],
        "delta_percent_data": [-20.0, -10.0, 140.0],
        "status": ["ok", "ok", "warning"],
        "confidence_status": "approx_recalc"
      }
    ]
  },
  "insights": [
    {
      "insight_id": "scenario_ins_001",
      "level": "info",
      "category": "what_if",
      "title": "Сценарий снижает дефицит в одном окне",
      "text": "После снижения цены апгрейда чистый поток в run_003 становится положительным.",
      "recommendation": "Проверьте, не создаёт ли это профицит на более длинной истории.",
      "metric_keys": ["net_flow"],
      "confidence": "scenario_estimate",
      "evidence": {
        "window": "run_003",
        "historical_value": -5,
        "scenario_value": 2
      }
    }
  ],
  "limitations": [
    {
      "code": "APPROX_RECALC",
      "message": "Поведение игрока не моделируется; последовательность событий сохранена."
    }
  ]
}
```

## Empty state

Если сценарий создан, но результат не рассчитан:

```json
{
  "empty_state": {
    "code": "SCENARIO_NOT_RUN",
    "title": "Сценарий ещё не рассчитан",
    "message": "Запустите What-if, чтобы увидеть сравнение.",
    "next_action": "run_scenario"
  }
}
```

---

# What-if UI obligations

UI должен показывать рядом со сценарием:

- `confidence_status`;
- limitations;
- что raw history не изменена;
- что MVP не моделирует новое поведение игрока.

Запрещённая формулировка:

```text
Игра будет вести себя вот так.
```

Корректная формулировка:

```text
При той же истории событий и изменённом параметре метрика изменилась бы так.
```

или:

```text
Параметр связан с этими метриками, но для точного пересчёта не хватает модели.
```

## Review notes

1. Для P0 можно ограничиться одним override за сценарий, если multi-override усложнит UI.
2. `runScenario()` сейчас объединяет create/update/run. Можно разделить на `createScenario()` и `runScenario()`, но для MVP единый метод проще.
3. Если parameter import не входит в P0, demo project должен содержать seeded parameters, иначе What-if будет нечего менять.
4. Нужно не дать UI назвать `impact_estimate` “прогнозом”. Это только оценка потенциального влияния.
