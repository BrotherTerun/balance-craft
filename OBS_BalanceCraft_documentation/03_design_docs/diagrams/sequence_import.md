# FILE: `docs/diagrams/sequence_import.md`

# Sequence diagram — JSONL import and profiling

Дата: 2026-07-02  
Статус: рабочий черновик для Obsidian/Mermaid

## Назначение

Диаграмма показывает основной путь импорта JSONL, сохранения raw-событий, профилирования данных и возврата import report в UI.

```mermaid
sequenceDiagram
  actor User as User
  participant UI as Frontend UI
  participant API as Backend API Facade
  participant Import as Import Service
  participant FS as Local Filesystem
  participant DB as DB Layer
  participant SQL as SQLite
  participant Profiler as Data Profiler
  participant Coverage as Analysis Coverage Service

  User->>UI: Select JSONL file/folder
  UI->>API: importEvents(project_id, source_path)
  API->>Import: startImport(project_id, source_path)
  Import->>FS: discover *.jsonl files
  FS-->>Import: file list

  Import->>DB: create import_run(status=running)
  DB->>SQL: INSERT import_runs
  SQL-->>DB: import_run_id
  DB-->>Import: import_run_id

  loop For each source file
    Import->>DB: create source_file(status=running)
    DB->>SQL: INSERT source_files
    Import->>FS: read lines

    loop For each line
      Import->>Import: parse JSON
      alt Valid event envelope
        Import->>Import: normalize event
        Import->>DB: upsert entity / observation
        DB->>SQL: INSERT OR UPDATE entities, observations
        Import->>DB: insert raw event
        DB->>SQL: INSERT events
      else Invalid line
        Import->>Import: collect row error
      end
    end

    Import->>DB: update source_file summary
    DB->>SQL: UPDATE source_files
  end

  Import->>Profiler: buildProfile(project_id)
  Profiler->>DB: read events
  DB->>SQL: SELECT events
  SQL-->>DB: raw event rows
  DB-->>Profiler: event rows
  Profiler->>DB: save event_attribute_profile
  DB->>SQL: UPSERT event_attribute_profile

  Profiler->>Coverage: checkBasicCoverage(project_id)
  Coverage->>DB: read profile / bindings / parameters
  DB->>SQL: SELECT profile, bindings, parameters
  SQL-->>DB: coverage inputs
  DB-->>Coverage: coverage inputs
  Coverage-->>Profiler: coverage summary

  Import->>DB: finish import_run(status=completed or completed_with_warnings)
  DB->>SQL: UPDATE import_runs
  Import-->>API: import report + warnings + coverage summary
  API-->>UI: envelope(success, data, warnings, errors)
  UI-->>User: Show import report and next action
```

## Notes

- `events` пишутся как raw history и дальше не изменяются.
- Битые строки не обязаны валить весь import run, если есть валидные события.
- Для P0 coverage может считаться на лету без записи в `analysis_coverage_cache`.
- Если Import Service не нашёл ни одного валидного события, UI должен показать failed import report, а не пустой dashboard.
