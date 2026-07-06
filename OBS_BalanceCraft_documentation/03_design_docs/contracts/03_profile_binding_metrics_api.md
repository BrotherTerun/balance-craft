# FILE: `docs/contracts/03_profile_binding_metrics_api.md`

# 03. Data profile, coverage, bindings and metric calculation API

Дата: 2026-07-02  
Статус: proposed

## Назначение

Файл описывает API для:

- карты данных;
- coverage проверки;
- metric templates;
- semantic bindings;
- metric runs.

---

# Common DTOs

## DataProfile

```json
{
  "project_id": 1,
  "profile_built_at": "2026-07-02T12:20:00Z",
  "events_count": 1250,
  "event_types": [],
  "attributes": [],
  "numeric_attributes": [],
  "warnings": []
}
```

## EventTypeProfile

```json
{
  "event_type": "resource_gained",
  "count": 420,
  "first_seen_at": "2026-07-02T12:00:01Z",
  "last_seen_at": "2026-07-02T12:30:00Z",
  "attributes": ["amount", "resource_type", "source"],
  "sample_event": {
    "timestamp": "2026-07-02T12:00:01Z",
    "entity_id": "actor_001",
    "event_type": "resource_gained",
    "attributes": {
      "amount": 25,
      "resource_type": "gold"
    }
  }
}
```

## AttributeProfile

```json
{
  "attribute_key": "amount",
  "event_type": "resource_gained",
  "count": 420,
  "numeric_count": 420,
  "string_count": 0,
  "boolean_count": 0,
  "null_count": 0,
  "min_value": 1,
  "max_value": 250,
  "sample_values": [25, 10, 50]
}
```

## AnalysisCoverageItem

```json
{
  "problem_key": "deficit",
  "problem_label": "Дефицит ресурса",
  "status": "available",
  "template_key": "flow_balance",
  "required_signals": ["flow_in", "flow_out"],
  "available_signals": ["resource_gained.amount", "resource_spent.amount"],
  "missing_signals": [],
  "explanation": "Есть события дохода и расхода с числовым amount."
}
```

## MetricTemplateSummary

```json
{
  "template_key": "flow_balance",
  "name": "Баланс потоков",
  "priority": "P0",
  "description": "Анализ входящих и исходящих значений.",
  "variables": [],
  "metrics": []
}
```

## BindingSet

```json
{
  "binding_set_id": 3,
  "project_id": 1,
  "template_key": "flow_balance",
  "name": "Gold flow",
  "scope_json": {
    "group_by": "observation_id"
  },
  "bindings": []
}
```

## SemanticBinding

```json
{
  "variable_key": "flow_in",
  "source_kind": "event_attribute",
  "source_path": "attributes.amount",
  "event_types": ["resource_gained"],
  "aggregation": "sum",
  "filters": {
    "attributes.resource_type": "gold"
  },
  "label": "Доход золота"
}
```

## Scope DTO

```json
{
  "group_by": "observation_id",
  "filters": {
    "build_id": "demo-1.0"
  }
}
```

Допустимые значения `group_by` в BalanceCraft 1.5:

```text
whole_project
entity_id
observation_id
observation_type
event_type
build_id
```

Правила:

- `whole_project` создаёт одну группу для всего выбранного набора данных;
- остальные значения группируют по соответствующему стабильному ключу;
- неизвестный `group_by` возвращает validation error;
- порядок точек и присвоение `x_index` выполняются по deterministic rules из `21_data_flows.md`.

## Aggregation enum

Допустимые P0-значения:

```text
sum
avg
min
max
count
first
last
```

Default aggregation не определяется по типу числового поля. Его задаёт variable definition внутри MetricTemplate.

Правила:

- request может не передавать `aggregation`, только если template variable имеет `default_aggregation`;
- backend сохраняет и возвращает effective aggregation в binding;
- если нет ни явной aggregation, ни template default, binding validation завершается ошибкой;
- `sum` не должен автоматически применяться ко всем numeric attributes.

---

# `getDataProfile(payload)`

Приоритет: P0  
Side effect: read-only or compute-read if profile is rebuilt on demand

## Request

```json
{
  "project_id": 1,
  "options": {
    "include_samples": true,
    "include_attribute_profiles": true,
    "event_type_filter": null,
    "rebuild_if_stale": true
  }
}
```

## Response `data`

```json
{
  "profile": {
    "project_id": 1,
    "profile_built_at": "2026-07-02T12:20:00Z",
    "events_count": 1250,
    "event_types": [
      {
        "event_type": "resource_gained",
        "count": 420,
        "attributes": ["amount", "resource_type", "source"]
      }
    ],
    "attributes": [
      {
        "attribute_key": "amount",
        "event_type": "resource_gained",
        "numeric_count": 420,
        "min_value": 1,
        "max_value": 250,
        "sample_values": [25, 10, 50]
      }
    ],
    "numeric_attributes": [
      "attributes.amount",
      "attributes.cost",
      "attributes.result"
    ]
  }
}
```

## Empty states

- `NO_IMPORTED_EVENTS`
- `NO_NUMERIC_ATTRIBUTES`

---

# `getAnalysisCoverage(payload)`

Приоритет: P0 for on-the-fly basic coverage, P1 for cached/expanded coverage  
Side effect: read-only or compute-read

## Request

```json
{
  "project_id": 1,
  "binding_set_id": 3,
  "options": {
    "include_p1_problems": true,
    "include_missing_signals": true
  }
}
```

`binding_set_id` optional. Если binding ещё нет, coverage строится по data profile и показывает потенциальное покрытие.

## Response `data`

```json
{
  "coverage": [
    {
      "problem_key": "deficit",
      "problem_label": "Дефицит ресурса",
      "status": "available",
      "template_key": "flow_balance",
      "required_signals": ["flow_in", "flow_out"],
      "available_signals": ["resource_gained.amount", "resource_spent.amount"],
      "missing_signals": [],
      "explanation": "Есть события дохода и расхода с числовым amount."
    },
    {
      "problem_key": "bottleneck",
      "problem_label": "Бутылочное горлышко",
      "status": "missing_data",
      "template_key": "action_availability",
      "required_signals": ["operation_attempted", "operation_blocked"],
      "available_signals": ["operation_attempted"],
      "missing_signals": ["operation_blocked.reason"],
      "explanation": "Нет событий блокировки с причиной отказа."
    }
  ]
}
```

## Notes

Coverage не должен блокировать metric run, если выбранный template валиден.

---

# `listMetricTemplates(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "priority_filter": ["P0", "P1"],
  "include_variables": true,
  "include_metrics": true
}
```

## Response `data`

```json
{
  "templates": [
    {
      "template_key": "flow_balance",
      "name": "Баланс потоков",
      "priority": "P0",
      "description": "Анализ входящих и исходящих значений.",
      "variables": [
        {
          "variable_key": "flow_in",
          "label": "Входящий поток",
          "required": true,
          "accepted_source_kinds": ["event_attribute"],
          "accepted_value_types": ["number"]
        }
      ],
      "metrics": [
        {
          "metric_key": "net_flow",
          "label": "Чистый поток",
          "formula_label": "Σflow_in - Σflow_out"
        }
      ]
    }
  ]
}
```

---

# `getMetricTemplate(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "template_key": "flow_balance"
}
```

## Response `data`

```json
{
  "template": {
    "template_key": "flow_balance",
    "name": "Баланс потоков",
    "description": "Анализ входящих и исходящих значений.",
    "variables": [],
    "metrics": [],
    "default_scope": {
      "group_by": "observation_id"
    },
    "warnings": []
  }
}
```

---

# `validateBindingSet(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "binding_set": {
    "template_key": "flow_balance",
    "name": "Gold flow",
    "scope_json": {
      "group_by": "observation_id"
    },
    "bindings": [
      {
        "variable_key": "flow_in",
        "source_kind": "event_attribute",
        "source_path": "attributes.amount",
        "event_types": ["resource_gained"],
        "aggregation": "sum",
        "filters": {
          "attributes.resource_type": "gold"
        },
        "label": "Доход золота"
      }
    ]
  }
}
```

## Response `data`

```json
{
  "valid": true,
  "binding_preview": {
    "matched_events": 420,
    "matched_observations": 25,
    "sample_values": [25, 10, 50]
  },
  "variable_statuses": [
    {
      "variable_key": "flow_in",
      "status": "ok",
      "matched_events": 420,
      "warnings": []
    }
  ]
}
```

## Errors

- `TEMPLATE_NOT_FOUND`
- `BINDING_INVALID`
- `VALIDATION_ERROR`

---

# `saveBindingSet(payload)`

Приоритет: P0  
Side effect: write

## Request

```json
{
  "project_id": 1,
  "binding_set": {
    "binding_set_id": null,
    "template_key": "flow_balance",
    "name": "Gold flow",
    "scope_json": {
      "group_by": "observation_id"
    },
    "bindings": []
  }
}
```

Если `binding_set_id = null`, создаётся новый set. Если ID передан, обновляется существующий.

## Writes

- `semantic_binding_sets`
- `semantic_bindings`

## Response `data`

```json
{
  "binding_set": {
    "binding_set_id": 3,
    "project_id": 1,
    "template_key": "flow_balance",
    "name": "Gold flow",
    "bindings_count": 2,
    "updated_at": "2026-07-02T12:40:00Z"
  },
  "next_action": "run_metric_calculation"
}
```

## Notes

Сохранение binding не должно автоматически пересчитывать все metric runs. UI может предложить запустить новый расчёт.

---

# `listBindingSets(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "template_key": null
}
```

## Response `data`

```json
{
  "binding_sets": [
    {
      "binding_set_id": 3,
      "template_key": "flow_balance",
      "name": "Gold flow",
      "bindings_count": 2,
      "updated_at": "2026-07-02T12:40:00Z"
    }
  ]
}
```

---

# `getBindingSet(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "binding_set_id": 3
}
```

## Response `data`

```json
{
  "binding_set": {
    "binding_set_id": 3,
    "project_id": 1,
    "template_key": "flow_balance",
    "name": "Gold flow",
    "scope_json": {
      "group_by": "observation_id"
    },
    "bindings": []
  }
}
```

---

# `runMetricCalculation(payload)`

Приоритет: P0  
Side effect: compute-write

## Request

```json
{
  "project_id": 1,
  "binding_set_id": 3,
  "options": {
    "scope": {
      "group_by": "observation_id",
      "filters": {
        "build_id": "demo-1.0"
      }
    },
    "run_label": "Gold flow by run",
    "recalculate": false
  }
}
```

## Writes

- `metric_runs`
- `metric_values`

## Response `data`

```json
{
  "metric_run": {
    "metric_run_id": 4,
    "project_id": 1,
    "binding_set_id": 3,
    "template_key": "flow_balance",
    "status": "completed_with_warnings",
    "metric_values_count": 50,
    "started_at": "2026-07-02T12:45:00Z",
    "finished_at": "2026-07-02T12:45:02Z"
  },
  "calculation_summary": {
    "groups_count": 25,
    "metrics_count": 2,
    "na_values_count": 3,
    "warnings_count": 3
  },
  "next_action": "open_dashboard"
}
```

## Warnings

- `SAFE_DIV_NA`
- `LOW_SAMPLE_SIZE`
- `UNCOMPARABLE_UNITS`
- `NO_NUMERIC_VALUES`

## Notes

`metric_run` сохраняет snapshots binding/formula, чтобы старые расчёты не менялись после правки binding.

---

# `listMetricRuns(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "template_key": null,
  "binding_set_id": null,
  "limit": 20
}
```

## Response `data`

```json
{
  "metric_runs": [
    {
      "metric_run_id": 4,
      "template_key": "flow_balance",
      "template_name": "Баланс потоков",
      "run_label": "Gold flow by run",
      "status": "completed_with_warnings",
      "created_at": "2026-07-02T12:45:00Z",
      "warnings_count": 3
    }
  ]
}
```

---

# `getMetricRun(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "metric_run_id": 4,
  "include_snapshots": false,
  "include_warnings": true
}
```

## Response `data`

```json
{
  "metric_run": {
    "metric_run_id": 4,
    "project_id": 1,
    "template_key": "flow_balance",
    "template_name": "Баланс потоков",
    "status": "completed_with_warnings",
    "metric_values_count": 50,
    "warnings": []
  }
}
```
