from datetime import date

import pytest

from demand_workbench.domain import (
    ForecastBatch,
    ForecastPoint,
    ScenarioRule,
    SeriesForecast,
    SeriesKey,
)
from demand_workbench.scenarios import ScenarioEngine


def _forecast() -> ForecastBatch:
    return ForecastBatch(
        input_sha256="c" * 64,
        horizon=2,
        accepted_rows=10,
        rejected_rows=(),
        series=(
            SeriesForecast(
                key=SeriesKey("SKU-1", "NORTH"),
                selected_model="fixture",
                scores=(),
                points=(
                    ForecastPoint(date(2026, 2, 1), 10, 8, 12),
                    ForecastPoint(date(2026, 2, 2), 20, 16, 24),
                ),
            ),
        ),
    )


def test_scenario_rules_are_scoped_and_ordered() -> None:
    rules = (
        ScenarioRule("multiplier", 1.5, date(2026, 2, 1), date(2026, 2, 2), "SKU-1"),
        ScenarioRule("additive", 5, date(2026, 2, 2), date(2026, 2, 2), "SKU-1"),
    )
    result = ScenarioEngine().apply(_forecast(), "Promotion", rules)
    assert [point.scenario for point in result.series[0].points] == [15, 35]
    assert result.base_units == 30
    assert result.delta_units == 20


def test_scenario_rejects_reverse_date_range() -> None:
    with pytest.raises(ValueError, match="end_date"):
        ScenarioRule("override", 5, date(2026, 2, 2), date(2026, 2, 1))

