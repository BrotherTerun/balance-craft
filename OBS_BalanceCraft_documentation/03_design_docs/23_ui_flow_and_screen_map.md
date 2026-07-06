# FILE: `docs/23_ui_flow_and_screen_map.md`

# 23. UI flow и карта экранов BalanceCraft Desktop

Дата: 2026-07-02  
Статус: проектный черновик для ревью

## Назначение

Этот документ фиксирует пользовательскую структуру BalanceCraft Desktop 1.5.

Он не является финальным визуальным дизайном, UI kit или набором пиксельных макетов. Его задача — определить:

- какие экраны и панели нужны;
- как пользователь проходит основной сценарий;
- какие данные нужны каждому экрану;
- какие действия пользователь может выполнить;
- какие empty, warning и error states должны быть предусмотрены;
- где UI вызывает backend-контракты.

Главный критерий: по этому документу можно реализовывать интерфейс без повторного обсуждения базового маршрута.

## Базовая UX-цель

Пользователь должен увидеть пользу до того, как столкнётся с полной сложностью системы.

Целевой первый путь:

```text
launch app
→ open demo project
→ see ready dashboard
→ inspect data map
→ inspect semantic bindings
→ run one metric calculation
→ open insights
→ try one simple What-if
```

Для пользовательского проекта:

```text
launch app
→ create/open project
→ import JSONL
→ see import report
→ inspect data map
→ configure semantic binding
→ run metric calculation
→ see dashboard and insights
→ optionally run What-if
```

## Общая карта экранов

См. также: `docs/diagrams/ui_flow.md`.

```text
Start / Project Hub
├─ Open Demo Project
│  └─ Project Dashboard
├─ Create Project
│  └─ Import Data
├─ Open Existing Project
│  └─ Project Dashboard
└─ Recent Projects
   └─ Project Dashboard

Project Dashboard
├─ Import Data
├─ Data Map
├─ Analysis Coverage
├─ Binding Wizard
├─ Metric Dashboard
├─ Insights Panel
├─ What-if Panel
└─ Project Settings
```

## Навигационный принцип

Для MVP не нужен сложный многооконный интерфейс. Достаточно одного desktop shell с главным рабочим пространством и панельной навигацией.

Рекомендуемая структура:

```text
Top bar:
  project name
  current build/filter status
  import status
  run status

Left navigation:
  Overview
  Import
  Data Map
  Bindings
  Metrics
  Insights
  What-if
  Settings

Main content:
  активный экран или панель

Right/Bottom auxiliary panel:
  warnings
  selected entity/metric details
  current review notes
```

Если UI уже технически устроен иначе, это не критично. Важнее сохранить пользовательский маршрут и доступность действий.

## Экран 1. Start / Project Hub

### Назначение

Точка входа в приложение.

### Основные действия

- открыть demo project;
- создать новый project;
- открыть existing project;
- открыть recent project;
- перейти к документации/quick start;
- увидеть статус local-only.

### Данные экрана

- recent projects;
- last opened timestamp;
- project path / db path;
- short project status;
- app version.

### Backend methods

- `listRecentProjects`
- `createProject`
- `openProject`
- `openDemoProject`
- `removeRecentProject`

### Empty state

Если recent projects нет:

```text
Пока нет проектов.
Откройте демо-проект, чтобы увидеть BalanceCraft в работе,
или создайте новый проект и импортируйте JSONL-события.
```

### Error states

| Ситуация | Сообщение |
|---|---|
| project file/database missing | Проект не найден. Возможно, файл был перемещён или удалён. |
| incompatible schema | Версия базы проекта несовместима с текущей версией BalanceCraft. |
| db open error | Не удалось открыть локальную базу проекта. Проверьте доступ к файлу. |

### MVP notes

Demo project должен быть доступен прямо отсюда. Если пользователь не может за 10 секунд открыть готовый пример, ценность продукта хуже считывается.

## Экран 2. Project Dashboard / Overview

### Назначение

Главный экран проекта. Показывает состояние проекта и следующий рекомендуемый шаг.

### Основные блоки

- project summary;
- import status;
- data profile summary;
- configured bindings;
- last metric run;
- available analysis coverage;
- quick actions.

### Quick actions

```text
Import data
Open data map
Configure binding
Run metric calculation
Open dashboard
Try What-if
```

### Данные экрана

- project metadata;
- last import run;
- count of events/entities/observations;
- available event types;
- configured templates;
- last metric run status;
- warnings summary.

### Backend methods

- `getProjectOverview`
- `getImportRuns`
- `getDataProfileSummary`
- `getAnalysisCoverage`
- `listBindingSets`
- `listMetricRuns`

### Empty states

| Ситуация | UI |
|---|---|
| project created, no events | Показать CTA “Import JSONL” |
| events imported, no bindings | Показать CTA “Configure semantic binding” |
| bindings exist, no metric runs | Показать CTA “Run calculation” |
| metric runs exist | Показать last run + dashboard link |

### MVP notes

Overview не должен быть тяжёлым dashboard. Это навигационная панель состояния проекта.

## Экран 3. Import Data

### Назначение

Выбор локальных JSONL-файлов, запуск импорта и просмотр отчёта.

### Основные действия

- выбрать файл или папку;
- просмотреть найденные `.jsonl`;
- запустить импорт;
- отменить импорт, если это технически поддержано;
- открыть import report;
- перейти к data map.

### Данные экрана

- selected source path;
- found files;
- import status;
- read lines;
- valid events;
- invalid events;
- imported events;
- created entities;
- created observations;
- warnings;
- errors grouped by file and line.

### Backend methods

- `scanImportSource`
- `importEvents`
- `getImportRun`
- `listImportRuns`

### States

| State | UI |
|---|---|
| idle | source picker + instructions |
| scanning | progress indicator |
| ready | list of files and estimated import |
| importing | progress by file/line if available |
| finished | report summary |
| finished with warnings | report + warning panel |
| failed | human-readable error + retry |

### Warnings

- unknown schema version;
- missing `observation_id`;
- no numeric attributes;
- mixed attribute types;
- no blocking events;
- no reward events;
- no parameter data.

### MVP notes

Импорт не должен требовать от пользователя знания схемы БД. Ошибки должны быть человеческими, а не stack trace.

## Экран 4. Import Report

### Назначение

Показать результат конкретного import run.

Может быть отдельным экраном или секцией внутри Import Data.

### Основные блоки

- summary cards;
- files table;
- invalid lines preview;
- warnings;
- next recommended action.

### Summary cards

```text
Files read
Lines read
Valid events
Invalid events
Imported events
Created entities
Created observations
```

### Next action

После успешного импорта:

```text
Open Data Map
```

После импорта с предупреждениями:

```text
Open Data Map anyway
Review warnings
```

После failed import:

```text
Fix source file
Retry import
```

## Экран 5. Data Map

### Назначение

Показать структуру импортированных событий без открытия raw JSON.

### Основные действия

- посмотреть event types;
- выбрать event type;
- посмотреть attributes;
- увидеть типы, частоты, примеры, диапазоны;
- понять, какие поля можно использовать в Binding Wizard;
- перейти к Analysis Coverage;
- перейти к Binding Wizard.

### Данные экрана

- event types and counts;
- attribute profiles;
- numeric/string/boolean/null counts;
- min/max for numeric fields;
- sample values;
- mixed type warnings;
- schema version distribution;
- build_id distribution.

### Backend methods

- `getDataProfile`
- `getEventTypes`
- `getAttributeProfile`
- `getAnalysisCoverage`

### UI structure

```text
Left: event_type list
Main: attributes table for selected event_type
Right: samples/warnings/next steps
```

### Attribute table columns

```text
attribute_key
detected_types
count
numeric_count
null_count
min
max
sample_values
usable_for_templates
warnings
```

### Empty states

| Ситуация | UI |
|---|---|
| no events | предложить Import Data |
| no numeric fields | объяснить ограниченность metric templates |
| selected event type has no attributes | показать raw event metadata only |
| profile not built | предложить rebuild profile |

## Экран 6. Analysis Coverage

### Назначение

Показать, какие классы проблем можно анализировать по текущим данным и bindings.

Может быть отдельной панелью или секцией внутри Data Map / Overview.

### Основные действия

- посмотреть available / partially available / missing / unsupported;
- открыть объяснение missing signals;
- перейти к Binding Wizard для настройки;
- перейти к Import для добавления данных.

### Данные экрана

- problem key;
- problem label;
- status;
- required signals;
- available signals;
- missing signals;
- related templates;
- version support.

### Backend methods

- `getAnalysisCoverage`

### Status labels

| Technical | UI |
|---|---|
| `available` | Можно анализировать |
| `partially_available` | Частично доступно |
| `missing_data` | Не хватает данных |
| `unsupported_in_version` | Не поддерживается в текущей версии |

### MVP notes

Coverage не должен блокировать анализ. Это диагностическая панель честности, а не gatekeeper.

## Экран 7. Binding Wizard

### Назначение

Связать переменные шаблона анализа с конкретными event types, attributes, filters и aggregations.

### Wizard steps

```text
1. Choose template
2. Review required variables
3. Map variables to data sources
4. Configure filters and aggregation
5. Review formulas and warnings
6. Save binding set
```

### Step 1. Choose template

Показывает:

- P0 templates;
- short description;
- required variables;
- supported problems.

P0:

```text
Flow Balance
Stock Dynamics
Conversion Efficiency
Operation Intensity
```

### Step 2. Review variables

Для каждого template:

```text
variable_key
variable_label
required/optional
expected type
description
```

### Step 3. Map variables

Пользователь выбирает:

- source kind: `event_attribute`, `event_field`, `parameter`, `constant`;
- event type filter;
- source path, например `attributes.amount`;
- aggregation;
- optional filters.

### Step 4. Filters and aggregation

Примеры:

```text
event_type = resource_gained
attributes.resource_type = gold
aggregation = sum
group_by = observation_id
```

### Step 5. Review formulas

Показывает:

- какие метрики будут рассчитаны;
- какие формулы используются;
- где возможны `N/A`;
- какие warning rules активны.

### Step 6. Save

Сохраняет binding set.

### Backend methods

- `listMetricTemplates`
- `getMetricTemplate`
- `validateBindingDraft`
- `saveBindingSet`
- `getBindingSet`
- `listBindingSets`

### Empty/error states

| Ситуация | UI |
|---|---|
| no templates | internal error / templates unavailable |
| no data profile | предложить импортировать данные |
| missing required variable | нельзя сохранить binding |
| incompatible type | warning или blocking validation |
| no matching events | warning: metric may return N/A |

### MVP notes

Binding Wizard — центральная фича. Его нельзя превращать в spreadsheet hell. Лучше меньше опций, но понятный happy path.

## Экран 8. Metric Dashboard

### Назначение

Показать рассчитанные metric values в виде графиков, таблиц и summary cards.

### Основные действия

- выбрать binding set/template;
- запустить metric run;
- выбрать metric run;
- выбрать scope;
- посмотреть графики;
- открыть insight details;
- перейти к What-if.

### Данные экрана

- metric runs;
- selected run metadata;
- chart labels;
- datasets;
- metric statuses;
- warnings;
- scope options;
- insights.

### Backend methods

- `runMetricCalculation`
- `getMetricRun`
- `listMetricRuns`
- `getDashboardData`
- `getInsights`

### UI structure

```text
Top:
  template/run/scope selectors

Main:
  chart area

Bottom/Right:
  metric cards
  warnings
  insights preview
```

### Scope selector

Минимум:

```text
whole_project
entity_id
observation_id
observation_type
event_type
build_id
```

### Chart requirements

- поддержка нескольких datasets;
- показывать `N/A`, а не скрывать молча;
- warning badges на проблемных точках;
- readable labels;
- no raw Python/SQL errors.

### Empty states

| Ситуация | UI |
|---|---|
| no bindings | предложить Binding Wizard |
| no metric runs | CTA “Run calculation” |
| metric run failed | show error + logs/warnings |
| no data for selected scope | explain scope has no matching data |

## Экран 9. Insights Panel

### Назначение

Показать практические выводы поверх рассчитанных метрик.

Может быть отдельным экраном или панелью dashboard.

### Insight card fields

```text
severity
category
title
summary
recommendation
evidence
related_metric_keys
related_scope
confidence/limitations
```

### Backend methods

- `getInsights`
- optionally `getInsightDetails`

### UI labels

В русском UI:

```text
evidence → основание вывода
```

Не использовать слово “доказательство”, чтобы не обещать причинность.

### States

| State | UI |
|---|---|
| no insights | Нет явных проблем по текущим данным |
| warnings only | Показать ограничения расчёта |
| insights generated | cards by severity/category |
| insufficient data | объяснить, чего не хватает |

### MVP notes

Insight должен отвечать на вопрос: “на что дизайнеру посмотреть?”. Не нужно превращать его в магического аналитика, который “понял игру”.

## Экран 10. What-if Panel

### Назначение

Проверить простой параметрический сценарий без изменения исторических данных.

### Основные действия

- выбрать base metric run;
- выбрать parameter;
- задать override;
- запустить scenario;
- увидеть historical vs scenario line;
- увидеть delta;
- увидеть confidence status;
- сохранить/сбросить scenario.

### Данные экрана

- available parameters;
- selected parameter metadata;
- original value;
- override mode;
- scenario value;
- affected metrics;
- scenario results;
- confidence status;
- warnings.

### Backend methods

- `listScenarioParameters`
- `createScenario`
- `runScenario`
- `getScenarioResult`
- `listScenarios`

### Override modes

```text
set
delta
multiplier
```

### Confidence statuses

```text
exact_recalc
approx_recalc
impact_estimate
insufficient_model
insufficient_data
```

### UI warning

What-if panel должен явно показывать:

```text
Сценарий не изменяет исторические события.
Результат показывает пересчёт доступного слоя, а не полную симуляцию поведения игрока.
```

### Empty states

| Ситуация | UI |
|---|---|
| no metric run | сначала рассчитать метрики |
| no parameters | импортировать/создать параметры или использовать демо |
| no dependency rule | показать impact estimate или insufficient model |
| scenario failed | показать readable error |

## Экран 11. Project Settings

### Назначение

Настройки проекта, не связанные с raw event editing.

### Основные блоки

- project name;
- default build_id;
- local db path;
- import preferences;
- UI preferences;
- feature flags if needed;
- data safety info.

### Backend methods

- `getProjectSettings`
- `updateProjectSettings`

### MVP notes

Не делать Settings слишком большим. Всё, что не нужно для vertical slice, можно отложить.

## Экран 12. Demo Mode / Demo Project

### Назначение

Показать BalanceCraft без внешних файлов.

Demo project должен быть полноценным проектом с событиями, параметрами, bindings, metric runs и готовыми dashboard states.

### Основные действия

- открыть готовый dashboard;
- посмотреть data map;
- открыть binding wizard в read/edit mode;
- запустить metric run повторно;
- запустить prepared What-if;
- прочитать demo explanation.

### Связанный документ

Подробно: `docs/24_demo_project_spec.md`.

## Global UI states

## Loading

Показывать для:

- project open;
- import;
- profiling;
- metric calculation;
- scenario run.

Минимум:

```text
operation name
progress if available
current step
safe cancel only if implemented
```

## Warning panel

Единая логика warnings:

```text
data_quality
calculation
coverage
scenario
performance
compatibility
```

Warning не равен error. Пользователь должен понимать, можно ли продолжить.

## Error panel

Error должен содержать:

```text
human_message
technical_code
details optional
suggested_action
```

Stack trace не показывать как основной текст.

## Empty states

Empty state всегда должен отвечать:

```text
что произошло
почему это нормально/проблема
что делать дальше
```

## Первый demo walkthrough

Целевой маршрут для README/GIF:

```text
1. Launch app.
2. Click Open Demo Project.
3. See dashboard with resource flow chart.
4. Open Data Map and inspect `resource_gained/resource_spent`.
5. Open Binding Wizard and see how `flow_in/flow_out` are mapped.
6. Run Metric Calculation.
7. Read insight about resource surplus or bottleneck.
8. Open What-if.
9. Reduce reward or increase sink by 20%.
10. See scenario line and confidence status.
```

## MVP screen priority

| Screen / panel | Priority |
|---|---|
| Start / Project Hub | P0 |
| Demo Project | P0 |
| Project Dashboard / Overview | P0 |
| Import Data | P0 |
| Import Report | P0 |
| Data Map | P0 |
| Analysis Coverage basic | P0 |
| Binding Wizard | P0 |
| Metric Dashboard | P0 |
| Insights Panel | P0 |
| What-if Panel | P0/P1 |
| Project Settings | P1 |
| Advanced dashboard customization | P2 |
| Formula editor | P2 |
| Collector/SDK screens | P3 |

## Что не проектируем в UI 1.5

- аккаунты;
- облачная авторизация;
- team sharing;
- live ingestion dashboard;
- full BI dashboard builder;
- visual economy model editor;
- custom formula editor;
- Collector admin UI;
- SDK configuration UI.

## Review notes

Эти вопросы не блокируют текущий батч, но их нужно рассмотреть при финальном ревью:

1. Делать ли `Analysis Coverage` отдельным экраном или секцией Data Map/Overview.
2. Делать ли `Insights` отдельным экраном или правой панелью Metric Dashboard.
3. Нужен ли отдельный `Import Report`, или достаточно состояния внутри Import Data.
4. Должен ли Demo Project открываться как read-only или как обычный проект, который можно портить.
5. Насколько рано нужно показывать What-if, если параметры ещё не импортированы.
6. Как визуально показать `N/A` точки на графике без перегруза.
7. Нужен ли отдельный экран `Templates`, или шаблоны живут только внутри Binding Wizard.
