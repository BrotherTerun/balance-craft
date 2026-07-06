# FILE: `docs/diagrams/sequence_metric_run.md`

# Sequence diagram — metric run and dashboard

Дата: 2026-07-02  
Статус: рабочий черновик для Obsidian/Mermaid

## Назначение

Диаграмма показывает путь от сохранённого semantic binding до рассчитанных metric values, dashboard datasets и practical insights.

```mermaid
sequenceDiagram
  actor User as User
  participant UI as Frontend UI
  participant API as Backend API Facade
  participant Binding as Binding Service
  participant Templates as Metric Template Registry
  participant Engine as Metric Engine
  participant DB as DB Layer
  participant SQL as SQLite
  participant Dashboard as Dashboard Service
  participant Insights as Insight Engine

  User->>UI: Click Run Calculation
  UI->>API: runMetricCalculation(project_id, binding_set_id, scope)
  API->>Binding: getBindingSet(binding_set_id)
  Binding->>DB: read semantic_binding_sets and semantic_bindings
  DB->>SQL: SELECT bindings
  SQL-->>DB: binding rows
  DB-->>Binding: binding set

  API->>Templates: getTemplate(template_key)
  Templates-->>API: variables, formulas, metric definitions

  API->>Engine: runMetric(project_id, template, bindings, scope)
  Engine->>DB: create metric_run(status=running)
  DB->>SQL: INSERT metric_runs
  SQL-->>DB: metric_run_id
  DB-->>Engine: metric_run_id

  Engine->>DB: query events by binding filters and scope
  DB->>SQL: SELECT events WHERE project_id and filters
  SQL-->>DB: event rows
  DB-->>Engine: event rows

  Engine->>Engine: aggregate variables by x-axis and scope
  Engine->>Engine: calculate formulas
  Engine->>Engine: apply safe_div, N/A, warnings

  alt Calculation has values
    Engine->>DB: insert metric_values
    DB->>SQL: INSERT metric_values
    Engine->>DB: update metric_run(status=completed or completed_with_warnings)
    DB->>SQL: UPDATE metric_runs
  else No valid values
    Engine->>DB: update metric_run(status=failed)
    DB->>SQL: UPDATE metric_runs
  end

  Engine-->>API: metric_run summary
  API-->>UI: envelope(success, data, warnings, errors)

  UI->>API: getDashboardData(project_id, metric_run_id)
  API->>Dashboard: prepareDashboardData(metric_run_id)
  Dashboard->>DB: read metric_run and metric_values
  DB->>SQL: SELECT metric_runs, metric_values
  SQL-->>DB: metric data
  DB-->>Dashboard: metric data

  Dashboard->>Insights: generateInsights(metric series, warnings, coverage)
  Insights-->>Dashboard: insight cards

  Dashboard-->>API: chart datasets + insight cards
  API-->>UI: envelope(success, data, warnings, errors)
  UI-->>User: Render chart, warnings, insights
```

## Notes

- `metric_runs.binding_snapshot_json` и `metric_runs.formula_snapshot_json` нужны, чтобы старые результаты не менялись после правки binding/template.
- `safe_div` не подменяет нулевой знаменатель на `1`. Для такой точки должен быть `N/A` или warning.
- Dashboard получает уже подготовленные datasets. Frontend не должен собирать SQL-запросы или самостоятельно интерпретировать raw events.
