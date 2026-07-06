# FILE: `docs/contracts/04_dashboard_insights_api.md`

# 04. Dashboard and insights API

Дата: 2026-07-02  
Статус: proposed

## Назначение

Файл описывает API для:

- получения данных dashboard;
- построения графиков;
- отображения metric cards;
- вывода practical insights;
- связанных warnings и empty states.

---

# Common DTOs

## DashboardData

```json
{
  "metric_run_id": 4,
  "project_id": 1,
  "title": "Gold flow by run",
  "labels": ["run_001", "run_002", "run_003"],
  "datasets": [],
  "metric_cards": [],
  "insights": [],
  "warnings": [],
  "available_actions": []
}
```

## ChartDataset

```json
{
  "dataset_key": "net_flow",
  "metric_key": "net_flow",
  "label": "Чистый поток",
  "data": [15, 20, -5],
  "status": ["ok", "ok", "ok"],
  "warnings_by_point": [[], [], []],
  "unit": "gold",
  "display": {
    "chart_type": "line",
    "y_axis": "left"
  }
}
```

## MetricCard

```json
{
  "metric_key": "net_flow",
  "label": "Чистый поток",
  "current_value": -5,
  "status": "warning",
  "summary": "В последнем окне расход превысил доход.",
  "unit": "gold"
}
```

## Insight

```json
{
  "insight_id": "ins_001",
  "level": "warning",
  "category": "flow_balance",
  "title": "Расход выше дохода",
  "text": "В 3 из 10 окон расход ресурса выше дохода.",
  "recommendation": "Проверьте источники дохода или стоимость операций в этих окнах.",
  "metric_keys": ["net_flow", "spend_income_ratio"],
  "evidence": {
    "windows": ["run_003", "run_007", "run_008"],
    "values": {
      "net_flow_min": -45
    }
  },
  "confidence": "diagnostic"
}
```

---

# `getDashboardData(payload)`

Приоритет: P0  
Side effect: read-only

## Назначение

Получить данные для dashboard после metric run.

Метод должен возвращать DTO, удобный для Chart.js/UI, а не сырые строки `metric_values`.

## Request

```json
{
  "project_id": 1,
  "metric_run_id": 4,
  "options": {
    "metric_keys": ["net_flow", "spend_income_ratio"],
    "scope_filter": null,
    "include_insights": true,
    "include_metric_cards": true,
    "include_warnings": true
  }
}
```

## Response `data`

```json
{
  "dashboard": {
    "metric_run_id": 4,
    "project_id": 1,
    "title": "Gold flow by run",
    "template_key": "flow_balance",
    "template_name": "Баланс потоков",
    "scope": {
      "group_by": "observation_id",
      "filters": {
        "build_id": "demo-1.0"
      }
    },
    "labels": ["run_001", "run_002", "run_003"],
    "datasets": [
      {
        "dataset_key": "net_flow",
        "metric_key": "net_flow",
        "label": "Чистый поток",
        "data": [15, 20, -5],
        "status": ["ok", "ok", "ok"],
        "warnings_by_point": [[], [], []],
        "unit": "gold",
        "display": {
          "chart_type": "line",
          "y_axis": "left"
        }
      }
    ],
    "metric_cards": [
      {
        "metric_key": "net_flow",
        "label": "Чистый поток",
        "current_value": -5,
        "status": "warning",
        "summary": "В последнем окне расход превысил доход.",
        "unit": "gold"
      }
    ],
    "insights": [],
    "available_actions": ["open_data_map", "open_binding_wizard", "open_what_if"]
  }
}
```

## Empty states

- `NO_METRIC_RUNS`
- `NO_DASHBOARD_DATA`

## Warnings

Dashboard-level warnings должны агрегировать point-level warnings, но не скрывать их.

Пример:

```json
{
  "code": "SAFE_DIV_NA",
  "message": "3 значения отношения не рассчитаны из-за нулевого знаменателя.",
  "details": {
    "metric_key": "spend_income_ratio",
    "affected_points": 3
  }
}
```

## Notes

- `data` в dataset может содержать `null`, если point имеет status `n/a`.
- UI должен уметь показывать gaps/markers для `null` значений.
- Backend не должен заменять `null` на 0 для красоты графика.

---

# `getInsights(payload)`

Приоритет: P0/P1  
Side effect: read-only or compute-read

## Назначение

Получить practical insights для metric run или scenario.

Метод можно использовать отдельно от `getDashboardData()` для lazy loading или повторного вычисления insights после изменения thresholds.

## Request for metric run

```json
{
  "project_id": 1,
  "source_kind": "metric_run",
  "metric_run_id": 4,
  "options": {
    "level_filter": null,
    "category_filter": null,
    "limit": 20
  }
}
```

## Request for scenario

```json
{
  "project_id": 1,
  "source_kind": "scenario",
  "scenario_id": 2,
  "options": {
    "include_comparison_insights": true,
    "limit": 20
  }
}
```

## Response `data`

```json
{
  "insights": [
    {
      "insight_id": "ins_001",
      "level": "warning",
      "category": "flow_balance",
      "title": "Расход выше дохода",
      "text": "В 3 из 10 окон расход ресурса выше дохода.",
      "recommendation": "Проверьте источники дохода или стоимость операций в этих окнах.",
      "metric_keys": ["net_flow", "spend_income_ratio"],
      "evidence": {
        "windows": ["run_003", "run_007", "run_008"],
        "values": {
          "net_flow_min": -45
        }
      },
      "confidence": "diagnostic"
    }
  ]
}
```

## Insight levels

```text
info
warning
critical
```

## Insight confidence

Для MVP:

```text
diagnostic
limited_data
scenario_estimate
```

Это не то же самое, что `scenario.confidence_status`, но scenario insight может ссылаться на него.

## Notes

- Insight должен иметь evidence.
- Insight не должен звучать как абсолютная причинная истина.
- Если данных мало, insight должен быть `limited_data` или warning должен объяснять ограничение.

---

# Dashboard available actions

Backend может вернуть список доступных UI actions.

```json
{
  "available_actions": [
    {
      "action_key": "open_what_if",
      "label": "Проверить What-if",
      "enabled": true
    },
    {
      "action_key": "open_parameter_import",
      "label": "Добавить параметры",
      "enabled": false,
      "disabled_reason": "Импорт параметров не входит в текущий P0."
    }
  ]
}
```

Для P0 допускается простой массив строк, но object-format лучше для UI.

---

# Dashboard compatibility with scenarios

`getDashboardData()` может в будущем поддерживать scenario overlay:

```json
{
  "project_id": 1,
  "metric_run_id": 4,
  "options": {
    "scenario_id": 2,
    "include_scenario_overlay": true
  }
}
```

Для MVP можно держать scenario comparison в `getScenarioResult()`, чтобы не перегружать dashboard contract.
