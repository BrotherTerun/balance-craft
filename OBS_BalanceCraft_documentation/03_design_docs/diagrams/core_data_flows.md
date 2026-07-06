# FILE: `03_design_docs/diagrams/core_data_flows.md`
# Core data flow diagrams

Дата: 2026-07-02  
Статус: рабочий черновик для Obsidian/Mermaid

## 1. P0 vertical slice

```mermaid
flowchart LR
  A["Create/Open Project"] --> B["Import JSONL"]
  B --> C["Store Raw Events"]
  C --> D["Build Data Profile"]
  D --> E["Configure Semantic Binding"]
  E --> F["Run Metric Calculation"]
  F --> G["Store Metric Values"]
  G --> H["Prepare Dashboard Dataset"]
  H --> I["Render Charts"]
  I --> J["Generate Practical Insights"]

  C -. "events are immutable" .-> C
  F -. "calculation warnings" .-> H
  J -. "evidence and recommendations" .-> I
```

## 2. Import and profiling flow

```mermaid
flowchart TB
  UI["Import UI"] --> API["Backend API Facade"]
  API --> Import["Import Service"]
  Import --> FS["Local JSONL Files"]

  Import --> Run["Create import_run"]
  Import --> File["Create source_file records"]
  Import --> Parse["Parse JSON lines"]
  Parse --> Validate["Validate event envelope"]

  Validate -->|valid| Normalize["Normalize to internal event model"]
  Validate -->|invalid| ErrorLog["Collect row errors"]

  Normalize --> UpsertEntities["Upsert entities"]
  Normalize --> UpsertObservations["Upsert observations"]
  Normalize --> InsertEvents["Insert raw events"]

  UpsertEntities --> DB[("SQLite")]
  UpsertObservations --> DB
  InsertEvents --> DB
  ErrorLog --> Run

  DB --> Profiler["Data Profiler"]
  Profiler --> Profile["event_attribute_profile"]
  Profile --> Coverage["Analysis Coverage Service"]
  Coverage --> Report["Import Report + Data Map State"]
  Report --> UI
```

## 3. Data map and analysis coverage

```mermaid
flowchart LR
  Events[("events")] --> Profiler["Data Profiler"]
  Profiler --> EventTypes["event_type counts"]
  Profiler --> Attributes["attribute keys"]
  Profiler --> Types["type distribution"]
  Profiler --> Ranges["numeric ranges"]
  Profiler --> Samples["sample values"]

  EventTypes --> DataMap["Data Map UI"]
  Attributes --> DataMap
  Types --> DataMap
  Ranges --> DataMap
  Samples --> DataMap

  EventTypes --> Coverage["Analysis Coverage Service"]
  Attributes --> Coverage
  Bindings[("semantic_bindings")] --> Coverage
  Params[("entity_parameters")] --> Coverage

  Coverage --> Available["available"]
  Coverage --> Partial["partially_available"]
  Coverage --> Missing["missing_data"]
  Coverage --> Unsupported["unsupported_in_version"]

  Available --> CoverageUI["Coverage UI"]
  Partial --> CoverageUI
  Missing --> CoverageUI
  Unsupported --> CoverageUI
```

## 4. Semantic binding to metric run

```mermaid
flowchart TB
  UI["Binding Wizard"] --> Templates["Metric Template Registry"]
  UI --> Profile["Data Profile"]
  Templates --> Draft["Draft Binding"]
  Profile --> Draft

  Draft --> Validate["Binding Validation"]
  Validate -->|warnings| UI
  Validate -->|ok or accepted warnings| Save["Save Binding Set"]

  Save --> BindingSet[("semantic_binding_sets")]
  Save --> Bindings[("semantic_bindings")]

  UI --> Run["Run Calculation"]
  Run --> Engine["Metric Engine"]
  BindingSet --> Engine
  Bindings --> Engine
  Templates --> Engine
  Events[("events")] --> Engine

  Engine --> SafeCalc["safe_div / N/A / warnings"]
  SafeCalc --> MetricRun[("metric_runs")]
  SafeCalc --> MetricValues[("metric_values")]
  MetricValues --> Dashboard["Dashboard Dataset"]
```

## 5. Dashboard and insights

```mermaid
flowchart LR
  UI["Dashboard UI"] --> API["getDashboardData"]
  API --> DashboardService["Dashboard Service"]
  DashboardService --> Runs[("metric_runs")]
  DashboardService --> Values[("metric_values")]

  Values --> Datasets["Chart datasets"]
  Values --> InsightEngine["Insight Engine"]
  Runs --> InsightEngine
  Warnings["calculation warnings"] --> InsightEngine
  Coverage["analysis coverage"] --> InsightEngine

  InsightEngine --> Insights["Insight cards"]
  Datasets --> UI
  Insights --> UI

  ScenarioResults[("scenario_results")] -. "optional overlay" .-> DashboardService
```

## 6. Simple What-if flow

```mermaid
flowchart TB
  UI["What-if Panel"] --> Controls["Get controllable parameters"]
  Params[("entity_parameters")] --> Controls
  Bindings[("semantic_bindings")] --> Controls
  Controls --> UI

  UI --> Scenario["Create Scenario"]
  Scenario --> Override["Add Parameter Override"]
  Override --> Confidence["Determine confidence_status"]

  Confidence -->|exact_recalc| Exact["Counterfactual recalculation"]
  Confidence -->|approx_recalc| Approx["Approximate recalculation"]
  Confidence -->|impact_estimate| Impact["Impact estimate"]
  Confidence -->|insufficient_model| StopModel["Return model limitation"]
  Confidence -->|insufficient_data| StopData["Return data limitation"]

  Exact --> Results[("scenario_results")]
  Approx --> Results
  Impact --> Results
  StopModel --> ScenarioState[("scenarios")]
  StopData --> ScenarioState
  Override --> Overrides[("scenario_overrides")]
  Scenario --> ScenarioState

  Results --> Compare["Comparison dataset"]
  Compare --> UI
```

## 7. Error and warning propagation

```mermaid
flowchart LR
  Service["Service layer"] --> Problem["Detected problem"]
  Problem --> Warning["Structured warning"]
  Problem --> Error["Structured error"]

  Warning --> Envelope["API Envelope"]
  Error --> Envelope

  Envelope --> UI["Frontend UI"]
  UI --> HumanText["Human-readable message"]
  UI --> Details["Technical details / debug"]

  StackTrace["Raw stack trace"] -. "not user-facing" .-> Details
```
