# Diagram: Architecture Context

Дата: 2026-07-02  
Статус: рабочая Mermaid-диаграмма для Obsidian  
Связанный документ: `../18_architecture_overview.md`

## 1. System context — MVP 1.5

```mermaid
flowchart LR
  User["User / game designer"]

  BC["BalanceCraft Desktop 1.5<br/>local balance analysis tool"]

  JSONL["Local JSONL files<br/>playtest logs / exported telemetry"]
  Demo["Demo project<br/>synthetic local dataset"]
  SQLite[("Local SQLite DB<br/>balancecraft.db")]
  FS["Local file system<br/>user-selected files and app data"]

  User -->|"opens app, imports data,<br/>configures bindings, reviews charts"| BC

  JSONL -->|"manual import"| BC
  Demo -->|"open demo"| BC
  BC -->|"read/write"| SQLite
  BC -->|"read selected files,<br/>store app/project data"| FS

  classDef p0 fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px,color:#111
  classDef store fill:#e3f2fd,stroke:#1565c0,stroke-width:1px,color:#111

  class BC,JSONL,Demo,FS p0
  class SQLite store
```

## 2. System context — future extensions

```mermaid
flowchart LR
  User["User / developer"]
  Game["Game / test build"]
  SDK["SDK Lite<br/>future P2"]
  Collector["Self-hosted Collector<br/>future P3"]
  ExternalSim["External game simulator<br/>future"]
  Export["Collector export<br/>JSONL/CSV future"]
  BC["BalanceCraft Desktop 1.5<br/>MVP local app"]
  SQLite[("Local SQLite DB")]

  User --> BC
  Game -.->|"writes local JSONL<br/>future SDK output"| SDK
  SDK -.->|"local JSONL"| BC
  SDK -.->|"batch upload<br/>only if configured"| Collector
  Collector -.->|"export"| Export
  Export -.->|"manual import"| BC

  BC -.->|"scenario config<br/>future adapter"| ExternalSim
  ExternalSim -.->|"generated events"| BC

  BC --> SQLite

  classDef p0 fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px,color:#111
  classDef future fill:#fff8e1,stroke:#f9a825,stroke-dasharray: 5 5,color:#111
  classDef store fill:#e3f2fd,stroke:#1565c0,color:#111

  class BC p0
  class SQLite store
  class SDK,Collector,ExternalSim,Export future
```

## 3. Context boundaries

```mermaid
flowchart TB
  subgraph MVP["MVP 1.5 boundary"]
    BC["BalanceCraft Desktop"]
    SQLite[("SQLite")]
    Demo["Demo project"]
    Import["Manual JSONL import"]
  end

  subgraph Future["Future / out of MVP"]
    SDK["SDK Lite"]
    Collector["Self-hosted Collector"]
    Cloud["BalanceCraft Cloud<br/>rejected alternative"]
    ExternalSim["External simulation adapter"]
  end

  Import --> BC
  Demo --> BC
  BC --> SQLite

  SDK -.-> Import
  Collector -.-> Import
  ExternalSim -.-> Import
  Cloud -.-x BC

  classDef mvp fill:#e8f5e9,stroke:#2e7d32,color:#111
  classDef future fill:#fff8e1,stroke:#f9a825,stroke-dasharray: 5 5,color:#111
  classDef rejected fill:#ffebee,stroke:#c62828,stroke-dasharray: 5 5,color:#111

  class BC,SQLite,Demo,Import mvp
  class SDK,Collector,ExternalSim future
  class Cloud rejected
```

## Notes

- BalanceCraft Cloud не является целевым компонентом.
- SDK Lite и Self-hosted Collector показаны только для архитектурной совместимости.
- Единственный runtime-storage MVP — локальный SQLite.
