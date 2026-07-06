# 99. Внешние источники и референсы

## Назначение

Этот файл фиксирует внешние материалы, которые использовались как референсы при формировании продуктовой рамки, анализа аналогов и структуры документации.

Внешние источники не заменяют внутренние решения BalanceCraft. Они используются как ориентиры последнего приоритета, когда внутренние источники не отвечают на вопрос.

## Product requirements / PRD

### Atlassian — Product requirements document

Используется как ориентир для структуры требований: цель продукта, пользовательские нужды, функции, критерии успеха и единый источник правды для команды.

URL:

```text
https://www.atlassian.com/agile/product-management/requirements
```

## Architecture Decision Records

### Microsoft Azure Architecture Center — Architecture decision records

Используется как ориентир для ADR: контекст, решение, альтернативы, последствия.

URL:

```text
https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
```

## Steamworks

### Steamworks UTM Analytics

Референс по простым отчётам, связи источника трафика с действиями пользователя и понятным breakdowns.

URL:

```text
https://partner.steamgames.com/doc/marketing/utm_analytics
```

### Steamworks Wishlist Reporting

Референс по платформенным отчётам и понятным сводкам.

URL:

```text
https://partner.steamgames.com/doc/marketing/wishlist
```

## Unity Analytics

### Unity Analytics Events

Референс по событийному подходу и custom events.

URL:

```text
https://docs.unity.com/ugs/en-us/manual/analytics/manual/events
```

### Unity Analytics Dashboards

Референс по dashboard-подходу и метрикам.

URL:

```text
https://docs.unity.com/ugs/en-us/manual/analytics/manual/dashboards
```

### Unity Analytics Data Explorer

Референс по пользовательским отчётам, custom events, метрикам и изменению активности/событий во времени. Используется как ориентир для простых рядов, группировок и dashboard-подхода без ручного SQL.

URL:

```text
https://docs.unity.com/en-us/analytics/data-explorer/data-explorer
```

## GameAnalytics

### GameAnalytics Dashboards

Референс по игровым dashboards, custom dashboards и быстрым аналитическим срезам.

URL:

```text
https://docs.gameanalytics.com/products-and-features/analytics-iq/dashboards/overview/
```

### GameAnalytics Design Events

Референс по событиям, связанным с игровым дизайном.

URL:

```text
https://docs.gameanalytics.com/integrations/sdk/guides/design-events/
```

### GameAnalytics Resource Events

Референс по tracking источников и sinks виртуальной экономики: `source`, `sink`, currency, amount, item type, item id. Используется для обоснования шаблона “Баланс потоков”.

URL:

```text
https://docs.gameanalytics.com/events-metrics-and-filtering/event-types/resource-events/
```

### GameAnalytics Progression Events

Референс по отслеживанию structured progression: start, complete, fail, уровни, миссии, квесты, numeric value. Используется для обоснования шаблонов “Динамика запаса”, “Интенсивность операций” и “Ритм наград”.

URL:

```text
https://docs.gameanalytics.com/events-metrics-and-filtering/event-types/progression-events/
```

## Machinations

### Machinations product site

Референс по моделированию экономики, сценариям, digital twins и симуляциям.

URL:

```text
https://machinations.io/
```

### Machinations Monte Carlo simulation docs

Референс по вероятностной симуляции и диапазонам результатов.

URL:

```text
https://machinations.io/docs/monte-carlo-simulations/
```

## Как использовать эти источники

- Steamworks: ориентир для простых отчётов и понятного “source → result”.
- Unity Analytics: ориентир для event/dashboard UX.
- GameAnalytics: ориентир для design events и custom dashboards.
- Machinations: ориентир для сценарного мышления, но не цель MVP.
- PRD/ADR материалы: ориентир для структуры документации и фиксации решений.
