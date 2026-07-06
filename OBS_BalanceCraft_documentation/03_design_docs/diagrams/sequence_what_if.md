# FILE: `03_design_docs/diagrams/sequence_what_if.md`
# Sequence diagram — simple What-if scenario

Дата: 2026-07-02  
Статус: рабочий черновик для Obsidian/Mermaid

## Назначение

Диаграмма показывает простой параметрический What-if: выбор параметра, сохранение scenario override, определение confidence status, расчёт scenario results и показ сравнения в dashboard.

```mermaid
sequenceDiagram
  actor User as User
  participant UI as What-if Panel
  participant API as Backend API Facade
  participant WhatIf as What-if Engine
  participant Binding as Binding Service
  participant Metrics as Metric Engine
  participant DB as DB Layer
  participant SQL as SQLite
  participant Dashboard as Dashboard Service

  User->>UI: Open What-if panel
  UI->>API: getWhatIfControls(project_id, metric_run_id)
  API->>WhatIf: getControllableParameters(project_id, metric_run_id)

  WhatIf->>DB: read entity_parameters
  DB->>SQL: SELECT entity_parameters
  SQL-->>DB: parameters
  DB-->>WhatIf: parameters

  WhatIf->>Binding: get metric/binding context
  Binding->>DB: read bindings and metric_run snapshots
  DB->>SQL: SELECT semantic_bindings, metric_runs
  SQL-->>DB: binding context
  DB-->>Binding: binding context
  Binding-->>WhatIf: binding context

  WhatIf-->>API: controllable parameters + limitations
  API-->>UI: envelope(success, data, warnings, errors)
  UI-->>User: Show parameters and confidence hints

  User->>UI: Change parameter value
  UI->>API: runScenario(project_id, base_metric_run_id, overrides)
  API->>WhatIf: createScenarioAndRun(overrides)

  WhatIf->>DB: insert scenario
  DB->>SQL: INSERT scenarios
  SQL-->>DB: scenario_id
  DB-->>WhatIf: scenario_id

  WhatIf->>DB: insert scenario_overrides
  DB->>SQL: INSERT scenario_overrides

  WhatIf->>WhatIf: determine confidence_status

  alt exact_recalc
    WhatIf->>Metrics: recalculate with parameter override and same event sequence
    Metrics-->>WhatIf: scenario metric series
    WhatIf->>DB: insert scenario_results(confidence=exact_recalc)
    DB->>SQL: INSERT scenario_results
  else approx_recalc
    WhatIf->>Metrics: recalculate with simplified assumptions
    Metrics-->>WhatIf: approximate scenario metric series
    WhatIf->>DB: insert scenario_results(confidence=approx_recalc)
    DB->>SQL: INSERT scenario_results
  else impact_estimate
    WhatIf->>WhatIf: build impact-only result
    WhatIf->>DB: insert scenario_results(confidence=impact_estimate)
    DB->>SQL: INSERT scenario_results
  else insufficient_model
    WhatIf->>DB: update scenario(confidence=insufficient_model)
    DB->>SQL: UPDATE scenarios
  else insufficient_data
    WhatIf->>DB: update scenario(confidence=insufficient_data)
    DB->>SQL: UPDATE scenarios
  end

  WhatIf-->>API: scenario summary
  API-->>UI: envelope(success, data, warnings, errors)

  UI->>API: getDashboardData(project_id, base_metric_run_id, scenario_id)
  API->>Dashboard: prepareComparisonDataset(base_metric_run_id, scenario_id)
  Dashboard->>DB: read metric_values and scenario_results
  DB->>SQL: SELECT metric_values, scenario_results
  SQL-->>DB: comparison rows
  DB-->>Dashboard: comparison rows
  Dashboard-->>API: historical + scenario datasets
  API-->>UI: envelope(success, data, warnings, errors)
  UI-->>User: Show historical line, scenario line, confidence status
```

## Notes

- What-if не меняет `events` и `metric_values`.
- `scenario_results` хранятся отдельно, чтобы не смешивать историю и сценарий.
- MVP не пересимулирует поведение пользователя. Он пересчитывает доступный слой при той же истории событий или честно показывает ограничение.
- `confidence_status` — rule-based статус, а не вероятность и не математическая гарантия.
