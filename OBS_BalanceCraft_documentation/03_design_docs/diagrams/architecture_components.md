# Diagram: Architecture Components

Дата: 2026-07-02  
Статус: рабочая Mermaid-диаграмма для Obsidian  
Связанный документ: `../18_architecture_overview.md`

## 1. Backend components

```mermaid
flowchart TB
  Bridge["QWebChannel Bridge"]
  API["Backend API Facade"]

  Project["Project Service"]
  Settings["Settings Service"]
  Demo["Demo Project Service"]
  Import["Import Service"]
  Profiler["Data Profiler"]
  Coverage["Analysis Coverage Service"]
  Binding["Binding Service"]
  Templates["Metric Template Registry"]
  Metrics["Metric Engine"]
  Insights["Insight Engine"]
  WhatIf["What-if Engine"]
  DBLayer["DB Layer"]
  SQLite[("SQLite DB")]

  Bridge --> API

  API --> Project
  API --> Settings
  API --> Demo
  API --> Import
  API --> Profiler
  API --> Coverage
  API --> Binding
  API --> Metrics
  API --> Insights
  API --> WhatIf

  Project --> DBLayer
  Settings --> DBLayer
  Demo --> Project
  Demo --> Import
  Demo --> Binding
  Import --> DBLayer
  Profiler --> DBLayer
  Coverage --> Profiler
  Coverage --> Binding
  Coverage --> DBLayer
  Binding --> Templates
  Binding --> DBLayer
  Metrics --> Templates
  Metrics --> Binding
  Metrics --> DBLayer
  Insights --> Metrics
  Insights --> DBLayer
  WhatIf --> Metrics
  WhatIf --> DBLayer

  DBLayer --> SQLite

  classDef api fill:#f3e5f5,stroke:#6a1b9a,color:#111
  classDef service fill:#e8f5e9,stroke:#2e7d32,color:#111
  classDef db fill:#e3f2fd,stroke:#1565c0,color:#111

  class Bridge,API api
  class Project,Settings,Demo,Import,Profiler,Coverage,Binding,Templates,Metrics,Insights,WhatIf service
  class DBLayer,SQLite db
```

## 2. Frontend components

```mermaid
flowchart TB
  Shell["Desktop Shell<br/>QWebEngine host"]
  AppState["Frontend App State"]
  ApiClient["JS API Client<br/>QWebChannel wrapper"]

  Start["Start / Projects UI"]
  ProjectDash["Project Dashboard UI"]
  ImportUI["Import UI"]
  DataMap["Data Map UI"]
  CoverageUI["Analysis Coverage UI"]
  BindingUI["Binding Wizard UI"]
  Dashboard["Dashboard UI"]
  Charts["Chart Components<br/>Chart.js"]
  InsightPanel["Insight Panel UI"]
  WhatIfUI["What-if Panel UI"]
  SettingsUI["Settings UI"]
  ErrorUI["Empty/Error States"]

  Shell --> AppState
  AppState --> Start
  AppState --> ProjectDash
  AppState --> ImportUI
  AppState --> DataMap
  AppState --> CoverageUI
  AppState --> BindingUI
  AppState --> Dashboard
  AppState --> WhatIfUI
  AppState --> SettingsUI
  AppState --> ErrorUI

  Start --> ApiClient
  ProjectDash --> ApiClient
  ImportUI --> ApiClient
  DataMap --> ApiClient
  CoverageUI --> ApiClient
  BindingUI --> ApiClient
  Dashboard --> ApiClient
  WhatIfUI --> ApiClient
  SettingsUI --> ApiClient

  Dashboard --> Charts
  Dashboard --> InsightPanel

  ApiClient -->|"QWebChannel calls"| Backend["Backend API Facade"]

  classDef frontend fill:#f3e5f5,stroke:#6a1b9a,color:#111
  classDef backend fill:#e8f5e9,stroke:#2e7d32,color:#111

  class Shell,AppState,ApiClient,Start,ProjectDash,ImportUI,DataMap,CoverageUI,BindingUI,Dashboard,Charts,InsightPanel,WhatIfUI,SettingsUI,ErrorUI frontend
  class Backend backend
```

## 3. Component groups by vertical slice

```mermaid
flowchart LR
  subgraph ImportSlice["Import vertical slice"]
    ImportUI["Import UI"]
    ImportService["Import Service"]
    Profiler["Data Profiler"]
    Events[("events")]
    Profiles[("event_attribute_profile")]
  end

  subgraph BindingSlice["Binding vertical slice"]
    DataMap["Data Map UI"]
    BindingUI["Binding Wizard UI"]
    BindingService["Binding Service"]
    Templates["Metric Template Registry"]
    Bindings[("semantic_binding_sets<br/>semantic_bindings")]
  end

  subgraph MetricSlice["Metric vertical slice"]
    Dashboard["Dashboard UI"]
    MetricEngine["Metric Engine"]
    InsightEngine["Insight Engine"]
    Runs[("metric_runs")]
    Values[("metric_values")]
  end

  subgraph WhatIfSlice["What-if vertical slice"]
    WhatIfUI["What-if UI"]
    WhatIfEngine["What-if Engine"]
    Scenarios[("scenarios")]
    Results[("scenario_results")]
  end

  ImportUI --> ImportService --> Events
  ImportService --> Profiler --> Profiles
  DataMap --> BindingUI --> BindingService --> Bindings
  BindingService --> Templates
  Dashboard --> MetricEngine --> Runs
  MetricEngine --> Values
  MetricEngine --> InsightEngine
  WhatIfUI --> WhatIfEngine --> Scenarios
  WhatIfEngine --> Results

  Events --> BindingService
  Bindings --> MetricEngine
  Values --> InsightEngine
  Runs --> WhatIfEngine

  classDef slice fill:#f5f5f5,stroke:#616161,color:#111
```

## 4. Legacy migration component view

```mermaid
flowchart TB
  subgraph Legacy["Legacy prototype"]
    OldMain["main.py<br/>PySide/QWebEngine + MySQL API"]
    OldPipeline["pipeline.py<br/>MySQL import"]
    OldDB["db_init.py<br/>MySQL schema"]
    OldProgression["progression_model.py<br/>RPG progression metrics"]
    OldWhatIf["what_if_analysis.py<br/>items/skills/player/session based"]
    OldUI["app.js<br/>player/session UI"]
  end

  subgraph New["Target architecture"]
    Shell["Desktop App Shell"]
    API["Backend API Facade"]
    Import["Import Service"]
    DBLayer["SQLite DB Layer"]
    Metrics["Metric Engine"]
    WhatIf["What-if Engine"]
    UI["Universal Scope UI"]
  end

  OldMain -->|"keep shell idea,<br/>remove MySQL API"| Shell
  OldMain -->|"extract public methods"| API
  OldPipeline -->|"reuse JSONL validation ideas,<br/>rewrite storage"| Import
  OldDB -->|"replace"| DBLayer
  OldProgression -->|"generalize"| Metrics
  OldWhatIf -->|"generalize parameters/scenarios"| WhatIf
  OldUI -->|"replace player selector<br/>with scope selector"| UI

  classDef legacy fill:#ffebee,stroke:#c62828,color:#111
  classDef target fill:#e8f5e9,stroke:#2e7d32,color:#111

  class OldMain,OldPipeline,OldDB,OldProgression,OldWhatIf,OldUI legacy
  class Shell,API,Import,DBLayer,Metrics,WhatIf,UI target
```

## Notes

- `progression_model.py` может стать основой `metric_engine.py`, но только после удаления RPG/MySQL-зависимостей.
- `practical_insights.py` логически ближе всего к сохранению как отдельный `insight engine`.
- Старый player selector должен стать универсальным scope selector.
