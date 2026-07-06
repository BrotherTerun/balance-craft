# FILE: `00_INDEX.md`
# BalanceCraft Docs Pack v0.1

Дата: 2026-07-02  
Статус: рабочий пакет для разработки и ревью

Этот пакет — внутренняя проектная документация BalanceCraft. Задача пакета — зафиксировать продуктовую рамку, требования, ограничения, данные и проектные решения так, чтобы по ним можно было продолжать разработку без повторного обсуждения базовых вещей.

## Структура пакета

```text
OBS_BalanceCraft_documentation/
├── README.md
├── 00_INDEX.md
├── 01_pre_design_docs/
│   ├── adr/
│   ├── 01_problem_audience.md
│   ├── ...
│   ├── 15_documentation_plan.md
│   └── 99_external_references.md
└── 03_design_docs/
    ├── contracts/
    ├── diagrams/
    ├── 16_feature_list.md
    ├── ...
    └── 26_definition_of_done.md
```

## Порядок чтения

### Предпроектный слой

1. `01_pre_design_docs/01_problem_audience.md` — проблема, гипотеза, целевая аудитория.
2. `01_pre_design_docs/02_product_frame.md` — продуктовая рамка BalanceCraft.
3. `01_pre_design_docs/03_references_and_analogs.md` — аналоги, референсы, сравнительные таблицы.
4. `01_pre_design_docs/04_analysis_templates.md` — универсальные шаблоны анализа.
5. `01_pre_design_docs/05_what_if_levels.md` — уровни What-if и границы сценарного анализа.
6. `01_pre_design_docs/06_user_flow_and_ux.md` — базовый пользовательский сценарий и UX-логика.
7. `01_pre_design_docs/07_privacy_and_data_principles.md` — принципы работы с телеметрией и данными.
8. `01_pre_design_docs/08_requirements.md` — функциональные и нефункциональные требования.
9. `01_pre_design_docs/09_mvp_scope_timeline.md` — границы MVP, приоритеты, оценка 48 часов.
10. `01_pre_design_docs/10_prototype_audit.md` — поверхностный аудит текущего кода.
11. `01_pre_design_docs/11_glossary.md` — словарь сущностей и терминов.
12. `01_pre_design_docs/12_input_data_formats.md` — форматы событий, параметров, ошибок импорта.
13. `01_pre_design_docs/13_design_requirements.md` — требования к проектированию БД, модулей, схем и потоков данных.
14. `01_pre_design_docs/14_risks_open_questions.md` — риски, допущения, открытые вопросы.
15. `01_pre_design_docs/15_documentation_plan.md` — структура документации репозитория.

### Проектировочный слой

16. `03_design_docs/16_feature_list.md` — рабочий feature list BalanceCraft 1.5.
17. `03_design_docs/17_implementation_checklist.md` — порядок реализации и чеклист фаз.
18. `03_design_docs/18_architecture_overview.md` — архитектурный обзор Desktop 1.5.
19. `03_design_docs/19_data_model_concept.md` — концептуальная модель данных.
20. `03_design_docs/20_sqlite_schema_design.md` — физический дизайн SQLite-схемы.
21. `03_design_docs/21_data_flows.md` — основные потоки данных и sequence-level логика.
22. `03_design_docs/22_backend_frontend_contracts.md` — контракты Python backend ↔ JS frontend.
23. `03_design_docs/23_ui_flow_and_screen_map.md` — карта экранов и UX-переходов.
24. `03_design_docs/24_demo_project_spec.md` — спецификация demo project.
25. `03_design_docs/25_test_plan.md` — test plan и QA checklist.
26. `03_design_docs/26_definition_of_done.md` — Definition of Done для функций, фаз и версии 1.5.

### Индексы, диаграммы, контракты и ADR

27. `03_design_docs/contracts/00_contracts_index.md` — индекс детальных backend/frontend контрактов.
28. `03_design_docs/diagrams/00_diagrams_index.md` — индекс Mermaid-диаграмм.
29. `01_pre_design_docs/99_external_references.md` — внешние источники и референсы.
30. `01_pre_design_docs/adr/` — Architecture Decision Records.

## Приоритет источников

1. Документация из `OBS_BalanceCraft_documentation/`.
2. Актуальный код репозитория.
3. Старые исторические материалы проекта.
4. Контекст обсуждений и рабочие заметки.
5. Внешние ресурсы и документация инструментов — когда предыдущие источники не отвечают на вопрос.

При конфликте документов внутри пакета более конкретный и более поздний проектировочный документ имеет приоритет над ранним общим описанием, если это не противоречит принятому ADR.

## Базовая позиция проекта

BalanceCraft — локальный инструмент анализа числового баланса игровых систем на основе событийной телеметрии. Он ориентирован на инди-разработчиков и небольшие команды, которым нужно быстро понять, что происходит с ресурсами, прогрессией, стоимостью действий, доступностью операций и устойчивостью игровых систем без развёртывания тяжёлой аналитической инфраструктуры.

```text
BalanceCraft анализирует не игроков, предметы, навыки или жанры.
BalanceCraft анализирует числовые события игровой системы,
позволяя разработчику самому назначить им смысл,
рассчитать метрики и увидеть проблемы баланса.
```

## Целевой результат BalanceCraft 1.5

```text
скачал приложение
→ запустил
→ открыл демо-проект или импортировал JSONL
→ увидел карту данных
→ настроил семантику
→ получил графики и выводы
→ проверил простой сценарий What-if
```
