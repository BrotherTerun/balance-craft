# 13. Требования к проектированию

## Назначение

Этот документ начинается после продуктовой рамки, сценариев, требований и форматов данных. Здесь фиксируется техническая основа, по которой можно проектировать БД, модули и потоки данных.

## Архитектурная цель версии 1.5

```text
BalanceCraft Desktop local-only
+ SQLite
+ universal data model
+ JSONL import
+ semantic binding
+ metric engine
+ chart dashboard
+ practical insights
+ simple parameter What-if
```

## Компоненты Desktop

| Компонент | Ответственность |
|---|---|
| `app shell` | запуск desktop-приложения, QWebEngine, lifecycle |
| `db layer` | SQLite connection, migrations, transactions |
| `project service` | проекты, настройки, recent projects |
| `settings service` | пользовательские настройки, пути, feature flags, local-only параметры |
| `import service` | чтение файлов, валидация, import runs |
| `data profiler` | карта событий, attributes, типы, примеры |
| `analysis coverage service` | определение проблем баланса, которые можно проверить по текущим данным |
| `binding service` | semantic bindings, templates, formulas |
| `metric engine` | расчёт metric runs и metric values |
| `insight engine` | practical insights поверх рядов |
| `what-if engine` | сценарии, overrides, confidence statuses |
| `frontend` | UI, графики, wizard, panels |

## Предварительная SQLite-модель

### `schema_migrations`

Хранит версии схемы.

```text
version
applied_at
name
```

### `app_settings`

Локальные настройки приложения, не являющиеся raw-данными проекта.

```text
key
value_json
updated_at
```

Примеры: последние проекты, путь по умолчанию, feature flags, настройки UI.

### `projects`

```text
id
name
created_at
updated_at
last_opened_at
default_build_id
settings_json
```

### `import_runs`

```text
id
project_id
source_path
started_at
finished_at
status
source_files_count
read_lines
valid_events
invalid_events
imported_events
warnings_json
errors_json
```

### `source_files`

```text
id
import_run_id
project_id
file_path
file_name
file_hash
lines_count
valid_events
invalid_events
status
```

### `entities`

```text
id
project_id
entity_id
entity_type
label
metadata_json
created_at
updated_at
```

Уникальность: `project_id + entity_id`.

### `observations`

```text
id
project_id
observation_id
observation_type
started_at
ended_at
build_id
metadata_json
```

Уникальность: `project_id + observation_id`.

### `events`

```text
id
project_id
import_run_id
source_file_id
source_line_number
timestamp
entity_id
entity_type
observation_id
observation_type
event_type
build_id
schema_version
attributes_json
```

`attributes_json` хранит raw attributes без потери данных.

### `event_attribute_profile`

Кэш карты данных.

```text
id
project_id
attribute_key
event_type
count
numeric_count
string_count
boolean_count
null_count
min_value
max_value
sample_values_json
last_profiled_at
```


### `analysis_coverage_cache`

P1-кэш результата проверки покрытия анализа. Для P0 coverage может считаться на лету backend API без отдельной таблицы.

```text
id
project_id
problem_key
problem_label
status
required_signals_json
available_signals_json
missing_signals_json
template_key
last_checked_at
metadata_json
```

`status`:

```text
available
partially_available
missing_data
unsupported_in_version
```

Таблица не обязана быть частью P0, если покрытие анализа считается на лету. Но модель должна учитывать такой результат как часть UX и диагностики.

### `parameter_catalogs`

```text
id
project_id
catalog_id
name
build_id
schema_version
source_path
created_at
metadata_json
```

### `entity_parameters`

```text
id
project_id
catalog_id
entity_id
entity_type
parameter_key
value
value_type
unit
valid_from
valid_to
build_id
metadata_json
```

### `value_normalization_profiles`

P1-таблица для случаев, когда проекту нужен нормализованный ROI. Для P0 строгий ROI можно считать только если `cost_value/result_value/value_unit` уже присутствуют во входных данных.

```text
id
project_id
name
value_unit
mapping_rules_json
created_at
updated_at
```

`mapping_rules_json` описывает, какие поля или параметры используются для приведения разных величин к общей шкале. Raw-события при этом не изменяются.

### `metric_templates`

```text
id
template_key
name
description
variables_json
metrics_json
default_formulas_json
is_builtin
```

Встроенные шаблоны можно хранить в коде, но БД должна позволять сохранять пользовательские настройки.

### `semantic_bindings`

```text
id
project_id
template_key
variable_key
source_kind
source_path
event_types_json
aggregation
filters_json
created_at
updated_at
```

### `metric_runs`

```text
id
project_id
template_key
scope_json
binding_snapshot_json
formula_snapshot_json
started_at
finished_at
status
warnings_json
```

### `metric_values`

```text
id
metric_run_id
project_id
metric_key
metric_label
scope_key
entity_id
observation_id
x_index
x_label
value
status
warnings_json
metadata_json
```

### `scenarios`

```text
id
project_id
name
description
base_metric_run_id
created_at
updated_at
status
confidence_status
```

### `scenario_overrides`

```text
id
scenario_id
entity_id
parameter_key
override_mode
original_value
scenario_value
multiplier
delta
metadata_json
```

### `scenario_results`

```text
id
scenario_id
metric_key
scope_key
entity_id
observation_id
x_index
x_label
historical_value
scenario_value
delta_value
delta_percent
confidence_status
metadata_json
```

## Индексы

Минимум:

```sql
CREATE INDEX idx_events_project_time ON events(project_id, timestamp);
CREATE INDEX idx_events_project_entity ON events(project_id, entity_id);
CREATE INDEX idx_events_project_observation ON events(project_id, observation_id);
CREATE INDEX idx_events_project_type ON events(project_id, event_type);
CREATE INDEX idx_events_project_build ON events(project_id, build_id);
CREATE INDEX idx_metric_values_run_key ON metric_values(metric_run_id, metric_key);
CREATE INDEX idx_parameters_project_entity ON entity_parameters(project_id, entity_id);
CREATE INDEX idx_parameters_project_key ON entity_parameters(project_id, parameter_key);
```

## Поток данных импорта

```text
выбор источника
→ поиск файлов
→ чтение строк
→ parse JSON
→ validation
→ import_run
→ source_files
→ entities / observations upsert
→ events insert
→ profile data
→ import report
```


## Поток проверки покрытия анализа

```text
profile data
→ прочитать event_type, attributes, semantic bindings и parameters
→ сопоставить с таксономией проблем баланса
→ определить available / partially_available / missing_data
→ показать пользователю, какие проблемы можно проверить
→ объяснить, каких событий или полей не хватает
```

Минимальный P0-результат может считаться без отдельной таблицы, но API должен возвращать этот блок в стабильном формате.

## Поток данных расчёта метрик

```text
выбор шаблона
→ чтение semantic_bindings
→ построение scope
→ выбор событий
→ агрегация переменных
→ расчёт формул
→ проверка `safe_div`, единиц измерения и calculation warnings
→ metric_run
→ metric_values
→ datasets для UI
→ practical insights
```

## Поток What-if

```text
выбор сценария
→ выбор parameter overrides
→ определение уровня What-if
→ пересчёт доступного слоя
→ scenario_results
→ comparison datasets
→ scenario insights
→ confidence status по правилам из `05_what_if_levels.md`
```

## Требования к SQL-слою

- Один модуль отвечает за соединение с БД.
- Все запросы используют параметризованные placeholders SQLite.
- Включить `PRAGMA foreign_keys = ON`.
- Рассмотреть `WAL` для устойчивости.
- Не использовать MySQL-specific SQL.
- Не обращаться к `INFORMATION_SCHEMA`.
- Для introspection использовать `PRAGMA table_info`.
- Импорт и расчёт метрик выполняются в транзакциях.
- Частично упавший импорт не должен оставлять проект в невалидном состоянии.
- Все таблицы с пользовательскими данными проекта должны иметь `project_id`, если они не являются глобальными справочниками приложения.
- Значения метрик должны хранить status/warnings, чтобы UI мог отличить корректное число от `N/A` или расчёта с предупреждением.
- Формулы шаблонов должны сохраняться как snapshot на уровне metric run.
- Пользовательские формулы не проектируются как часть 1.5; если появятся позже, для них нужен отдельный безопасный expression layer.

## Требования к API между backend и frontend

Backend должен отдавать JSON-ответы стабильной структуры. UI не должен зависеть от сырого SQL, traceback или внутренних исключений Python.

Общий envelope ответа:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": []
}
```

Правила:

- ошибки backend возвращаются как структурированные `errors`;
- пользовательские сообщения отделяются от технических details;
- `warnings` используются для неполных данных, `N/A`, пропусков и ограничений расчёта;
- для долгих операций желательно возвращать progress/status, даже если это будет P1.

Пример dataset:

```json
{
  "success": true,
  "labels": ["1", "2", "3"],
  "datasets": [
    {
      "metric_key": "NET_FLOW",
      "label": "Чистый поток",
      "data": [10, 12, -3],
      "status": ["ok", "ok", "ok"],
      "warnings": []
    }
  ],
  "insights": []
}
```

## Тестовые сценарии проектирования

1. Новый проект создаётся и переживает перезапуск.
2. JSONL с 100 событиями импортируется.
3. Битая строка не валит весь импорт.
4. Карта данных показывает `event_type` и attributes.
5. Система показывает хотя бы базовое покрытие анализа: какие проблемы можно/нельзя проверить.
6. Binding Wizard сохраняет конфигурацию.
7. Metric run создаётся отдельно от raw events.
8. Dashboard строит график.
9. Scenario не изменяет историю.
10. UI показывает `N/A` и calculation warnings без падения графика.
11. SDK-like JSONL sample импортируется без конвертации.
12. Данные не отправляются наружу.

## Главное правило проектирования

Сначала универсальная модель и local-first runtime. Потом расширения.
