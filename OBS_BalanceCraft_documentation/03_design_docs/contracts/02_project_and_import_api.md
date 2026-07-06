# FILE: `docs/contracts/02_project_and_import_api.md`

# 02. Project lifecycle and import API

Дата: 2026-07-02  
Статус: proposed

## Назначение

Файл описывает API для:

- состояния приложения;
- списка проектов;
- создания/открытия проекта;
- demo project;
- импорта JSONL;
- отчёта импорта.

## Common DTOs

### ProjectSummary

```json
{
  "project_id": 1,
  "name": "Demo Economy",
  "created_at": "2026-07-02T12:00:00Z",
  "updated_at": "2026-07-02T12:30:00Z",
  "last_opened_at": "2026-07-02T12:30:00Z",
  "default_build_id": "demo-1.0",
  "events_count": 1250,
  "entities_count": 42,
  "observations_count": 25,
  "metric_runs_count": 3,
  "last_import_run_id": 7,
  "last_import_status": "completed_with_warnings",
  "is_demo": true
}
```

### ImportReport

```json
{
  "import_run_id": 7,
  "project_id": 1,
  "status": "completed_with_warnings",
  "source_path": "H:/BalanceCraft/demo_logs",
  "started_at": "2026-07-02T12:10:00Z",
  "finished_at": "2026-07-02T12:10:04Z",
  "source_files_count": 2,
  "read_lines": 1000,
  "valid_events": 980,
  "invalid_events": 20,
  "imported_events": 980,
  "created_entities": 12,
  "created_observations": 8,
  "source_files": []
}
```

### SourceFileReport

```json
{
  "source_file_id": 14,
  "file_name": "events_run_001.jsonl",
  "file_path": "H:/BalanceCraft/demo_logs/events_run_001.jsonl",
  "file_hash": "sha256:...",
  "lines_count": 500,
  "valid_events": 490,
  "invalid_events": 10,
  "status": "completed_with_warnings",
  "errors_sample": [
    {
      "line_number": 22,
      "code": "JSON_PARSE_ERROR",
      "message": "Строка не является валидным JSON."
    }
  ]
}
```

---

# `getAppState()`

Приоритет: P0  
Side effect: read-only

## Назначение

Получить стартовое состояние приложения при запуске UI.

UI использует метод, чтобы понять:

- есть ли последние проекты;
- есть ли demo project;
- какой проект был открыт последним;
- какие feature flags включены.

## Request

```json
{}
```

## Response `data`

```json
{
  "app_version": "1.5-draft",
  "api_version": "1.5-draft",
  "local_mode": true,
  "last_opened_project_id": 1,
  "recent_projects": [],
  "demo_available": true,
  "feature_flags": {
    "what_if": true,
    "analysis_coverage": true,
    "parameter_import": false,
    "progress_api": false
  }
}
```

## Notes

- Метод не должен создавать проект сам по себе.
- Demo project может быть создан lazy через `openDemoProject()`.

---

# `listProjects()`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "include_demo": true,
  "limit": 20
}
```

## Response `data`

```json
{
  "projects": [
    {
      "project_id": 1,
      "name": "Demo Economy",
      "last_opened_at": "2026-07-02T12:30:00Z",
      "events_count": 1250,
      "last_import_status": "completed_with_warnings",
      "is_demo": true
    }
  ]
}
```

## Empty state

Если проектов нет:

```json
{
  "empty_state": {
    "code": "NO_PROJECTS",
    "title": "Проектов пока нет",
    "message": "Создайте проект или откройте demo project.",
    "next_action": "open_demo"
  },
  "projects": []
}
```

---

# `createProject(payload)`

Приоритет: P0  
Side effect: write

## Request

```json
{
  "name": "My Balance Project",
  "default_build_id": "0.1-playtest",
  "settings": {
    "time_zone": "UTC"
  }
}
```

## Validation

| Field | Rule |
|---|---|
| `name` | required, non-empty string |
| `default_build_id` | optional string |
| `settings` | optional object |

## Writes

- `projects`
- `app_settings` / recent projects

## Response `data`

```json
{
  "project": {
    "project_id": 2,
    "name": "My Balance Project",
    "created_at": "2026-07-02T12:00:00Z",
    "default_build_id": "0.1-playtest",
    "is_demo": false
  },
  "next_action": "open_import"
}
```

---

# `openProject(payload)`

Приоритет: P0  
Side effect: write, потому что обновляет `last_opened_at` и recent projects

## Request

```json
{
  "project_id": 2
}
```

Альтернатива для будущей project-local DB:

```json
{
  "project_path": "H:/Projects/BalanceCraft/my_project/balancecraft.db"
}
```

Для MVP предпочтителен `project_id`, если используется single app DB.

## Response `data`

```json
{
  "project": {
    "project_id": 2,
    "name": "My Balance Project",
    "events_count": 0,
    "entities_count": 0,
    "observations_count": 0,
    "metric_runs_count": 0,
    "is_demo": false
  },
  "project_state": {
    "has_events": false,
    "has_profile": false,
    "has_bindings": false,
    "has_metric_runs": false,
    "has_parameters": false
  },
  "next_action": "open_import"
}
```

---

# `openDemoProject()`

Приоритет: P0  
Side effect: write, если demo project ещё не создан

## Назначение

Открыть demo project для первого запуска и портфолио-показа.

## Request

```json
{}
```

## Writes

Если demo ещё нет:

- `projects`
- `import_runs`
- `source_files`
- `entities`
- `observations`
- `events`
- `event_attribute_profile`
- optional demo `semantic_binding_sets`
- optional demo `metric_runs`

## Response `data`

```json
{
  "project": {
    "project_id": 1,
    "name": "BalanceCraft Demo Economy",
    "is_demo": true,
    "events_count": 1250,
    "entities_count": 42,
    "observations_count": 25,
    "metric_runs_count": 2
  },
  "demo_state": {
    "created_now": false,
    "has_demo_logs": true,
    "has_demo_bindings": true,
    "has_demo_metric_runs": true
  },
  "next_action": "open_dashboard"
}
```

## Notes

Demo project должен быть безопасен для повторного открытия.

---

# `getProjectSummary(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1
}
```

## Response `data`

```json
{
  "project": {
    "project_id": 1,
    "name": "BalanceCraft Demo Economy",
    "is_demo": true,
    "events_count": 1250,
    "event_types_count": 8,
    "entities_count": 42,
    "observations_count": 25,
    "metric_runs_count": 2,
    "scenarios_count": 1,
    "last_import_run_id": 7,
    "last_metric_run_id": 4
  },
  "available_actions": [
    "open_data_map",
    "open_binding_wizard",
    "open_dashboard",
    "open_what_if"
  ]
}
```

---

# `importEvents(payload)`

Приоритет: P0  
Side effect: import-write

## Назначение

Импортировать локальные JSONL-файлы в проект.

## Request

```json
{
  "project_id": 1,
  "source_paths": [
    "H:/BalanceCraft/logs/events_001.jsonl"
  ],
  "options": {
    "recursive": false,
    "file_pattern": "*.jsonl",
    "default_build_id": "0.1-playtest",
    "on_invalid_line": "skip",
    "create_auto_observation": true,
    "rebuild_profile_after_import": true
  }
}
```

## Validation

| Field | Rule |
|---|---|
| `project_id` | required |
| `source_paths` | required, non-empty array |
| `options.on_invalid_line` | `skip` for MVP; `fail_file` optional P1 |
| `attributes` in events | must be object |

## Writes

- `import_runs`
- `source_files`
- `entities`
- `observations`
- `events`
- `event_attribute_profile`, если `rebuild_profile_after_import = true`

## Response `data`

```json
{
  "import_report": {
    "import_run_id": 7,
    "project_id": 1,
    "status": "completed_with_warnings",
    "source_files_count": 2,
    "read_lines": 1000,
    "valid_events": 980,
    "invalid_events": 20,
    "imported_events": 980,
    "created_entities": 12,
    "created_observations": 8
  },
  "profile_rebuilt": true,
  "next_action": "open_data_map"
}
```

## Warnings

- `PARTIAL_IMPORT`
- `MISSING_OPTIONAL_FIELD`
- `AUTO_OBSERVATION_CREATED`
- `MIXED_ATTRIBUTE_TYPES`

## Transaction policy

Проектное решение Batch 05: транзакция на файл, а не на весь import run.

Правило:

```text
битый файл не должен откатывать уже успешно импортированные файлы import run,
но в рамках одного файла частичная запись должна быть контролируемой и отражённой в отчёте.
```

---

# `getImportRun(payload)`

Приоритет: P0  
Side effect: read-only

## Request

```json
{
  "project_id": 1,
  "import_run_id": 7,
  "include_files": true,
  "include_error_samples": true
}
```

## Response `data`

```json
{
  "import_report": {
    "import_run_id": 7,
    "project_id": 1,
    "status": "completed_with_warnings",
    "read_lines": 1000,
    "valid_events": 980,
    "invalid_events": 20,
    "imported_events": 980,
    "source_files": [
      {
        "source_file_id": 14,
        "file_name": "events_run_001.jsonl",
        "lines_count": 500,
        "valid_events": 490,
        "invalid_events": 10,
        "status": "completed_with_warnings",
        "errors_sample": []
      }
    ]
  }
}
```

## Notes

UI должен использовать этот метод для import details screen/modal.
