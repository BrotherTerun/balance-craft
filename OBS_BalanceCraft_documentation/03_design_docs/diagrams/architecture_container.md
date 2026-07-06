# Diagram: Architecture Container

Дата: 2026-07-02  
Статус: рабочая Mermaid-диаграмма для Obsidian  
Связанный документ: `../18_architecture_overview.md`

## 1. Container diagram — Desktop MVP

```mermaid
flowchart LR
  User["User"]

  subgraph Desktop["BalanceCraft Desktop process"]
    Shell["Desktop App Shell<br/>PySide6 / QWebEngine"]
    UI["Frontend UI<br/>HTML / CSS / JS / Chart.js"]
    Bridge["QWebChannel Bridge<br/>JS ⇄ Python"]
    API["Backend API Facade<br/>structured envelope"]
    Services["Backend Services<br/>project/import/profile/binding/metrics/insights/what-if"]
    DBLayer["DB Layer<br/>SQLite connection, migrations, transactions"]
  end

  DB[("SQLite DB<br/>local")]
  Files["Local files<br/>JSONL / demo / parameters"]

  User -->|"interacts"| Shell
  Shell -->|"hosts"| UI
  UI -->|"calls methods"| Bridge
  Bridge -->|"invokes"| API
  API --> Services
  Services --> DBLayer
  DBLayer --> DB

  Files -->|"selected/imported by user"| Services

  Services -->|"datasets, warnings, errors"| API
  API -->|"JSON envelope"| Bridge
  Bridge -->|"response"| UI
  UI -->|"charts / tables / insights"| User

  classDef ui fill:#f3e5f5,stroke:#6a1b9a,color:#111
  classDef backend fill:#e8f5e9,stroke:#2e7d32,color:#111
  classDef store fill:#e3f2fd,stroke:#1565c0,color:#111
  classDef file fill:#fff8e1,stroke:#f9a825,color:#111

  class Shell,UI,Bridge ui
  class API,Services,DBLayer backend
  class DB store
  class Files file
```

## 2. Container responsibilities

```mermaid
flowchart TB
  UI["Frontend UI"] --> UIResp["Responsible for:<br/>screens, forms, charts,<br/>warnings display, navigation"]

  API["Backend API Facade"] --> APIResp["Responsible for:<br/>stable QWebChannel methods,<br/>success/data/warnings/errors envelope"]

  Services["Backend Services"] --> ServicesResp["Responsible for:<br/>business logic,<br/>import, profiling, bindings,<br/>metric runs, insights, scenarios"]

  DBLayer["DB Layer"] --> DBResp["Responsible for:<br/>connection, migrations,<br/>transactions, SQL helpers"]

  SQLite[("SQLite")] --> StoreResp["Stores:<br/>projects, events, profiles,<br/>bindings, metric runs,<br/>metric values, scenarios"]

  classDef box fill:#f5f5f5,stroke:#616161,color:#111
  class UI,API,Services,DBLayer,SQLite,UIResp,APIResp,ServicesResp,DBResp,StoreResp box
```

## 3. Forbidden container shortcuts

```mermaid
flowchart LR
  UI["Frontend UI"]
  DB[("SQLite DB")]
  Import["Import Service"]
  Chart["Chart.js rendering"]
  Metric["Metric Engine"]
  DOM["DOM / UI state"]
  MySQL[("MySQL Server<br/>legacy")]
  InfoSchema["INFORMATION_SCHEMA<br/>legacy"]

  UI -. forbidden .-> DB
  Import -. forbidden .-> Chart
  Metric -. forbidden .-> DOM
  MySQL -. forbidden .-> UI
  InfoSchema -. forbidden .-> Metric

  classDef forbidden fill:#ffebee,stroke:#c62828,stroke-dasharray: 5 5,color:#111
  class UI,DB,Import,Chart,Metric,DOM,MySQL,InfoSchema forbidden
```

## Notes

- Контейнеры не означают отдельные процессы.
- MVP остаётся desktop-монолитом, но с внутренними архитектурными слоями.
- Главный запрет: UI не должен напрямую зависеть от SQL или старой MySQL-модели.
