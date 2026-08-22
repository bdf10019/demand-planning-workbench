"""Rolling-origin model evaluation and traceable forecast generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from demand_workbench.domain import (
    ForecastBatch,
    ForecastPoint,
    IngestionResult,
    ModelScore,
    SeriesData,
    SeriesForecast,
)
from demand_workbench.metrics import absolute_error_quantile, bias, mase, wape
from demand_workbench.models import ForecastModel, ModelRegistry, default_model_registry


@dataclass(frozen=True)
class _Evaluation:
    score: ModelScore
    residuals: tuple[float, ...]


class ForecastEngine:
    """Select a model per business series using chronological validation only."""

    def __init__(self, registry: ModelRegistry | None = None, max_folds: int = 3) -> None:
        if max_folds < 1:
            raise ValueError("max_folds must be positive.")
        self.registry = registry or default_model_registry()
        self.max_folds = max_folds

    def run(self, ingestion: IngestionResult, horizon: int) -> ForecastBatch:
        if not 1 <= horizon <= 90:
            raise ValueError("Forecast horizon must be between 1 and 90 days.")
        forecasts = tuple(self.forecast_series(series, horizon) for series in ingestion.series)
        return ForecastBatch(
            input_sha256=ingestion.input_sha256,
            horizon=horizon,
            series=forecasts,
            accepted_rows=ingestion.accepted_rows,
            rejected_rows=ingestion.rejected_rows,
            warnings=ingestion.warnings,
        )

    def forecast_series(self, series: SeriesData, horizon: int) -> SeriesForecast:
        history = [observation.units for observation in series.observations]
        if not history:
            raise ValueError("A demand series must contain at least one observation.")

        evaluations = tuple(
            self._evaluate(model, history, horizon) for model in self.registry.all()
        )
        winner = min(
            evaluations,
            key=lambda evaluation: (
                self._finite_or_large(evaluation.score.wape),
                abs(self._finite_or_large(evaluation.score.bias)),
                evaluation.score.model_name,
            ),
        )
        model = self.registry.get(winner.score.model_name)
        predictions = model.predict(history, horizon)
        interval = absolute_error_quantile(winner.residuals, 0.9)
        last_day = series.observations[-1].date
        points = tuple(
            ForecastPoint(
                date=last_day + timedelta(days=index + 1),
                point=prediction,
                lower=max(0.0, prediction - interval),
                upper=prediction + interval,
            )
            for index, prediction in enumerate(predictions)
        )
        warnings = list(series.warnings)
        if len(history) < 28:
            warnings.append("Fewer than 28 history days; model comparison is low confidence.")
        if not winner.residuals:
            warnings.append(
                "History was insufficient for a validation fold; interval width is zero."
            )
        return SeriesForecast(
            key=series.key,
            selected_model=winner.score.model_name,
            scores=tuple(evaluation.score for evaluation in evaluations),
            points=points,
            warnings=tuple(warnings),
        )

    def _evaluate(
        self, model: ForecastModel, history: list[float], requested_horizon: int
    ) -> _Evaluation:
        origins = self._origins(len(history), requested_horizon)
        all_actual: list[float] = []
        all_predicted: list[float] = []
        fold_mase: list[float] = []
        residuals: list[float] = []

        for origin, validation_horizon in origins:
            training = history[:origin]
            actual = history[origin : origin + validation_horizon]
            predicted = model.predict(training, validation_horizon)
            all_actual.extend(actual)
            all_predicted.extend(predicted)
            fold_mase.append(mase(actual, predicted, training))
            residuals.extend(
                observed - forecast for observed, forecast in zip(actual, predicted, strict=True)
            )

        if not origins:
            score = ModelScore(
                model_name=model.name,
                wape=math.inf,
                mase=math.inf,
                bias=math.inf,
                folds=0,
            )
        else:
            finite_mase = [value for value in fold_mase if math.isfinite(value)]
            score = ModelScore(
                model_name=model.name,
                wape=wape(all_actual, all_predicted),
                mase=sum(finite_mase) / len(finite_mase) if finite_mase else math.inf,
                bias=bias(all_actual, all_predicted),
                folds=len(origins),
            )
        return _Evaluation(score=score, residuals=tuple(residuals))

    def _origins(self, history_length: int, requested_horizon: int) -> tuple[tuple[int, int], ...]:
        if history_length < 8:
            return ()
        validation_horizon = min(requested_horizon, max(1, history_length // 4))
        minimum_training = min(14, max(4, history_length // 2))
        candidates: list[tuple[int, int]] = []
        origin = history_length - validation_horizon
        while origin >= minimum_training and len(candidates) < self.max_folds:
            candidates.append((origin, validation_horizon))
            origin -= validation_horizon
        return tuple(reversed(candidates))

    @staticmethod
    def _finite_or_large(value: float) -> float:
        return value if math.isfinite(value) else 1e300
