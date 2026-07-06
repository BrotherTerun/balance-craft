# 10. Поверхностный аудит текущего прототипа

## Цель аудита

Этот документ не является полным code review. Его задача — быстро разделить текущий код на:

- оставить;
- переработать;
- удалить;
- использовать только как legacy/demo.

## Что прототип уже доказывает

Текущий прототип показывает, что базовый цикл продукта реален:

```text
импорт событий
→ хранение
→ расчёт метрик
→ визуализация
→ практические выводы
→ What-if
```

Также уже есть:

- desktop shell на PySide6 + QWebEngine;
- frontend на HTML/CSS/JS;
- Chart.js графики;
- Binding Wizard;
- панель practical insights;
- модуль stability analysis;
- what-if panel;
- управление проектами через локальный файл.

## Главная проблема прототипа

Код всё ещё завязан на старую учебную модель:

```text
players
sessions
events
items
skills
session_metrics
MySQL
monitor_rpg_model
```

Для BalanceCraft 1.5 это не ядро, а legacy-слой. Новое ядро строится вокруг:

```text
projects
entities
observations
events
entity_parameters
semantic_bindings
metric_templates
metric_runs
metric_values
scenarios
```

## Что оставить

### UI-shell

Оставить направление:

- PySide6;
- QWebEngine;
- QWebChannel;
- HTML/CSS/JS frontend.

Причина: это уже работает как desktop-приложение и подходит для портфолио-демо.

### Project screen

Оставить концепцию:

- создать проект;
- открыть проект;
- последние проекты.

Переработать хранение проектов: уйти от JSON-файла как единственного источника состояния в сторону SQLite.

### Source import modal

Оставить UX-идею выбора папки с событиями.

Переработать backend на новую модель и SQLite.

### Binding Wizard

Оставить как ключевую продуктовую фичу.

Переработать:

- убрать жанровые таблицы из кандидатов;
- перейти на карту событий и параметров;
- заменить “игроки/сессии” на entities/observations;
- добавить явный выбор aggregation и scope.

### Chart dashboard

Оставить Chart.js и идею нескольких линий метрик.

Переработать:

- ось X должна поддерживать observation order/time;
- selector “Игрок” заменить на universal scope selector;
- scenario lines должны ссылаться на scenario_run.

### Practical insights

Оставить почти полностью как отдельный слой интерпретации.

Причина: модуль уже принимает подготовленные ряды и отдаёт структурированные выводы:

```text
level
category
title
text
recommendation
metric_keys
evidence   // technical field; в UI: “основание вывода”
```

Нужно только отвязать тексты от старых метрик и расширить под универсальные шаблоны.

### Stability analysis

Оставить как P1/P2.

Модуль в целом независим от БД и работает с матрицей рядов. Он полезен, но не должен блокировать MVP.

## Что переработать

### `main.py`

Проблемы:

- `mysql.connector`;
- `DB_CONFIG` с root-паролем;
- фиксированная база `monitor_rpg_model`;
- candidates через `INFORMATION_SCHEMA`;
- `BINDING_TABLES` с `players`, `sessions`, `items`, `skills`;
- старый project state в JSON.

Что сделать:

- вынести DB-доступ в `backend/db.py`;
- использовать SQLite connection;
- заменить candidates на data profiling из новой БД;
- заменить player selector на scope selector;
- хранить проекты и настройки в SQLite.

### `pipeline.py`

Проблемы:

- MySQL connection;
- `REQUIRED_TABLES = players/sessions/events/session_metrics`;
- metadata через `INFORMATION_SCHEMA`;
- автоматическое создание игрока и сессии;
- события пишутся в старую модель.

Что сделать:

- валидатор JSONL оставить;
- `timestamp/entity_id/event_type/attributes` оставить;
- добавить `observation_id`, `observation_type`, `build_id`, `schema_version`;
- писать в `events`, `entities`, `observations`, `import_runs`, `source_files`;
- не создавать “игроков” как обязательный тип.

### `db_init.py`

Проблемы:

- MySQL init;
- `CREATE DATABASE`;
- SQL scripts старого формата;
- seed-данные под RPG.

Что сделать:

- заменить на SQLite schema initialization;
- добавить `schema_migrations`;
- создать `backend/schema_sqlite.sql`;
- seed делать только для demo project, а не как ядро.

### `progression_model.py`

Проблемы:

- MySQL;
- загрузка `session_metrics` через `sessions.player_id`;
- `ALL_PLAYERS_ID` как специальный режим;
- шаблоны всё ещё частично старые.

Что сделать:

- переименовать или разделить на `metric_engine.py`;
- работать с `metric_runs` и `metric_values`;
- принимать scope/filter;
- вернуть datasets для Chart.js;
- сохранить integration с practical insights.

### `what_if_analysis.py`

Проблемы:

- MySQL;
- `items/skills/players/sessions` как источники параметров;
- `INFORMATION_SCHEMA`;
- сценарии строятся вокруг table_field/event_signal/computed_signal;
- часть прогнозов опирается на производные потоки.

Что сделать:

- перевести на `entity_parameters`;
- ввести `scenario`, `scenario_overrides`, `scenario_results`;
- различать уровни What-if;
- показывать confidence_status;
- не обещать simulation без dependency rules.

### `app.js`

Оставить:

- project flow;
- Binding Wizard flow;
- chart updates;
- insights rendering;
- what-if panel.

Переработать:

- player dropdown;
- тексты RPG-метрик;
- states вокруг currentProject;
- сценарные controls под параметры сущностей;
- сообщения об ошибках MySQL заменить на локальное хранилище/SQLite.

## Что удалить

- MySQL как runtime dependency.
- Root password в коде.
- `monitor_rpg_model` как фиксированная база.
- `INFORMATION_SCHEMA`.
- Автозапуск MySQL.
- Обязательные `players/items/skills` как фундамент.
- UI-тексты, где BalanceCraft выглядит как RPG progression analyzer.

## Что оставить как legacy/demo

- Старые шаблоны прогрессии — только после переименования и обобщения.
- Старые метрики `EV/PGR/DR` — как совместимость или demo, не как ядро.
- Demo RPG/survival/strategy scenarios — как примеры входных данных.
- `players/sessions` — только как пользовательская семантика demo-проекта.

## Минимальная карта миграции файлов

| Файл | Действие |
|---|---|
| `main.py` | удалить MySQL, подключить SQLite/db layer, обновить backend API |
| `pipeline.py` | переписать импорт в новую модель |
| `db_init.py` | заменить на SQLite init |
| `progression_model.py` | превратить в универсальный metric engine |
| `what_if_analysis.py` | перевести на entity parameters и scenario model |
| `practical_insights.py` | сохранить, обновить тексты и шаблоны |
| `stability_analysis.py` | сохранить как независимый модуль |
| `app.js` | заменить player/session UX на scope/entity/observation UX |
| `index.html` | обновить тексты и структуру панелей |
| `styles.css` | трогать минимально |

## Критерий успешной миграции

```text
grep по проекту не находит runtime-зависимостей:
mysql.connector
DB_CONFIG root/2256
monitor_rpg_model
INFORMATION_SCHEMA
MySQL как обязательное условие запуска
```

Допустимы только упоминания в документации миграции или legacy-комментариях.
