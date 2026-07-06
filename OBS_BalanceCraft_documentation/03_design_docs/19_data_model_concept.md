# 19. Концептуальная модель данных BalanceCraft

Дата: 2026-07-02  
Статус: draft  
Связанные документы: `../01_pre_design_docs/11_glossary.md`, `../01_pre_design_docs/12_input_data_formats.md`, `../01_pre_design_docs/13_design_requirements.md`, `16_feature_list.md`, `17_implementation_checklist.md`, `26_definition_of_done.md`, `../01_pre_design_docs/adr/ADR-003-entity-observation-model.md`, `../01_pre_design_docs/adr/ADR-004-late-semantic-binding.md`, `../01_pre_design_docs/adr/ADR-005-what-if-levels.md`

Диаграмма: [`diagrams/conceptual_data_model.md`](diagrams/conceptual_data_model.md)

---

## 1. Назначение документа

Этот документ фиксирует концептуальную модель данных BalanceCraft до проектирования физической SQLite-схемы.

Задача документа — ответить на вопросы:

- какие сущности существуют в предметной области BalanceCraft;
- какие данные являются raw-данными, а какие производными;
- где появляется пользовательская семантика;
- как события превращаются в метрики;
- как параметры используются в What-if;
- какие legacy-понятия старого прототипа не должны стать ядром новой модели.

Концептуальная модель не описывает конкретные типы SQLite, индексы, nullable-поля, миграции и SQL-ограничения. Это будет зафиксировано отдельно в `20_sqlite_schema_design.md`.

---

## 2. Главный принцип модели

BalanceCraft не строится вокруг жанровых объектов.

В ядре нет обязательных:

- игроков;
- сессий;
- предметов;
- навыков;
- опыта;
- уровней;
- квестов;
- боёв;
- персонажей.

Все эти понятия могут существовать в конкретном проекте пользователя как значения `entity_type`, `observation_type`, `event_type`, `attribute` или `parameter_key`, но не как фундаментальные таблицы и не как обязательная логика ядра.

Базовая модель:

```text
Project
→ Entity / Observation / Event / Parameter
→ SemanticBinding
→ MetricRun / MetricValue
→ Insight
→ Scenario / ScenarioOverride / ScenarioResult
```

---

## 3. Слои данных

Модель делится на несколько слоёв.

| Слой | Сущности | Назначение |
|---|---|---|
| Project layer | `Project`, `ProjectSettings` | локальный контейнер анализа |
| Raw data layer | `Event`, `Attribute`, `Entity`, `Observation`, `ImportRun`, `SourceFile` | исходные события и происхождение данных |
| Semantic layer | `MetricTemplate`, `SemanticBinding`, `Scope` | назначение смысла данным |
| Calculation layer | `MetricRun`, `MetricValue`, `CalculationWarning` | результаты расчётов |
| Interpretation layer | `Insight`, `Evidence`, `AnalysisCoverageResult` | объяснение проблем и возможностей анализа |
| Parameter layer | `ParameterCatalog`, `EntityParameter` | изменяемые параметры игровых систем |
| Scenario layer | `Scenario`, `ScenarioOverride`, `ScenarioResult`, `ConfidenceStatus` | простой What-if и сравнение сценариев |

Главное правило: raw-события не изменяются при настройке семантики, расчёте метрик или запуске сценариев.

---

## 4. Project

### Смысл

`Project` — локальный проект анализа в BalanceCraft.

Он объединяет:

- импортированные raw-события;
- найденные сущности;
- окна наблюдения;
- параметры;
- semantic bindings;
- metric runs;
- scenarios;
- пользовательские настройки проекта.

### Основные данные

Концептуально проект содержит:

- идентификатор;
- название;
- дату создания и изменения;
- последний открытый момент;
- настройки проекта;
- default build, если он задан.

### Связи

- Один `Project` содержит много `Event`.
- Один `Project` содержит много `Entity`.
- Один `Project` содержит много `Observation`.
- Один `Project` содержит много `SemanticBindingSet`.
- Один `SemanticBindingSet` содержит много `SemanticBinding`.
- Один `Project` содержит много `MetricRun`.
- Один `Project` содержит много `Scenario`.

### Правила

- Данные разных проектов не должны смешиваться.
- Проект является границей изоляции данных.
- Удаление проекта не должно требовать ручной очистки SQL.

---

## 5. ImportRun и SourceFile

### Смысл

`ImportRun` фиксирует факт импорта данных.

`SourceFile` фиксирует конкретный файл, из которого были прочитаны события.

Эти сущности нужны не для анализа баланса напрямую, а для трассировки происхождения данных и человеческой диагностики.

### ImportRun содержит

- проект;
- источник импорта;
- время начала и завершения;
- статус;
- количество прочитанных строк;
- количество валидных и невалидных событий;
- warnings;
- errors.

### SourceFile содержит

- import run;
- путь или имя файла;
- hash файла, если он считается;
- количество строк;
- количество валидных и невалидных событий;
- статус обработки.

### Связи

- Один `Project` содержит много `ImportRun`.
- Один `ImportRun` содержит много `SourceFile`.
- Один `SourceFile` может породить много `Event`.
- Один `Event` может ссылаться на конкретную строку `SourceFile`.

### Правила

- Битая строка не должна валить весь импорт, если в файле есть валидные события.
- Ошибки импорта должны сохранять связь с файлом и строкой.
- Повторный импорт должен быть отличим от первого импорта.

---

## 6. Entity

### Смысл

`Entity` — любая анализируемая или параметризуемая сущность игровой системы.

Примеры возможных сущностей:

- actor;
- player;
- resource;
- item;
- skill;
- operation;
- upgrade;
- rule;
- level;
- wave;
- build;
- system;
- custom object.

Важно: `player`, `item`, `skill` — не отдельные фундаментальные модели, а возможные значения `entity_type`.

### Основные данные

Концептуально entity содержит:

- `entity_id` из входных данных;
- `entity_type`, если он есть;
- пользовательский label;
- metadata.

### Связи

- Один `Project` содержит много `Entity`.
- Один `Event` обычно связан с одной основной `Entity`.
- Одна `Entity` может иметь много `EntityParameter`.
- Одна `Entity` может участвовать в `MetricValue` как срез анализа.
- Одна `Entity` может быть целью `ScenarioOverride`.

### Правила

- `Entity` создаётся из импортированных событий или параметров.
- Отсутствующий `entity_type` не должен ломать импорт.
- `Entity` не обязана быть игроком или персонажем.

---

## 7. Observation

### Смысл

`Observation` — окно наблюдения, в рамках которого группируются события и считаются метрики.

Примеры:

- session;
- run;
- level;
- combat;
- wave;
- chapter;
- test pass;
- day;
- arbitrary time window.

Старый термин `Session` становится частным случаем `Observation`.

### Основные данные

Концептуально observation содержит:

- `observation_id` из входных данных или auto-generated значение;
- `observation_type`;
- время начала и завершения, если оно известно;
- build;
- metadata.

### Связи

- Один `Project` содержит много `Observation`.
- Один `Event` может относиться к одной `Observation`.
- Один `MetricValue` может быть рассчитан для конкретной `Observation`.
- Один `ScenarioResult` может сравнивать значения по `Observation`.

### Правила

- Если `observation_id` отсутствует, импорт может создать auto-observation.
- Observation не обязана быть игровой сессией.
- Observation нужна для временных рядов, группировок и x-axis графиков.

---

## 8. Event

### Смысл

`Event` — атомарная запись о том, что произошло в игре или игровой системе.

Событие может описывать:

- получение ресурса;
- расход ресурса;
- изменение запаса;
- попытку операции;
- успешную операцию;
- блокировку операции;
- получение награды;
- использование контента;
- покупку апгрейда;
- изменение параметра.

### Основные данные

Концептуально event содержит:

- timestamp;
- entity reference;
- observation reference;
- event type;
- build id;
- schema version;
- source reference;
- attributes.

### Связи

- Один `Project` содержит много `Event`.
- Один `Event` принадлежит одному `ImportRun`.
- Один `Event` может ссылаться на один `SourceFile`.
- Один `Event` может быть связан с одной `Entity`.
- Один `Event` может быть связан с одной `Observation`.
- Один `Event` содержит набор `Attribute`.
- Много `Event` используются при расчёте одного `MetricRun`.

### Правила

- Event хранится как raw-data.
- Event не изменяется при semantic binding.
- Event не изменяется при metric calculation.
- Event не изменяется при What-if.
- Смысл event задаётся позднее через `SemanticBinding`.

---

## 9. Attribute

### Смысл

`Attribute` — произвольное поле внутри payload события.

Пример:

```json
{
  "amount": 25,
  "resource_type": "gold",
  "source": "quest_reward"
}
```

BalanceCraft не должен заранее знать, что означает `amount`, `resource_type` или `source`.

### Основные данные

Концептуально attribute имеет:

- key;
- value;
- value type;
- optional unit;
- optional role после semantic binding.

В физической SQLite-модели attributes могут храниться как JSON и дополнительно профилироваться в кэше карты данных.

### Связи

- Один `Event` содержит много `Attribute`.
- `SemanticBinding` указывает на конкретные attribute paths.
- `DataProfile` агрегирует информацию об attributes.

### Правила

- Для MVP лучше считать attributes плоскими.
- Вложенные объекты и массивы можно отложить на P1/P2.
- Смешанные типы поля должны создавать warning.

---

## 10. DataProfile

### Смысл

`DataProfile` — результат анализа структуры импортированных событий.

Он отвечает на вопросы:

- какие `event_type` есть в проекте;
- какие attributes встречаются;
- какие типы значений найдены;
- какие числовые диапазоны доступны;
- какие поля грязные или смешанные;
- какие примеры значений можно показать пользователю.

### Связи

- Один `Project` имеет один или несколько актуальных профилей данных.
- `DataProfile` строится по `Event` и `Attribute`.
- `SemanticBinding` использует `DataProfile` как источник кандидатов.
- `AnalysisCoverageResult` использует `DataProfile` для проверки доступных сигналов.

### Правила

- DataProfile является производным слоем.
- Устаревший профиль можно пересчитать.
- Ошибка профилирования не должна повреждать raw-events.

---

## 11. MetricTemplate

### Смысл

`MetricTemplate` — шаблон анализа, описывающий типовую числовую зависимость.

Примеры P0-шаблонов:

- баланс потоков;
- динамика запаса;
- эффективность конверсии;
- интенсивность операций.

### Основные данные

Концептуально template содержит:

- template key;
- название;
- описание;
- список переменных;
- формулы метрик;
- правила интерпретации;
- ограничения;
- default thresholds, если они есть.

### Связи

- Один `MetricTemplate` может использоваться во многих `SemanticBindingSet`.
- Один `MetricTemplate` может использоваться во многих `MetricRun`.
- Один `MetricRun` должен сохранять snapshot template/formulas.

### Правила

- Template не должен быть жанровым.
- Template не должен требовать игрока.
- Template задаёт переменные, но не знает заранее, где они лежат во входных данных.
- Пользовательские формулы не входят в BalanceCraft 1.5.

---

## 12. SemanticBindingSet

### Смысл

`SemanticBindingSet` — сохранённая конфигурация связей для одного шаблона анализа в рамках проекта.

Он нужен потому, что практически полезный binding — это не одна переменная, а согласованный набор переменных одного `MetricTemplate`: например, `flow_in`, `flow_out`, `stock_value`, фильтры, агрегации и пользовательские подписи.

### Основные данные

Концептуально binding set содержит:

- project;
- template key;
- name / label;
- status;
- список `SemanticBinding`;
- validation warnings;
- дату создания и обновления.

### Связи

- Один `Project` содержит много `SemanticBindingSet`.
- Один `SemanticBindingSet` относится к одному `MetricTemplate`.
- Один `SemanticBindingSet` содержит много `SemanticBinding`.
- Один `MetricRun` использует один `SemanticBindingSet` и сохраняет его snapshot.

### Правила

- Binding set — пользовательская конфигурация анализа, а не raw-data.
- Binding set можно изменить, но это не должно менять уже созданные metric runs.
- Для воспроизводимости `MetricRun` хранит snapshot binding set.

---

## 13. SemanticBinding

### Смысл

`SemanticBinding` связывает одну переменную шаблона с конкретными полями событий или параметров проекта.

Пример:

```text
flow_in  → attributes.amount where event_type = resource_gained
flow_out → attributes.amount where event_type = resource_spent
```

### Основные данные

Концептуально binding содержит:

- project;
- template key;
- variable key;
- source kind;
- source path;
- event type filters;
- additional filters;
- aggregation;
- user label.

### Связи

- Один `Project` содержит много `SemanticBindingSet`.
- Один `SemanticBindingSet` содержит много `SemanticBinding`.
- Один `SemanticBinding` относится к одной переменной одного `MetricTemplate` через свой `SemanticBindingSet`.
- Один `SemanticBinding` может ссылаться на `Event.Attribute` или `EntityParameter`.
- Один `MetricRun` использует snapshot набора bindings.

### Правила

- Binding является пользовательским назначением смысла.
- Binding не меняет raw-events.
- Binding можно изменить, но старые metric runs должны оставаться воспроизводимыми через snapshot.
- Невалидный binding должен давать warning/error до запуска расчёта.

---

## 14. Scope

### Смысл

`Scope` — правило отбора и группировки данных для анализа.

Примеры scope:

- весь проект;
- entity;
- observation;
- observation type;
- event type;
- build id;
- attribute value;
- custom group.

### Связи

- `MetricRun` выполняется в конкретном scope.
- `MetricValue` сохраняет scope key и связанные entity/observation, если они есть.
- Dashboard использует scope для построения графиков.

### Правила

- Старый selector “Игрок” заменяется универсальным scope selector.
- Scope не обязан совпадать с entity.
- Scope может быть простым в MVP и расширяться позже.

---

## 15. MetricRun

### Смысл

`MetricRun` — один факт расчёта метрик по выбранному шаблону, bindings и scope.

Он нужен, чтобы:

- не смешивать старые и новые результаты;
- пересчитывать метрики без потери истории;
- сохранять formula snapshot;
- сохранять binding snapshot;
- сохранять warnings.

### Основные данные

Концептуально metric run содержит:

- project;
- template key;
- scope;
- binding snapshot;
- formula snapshot;
- время запуска и завершения;
- status;
- warnings.

### Связи

- Один `Project` содержит много `MetricRun`.
- Один `MetricRun` относится к одному `MetricTemplate`.
- Один `MetricRun` создаёт много `MetricValue`.
- Один `MetricRun` может быть основой для `Scenario`.
- Один `MetricRun` может порождать `Insight`.

### Правила

- MetricRun не меняет raw-events.
- MetricRun хранит snapshot формул и bindings.
- Ошибки расчёта не должны исчезать в консоли.

---

## 16. MetricValue

### Смысл

`MetricValue` — конкретное рассчитанное значение метрики.

Пример:

```text
metric_key = NET_FLOW
scope_key = observation:run_001
x_label = Run 001
value = -35
status = ok
```

### Основные данные

Концептуально metric value содержит:

- metric run;
- metric key;
- metric label;
- scope key;
- optional entity;
- optional observation;
- x-index;
- x-label;
- value;
- status;
- warnings;
- metadata.

### Связи

- Один `MetricRun` содержит много `MetricValue`.
- `Insight` ссылается на `MetricValue` через evidence.
- `ScenarioResult` сравнивает historical metric value с scenario value.

### Правила

- Если значение нельзя корректно посчитать, оно должно иметь status `n/a`, `warning` или `error`.
- Деление на ноль не маскируется искусственным делением на `1`.
- Несопоставимые единицы не должны называться строгим ROI.

---

## 17. CalculationWarning

### Смысл

`CalculationWarning` — предупреждение о том, что расчёт выполнен с ограничениями или не может быть выполнен полностью.

Примеры:

- denominator is zero;
- missing attribute;
- mixed value types;
- insufficient observations;
- incompatible units;
- low sample size;
- unsupported template variable.

### Связи

- Warning может относиться к `MetricRun`.
- Warning может относиться к конкретному `MetricValue`.
- Warning может показываться в UI и insight evidence.

### Правила

- Warning не должен скрываться.
- Warning не всегда означает ошибку.
- Warning должен быть человекочитаемым.

---

## 18. Insight и Evidence

### Смысл

`Insight` — практический вывод, построенный поверх рассчитанных метрик.

`Evidence` — основание вывода: метрики, значения, окна наблюдения, события или сравнения, на которые ссылается insight.

### Insight содержит

- severity;
- category;
- title;
- text;
- recommendation;
- related metrics;
- evidence.

### Связи

- Один `MetricRun` может породить много `Insight`.
- Один `Insight` ссылается на один или несколько `MetricValue`.
- Scenario может породить scenario insight или сравнение с historical insight.

### Правила

- Insight не является абсолютным диагнозом игры.
- Insight должен объяснять, почему проблема подсвечена.
- Если данных недостаточно, insight должен говорить об ограничении, а не притворяться уверенным.

---

## 19. AnalysisCoverageResult

### Смысл

`AnalysisCoverageResult` показывает, какие проблемы баланса можно проверить по текущим данным и semantic bindings.

Примеры статусов:

- `available`;
- `partially_available`;
- `missing_data`;
- `unsupported_in_version`.

### Основные данные

Концептуально coverage result содержит:

- problem key;
- problem label;
- status;
- required signals;
- available signals;
- missing signals;
- related template;
- explanation.

### Связи

- Coverage строится по `DataProfile`.
- Coverage учитывает `SemanticBinding`.
- Coverage может учитывать `EntityParameter`.
- Coverage показывается в UI как диагностика возможностей анализа.

### Правила

- Отсутствие покрытия одной проблемы не блокирует другие виды анализа.
- P0-coverage может считаться на лету.
- Кэш coverage — P1, а не обязательная часть MVP.

---

## 20. ParameterCatalog

### Смысл

`ParameterCatalog` — набор параметров, импортированный или созданный в проекте.

Примеры:

- таблица цен апгрейдов;
- таблица наград;
- таблица множителей;
- таблица лимитов;
- таблица cooldown-ов;
- таблица шансов.

### Основные данные

Концептуально catalog содержит:

- catalog id;
- project;
- name;
- build id;
- schema version;
- source;
- metadata.

### Связи

- Один `Project` содержит много `ParameterCatalog`.
- Один `ParameterCatalog` содержит много `EntityParameter`.
- `ScenarioOverride` обычно изменяет значения из parameter layer.

### Правила

- ParameterCatalog не является raw-event log.
- CSV/JSON import параметров можно реализовать P1, но модель должна учитывать эту возможность.
- Параметры не должны подменять события: это отдельный слой.

---

## 21. EntityParameter

### Смысл

`EntityParameter` — конкретное значение параметра для конкретной entity.

Пример:

```text
entity_id = upgrade_sword_01
parameter_key = cost_gold
value = 120
```

### Основные данные

Концептуально entity parameter содержит:

- project;
- catalog;
- entity;
- entity type;
- parameter key;
- value;
- value type;
- unit;
- build id;
- validity window, если нужно;
- metadata.

### Связи

- Один `Entity` может иметь много `EntityParameter`.
- Один `ParameterCatalog` содержит много `EntityParameter`.
- `SemanticBinding` может использовать parameter как source.
- `ScenarioOverride` изменяет parameter value для What-if.

### Правила

- EntityParameter не изменяет historical events.
- Если параметр отсутствует, What-if должен возвращать insufficient data/model.
- Параметры должны быть связаны с entity, operation или rule, а не висеть в пустоте.

---

## 22. Scenario

### Смысл

`Scenario` — named What-if эксперимент.

Он отвечает на вопрос:

```text
Что изменится в доступном уровне модели, если изменить выбранные параметры?
```

### Основные данные

Концептуально scenario содержит:

- project;
- name;
- description;
- base metric run;
- status;
- confidence status;
- список overrides.

### Связи

- Один `Project` содержит много `Scenario`.
- Один `Scenario` может ссылаться на один base `MetricRun`.
- Один `Scenario` содержит много `ScenarioOverride`.
- Один `Scenario` создаёт много `ScenarioResult`.

### Правила

- Scenario не меняет raw-events.
- Scenario не меняет historical metric values.
- Scenario должен показывать confidence status.
- Если изменение параметра может изменить sequence событий, MVP не должен называть результат точной симуляцией.

---

## 23. ScenarioOverride

### Смысл

`ScenarioOverride` — одно изменение параметра внутри сценария.

Примеры:

```text
cost_gold = 90
reward_gold += 10
upgrade_cost *= 0.8
cooldown = 5
```

### Основные данные

Концептуально override содержит:

- scenario;
- target entity;
- parameter key;
- override mode;
- original value;
- scenario value;
- multiplier;
- delta;
- metadata.

### Связи

- Один `Scenario` содержит много `ScenarioOverride`.
- Один `ScenarioOverride` обычно относится к одному `EntityParameter`.
- `WhatIfEngine` использует overrides для создания `ScenarioResult`.

### Правила

- Override должен быть явным.
- Override не должен перезаписывать parameter catalog.
- Несколько overrides должны быть видны пользователю до запуска сценария.

---

## 24. ScenarioResult

### Смысл

`ScenarioResult` — результат сравнения исторического значения и сценарного значения.

Пример:

```text
historical NET_FLOW = -35
scenario NET_FLOW = -10
delta = +25
confidence_status = approx_recalc
```

### Основные данные

Концептуально scenario result содержит:

- scenario;
- metric key;
- scope key;
- optional entity;
- optional observation;
- x-index;
- x-label;
- historical value;
- scenario value;
- delta;
- delta percent;
- confidence status;
- metadata.

### Связи

- Один `Scenario` создаёт много `ScenarioResult`.
- `ScenarioResult` сравнивается с `MetricValue` из base metric run.
- Dashboard показывает historical и scenario series вместе.

### Правила

- ScenarioResult не является новым raw-event.
- ScenarioResult не должен выглядеть точнее, чем позволяет модель.
- ScenarioResult должен хранить confidence status.

---

## 25. ConfidenceStatus

### Смысл

`ConfidenceStatus` — rule-based статус надёжности сценарного результата.

Это не вероятность и не статистическая уверенность.

Возможные значения:

- `exact_recalc` — точный пересчёт;
- `approx_recalc` — приближённый пересчёт;
- `impact_estimate` — оценка потенциального влияния;
- `insufficient_model` — недостаточно модели;
- `insufficient_data` — недостаточно данных.

### Связи

- `Scenario` может иметь общий confidence status.
- Каждый `ScenarioResult` может иметь свой confidence status.
- UI показывает confidence status рядом со сценарной линией.

### Правила

- Не использовать проценты уверенности в MVP.
- Не обещать точную симуляцию без dependency rules.
- Если sequence событий может измениться, exact recalculation недоступен.

---

## 26. ValueNormalizationProfile

### Смысл

`ValueNormalizationProfile` — правило приведения разных игровых величин к общей дизайнерской шкале.

Пример проблемы:

```text
cost = 120 gold
result = 18 damage
```

Эти значения нельзя напрямую считать финансовым ROI без общей шкалы.

### Статус в MVP

- Полноценный editor профилей нормализации не входит в BalanceCraft 1.5.
- В MVP нормализованный ROI возможен только если входные данные уже содержат `cost_value`, `result_value`, `value_unit`.
- Сама концепция нужна модели, чтобы не заблокировать будущую версию.

### Связи

- Может использоваться `MetricTemplate` для нормализованного ROI.
- Может использоваться `MetricRun` как часть formula/binding snapshot.

### Правила

- Если нормализации нет, UI использует формулировки “результат на единицу затрат” и “стоимость единицы результата”.
- Нельзя называть отношение разных единиц строгим ROI.

---

## 27. Legacy mapping

| Legacy term | Новый концепт | Правило |
|---|---|---|
| `Player` | `Entity` с `entity_type = actor/player` | не фундаментальная сущность |
| `Session` | `Observation` с `observation_type = session` | не фундаментальная сущность |
| `Item` | `Entity` с `entity_type = item` | не отдельная обязательная таблица |
| `Skill` | `Entity` с `entity_type = skill` | не отдельная обязательная таблица |
| `XP` | `Attribute` или `Parameter` | не встроенный смысл |
| `session_metrics` | `MetricRun` + `MetricValue` | старая агрегированная таблица заменяется универсальным расчётом |
| `simulation_results` | `ScenarioResult` | сценарии не должны называться simulation, если нет модели симуляции |
| `players.id` selector | `Scope` selector | UI должен быть универсальным |

---

## 28. Минимальная модель для P0 vertical slice

Для первого рабочего vertical slice достаточно следующего набора концептов:

```text
Project
ImportRun
SourceFile
Entity
Observation
Event
Attribute
DataProfile
MetricTemplate
SemanticBinding
Scope
MetricRun
MetricValue
CalculationWarning
Insight
Evidence
AnalysisCoverageResult
```

P0/P1, если успеваем:

```text
ParameterCatalog
EntityParameter
Scenario
ScenarioOverride
ScenarioResult
ConfidenceStatus
```

P1/P2:

```text
ValueNormalizationProfile
advanced AnalysisCoverage cache
advanced Scenario dependency rules
custom Formula Editor
```

---

## 29. Главные инварианты модели

1. Raw events не изменяются после импорта.
2. Смысл данных назначается через SemanticBinding.
3. MetricRun хранит snapshot bindings и formulas.
4. MetricValue хранит status/warnings, а не только число.
5. Scenario не изменяет historical data.
6. ScenarioResult хранит confidence status.
7. Entity и Observation универсальны.
8. Player и Session не являются ядром.
9. Параметры живут отдельно от событий.
10. Analysis coverage объясняет, что можно и нельзя проверить.
11. UI не должен показывать жанровую модель как обязательную.
12. Любая производная сущность должна быть пересчитываемой или трассируемой к raw-data и bindings.

---

## 30. Вопросы для ревью

| ID | Вопрос | Комментарий |
|---|---|---|
| DM-Q1 | Нужен ли `AnalysisCoverageResult` как полноценный концепт уже в P0? | Сейчас да, но физический кэш можно отложить. |
| DM-Q2 | Держим ли `ParameterCatalog` в P0 или P1? | Модель нужна сейчас, импорт параметров можно резать. |
| DM-Q3 | Нужно ли отличать `Insight` и `ScenarioInsight`? | Пока можно считать scenario insight частным случаем Insight с привязкой к scenario. |
| DM-Q4 | Должен ли `Scope` быть отдельной сохраняемой сущностью? | Концептуально да, физически может быть JSON внутри MetricRun. |
| DM-Q5 | Нужна ли отдельная сущность `AttributeProfile` вместо общего `DataProfile`? | Физически вероятно да, концептуально достаточно DataProfile. |
| DM-Q6 | Нужно ли хранить связи event → multiple entities? | Для MVP нет, но P1/P2 может потребовать event object refs. |

---

## 31. Переход к следующему документу

Следующий шаг — `20_sqlite_schema_design.md`.

В нём эта концептуальная модель будет превращена в физическую SQLite-схему:

- таблицы;
- поля;
- типы;
- PK/FK;
- индексы;
- JSON-поля;
- миграции;
- правила транзакций;
- schema versioning.

Важно: физическая схема может оптимизировать или объединять некоторые концепты, но не должна нарушать инварианты из этого документа.
