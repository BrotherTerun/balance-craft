# 20. SQLite schema design

Дата: 2026-07-02  
Статус: рабочий проектировочный черновик  
Связанные документы: `13_design_requirements.md`, `19_data_model_concept.md`, `docs/diagrams/sqlite_erd.md`

## 1. Назначение документа

Этот документ фиксирует физическую SQLite-модель BalanceCraft Desktop 1.5.

Задача документа — не написать финальный `schema.sql` до последней запятой, а определить:

- какие таблицы нужны;
- какие поля в них хранятся;
- где проходят связи;
- какие таблицы входят в P0;
- какие таблицы можно отложить;
- какие индексы нужны для первого рабочего vertical slice;
- какие решения нужно отдельно проверить при ревью.

Главный ориентир остаётся прежним:

```text
SQLite schema
→ import one JSONL
→ profile data
→ bind one template
→ calculate metric values
→ draw chart
→ show one insight
```

## 2. Ключевые решения схемы

### 2.1. Одна локальная SQLite-БД приложения

Для BalanceCraft Desktop 1.5 базовая модель — один локальный файл:

```text
Документы/BalanceCraft/balancecraft.db
```

Внутри него могут храниться несколько проектов. Поэтому почти все таблицы пользовательских данных имеют `project_id`.

Это проще для MVP:

- один путь к БД;
- один db layer;
- один механизм init/migrations;
- проще recent projects;
- проще демо-проект.

В будущем можно перейти к per-project database, но для версии 1.5 это не требуется.

### 2.2. SQLite вместо MySQL

Схема не использует:

- `CREATE DATABASE`;
- `INFORMATION_SCHEMA`;
- MySQL placeholders `%s`;
- MySQL JSON-типы;
- внешнюю службу БД.

Используются:

- SQLite-файл;
- `PRAGMA foreign_keys = ON`;
- placeholders `?`;
- `TEXT` для JSON-полей;
- `PRAGMA table_info` для introspection, если понадобится.

### 2.3. Raw events отдельно от производных данных

`events` — исторический слой. Он не изменяется при:

- расчёте метрик;
- правке semantic bindings;
- запуске What-if;
- пересчёте сценариев;
- генерации insights.

Производные данные живут отдельно:

```text
metric_runs
metric_values
scenarios
scenario_overrides
scenario_results
```

### 2.4. Entity / Observation — справочники, а не жанровая модель

`entities` и `observations` не означают “игроки” и “сессии”.

`player`, `session`, `item`, `skill`, `level`, `run`, `wave`, `battle`, `resource`, `operation` — это возможные значения `entity_type` или `observation_type`, а не отдельные фундаментальные таблицы ядра.

### 2.5. Soft relationship для event entity/observation

В P0 `events.entity_id` и `events.observation_id` хранят строковые идентификаторы из входных данных.

`entities` и `observations` создаются через upsert во время импорта, но события не обязаны иметь жёсткий FK на surrogate `entities.id` / `observations.id`.

Причины:

- события должны сохраняться даже при неполных данных;
- `entity_id` и `observation_id` приходят из пользовательских логов;
- SQLite composite FK по `project_id + entity_id` возможен, но усложняет миграцию и импорт;
- для MVP важнее устойчивый импорт, чем идеальная ссылочная строгость.

На уровне приложения действует правило:

```text
если событие содержит entity_id / observation_id,
import service должен создать или обновить соответствующую запись в справочнике.
```

### 2.6. JSON как TEXT

SQLite не требует отдельного JSON-типа. Поэтому поля вида `*_json` хранятся как `TEXT`.

Правило:

```text
JSON-поля должны хранить валидный JSON-string,
а backend отвечает за сериализацию, десериализацию и валидацию.
```

Для P0 не требуется строить индексы по JSON-полям. Профилирование данных выносит часто нужную информацию из `events.attributes_json` в `event_attribute_profile`.

### 2.7. Denormalized `project_id` в производных таблицах

`metric_values` и `scenario_results` хранят `project_id`, хотя его можно получить через `metric_run_id` или `scenario_id`.

Это сознательная денормализация для:

- быстрых выборок dashboard;
- простых фильтров по проекту;
- защиты от случайного смешивания данных;
- более прямых индексов.

Целостность должна поддерживаться service layer и транзакциями.

## 3. Таблицы по приоритетам

### 3.1. P0 — обязательная схема vertical slice

```text
projects
app_settings
schema_migrations
import_runs
source_files
entities
observations
events
event_attribute_profile
semantic_binding_sets
semantic_bindings
metric_templates
metric_runs
metric_values
```

Примечание: `schema_migrations` и `metric_templates` можно реализовать как P0-lite. Полноценный migration runner и редактируемые шаблоны можно отложить, но сами таблицы дешёвы и снижают риск хаоса.

### 3.2. P0/P1 — What-if и параметры

```text
parameter_catalogs
entity_parameters
scenarios
scenario_overrides
scenario_results
```

Эти таблицы нужны, если простой What-if входит в первый демонстрируемый vertical slice. Если What-if режется из P0, таблицы можно оставить в схеме, но не подключать UI.

### 3.3. P1 — расширение диагностики

```text
analysis_coverage_cache
value_normalization_profiles
```

В P0 analysis coverage может считаться на лету через backend API. Кэш нужен только если проверка покрытия станет заметно дорогой или понадобится история проверок.

`value_normalization_profiles` нужен для честного нормализованного ROI, но не нужен для базовых метрик “результат на единицу затрат” и “стоимость единицы результата”.

### 3.4. Не добавляем в 1.5

```text
players
sessions
items
skills
session_metrics
simulation_results
user_formula_definitions
collector_batches
sdk_clients
cloud_accounts
```

Эти таблицы либо legacy, либо future scope, либо противоречат текущей local-first рамке.

## 4. Общие соглашения по полям

### 4.1. Идентификаторы

Внутренние PK:

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
```

Внешние пользовательские идентификаторы:

```sql
entity_id TEXT
observation_id TEXT
catalog_id TEXT
template_key TEXT
metric_key TEXT
parameter_key TEXT
```

### 4.2. Даты и время

P0-формат:

```sql
TEXT -- ISO 8601 UTC
```

Примеры:

```text
2026-07-02T15:10:22Z
2026-07-02T15:10:22.120Z
```

Правило:

```text
backend нормализует timestamp до UTC-строки до записи в БД.
```

### 4.3. Статусы

Статусы хранятся как `TEXT` с application-level validation. Для самых стабильных полей можно добавить `CHECK`, но не стоит превращать первую схему в витрину SQL-героизма.

Базовые значения:

```text
pending
running
completed
completed_with_warnings
failed
cancelled
```

Для metric/scenario values:

```text
ok
n/a
warning
error
```

Для coverage:

```text
available
partially_available
missing_data
unsupported_in_version
```

Для What-if confidence:

```text
exact_recalc
approx_recalc
impact_estimate
insufficient_model
insufficient_data
```

### 4.4. JSON-поля

Все поля `*_json`:

- `TEXT`;
- nullable, если данные опциональны;
- содержат валидный JSON при записи;
- не используются как основной источник быстрых фильтров в P0.

### 4.5. Удаление проекта

Для таблиц пользовательских данных используется:

```sql
FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
```

Удаление проекта должно удалять:

- import runs;
- source files;
- events;
- entities;
- observations;
- profiles;
- bindings;
- metric runs;
- metric values;
- parameters;
- scenarios;
- scenario results.

## 5. P0 tables

## 5.1. `schema_migrations`

Назначение: хранить применённые версии схемы.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `version` | INTEGER | PK | Номер миграции |
| `name` | TEXT | NOT NULL | Человекочитаемое имя |
| `applied_at` | TEXT | NOT NULL | Время применения |
| `checksum` | TEXT | NULL | Контрольная сумма миграции |

Правило: повторный запуск init не должен ломать БД.

## 5.2. `app_settings`

Назначение: хранить настройки приложения, не относящиеся к raw-данным конкретного проекта.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `key` | TEXT | PK | Ключ настройки |
| `value_json` | TEXT | NOT NULL | Значение как JSON |
| `updated_at` | TEXT | NOT NULL | Дата обновления |

Примеры:

```text
recent_projects
default_workspace_path
ui_theme
feature_flags
```

## 5.3. `projects`

Назначение: локальные проекты анализа.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | Внутренний ID проекта |
| `name` | TEXT | NOT NULL | Название проекта |
| `created_at` | TEXT | NOT NULL | Дата создания |
| `updated_at` | TEXT | NOT NULL | Дата обновления |
| `last_opened_at` | TEXT | NULL | Последнее открытие |
| `default_build_id` | TEXT | NULL | Билд по умолчанию |
| `settings_json` | TEXT | NULL | Настройки проекта |

Индексы:

```sql
CREATE INDEX idx_projects_last_opened ON projects(last_opened_at);
```

## 5.4. `import_runs`

Назначение: один запуск импорта.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID импорта |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `source_path` | TEXT | NULL | Исходный путь: файл или папка |
| `started_at` | TEXT | NOT NULL | Старт |
| `finished_at` | TEXT | NULL | Завершение |
| `status` | TEXT | NOT NULL | Статус |
| `source_files_count` | INTEGER | NOT NULL DEFAULT 0 | Количество файлов |
| `read_lines` | INTEGER | NOT NULL DEFAULT 0 | Прочитанные строки |
| `valid_events` | INTEGER | NOT NULL DEFAULT 0 | Валидные события |
| `invalid_events` | INTEGER | NOT NULL DEFAULT 0 | Невалидные события |
| `imported_events` | INTEGER | NOT NULL DEFAULT 0 | Записанные события |
| `warnings_json` | TEXT | NULL | Предупреждения |
| `errors_json` | TEXT | NULL | Ошибки |

Индексы:

```sql
CREATE INDEX idx_import_runs_project_started ON import_runs(project_id, started_at);
```

## 5.5. `source_files`

Назначение: файлы, участвовавшие в import run.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID файла |
| `import_run_id` | INTEGER | FK, NOT NULL | Запуск импорта |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `file_path` | TEXT | NULL | Полный путь, если доступен |
| `file_name` | TEXT | NOT NULL | Имя файла |
| `file_hash` | TEXT | NULL | Hash содержимого |
| `lines_count` | INTEGER | NOT NULL DEFAULT 0 | Строки |
| `valid_events` | INTEGER | NOT NULL DEFAULT 0 | Валидные события |
| `invalid_events` | INTEGER | NOT NULL DEFAULT 0 | Невалидные строки |
| `status` | TEXT | NOT NULL | Статус |
| `errors_json` | TEXT | NULL | Ошибки файла |

Индексы:

```sql
CREATE INDEX idx_source_files_import_run ON source_files(import_run_id);
CREATE INDEX idx_source_files_project_hash ON source_files(project_id, file_hash);
```

## 5.6. `entities`

Назначение: справочник сущностей проекта.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | Внутренний ID |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `entity_id` | TEXT | NOT NULL | Внешний ID из логов/параметров |
| `entity_type` | TEXT | NULL | Тип сущности |
| `label` | TEXT | NULL | Человекочитаемое имя |
| `metadata_json` | TEXT | NULL | Дополнительные данные |
| `created_at` | TEXT | NOT NULL | Создание |
| `updated_at` | TEXT | NOT NULL | Обновление |

Ограничения:

```sql
UNIQUE(project_id, entity_id)
```

Индексы:

```sql
CREATE INDEX idx_entities_project_type ON entities(project_id, entity_type);
```

## 5.7. `observations`

Назначение: окна наблюдения: run, session, level, battle, day, wave, playtest и т.д.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | Внутренний ID |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `observation_id` | TEXT | NOT NULL | Внешний ID окна |
| `observation_type` | TEXT | NULL | Тип окна |
| `started_at` | TEXT | NULL | Начало окна |
| `ended_at` | TEXT | NULL | Конец окна |
| `build_id` | TEXT | NULL | Билд |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Ограничения:

```sql
UNIQUE(project_id, observation_id)
```

Индексы:

```sql
CREATE INDEX idx_observations_project_type ON observations(project_id, observation_type);
CREATE INDEX idx_observations_project_build ON observations(project_id, build_id);
```

## 5.8. `events`

Назначение: raw-события.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | Внутренний ID события |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `import_run_id` | INTEGER | FK, NOT NULL | Запуск импорта |
| `source_file_id` | INTEGER | FK, NULL | Исходный файл |
| `source_line_number` | INTEGER | NULL | Номер строки |
| `timestamp` | TEXT | NOT NULL | ISO UTC timestamp |
| `event_order` | INTEGER | NULL | Порядок внутри импорта, если timestamp одинаковый/неточный |
| `entity_id` | TEXT | NOT NULL | Внешний ID сущности |
| `entity_type` | TEXT | NULL | Тип сущности из события |
| `observation_id` | TEXT | NULL | ID окна наблюдения |
| `observation_type` | TEXT | NULL | Тип окна из события |
| `event_type` | TEXT | NOT NULL | Тип события |
| `build_id` | TEXT | NULL | Версия игры/билда |
| `schema_version` | TEXT | NULL | Версия формата события |
| `source_id` | TEXT | NULL | Источник логов |
| `attributes_json` | TEXT | NOT NULL | Raw attributes |

Индексы:

```sql
CREATE INDEX idx_events_project_time ON events(project_id, timestamp);
CREATE INDEX idx_events_project_type_time ON events(project_id, event_type, timestamp);
CREATE INDEX idx_events_project_entity_time ON events(project_id, entity_id, timestamp);
CREATE INDEX idx_events_project_observation ON events(project_id, observation_id);
CREATE INDEX idx_events_project_build ON events(project_id, build_id);
CREATE INDEX idx_events_import_run ON events(import_run_id);
CREATE INDEX idx_events_source_file ON events(source_file_id);
```

Важное правило: `events.attributes_json` хранит исходный payload без потери данных.

## 5.9. `event_attribute_profile`

Назначение: кэш карты данных после профилирования событий.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID профиля |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `event_type` | TEXT | NOT NULL | Тип события |
| `attribute_key` | TEXT | NOT NULL | Ключ attribute |
| `attribute_path` | TEXT | NULL | Путь для будущих вложенных полей |
| `total_count` | INTEGER | NOT NULL DEFAULT 0 | Всего значений |
| `numeric_count` | INTEGER | NOT NULL DEFAULT 0 | Числа |
| `string_count` | INTEGER | NOT NULL DEFAULT 0 | Строки |
| `boolean_count` | INTEGER | NOT NULL DEFAULT 0 | Boolean |
| `null_count` | INTEGER | NOT NULL DEFAULT 0 | Null |
| `missing_count` | INTEGER | NOT NULL DEFAULT 0 | Отсутствует в событиях данного типа |
| `min_value` | REAL | NULL | Минимум для чисел |
| `max_value` | REAL | NULL | Максимум для чисел |
| `sample_values_json` | TEXT | NULL | Примеры значений |
| `last_profiled_at` | TEXT | NOT NULL | Последнее профилирование |

Ограничения:

```sql
UNIQUE(project_id, event_type, attribute_key)
```

Индексы:

```sql
CREATE INDEX idx_attr_profile_project_event ON event_attribute_profile(project_id, event_type);
CREATE INDEX idx_attr_profile_project_key ON event_attribute_profile(project_id, attribute_key);
```

## 5.10. `metric_templates`

Назначение: каталог шаблонов метрик.

В P0 источником истины может быть code registry. Таблица нужна для:

- отображения шаблонов в UI;
- snapshot/debug;
- будущего расширения;
- единых ключей `template_key`.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID шаблона |
| `template_key` | TEXT | UNIQUE, NOT NULL | Стабильный ключ |
| `version` | TEXT | NOT NULL DEFAULT '1.0' | Версия шаблона |
| `name` | TEXT | NOT NULL | Название |
| `description` | TEXT | NULL | Описание |
| `priority` | TEXT | NULL | P0/P1/P2 |
| `variables_json` | TEXT | NOT NULL | Переменные шаблона |
| `metrics_json` | TEXT | NOT NULL | Метрики шаблона |
| `default_formulas_json` | TEXT | NOT NULL | Формулы |
| `is_builtin` | INTEGER | NOT NULL DEFAULT 1 | Встроенный шаблон |
| `created_at` | TEXT | NOT NULL | Создание |
| `updated_at` | TEXT | NOT NULL | Обновление |

Индексы:

```sql
CREATE INDEX idx_metric_templates_key ON metric_templates(template_key);
CREATE INDEX idx_metric_templates_priority ON metric_templates(priority);
```

P0-шаблоны:

```text
flow_balance
stock_dynamics
conversion_efficiency
operation_intensity
```

## 5.11. `semantic_binding_sets`

Назначение: группа semantic bindings для одного шаблона.

Почему нужна отдельная таблица: один шаблон требует несколько переменных. Плоская таблица `semantic_bindings` без группы усложняет сохранение набора, переиспользование, запуск metric run и UI-редактирование.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID набора |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `template_key` | TEXT | NOT NULL | Ключ шаблона |
| `name` | TEXT | NOT NULL | Название настройки |
| `scope_json` | TEXT | NULL | Базовый scope |
| `status` | TEXT | NOT NULL | draft/valid/invalid |
| `warnings_json` | TEXT | NULL | Предупреждения валидации |
| `created_at` | TEXT | NOT NULL | Создание |
| `updated_at` | TEXT | NOT NULL | Обновление |

Индексы:

```sql
CREATE INDEX idx_binding_sets_project_template ON semantic_binding_sets(project_id, template_key);
```

## 5.12. `semantic_bindings`

Назначение: связь переменной шаблона с источником данных.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID binding-а |
| `binding_set_id` | INTEGER | FK, NOT NULL | Набор binding-ов |
| `project_id` | INTEGER | FK, NOT NULL | Денормализованный project_id |
| `variable_key` | TEXT | NOT NULL | Переменная шаблона |
| `source_kind` | TEXT | NOT NULL | event_attribute / parameter / computed |
| `source_path` | TEXT | NOT NULL | Например `attributes.amount` |
| `event_types_json` | TEXT | NULL | Фильтр event_type |
| `aggregation` | TEXT | NULL | sum/avg/count/min/max/last |
| `filters_json` | TEXT | NULL | Дополнительные фильтры |
| `unit` | TEXT | NULL | Единица измерения |
| `label` | TEXT | NULL | Пользовательская подпись |
| `is_required` | INTEGER | NOT NULL DEFAULT 1 | Обязательная переменная |
| `status` | TEXT | NOT NULL | valid/invalid/warning |
| `warnings_json` | TEXT | NULL | Предупреждения |

Ограничения:

```sql
UNIQUE(binding_set_id, variable_key)
```

Индексы:

```sql
CREATE INDEX idx_semantic_bindings_set ON semantic_bindings(binding_set_id);
CREATE INDEX idx_semantic_bindings_project_source ON semantic_bindings(project_id, source_kind);
```

## 5.13. `metric_runs`

Назначение: один запуск расчёта метрик.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID запуска |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `template_key` | TEXT | NOT NULL | Шаблон |
| `binding_set_id` | INTEGER | FK, NULL | Использованный набор binding-ов |
| `scope_json` | TEXT | NULL | Срез расчёта |
| `binding_snapshot_json` | TEXT | NOT NULL | Snapshot binding-ов |
| `formula_snapshot_json` | TEXT | NOT NULL | Snapshot формул |
| `started_at` | TEXT | NOT NULL | Старт |
| `finished_at` | TEXT | NULL | Завершение |
| `status` | TEXT | NOT NULL | Статус |
| `warnings_json` | TEXT | NULL | Warnings |
| `errors_json` | TEXT | NULL | Errors |

Индексы:

```sql
CREATE INDEX idx_metric_runs_project_started ON metric_runs(project_id, started_at);
CREATE INDEX idx_metric_runs_project_template ON metric_runs(project_id, template_key);
CREATE INDEX idx_metric_runs_binding_set ON metric_runs(binding_set_id);
```

## 5.14. `metric_values`

Назначение: рассчитанные значения метрик.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID значения |
| `metric_run_id` | INTEGER | FK, NOT NULL | Запуск расчёта |
| `project_id` | INTEGER | FK, NOT NULL | Денормализованный проект |
| `metric_key` | TEXT | NOT NULL | Ключ метрики |
| `metric_label` | TEXT | NULL | Подпись метрики |
| `scope_key` | TEXT | NULL | Срез/группа |
| `entity_id` | TEXT | NULL | Сущность, если применимо |
| `observation_id` | TEXT | NULL | Окно, если применимо |
| `event_type` | TEXT | NULL | Тип события, если применимо |
| `build_id` | TEXT | NULL | Билд, если применимо |
| `x_index` | INTEGER | NULL | Порядок точки |
| `x_label` | TEXT | NULL | Подпись точки |
| `x_timestamp` | TEXT | NULL | Время точки |
| `value_number` | REAL | NULL | Числовое значение |
| `value_text` | TEXT | NULL | Текстовое значение, если нужно |
| `status` | TEXT | NOT NULL | ok/n/a/warning/error |
| `warnings_json` | TEXT | NULL | Warnings |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Индексы:

```sql
CREATE INDEX idx_metric_values_run_key ON metric_values(metric_run_id, metric_key);
CREATE INDEX idx_metric_values_project_key ON metric_values(project_id, metric_key);
CREATE INDEX idx_metric_values_project_scope ON metric_values(project_id, scope_key);
CREATE INDEX idx_metric_values_project_entity ON metric_values(project_id, entity_id);
CREATE INDEX idx_metric_values_project_observation ON metric_values(project_id, observation_id);
```

Правило расчёта:

```text
если значение нельзя корректно посчитать,
value_number = NULL,
status = 'n/a' или 'warning',
warnings_json объясняет причину.
```

## 6. Parameters and What-if tables

## 6.1. `parameter_catalogs`

Назначение: источник параметров проекта.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID каталога |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `catalog_id` | TEXT | NOT NULL | Внешний ключ каталога |
| `name` | TEXT | NOT NULL | Название |
| `build_id` | TEXT | NULL | Билд |
| `schema_version` | TEXT | NULL | Версия формата |
| `source_path` | TEXT | NULL | Источник |
| `created_at` | TEXT | NOT NULL | Создание |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Ограничения:

```sql
UNIQUE(project_id, catalog_id)
```

## 6.2. `entity_parameters`

Назначение: значения параметров сущностей.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID параметра |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `catalog_id` | INTEGER | FK, NULL | Каталог параметров |
| `entity_id` | TEXT | NOT NULL | Сущность |
| `entity_type` | TEXT | NULL | Тип сущности |
| `parameter_key` | TEXT | NOT NULL | Ключ параметра |
| `value_type` | TEXT | NOT NULL | number/string/boolean/json/null |
| `value_number` | REAL | NULL | Числовое значение |
| `value_text` | TEXT | NULL | Строковое значение |
| `value_bool` | INTEGER | NULL | Boolean как 0/1 |
| `value_json` | TEXT | NULL | Сложное значение |
| `unit` | TEXT | NULL | Единица измерения |
| `valid_from` | TEXT | NULL | Начало действия |
| `valid_to` | TEXT | NULL | Конец действия |
| `build_id` | TEXT | NULL | Билд |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Индексы:

```sql
CREATE INDEX idx_parameters_project_entity ON entity_parameters(project_id, entity_id);
CREATE INDEX idx_parameters_project_key ON entity_parameters(project_id, parameter_key);
CREATE INDEX idx_parameters_project_entity_key ON entity_parameters(project_id, entity_id, parameter_key);
CREATE INDEX idx_parameters_project_build ON entity_parameters(project_id, build_id);
```

Правило: для `value_type = 'number'` используется `value_number`; для остальных типов backend должен явно выбирать соответствующее поле.

## 6.3. `scenarios`

Назначение: What-if сценарии.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID сценария |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `name` | TEXT | NOT NULL | Название |
| `description` | TEXT | NULL | Описание |
| `base_metric_run_id` | INTEGER | FK, NULL | Исторический metric run |
| `created_at` | TEXT | NOT NULL | Создание |
| `updated_at` | TEXT | NOT NULL | Обновление |
| `status` | TEXT | NOT NULL | Статус |
| `confidence_status` | TEXT | NULL | Статус уверенности |
| `warnings_json` | TEXT | NULL | Warnings |

Индексы:

```sql
CREATE INDEX idx_scenarios_project ON scenarios(project_id);
CREATE INDEX idx_scenarios_base_run ON scenarios(base_metric_run_id);
```

## 6.4. `scenario_overrides`

Назначение: конкретные изменения параметров в сценарии.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID override |
| `scenario_id` | INTEGER | FK, NOT NULL | Сценарий |
| `project_id` | INTEGER | FK, NOT NULL | Денормализованный проект |
| `entity_id` | TEXT | NOT NULL | Сущность |
| `parameter_key` | TEXT | NOT NULL | Параметр |
| `override_mode` | TEXT | NOT NULL | set/multiplier/delta |
| `original_value_number` | REAL | NULL | Старое число |
| `scenario_value_number` | REAL | NULL | Новое число |
| `original_value_text` | TEXT | NULL | Старое текстовое значение |
| `scenario_value_text` | TEXT | NULL | Новое текстовое значение |
| `multiplier` | REAL | NULL | Множитель |
| `delta` | REAL | NULL | Дельта |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Индексы:

```sql
CREATE INDEX idx_scenario_overrides_scenario ON scenario_overrides(scenario_id);
CREATE INDEX idx_scenario_overrides_project_param ON scenario_overrides(project_id, parameter_key);
```

## 6.5. `scenario_results`

Назначение: результат сценарного пересчёта.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID результата |
| `scenario_id` | INTEGER | FK, NOT NULL | Сценарий |
| `project_id` | INTEGER | FK, NOT NULL | Денормализованный проект |
| `metric_key` | TEXT | NOT NULL | Метрика |
| `metric_label` | TEXT | NULL | Подпись |
| `scope_key` | TEXT | NULL | Срез |
| `entity_id` | TEXT | NULL | Сущность |
| `observation_id` | TEXT | NULL | Окно |
| `x_index` | INTEGER | NULL | Порядок точки |
| `x_label` | TEXT | NULL | Подпись точки |
| `x_timestamp` | TEXT | NULL | Время точки |
| `historical_value_number` | REAL | NULL | Историческое значение |
| `scenario_value_number` | REAL | NULL | Сценарное значение |
| `delta_value` | REAL | NULL | Разница |
| `delta_percent` | REAL | NULL | Процент изменения |
| `status` | TEXT | NOT NULL | ok/n/a/warning/error |
| `confidence_status` | TEXT | NOT NULL | Уровень уверенности |
| `warnings_json` | TEXT | NULL | Warnings |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Индексы:

```sql
CREATE INDEX idx_scenario_results_scenario_key ON scenario_results(scenario_id, metric_key);
CREATE INDEX idx_scenario_results_project_key ON scenario_results(project_id, metric_key);
CREATE INDEX idx_scenario_results_project_scope ON scenario_results(project_id, scope_key);
```

Правило: сценарные результаты не изменяют `metric_values` и не изменяют `events`.

## 7. P1 tables

## 7.1. `analysis_coverage_cache`

Назначение: кэш результата проверки, какие проблемы баланса можно проверить по текущим данным.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID результата |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `problem_key` | TEXT | NOT NULL | Ключ проблемы |
| `problem_label` | TEXT | NOT NULL | Название |
| `status` | TEXT | NOT NULL | available/partially/missing/unsupported |
| `required_signals_json` | TEXT | NULL | Что нужно |
| `available_signals_json` | TEXT | NULL | Что найдено |
| `missing_signals_json` | TEXT | NULL | Чего не хватает |
| `template_key` | TEXT | NULL | Связанный шаблон |
| `last_checked_at` | TEXT | NOT NULL | Дата проверки |
| `metadata_json` | TEXT | NULL | Дополнительные данные |

Ограничения:

```sql
UNIQUE(project_id, problem_key)
```

P0-альтернатива: считать coverage на лету и не писать в БД.

## 7.2. `value_normalization_profiles`

Назначение: правила приведения разных единиц к общей дизайнерской шкале.

| Поле | Тип | Ограничения | Назначение |
|---|---|---|---|
| `id` | INTEGER | PK | ID профиля |
| `project_id` | INTEGER | FK, NOT NULL | Проект |
| `name` | TEXT | NOT NULL | Название |
| `value_unit` | TEXT | NOT NULL | Общая единица |
| `mapping_rules_json` | TEXT | NOT NULL | Правила нормализации |
| `created_at` | TEXT | NOT NULL | Создание |
| `updated_at` | TEXT | NOT NULL | Обновление |

P0-альтернатива: считать строгий ROI только если входные данные уже содержат `cost_value`, `result_value`, `value_unit`.

## 8. Таблицы, которые не нужны

### 8.1. `insights`

Для P0 отдельная таблица `insights` не нужна.

Причина: practical insights могут генерироваться на лету из `metric_values`, `metric_runs.warnings_json` и данных шаблона.

Постоянное хранение insights можно добавить позже, если понадобится:

- история выводов;
- пользовательские пометки;
- экспорт отчётов;
- сравнение выводов между билдами.

### 8.2. `event_attributes`

Для P0 не нужно разносить каждый attribute каждой строки события в отдельную таблицу.

Причина: это резко раздует объём БД. Вместо этого:

```text
events.attributes_json хранит raw payload;
event_attribute_profile хранит карту полей;
metric engine достаёт нужные поля при расчёте.
```

Если производительность по JSON extraction станет проблемой, позже можно добавить materialized attribute columns или отдельную таблицу для selected numeric attributes.

### 8.3. `users`

BalanceCraft Desktop 1.5 local-only. Аккаунты пользователей не нужны.

## 9. Foreign keys

Базовые FK:

```sql
import_runs.project_id → projects.id
source_files.project_id → projects.id
source_files.import_run_id → import_runs.id
entities.project_id → projects.id
observations.project_id → projects.id
events.project_id → projects.id
events.import_run_id → import_runs.id
events.source_file_id → source_files.id
event_attribute_profile.project_id → projects.id
semantic_binding_sets.project_id → projects.id
semantic_bindings.project_id → projects.id
semantic_bindings.binding_set_id → semantic_binding_sets.id
metric_runs.project_id → projects.id
metric_runs.binding_set_id → semantic_binding_sets.id
metric_values.project_id → projects.id
metric_values.metric_run_id → metric_runs.id
parameter_catalogs.project_id → projects.id
entity_parameters.project_id → projects.id
entity_parameters.catalog_id → parameter_catalogs.id
scenarios.project_id → projects.id
scenarios.base_metric_run_id → metric_runs.id
scenario_overrides.project_id → projects.id
scenario_overrides.scenario_id → scenarios.id
scenario_results.project_id → projects.id
scenario_results.scenario_id → scenarios.id
```

Не P0-FK:

```text
events.entity_id → entities.entity_id
events.observation_id → observations.observation_id
metric_values.entity_id → entities.entity_id
metric_values.observation_id → observations.observation_id
```

Они остаются soft relationships через `project_id + external_id`.

## 10. Минимальный schema SQL skeleton

Это не финальный файл миграции, а ориентир для реализации.

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_opened_at TEXT,
  default_build_id TEXT,
  settings_json TEXT
);

CREATE TABLE IF NOT EXISTS import_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  source_path TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  source_files_count INTEGER NOT NULL DEFAULT 0,
  read_lines INTEGER NOT NULL DEFAULT 0,
  valid_events INTEGER NOT NULL DEFAULT 0,
  invalid_events INTEGER NOT NULL DEFAULT 0,
  imported_events INTEGER NOT NULL DEFAULT 0,
  warnings_json TEXT,
  errors_json TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  import_run_id INTEGER NOT NULL,
  source_file_id INTEGER,
  source_line_number INTEGER,
  timestamp TEXT NOT NULL,
  event_order INTEGER,
  entity_id TEXT NOT NULL,
  entity_type TEXT,
  observation_id TEXT,
  observation_type TEXT,
  event_type TEXT NOT NULL,
  build_id TEXT,
  schema_version TEXT,
  source_id TEXT,
  attributes_json TEXT NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY(import_run_id) REFERENCES import_runs(id) ON DELETE CASCADE,
  FOREIGN KEY(source_file_id) REFERENCES source_files(id) ON DELETE SET NULL
);
```

Полный `schema.sql` лучше писать уже на этапе разработки после утверждения этого дизайна.

## 11. Минимальные индексы P0

Обязательный набор:

```sql
CREATE INDEX idx_events_project_time ON events(project_id, timestamp);
CREATE INDEX idx_events_project_type_time ON events(project_id, event_type, timestamp);
CREATE INDEX idx_events_project_entity_time ON events(project_id, entity_id, timestamp);
CREATE INDEX idx_events_project_observation ON events(project_id, observation_id);
CREATE INDEX idx_events_project_build ON events(project_id, build_id);

CREATE INDEX idx_metric_values_run_key ON metric_values(metric_run_id, metric_key);
CREATE INDEX idx_metric_values_project_key ON metric_values(project_id, metric_key);
CREATE INDEX idx_metric_values_project_scope ON metric_values(project_id, scope_key);

CREATE INDEX idx_parameters_project_entity ON entity_parameters(project_id, entity_id);
CREATE INDEX idx_parameters_project_key ON entity_parameters(project_id, parameter_key);
```

Не нужно на старте индексировать всё подряд. Индекс — это не бесплатная магическая руна скорости, а дополнительная стоимость на импорт и запись.

## 12. Транзакции

Транзакция импорта:

```text
BEGIN
→ create import_run
→ create source_files
→ upsert entities
→ upsert observations
→ insert events
→ update import_run counters
→ profile data
COMMIT
```

Если импорт падает:

```text
ROLLBACK
→ показать import error
→ не оставлять половину событий без import_run
```

Транзакция metric run:

```text
BEGIN
→ create metric_run
→ calculate aggregates
→ insert metric_values
→ write warnings/errors
→ update metric_run status
COMMIT
```

Транзакция scenario run:

```text
BEGIN
→ create/update scenario
→ write scenario_overrides
→ calculate scenario_results
→ update confidence_status
COMMIT
```

## 13. Проверки корректности

### 13.1. Import checks

- `timestamp` есть и парсится;
- `entity_id` есть;
- `event_type` есть;
- `attributes` является object;
- строка невалидного JSON не валит весь файл;
- source file и line number сохраняются.

### 13.2. Binding checks

- все required variables связаны;
- `source_path` существует в profile или parameters;
- для числовых формул источник содержит числовые значения;
- фильтр `event_type` не возвращает пустой набор без warning;
- несовместимые единицы дают warning.

### 13.3. Metric checks

- `safe_div` возвращает `N/A` при нулевом знаменателе;
- `ROI` не считается как строгий ROI без сопоставимых units/value fields;
- `metric_values.status` отражает качество значения;
- warnings сохраняются вместе с run/value.

### 13.4. Scenario checks

- scenario не изменяет `events`;
- scenario не перезаписывает `metric_values`;
- `confidence_status` сохраняется;
- отсутствие модели возвращает `insufficient_model`, а не фальшивый прогноз.

## 14. Review notes

### RN-1. Single app DB vs per-project DB

Текущее решение: один `balancecraft.db`, несколько проектов через `project_id`.

Почему пока так:

- проще MVP;
- проще recent projects;
- проще демо;
- проще миграции.

К чему вернуться позже: portable project folder with own `project.db`.

### RN-2. `metric_templates`: code-first или DB-first

Текущее решение: hybrid.

- P0 источник истины — code registry.
- Таблица `metric_templates` может seed-иться из кода.
- `metric_runs.formula_snapshot_json` обязательно сохраняет фактически использованные формулы.

Так мы не блокируем разработку UI/engine и не строим преждевременный template editor.

### RN-3. `semantic_binding_sets`

Это уточнение относительно ранней предварительной схемы, где была только таблица `semantic_bindings`.

Причина изменения: binding в реальности является набором переменных одного шаблона. Без `binding_set` сложнее:

- валидировать конфигурацию целиком;
- запускать metric run;
- хранить draft/valid state;
- показывать список сохранённых настроек.

### RN-4. Strong FK для `events.entity_id`

Текущее решение: soft relationship.

Жёсткий FK можно добавить позже, но для P0 он создаёт больше проблем, чем пользы:

- nullable/dirty observation_id;
- legacy logs;
- auto observations;
- импорт частично грязных файлов.

### RN-5. What-if tables

Схема включает What-if tables, даже если UI What-if будет срезан из самого первого P0.

Причина: таблицы не ломают P0, но помогают не перепроектировать БД через два дня после появления панели сценариев.

### RN-6. `analysis_coverage_cache`

Таблица P1. P0 должен уметь вернуть coverage из backend API на лету.

Кэш добавляется только если:

- проверка coverage становится дорогой;
- требуется история проверок;
- UI начинает использовать coverage как отдельный persisted state.

### RN-7. Value normalization

`value_normalization_profiles` не должен тащить в MVP полноценный редактор нормализации.

P0-правило проще:

```text
если есть cost_value/result_value/value_unit → можно считать нормализованный ROI;
если нет → считать result_per_cost или cost_per_result.
```

## 15. Критерий готовности схемы к реализации

Схема считается достаточно спроектированной для начала разработки, если:

```text
приложение может создать SQLite-БД;
может создать проект;
может импортировать JSONL в events;
может восстановить import report;
может построить event_attribute_profile;
может сохранить binding set;
может создать metric run;
может сохранить metric values с N/A/warnings;
может построить dashboard dataset;
What-if tables не мешают P0, даже если UI будет отложен;
в схеме нет MySQL, players/sessions/items/skills как ядра.
```

