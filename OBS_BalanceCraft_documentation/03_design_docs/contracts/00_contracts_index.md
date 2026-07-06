# FILE: `docs/contracts/00_contracts_index.md`

# Backend ↔ Frontend contracts index

Дата: 2026-07-02  
Статус: рабочий черновик для проектирования и ревью

## Назначение

Индекс детальных API-контрактов BalanceCraft Desktop 1.5.

Главный обзор находится в `../22_backend_frontend_contracts.md`.

## Файлы

```text
01_common_envelope.md
02_project_and_import_api.md
03_profile_binding_metrics_api.md
04_dashboard_insights_api.md
05_what_if_api.md
```

## Рекомендуемый порядок чтения

1. `01_common_envelope.md` — общий формат ответа, ошибок, warnings, empty states.
2. `02_project_and_import_api.md` — project lifecycle, demo project, JSONL import.
3. `03_profile_binding_metrics_api.md` — data profile, analysis coverage, templates, semantic bindings, metric runs.
4. `04_dashboard_insights_api.md` — dashboard DTO и practical insights.
5. `05_what_if_api.md` — What-if controls, scenario run, scenario result.

## Границы

Эти контракты описывают frontend/backend API, а не внутренние Python service contracts.

То есть здесь фиксируется:

```text
JS UI → QWebChannel → Python backend facade
```

А не:

```text
MetricEngine → DBRepository
```

Внутренние сервисы могут иметь другие интерфейсы, если внешний contract остаётся стабильным.

## Naming rules

- Backend method names: `camelCase`, чтобы их удобно вызывать из JS.
- Python implementation может использовать `snake_case`, но QWebChannel facade должен публиковать `camelCase`.
- DTO fields: `snake_case`, чтобы совпадать с Python/SQLite vocabulary.
- UI labels: отдельные `label`, `title`, `message`.

Пример:

```json
{
  "metric_key": "net_flow",
  "metric_label": "Чистый поток"
}
```

## Contract status labels

| Статус | Значение |
|---|---|
| proposed | предложено, требует ревью |
| accepted | принято в проектировании |
| deferred | отложено |
| deprecated | оставлено только для legacy |

На момент Batch 06 все контракты имеют статус `proposed`.
