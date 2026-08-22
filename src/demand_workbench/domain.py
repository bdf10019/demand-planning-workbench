"""Domain objects shared by ingestion, forecasting and scenario planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass(frozen=True, order=True)
class SeriesKey:
    """Stable business key for one daily demand series."""

    sku_id: str
    location_id: str

    @property
    def value(self) -> str:
        return f"{self.sku_id}@{self.location_id}"


@dataclass(frozen=True)
class Observation:
    """One normalized daily observation."""

    date: date
    units: float
    price: float | None = None
    promo: bool | None = None
    stockout: bool | None = None
    imputed: bool = False


@dataclass(frozen=True)
class SeriesData:
    key: SeriesKey
    observations: tuple[Observation, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RejectedRow:
    row_number: int
    reason: str


@dataclass(frozen=True)
class IngestionResult:
    input_sha256: str
    source_name: str
    accepted_rows: int
    rejected_rows: tuple[RejectedRow, ...]
    series: tuple[SeriesData, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelScore:
    model_name: str
    wape: float
    mase: float
    bias: float
    folds: int


@dataclass(frozen=True)
class ForecastPoint:
    date: date
    point: float
    lower: float
    upper: float


@dataclass(frozen=True)
class SeriesForecast:
    key: SeriesKey
    selected_model: str
    scores: tuple[ModelScore, ...]
    points: tuple[ForecastPoint, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ForecastBatch:
    input_sha256: str
    horizon: int
    series: tuple[SeriesForecast, ...]
    accepted_rows: int
    rejected_rows: tuple[RejectedRow, ...]
    warnings: tuple[str, ...] = ()


ScenarioOperation = Literal["multiplier", "additive", "override"]


@dataclass(frozen=True)
class ScenarioRule:
    operation: ScenarioOperation
    value: float
    start_date: date
    end_date: date
    sku_id: str | None = None
    location_id: str | None = None

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("Scenario end_date must not be earlier than start_date.")
        if self.operation == "multiplier" and self.value < 0:
            raise ValueError("Scenario multiplier must be non-negative.")


@dataclass(frozen=True)
class ScenarioPoint:
    date: date
    base: float
    scenario: float

    @property
    def delta(self) -> float:
        return self.scenario - self.base


@dataclass(frozen=True)
class ScenarioSeries:
    key: SeriesKey
    points: tuple[ScenarioPoint, ...]


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    rules: tuple[ScenarioRule, ...]
    series: tuple[ScenarioSeries, ...]
    base_units: float = field(init=False)
    scenario_units: float = field(init=False)
    delta_units: float = field(init=False)

    def __post_init__(self) -> None:
        base = sum(point.base for series in self.series for point in series.points)
        scenario = sum(point.scenario for series in self.series for point in series.points)
        object.__setattr__(self, "base_units", base)
        object.__setattr__(self, "scenario_units", scenario)
        object.__setattr__(self, "delta_units", scenario - base)
