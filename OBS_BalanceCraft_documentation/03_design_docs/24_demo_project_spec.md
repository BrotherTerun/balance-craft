# FILE: `03_design_docs/24_demo_project_spec.md`
# 24. Demo project specification

Дата: 2026-07-02  
Статус: проектный черновик для ревью

## Назначение

Demo project нужен, чтобы пользователь понял ценность BalanceCraft без подготовки собственных логов.

Это не “пример настоящей игры целиком”. Это управляемый синтетический проект, который демонстрирует основной vertical slice:

```text
events
→ data map
→ semantic binding
→ metric calculation
→ dashboard
→ practical insight
→ simple What-if
```

Demo должен быть честно маркирован как synthetic sample.

## Цели demo project

Demo project должен показать:

1. BalanceCraft работает local-only.
2. JSONL-события можно импортировать без ручного SQL.
3. Data Map помогает понять структуру событий.
4. Semantic Binding превращает нейтральные поля в смысловые переменные.
5. Metric templates дают понятные графики.
6. Insights объясняют, на что обратить внимание.
7. What-if пересчитывает простой параметрический сценарий и показывает confidence status.
8. BalanceCraft не требует MySQL, сервера, SDK или облака.

## Что demo не должен обещать

Demo не должен создавать впечатление, что BalanceCraft:

- автоматически понимает любую игру;
- симулирует поведение игрока;
- заменяет полноценный playtest;
- строит точную экономическую модель без правил;
- анализирует художественное качество игры;
- покрывает все проблемы баланса из таксономии сразу.

## Рекомендуемая демо-игра

Рабочее название:

```text
Demo Forge
```

Жанровая абстракция:

```text
маленькая idle/RPG-like экономика улучшений кузницы
```

Почему такой сценарий подходит:

- есть ресурсы;
- есть доходы и траты;
- есть операции покупки апгрейдов;
- есть прогрессия;
- есть параметры цен/наград;
- легко показать flow balance, stock dynamics, conversion efficiency и operation intensity;
- не нужно имитировать сложное поведение игрока.

Важно: demo game — только оболочка. В документации можно прямо сказать, что это synthetic economy sample, а не “игра”.

## Демо-сюжет в одну фразу

Игрок управляет кузницей, получает `coins` и `ore`, покупает апгрейды, открывает заказы и постепенно накапливает слишком много coins из-за слабых sink-механик и переэффективного апгрейда.

## Демонстрируемые проблемы баланса

## P0 problems

| Problem | Как проявляется в demo | Template |
|---|---|---|
| Профицит ресурса | `coins` растут быстрее расходов | Flow Balance |
| Инфляция/накопление | stock `coins` стабильно растёт по run/day windows | Stock Dynamics |
| Перегретая конверсия | upgrade `bellows_02` даёт слишком высокий result per cost | Conversion Efficiency |
| Просадка интенсивности | после середины observation падает число completed operations | Operation Intensity |

## P1-lite optional

| Problem | Как проявляется | Template |
|---|---|---|
| Недостаточный sink | мало `resource_spent` относительно `resource_gained` | Flow Balance |
| Блокировка операции | часть upgrades blocked из-за `ore` | Action Availability, если P1 включён |
| Неровный pacing наград | редкие крупные reward spikes | Reward Pacing, если P1 включён |

P1-lite события можно включить в demo logs, даже если UI 1.5 показывает их только как missing/partially available coverage.

## Минимальный размер demo data

Для MVP достаточно:

```text
3 builds or 1 build with 3 phases
10 observations
200–500 events
10–20 entities
8–12 parameters
4 configured binding sets
4 metric runs or one multi-template demo run
1 prepared What-if scenario
```

Если хочется проще для разработки:

```text
1 build
6 observations
120–200 events
6–10 entities
6–8 parameters
2 templates
1 prepared scenario
```

Главное — чтобы графики были читаемыми, а не похожими на кардиограмму кофейного демона.

## Сущности demo

## Entity types

| entity_type | Примеры | Назначение |
|---|---|---|
| `actor` | `smith_player` | условный субъект экономики |
| `resource` | `coins`, `ore`, `reputation` | анализ flow/stock |
| `operation` | `craft_order`, `buy_upgrade`, `refine_ore` | intensity/conversion |
| `upgrade` | `bellows_01`, `bellows_02`, `anvil_01` | parameters/What-if |
| `system` | `forge_economy` | общий scope |

## Observations

Observation лучше моделировать как `day` или `run`.

Рекомендуется:

```text
observation_type = day
observation_id = day_01 ... day_10
```

Так проще читать графики.

## Event types

Demo logs должны использовать рекомендуемый словарь из input data docs.

| event_type | Обязателен | Назначение |
|---|---:|---|
| `resource_gained` | yes | доходы coins/ore/reputation |
| `resource_spent` | yes | траты на upgrades/orders |
| `stock_changed` | yes | snapshot/изменение stock |
| `operation_attempted` | yes | попытка craft/upgrade/refine |
| `operation_completed` | yes | успешная операция |
| `upgrade_purchased` | yes | cost/result для conversion |
| `reward_received` | optional | reward pacing |
| `operation_blocked` | optional | availability/bottleneck |
| `content_used` | optional | content usage |

## JSONL event examples

### resource_gained

```json
{"timestamp":"2026-07-02T10:00:00Z","entity_id":"coins","entity_type":"resource","observation_id":"day_01","observation_type":"day","event_type":"resource_gained","build_id":"demo_1.0","schema_version":"1.0","attributes":{"amount":40,"resource_type":"coins","source":"order_reward"}}
```

### resource_spent

```json
{"timestamp":"2026-07-02T10:05:00Z","entity_id":"coins","entity_type":"resource","observation_id":"day_01","observation_type":"day","event_type":"resource_spent","build_id":"demo_1.0","schema_version":"1.0","attributes":{"amount":15,"resource_type":"coins","sink":"upgrade_purchase","operation_id":"buy_upgrade"}}
```

### stock_changed

```json
{"timestamp":"2026-07-02T10:10:00Z","entity_id":"coins","entity_type":"resource","observation_id":"day_01","observation_type":"day","event_type":"stock_changed","build_id":"demo_1.0","schema_version":"1.0","attributes":{"stock_value":125,"resource_type":"coins"}}
```

### operation_completed

```json
{"timestamp":"2026-07-02T10:12:00Z","entity_id":"craft_order","entity_type":"operation","observation_id":"day_01","observation_type":"day","event_type":"operation_completed","build_id":"demo_1.0","schema_version":"1.0","attributes":{"operation_type":"craft_order","reward_coins":40,"duration_seconds":60}}
```

### upgrade_purchased

```json
{"timestamp":"2026-07-02T10:15:00Z","entity_id":"bellows_02","entity_type":"upgrade","observation_id":"day_04","observation_type":"day","event_type":"upgrade_purchased","build_id":"demo_1.0","schema_version":"1.0","attributes":{"cost":90,"cost_type":"coins","result":35,"result_type":"production_bonus","cost_value":90,"result_value":180,"value_unit":"designer_score"}}
```

### operation_blocked optional

```json
{"timestamp":"2026-07-02T10:17:00Z","entity_id":"anvil_02","entity_type":"upgrade","observation_id":"day_05","observation_type":"day","event_type":"operation_blocked","build_id":"demo_1.0","schema_version":"1.0","attributes":{"reason":"not_enough_ore","required":80,"available":45,"operation_type":"upgrade_purchase"}}
```

## Parameter catalog

Demo should include parameter data for What-if.

Recommended JSON:

```json
{
  "catalog_id": "demo_forge_parameters_v1",
  "build_id": "demo_1.0",
  "schema_version": "1.0",
  "parameters": [
    {
      "entity_id": "order_basic",
      "entity_type": "operation",
      "parameter_key": "reward_coins",
      "value": 40,
      "value_type": "number",
      "unit": "coins"
    },
    {
      "entity_id": "bellows_02",
      "entity_type": "upgrade",
      "parameter_key": "cost_coins",
      "value": 90,
      "value_type": "number",
      "unit": "coins"
    },
    {
      "entity_id": "bellows_02",
      "entity_type": "upgrade",
      "parameter_key": "production_bonus",
      "value": 35,
      "value_type": "number",
      "unit": "designer_score"
    }
  ]
}
```

## Рекомендуемые параметры

| entity_id | parameter_key | value | unit | Назначение |
|---|---|---:|---|---|
| `order_basic` | `reward_coins` | 40 | coins | доход |
| `order_advanced` | `reward_coins` | 85 | coins | доход |
| `bellows_01` | `cost_coins` | 60 | coins | upgrade cost |
| `bellows_02` | `cost_coins` | 90 | coins | подозрительно дешёвый upgrade |
| `bellows_02` | `production_bonus` | 35 | designer_score | слишком сильный result |
| `anvil_01` | `cost_ore` | 45 | ore | ore sink |
| `anvil_02` | `cost_ore` | 120 | ore | bottleneck optional |
| `refine_ore` | `cooldown_seconds` | 90 | seconds | pacing/intensity optional |

## Prepared binding sets

Demo должен содержать заранее настроенные semantic bindings.

## Binding set 1. Flow Balance — coins

| Template variable | Source |
|---|---|
| `flow_in` | `attributes.amount` where `event_type = resource_gained` and `attributes.resource_type = coins` |
| `flow_out` | `attributes.amount` where `event_type = resource_spent` and `attributes.resource_type = coins` |
| `context` | `attributes.source` or `attributes.sink` |
| `group_by` | `observation_id` |

Expected metrics:

```text
net_flow
spend_to_income_ratio
stock_delta_estimated
```

Expected insight:

```text
Coins accumulate across most observations. Spending does not keep pace with income.
```

## Binding set 2. Stock Dynamics — coins

| Template variable | Source |
|---|---|
| `stock_value` | `attributes.stock_value` where `event_type = stock_changed` and `attributes.resource_type = coins` |
| `timestamp` | `timestamp` |
| `group_by` | `observation_id` |

Expected metrics:

```text
stock_change
change_rate
plateau_indicator
jump_indicator
```

Expected insight:

```text
Coin stock grows consistently and may indicate inflation or weak sinks.
```

## Binding set 3. Conversion Efficiency — upgrades

| Template variable | Source |
|---|---|
| `cost` | `attributes.cost` where `event_type = upgrade_purchased` |
| `result` | `attributes.result` where `event_type = upgrade_purchased` |
| `cost_value` | `attributes.cost_value` optional |
| `result_value` | `attributes.result_value` optional |
| `context` | `entity_id` |

Expected metrics:

```text
result_per_cost
cost_per_result
normalized_roi if cost_value/result_value exist
```

Expected insight:

```text
bellows_02 gives unusually high result per cost compared with other upgrades.
```

## Binding set 4. Operation Intensity

| Template variable | Source |
|---|---|
| `action` | events where `event_type = operation_completed` |
| `duration` | observation duration or count-based proxy |
| `reward` | `attributes.reward_coins` optional |
| `group_by` | `observation_id` |

Expected metrics:

```text
operations_per_observation
reward_per_observation
average_operation_interval
```

Expected insight:

```text
Operation intensity drops after mid-demo while resource stock continues to grow.
```

## Prepared metric runs

Demo should ship with precomputed metric runs or generate them on first open.

Preferred MVP behavior:

```text
Open Demo Project
→ demo DB already contains events, bindings and one metric run
→ dashboard opens immediately
→ user can rerun calculation manually
```

This avoids first-launch friction.

## Prepared What-if scenario

Scenario A входит в обязательный P0 demo path. Scenario B остаётся P1/optional.

## Scenario A. Increase sink pressure

Question:

```text
What if bellows_02 cost was increased by 50%?
```

Override:

```text
entity_id = bellows_02
parameter_key = cost_coins
override_mode = multiplier
multiplier = 1.5
```

Expected result:

- `result_per_cost` decreases;
- normalized ROI decreases if value fields are present;
- scenario line differs from historical line;
- P0 demo includes an explicit dependency rule `bellows_02.cost_coins → upgrade_purchased.attributes.cost`;
- historical event sequence remains unchanged;
- therefore the prepared demo result uses `exact_recalc`;
- outside this explicit rule the engine may fall back to `impact_estimate`, `approx_recalc` or `insufficient_model`.

UI text:

```text
This scenario recalculates known upgrade cost under unchanged historical sequence.
It does not predict whether players would still buy the upgrade.
```

## Scenario B optional. Reduce order reward

Question:

```text
What if basic order rewards were reduced by 20%?
```

Override:

```text
entity_id = order_basic
parameter_key = reward_coins
override_mode = multiplier
multiplier = 0.8
```

Expected result:

- lower flow_in;
- lower net_flow;
- less accumulation;
- confidence status depends on explicit mapping from parameter to `resource_gained`.

## Demo dashboard layout

Recommended initial dashboard:

```text
Chart 1: Coins net flow by day
Chart 2: Coins stock by day
Chart 3: Upgrade result per cost by upgrade
Chart 4: Operations completed by day

Insight cards:
- Coin surplus / weak sinks
- bellows_02 over-efficiency
- Optional: ore bottleneck / blocked upgrades
```

## Demo walkthrough

Use this in README/GIF/video:

```text
1. Open Demo Project.
2. Dashboard shows coin surplus.
3. Click insight: "Coins accumulate across most observations."
4. Open Data Map and inspect resource_gained/resource_spent.
5. Open Binding Wizard and see flow_in/flow_out mapping.
6. Open Conversion Efficiency chart.
7. Notice bellows_02 outlier.
8. Open What-if.
9. Increase bellows_02 cost by 50%.
10. Compare historical and scenario line.
11. Read confidence status and limitation.
```

## Demo file structure

Recommended repository structure:

```text
examples/
  demo_project/
    README.md
    demo_forge.balancecraft.db
  demo_logs/
    demo_forge_events.jsonl
  demo_parameters/
    demo_forge_parameters.json
```

If shipping a prebuilt demo DB is inconvenient:

```text
examples/
  demo_project/
    README.md
    demo_project_manifest.json
  demo_logs/
    demo_forge_events.jsonl
  demo_parameters/
    demo_forge_parameters.json
```

Then Desktop can build demo project from seed files.

## Demo project manifest

Optional manifest:

```json
{
  "project_name": "Demo Forge",
  "description": "Synthetic economy sample for BalanceCraft Desktop 1.5",
  "events_path": "../demo_logs/demo_forge_events.jsonl",
  "parameters_path": "../demo_parameters/demo_forge_parameters.json",
  "default_build_id": "demo_1.0",
  "prepared_bindings": true,
  "prepared_metric_runs": true,
  "prepared_scenarios": true
}
```

## Acceptance criteria

Demo project is acceptable when:

```text
Open Demo Project works from Start screen.
Dashboard opens without external files.
Data Map shows at least 5 event types.
At least 2 P0 templates have configured bindings.
At least 1 metric chart renders.
At least 1 insight is visible and understandable.
What-if panel has at least 1 ready scenario or ready parameter.
Scenario does not mutate historical events.
Warnings are visible but not catastrophic.
README can explain the demo in under 2 minutes.
```

Stretch acceptance:

```text
All 4 P0 templates have configured bindings.
All 4 P0 charts render.
Analysis coverage shows available and missing problems.
Demo can be rebuilt from JSONL + parameters.
One GIF/video walkthrough can be recorded without manual setup.
```

## Data quality requirements

Demo data should intentionally include some imperfection, but not chaos.

Allowed:

- a few warnings;
- optional missing P1 signals;
- one mixed-type attribute if we want to demonstrate profiling;
- a few blocked operations.

Avoid:

- malformed JSON lines in default demo;
- too many event types;
- unclear entity ids;
- unreadable labels;
- random noise that hides intended patterns;
- values that make charts visually flat.

## Naming conventions

Use readable identifiers:

```text
day_01
coins
ore
order_basic
order_advanced
bellows_02
anvil_01
craft_order
```

Avoid:

```text
p_001
x7
skill_mega_thing
session_final_final2
```

## Review notes

Review together with UI batch:

1. Is `Demo Forge` a good enough sample, or should the demo be less RPG/idle-flavoured?
2. Should demo use `day` observations or `run` observations?
3. Should demo include optional broken/dirty rows, or keep default demo clean?
4. Should prepared metric runs be stored in demo DB, or generated on first open?
5. Resolved: prepared What-if Scenario A is mandatory for the complete BalanceCraft 1.5 demo; generic scenario management remains P1.
6. Which exact insight texts do we want visible in README screenshots?
7. Should demo include build comparison now, or keep `build_id` only as metadata?
