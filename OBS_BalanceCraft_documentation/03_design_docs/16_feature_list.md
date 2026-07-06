---
title: 16. Feature list
status: draft
version: 0.1
date: 2026-07-02
tags:
  - balancecraft
  - design
  - mvp
  - feature-list
---

# 16. Feature list

## Назначение

Этот документ фиксирует рабочий список функций BalanceCraft 1.5 перед началом рефакторинга и разработки.

`08_requirements.md` описывает требования подробно. Этот файл нужен как более прикладная карта scope: что делаем, что можно резать, от чего зависит каждая функция и как понять, что она готова.

Главное правило:

```text
Feature list управляет разработкой.
Requirements объясняют, почему функция нужна и какие требования она закрывает.
Implementation checklist превращает feature list в порядок работ.
```

## Приоритеты

| Приоритет | Значение |
|---|---|
| P0 | Обязательно для BalanceCraft Desktop 1.5 |
| P1 | Желательно для портфолио-версии, если P0 не горит |
| P2 | После MVP / следующий этап |
| P3 | Будущие версии |

## Статусы

| Статус | Значение |
|---|---|
| `planned` | Запланировано, но работа не начата |
| `in_progress` | В работе |
| `blocked` | Заблокировано зависимостью или нерешённым вопросом |
| `done` | Реализовано и прошло DoD |
| `cut` | Вырезано из текущего scope |
| `deferred` | Сознательно перенесено на будущую версию |

## Правила scope

1. P0 нельзя вырезать без замены, которая сохраняет рабочий vertical slice.
2. P1 режется первым, если P0 начинает расползаться.
3. P2/P3 не реализуются до готового Desktop vertical slice.
4. Фича не считается готовой, если она работает только через старую MySQL/RPG-модель.
5. Пользовательская ценность важнее красивой внутренней полноты.
6. Любая функция, которая может создать false-аналитику, обязана показывать ограничения, warnings или confidence status.

## P0 vertical slice

Минимальная цепочка, ради которой существует BalanceCraft 1.5:

```text
запуск Desktop без MySQL
→ открыть demo project или создать проект
→ импортировать JSONL
→ увидеть data map
→ настроить semantic binding
→ рассчитать metric run
→ увидеть chart dashboard
→ увидеть practical insight
→ понять, какие данные/проблемы покрыты анализом
→ открыть подготовленный What-if
→ изменить один seeded parameter
→ увидеть impact estimate или узкий deterministic recalculation с confidence status
```

Минимальный What-if входит в P0 BalanceCraft 1.5. Его границы жёсткие: Level 1 impact estimate + один узкий детерминированный Level 2 сценарий с одним override и явным правилом пересчёта. Generic Level 2, полноценный import параметров и управление множеством сценариев остаются P1.

---

# 1. Project management и app shell

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-PROJ-01 | Создание проекта | P0 | planned | SQLite core | Пользователь создаёт проект без ручного SQL; проект появляется в списке recent projects | Нельзя резать |
| F-PROJ-02 | Открытие проекта | P0 | planned | SQLite core, project metadata | Проект открывается после перезапуска приложения; ошибки открытия понятны человеку | Нельзя резать |
| F-PROJ-03 | Demo project entry | P0 | planned | Demo data, seed/import flow | На стартовом экране есть путь к демо; демо открывается без внешних файлов | Нельзя резать |
| F-PROJ-04 | Recent projects | P1 | planned | app_settings/project service | Последние проекты отображаются и открываются | Можно упростить до списка путей |
| F-PROJ-05 | Project settings | P1 | planned | project service | У проекта есть базовые settings_json/default_build_id | Можно оставить только техническое хранение без UI |

## Комментарий

Экран проекта должен поддерживать главный UX-сценарий: пользователь быстро открывает демо или создаёт проект и не видит SQL, MySQL, root-пароли и прочий гоблинский быт.

---

# 2. SQLite и DB layer

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-DB-01 | SQLite runtime | P0 | planned | schema design | Приложение работает без MySQL/PostgreSQL/Docker; БД создаётся автоматически | Нельзя резать |
| F-DB-02 | Единый DB layer | P0 | planned | SQLite runtime | Все обращения к БД идут через один слой; включён `PRAGMA foreign_keys = ON` | Нельзя резать |
| F-DB-03 | Schema initialization | P0 | planned | SQLite runtime | При первом запуске создаются P0-таблицы; повторный init не ломает БД | Нельзя резать |
| F-DB-04 | Transactions for import/calculation | P0 | planned | DB layer | Частично упавший импорт/расчёт не оставляет проект в невалидном состоянии | Нельзя резать |
| F-DB-05 | Schema migrations mechanism | P1 | planned | schema initialization | Есть механизм идемпотентных миграций поверх `schema_migrations` | В раннем MVP можно оставить только P0-таблицу `schema_migrations` как version ledger и один init script |
| F-DB-06 | Basic indexes | P0 | planned | schema design | Есть индексы для project/time/entity/observation/event_type/metric_run | Нельзя резать, но набор можно минимизировать |
| F-DB-07 | WAL/устойчивость | P1 | planned | DB layer | Рассмотрен WAL; нет потери данных при обычном закрытии | Можно отложить |

## Комментарий

SQLite — не “просто поменять коннектор”. Это смена runtime-модели продукта. После этой фичи BalanceCraft должен перестать быть учебным прототипом с внешней БД и стать нормальным local-first desktop-инструментом.

---

# 3. Import service

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-IMP-01 | Выбор JSONL-файла или папки | P0 | planned | app shell, frontend bridge | Пользователь выбирает `.jsonl` файл или папку; система находит файлы | Нельзя резать |
| F-IMP-02 | JSONL parser | P0 | planned | import service | Каждая строка парсится как отдельное событие; битые строки не валят весь импорт | Нельзя резать |
| F-IMP-03 | Event validation | P0 | planned | input format rules | Проверяются `timestamp`, `entity_id`, `event_type`, `attributes` | Нельзя резать |
| F-IMP-04 | Import runs | P0 | planned | SQLite schema | Каждый импорт создаёт `import_run`; отчёт восстанавливается после перезапуска | Нельзя резать |
| F-IMP-05 | Source files traceability | P0 | planned | SQLite schema | Для события хранится source_file и line number | Нельзя резать |
| F-IMP-06 | Entities/observations upsert | P0 | planned | SQLite schema | Сущности и окна наблюдения создаются/обновляются без жанровой логики | Нельзя резать |
| F-IMP-07 | Human-readable import report | P0 | planned | import service, frontend | Показаны строки, валидные/битые события, warnings, errors | Нельзя резать |
| F-IMP-08 | CSV import for parameters | P1 | planned | parameter model | Можно импортировать справочник параметров из CSV | Резать первым, если горит P0 |
| F-IMP-09 | JSON parameter catalog import | P1 | planned | parameter model | Можно импортировать JSON-каталог параметров | Можно заменить демо-seed данными |

## Комментарий

Импорт не должен “понимать игру”. Он должен аккуратно загрузить события, сохранить raw attributes и подготовить почву для поздней семантики.

---

# 4. Data profiling и data map

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-PROF-01 | Event type counts | P0 | planned | imported events | UI показывает список `event_type` и количество событий | Нельзя резать |
| F-PROF-02 | Attribute discovery | P0 | planned | imported events | UI показывает найденные `attributes` по event_type | Нельзя резать |
| F-PROF-03 | Attribute type profiling | P0 | planned | imported events | Для поля показаны numeric/string/boolean/null counts | Нельзя резать |
| F-PROF-04 | Numeric ranges | P0 | planned | attribute profiling | Для числовых полей показаны min/max | Нельзя резать |
| F-PROF-05 | Sample values | P0 | planned | attribute profiling | Для полей показаны примеры значений | Нельзя резать |
| F-PROF-06 | Dirty data warnings | P0 | planned | attribute profiling | Смешанные типы и пропуски помечаются warning | Нельзя резать |
| F-PROF-07 | Materialized profile table | P0 | planned | event_attribute_profile | Профиль сохраняется в `event_attribute_profile` после импорта/перепрофилирования и используется Data Map / Binding Wizard | Таблицу не режем; при необходимости можно пересчитывать содержимое |

## Комментарий

Data map — первая точка, где пользователь понимает, что он вообще импортировал. Без неё Binding Wizard превращается в гадание на JSON-кишках.

---

# 5. Analysis coverage

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-COV-01 | P0 coverage on the fly | P0 | planned | data profile, templates | Система показывает, можно ли проверить дефицит/профицит/инфляцию/плато/конверсию | Нельзя резать |
| F-COV-02 | Missing data explanation | P0 | planned | coverage rules | Для недоступной проблемы указано, каких событий/полей не хватает | Нельзя резать |
| F-COV-03 | Partial availability | P1 | planned | coverage rules | Статус `partially_available` показывает неполное покрытие | Можно упростить до available/missing |
| F-COV-04 | Coverage cache | P1 | planned | analysis_coverage_cache | Результат можно кэшировать в БД | Можно считать на лету |
| F-COV-05 | P1/P2 problem coverage | P1 | planned | extended templates | Coverage показывает bottleneck, dead content, reward pacing и т.д. | Можно отложить |

## Комментарий

Coverage нужен не для красоты. Это страховка от false-аналитики: система честно говорит, что может проверить, а где данных нет.

---

# 6. Semantic Binding Wizard

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-BIND-01 | Template selection | P0 | planned | template registry | Пользователь выбирает шаблон анализа | Нельзя резать |
| F-BIND-02 | Variable-to-field binding | P0 | planned | data profile | Пользователь связывает переменные шаблона с fields/source paths | Нельзя резать |
| F-BIND-03 | Event type filters | P0 | planned | data profile | Для переменной задаются event_type filters | Нельзя резать |
| F-BIND-04 | Aggregation selection | P0 | planned | metric engine | Пользователь выбирает sum/count/mean/etc. там, где применимо | Нельзя резать, но можно ограничить набор |
| F-BIND-05 | Labels for metrics | P0 | planned | template registry | Пользователь может задать/подтвердить названия метрик | Можно упростить до default labels |
| F-BIND-06 | Binding validation | P0 | planned | data profile | UI предупреждает о несовместимых типах и пропусках | Нельзя резать |
| F-BIND-07 | Save/load binding | P0 | planned | SQLite schema | Binding сохраняется и открывается после перезапуска | Нельзя резать |
| F-BIND-08 | Binding snapshot in metric run | P0 | planned | metric engine | Metric run сохраняет snapshot binding | Нельзя резать |
| F-BIND-09 | Auto-suggestions | P2 | deferred | profiling heuristics | Система предлагает вероятные связи | Не входит в 1.5 |

## Комментарий

Binding Wizard — сердце BalanceCraft. Именно он превращает “нейтральные события” в осмысленный анализ, не заставляя ядро притворяться, что все игры — RPG с игроком, сессией и опытом.

---

# 7. Metric templates

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-TPL-01 | Template registry | P0 | planned | metric engine | В системе есть реестр шаблонов с variables/formulas/labels | Нельзя резать |
| F-TPL-02 | Баланс потоков | P0 | planned | binding, metric engine | Считаются net flow и ratio расход/доход с `safe_div` | Нельзя резать |
| F-TPL-03 | Динамика запаса | P0 | planned | binding, metric engine | Считается изменение/темп/плато по stock_value или gain/loss | Желательно оставить |
| F-TPL-04 | Эффективность конверсии | P0 | planned | binding, metric engine | Считается result_per_cost/cost_per_result без ложного ROI | Желательно оставить |
| F-TPL-05 | Интенсивность операций | P0 | planned | binding, metric engine | Считается count/duration и/или reward/duration | Можно отложить, если нужны только 2–3 шаблона |
| F-TPL-06 | Давление стоимости | P1 | planned | operation/parameter data | Считается cost pressure и availability margin | Можно отложить |
| F-TPL-07 | Доступность действий | P1 | planned | attempt/success/blocked events | Считаются success/block rates | Можно отложить |
| F-TPL-08 | Использование контента | P1 | planned | usage events | Считаются usage share и low-usage signals | Можно отложить |
| F-TPL-09 | Ритм наград | P1 | planned | reward timestamps | Считаются intervals/frequency/variance | Можно отложить |
| F-TPL-10 | Пользовательские формулы | P2 | deferred | safe expression layer | Пользователь пишет формулы в ограниченном expression language | Не входит в 1.5 |

## Комментарий

Целевой набор BalanceCraft 1.5 — 4 P0-шаблона. В аварийном 48-часовом режиме можно временно запустить vertical slice на 2–3 шаблонах, но такую сборку нельзя называть полной реализацией заявленного MVP 1.5. В документации и UI нельзя обещать поддержку проблемы баланса, если соответствующий шаблон не реализован.

---

# 8. Metric engine

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-MET-01 | Run metric calculation | P0 | planned | bindings, templates, DB layer | Пользователь запускает расчёт по выбранному шаблону | Нельзя резать |
| F-MET-02 | Scope support | P0 | planned | data model | Поддержан минимум весь проект, entity_id, observation_id, event_type, build_id | Нельзя резать, но можно начать с whole project + observation |
| F-MET-03 | Metric runs | P0 | planned | SQLite schema | Каждый расчёт сохраняется как `metric_run` | Нельзя резать |
| F-MET-04 | Metric values | P0 | planned | SQLite schema | Значения сохраняются в `metric_values` со status/warnings | Нельзя резать |
| F-MET-05 | Formula snapshot | P0 | planned | template registry | Metric run хранит snapshot формул | Нельзя резать |
| F-MET-06 | Safe division policy | P0 | planned | formula execution | Деление на ноль возвращает `N/A`/warning, а не подставляет 1 | Нельзя резать |
| F-MET-07 | Calculation warnings | P0 | planned | metric engine | Warnings сохраняются или возвращаются API | Нельзя резать |
| F-MET-08 | Repeat calculation | P0 | planned | metric runs | Расчёт можно повторить без повторного импорта | Нельзя резать |
| F-MET-09 | Compare builds | P1 | planned | build_id scope | Можно сравнить metric runs по build_id | Можно отложить |

## Комментарий

Metric engine должен работать поверх semantic bindings, а не поверх старых `session_metrics`. Старые формулы могут быть источником опыта, но не ядром.

---

# 9. Dashboard и визуализация

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-DASH-01 | Metric run selector | P0 | planned | metric runs | Пользователь выбирает запуск расчёта | Нельзя резать |
| F-DASH-02 | Scope selector | P0 | planned | metric values | Старый “Игрок” заменён на универсальный срез | Нельзя резать |
| F-DASH-03 | Chart datasets | P0 | planned | dashboard API | UI получает labels/datasets/status/warnings в стабильном формате | Нельзя резать |
| F-DASH-04 | Chart rendering | P0 | planned | frontend, Chart.js | График строится по выбранным метрикам | Нельзя резать |
| F-DASH-05 | N/A/warnings visibility | P0 | planned | metric values | `N/A` и warnings не скрываются | Нельзя резать |
| F-DASH-06 | Multiple metrics | P0 | planned | chart rendering | Можно показать несколько рядов | Можно упростить до 1–2 рядов |
| F-DASH-07 | Minimal scenario comparison overlay | P0 | planned | scenario results | Для подготовленного P0-сценария история и сценарий показаны на одном графике или эквивалентном сравнении | Нельзя резать вместе с минимальным What-if |

## Комментарий

Dashboard должен быть достаточно простым, чтобы показать ценность, и достаточно честным, чтобы не скрывать проблемы данных.

---

# 10. Practical insights

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-INS-01 | Insight engine interface | P0 | planned | metric datasets | Модуль принимает ряды и возвращает структурированные insights | Нельзя резать |
| F-INS-02 | Basic P0 insights | P0 | planned | P0 templates | Есть выводы для дефицита/профицита/плато/конверсии/волатильности по реализованным шаблонам | Нельзя резать, но набор зависит от шаблонов |
| F-INS-03 | Evidence field | P0 | planned | metric values | Каждый insight содержит основание вывода | Нельзя резать |
| F-INS-04 | Severity level | P0 | planned | insight rules | Каждый insight имеет уровень важности | Нельзя резать |
| F-INS-05 | Recommendation text | P0 | planned | insight rules | Каждый insight даёт практическую рекомендацию | Нельзя резать |
| F-INS-06 | Scenario insights | P1 | planned | What-if | Insight по сценарию учитывает confidence status | Можно отложить |

## Комментарий

Insight без evidence — это не аналитика, а гороскоп для геймдизайнера. Не делаем так.

---

# 11. Simple What-if

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-WI-01 | Seeded parameter storage | P0 | planned | SQLite schema | Demo parameters и уже существующие `entity_parameters` доступны отдельно от raw events | Полноценный import можно резать, storage — нет |
| F-WI-02 | Prepared single-override scenario | P0 | planned | parameters, metric runs | Один подготовленный сценарий применяет один fixed/multiplier override | Нельзя резать из полной 1.5 |
| F-WI-03 | Generic scenario management | P1 | planned | scenario schema | Пользователь создаёт произвольные сценарии и несколько overrides | Резать первым |
| F-WI-04 | Level 1 impact estimate | P0 | planned | bindings, parameters | Система показывает связанные события, bindings и метрики | Нельзя резать |
| F-WI-05 | Narrow deterministic Level 2 recalculation | P0 | planned | metric engine, explicit dependency rule | Один подготовленный сценарий пересчитывает известные значения при неизменной sequence событий | Не расширять до generic engine в P0 |
| F-WI-06 | Confidence status | P0 | planned | what-if rules | Result показывает `exact_recalc/approx_recalc/impact_estimate/insufficient_*` и ограничение модели | Нельзя резать |
| F-WI-07 | Separate scenario results | P0 | planned | scenario schema | Сценарные результаты не изменяют raw events и historical metric values | Нельзя резать |
| F-WI-08 | JSON/CSV parameter import | P1 | planned | parameter catalogs | Пользователь импортирует параметры вне demo seed | После P0 |

## Комментарий

P0 What-if — не универсальный симулятор. Он обязан доказать продуктовую цепочку `реальный параметр → явное влияние/пересчёт → сравнение → confidence status` на одном подготовленном сценарии. Generic Level 2, multiple scenarios и полноценный parameter import остаются P1.

---

# 12. Demo project

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-DEMO-01 | Demo scenario design | P0 | planned | feature list, templates | Описана условная игра, события, параметры, ожидаемые проблемы | Нельзя резать |
| F-DEMO-02 | Demo JSONL logs | P0 | planned | input format | Есть импортируемые демо-логи | Нельзя резать |
| F-DEMO-03 | Demo project seed/import | P0 | planned | import/project service | Демо открывается с первого экрана | Нельзя резать |
| F-DEMO-04 | Demo bindings | P0 | planned | binding service | В демо есть готовые semantic bindings или walkthrough их настройки | Нельзя резать |
| F-DEMO-05 | Demo metric runs | P0 | planned | metric engine | В демо можно получить график без внешних файлов | Нельзя резать |
| F-DEMO-06 | Demo insights | P0 | planned | insight engine | В демо видны 2–3 понятные проблемы баланса | Нельзя резать |
| F-DEMO-07 | Demo What-if scenario | P0 | planned | What-if | Подготовленный single-override сценарий показывает изменение реального параметра, comparison и confidence status | Нельзя резать из полной 1.5 |

## Комментарий

Демо — не приложение второго сорта. Для портфолио оно почти важнее, чем поддержка десяти экзотических кейсов. Без демо пользователь видит не продукт, а конструктор самолёта в разобранном виде.

---

# 13. Packaging, README и портфолио

| ID | Feature | Priority | Status | Depends on | Acceptance criteria | Cut rule |
|---|---|---|---|---|---|---|
| F-PACK-01 | Root README update | P1 | planned | demo project | README объясняет продукт за 1–2 минуты | Можно сделать минимально |
| F-PACK-02 | Quick start | P1 | planned | packaging/demo | Есть путь “скачал → запустил → открыл демо” | Желательно оставить |
| F-PACK-03 | Screenshots | P1 | planned | working UI | Есть 2–4 скриншота ключевых экранов | Можно заменить позже |
| F-PACK-04 | Packaging smoke | P1 | planned | app shell | Приложение запускается из собранного пакета | Можно заменить запуском из dev env для раннего MVP |
| F-PACK-05 | Portfolio case notes | P2 | deferred | stable MVP | Отдельное описание рефакторинга и архитектуры для портфолио | После MVP |

---

# 14. Явно вне scope BalanceCraft 1.5

| Feature | Priority | Reason |
|---|---|---|
| BalanceCraft Cloud | P3+ | Противоречит local-first и создаёт лишние privacy/security риски |
| Self-hosted Collector runtime | P3 | Требует отдельного backend/deploy/security слоя |
| SDK Lite implementation | P2 | Формат должен быть совместим, но сам SDK после Desktop vertical slice |
| Full model simulation | P3 | Нужна явная модель зависимостей |
| External simulation adapter | P3 | Требует интеграции с игрой/симулятором |
| Full BI dashboard builder | P3 | Раздувает UI и не нужен для MVP |
| User formula editor | P2 | Требует безопасного expression layer |
| ML interpretation | P3 | Не нужна для честного MVP и повышает риск false-аналитики |

---

# 15. Решения, закрытые проектированием

| ID | Решение |
|---|---|
| FL-Q1 | Полный P0 содержит четыре шаблона: Flow Balance, Stock Dynamics, Conversion Efficiency, Operation Intensity |
| FL-Q2 | Полноценный parameter import — P1; P0 использует demo seed или уже существующие `entity_parameters` |
| FL-Q3 | Минимальный What-if — P0: Level 1 + один узкий deterministic Level 2 single-override сценарий |
| FL-Q4 | Built-in templates живут в code registry; snapshots расчёта и bindings сохраняются в БД |
| FL-Q5 | Demo project поставляется с готовыми bindings для быстрого результата; Binding Wizard остаётся отдельным обязательным пользовательским маршрутом |

---

# 16. Итоговая позиция

BalanceCraft 1.5 должен доказать не то, что система уже умеет всё.

Он должен доказать, что:

```text
универсальная событийная модель работает;
поздняя семантика работает;
метрики считаются честно;
графики и insights дают практическую пользу;
приложение запускается локально без инфраструктурной боли.
```

Всё остальное можно докрутить после того, как этот фундамент перестанет шататься.
