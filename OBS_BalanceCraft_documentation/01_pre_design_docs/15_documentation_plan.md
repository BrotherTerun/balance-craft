# 15. План документации репозитория

## Назначение

Документация должна помогать быстро понять проект, запустить его, оценить архитектуру и продолжить разработку.

Она не должна быть одним файлом на 100 страниц. Каждый документ отвечает за один слой проекта.

## Корневая структура

```text
README.md
docs/
  00_INDEX.md
  01_problem_audience.md
  ...
  15_documentation_plan.md
  99_external_references.md
  adr/
examples/
  demo_project/
  demo_logs/
  demo_parameters/
src/ или app/
```

## README.md

Задача: продать смысл проекта за 1–2 минуты.

Содержание:

- что такое BalanceCraft;
- для кого;
- какую проблему решает;
- скриншоты;
- быстрый старт;
- demo scenario;
- текущий статус;
- roadmap;
- ссылка на docs.

## `docs/00_INDEX.md`

Задача: навигация по документации и порядок чтения.

## `docs/01_problem_audience.md`

Проблема, гипотеза, ЦА, JTBD.

## `docs/02_product_frame.md`

Продуктовая рамка: что BalanceCraft делает, что не делает, компоненты, режимы.

## `docs/03_references_and_analogs.md`

Аналоги и референсы: Steamworks, Unity Analytics, GameAnalytics, Machinations.

## `docs/04_analysis_templates.md`

Шаблоны анализа и их русские названия.

## `docs/05_what_if_levels.md`

Уровни сценарного анализа и статусы уверенности.

## `docs/06_user_flow_and_ux.md`

Пользовательские сценарии, экраны, empty states, ошибки.

## `docs/07_privacy_and_data_principles.md`

Local Mode, Self-hosted, допустимые данные, SDK/Collector rules.

## `docs/08_requirements.md`

Функциональные и нефункциональные требования.

## `docs/09_mvp_scope_timeline.md`

MVP, P0/P1/P2/P3, оценка 48 часов, DoD.

## `docs/10_prototype_audit.md`

Что оставить, переписать, удалить в текущем коде.

## `docs/11_glossary.md`

Термины: entity, observation, event, parameter, metric, scenario.

## `docs/12_input_data_formats.md`

JSONL, параметры, ошибки импорта, отчёт импорта.

## `docs/13_design_requirements.md`

Предварительная схема БД, модули, потоки данных, индексы.

## `docs/14_risks_open_questions.md`

Риски, допущения, открытые вопросы.

## `docs/99_external_references.md`

Ссылки на внешние источники и официальные документации.

## `docs/adr/`

Короткие архитектурные решения.

Формат каждого ADR:

```text
Контекст
Решение
Альтернативы
Последствия
Статус
```

## Документация после реализации

После MVP нужно добавить:

```text
docs/architecture.md
docs/sqlite_schema.md
docs/developer_setup.md
docs/release_checklist.md
docs/demo_scenario.md
docs/troubleshooting.md
docs/sdk_lite.md
docs/self_hosted_collector.md
docs/value_normalization.md
```

## Правила стиля

- Писать прямо и прикладно.
- Не использовать академическую воду.
- Не описывать историю разработки, если она не нужна для решения.
- Не писать “идеально в будущем”, если это не входит в scope.
- Любое требование должно иметь проверяемый результат.
- Любой риск должен иметь контрмеру.

## Минимальный набор для GitHub-портфолио

Перед публикацией репозитория желательно иметь:

- корневой README;
- скриншоты интерфейса;
- demo logs;
- demo project;
- quick start;
- docs index;
- requirements;
- architecture overview;
- privacy note;
- roadmap.

SDK Lite, Self-hosted Collector и value normalization могут иметь подробные требования в `08_requirements.md`, но отдельная пользовательская документация по ним нужна только после перехода к P2/P3.
