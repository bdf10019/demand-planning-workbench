from datetime import date, timedelta

from demand_workbench.backtesting import ForecastEngine
from demand_workbench.domain import IngestionResult, Observation, SeriesData, SeriesKey


def _weekly_series(days: int = 56) -> SeriesData:
    pattern = [4, 5, 6, 7, 8, 12, 10]
    start = date(2026, 1, 1)
    observations = tuple(
        Observation(date=start + timedelta(days=index), units=pattern[index % 7])
        for index in range(days)
    )
    return SeriesData(key=SeriesKey("SKU-1", "NORTH"), observations=observations)


def test_engine_selects_seasonal_model_for_weekly_pattern() -> None:
    ingestion = IngestionResult(
        input_sha256="a" * 64,
        source_name="fixture.csv",
        accepted_rows=56,
        rejected_rows=(),
        series=(_weekly_series(),),
    )

    result = ForecastEngine().run(ingestion, horizon=14)

    forecast = result.series[0]
    assert forecast.selected_model == "seasonal_naive_7"
    assert forecast.points[0].point == 4
    assert forecast.points[0].date == date(2026, 2, 26)
    assert forecast.scores[0].folds == 3
    assert forecast.scores[0].wape == 0


def test_short_history_is_forecast_with_warning() -> None:
    ingestion = IngestionResult(
        input_sha256="b" * 64,
        source_name="fixture.csv",
        accepted_rows=3,
        rejected_rows=(),
        series=(_weekly_series(3),),
    )
    result = ForecastEngine().run(ingestion, horizon=2)
    assert len(result.series[0].points) == 2
    assert any("insufficient" in warning.lower() for warning in result.series[0].warnings)

