"""
Stability and Lyapunov analysis helpers for BalanceCraft.

Модуль вынесен отдельно от progression_model.py, чтобы не раздувать
основной скрипт визуализации. Здесь считаются:
- дискретная конечновременная оценка показателя Ляпунова;
- точки резких изменений состояния системы;
- текстовая классификация устойчивости.

Оценка основана на классической идее показателя Ляпунова:
    lambda = (1 / t) * ln(d(t) / d(0))

Для прототипа состояние системы X_i задаётся вектором метрик выбранного
шаблона на i-й сессии. Для каждого состояния ищется ближайшее другое
состояние, после чего оценивается, насколько расстояние между этими
близкими состояниями меняется на следующем шаге.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence
import math

import numpy as np


EPSILON = 1e-9
MIN_SESSIONS_FOR_STABILITY = 4


def _to_float(value, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default

    if math.isnan(result) or math.isinf(result):
        return default

    return result


def _sanitize_series(values: Sequence[float], target_length: int) -> List[float]:
    prepared = [_to_float(value) for value in values or []]

    if len(prepared) < target_length:
        prepared.extend([0.0] * (target_length - len(prepared)))

    return prepared[:target_length]


def _robust_normalize_column(values: np.ndarray) -> np.ndarray:
    """
    Нормализует один ряд метрик.

    Без нормализации крупные абсолютные значения вроде K_POWER_SCORE
    полностью подавляют долевые показатели вроде SSR_SPEND_SHARE.
    Используем z-нормализацию; если ряд почти постоянный, возвращаем нули.
    """

    if values.size == 0:
        return values

    mean = float(np.mean(values))
    std = float(np.std(values))

    if std < EPSILON:
        return np.zeros_like(values, dtype=float)

    return (values - mean) / std


def normalize_state_matrix(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix

    normalized_columns = [
        _robust_normalize_column(matrix[:, column_index])
        for column_index in range(matrix.shape[1])
    ]

    return np.column_stack(normalized_columns)


def build_state_vectors(
    values_by_metric: Dict[str, Sequence[float]],
    metric_order: Sequence[str]
) -> np.ndarray:
    """
    Формирует матрицу состояний X_i.

    Строка — состояние системы на i-й сессии.
    Столбец — одна метрика выбранного аналитического шаблона.
    """

    active_metrics = [
        metric_key
        for metric_key in metric_order
        if metric_key in values_by_metric
    ]

    if not active_metrics:
        return np.empty((0, 0), dtype=float)

    length = max(
        len(values_by_metric.get(metric_key) or [])
        for metric_key in active_metrics
    )

    if length == 0:
        return np.empty((0, len(active_metrics)), dtype=float)

    columns = [
        _sanitize_series(values_by_metric.get(metric_key) or [], length)
        for metric_key in active_metrics
    ]

    return np.array(columns, dtype=float).T


def find_nearest_successor_pairs(states: np.ndarray) -> List[tuple[int, int]]:
    """
    Возвращает пары близких состояний (i, j), для которых существуют
    следующие состояния i+1 и j+1.

    Для малых рядов не вводим строгий Theiler window: иначе на 4–5 сессиях
    может не остаться допустимых пар. Главное ограничение — i != j.
    """

    n = states.shape[0]
    pairs: List[tuple[int, int]] = []

    if n < 2:
        return pairs

    # Последнее состояние нельзя брать как стартовое: для него нет i+1.
    for i in range(n - 1):
        best_j: Optional[int] = None
        best_distance: Optional[float] = None

        for j in range(n - 1):
            if i == j:
                continue

            distance = float(np.linalg.norm(states[i] - states[j]))

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_j = j

        if best_j is not None:
            pairs.append((i, best_j))

    return pairs


def estimate_lyapunov(
    state_matrix: np.ndarray,
    epsilon: float = EPSILON,
    min_sessions: int = MIN_SESSIONS_FOR_STABILITY
) -> Optional[float]:
    """
    Дискретная конечновременная оценка показателя Ляпунова.

    Формула прототипа:
        lambda_hat = mean(ln((||X_{i+1} - X_{j+1}|| + eps) /
                              (||X_i - X_j|| + eps)))

    где X_j — ближайшее к X_i другое наблюдаемое состояние системы.
    """

    if state_matrix.shape[0] < min_sessions or state_matrix.shape[1] == 0:
        return None

    states = normalize_state_matrix(state_matrix)
    pairs = find_nearest_successor_pairs(states)

    if not pairs:
        return None

    local_estimates = []

    for i, j in pairs:
        d0 = float(np.linalg.norm(states[i] - states[j]))
        d1 = float(np.linalg.norm(states[i + 1] - states[j + 1]))

        local_estimates.append(
            math.log((d1 + epsilon) / (d0 + epsilon))
        )

    if not local_estimates:
        return None

    value = float(np.mean(local_estimates))

    if math.isnan(value) or math.isinf(value):
        return None

    return value


def detect_bifurcations_from_states(
    state_matrix: np.ndarray,
    min_sessions: int = 5
) -> List[int]:
    """
    Ищет точки резкого изменения траектории в пространстве метрик.

    Индекс возвращается в координатах оси X графика: точка i означает,
    что резкое изменение проявилось около i-й сессии.
    """

    if state_matrix.shape[0] < min_sessions or state_matrix.shape[1] == 0:
        return []

    states = normalize_state_matrix(state_matrix)

    if states.shape[0] < 3:
        return []

    velocity = np.linalg.norm(np.diff(states, axis=0), axis=1)

    if velocity.size < 3:
        return []

    acceleration = np.abs(np.diff(velocity))

    if acceleration.size == 0:
        return []

    threshold = float(np.mean(acceleration) + np.std(acceleration) * 1.5)

    if threshold <= EPSILON:
        return []

    points = []

    for index, value in enumerate(acceleration):
        if float(value) > threshold:
            # acceleration[index] описывает изменение около index + 1.
            points.append(index + 1)

    return points


def classify_stability(lyapunov: Optional[float], sessions_count: int) -> Dict[str, str]:
    if lyapunov is None:
        return {
            "status": "insufficient_data",
            "text": "Недостаточно данных для оценки устойчивости"
        }

    if sessions_count < 6:
        prefix = "Предварительная оценка: "
    else:
        prefix = ""

    if lyapunov < -0.05:
        return {
            "status": "stable",
            "text": prefix + "стабильная сходящаяся динамика"
        }

    if lyapunov <= 0.05:
        return {
            "status": "neutral",
            "text": prefix + "условно нейтральная динамика"
        }

    if lyapunov <= 0.25:
        return {
            "status": "moderate_instability",
            "text": prefix + "умеренная нестабильность"
        }

    return {
        "status": "high_instability",
        "text": prefix + "высокая нестабильность системы"
    }


def analyze_stability(
    values_by_metric: Dict[str, Sequence[float]],
    metric_order: Sequence[str]
) -> Dict[str, object]:
    """
    Главная точка входа для progression_model.py.
    """

    state_matrix = build_state_vectors(values_by_metric, metric_order)
    sessions_count = int(state_matrix.shape[0]) if state_matrix.size else 0

    lyapunov = estimate_lyapunov(state_matrix)
    bifurcation_points = detect_bifurcations_from_states(state_matrix)
    classification = classify_stability(lyapunov, sessions_count)

    return {
        "lyapunov": lyapunov,
        "bifurcation_points": bifurcation_points,
        "status": classification["status"],
        "text": classification["text"],
        "sessions_count": sessions_count,
        "metrics_count": int(state_matrix.shape[1]) if state_matrix.size else 0
    }


def analyze_single_series_stability(
    values: Iterable[float],
    epsilon: float = EPSILON
) -> Dict[str, object]:
    """
    Совместимость со старым fallback-анализом, где есть один ряд.
    """

    series = list(values or [])

    matrix = np.array([
        [_to_float(value)]
        for value in series
    ], dtype=float)

    lyapunov = estimate_lyapunov(matrix, epsilon=epsilon)
    bifurcation_points = detect_bifurcations_from_states(matrix)
    classification = classify_stability(lyapunov, len(series))

    return {
        "lyapunov": lyapunov,
        "bifurcation_points": bifurcation_points,
        "status": classification["status"],
        "text": classification["text"],
        "sessions_count": len(series),
        "metrics_count": 1 if series else 0
    }
