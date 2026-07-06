# FILE: `docs/diagrams/migration_overview.md`

# Migration Overview Diagrams

Дата: 2026-07-02  
Статус: рабочий проектный документ

## Назначение

Этот файл показывает миграцию BalanceCraft от старого учебно-дипломного прототипа к новой архитектуре BalanceCraft Desktop 1.5.

Главная мысль:

```text
Мы не “допиливаем MySQL RPG progression analyzer”.
Мы переносим доказанные UI/аналитические идеи в новое local-first ядро.
```

## 1. High-level migration map

```mermaid
flowchart LR
  subgraph OLD[Old prototype]
    OLD_UI[PySide6 + QWebEngine UI]
    OLD_JS[HTML/CSS/JS + Chart.js]
    OLD_BACKEND[Python backend scripts]
    OLD_MYSQL[(MySQL runtime)]
    OLD_MODEL[players / sessions / events / items / skills / session_metrics]
    OLD_RPG[RPG progression framing]
  end

  subgraph KEEP[Keep / adapt]
    KEEP_SHELL[Desktop shell idea]
    KEEP_UI[Frontend panels and charts]
    KEEP_WIZARD[Binding Wizard concept]
    KEEP_INSIGHTS[Practical insights concept]
    KEEP_WHATIF[What-if panel concept]
  end

  subgraph NEW[BalanceCraft Desktop 1.5]
    NEW_SQLITE[(SQLite local DB)]
    NEW_MODEL[projects / entities / observations / events / parameters / metrics / scenarios]
    NEW_SERVICES[Modular backend services]
    NEW_BINDING[Late semantic binding]
    NEW_TEMPLATES[Universal metric templates]
    NEW_UI[Scope-based UI]
    NEW_LOCAL[Local-first product frame]
  end

  OLD_UI --> KEEP_SHELL
  OLD_JS --> KEEP_UI
  OLD_BACKEND --> KEEP_WIZARD
  OLD_BACKEND --> KEEP_INSIGHTS
  OLD_BACKEND --> KEEP_WHATIF

  KEEP_SHELL --> NEW_UI
  KEEP_UI --> NEW_UI
  KEEP_WIZARD --> NEW_BINDING
  KEEP_INSIGHTS --> NEW_SERVICES
  KEEP_WHATIF --> NEW_SERVICES

  OLD_MYSQL -. remove .-> NEW_SQLITE
  OLD_MODEL -. replace .-> NEW_MODEL
  OLD_RPG -. generalize .-> NEW_TEMPLATES

  NEW_SQLITE --> NEW_SERVICES
  NEW_MODEL --> NEW_SERVICES
  NEW_BINDING --> NEW_SERVICES
  NEW_TEMPLATES --> NEW_SERVICES
  NEW_SERVICES --> NEW_UI
  NEW_LOCAL --> NEW_UI
```

## 2. Data model migration

```mermaid
erDiagram
  OLD_PLAYERS {
    int id
    string name
  }

  OLD_SESSIONS {
    int id
    int player_id
    datetime started_at
  }

  OLD_ITEMS {
    int id
    string item_name
  }

  OLD_SKILLS {
    int id
    string skill_name
  }

  OLD_EVENTS {
    int id
    int player_id
    int session_id
    string event_type
    json payload
  }

  OLD_SESSION_METRICS {
    int id
    int session_id
    float metric_value
  }

  NEW_ENTITIES {
    int id
    string entity_id
    string entity_type
  }

  NEW_OBSERVATIONS {
    int id
    string observation_id
    string observation_type
  }

  NEW_EVENTS {
    int id
    string entity_id
    string observation_id
    string event_type
    json attributes_json
  }

  NEW_ENTITY_PARAMETERS {
    int id
    string entity_id
    string parameter_key
    string value
  }

  NEW_METRIC_RUNS {
    int id
    string template_key
    json binding_snapshot_json
  }

  NEW_METRIC_VALUES {
    int id
    int metric_run_id
    string metric_key
    float value
    string status
  }

  OLD_PLAYERS ||--o{ OLD_SESSIONS : owns
  OLD_PLAYERS ||--o{ OLD_EVENTS : produces
  OLD_SESSIONS ||--o{ OLD_EVENTS : groups
  OLD_SESSIONS ||--o{ OLD_SESSION_METRICS : aggregates

  OLD_PLAYERS -. becomes_entity_type_actor .-> NEW_ENTITIES
  OLD_SESSIONS -. becomes_observation_type_session .-> NEW_OBSERVATIONS
  OLD_ITEMS -. becomes_entity_type_item_or_parameterized_entity .-> NEW_ENTITIES
  OLD_SKILLS -. becomes_entity_type_skill_or_action .-> NEW_ENTITIES
  OLD_EVENTS -. becomes_neutral_event .-> NEW_EVENTS
  OLD_SESSION_METRICS -. replaced_by_metric_runs_values .-> NEW_METRIC_RUNS
  OLD_SESSION_METRICS -. replaced_by_metric_runs_values .-> NEW_METRIC_VALUES

  NEW_ENTITIES ||--o{ NEW_EVENTS : referenced_by_entity_id
  NEW_OBSERVATIONS ||--o{ NEW_EVENTS : referenced_by_observation_id
  NEW_ENTITIES ||--o{ NEW_ENTITY_PARAMETERS : has
  NEW_METRIC_RUNS ||--o{ NEW_METRIC_VALUES : produces
```

## 3. Module migration map

```mermaid
flowchart TB
  subgraph LEGACY[Legacy files / responsibilities]
    MAIN[main.py]
    PIPELINE[pipeline.py]
    DBINIT[db_init.py]
    PROGRESSION[progression_model.py]
    WHATIF[what_if_analysis.py]
    INSIGHTS[practical_insights.py]
    STABILITY[stability_analysis.py]
    APPJS[app.js]
  end

  subgraph TARGET[Target modules]
    APP_SHELL[app shell]
    DB_LAYER[db layer]
    PROJECT_SERVICE[project service]
    IMPORT_SERVICE[import service]
    PROFILER[data profiler]
    COVERAGE[analysis coverage service]
    BINDING[binding service]
    METRIC[metric engine]
    INSIGHT_ENGINE[insight engine]
    WHATIF_ENGINE[what-if engine]
    FRONTEND[frontend UI]
  end

  MAIN --> APP_SHELL
  MAIN --> PROJECT_SERVICE
  MAIN --> DB_LAYER

  PIPELINE --> IMPORT_SERVICE
  PIPELINE --> PROFILER

  DBINIT --> DB_LAYER

  PROGRESSION --> METRIC
  PROGRESSION --> INSIGHT_ENGINE

  WHATIF --> WHATIF_ENGINE

  INSIGHTS --> INSIGHT_ENGINE
  STABILITY --> INSIGHT_ENGINE

  APPJS --> FRONTEND
  APPJS --> BINDING
  APPJS --> WHATIF_ENGINE

  DB_LAYER --> TARGET_DONE[(SQLite runtime)]
```

## 4. Runtime dependency cleanup

```mermaid
flowchart LR
  START[Existing runtime] --> FIND[Find forbidden runtime dependencies]

  FIND --> MYSQL[mysql.connector]
  FIND --> CONFIG[DB_CONFIG / root password]
  FIND --> INFO_SCHEMA[INFORMATION_SCHEMA]
  FIND --> RPG_DB[monitor_rpg_model]
  FIND --> LEGACY_TABLES[required players/sessions/items/skills]

  MYSQL --> REMOVE[Remove from runtime]
  CONFIG --> REMOVE
  INFO_SCHEMA --> REPLACE[Replace with SQLite PRAGMA / explicit schema services]
  RPG_DB --> PROJECT_DB[Project-based SQLite DB]
  LEGACY_TABLES --> ENTITY_MODEL[Entity / Observation / Event model]

  REMOVE --> TEST[Run legacy grep checklist]
  REPLACE --> TEST
  PROJECT_DB --> TEST
  ENTITY_MODEL --> TEST

  TEST --> PASS{No forbidden runtime references?}
  PASS -->|yes| READY[Runtime migration acceptable]
  PASS -->|no| FIX[Patch code and repeat]
  FIX --> TEST
```

## 5. Vertical slice migration order

```mermaid
flowchart TD
  A[0. Freeze scope and DoD] --> B[1. Create SQLite schema]
  B --> C[2. Implement db layer]
  C --> D[3. Create/open project]
  D --> E[4. Import one JSONL file]
  E --> F[5. Store events/entities/observations]
  F --> G[6. Build data profile]
  G --> H[7. Save one binding set]
  H --> I[8. Run one metric template]
  I --> J[9. Store metric run and values]
  J --> K[10. Return dashboard dataset]
  K --> L[11. Draw chart]
  L --> M[12. Show one insight]
  M --> N[13. Optional simple What-if]
  N --> O[14. Demo acceptance]
```

## 6. What gets deleted, adapted, and postponed

```mermaid
flowchart LR
  subgraph DELETE[Delete / remove from runtime]
    D1[MySQL runtime]
    D2[root password / DB_CONFIG]
    D3[INFORMATION_SCHEMA]
    D4[hardcoded monitor_rpg_model]
    D5[required genre tables]
  end

  subgraph ADAPT[Adapt / keep idea]
    A1[PySide6 shell]
    A2[QWebChannel bridge]
    A3[Chart.js dashboard]
    A4[Binding Wizard]
    A5[Practical insights]
    A6[What-if panel]
  end

  subgraph POSTPONE[Postpone]
    P1[SDK Lite]
    P2[Self-hosted Collector]
    P3[Formula editor]
    P4[External simulation]
    P5[Cloud]
  end

  subgraph BUILD[Build now]
    B1[SQLite]
    B2[Universal events]
    B3[Data profiling]
    B4[Semantic binding]
    B5[Metric templates]
    B6[Dashboard]
    B7[Demo project]
  end

  DELETE --> BUILD
  ADAPT --> BUILD
  POSTPONE -. keep as future extension .-> BUILD
```

## 7. Legacy terminology migration

```mermaid
flowchart TB
  subgraph OLD_TERMS[Old terms]
    PLAYER[Player]
    SESSION[Session]
    ITEM[Item]
    SKILL[Skill]
    XP[XP / RPG progression]
  end

  subgraph NEW_CORE[New core terms]
    ENTITY[Entity]
    OBSERVATION[Observation]
    PARAMETER[Parameter]
    EVENT[Event attribute]
    METRIC[Metric template]
  end

  PLAYER -->|possible entity_type=actor/player| ENTITY
  SESSION -->|possible observation_type=session/run| OBSERVATION
  ITEM -->|possible entity_type=item or parameterized object| ENTITY
  ITEM --> PARAMETER
  SKILL -->|possible entity_type=skill/action| ENTITY
  SKILL --> PARAMETER
  XP -->|possible attribute or metric meaning| EVENT
  XP --> METRIC
```

## Review checklist

```text
[ ] Диаграммы не создают впечатление, что старую БД нужно мигрировать “как есть”.
[ ] MySQL явно показан как runtime dependency to remove.
[ ] players/sessions/items/skills не исчезают из мира вообще, но перестают быть ядром.
[ ] Vertical slice начинается с SQLite и заканчивается chart + insight.
[ ] SDK/Collector показаны как future, а не как скрытый MVP scope.
[ ] What-if не выглядит как полноценная симуляция игры.
```

## Notes

Эта диаграмма не является планом переноса существующих пользовательских данных. На текущем этапе старый прототип рассматривается как источник идей, UI-направлений и частично переиспользуемых модулей, но не как схема, которую нужно механически сохранить.
