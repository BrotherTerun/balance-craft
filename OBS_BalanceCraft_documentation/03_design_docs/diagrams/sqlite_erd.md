# SQLite ERD diagrams

Дата: 2026-07-02  
Статус: рабочий проектировочный черновик  
Связанный документ: `../20_sqlite_schema_design.md`

## 1. Быстрая карта групп таблиц

```mermaid
flowchart TD
  App[App-level tables] --> Settings[app_settings]
  App --> Migrations[schema_migrations]

  Project[Project core] --> Projects[projects]
  Projects --> Import[Import layer]
  Projects --> Data[Raw data layer]
  Projects --> Binding[Semantic binding layer]
  Projects --> Metrics[Metric layer]
  Projects --> Params[Parameter layer]
  Projects --> Scenarios[What-if layer]
  Projects --> Coverage[Analysis coverage P1]

  Import --> ImportRuns[import_runs]
  Import --> SourceFiles[source_files]

  Data --> Entities[entities]
  Data --> Observations[observations]
  Data --> Events[events]
  Data --> Profile[event_attribute_profile]

  Binding --> BindingSets[semantic_binding_sets]
  Binding --> SemanticBindings[semantic_bindings]
  Binding --> Templates[metric_templates]

  Metrics --> MetricRuns[metric_runs]
  Metrics --> MetricValues[metric_values]

  Params --> ParameterCatalogs[parameter_catalogs]
  Params --> EntityParameters[entity_parameters]
  Params --> ValueNormalization[value_normalization_profiles P1]

  Scenarios --> ScenarioTable[scenarios]
  Scenarios --> Overrides[scenario_overrides]
  Scenarios --> Results[scenario_results]

  Coverage --> AnalysisCoverage[analysis_coverage_cache P1]
```

## 2. P0 physical ERD

```mermaid
erDiagram
  PROJECTS {
    integer id PK
    text name
    text created_at
    text updated_at
    text last_opened_at
    text default_build_id
    text settings_json
  }

  APP_SETTINGS {
    text key PK
    text value_json
    text updated_at
  }

  SCHEMA_MIGRATIONS {
    integer version PK
    text name
    text applied_at
    text checksum
  }

  IMPORT_RUNS {
    integer id PK
    integer project_id FK
    text source_path
    text started_at
    text finished_at
    text status
    integer source_files_count
    integer read_lines
    integer valid_events
    integer invalid_events
    integer imported_events
    text warnings_json
    text errors_json
  }

  SOURCE_FILES {
    integer id PK
    integer import_run_id FK
    integer project_id FK
    text file_path
    text file_name
    text file_hash
    integer lines_count
    integer valid_events
    integer invalid_events
    text status
    text errors_json
  }

  ENTITIES {
    integer id PK
    integer project_id FK
    text entity_id UK
    text entity_type
    text label
    text metadata_json
    text created_at
    text updated_at
  }

  OBSERVATIONS {
    integer id PK
    integer project_id FK
    text observation_id UK
    text observation_type
    text started_at
    text ended_at
    text build_id
    text metadata_json
  }

  EVENTS {
    integer id PK
    integer project_id FK
    integer import_run_id FK
    integer source_file_id FK
    integer source_line_number
    text timestamp
    integer event_order
    text entity_id
    text entity_type
    text observation_id
    text observation_type
    text event_type
    text build_id
    text schema_version
    text source_id
    text attributes_json
  }

  EVENT_ATTRIBUTE_PROFILE {
    integer id PK
    integer project_id FK
    text event_type
    text attribute_key
    text attribute_path
    integer total_count
    integer numeric_count
    integer string_count
    integer boolean_count
    integer null_count
    integer missing_count
    real min_value
    real max_value
    text sample_values_json
    text last_profiled_at
  }

  METRIC_TEMPLATES {
    integer id PK
    text template_key UK
    text version
    text name
    text description
    text priority
    text variables_json
    text metrics_json
    text default_formulas_json
    integer is_builtin
    text created_at
    text updated_at
  }

  SEMANTIC_BINDING_SETS {
    integer id PK
    integer project_id FK
    text template_key
    text name
    text scope_json
    text status
    text warnings_json
    text created_at
    text updated_at
  }

  SEMANTIC_BINDINGS {
    integer id PK
    integer binding_set_id FK
    integer project_id FK
    text variable_key
    text source_kind
    text source_path
    text event_types_json
    text aggregation
    text filters_json
    text unit
    text label
    integer is_required
    text status
    text warnings_json
  }

  METRIC_RUNS {
    integer id PK
    integer project_id FK
    text template_key
    integer binding_set_id FK
    text scope_json
    text binding_snapshot_json
    text formula_snapshot_json
    text started_at
    text finished_at
    text status
    text warnings_json
    text errors_json
  }

  METRIC_VALUES {
    integer id PK
    integer metric_run_id FK
    integer project_id FK
    text metric_key
    text metric_label
    text scope_key
    text entity_id
    text observation_id
    text event_type
    text build_id
    integer x_index
    text x_label
    text x_timestamp
    real value_number
    text value_text
    text status
    text warnings_json
    text metadata_json
  }

  PROJECTS ||--o{ IMPORT_RUNS : has
  PROJECTS ||--o{ SOURCE_FILES : has
  IMPORT_RUNS ||--o{ SOURCE_FILES : contains
  PROJECTS ||--o{ ENTITIES : catalogs
  PROJECTS ||--o{ OBSERVATIONS : catalogs
  PROJECTS ||--o{ EVENTS : owns
  IMPORT_RUNS ||--o{ EVENTS : imports
  SOURCE_FILES ||--o{ EVENTS : contains
  PROJECTS ||--o{ EVENT_ATTRIBUTE_PROFILE : profiles
  PROJECTS ||--o{ SEMANTIC_BINDING_SETS : has
  SEMANTIC_BINDING_SETS ||--o{ SEMANTIC_BINDINGS : contains
  PROJECTS ||--o{ SEMANTIC_BINDINGS : owns
  PROJECTS ||--o{ METRIC_RUNS : has
  SEMANTIC_BINDING_SETS ||--o{ METRIC_RUNS : used_by
  METRIC_RUNS ||--o{ METRIC_VALUES : produces
  PROJECTS ||--o{ METRIC_VALUES : owns
```

### Примечание по ERD

`events.entity_id` и `events.observation_id` являются soft relationships к `entities.entity_id` и `observations.observation_id` внутри одного `project_id`.

Mermaid ERD выше не показывает soft relationship как FK, потому что в P0 это не жёсткая ссылочная связь.

## 3. Parameters + What-if ERD

```mermaid
erDiagram
  PROJECTS {
    integer id PK
    text name
  }

  PARAMETER_CATALOGS {
    integer id PK
    integer project_id FK
    text catalog_id UK
    text name
    text build_id
    text schema_version
    text source_path
    text created_at
    text metadata_json
  }

  ENTITY_PARAMETERS {
    integer id PK
    integer project_id FK
    integer catalog_id FK
    text entity_id
    text entity_type
    text parameter_key
    text value_type
    real value_number
    text value_text
    integer value_bool
    text value_json
    text unit
    text valid_from
    text valid_to
    text build_id
    text metadata_json
  }

  METRIC_RUNS {
    integer id PK
    integer project_id FK
    text template_key
    integer binding_set_id FK
    text status
  }

  SCENARIOS {
    integer id PK
    integer project_id FK
    text name
    text description
    integer base_metric_run_id FK
    text created_at
    text updated_at
    text status
    text confidence_status
    text warnings_json
  }

  SCENARIO_OVERRIDES {
    integer id PK
    integer scenario_id FK
    integer project_id FK
    text entity_id
    text parameter_key
    text override_mode
    real original_value_number
    real scenario_value_number
    text original_value_text
    text scenario_value_text
    real multiplier
    real delta
    text metadata_json
  }

  SCENARIO_RESULTS {
    integer id PK
    integer scenario_id FK
    integer project_id FK
    text metric_key
    text metric_label
    text scope_key
    text entity_id
    text observation_id
    integer x_index
    text x_label
    text x_timestamp
    real historical_value_number
    real scenario_value_number
    real delta_value
    real delta_percent
    text status
    text confidence_status
    text warnings_json
    text metadata_json
  }

  PROJECTS ||--o{ PARAMETER_CATALOGS : has
  PROJECTS ||--o{ ENTITY_PARAMETERS : has
  PARAMETER_CATALOGS ||--o{ ENTITY_PARAMETERS : contains
  PROJECTS ||--o{ SCENARIOS : has
  METRIC_RUNS ||--o{ SCENARIOS : base_for
  SCENARIOS ||--o{ SCENARIO_OVERRIDES : changes
  SCENARIOS ||--o{ SCENARIO_RESULTS : produces
  PROJECTS ||--o{ SCENARIO_OVERRIDES : owns
  PROJECTS ||--o{ SCENARIO_RESULTS : owns
```

## 4. P1 extension ERD

```mermaid
erDiagram
  PROJECTS {
    integer id PK
    text name
  }

  ANALYSIS_COVERAGE_CACHE {
    integer id PK
    integer project_id FK
    text problem_key
    text problem_label
    text status
    text required_signals_json
    text available_signals_json
    text missing_signals_json
    text template_key
    text last_checked_at
    text metadata_json
  }

  VALUE_NORMALIZATION_PROFILES {
    integer id PK
    integer project_id FK
    text name
    text value_unit
    text mapping_rules_json
    text created_at
    text updated_at
  }

  PROJECTS ||--o{ ANALYSIS_COVERAGE_CACHE : caches
  PROJECTS ||--o{ VALUE_NORMALIZATION_PROFILES : defines
```

## 5. Import and profiling slice

```mermaid
flowchart LR
  JSONL[JSONL files] --> ImportRun[import_runs]
  ImportRun --> SourceFiles[source_files]
  SourceFiles --> Events[events]
  Events --> Entities[entities upsert]
  Events --> Observations[observations upsert]
  Events --> Profile[event_attribute_profile]
  Profile --> DataMap[Data Map UI]
```

## 6. Metric calculation slice

```mermaid
flowchart LR
  Templates[metric_templates / code registry] --> BindingSet[semantic_binding_sets]
  BindingSet --> Bindings[semantic_bindings]
  Events[events] --> Engine[metric engine]
  Bindings --> Engine
  Engine --> Run[metric_runs]
  Run --> Values[metric_values]
  Values --> Dashboard[Dashboard datasets]
  Values --> Insights[Insight engine]
```

## 7. What-if slice

```mermaid
flowchart LR
  Params[entity_parameters] --> Scenario[scenarios]
  Scenario --> Overrides[scenario_overrides]
  MetricRun[base metric_runs] --> WhatIf[what-if engine]
  Overrides --> WhatIf
  Params --> WhatIf
  WhatIf --> Results[scenario_results]
  Results --> Compare[Scenario comparison UI]
  Results --> Confidence[confidence_status]
```

## 8. Legacy mapping reminder

```mermaid
flowchart TD
  OldPlayers[players] --> NewEntities[entities]
  OldSessions[sessions] --> NewObservations[observations]
  OldEvents[events] --> NewEvents[events + attributes_json]
  OldItems[items] --> NewEntityParameters[entity_parameters or entity_type=item]
  OldSkills[skills] --> NewEntityParameters
  OldSessionMetrics[session_metrics] --> NewMetricValues[metric_runs + metric_values]
  OldSimulationResults[simulation_results] --> NewScenarioResults[scenarios + scenario_results]
  MySQL[MySQL runtime] --> SQLite[SQLite local database]
```

## 9. Что важно помнить при чтении диаграмм

- `entities` и `observations` — универсальные справочники, а не обязательные игроки/сессии.
- `events.attributes_json` — raw payload, не нормализованный attribute warehouse.
- `event_attribute_profile` — карта данных, а не источник истины.
- `metric_values.project_id` — намеренная денормализация.
- What-if не меняет `events` и `metric_values`.
- `analysis_coverage_cache` и `value_normalization_profiles` — P1, не обязательный P0.

