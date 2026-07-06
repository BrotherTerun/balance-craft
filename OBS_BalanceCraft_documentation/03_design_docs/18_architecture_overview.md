# 18. Architecture overview

Дата: 2026-07-02  
Статус: рабочий проектировочный документ  
Связанные документы: `02_product_frame.md`, `08_requirements.md`, `09_mvp_scope_timeline.md`, `10_prototype_audit.md`, `13_design_requirements.md`, `16_feature_list.md`, `17_implementation_checklist.md`, `19_data_model_concept.md`, `20_sqlite_schema_design.md`

## 1. Назначение документа

Этот документ описывает архитектуру BalanceCraft 1.5 на уровне системы, контейнеров и ключевых компонентов.

Цель документа — зафиксировать, **как части приложения связаны между собой**, где проходят границы ответственности и какие будущие расширения не должны протечь в MVP.

Документ не заменяет:

- физическую SQLite-схему;
- backend/frontend API-контракты;
- data flow / sequence diagrams;
- UI screen map.

Они будут описаны в отдельных документах.

## 2. Архитектурная цель BalanceCraft 1.5

BalanceCraft 1.5 — локальное desktop-приложение для анализа числового баланса игровых систем по локальным событиям.

Целевая схема:

```text
Пользователь
→ BalanceCraft Desktop
→ импорт локальных JSONL/demo данных
→ локальная SQLite DB
→ профилирование
→ semantic binding
→ metric calculation
→ dashboard / insights / simple What-if
```

Главное архитектурное обещание:

```text
Приложение запускается и показывает пользу без MySQL, внешнего сервера, облака, регистрации и сетевой аналитики.
```

## 3. Архитектурные принципы

### 3.1. Local-first runtime

Runtime-ядро BalanceCraft 1.5 не зависит от внешней СУБД, backend-сервера или облака.

SQLite — часть локального приложения, а не отдельный сервис.

### 3.2. Desktop first, extensions later

В MVP есть только Desktop. Будущие компоненты проектируются как расширения:

- SDK Lite;
- Self-hosted Collector;
- external simulator adapter.

Они не должны диктовать структуру MVP сильнее, чем это нужно для совместимости формата данных.

### 3.3. Universal data model

Ядро архитектуры строится вокруг:

```text
project
entity
observation
event
attribute
parameter
semantic binding
metric template
metric run
metric value
scenario
```

`player`, `session`, `item`, `skill` не являются системными контейнерами или обязательными таблицами. Это только возможная пользовательская семантика.

### 3.4. Late semantic binding

Импорт не пытается автоматически понять смысл событий.

Смысл задаётся позже через Binding Wizard:

```text
template variable
→ event_type filter
→ source path
→ aggregation
→ label
```

### 3.5. Raw events are immutable

Импортированные события не изменяются расчётами, сценариями или правками semantic bindings.

Все производные данные хранятся отдельно:

```text
events
→ metric_runs / metric_values
→ scenarios / scenario_results
```

### 3.6. Human diagnostics over raw exceptions

Backend не должен отдавать UI stack traces как пользовательскую ошибку.

Все публичные ответы идут через структурированный envelope:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": []
}
```

### 3.7. Diagrams are part of architecture

Диаграммы в `docs/diagrams/` считаются частью проектирования, а не декоративным приложением.

Если текст и диаграмма расходятся, это баг документации.

## 4. C4 Context level

См. `diagrams/architecture_context.md`.

Контекстная диаграмма показывает BalanceCraft Desktop как систему между пользователем, локальными файлами, demo project и будущими внешними компонентами.

В MVP активны только:

- пользователь;
- BalanceCraft Desktop;
- локальные JSONL-файлы;
- demo project;
- локальный SQLite-файл.

Будущие компоненты:

- SDK Lite;
- Self-hosted Collector;
- external simulator/game runner.

Они показаны как `future/out of MVP`.

## 5. C4 Container level

См. `diagrams/architecture_container.md`.

Основные контейнеры BalanceCraft Desktop:

| Контейнер | Назначение | Статус |
|---|---|---|
| Desktop App Shell | запускает PySide/QWebEngine, управляет lifecycle | P0 |
| Frontend UI | экраны, wizard, charts, panels | P0 |
| QWebChannel Bridge | связь JS frontend с Python backend | P0 |
| Backend Services | бизнес-логика приложения | P0 |
| SQLite DB | локальное хранилище проекта и производных данных | P0 |
| Local File System | источники JSONL, demo files, локальная БД | P0 |

Контейнеры не означают отдельные процессы. В версии 1.5 BalanceCraft остаётся монолитным desktop-приложением с внутренним разделением слоёв.

## 6. Component level

См. `diagrams/architecture_components.md`.

Backend разделяется на сервисы:

| Компонент | Ответственность |
|---|---|
| `db layer` | connection, migrations, transactions, SQL helpers |
| `project service` | создание/открытие проектов, recent projects, project metadata |
| `settings service` | локальные настройки приложения |
| `import service` | чтение JSONL, validation, import report |
| `data profiler` | карта событий и attributes |
| `analysis coverage service` | проверка доступности классов анализа |
| `binding service` | semantic binding sets и binding rows |
| `metric template registry` | встроенные шаблоны и metadata |
| `metric engine` | расчёт metric runs / metric values |
| `insight engine` | practical insights поверх рассчитанных рядов |
| `what-if engine` | scenarios, overrides, confidence statuses |
| `demo project service` | создание/открытие demo project |
| `API facade` | публичные методы для QWebChannel |

Frontend разделяется по пользовательским зонам:

| Компонент | Ответственность |
|---|---|
| Start / Projects UI | создать/открыть проект, demo, recent |
| Import UI | выбор файлов, прогресс, отчёт импорта |
| Data Map UI | event types, attributes, examples, warnings |
| Binding Wizard UI | настройка semantic bindings |
| Dashboard UI | графики и таблицы метрик |
| Insight Panel UI | practical insights |
| Analysis Coverage UI | что можно/нельзя проверить |
| What-if Panel UI | overrides, scenario run, comparison |
| Settings UI | локальные настройки |

## 7. Runtime architecture

### 7.1. Single-user local application

BalanceCraft 1.5 не проектируется как multi-user сервис.

Следствия:

- нет авторизации;
- нет ролей;
- нет сетевых tenants;
- нет remote project sync;
- file locking нужен только в минимальном виде;
- конфликты одновременного редактирования не являются P0.

### 7.2. One application, one local database file

Базовый вариант:

```text
BalanceCraft Desktop
→ user data directory
→ balancecraft.db
```

Возможное расширение:

```text
project folder
→ project-local SQLite DB
```

Это можно оставить как P1/P2-уточнение. Для MVP важнее единый стабильный путь.

### 7.3. SQLite as internal persistence layer

SQLite — не публичный API. UI и frontend не должны знать SQL.

Правильная зависимость:

```text
Frontend
→ QWebChannel
→ API facade
→ services
→ repositories / db layer
→ SQLite
```

Неправильная зависимость:

```text
Frontend
→ raw SQL
→ SQLite
```

## 8. Boundaries and responsibilities

### 8.1. Frontend boundary

Frontend отвечает за:

- отображение состояния;
- ввод пользователя;
- запуск backend-операций;
- визуализацию графиков;
- показ warnings/errors;
- локальную UI-навигацию.

Frontend не отвечает за:

- SQL;
- расчёт метрик;
- валидацию схемы JSONL как источник истины;
- интерпретацию semantic bindings;
- генерацию insights как источник истины.

### 8.2. Backend boundary

Backend отвечает за:

- бизнес-логику;
- работу с БД;
- импорт и валидацию;
- профилирование;
- metric calculation;
- scenario calculation;
- insight generation;
- стабильные JSON-ответы.

Backend не отвечает за:

- внешний web-сервер;
- cloud sync;
- сбор live-телеметрии;
- SDK runtime в игре.

### 8.3. Database boundary

SQLite хранит:

- project metadata;
- raw events;
- profiles;
- parameters;
- semantic bindings;
- metric runs;
- metric values;
- scenarios;
- scenario results;
- warnings and snapshots.

SQLite не должна хранить:

- пользовательские секреты для внешнего cloud;
- обязательные MySQL-совместимые структуры;
- жанровые таблицы как ядро;
- данные SDK/Collector, если они не импортированы в Desktop.

### 8.4. Demo boundary

Demo project — часть продукта 1.5, потому что без него ценность трудно увидеть с первого запуска.

Demo не является “истинной моделью игры”. Это управляемый synthetic dataset, который демонстрирует P0-пайплайн.

## 9. Dependency direction

Целевое направление зависимостей:

```text
UI components
→ frontend api client
→ QWebChannel bridge
→ backend API facade
→ domain services
→ repositories/db layer
→ SQLite
```

Сервисы могут использовать общие domain-модели и utility-модули.

Запрещённые зависимости:

```text
metric engine → frontend DOM
db layer → frontend state
import service → chart rendering
insight engine → direct SQL outside repositories, если есть repository layer
frontend → raw database path as business state
```

## 10. Main backend services

### 10.1. Project Service

Отвечает за:

- создание проекта;
- открытие проекта;
- обновление metadata;
- recent projects;
- default build id;
- связь с demo project service.

Типовые методы будут описаны в `22_backend_frontend_contracts.md`.

### 10.2. Import Service

Отвечает за:

- поиск JSONL-файлов;
- чтение строк;
- parse JSON;
- validation;
- import run;
- source files;
- events insert;
- entities/observations upsert;
- import report.

### 10.3. Data Profiler

Отвечает за:

- список event types;
- список attribute keys;
- типы значений;
- numeric ranges;
- sample values;
- грязные/mixed поля;
- обновление `event_attribute_profile`.

### 10.4. Analysis Coverage Service

Отвечает за:

- сопоставление текущих данных с проблемами баланса;
- статусы `available`, `partially_available`, `missing_data`, `unsupported_in_version`;
- список недостающих событий/полей/параметров;
- объяснение ограничений анализа.

P0 может считать coverage на лету. P1 может кэшировать результат.

### 10.5. Binding Service

Отвечает за:

- создание binding set;
- сохранение binding rows;
- validation связок;
- подготовку binding snapshot для metric run;
- загрузку binding для повторного расчёта.

### 10.6. Metric Template Registry

Отвечает за:

- встроенные шаблоны;
- переменные шаблона;
- формулы;
- labels;
- thresholds;
- warnings rules;
- version/snapshot данных.

В MVP шаблоны могут жить в коде. БД может хранить metadata/snapshots.

### 10.7. Metric Engine

Отвечает за:

- чтение events по scope;
- агрегацию переменных;
- применение формул;
- `safe_div` / `N/A`;
- calculation warnings;
- запись metric run;
- запись metric values;
- подготовку dashboard dataset.

Metric Engine не должен знать о DOM, Chart.js или конкретной странице UI.

### 10.8. Insight Engine

Отвечает за:

- чтение metric series;
- rule-based анализ;
- practical insights;
- evidence/основание вывода;
- severity;
- рекомендации;
- warnings о недостаточности данных.

### 10.9. What-if Engine

Отвечает за:

- сценарии;
- overrides;
- Level 1 impact estimate;
- limited Level 2 counterfactual recalculation;
- scenario results;
- confidence status;
- comparison datasets.

What-if Engine не должен изменять raw events и historical metric values.

### 10.10. Demo Project Service

Отвечает за:

- создание/открытие demo project;
- загрузку synthetic demo logs;
- преднастройку semantic bindings;
- запуск демонстрационного metric run;
- reset demo project, если понадобится.

## 11. Frontend application areas

### 11.1. Start screen

Первый экран:

- открыть demo;
- создать проект;
- открыть проект;
- recent projects;
- короткое объяснение продукта.

### 11.2. Project dashboard

Центр проекта:

- последний импорт;
- состояние data profile;
- состояние bindings;
- последние metric runs;
- доступные next steps.

### 11.3. Import UI

Функции:

- выбрать файл/папку;
- показать найденные файлы;
- показать progress/status;
- показать import report;
- перейти к data map.

### 11.4. Data Map UI

Функции:

- event types;
- attributes;
- counts;
- sample values;
- warnings;
- переход к Binding Wizard.

### 11.5. Binding Wizard UI

Функции:

- выбрать template;
- выбрать event filters;
- связать variables;
- выбрать aggregation;
- задать labels;
- сохранить binding set.

### 11.6. Dashboard UI

Функции:

- выбрать metric run;
- выбрать scope;
- увидеть charts;
- увидеть metric table;
- увидеть warnings.

### 11.7. Insight Panel UI

Функции:

- список insights;
- severity;
- recommendation;
- evidence;
- links to metrics/windows.

### 11.8. Analysis Coverage UI

Функции:

- показать, какие классы проблем доступны;
- показать, какие не проверяются;
- объяснить missing signals;
- предложить, какие события логировать в будущем.

### 11.9. What-if Panel UI

Функции:

- выбрать scenario или создать новый;
- выбрать parameter;
- задать override;
- запустить scenario;
- увидеть historical vs scenario;
- увидеть confidence status.

## 12. Future extension points

### 12.1. SDK Lite

Будущий компонент, который пишет события в JSONL или отправляет их на Self-hosted Collector.

Для архитектуры Desktop важно только:

```text
SDK output JSONL
→ должен импортироваться через существующий Import Service
```

SDK не должен становиться runtime dependency Desktop 1.5.

### 12.2. Self-hosted Collector

Будущий сервер разработчика игры.

Для архитектуры Desktop важно только:

```text
Collector export JSONL
→ должен импортироваться как обычный источник
```

Desktop не зависит от Collector.

### 12.3. External simulation adapter

Будущий уровень What-if.

Для MVP не проектируется как активный компонент. Архитектура должна только не закрыть возможность:

```text
scenario config
→ external runner
→ generated events
→ import as new source/scenario run
```

## 13. Legacy boundaries

Старый прототип может дать полезные элементы:

- PySide6/QWebEngine shell;
- QWebChannel pattern;
- Chart.js UI;
- Binding Wizard UX;
- practical insights structure;
- what-if UI idea.

Но legacy не должен протечь в новое ядро как:

```text
mysql.connector
DB_CONFIG root password
monitor_rpg_model
INFORMATION_SCHEMA
players as required table
sessions as required table
items/skills as required core tables
player selector as main scope model
```

## 14. Architecture quality checks

Перед переходом к реализации архитектура считается согласованной, если выполняется:

- Desktop запускается без внешней СУБД.
- Все P0-пути проходят через SQLite.
- Frontend не знает SQL.
- Raw events не изменяются расчётами.
- Метрики создаются через `metric_runs`.
- What-if создаёт `scenario_results`, а не переписывает историю.
- `player/session/item/skill` не являются core architecture containers.
- SDK/Collector не являются P0-зависимостями.
- API возвращает structured envelope.
- Все диаграммы соответствуют тексту.

## 15. Review notes

Эти вопросы не блокируют батч, но их стоит рассмотреть одним общим ревью-проходом.

### RN-18-01. Где хранить SQLite-файл

Варианты:

1. единый `balancecraft.db` в пользовательской папке приложения;
2. отдельный `.db` рядом с каждым проектом;
3. гибрид: app DB + project DB.

Для MVP проще единый DB. Для переносимых проектов лучше project-local DB. Решение можно принять перед реализацией `db layer`.

### RN-18-02. Нужен ли repository layer поверх db layer

Для MVP можно писать SQL внутри сервисов через общий db helper. Для более чистой архитектуры лучше repositories.

Компромисс:

```text
db.py для connection/transactions
repositories/*.py для сложных таблиц
services/*.py для бизнес-логики
```

### RN-18-03. Где хранить встроенные metric templates

Варианты:

1. только в коде;
2. seed в `metric_templates`;
3. оба: source of truth в коде + snapshot в DB.

Предварительно лучше третий вариант: шаблоны в коде, snapshots в `metric_runs`.

### RN-18-04. Насколько What-if P0

Архитектурно What-if включён как extension point и ограниченный P0/P1-компонент. Если сроки горят, UI и storage можно оставить, но полноценный пересчёт сценариев резать после baseline dashboard.

### RN-18-05. Нужно ли делать Analysis Coverage отдельным экраном

Для MVP coverage может быть панелью в Dashboard/Data Map, а не отдельным экраном. Архитектурно это отдельный backend service, UI-формат решается позже.
