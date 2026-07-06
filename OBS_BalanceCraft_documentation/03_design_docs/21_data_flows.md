# FILE: `03_design_docs/21_data_flows.md`
# 21. Data flows

Дата: 2026-07-02  
Статус: рабочий черновик для проектирования и ревью

## Назначение

Документ фиксирует основные потоки данных BalanceCraft Desktop 1.5.

Он нужен, чтобы до разработки было понятно:

- какие действия запускает пользователь;
- какие backend-компоненты участвуют;
- какие таблицы читаются и пишутся;
- где возникают warnings и errors;
- где raw-события остаются неизменными;
- где формируются данные для UI;
- где заканчивается MVP и начинается будущая архитектура.

Этот документ не заменяет `22_backend_frontend_contracts.md`. Здесь описывается логика потока. В следующем документе будут зафиксированы конкретные методы QWebChannel/API, input/output и error envelope.

## Связанные документы

- `16_feature_list.md`
- `17_implementation_checklist.md`
- `18_architecture_overview.md`
- `19_data_model_concept.md`
- `20_sqlite_schema_design.md`
- `26_definition_of_done.md`
- `diagrams/core_data_flows.md`
- `diagrams/sequence_import.md`
- `diagrams/sequence_metric_run.md`
- `diagrams/sequence_what_if.md`

## Общие правила потоков

### 1. Raw events не меняются

`events.attributes_json` хранит исходные attributes события. Импорт, profiling, semantic binding, metric run, dashboard и scenario run не должны переписывать raw-события.

Если пользователь меняет semantic binding, пересчитываются metric runs, но не events.

Если пользователь запускает What-if, создаются scenario overrides/results, но не изменяется история.

### 2. Все пользовательские операции идут через API Facade

Frontend не обращается к SQLite напрямую.

Цепочка:

```text
Frontend UI
→ QWebChannel
→ Backend API Facade
→ Service layer
→ DB Layer
→ SQLite
```

### 3. Backend возвращает структурированный envelope

Базовый формат:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": []
}
```

`warnings` используются, если операция частично успешна или данные неполны.  
`errors` используются, если операция не может быть завершена.

### 4. UI показывает следующий полезный шаг

Каждый поток должен заканчиваться не только данными, но и состоянием интерфейса:

- после создания проекта → предложить открыть демо или импорт;
- после импорта → перейти к data map;
- после profiling → предложить coverage/binding;
- после binding → предложить metric run;
- после metric run → открыть dashboard;
- после dashboard → показать insights/What-if.

### 5. Future-компоненты не участвуют в MVP-потоках

SDK Lite и Self-hosted Collector могут производить данные совместимого формата, но не являются runtime-зависимостями Desktop 1.5.

Для MVP входная точка — локальный JSONL или demo project.

---

# 1. Поток создания проекта

## Цель

Создать локальный проект анализа, который можно открыть повторно после перезапуска приложения.

## Участники

- Frontend UI;
- Backend API Facade;
- Project Service;
- DB Layer;
- SQLite;
- Settings Service.

## Шаги

```text
пользователь нажимает Create Project
→ UI отправляет название и настройки
→ API валидирует название
→ Project Service создаёт проект
→ DB Layer создаёт запись в projects
→ Settings Service обновляет recent projects
→ API возвращает project summary
→ UI открывает project dashboard
```

## Запись в БД

| Таблица | Действие |
|---|---|
| `projects` | insert |
| `app_settings` | update recent projects |

## Результат для UI

```text
project_id
project_name
created_at
last_opened_at
available_actions
```

## Ошибки

| Ситуация | Поведение |
|---|---|
| пустое имя проекта | показать validation error |
| БД недоступна | показать storage error |
| проект с таким именем уже есть | предложить другое имя или открыть существующий |

---

# 2. Поток открытия проекта

## Цель

Открыть существующий проект и восстановить его рабочее состояние.

## Шаги

```text
пользователь выбирает recent project или файл проекта
→ API проверяет доступность БД
→ Project Service читает projects
→ Import Service читает последний import_run
→ Binding Service читает binding sets
→ Metric Engine читает последние metric_runs
→ API собирает project dashboard state
→ UI показывает доступные действия
```

## Чтение из БД

| Таблица | Действие |
|---|---|
| `projects` | read |
| `import_runs` | read last status |
| `source_files` | read summary |
| `semantic_binding_sets` | read summaries |
| `metric_runs` | read latest runs |
| `scenarios` | read latest scenarios |
| `app_settings` | update recent projects |

## Результат для UI

```text
project summary
last import status
data availability summary
binding summary
latest metric runs
latest scenarios
recommended next action
```

---

# 3. Поток открытия demo project

## Цель

Дать пользователю первый полезный результат без импорта внешних файлов.

## Шаги

```text
пользователь нажимает Open Demo
→ Demo Service проверяет наличие demo data
→ если demo project ещё не создан, создаёт его
→ импортирует demo JSONL и demo parameters
→ применяет preconfigured semantic bindings
→ запускает precomputed или fresh metric run
→ возвращает готовый dashboard state
→ UI открывает dashboard с подсказками
```

## Важное ограничение

Demo project может использовать synthetic data, но это должно быть честно описано в `24_demo_project_spec.md`.

## Запись в БД

| Таблица | Действие |
|---|---|
| `projects` | insert/read |
| `import_runs` | insert |
| `source_files` | insert |
| `entities` | upsert |
| `observations` | upsert |
| `events` | insert |
| `event_attribute_profile` | insert/update |
| `parameter_catalogs` | insert, если demo parameters входят в батч |
| `entity_parameters` | insert, если demo parameters входят в батч |
| `semantic_binding_sets` | insert |
| `semantic_bindings` | insert |
| `metric_runs` | insert |
| `metric_values` | insert |

---

# 4. Поток импорта JSONL

## Цель

Прочитать локальные JSONL-файлы, провалидировать события, сохранить raw-события и подготовить data map.

## Участники

- Frontend UI;
- Backend API Facade;
- Import Service;
- Data Profiler;
- Analysis Coverage Service;
- DB Layer;
- SQLite;
- Local Filesystem.

## Основной поток

```text
пользователь выбирает файл или папку
→ UI отправляет путь в importEvents
→ API проверяет project_id и source path
→ Import Service находит JSONL-файлы
→ Import Service создаёт import_run со status = running
→ для каждого файла создаёт source_file
→ читает строки
→ парсит JSON
→ валидирует минимальный event envelope
→ валидные события нормализует к внутреннему формату
→ upsert entities
→ upsert observations
→ insert events
→ сохраняет ошибки по битым строкам
→ Data Profiler строит/обновляет event_attribute_profile
→ Analysis Coverage Service считает базовое покрытие анализа
→ Import Service завершает import_run
→ API возвращает import report
→ UI показывает report и предлагает открыть data map
```

## Минимальная валидация события

| Поле | Правило |
|---|---|
| `timestamp` | должно существовать и парситься |
| `entity_id` | должно существовать |
| `event_type` | должно существовать |
| `attributes` | должен быть object |
| `observation_id` | желательно; если отсутствует, можно создать auto observation |
| `build_id` | желательно; отсутствие не блокирует импорт |

## Политика частично битого файла

MVP-поведение:

```text
валидные строки импортируются;
битые строки пропускаются;
ошибки сохраняются в import_run.errors_json и source_files;
пользователь видит файл и номер строки;
операция завершается с warnings, если есть валидные события.
```

Если файл полностью невалиден, операция может завершиться как failed, но уже созданный import_run должен содержать диагностический отчёт.

## Порядок событий при импорте

`event_order` назначается по исходному порядку строки внутри `source_file`. Он используется как стабильный tie-breaker, если несколько событий имеют одинаковый или недостаточно точный `timestamp`.

Детерминированный порядок события:

```text
timestamp ASC
→ source_file_id ASC
→ event_order ASC
→ event.id ASC как последний технический tie-breaker
```

## Запись в БД

| Таблица | Действие |
|---|---|
| `import_runs` | insert/update |
| `source_files` | insert/update |
| `entities` | upsert |
| `observations` | upsert |
| `events` | bulk insert |
| `event_attribute_profile` | rebuild/update |
| `analysis_coverage_cache` | P1 cache; для P0 можно считать на лету |

## Транзакции

Импорт должен использовать транзакцию на уровне файла или всего import run.

Рекомендуемая политика для MVP:

```text
import_run создаётся до транзакции;
каждый source_file импортируется в собственной транзакции;
ошибка одного файла не откатывает валидные файлы;
итоговый import_run хранит общий статус и warnings.
```

Это проще для пользователя, чем “одна битая строка убила весь импорт”.

## Результат для UI

```text
import_run_id
source_files_count
read_lines
valid_events
invalid_events
imported_events
created_entities
created_observations
warnings
errors
next_action = "open_data_map"
```

---

# 5. Поток профилирования данных

## Цель

Построить карту импортированных событий, чтобы пользователь понимал структуру данных до настройки semantic bindings.

## Участники

- Data Profiler;
- DB Layer;
- SQLite;
- UI Data Map.

## Основной поток

```text
после импорта или по запросу пользователя
→ Data Profiler читает events по project_id
→ группирует по event_type
→ извлекает keys из attributes_json
→ определяет типы значений
→ считает частоты, null count, numeric/string/boolean count
→ считает min/max для числовых полей
→ сохраняет профиль
→ API возвращает data profile
→ UI показывает data map
```

## Чтение/запись в БД

| Таблица | Действие |
|---|---|
| `events` | read |
| `event_attribute_profile` | insert/update/read |

## Результат для UI

```text
event types
event counts
attribute keys
type distribution
numeric ranges
sample values
warnings
```

## Warnings

| Ситуация | Warning |
|---|---|
| поле имеет смешанные типы | mixed_type_attribute |
| числовое поле частично отсутствует | sparse_numeric_attribute |
| слишком мало событий | low_sample_size |
| нет числовых полей | no_numeric_attributes |
| нет observation_id | auto_observation_used |

---

# 6. Поток проверки analysis coverage

## Цель

Показать, какие классы проблем баланса можно проверить по текущим данным и bindings.

## Основной поток

```text
Data Profiler отдаёт карту данных
→ Analysis Coverage Service читает event types, attributes, bindings и parameters
→ сопоставляет данные с requirements шаблонов
→ формирует статусы coverage
→ API возвращает coverage summary
→ UI показывает available / partial / missing / unsupported
```

## Статусы

| Статус | Значение |
|---|---|
| `available` | можно проверить по текущим данным |
| `partially_available` | часть сигналов есть, часть отсутствует |
| `missing_data` | не хватает обязательных событий/полей |
| `unsupported_in_version` | проблема известна, но не входит в текущую версию |

## P0-поведение

Для P0 coverage можно считать на лету без сохранения в БД.

## P1-поведение

Для P1 результат можно кэшировать в `analysis_coverage_cache`, если проверка окажется дорогой или нужна история coverage.

## Результат для UI

```text
problem_key
problem_label
status
available_signals
missing_signals
related_template_key
explanation
recommended_next_step
```

---

# 7. Поток настройки semantic binding

## Цель

Связать переменные шаблона анализа с конкретными event_type, attributes, filters и aggregation.

## Участники

- Frontend Binding Wizard;
- Backend API Facade;
- Binding Service;
- Data Profiler;
- Metric Template Registry;
- DB Layer;
- SQLite.

## Основной поток

```text
пользователь открывает Binding Wizard
→ UI запрашивает список templates
→ API возвращает templates и required variables
→ UI запрашивает data profile
→ пользователь выбирает template
→ пользователь связывает variables с event_type/attribute/filter/aggregation
→ UI отправляет draft binding на validation
→ Binding Service проверяет типы и полноту
→ API возвращает validation warnings
→ пользователь сохраняет binding set
→ Binding Service пишет semantic_binding_sets и semantic_bindings
→ UI предлагает run metric calculation
```

## Запись в БД

| Таблица | Действие |
|---|---|
| `semantic_binding_sets` | insert/update |
| `semantic_bindings` | insert/update |
| `metric_templates` | read или seed/read, если templates хранятся в БД |

## Validation warnings

| Ситуация | Warning |
|---|---|
| обязательная переменная не связана | missing_required_variable |
| выбранное поле не numeric для numeric variable | incompatible_attribute_type |
| event_type слишком редкий | low_sample_size |
| filters исключают все события | empty_binding_result |
| cost/result имеют разные units | incomparable_units |

## Важное правило

Binding Wizard не должен угадывать смысл данных как окончательную истину. Он может предлагать candidates, но пользователь подтверждает семантику.

---

# 8. Поток запуска metric run

## Цель

Рассчитать значения метрик по выбранному template + semantic binding + scope.

## Участники

- Frontend UI;
- Backend API Facade;
- Binding Service;
- Metric Template Registry;
- Metric Engine;
- DB Layer;
- SQLite.

## Основной поток

```text
пользователь нажимает Run Calculation
→ UI отправляет binding_set_id, template_key и scope
→ API валидирует project_id и binding_set
→ Binding Service читает binding set
→ Template Registry отдаёт formulas и metric definitions
→ Metric Engine создаёт metric_run со status = running
→ Metric Engine читает события по bindings и scope
→ агрегирует переменные по x_index / observation / entity / time window
→ считает формулы
→ применяет safe_div и правила N/A
→ сохраняет metric_values
→ сохраняет warnings и formula/binding snapshots
→ завершает metric_run
→ API возвращает metric_run summary
→ UI открывает dashboard
```

## Чтение/запись в БД

| Таблица | Действие |
|---|---|
| `semantic_binding_sets` | read |
| `semantic_bindings` | read |
| `metric_templates` | read или code registry |
| `events` | read |
| `entity_parameters` | read, если template/what-if требует |
| `metric_runs` | insert/update |
| `metric_values` | insert |

## Формирование x-axis

P0-источники x-axis:

| Источник | Когда использовать |
|---|---|
| `observation_id` | если данные сгруппированы по observation |
| `timestamp` window | если выбран временной ряд |
| `x_index` | технический стабильный индекс после сортировки точек |
| `build_id` | если пользователь сравнивает билды |

Порядок точек должен быть детерминированным:

```text
time window
→ window_start ASC

observation
→ observations.started_at ASC, NULLS LAST
→ observation_id ASC как tie-breaker

entity / event_type / build_id category
→ время первого события ASC
→ stable category key ASC как tie-breaker

после сортировки
→ присвоить x_index = 0..N-1
```

`x_label` — человекочитаемая подпись уже отсортированной точки. Повторный расчёт по тем же данным и scope должен давать тот же порядок `x_index`.

## Calculation warnings

| Ситуация | Поведение |
|---|---|
| деление на ноль | `status = n/a`, warning |
| отсутствует переменная | `status = error` или metric-level warning |
| мало точек | warning, но график строится |
| несопоставимые units для ROI | не считать strict ROI, предложить result_per_cost |
| mixed types | пропустить нечисловые значения с warning |
| пустой result set | metric_run failed или completed_with_warnings |

---

# 9. Поток подготовки dashboard data

## Цель

Отдать UI данные графиков, таблиц и карточек без SQL-логики на frontend.

## Основной поток

```text
UI открывает dashboard или выбирает metric_run
→ API получает getDashboardData
→ Metric Engine / Dashboard Service читает metric_values
→ группирует значения по metric_key и scope
→ добавляет labels, statuses, warnings
→ Insight Engine генерирует или читает insights
→ API возвращает chart datasets и insight cards
→ UI строит Chart.js графики
```

## Чтение из БД

| Таблица | Действие |
|---|---|
| `metric_runs` | read |
| `metric_values` | read |
| `scenarios` | read, если включено сравнение |
| `scenario_results` | read, если есть scenario overlay |

## Результат для UI

```json
{
  "metric_run_id": 1,
  "labels": ["run_001", "run_002", "run_003"],
  "datasets": [
    {
      "metric_key": "net_flow",
      "label": "Чистый поток",
      "data": [10, 5, -2],
      "status": ["ok", "ok", "warning"],
      "warnings": [[], [], ["low_sample_size"]]
    }
  ],
  "insights": []
}
```

## Правило UI

UI не должен молча скрывать `N/A`, warnings и errors. Если точка не рассчитана, пользователь должен понимать почему.

---

# 10. Поток генерации practical insights

## Цель

Сформировать человекочитаемые выводы по рассчитанным метрикам.

## Основной поток

```text
metric_values готовы
→ Insight Engine читает series и warnings
→ применяет rule-based checks
→ формирует insight cards
→ добавляет severity, evidence и recommendation
→ API возвращает insights вместе с dashboard data
```

## Входы Insight Engine

```text
metric_run
metric_values
template metadata
scope
calculation warnings
analysis coverage
optional scenario comparison
```

## Выходы Insight Engine

```text
level
category
title
text
recommendation
metric_keys
evidence
confidence/context notes
```

## Важное правило

Insight не должен звучать увереннее, чем позволяют данные.

Плохая формулировка:

```text
Экономика сломана.
```

Хорошая формулировка:

```text
В выбранных observation чистый поток ресурса остаётся положительным 8 окон подряд.
Это может указывать на профицит или недостаточные sink-механики.
Проверьте источники расхода и лимиты накопления.
```

---

# 11. Поток простого What-if

## Цель

Проверить влияние изменения параметра без изменения исторических raw-событий.

## Участники

- Frontend What-if Panel;
- Backend API Facade;
- What-if Engine;
- Metric Engine;
- Binding Service;
- DB Layer;
- SQLite.

## Основной поток

```text
пользователь открывает What-if panel
→ UI запрашивает доступные параметры
→ What-if Engine читает entity_parameters и binding context
→ UI показывает controllable parameters
→ пользователь выбирает подготовленный P0-сценарий или его единственный controllable parameter
→ пользователь задаёт один override
→ UI запускает сценарий
→ What-if Engine определяет confidence_status
→ если есть точная формула пересчёта, выполняется exact_recalc
→ если формула частичная, выполняется approx_recalc
→ если есть только связь параметра с метрикой, выполняется impact_estimate
→ если модели или данных нет, возвращается insufficient_model/insufficient_data
→ scenario и overrides сохраняются
→ scenario_results сохраняются отдельно от metric_values
→ API возвращает comparison datasets
→ UI показывает историческую и сценарную линии
```

## Запись в БД

| Таблица | Действие |
|---|---|
| `scenarios` | insert/update |
| `scenario_overrides` | insert |
| `scenario_results` | insert |
| `metric_values` | read only |
| `events` | read only |
| `entity_parameters` | read only |

## Confidence statuses

| Статус | Когда использовать |
|---|---|
| `exact_recalc` | есть parameter override, binding и полная формула пересчёта |
| `approx_recalc` | формула есть, но использует допущения |
| `impact_estimate` | связь parameter → event/metric есть, но пересчёт не определён |
| `insufficient_model` | нет dependency rule или формулы |
| `insufficient_data` | не хватает данных для сценарного расчёта |

## Важное ограничение MVP

MVP не предсказывает изменение поведения игрока.

Если изменение цены могло бы заставить игрока не покупать апгрейд, BalanceCraft 1.5 не должен делать вид, что знает это поведение. Он может показать:

```text
при той же истории действий стоимость изменилась бы так-то;
точность: exact_recalc / approx_recalc / impact_estimate;
ограничение: последовательность событий не пересимулируется.
```

---

# 12. Поток ошибок и warnings

## Цель

Сделать диагностику предсказуемой и человекочитаемой.

## Общая цепочка

```text
Service detects problem
→ creates structured warning/error
→ API Facade wraps it into envelope
→ Frontend renders human message
→ technical details доступны только как details/debug
```

## Error object

Рекомендуемый формат:

```json
{
  "code": "missing_required_field",
  "message": "В событии не найдено обязательное поле timestamp.",
  "details": {
    "file": "events.jsonl",
    "line": 42,
    "field": "timestamp"
  }
}
```

## Warning object

```json
{
  "code": "division_by_zero",
  "message": "Метрика не рассчитана: знаменатель равен нулю.",
  "details": {
    "metric_key": "spend_to_income_ratio",
    "x_label": "run_003"
  }
}
```

## Правило

Stack trace не должен быть основным текстом ошибки для пользователя.

---

# 13. Таблица потоков и артефактов

| Flow | Основной input | Основной output | Пишет в БД |
|---|---|---|---|
| Create Project | name/settings | project summary | `projects`, `app_settings` |
| Open Project | project_id/path | project state | `app_settings` |
| Open Demo | demo preset | ready dashboard | many P0 tables |
| Import JSONL | file/folder path | import report | `import_runs`, `source_files`, `entities`, `observations`, `events` |
| Profile Data | project_id | data map | `event_attribute_profile` |
| Analysis Coverage | profile/bindings | coverage summary | optional `analysis_coverage_cache` |
| Save Binding | template + variable mappings | binding set | `semantic_binding_sets`, `semantic_bindings` |
| Run Metric | binding set + scope | metric run summary | `metric_runs`, `metric_values` |
| Get Dashboard | metric_run_id | chart datasets | no required writes |
| Generate Insights | metric series | insight cards | no required writes in P0 |
| Run What-if | scenario overrides | scenario comparison | `scenarios`, `scenario_overrides`, `scenario_results` |

---

# 14. MVP vertical slice

Главная проверка разработки:

```text
SQLite schema
→ create project
→ import one JSONL
→ profile data
→ bind one template
→ calculate metric values
→ draw chart
→ show one insight
```

Расширенный, но всё ещё разумный vertical slice:

```text
+ load demo project
+ show analysis coverage
+ run simple What-if
+ show confidence status
```

---

# 15. Review notes

## RN-1. Гранулярность транзакции импорта

Текущий вариант предлагает транзакцию на уровне файла внутри import run. Это дружелюбнее к частично битым наборам данных, но сложнее в реализации статусов.

Альтернатива: одна транзакция на весь import run. Она проще, но может раздражать пользователя, если один битый файл ломает весь импорт.

## RN-2. Где хранить insights

P0 может генерировать insights на лету по `metric_values`.  
P1 может добавить таблицу `insight_runs` / `insight_cards`, если потребуется история выводов.

Пока отдельная таблица не включается в P0, чтобы не раздувать схему.

## RN-3. Что является source of truth для templates

Есть три варианта:

1. templates только в коде;
2. templates только в БД;
3. builtin templates в коде + snapshot в metric_runs + optional metadata в БД.

Текущая рекомендация: вариант 3.

## RN-4. Scenario results и metric engine

Текущий flow допускает, что What-if Engine использует Metric Engine для пересчёта сценарных значений, но сохраняет результат в `scenario_results`, а не в `metric_values`.

Это сохраняет разделение истории и сценария, но потребует аккуратного кода, чтобы не дублировать формулы.

## RN-5. Analysis coverage на лету или кэш

P0 считает coverage на лету.  
P1 может кэшировать результат, если profiling/coverage станет дорогим.

## RN-6. Import parameters

Полноценный JSON/CSV import параметров — P1 и не является P0-flow. Минимальный What-if использует seeded demo parameters или уже существующие `entity_parameters`.

## RN-7. Progress updates

Для больших импортов и расчётов нужен progress API. Для MVP можно начать с blocking call + статус в UI, но архитектура не должна мешать будущему progress stream/polling.
