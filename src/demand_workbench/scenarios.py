"""Deterministic, auditable overlays for non-causal what-if planning."""

from __future__ import annotations

from datetime import date

from demand_workbench.domain import (
    ForecastBatch,
    ScenarioPoint,
    ScenarioResult,
    ScenarioRule,
    ScenarioSeries,
    SeriesForecast,
)


class ScenarioEngine:
    def apply(
        self, forecast: ForecastBatch, name: str, rules: tuple[ScenarioRule, ...]
    ) -> ScenarioResult:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Scenario name is required.")
        if not rules:
            raise ValueError("At least one scenario rule is required.")
        return ScenarioResult(
            name=clean_name,
            rules=rules,
            series=tuple(self._apply_series(series, rules) for series in forecast.series),
        )

    def _apply_series(
        self, forecast: SeriesForecast, rules: tuple[ScenarioRule, ...]
    ) -> ScenarioSeries:
        scenario_points: list[ScenarioPoint] = []
        for point in forecast.points:
            adjusted = point.point
            for rule in rules:
                if not self._matches(forecast, point.date, rule):
                    continue
                if rule.operation == "multiplier":
                    adjusted *= rule.value
                elif rule.operation == "additive":
                    adjusted += rule.value
                else:
                    adjusted = rule.value
                adjusted = max(0.0, adjusted)
            scenario_points.append(
                ScenarioPoint(date=point.date, base=point.point, scenario=adjusted)
            )
        return ScenarioSeries(key=forecast.key, points=tuple(scenario_points))

    @staticmethod
    def _matches(forecast: SeriesForecast, point_date: date, rule: ScenarioRule) -> bool:
        if not rule.start_date <= point_date <= rule.end_date:
            return False
        if rule.sku_id is not None and rule.sku_id != forecast.key.sku_id:
            return False
        return rule.location_id is None or rule.location_id == forecast.key.location_id
