# FILE: `docs/diagrams/00_diagrams_index.md`

# 00. Diagrams index

Дата: 2026-07-02  
Статус: рабочий индекс диаграмм для Obsidian

## Назначение

Этот файл — быстрый навигатор по визуальным артефактам проектирования BalanceCraft.

Идея простая:

```text
текстовые документы объясняют решения;
диаграммы позволяют быстро увидеть архитектуру, модель данных, потоки и миграцию.
```

Диаграммы хранятся как Markdown + Mermaid, чтобы их можно было смотреть и править прямо в Obsidian.

## Быстрый вход

| Нужно понять | Открыть |
|---|---|
| Общая модель данных | `conceptual_data_model.md` |
| Физическая SQLite ERD | `sqlite_erd.md` |
| Архитектура системы | `architecture_context.md`, `architecture_container.md`, `architecture_components.md` |
| Потоки данных | `core_data_flows.md` |
| Последовательности вызовов | `sequence_import.md`, `sequence_metric_run.md`, `sequence_what_if.md` |
| UI-навигация | `ui_flow.md` |
| Миграция от прототипа | `migration_overview.md` |

## Диаграммы модели данных

### `conceptual_data_model.md`

Связанный документ: `../19_data_model_concept.md`

Содержит:

- quick model map;
- conceptual ER view;
- P0 vertical slice view;
- What-if conceptual view;
- legacy mapping view.

Использовать, когда нужно понять:

```text
какие сущности существуют в мире BalanceCraft;
как Project связан с Entity, Observation, Event, Metric, Binding и Scenario;
почему Player/Session больше не ядро.
```

### `sqlite_erd.md`

Связанный документ: `../20_sqlite_schema_design.md`

Содержит:

- карту групп таблиц;
- P0 physical ERD;
- Parameters + What-if ERD;
- P1 extension ERD;
- import/profiling slice;
- metric calculation slice;
- What-if slice;
- legacy mapping reminder.

Использовать, когда нужно понять:

```text
какие таблицы есть в SQLite;
где PK/FK;
как events связаны с import_runs/source_files;
как metric_runs порождают metric_values;
как scenarios и scenario_results не меняют history.
```

## Архитектурные диаграммы

### `architecture_context.md`

Связанный документ: `../18_architecture_overview.md`

Содержит:

- system context BalanceCraft Desktop 1.5;
- local-only окружение;
- future extension points;
- MVP boundary.

Использовать, когда нужно объяснить:

```text
где BalanceCraft находится относительно пользователя, локальных JSONL, SQLite, SDK Lite и Collector;
почему SDK/Collector не входят в MVP;
почему Cloud отсутствует.
```

### `architecture_container.md`

Связанный документ: `../18_architecture_overview.md`

Содержит:

- Desktop Shell;
- Frontend UI;
- QWebChannel bridge;
- Backend API Facade;
- Backend Services;
- DB Layer;
- SQLite;
- Local Files.

Использовать, когда нужно понять:

```text
из каких крупных частей состоит приложение;
где проходит граница frontend/backend;
почему UI не должен ходить в БД напрямую.
```

### `architecture_components.md`

Связанный документ: `../18_architecture_overview.md`

Содержит:

- backend component map;
- frontend component map;
- service boundaries;
- legacy migration view.

Использовать, когда нужно понять:

```text
какой service за что отвечает;
куда относятся import, profiling, coverage, binding, metrics, insights и What-if;
какие legacy-модули можно адаптировать.
```

## Потоки данных

### `core_data_flows.md`

Связанный документ: `../21_data_flows.md`

Содержит:

- full vertical slice;
- import flow;
- data profile flow;
- analysis coverage flow;
- binding flow;
- metric/dashboard flow;
- insight flow;
- What-if flow;
- error/warning flow.

Использовать, когда нужно понять:

```text
как сырые JSONL становятся графиком и insight;
какие промежуточные данные создаются;
где появляются warnings/errors.
```

## Sequence diagrams

### `sequence_import.md`

Связанный документ: `../21_data_flows.md`

Содержит sequence diagram для:

```text
Frontend → Backend API → Import Service → DB Layer → SQLite → Data Profiler → UI
```

Использовать, когда нужно уточнить:

```text
кто создаёт import_run;
кто пишет source_files;
кто валидирует JSONL;
кто запускает profiling;
какой response получает UI.
```

### `sequence_metric_run.md`

Связанный документ: `../21_data_flows.md`

Содержит sequence diagram для:

```text
runMetricCalculation → Binding Service → Metric Engine → DB Layer → Dashboard DTO → Insight Engine
```

Использовать, когда нужно уточнить:

```text
где берётся binding snapshot;
где создаётся metric_run;
когда считаются metric_values;
кто готовит dashboard dataset;
кто создаёт insights.
```

### `sequence_what_if.md`

Связанный документ: `../21_data_flows.md`

Содержит sequence diagram для:

```text
What-if panel → Scenario Service → What-if Engine → Parameter Service → Metric Engine → Scenario Results
```

Использовать, когда нужно уточнить:

```text
как scenario override превращается в scenario result;
где определяется confidence_status;
почему raw events и historical metric values не меняются.
```

## UI diagram

### `ui_flow.md`

Связанные документы:

- `../23_ui_flow_and_screen_map.md`
- `../24_demo_project_spec.md`

Содержит:

- main UI flow;
- first launch demo walkthrough;
- user project happy path;
- screen state progression;
- navigation grouping;
- demo project internal flow;
- UI ↔ backend contract map;
- MVP vs future UI boundary.

Использовать, когда нужно понять:

```text
какие экраны есть в MVP;
как пользователь идёт от первого запуска к графику;
как demo project показывает ценность;
что спрятано в future UI.
```

## Migration diagram

### `migration_overview.md`

Связанный документ:

- `../10_prototype_audit.md`
- `../25_test_plan.md`

Содержит:

- high-level migration map;
- data model migration;
- module migration map;
- runtime dependency cleanup;
- vertical slice migration order;
- delete/adapt/postpone view;
- legacy terminology migration.

Использовать, когда нужно понять:

```text
что забираем из старого прототипа;
что удаляем;
что обобщаем;
как MySQL/RPG модель превращается в SQLite/universal model;
какой порядок рефакторинга безопаснее.
```

## Рекомендуемый порядок просмотра всех диаграмм

Для первого полного ревью:

```text
1. architecture_context.md
2. architecture_container.md
3. architecture_components.md
4. conceptual_data_model.md
5. sqlite_erd.md
6. core_data_flows.md
7. sequence_import.md
8. sequence_metric_run.md
9. sequence_what_if.md
10. ui_flow.md
11. migration_overview.md
```

Почему так:

```text
сначала система в целом;
потом внутренние компоненты;
потом данные;
потом движение данных;
потом UX;
потом миграция от старого прототипа.
```

## Mermaid troubleshooting для Obsidian

Если диаграмма не рендерится:

1. Проверить, включён ли Mermaid в Obsidian.
2. Проверить, что блок начинается с:

```text
```mermaid
```

3. Проверить, что в labels нет проблемных символов вроде необработанных кавычек.
4. Если ломается `erDiagram`, временно заменить сложный label на более простой.
5. Если ломается `sequenceDiagram`, проверить `participant` и стрелки `->>` / `-->>`.
6. Если ломается `flowchart`, проверить subgraph ids и закрытие `end`.

## Consistency checklist

Перед финальным утверждением проектировочного пакета:

```text
[ ] Все диаграммы рендерятся в Obsidian.
[ ] В core/runtime-диаграммах используется SQLite; MySQL появляется только как legacy/forbidden/deprecated boundary в migration diagrams.
[ ] Ядро везде называется Entity / Observation / Event.
[ ] Player / Session / Item / Skill не показаны как обязательные core tables.
[ ] MetricRun / MetricValue названы одинаково в conceptual и SQLite diagrams.
[ ] SemanticBinding / BindingSet согласованы с contract docs.
[ ] Scenario / ScenarioOverride / ScenarioResult согласованы с What-if docs.
[ ] SDK Lite и Self-hosted Collector показаны как future extensions.
[ ] Cloud не появляется как часть MVP.
[ ] UI flow совпадает с backend/frontend contracts.
[ ] Migration diagram совпадает с prototype audit.
```

## Возможная структура в репозитории

```text
docs/
  diagrams/
    00_diagrams_index.md
    architecture_context.md
    architecture_container.md
    architecture_components.md
    conceptual_data_model.md
    sqlite_erd.md
    core_data_flows.md
    sequence_import.md
    sequence_metric_run.md
    sequence_what_if.md
    ui_flow.md
    migration_overview.md
```

## Примечание по экспорту

Mermaid-диаграммы можно держать как исходники. Если позже понадобятся картинки для README/GitHub/портфолио, можно экспортировать их в PNG/SVG, но исходником всё равно должен оставаться Markdown/Mermaid.
