# FILE: `03_design_docs/diagrams/ui_flow.md`
# UI Flow Diagrams

Дата: 2026-07-02  
Статус: проектный черновик для ревью

## Назначение

Этот файл содержит Mermaid-диаграммы пользовательского потока BalanceCraft Desktop 1.5.

Связанный документ: `../23_ui_flow_and_screen_map.md`.

## 1. Main UI flow

```mermaid
flowchart TD
  Start[Start / Project Hub]

  Start --> Demo[Open Demo Project]
  Start --> Create[Create Project]
  Start --> Open[Open Existing Project]
  Start --> Recent[Open Recent Project]

  Demo --> Overview[Project Dashboard / Overview]
  Create --> Import[Import Data]
  Open --> Overview
  Recent --> Overview

  Import --> ImportReport[Import Report]
  ImportReport --> DataMap[Data Map]
  Overview --> Import
  Overview --> DataMap
  Overview --> Coverage[Analysis Coverage]
  Overview --> Bindings[Binding Wizard]
  Overview --> Metrics[Metric Dashboard]
  Overview --> Insights[Insights Panel]
  Overview --> WhatIf[What-if Panel]
  Overview --> Settings[Project Settings]

  DataMap --> Coverage
  DataMap --> Bindings
  Coverage --> Bindings
  Coverage --> Import

  Bindings --> Metrics
  Metrics --> Insights
  Metrics --> WhatIf
  WhatIf --> Metrics
```

## 2. First launch demo walkthrough

```mermaid
flowchart LR
  Launch[Launch App]
  OpenDemo[Click Open Demo Project]
  ReadyDashboard[Ready Dashboard]
  DataMap[Inspect Data Map]
  Binding[Inspect Binding Wizard]
  RunMetric[Run Metric Calculation]
  Insight[Read Insight]
  Scenario[Run What-if Scenario]
  Compare[Compare Historical vs Scenario]

  Launch --> OpenDemo --> ReadyDashboard --> DataMap --> Binding --> RunMetric --> Insight --> Scenario --> Compare
```

## 3. User project happy path

```mermaid
flowchart TD
  CreateProject[Create Project]
  SelectSource[Select JSONL file/folder]
  Scan[Scan source]
  Import[Import events]
  Report[Read import report]
  Profile[Build/View Data Map]
  Coverage[View Analysis Coverage]
  Template[Choose Metric Template]
  Binding[Configure Semantic Binding]
  Validate[Validate Binding Draft]
  Save[Save Binding Set]
  Run[Run Metric Calculation]
  Dashboard[Open Metric Dashboard]
  Insights[Read Insights]
  WhatIf[Optional What-if]

  CreateProject --> SelectSource --> Scan --> Import --> Report --> Profile
  Profile --> Coverage --> Template --> Binding --> Validate --> Save --> Run --> Dashboard --> Insights --> WhatIf
```

## 4. Screen state progression

```mermaid
stateDiagram-v2
  [*] --> NoProject
  NoProject --> ProjectOpened: open demo / create / open project

  ProjectOpened --> NoEvents: new empty project
  ProjectOpened --> HasEvents: demo or imported events

  NoEvents --> Importing: importEvents
  Importing --> ImportFailed: fatal error
  Importing --> HasEvents: success / partial success
  ImportFailed --> NoEvents: retry or change source

  HasEvents --> ProfileReady: build profile
  ProfileReady --> BindingMissing: no binding set
  BindingMissing --> BindingReady: save binding set

  BindingReady --> MetricRunMissing: no metric run
  MetricRunMissing --> Calculating: run metric calculation
  Calculating --> MetricRunFailed: calculation error
  Calculating --> DashboardReady: success / warnings
  MetricRunFailed --> BindingReady: fix binding or rerun

  DashboardReady --> InsightsReady: generate insights
  DashboardReady --> WhatIfReady: parameters available
  WhatIfReady --> ScenarioReady: run scenario
```

## 5. Navigation grouping

```mermaid
flowchart LR
  subgraph ProjectLevel[Project-level screens]
    Hub[Project Hub]
    Overview[Overview]
    Settings[Settings]
  end

  subgraph DataLevel[Data preparation]
    Import[Import]
    Report[Import Report]
    DataMap[Data Map]
    Coverage[Analysis Coverage]
  end

  subgraph AnalysisLevel[Analysis setup]
    Templates[Templates in Wizard]
    Binding[Binding Wizard]
    MetricRuns[Metric Runs]
  end

  subgraph ResultLevel[Results]
    Dashboard[Metric Dashboard]
    Insights[Insights]
    WhatIf[What-if]
  end

  Hub --> Overview
  Overview --> DataLevel
  DataLevel --> AnalysisLevel
  AnalysisLevel --> ResultLevel
```

## 6. Demo project internal flow

```mermaid
flowchart TD
  DemoSeed[Demo Seed Files or Prebuilt DB]
  DemoEvents[Demo JSONL Events]
  DemoParams[Demo Parameters]
  DemoBindings[Prepared Binding Sets]
  DemoRuns[Prepared Metric Runs]
  DemoScenarios[Prepared Scenarios]

  DemoSeed --> DemoEvents
  DemoSeed --> DemoParams
  DemoEvents --> DemoBindings
  DemoParams --> DemoScenarios
  DemoBindings --> DemoRuns
  DemoRuns --> DemoDashboard[Ready Demo Dashboard]
  DemoScenarios --> DemoWhatIf[Ready What-if Panel]
  DemoDashboard --> DemoWalkthrough[README / GIF Walkthrough]
  DemoWhatIf --> DemoWalkthrough
```

## 7. UI calls backend contract map

```mermaid
flowchart TD
  Hub[Project Hub] --> ProjectAPI[Project API]
  ImportScreen[Import Screen] --> ImportAPI[Import API]
  DataMap[Data Map] --> ProfileAPI[Profile API]
  Coverage[Analysis Coverage] --> CoverageAPI[Coverage API]
  BindingWizard[Binding Wizard] --> BindingAPI[Binding API]
  MetricDashboard[Metric Dashboard] --> MetricsAPI[Metrics API]
  InsightPanel[Insights Panel] --> InsightsAPI[Insights API]
  WhatIfPanel[What-if Panel] --> ScenarioAPI[What-if API]
  Settings[Settings] --> SettingsAPI[Settings API]

  ProjectAPI --> Envelope[Common Response Envelope]
  ImportAPI --> Envelope
  ProfileAPI --> Envelope
  CoverageAPI --> Envelope
  BindingAPI --> Envelope
  MetricsAPI --> Envelope
  InsightsAPI --> Envelope
  ScenarioAPI --> Envelope
  SettingsAPI --> Envelope
```

## 8. MVP vs future UI boundary

```mermaid
flowchart TB
  subgraph MVP[BalanceCraft Desktop 1.5 UI]
    Hub[Project Hub]
    Demo[Demo Project]
    Import[JSONL Import]
    DataMap[Data Map]
    Binding[Binding Wizard]
    Dashboard[Metric Dashboard]
    Insights[Insights]
    WhatIf[Simple What-if]
  end

  subgraph Future[Future UI / Not MVP]
    Accounts[Accounts / Cloud Auth]
    CollectorAdmin[Collector Admin UI]
    SDKConfig[SDK Configuration UI]
    BI[Full BI Dashboard Builder]
    FormulaEditor[Custom Formula Editor]
    VisualModel[Visual Economy Model Editor]
  end

  MVP -. not in 1.5 .-> Future
```
