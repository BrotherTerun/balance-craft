# FILE: `03_design_docs/25_test_plan.md`
# 25. Test plan и QA checklist

Дата: 2026-07-02  
Статус: рабочий проектный документ

## Назначение

Этот документ фиксирует тестовый план BalanceCraft Desktop 1.5.

Цель test plan — не построить enterprise-QA-машину на три отдела, а защитить портфолио-MVP от наиболее вероятных поломок:

```text
SQLite не создаётся
→ JSONL не импортируется
→ data profile врёт
→ binding сохраняется неправильно
→ metric run считает ложные значения
→ dashboard падает на N/A
→ insight говорит уверенную ерунду
→ What-if меняет историю
→ старый MySQL-зомби вылезает из подвала
```

## Связанные документы

- `../01_pre_design_docs/08_requirements.md`
- `../01_pre_design_docs/09_mvp_scope_timeline.md`
- `../01_pre_design_docs/10_prototype_audit.md`
- `../01_pre_design_docs/12_input_data_formats.md`
- `../01_pre_design_docs/13_design_requirements.md`
- `16_feature_list.md`
- `17_implementation_checklist.md`
- `18_architecture_overview.md`
- `20_sqlite_schema_design.md`
- `21_data_flows.md`
- `22_backend_frontend_contracts.md`
- `23_ui_flow_and_screen_map.md`
- `24_demo_project_spec.md`
- `26_definition_of_done.md`

## QA-позиция BalanceCraft 1.5

BalanceCraft 1.5 — портфолио vertical slice, а не production SaaS. Поэтому тестирование делится на три уровня:

| Уровень | Назначение | Обязателен для 1.5 |
|---|---|---|
| Smoke tests | проверить, что основной путь запускается | да |
| Feature acceptance checks | проверить P0-фичи по критериям готовности | да |
| Regression/edge cases | поймать критичные ошибки данных и расчётов | частично |
| Full automation | покрыть всё автотестами | нет |

Главный критерий: пользователь должен пройти путь от демо/JSONL до графика и insight без ручного SQL, MySQL, внешних сервисов и скрытых правок данных.

## Test data strategy

### Минимальные наборы тестовых данных

```text
examples/test_data/
  demo_forge_happy_path/
    events.jsonl
    parameters.json
  malformed_jsonl/
    broken_lines.jsonl
  missing_numeric_fields/
    events.jsonl
  zero_denominator/
    conversion_events.jsonl
  no_blocking_events/
    events.jsonl
  what_if_basic/
    events.jsonl
    parameters.json
  large_100k/
    events.jsonl
```

### Назначение наборов

| Набор | Что проверяет |
|---|---|
| `demo_forge_happy_path` | полный пользовательский путь на демо-проекте |
| `malformed_jsonl` | частично битые строки, ошибки файла/строки |
| `missing_numeric_fields` | импорт работает, но метрики ограничены |
| `zero_denominator` | `safe_div`, `N/A`, warnings |
| `no_blocking_events` | analysis coverage показывает missing data для bottleneck/action availability |
| `what_if_basic` | сценарий не меняет raw events и historical metric values |
| `large_100k` | грубый performance smoke для SQLite/индексов |

## Общие правила тестирования

1. Каждый тест должен иметь понятный expected result.
2. Raw events не изменяются после импорта.
3. Ошибки backend возвращаются через envelope, а не через stack trace в UI.
4. `warnings` не считаются провалом, если фича корректно показывает ограничение данных.
5. `N/A` лучше ложного числа.
6. Любой runtime-зависимости от MySQL быть не должно.
7. Если тест не автоматизирован, он должен быть описан как ручная проверка.

## P0 smoke scenario

Этот сценарий должен проходить перед любым “считаем, что MVP жив”.

```text
1. Запустить приложение.
2. Открыть demo project.
3. Увидеть dashboard с готовым графиком.
4. Открыть Data Map.
5. Увидеть event types и attributes.
6. Открыть Binding Wizard.
7. Увидеть готовый binding set.
8. Запустить metric calculation.
9. Получить metric run.
10. Увидеть chart dataset.
11. Увидеть хотя бы один practical insight.
12. Открыть What-if panel.
13. Изменить один параметр.
14. Увидеть scenario result и confidence status.
15. Проверить, что historical data не изменились.
```

Expected result:

```text
приложение работает local-only;
SQLite создаётся/открывается;
график строится;
warnings отображаются;
нет MySQL-зависимостей;
нет сетевой отправки данных.
```

## 1. Environment / startup tests

### ENV-001. Запуск без внешней БД

Priority: P0

Steps:

```text
1. Запустить приложение на машине без запущенного MySQL/PostgreSQL.
2. Создать новый проект.
3. Закрыть приложение.
4. Открыть приложение повторно.
5. Открыть созданный проект.
```

Expected:

```text
проект создан;
SQLite-файл создан;
приложение не требует MySQL, Docker, служб Windows или admin rights;
проект открывается после перезапуска.
```

### ENV-002. Local-only smoke

Priority: P0

Steps:

```text
1. Отключить интернет.
2. Запустить приложение.
3. Открыть demo project.
4. Выполнить metric run.
```

Expected:

```text
основной сценарий работает без сети;
нет обязательной регистрации;
нет запросов к внешним аналитическим сервисам.
```

## 2. SQLite schema tests

### DB-001. Schema initialization

Priority: P0

Steps:

```text
1. Удалить тестовую SQLite DB.
2. Запустить schema init.
3. Проверить наличие P0-таблиц.
4. Повторить schema init.
```

Expected:

```text
таблицы созданы;
повторный init не ломает БД;
foreign keys включены через PRAGMA;
ошибки возвращаются человекочитаемо.
```

Минимальные P0-таблицы:

```text
projects
import_runs
source_files
entities
observations
events
event_attribute_profile
metric_templates
semantic_binding_sets
semantic_bindings
metric_runs
metric_values
parameter_catalogs
entity_parameters
scenarios
scenario_overrides
scenario_results
```

### DB-002. Foreign key and transaction sanity

Priority: P0

Steps:

```text
1. Начать импорт файла.
2. Спровоцировать ошибку в середине записи.
3. Проверить состояние import_run/source_files/events.
```

Expected:

```text
БД не остаётся в полузаписанном невалидном состоянии;
ошибка сохранена в import report;
следующий импорт возможен без ручной чистки.
```

### DB-003. Index existence smoke

Priority: P0

Проверить наличие индексов:

```text
idx_events_project_time
idx_events_project_entity
idx_events_project_observation
idx_events_project_type
idx_events_project_build
idx_metric_values_run_key
idx_parameters_project_entity
idx_parameters_project_key
```

Expected:

```text
индексы созданы миграцией/schema init;
типовые dashboard/profile queries не требуют заведомо полного скана на малом наборе.
```

## 3. Project lifecycle tests

### PROJ-001. Create project

Priority: P0

Steps:

```text
1. Вызвать createProject.
2. Проверить response envelope.
3. Проверить запись в projects.
4. Проверить recent projects.
```

Expected:

```text
success = true;
project_id возвращён;
проект доступен после перезапуска;
ошибки пути/доступа возвращаются через errors[].
```

### PROJ-002. Open demo project

Priority: P0

Steps:

```text
1. На первом экране открыть demo project.
2. Проверить наличие событий, bindings, metric runs или готового сценария расчёта.
3. Открыть dashboard.
```

Expected:

```text
demo открывается без внешних файлов;
пользователь видит пользу до ручной настройки;
UI не требует SQL, JSON или знания БД.
```

## 4. JSONL import tests

### IMP-001. Happy path import

Priority: P0

Input:

```text
valid JSONL with timestamp/entity_id/event_type/attributes
```

Expected:

```text
import_run создан;
source_file создан;
events записаны;
entities upserted;
observations upserted или auto-created;
import report показывает counts.
```

### IMP-002. Partially malformed file

Priority: P0

Input:

```text
JSONL с валидными и битыми строками
```

Expected:

```text
валидные события импортированы;
битые строки пропущены;
errors содержат file_path/source_line_number;
импорт не падает целиком, если есть валидные события.
```

### IMP-003. Missing optional fields

Priority: P0

Input:

```text
события без observation_id/build_id/schema_version
```

Expected:

```text
события импортируются;
observation auto-created или помечен default observation;
warnings объясняют ограничения анализа.
```

### IMP-004. Invalid required fields

Priority: P0

Проверить отсутствие:

```text
timestamp
entity_id
event_type
attributes
```

Expected:

```text
строка не импортируется;
ошибка указывает поле, файл и строку;
валидные соседние строки не страдают.
```

## 5. Data profiling tests

### PROF-001. Event type counts

Priority: P0

Steps:

```text
1. Импортировать demo events.
2. Запустить getDataProfile.
3. Проверить event_type counts.
```

Expected:

```text
каждый event_type показан;
counts совпадают с входным файлом;
empty profile не возникает при наличии events.
```

### PROF-002. Attribute typing

Priority: P0

Проверить поля:

```text
number
string
boolean
null
mixed
```

Expected:

```text
profile показывает типы;
numeric ranges есть для числовых fields;
mixed fields помечены warning;
sample values не ломают UI.
```

## 6. Analysis coverage tests

### COV-001. P0 available coverage

Priority: P0

Input:

```text
события resource_gained/resource_spent/stock_changed/upgrade_purchased
```

Expected:

```text
flow balance available или partially_available;
stock dynamics available или partially_available;
conversion efficiency available или partially_available;
missing_signals пустой или объяснимый.
```

### COV-002. Missing blocking events

Priority: P0

Input:

```text
нет operation_blocked/action_blocked/block_reason
```

Expected:

```text
action availability/bottleneck отмечены missing_data или unsupported_in_version;
UI объясняет, какие events/fields нужны;
другие классы анализа не блокируются.
```

### COV-003. Unsupported in version

Priority: P1

Expected:

```text
P2-проблемы не выглядят как ошибка пользователя;
статус unsupported_in_version отделён от missing_data.
```

## 7. Semantic binding tests

### BIND-001. Save binding set

Priority: P0

Steps:

```text
1. Выбрать template flow_balance.
2. Привязать flow_in к attributes.amount where event_type=resource_gained.
3. Привязать flow_out к attributes.amount where event_type=resource_spent.
4. Сохранить binding set.
5. Перезапустить приложение.
6. Открыть binding set.
```

Expected:

```text
binding set сохранён;
variables восстановлены;
filters восстановлены;
aggregation восстановлена;
UI показывает тот же mapping.
```

### BIND-002. Incompatible field warning

Priority: P0

Input:

```text
пользователь выбирает string field для numeric variable
```

Expected:

```text
UI/backend возвращают warning или validation error;
metric run не считает ложное число;
пользователь понимает, что выбрать другое поле.
```

### BIND-003. Binding snapshot on metric run

Priority: P0

Steps:

```text
1. Создать binding set.
2. Запустить metric run.
3. Изменить binding set.
4. Проверить старый metric run.
```

Expected:

```text
старый metric run хранит binding_snapshot;
старые результаты не переинтерпретируются молча.
```

## 8. Metric engine tests

### MET-001. Flow balance calculation

Priority: P0

Expected metrics:

```text
net_flow = sum(flow_in) - sum(flow_out)
spend_to_income_ratio = safe_div(sum(flow_out), sum(flow_in))
```

Expected:

```text
значения совпадают с ручным расчётом;
metric_values записаны;
status = ok для валидных точек.
```

### MET-002. Stock dynamics calculation

Priority: P0

Expected:

```text
change/rate/plateau flags считаются по выбранным windows;
пороги visible или snapshoted;
малое количество точек создаёт warning.
```

### MET-003. Conversion efficiency calculation

Priority: P0

Expected:

```text
result_per_cost считается только при cost != 0;
cost_per_result считается только при result != 0;
ROI не называется ROI без comparable value fields.
```

### MET-004. Operation intensity calculation

Priority: P0

Expected:

```text
count/action over duration считается;
нулевая duration возвращает N/A/warning;
UI не падает.
```

### MET-005. safe_div / N/A policy

Priority: P0

Input:

```text
zero denominator cases
```

Expected:

```text
значение = null или N/A representation;
status = n/a или warning;
warnings_json содержит причину;
никаких делений на 1 ради красоты графика.
```

## 9. Dashboard and visualization tests

### DASH-001. Dashboard dataset contract

Priority: P0

Steps:

```text
1. Запустить metric run.
2. Вызвать getDashboardData.
3. Проверить labels/datasets/status/warnings.
```

Expected:

```text
response соответствует contract;
несколько datasets могут рендериться;
N/A точки не ломают график;
empty state понятен.
```

### DASH-002. Scope selector

Priority: P0

Проверить срезы:

```text
project
entity_id
observation_id
observation_type
event_type
build_id
```

Expected:

```text
нет обязательного player selector;
player может быть только demo entity_type;
названия в UI используют scope/entity/observation.
```

## 10. Insight engine tests

### INS-001. Insight evidence

Priority: P0

Expected:

```text
каждый insight имеет severity/category/title/text/recommendation/evidence/metric_keys;
evidence ссылается на реальные metric values/windows;
нет уверенного вывода без данных.
```

### INS-002. Missing data insight behavior

Priority: P0

Input:

```text
недостаточно точек или пропущены variables
```

Expected:

```text
insight либо не создаётся, либо создаётся как warning/diagnostic;
не появляется фальшивое “баланс плохой”, если данных нет.
```

## 11. What-if tests

### WIF-001. Create scenario

Priority: P0/P1

Steps:

```text
1. Выбрать base_metric_run.
2. Создать scenario.
3. Добавить parameter override.
4. Запустить runScenario.
```

Expected:

```text
scenario записан;
scenario_overrides записаны;
scenario_results записаны;
confidence_status возвращён;
historical metric values не изменены.
```

### WIF-002. Exact recalculation status

Priority: P1

Conditions:

```text
есть parameter override;
есть binding;
есть formula/recalc rule;
sequence событий не меняется.
```

Expected:

```text
confidence_status = exact_recalc.
```

### WIF-003. Impact estimate status

Priority: P1

Conditions:

```text
параметр связан с events/metrics;
нет правила пересчёта.
```

Expected:

```text
confidence_status = impact_estimate;
UI не обещает точную симуляцию.
```

### WIF-004. Insufficient model/data statuses

Priority: P1

Expected:

```text
нет dependency/recalc rule → insufficient_model;
нет данных для пересчёта → insufficient_data;
оба статуса объясняются пользователю.
```

## 12. Demo project acceptance

### DEMO-001. Demo first impression

Priority: P0

Expected:

```text
demo project открывается с первого экрана;
показывает минимум один готовый график;
показывает data map;
показывает binding examples;
показывает минимум один insight;
не требует пользователя импортировать свои файлы.
```

### DEMO-002. Demo Forge expected problems

Priority: P0

Проверить, что demo показывает минимум:

```text
resource surplus/deficit signal;
conversion efficiency issue;
progression/stock dynamic signal;
operation intensity или pacing signal.
```

Expected:

```text
insights связаны с реальными demo metrics;
проблемы не выглядят как произвольный текст;
What-if демонстрирует изменение параметра без обещания полной симуляции.
```

## 13. Error handling and UX states

### ERR-001. Backend error envelope

Priority: P0

Expected:

```json
{
  "success": false,
  "data": null,
  "warnings": [],
  "errors": [
    {
      "code": "...",
      "message": "...",
      "details": {}
    }
  ]
}
```

UI expected:

```text
показывает user-facing message;
не показывает raw traceback как основной текст;
предлагает следующий шаг, если он есть.
```

### ERR-002. Empty states

Priority: P0

Проверить состояния:

```text
нет проектов
нет событий
нет числовых полей
нет bindings
нет metric runs
нет parameters для What-if
```

Expected:

```text
каждое состояние объясняет, что делать дальше;
пользователь не упирается в пустой экран.
```

## 14. Privacy and local-first checks

### PRIV-001. No outbound analytics

Priority: P0

Expected:

```text
Desktop не отправляет raw events наружу;
нет обязательного cloud endpoint;
SDK/Collector не требуются для MVP;
README/privacy docs честно описывают local-only режим.
```

### PRIV-002. Forbidden default fields

Priority: P1

Проверить, что demo/SDK-like samples не используют по умолчанию:

```text
email
real player name
open SteamID
IP as analytic payload
payment data
chat/user text
precise geolocation
```

## 15. Legacy grep checklist

### LEG-001. Runtime MySQL cleanup

Priority: P0

Перед признанием MVP живым выполнить grep по runtime-коду.

Запрещено в runtime:

```text
mysql.connector
DB_CONFIG
root
2256
monitor_rpg_model
INFORMATION_SCHEMA
CREATE DATABASE
players as required core table
sessions as required core table
items as required core table
skills as required core table
```

Допустимо:

```text
упоминания в ../01_pre_design_docs/10_prototype_audit.md;
legacy migration notes;
comments в migration checklist, если они не выполняются runtime-кодом.
```

### LEG-002. UI terminology cleanup

Priority: P0

Проверить UI-тексты:

```text
Player selector → scope/entity selector
Session → observation, если речь о ядре
RPG progression analyzer → balance analysis tool
```

Expected:

```text
жанровые термины остаются только в demo context;
ядро и общие экраны говорят universal language.
```

## 16. Packaging smoke

### PACK-001. Fresh machine smoke

Priority: P1

Steps:

```text
1. Собрать приложение.
2. Запустить в чистой директории.
3. Открыть demo.
4. Импортировать test JSONL.
5. Закрыть/открыть повторно.
```

Expected:

```text
запуск не требует исходников рядом, кроме ожидаемых ресурсов;
пути работают;
SQLite создаётся;
demo доступен;
ошибки файлов понятны.
```

## 17. Performance smoke

### PERF-001. 100k events import/profile

Priority: P1

Rough target:

```text
100 000 events импортируются и профилируются без зависания UI навсегда.
```

Expected:

```text
операция завершается;
progress/status показывается, если реализован;
приложение остаётся пригодным для дальнейшего анализа;
индексы не забыты.
```

Этот тест не задаёт строгий SLA для MVP. Он нужен, чтобы не сделать продукт, который умирает на первом нормальном логе.

## 18. Regression checklist before each batch of implementation

Перед переходом к следующей фазе разработки проверять:

```text
[ ] приложение запускается
[ ] demo project открывается
[ ] JSONL import работает
[ ] data profile строится
[ ] binding set сохраняется
[ ] metric run создаётся
[ ] dashboard получает dataset
[ ] insight показывается
[ ] N/A не ломает график
[ ] What-if, если включён, не меняет историю
[ ] legacy grep не нашёл runtime MySQL
```

## Acceptance matrix для BalanceCraft 1.5

| Область | Минимум для Done |
|---|---|
| Startup | приложение запускается без внешней БД |
| SQLite | schema init работает, P0 tables есть |
| Project | create/open/demo работают |
| Import | valid JSONL импортируется, broken lines диагностируются |
| Profile | event types, attributes, types, samples видны |
| Coverage | базовые available/missing statuses видны |
| Binding | P0 binding set сохраняется и переоткрывается |
| Metrics | 2–4 P0 templates считаются |
| Correctness | `safe_div`/`N/A`/warnings работают |
| Dashboard | chart dataset строится |
| Insights | минимум один insight с evidence |
| What-if | если включён, есть confidence status и no-history-mutation |
| Demo | первый запуск показывает пользу |
| Privacy | local-only, без скрытой отправки данных |
| Legacy | MySQL не нужен runtime |

## Что не тестируем в MVP

В BalanceCraft 1.5 не требуется полноценное тестирование:

- SDK Lite;
- Self-hosted Collector;
- BalanceCraft Cloud;
- external simulation adapter;
- полноценного formula editor;
- multi-user collaboration;
- production security hardening;
- сложной миграции старых пользовательских БД.

## Review notes

Вопросы для общего ревью после сборки проектировочного комплекта:

1. Достаточно ли test data наборов или нужен отдельный `../README.md`?
2. Нужно ли делать `large_100k` обязательным для портфолио-MVP или оставить P1 smoke?
3. Должен ли What-if быть обязательным в acceptance matrix, если сроки начнут гореть?
4. Нужно ли выделять automated tests отдельно в `../README.md` после начала реализации?
5. Хватит ли grep checklist или нужен отдельный legacy CI-check script?

## Главное правило

Тестовый план считается полезным, если он защищает vertical slice:

```text
SQLite schema
→ import JSONL
→ profile data
→ bind template
→ calculate metric values
→ draw chart
→ show insight
→ optional simple What-if
```

Если тест не помогает защитить этот путь, он может подождать.
