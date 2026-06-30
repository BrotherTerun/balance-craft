"""
Practical insight generation for BalanceCraft.

Модуль превращает рассчитанные временные ряды метрик в прикладные
выводы для геймдизайнера. Он намеренно вынесен отдельно от
progression_model.py: модель прогрессии готовит данные и графики, а этот
модуль отвечает только за интерпретацию результатов анализа.

Формат вывода:
{
    "level": "info" | "warning" | "danger" | "success",
    "category": "general" | "template",
    "title": "Краткий заголовок",
    "text": "Что обнаружено в данных",
    "recommendation": "Что проверить или изменить в балансе",
    "metric_keys": ["RF_RESOURCE_FLOW"],
    "evidence": "Среднее значение: ..."
}
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import math


EPSILON = 1e-9
MAX_INSIGHTS = 6


def _to_float(value, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default

    if math.isnan(result) or math.isinf(result):
        return default

    return result


def _series(values: Sequence[float]) -> List[float]:
    return [_to_float(value) for value in (values or [])]


def _mean(values: Sequence[float]) -> float:
    prepared = _series(values)
    return sum(prepared) / len(prepared) if prepared else 0.0


def _abs_mean(values: Sequence[float]) -> float:
    prepared = _series(values)
    return sum(abs(value) for value in prepared) / len(prepared) if prepared else 0.0


def _first_non_null(values: Sequence[float]) -> float:
    prepared = _series(values)
    return prepared[0] if prepared else 0.0


def _last_non_null(values: Sequence[float]) -> float:
    prepared = _series(values)
    return prepared[-1] if prepared else 0.0


def _is_zero_series(values: Sequence[float], eps: float = 1e-8) -> bool:
    prepared = _series(values)
    return bool(prepared) and all(abs(value) <= eps for value in prepared)


def _all_metrics_zero(values_by_metric: Dict[str, Sequence[float]], metric_order: Sequence[str]) -> bool:
    active = [values_by_metric.get(metric_key, []) for metric_key in metric_order]

    if not active:
        return True

    return all(_is_zero_series(values) for values in active if values is not None)


def _relative_change(values: Sequence[float]) -> float:
    prepared = _series(values)

    if len(prepared) < 2:
        return 0.0

    start = prepared[0]
    end = prepared[-1]
    scale = max(abs(start), _abs_mean(prepared), 1.0)

    return (end - start) / scale


def _trend_label(change: float) -> str:
    if change > 0.15:
        return "растёт"
    if change < -0.15:
        return "снижается"
    return "остаётся примерно на одном уровне"


def _format_number(value: float) -> str:
    value = _to_float(value)

    if abs(value) >= 1000:
        return f"{value:.1f}"

    if abs(value) >= 10:
        return f"{value:.2f}"

    return f"{value:.3f}"


def _metric_label(metric_key: str, metric_labels: Dict[str, str]) -> str:
    return metric_labels.get(metric_key, metric_key)


def _make_insight(
    level: str,
    category: str,
    title: str,
    text: str,
    recommendation: str,
    metric_keys: Optional[List[str]] = None,
    evidence: str = ""
) -> Dict[str, object]:
    return {
        "level": level,
        "category": category,
        "title": title,
        "text": text,
        "recommendation": recommendation,
        "metric_keys": metric_keys or [],
        "evidence": evidence
    }


def _add_general_insights(
    insights: List[Dict[str, object]],
    values_by_metric: Dict[str, Sequence[float]],
    metric_order: Sequence[str],
    metric_labels: Dict[str, str],
    stability: Dict[str, object],
    analysis_scope: str
) -> None:
    sessions_count = int(stability.get("sessions_count") or 0)
    stability_status = str(stability.get("status") or "unknown")
    lyapunov = stability.get("lyapunov")
    bifurcation_points = list(stability.get("bifurcation_points") or [])

    if sessions_count < 4:
        insights.append(_make_insight(
            "info",
            "general",
            "Недостаточно данных для уверенной оценки",
            "Количество точек временного ряда слишком мало для устойчивой интерпретации динамики.",
            "Импортируйте больше сессий или рассматривайте текущий результат как предварительный.",
            evidence=f"Точек анализа: {sessions_count}."
        ))
        return

    if _all_metrics_zero(values_by_metric, metric_order):
        insights.append(_make_insight(
            "warning",
            "general",
            "Метрики выбранного шаблона равны нулю",
            "Все отображаемые ряды выбранного шаблона имеют нулевые значения.",
            "Проверьте формулы шаблона и привязку переменных к полям событий в мастере семантики.",
            metric_keys=list(metric_order),
            evidence="Все значения выбранных метрик равны 0."
        ))
        return

    if stability_status in {"high_instability", "moderate_instability"}:
        level = "danger" if stability_status == "high_instability" else "warning"
        title = "Высокая нестабильность динамики" if level == "danger" else "Умеренная нестабильность динамики"

        insights.append(_make_insight(
            level,
            "general",
            title,
            "Близкие состояния системы в среднем расходятся при дальнейшем развитии.",
            "Проверьте сессии с резкими скачками метрик: вероятно, в них меняются награды, цены, потери или интенсивность действий.",
            evidence=f"Оценка показателя Ляпунова: {_format_number(lyapunov)}." if lyapunov is not None else "Оценка показателя Ляпунова недоступна."
        ))
    elif stability_status in {"stable", "neutral"}:
        insights.append(_make_insight(
            "success",
            "general",
            "Динамика системы не показывает критической нестабильности",
            "По текущим данным траектория метрик не демонстрирует выраженного расхождения близких состояний.",
            "Можно переходить к анализу отдельных метрик шаблона и проверять, соответствует ли их уровень дизайнерским ожиданиям.",
            evidence=f"Оценка показателя Ляпунова: {_format_number(lyapunov)}." if lyapunov is not None else "Оценка показателя Ляпунова недоступна."
        ))

    if bifurcation_points:
        visible_points = ", ".join(str(point) for point in bifurcation_points[:5])

        insights.append(_make_insight(
            "warning",
            "general",
            "Обнаружены резкие изменения траектории",
            "В ряде метрик есть точки, где скорость изменения системы резко меняется.",
            "Сопоставьте эти точки с событиями в логах: выдачей наград, покупками, апгрейдами, потерями или изменением активности игрока.",
            evidence=f"Индексы точек: {visible_points}."
        ))

    if analysis_scope == "all_players_average":
        insights.append(_make_insight(
            "info",
            "general",
            "Показана усреднённая траектория игроков",
            "Текущий график отражает среднее значение метрик по порядковому номеру сессии всех игроков.",
            "Используйте этот режим как обзор баланса, а отдельных игроков — для проверки выбросов и нетипичных сценариев.",
            evidence="Ось X соответствует 1-й, 2-й, 3-й и последующим сессиям игрока."
        ))


def _add_progression_decay_insights(
    insights: List[Dict[str, object]],
    values_by_metric: Dict[str, Sequence[float]],
    metric_labels: Dict[str, str]
) -> None:
    """
    Интерпретация шаблона из таблицы 1.2:
    EV = опыт / время, PGR = прирост силы / время, DR = потери / текущая сила.
    Legacy-ключи старого прототипа читаются только как fallback.
    """

    ev = _series(values_by_metric.get("EV") or values_by_metric.get("Y_EXP_VELOCITY", []))
    pgr = _series(values_by_metric.get("PGR", []))
    dr = _series(values_by_metric.get("DR") or values_by_metric.get("D_PROGRESSION_DECAY", []))

    if len(ev) >= 2 and _relative_change(ev) < -0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Скорость прогрессии снижается",
            "Игроки получают меньше прогресса за единицу времени к концу наблюдаемого периода.",
            "Проверьте поздние награды, требования к развитию и возможные участки, где прогресс становится слишком медленным.",
            ["EV"],
            f"Тренд метрики «{_metric_label('EV', metric_labels)}»: {_trend_label(_relative_change(ev))}."
        ))

    if len(pgr) >= 2 and _relative_change(pgr) < -0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Темп роста силы падает",
            "Прирост силы игрока за сессию становится ниже относительно начала наблюдаемого периода.",
            "Сопоставьте этот участок с ценами улучшений, доступностью предметов, навыков и требованиями к дальнейшему развитию.",
            ["PGR"],
            f"Тренд метрики «{_metric_label('PGR', metric_labels)}»: {_trend_label(_relative_change(pgr))}."
        ))

    if len(pgr) >= 4:
        second_half = pgr[len(pgr) // 2:]
        if _abs_mean(second_half) < max(_abs_mean(pgr) * 0.18, 0.01):
            insights.append(_make_insight(
                "info",
                "template",
                "Рост силы выходит на плато",
                "Во второй части наблюдаемого периода темп роста силы близок к нулю.",
                "Проверьте, является ли это ожидаемым замедлением прогрессии или признаком нехватки новых источников развития.",
                ["PGR"],
                f"Средний темп роста силы во второй половине: {_format_number(_mean(second_half))}."
            ))

    if len(dr) >= 2 and _relative_change(dr) > 0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Деградация прогрессии усиливается",
            "Доля потерь относительно текущей силы игрока растёт к концу наблюдаемого периода.",
            "Проверьте штрафы, износ, смерти или другие механики потерь: возможно, они начинают слишком сильно подавлять развитие.",
            ["DR"],
            f"Тренд метрики «{_metric_label('DR', metric_labels)}»: {_trend_label(_relative_change(dr))}."
        ))

    if len(dr) >= 3 and _mean(dr[-3:]) > 0.45:
        insights.append(_make_insight(
            "danger",
            "template",
            "Высокая доля потерь прогрессии",
            "В последних сессиях потери составляют значительную часть текущей силы игрока.",
            "Проверьте, не превращаются ли штрафы в барьер прогрессии, особенно после смертей, неудачных попыток или дорогих улучшений.",
            ["DR"],
            f"Среднее значение DR за последние сессии: {_format_number(_mean(dr[-3:]))}."
        ))

def _add_resource_flow_insights(
    insights: List[Dict[str, object]],
    values_by_metric: Dict[str, Sequence[float]],
    metric_labels: Dict[str, str]
) -> None:
    flow = _series(values_by_metric.get("RF_RESOURCE_FLOW", []))
    spend_share = _series(values_by_metric.get("SSR_SPEND_SHARE", []))
    inflation = _series(values_by_metric.get("RI_RESOURCE_INFLATION", []))

    if flow:
        mean_flow = _mean(flow)
        scale = max(_abs_mean(flow), 1.0)

        if mean_flow > 0.10 * scale:
            insights.append(_make_insight(
                "warning",
                "template",
                "Ресурс в среднем накапливается",
                "Приход ресурса устойчиво превышает расход, что может привести к инфляции или обесцениванию наград.",
                "Проверьте цены, частоту покупок и наличие достаточных способов вывода ресурса из экономики.",
                ["RF_RESOURCE_FLOW"],
                f"Средний чистый поток: {_format_number(mean_flow)}."
            ))
        elif mean_flow < -0.10 * scale:
            insights.append(_make_insight(
                "danger",
                "template",
                "Ресурс в среднем уходит в дефицит",
                "Расход ресурса превышает приход, из-за чего игрок может столкнуться с нехваткой ресурсов.",
                "Проверьте доступность источников ресурса и стоимость обязательных действий.",
                ["RF_RESOURCE_FLOW"],
                f"Средний чистый поток: {_format_number(mean_flow)}."
            ))

    if spend_share:
        mean_share = _mean(spend_share)

        if mean_share < 0.30:
            insights.append(_make_insight(
                "warning",
                "template",
                "Доля расхода ресурса низкая",
                "Игроки тратят небольшую часть получаемого ресурса.",
                "Проверьте, достаточно ли привлекательны покупки, улучшения и другие способы расходования ресурса.",
                ["SSR_SPEND_SHARE"],
                f"Средняя доля расхода: {_format_number(mean_share)}."
            ))
        elif mean_share > 0.90:
            insights.append(_make_insight(
                "warning",
                "template",
                "Расход почти полностью съедает доход",
                "Большая часть получаемого ресурса сразу расходуется, что может создавать ощущение давления экономики.",
                "Проверьте, не слишком ли высоки обязательные траты относительно наград.",
                ["SSR_SPEND_SHARE"],
                f"Средняя доля расхода: {_format_number(mean_share)}."
            ))

    if len(inflation) >= 2 and _relative_change(inflation) > 0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Темп накопления ресурса растёт",
            "Ресурсная инфляция усиливается к концу наблюдаемого периода.",
            "Проверьте поздние награды, множители дохода и механики, увеличивающие приток ресурса.",
            ["RI_RESOURCE_INFLATION"],
            f"Тренд метрики: {_trend_label(_relative_change(inflation))}."
        ))


def _add_resource_conversion_insights(
    insights: List[Dict[str, object]],
    values_by_metric: Dict[str, Sequence[float]],
    metric_labels: Dict[str, str]
) -> None:
    efficiency = _series(values_by_metric.get("PE_PROGRESSION_EFFICIENCY", []))
    roi = _series(values_by_metric.get("ROI_RESOURCE_TO_POWER", []))
    cost = _series(values_by_metric.get("POWER_COST", []))

    if efficiency and _mean(efficiency) <= 0:
        insights.append(_make_insight(
            "danger",
            "template",
            "Действия не дают положительного прогресса",
            "Средняя эффективность прогрессии не показывает прироста силы или целевого показателя.",
            "Проверьте события прироста силы и формулы конверсии ресурсов в прогресс.",
            ["PE_PROGRESSION_EFFICIENCY"],
            f"Средняя эффективность: {_format_number(_mean(efficiency))}."
        ))

    if len(roi) >= 2 and _relative_change(roi) < -0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "ROI ресурсов в силу снижается",
            "Одинаковые или растущие затраты дают всё меньший прирост силы.",
            "Проверьте кривую цен апгрейдов и награды за вложенные ресурсы на поздних этапах.",
            ["ROI_RESOURCE_TO_POWER"],
            f"Тренд ROI: {_trend_label(_relative_change(roi))}."
        ))

    if len(cost) >= 2 and _relative_change(cost) > 0.25:
        insights.append(_make_insight(
            "warning",
            "template",
            "Стоимость единицы силы растёт",
            "Получение дополнительной силы становится заметно дороже к концу ряда.",
            "Проверьте, соответствует ли рост стоимости ожидаемому темпу усложнения игры.",
            ["POWER_COST"],
            f"Тренд стоимости: {_trend_label(_relative_change(cost))}."
        ))


def _add_engagement_resource_insights(
    insights: List[Dict[str, object]],
    values_by_metric: Dict[str, Sequence[float]],
    metric_labels: Dict[str, str]
) -> None:
    apm = _series(values_by_metric.get("APM_ACTIONS_PER_MINUTE", []))
    time_efficiency = _series(values_by_metric.get("TIME_EFFICIENCY", []))
    grind = _series(values_by_metric.get("GRIND_FACTOR", []))

    if len(apm) >= 2 and _relative_change(apm) < -0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Интенсивность действий снижается",
            "Игрок совершает меньше действий в минуту к концу наблюдаемого периода.",
            "Проверьте, не становится ли игровой цикл менее насыщенным или слишком рутинным.",
            ["APM_ACTIONS_PER_MINUTE"],
            f"Тренд APM: {_trend_label(_relative_change(apm))}."
        ))

    if len(time_efficiency) >= 2 and _relative_change(time_efficiency) < -0.20:
        insights.append(_make_insight(
            "warning",
            "template",
            "Эффективность времени снижается",
            "Игрок получает меньше награды за единицу времени на поздних сессиях.",
            "Проверьте баланс наград за активность и длительность повторяемых действий.",
            ["TIME_EFFICIENCY"],
            f"Тренд эффективности времени: {_trend_label(_relative_change(time_efficiency))}."
        ))

    if len(grind) >= 2 and _relative_change(grind) > 0.25:
        insights.append(_make_insight(
            "warning",
            "template",
            "Гринд-фактор растёт",
            "Для получения награды требуется всё больше действий.",
            "Проверьте повторяемые циклы действий: игрок может ощущать рост рутины без достаточной компенсации наградой.",
            ["GRIND_FACTOR"],
            f"Тренд гринд-фактора: {_trend_label(_relative_change(grind))}."
        ))


def _add_template_insights(
    insights: List[Dict[str, object]],
    template_id: str,
    values_by_metric: Dict[str, Sequence[float]],
    metric_labels: Dict[str, str]
) -> None:
    if template_id == "progression_decay":
        _add_progression_decay_insights(insights, values_by_metric, metric_labels)
    elif template_id == "resource_flow":
        _add_resource_flow_insights(insights, values_by_metric, metric_labels)
    elif template_id == "resource_conversion":
        _add_resource_conversion_insights(insights, values_by_metric, metric_labels)
    elif template_id == "engagement_resource":
        _add_engagement_resource_insights(insights, values_by_metric, metric_labels)


def _deduplicate_insights(insights: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    result = []

    priority = {
        "danger": 0,
        "warning": 1,
        "info": 2,
        "success": 3
    }

    for insight in sorted(insights, key=lambda item: priority.get(str(item.get("level")), 9)):
        key = (insight.get("level"), insight.get("category"), insight.get("title"))

        if key in seen:
            continue

        seen.add(key)
        result.append(insight)

    return result[:MAX_INSIGHTS]


def generate_practical_insights(
    template_id: str,
    values_by_metric: Dict[str, Sequence[float]],
    metric_order: Sequence[str],
    metric_labels: Optional[Dict[str, str]] = None,
    stability: Optional[Dict[str, object]] = None,
    analysis_scope: str = "single_player"
) -> List[Dict[str, object]]:
    """
    Главная точка входа для progression_model.py.

    Формирует общие выводы по состоянию ряда и дополнительные выводы,
    зависящие от выбранного шаблона анализа.
    """

    metric_labels = metric_labels or {}
    stability = stability or {}
    insights: List[Dict[str, object]] = []

    _add_general_insights(
        insights=insights,
        values_by_metric=values_by_metric,
        metric_order=metric_order,
        metric_labels=metric_labels,
        stability=stability,
        analysis_scope=analysis_scope
    )

    # Если данных недостаточно или все ряды нулевые, шаблонные выводы
    # обычно будут шумом. Общий вывод уже объясняет проблему.
    if not any(item.get("title") in {
        "Недостаточно данных для уверенной оценки",
        "Метрики выбранного шаблона равны нулю"
    } for item in insights):
        _add_template_insights(
            insights=insights,
            template_id=template_id,
            values_by_metric=values_by_metric,
            metric_labels=metric_labels
        )

    if not insights:
        insights.append(_make_insight(
            "info",
            "general",
            "Критических отклонений не обнаружено",
            "По текущему набору правил система не выявила выраженных проблем в динамике выбранных метрик.",
            "Используйте график для ручной проверки ожидаемой формы прогрессии и переходите к what-if анализу для сценарной оценки изменений."
        ))

    return _deduplicate_insights(insights)
