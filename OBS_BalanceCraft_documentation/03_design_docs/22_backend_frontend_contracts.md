# FILE: `03_design_docs/22_backend_frontend_contracts.md`
# 22. Backend ↔ Frontend contracts

Дата: 2026-07-02  
Статус: рабочий черновик для проектирования и ревью

## Назначение

Документ фиксирует контракт между frontend UI и backend BalanceCraft Desktop 1.5.

Контракт нужен, чтобы во время разработки не угадывать:

- какие методы вызывает JavaScript UI;
- какие payloads принимает backend;
- что backend обязан вернуть;
- где появляются `warnings`;
- как UI отличает пустые состояния от ошибок;
- какие операции меняют SQLite;
- какие методы входят в MVP, а какие остаются P1/P2.

Этот документ не описывает внутреннюю реализацию SQL и не заменяет `20_sqlite_schema_design.md`. Он описывает границу между UI и backend.

## Архитектурная позиция

BalanceCraft Desktop 1.5 использует локальный frontend на HTML/CSS/JS и backend на Python через PySide/QWebChannel.

Базовая цепочка:

```text
Frontend UI
→ QWebChannel bridge
→ Backend API Facade
→ Service layer
→ DB Layer
→ SQLite
```

Frontend:

- не обращается к SQLite напрямую;
- не знает SQL;
- не знает внутренние Python exceptions;
- не строит бизнес-логику расчёта метрик;
- получает структурированные DTO.

Backend:

- валидирует input;
- вызывает сервисы;
- управляет транзакциями через DB layer;
- возвращает stable JSON-like envelope;
- не возвращает raw traceback как пользовательскую ошибку.

## Почему детальные контракты вынесены в `contracts/`

API-контракты быстро становятся крупными. Чтобы `22_backend_frontend_contracts.md` не превратился в глиняную табличку на 80 экранов, подробные схемы методов вынесены в отдельные файлы:

```text
contracts/00_contracts_index.md
contracts/01_common_envelope.md
contracts/02_project_and_import_api.md
contracts/03_profile_binding_metrics_api.md
contracts/04_dashboard_insights_api.md
contracts/05_what_if_api.md
```

Этот файл остаётся главной точкой входа и фиксирует общие правила.

## API object

Рабочее имя объекта QWebChannel:

```text
balanceCraftApi
```

В JS допускается wrapper:

```js
const api = window.balanceCraftApi;
```

или Promise-wrapper поверх callback-style QWebChannel.

Правило для проектирования:

```text
UI-код работает так, будто каждый backend method возвращает Promise<Envelope>.
```

Даже если технически PySide/QWebChannel использует callback, frontend-слой должен оборачивать вызовы в единый async-style интерфейс.

## Envelope

Все методы возвращают envelope:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": []
}
```

Допускается optional `meta` для технических полей:

```json
{
  "success": true,
  "data": {},
  "warnings": [],
  "errors": [],
  "meta": {
    "api_version": "1.5-draft",
    "request_id": "req_..."
  }
}
```

UI не должен зависеть от наличия `meta` в P0.

Подробно: `contracts/01_common_envelope.md`.

## Приоритеты методов

| Приоритет | Значение |
|---|---|
| P0 | обязателен для BalanceCraft Desktop 1.5 vertical slice |
| P1 | нужен для удобства и портфолио-полировки, но может быть упрощён |
| P2 | будущие расширения |

## P0 method map

### Project lifecycle

| Method | Назначение |
|---|---|
| `getAppState()` | восстановить состояние UI при запуске |
| `listProjects()` | получить последние/доступные проекты |
| `createProject(payload)` | создать проект |
| `openProject(payload)` | открыть проект |
| `openDemoProject()` | открыть или создать demo project |
| `getProjectSummary(payload)` | получить сводку проекта |

### Import and data map

| Method | Назначение |
|---|---|
| `importEvents(payload)` | импортировать JSONL |
| `getImportRun(payload)` | получить отчёт импорта |
| `getDataProfile(payload)` | получить карту событий и attributes |
| `getAnalysisCoverage(payload)` | понять, какие проблемы можно проверить |

### Templates and bindings

| Method | Назначение |
|---|---|
| `listMetricTemplates(payload)` | получить доступные шаблоны метрик |
| `getMetricTemplate(payload)` | получить один шаблон |
| `validateBindingSet(payload)` | проверить semantic binding без сохранения |
| `saveBindingSet(payload)` | сохранить semantic binding set |
| `listBindingSets(payload)` | список сохранённых binding sets |
| `getBindingSet(payload)` | открыть binding set |

### Metric calculation

| Method | Назначение |
|---|---|
| `runMetricCalculation(payload)` | рассчитать metric run |
| `listMetricRuns(payload)` | список расчётов проекта |
| `getMetricRun(payload)` | статус и metadata расчёта |

### Dashboard and insights

| Method | Назначение |
|---|---|
| `getDashboardData(payload)` | данные для графиков, таблиц и карточек |
| `getInsights(payload)` | practical insights для metric run или scenario |

### What-if

| Method | Назначение |
|---|---|
| `getWhatIfControls(payload)` | доступные параметры и ограничения сценариев |
| `runScenario(payload)` | создать/обновить сценарий и рассчитать результат |
| `getScenarioResult(payload)` | получить scenario results для сравнения |

## P1/P2 method candidates

| Method | Приоритет | Комментарий |
|---|---:|---|
| `deleteProject(payload)` | P1 | можно отложить, если есть ручное удаление файла/записи |
| `renameProject(payload)` | P1 | удобство, не блокирует vertical slice |
| `updateProjectSettings(payload)` | P1 | полезно для UI preferences |
| `cancelOperation(payload)` | P1 | нужно, если импорт/расчёт долгие |
| `getOperationStatus(payload)` | P1 | progress UI для долгих задач |
| `importParameters(payload)` | P1 | зависит от решения по parameter import |
| `validateEventFile(payload)` | P1 | dry run импорта |
| `exportProjectReport(payload)` | P2 | портфолио/шаринг отчётов |
| `exportDemoLogs(payload)` | P2 | вспомогательно |

## Правило явного `project_id`

P0-методы, работающие с проектом, принимают `project_id` явно.

Да, UI может хранить `currentProject`. Но backend contract не должен зависеть только от скрытого active project, иначе при переключении проектов и async-вызовах легко поймать призрака старой сессии.

Правило:

```text
currentProject в UI — convenience state.
project_id в API payload — источник истины для backend operation.
```

Исключения:

- `getAppState()`;
- `listProjects()`;
- `createProject()`;
- `openDemoProject()`.

## Правила DTO

### 1. DTO не равны таблицам SQLite

Backend может использовать таблицы `events`, `metric_values`, `semantic_bindings`, но UI получает DTO, собранные под экран.

Например, `getDashboardData()` не обязан возвращать строки `metric_values` как есть. Он должен вернуть готовые `labels`, `datasets`, `warnings`, `available_actions`, `empty_state`.

### 2. UI labels отделены от technical keys

Каждый объект, который показывается пользователю, должен иметь:

```text
technical key/id → для кода
label/title → для UI
```

Пример:

```json
{
  "metric_key": "net_flow",
  "label": "Чистый поток"
}
```

### 3. Empty state — это не ошибка

Если данных нет, но операция выполнена корректно, возвращается:

```json
{
  "success": true,
  "data": {
    "empty_state": {
      "code": "NO_METRIC_RUNS",
      "title": "Метрики ещё не рассчитаны",
      "message": "Настройте semantic binding и запустите расчёт.",
      "next_action": "open_binding_wizard"
    }
  },
  "warnings": [],
  "errors": []
}
```

`success: false` используется только если операция не может быть завершена.

## Правила ошибок

Backend возвращает ошибки в человекочитаемом виде.

Плохо:

```text
KeyError: attributes.amount
```

Хорошо:

```json
{
  "code": "MISSING_ATTRIBUTE",
  "message": "В части событий не найдено поле attributes.amount.",
  "details": {
    "attribute_path": "attributes.amount",
    "affected_event_type": "resource_spent"
  },
  "hint": "Проверьте карту данных или выберите другое поле в Binding Wizard.",
  "recoverable": true
}
```

## Правила warnings

Warnings не должны блокировать весь поток, если результат всё ещё полезен.

Примеры:

- часть строк JSONL пропущена;
- у части событий нет `observation_id`;
- метрика рассчитана только по части событий;
- `safe_div` вернул `N/A`;
- What-if имеет статус `impact_estimate`, а не `exact_recalc`.

## Side effects

Каждый метод должен быть явно отнесён к одному из типов:

| Тип | Значение |
|---|---|
| read-only | не меняет SQLite |
| write | создаёт/обновляет записи |
| compute-write | выполняет расчёт и сохраняет результат |
| import-write | читает внешние файлы и пишет импорт |

Это важно для тестов и UI: пользователь должен понимать, где создаётся новая история расчётов, а где просто меняется отображение.

## Согласованность с data flows

Контракты следуют потокам из `21_data_flows.md`:

```text
create/open project
→ import JSONL
→ data profile
→ analysis coverage
→ semantic binding
→ metric calculation
→ dashboard
→ insights
→ What-if
```

Контракты не должны добавлять скрытый поток “backend сам понял смысл данных”. Семантика задаётся через Binding Wizard.

## Совместимость с будущими компонентами

SDK Lite и Self-hosted Collector не участвуют в runtime API Desktop 1.5.

Но формат `importEvents()` должен быть совместим с JSONL, который в будущем может производить SDK Lite или экспортировать Self-hosted Collector.

Правило:

```text
Desktop API импортирует локальные файлы.
SDK/Collector могут быть источниками этих файлов в будущем,
но не являются dependency Desktop 1.5.
```

## Review notes

1. Возможно, `getInsights()` можно не делать отдельным методом в P0, если `getDashboardData()` всегда возвращает insights. Но отдельный метод удобнее для lazy loading и повторного анализа.
2. Для долгих операций лучше иметь `operation_id` и progress API. Но если MVP работает с небольшими demo/JSONL, можно начать с синхронного ответа и добавить progress как P1.
3. `project_id` в каждом методе выглядит многословно, но это безопаснее скрытого global active project.
4. Нужно решить, насколько строго UI должен валидировать payload до backend. Предлагаемое правило: UI делает лёгкую валидацию формы, backend делает полную валидацию контракта.
5. Методы пока описаны как QWebChannel API, но структура envelope не мешает в будущем вынести тот же контракт в REST/CLI.
