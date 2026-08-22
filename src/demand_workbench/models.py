"""Small, explainable forecasting models behind a reusable registry."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol


class ForecastModel(Protocol):
    """Plugin contract used by backtesting and final forecasting."""

    name: str

    def predict(self, history: Sequence[float], horizon: int) -> list[float]: ...


class ModelRegistry:
    """Ordered model registry with duplicate-name protection."""

    def __init__(self) -> None:
        self._models: dict[str, ForecastModel] = {}

    def register(self, model: ForecastModel) -> None:
        if model.name in self._models:
            raise ValueError(f"Forecast model is already registered: {model.name}")
        self._models[model.name] = model

    def all(self) -> tuple[ForecastModel, ...]:
        return tuple(self._models.values())

    def get(self, name: str) -> ForecastModel:
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(f"Unknown forecast model: {name}") from exc


class SeasonalNaiveModel:
    name = "seasonal_naive_7"

    def predict(self, history: Sequence[float], horizon: int) -> list[float]:
        _validate(history, horizon)
        season = min(7, len(history))
        pattern = [float(value) for value in history[-season:]]
        return [max(0.0, pattern[index % season]) for index in range(horizon)]


class MovingAverageModel:
    name = "moving_average_28"

    def predict(self, history: Sequence[float], horizon: int) -> list[float]:
        _validate(history, horizon)
        window = history[-min(28, len(history)) :]
        estimate = sum(window) / len(window)
        return [max(0.0, float(estimate))] * horizon


class CrostonSbaModel:
    """Syntetos-Boylan corrected Croston estimate for intermittent demand."""

    name = "croston_sba"

    def __init__(self, alpha: float = 0.2) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("Croston alpha must be in (0, 1].")
        self.alpha = alpha

    def predict(self, history: Sequence[float], horizon: int) -> list[float]:
        _validate(history, horizon)
        nonzero = [(index, float(value)) for index, value in enumerate(history) if value > 0]
        if not nonzero:
            return [0.0] * horizon

        first_index, first_value = nonzero[0]
        demand = first_value
        interval = float(first_index + 1)
        previous_index = first_index
        for current_index, value in nonzero[1:]:
            gap = float(current_index - previous_index)
            demand = self.alpha * value + (1 - self.alpha) * demand
            interval = self.alpha * gap + (1 - self.alpha) * interval
            previous_index = current_index
        estimate = (1 - self.alpha / 2) * demand / max(interval, 1.0)
        return [max(0.0, estimate)] * horizon


class LinearTrendModel:
    """Bounded ordinary least-squares trend over the most recent 84 days."""

    name = "linear_trend_84"

    def predict(self, history: Sequence[float], horizon: int) -> list[float]:
        _validate(history, horizon)
        values = [float(value) for value in history[-min(84, len(history)) :]]
        if len(values) == 1:
            return [max(0.0, values[0])] * horizon

        count = len(values)
        mean_x = (count - 1) / 2
        mean_y = sum(values) / count
        denominator = sum((index - mean_x) ** 2 for index in range(count))
        slope = sum(
            (index - mean_x) * (value - mean_y) for index, value in enumerate(values)
        ) / max(denominator, 1.0)
        intercept = mean_y - slope * mean_x
        cap = max(max(values) * 3, mean_y * 3, 1.0)
        forecasts = []
        for step in range(horizon):
            estimate = intercept + slope * (count + step)
            forecasts.append(min(cap, max(0.0, estimate)))
        return forecasts


def default_model_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(SeasonalNaiveModel())
    registry.register(MovingAverageModel())
    registry.register(CrostonSbaModel())
    registry.register(LinearTrendModel())
    return registry


def _validate(history: Sequence[float], horizon: int) -> None:
    if not history:
        raise ValueError("Forecast history must not be empty.")
    if horizon < 1:
        raise ValueError("Forecast horizon must be positive.")
    if any(not math.isfinite(value) or value < 0 for value in history):
        raise ValueError("Forecast history must contain finite non-negative values.")
