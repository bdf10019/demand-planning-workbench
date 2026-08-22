"""Strict CSV ingestion and daily-series normalization."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from demand_workbench.domain import (
    IngestionResult,
    Observation,
    RejectedRow,
    SeriesData,
    SeriesKey,
)

REQUIRED_COLUMNS = frozenset({"date", "sku_id", "location_id", "units"})
OPTIONAL_COLUMNS = frozenset({"price", "promo", "stockout"})


@dataclass
class _Aggregate:
    units: float = 0.0
    price: float | None = None
    promo: bool | None = None
    stockout: bool | None = None
    rows: int = 0


class CsvIngestor:
    """Parse the public CSV contract without silently dropping invalid rows."""

    def parse(self, text: str, source_name: str = "sales.csv") -> IngestionResult:
        if not text.strip():
            raise ValueError("CSV input is empty.")

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        headers = set(reader.fieldnames or ())
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        aggregates: dict[tuple[SeriesKey, date], _Aggregate] = {}
        rejected: list[RejectedRow] = []
        accepted_rows = 0
        unknown_columns = headers - REQUIRED_COLUMNS - OPTIONAL_COLUMNS

        for row_number, row in enumerate(reader, start=2):
            try:
                key = SeriesKey(
                    sku_id=self._required_text(row, "sku_id"),
                    location_id=self._required_text(row, "location_id"),
                )
                observed_on = date.fromisoformat(self._required_text(row, "date"))
                units = self._non_negative_float(row, "units", required=True)
                price = self._non_negative_float(row, "price", required=False)
                promo = self._optional_bool(row.get("promo"), "promo")
                stockout = self._optional_bool(row.get("stockout"), "stockout")
            except ValueError as exc:
                rejected.append(RejectedRow(row_number=row_number, reason=str(exc)))
                continue

            aggregate = aggregates.setdefault((key, observed_on), _Aggregate())
            aggregate.units += units if units is not None else 0.0
            aggregate.price = price if price is not None else aggregate.price
            aggregate.promo = self._merge_flag(aggregate.promo, promo)
            aggregate.stockout = self._merge_flag(aggregate.stockout, stockout)
            aggregate.rows += 1
            accepted_rows += 1

        if not aggregates:
            raise ValueError("CSV contains no valid observations.")

        by_series: dict[SeriesKey, dict[date, _Aggregate]] = defaultdict(dict)
        for (key, observed_on), aggregate in aggregates.items():
            by_series[key][observed_on] = aggregate

        series_results: list[SeriesData] = []
        duplicate_groups = 0
        for key in sorted(by_series):
            dated = by_series[key]
            first_day = min(dated)
            last_day = max(dated)
            observations: list[Observation] = []
            missing_days = 0
            current = first_day
            while current <= last_day:
                current_aggregate = dated.get(current)
                if current_aggregate is None:
                    observations.append(Observation(date=current, units=0.0, imputed=True))
                    missing_days += 1
                else:
                    if current_aggregate.rows > 1:
                        duplicate_groups += 1
                    observations.append(
                        Observation(
                            date=current,
                            units=current_aggregate.units,
                            price=current_aggregate.price,
                            promo=current_aggregate.promo,
                            stockout=current_aggregate.stockout,
                        )
                    )
                current += timedelta(days=1)

            series_warnings: list[str] = []
            if missing_days:
                series_warnings.append(
                    f"{missing_days} missing calendar day(s) were filled with zero units."
                )
            if any(item.stockout for item in observations):
                series_warnings.append(
                    "Stockout flags are present; recorded sales may understate latent demand."
                )
            series_results.append(
                SeriesData(
                    key=key,
                    observations=tuple(observations),
                    warnings=tuple(series_warnings),
                )
            )

        warnings: list[str] = []
        if unknown_columns:
            warnings.append(f"Ignored columns: {', '.join(sorted(unknown_columns))}.")
        if duplicate_groups:
            warnings.append(f"Merged {duplicate_groups} duplicate series/date group(s).")

        return IngestionResult(
            input_sha256=digest,
            source_name=source_name,
            accepted_rows=accepted_rows,
            rejected_rows=tuple(rejected),
            series=tuple(series_results),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _required_text(row: dict[str, str | None], column: str) -> str:
        value = (row.get(column) or "").strip()
        if not value:
            raise ValueError(f"{column} is required")
        return value

    @staticmethod
    def _non_negative_float(
        row: dict[str, str | None], column: str, *, required: bool
    ) -> float | None:
        raw = (row.get(column) or "").strip()
        if not raw and not required:
            return None
        if not raw:
            raise ValueError(f"{column} is required")
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"{column} must be numeric") from exc
        if value < 0:
            raise ValueError(f"{column} must be non-negative")
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError(f"{column} must be finite")
        return value

    @staticmethod
    def _optional_bool(raw: str | None, column: str) -> bool | None:
        value = (raw or "").strip().lower()
        if not value:
            return None
        if value in {"1", "true", "yes", "y"}:
            return True
        if value in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"{column} must be true/false, yes/no, or 1/0")

    @staticmethod
    def _merge_flag(left: bool | None, right: bool | None) -> bool | None:
        if left is True or right is True:
            return True
        if left is False or right is False:
            return False
        return None
