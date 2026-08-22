"""Forecast accuracy metrics with explicit zero-demand behavior."""

from __future__ import annotations

import math
from collections.abc import Sequence


def wape(actual: Sequence[float], predicted: Sequence[float]) -> float:
    _validate_pair(actual, predicted)
    numerator = sum(
        abs(observed - forecast)
        for observed, forecast in zip(actual, predicted, strict=True)
    )
    denominator = sum(abs(value) for value in actual)
    if denominator == 0:
        return 0.0 if numerator == 0 else math.inf
    return numerator / denominator


def mase(
    actual: Sequence[float],
    predicted: Sequence[float],
    training: Sequence[float],
    *,
    season: int = 7,
) -> float:
    _validate_pair(actual, predicted)
    if not training:
        raise ValueError("MASE training data must not be empty.")
    lag = min(max(1, season), max(1, len(training) - 1))
    errors = [abs(training[index] - training[index - lag]) for index in range(lag, len(training))]
    scale = sum(errors) / len(errors) if errors else 0.0
    forecast_mae = sum(
        abs(observed - forecast)
        for observed, forecast in zip(actual, predicted, strict=True)
    ) / len(actual)
    if scale == 0:
        return 0.0 if forecast_mae == 0 else math.inf
    return forecast_mae / scale


def bias(actual: Sequence[float], predicted: Sequence[float]) -> float:
    _validate_pair(actual, predicted)
    delta = sum(
        forecast - observed for observed, forecast in zip(actual, predicted, strict=True)
    )
    denominator = sum(abs(value) for value in actual)
    if denominator == 0:
        return 0.0 if delta == 0 else math.copysign(math.inf, delta)
    return delta / denominator


def absolute_error_quantile(errors: Sequence[float], quantile: float = 0.9) -> float:
    if not errors:
        return 0.0
    if not 0 <= quantile <= 1:
        raise ValueError("Quantile must be between 0 and 1.")
    ordered = sorted(abs(value) for value in errors)
    index = math.ceil(quantile * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def _validate_pair(actual: Sequence[float], predicted: Sequence[float]) -> None:
    if not actual or len(actual) != len(predicted):
        raise ValueError("Metric inputs must be non-empty and have equal length.")
