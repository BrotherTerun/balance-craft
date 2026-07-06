# 15. План документации репозитория

## Назначение

Документация должна помогать быстро понять проект, запустить его, оценить архитектуру и продолжить разработку.

Она не должна быть одним файлом на 100 страниц. Каждый документ отвечает за один слой проекта.

## Актуальная структура

Внутренняя документация BalanceCraft хранится в отдельной директории:

```text
OBS_BalanceCraft_documentation/
├── README.md
├── 00_INDEX.md
├── 01_pre_design_docs/
│   ├── adr/
│   │   ├── ADR-000-template.md
│   │   ├── ADR-001-sqlite-runtime.md
│   │   ├── ADR-002-local-mode-first.md
│   │   ├── ADR-003-entity-observation-model.md
│   │   ├── ADR-004-late-semantic-binding.md
│   │   ├── ADR-005-what-if-levels.md
│   │   └── ADR-006-self-hosted-out-of-mvp.md
│   ├── 01_problem_audience.md
│   ├── ...
│   ├── 15_documentation_plan.md
│   └── 99_external_references.md
└── 03_design_docs/
    ├── contracts/
    │   ├── 00_contracts_index.md
    │   └── 01–05 detailed API contracts
    ├── diagrams/
    │   ├── 00_diagrams_index.md
    │   └── architecture, data, sequence, UI and migration diagrams
    ├── 16_feature_list.md
    ├── 17_implementation_checklist.md
    ├── 18_architecture_overview.md
    ├── 19_data_model_concept.md
    ├── 20_sqlite_schema_design.md
    ├── 21_data_flows.md
    ├── 22_backend_frontend_contracts.md
    ├── 23_ui_flow_and_screen_map.md
    ├── 24_demo_project_spec.md
    ├── 25_test_plan.md
    └── 26_definition_of_done.md
```

Разделение на слои сделано для удобства работы в Obsidian и Git:

```text
01_pre_design_docs
→ почему продукт нужен, что он должен делать и какие ограничения приняты

03_design_docs
→ как именно BalanceCraft 1.5 спроектирован и в каком порядке реализуется
```

ADR хранятся рядом с предпроектным слоем, потому что фиксируют фундаментальные решения, на которых строится проектирование.

## `../README.md`

Задача: кратко объяснить назначение внутреннего документационного пакета и привести к `../00_INDEX.md`.

Корневой публичный README самого проекта остаётся отдельным артефактом репозитория и перед портфолио-публикацией должен продавать смысл BalanceCraft за 1–2 минуты.

## `../00_INDEX.md`

Главная точка входа во внутреннюю документацию.

Задача:

- показать фактическую структуру пакета;
- дать порядок чтения;
- зафиксировать приоритет источников;
- привести к индексам contracts, diagrams и ADR.

## `01_pre_design_docs/`

### `01_problem_audience.md`

Проблема, гипотеза, ЦА, JTBD.

### `02_product_frame.md`

Продуктовая рамка: что BalanceCraft делает, что не делает, компоненты, режимы.

### `03_references_and_analogs.md`

Аналоги и референсы: Steamworks, Unity Analytics, GameAnalytics, Machinations.

### `04_analysis_templates.md`

Шаблоны анализа и их русские названия.

### `05_what_if_levels.md`

Уровни сценарного анализа и статусы уверенности.

### `06_user_flow_and_ux.md`

Пользовательские сценарии, экраны, empty states, ошибки.

### `07_privacy_and_data_principles.md`

Local Mode, Self-hosted, допустимые данные, SDK/Collector rules.

### `08_requirements.md`

Функциональные и нефункциональные требования.

### `09_mvp_scope_timeline.md`

MVP, P0/P1/P2/P3, оценка 48 часов, DoD.

### `10_prototype_audit.md`

Что оставить, переписать, удалить в текущем коде.

### `11_glossary.md`

Термины: entity, observation, event, parameter, metric, scenario.

### `12_input_data_formats.md`

JSONL, параметры, ошибки импорта, отчёт импорта.

### `13_design_requirements.md`

Требования к БД, модулям, потокам данных, индексам и проектным артефактам.

### `14_risks_open_questions.md`

Риски, допущения, решённые и отложенные вопросы.

### `15_documentation_plan.md`

Этот документ: правила и фактическая архитектура документации.

### `99_external_references.md`

Ссылки на внешние источники и официальные документации.

### `adr/`

Короткие архитектурные решения в формате:

```text
Контекст
Решение
Альтернативы
Последствия
Статус
```

## `03_design_docs/`

### `../03_design_docs/16_feature_list.md`

Рабочий scope и приоритеты функций BalanceCraft 1.5.

### `../03_design_docs/17_implementation_checklist.md`

Фазы разработки, ручные проверки и выход каждой фазы.

### `../03_design_docs/18_architecture_overview.md`

Архитектура Desktop, границы компонентов и направление зависимостей.

### `../03_design_docs/19_data_model_concept.md`

Концептуальная модель данных до SQLite-деталей.

### `../03_design_docs/20_sqlite_schema_design.md`

Физическая SQLite-модель, таблицы, ключи, индексы и миграционная позиция.

### `../03_design_docs/21_data_flows.md`

Основные потоки данных и sequence-level логика.

### `../03_design_docs/22_backend_frontend_contracts.md`

Главная точка входа в контракты Python backend ↔ JS frontend.

### `../03_design_docs/23_ui_flow_and_screen_map.md`

Карта экранов, состояния и пользовательские переходы.

### `../03_design_docs/24_demo_project_spec.md`

Спецификация Demo Forge и демонстрируемых проблем баланса.

### `../03_design_docs/25_test_plan.md`

Smoke tests, acceptance checks и критичные regression/edge cases.

### `../03_design_docs/26_definition_of_done.md`

Критерии готовности функций, фаз и версии 1.5.

### `contracts/`

Детальные backend/frontend API-контракты. Точка входа: `../03_design_docs/contracts/00_contracts_index.md`.

### `diagrams/`

Mermaid-диаграммы архитектуры, данных, потоков, UI и миграции. Точка входа: `../03_design_docs/diagrams/00_diagrams_index.md`.

## Документация после реализации

После MVP при необходимости добавляются пользовательские и эксплуатационные документы:

```text
developer setup
release checklist
quick start
demo scenario
troubleshooting
SDK Lite
Self-hosted Collector
value normalization
```

Их физическое размещение определяется при появлении соответствующего слоя. До этого не создаём пустые папки и не раздуваем пакет заранее.

## Правила ссылок

1. Ссылки должны соответствовать фактической структуре репозитория.
2. Между `01_pre_design_docs/` и `03_design_docs/` используются корректные относительные пути.
3. Внутри `contracts/` и `diagrams/` ссылки строятся относительно текущего файла.
4. `../00_INDEX.md` использует пути относительно корня `OBS_BalanceCraft_documentation/`.
5. Строка `# FILE:` при наличии показывает реальный путь внутри `OBS_BalanceCraft_documentation/`.
6. После перемещения файлов запускается проверка ссылок, а не ручная надежда на удачу.

## Правила стиля

- Писать прямо и прикладно.
- Не использовать академическую воду.
- Не описывать историю разработки, если она не нужна для решения.
- Не писать “идеально в будущем”, если это не входит в scope.
- Любое требование должно иметь проверяемый результат.
- Любой риск должен иметь контрмеру.

## Минимальный набор для GitHub-портфолио

Перед публикацией репозитория желательно иметь:

- корневой публичный README;
- скриншоты интерфейса;
- demo logs;
- demo project;
- quick start;
- внутренний docs index;
- requirements;
- architecture overview;
- privacy note;
- roadmap.

SDK Lite, Self-hosted Collector и value normalization могут иметь подробные требования в `08_requirements.md`, но отдельная пользовательская документация по ним нужна только после перехода к P2/P3.
