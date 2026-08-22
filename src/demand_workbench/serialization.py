"""JSON-safe API and report serialization."""

from __future__ import annotations

import math
from typing import Any

from demand_workbench.database import RunRecord, ScenarioRecord


def run_to_dict(record: RunRecord) -> dict[str, Any]:
    batch = record.batch
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "source_name": record.source_name,
        "input_sha256": batch.input_sha256,
        "horizon": batch.horizon,
        "accepted_rows": batch.accepted_rows,
        "rejected_rows": [
            {"row_number": row.row_number, "reason": row.reason} for row in batch.rejected_rows
        ],
        "warnings": list(batch.warnings),
        "series": [
            {
                "sku_id": series.key.sku_id,
                "location_id": series.key.location_id,
                "selected_model": series.selected_model,
                "warnings": list(series.warnings),
                "scores": [
                    {
                        "model_name": score.model_name,
                        "wape": _finite_or_none(score.wape),
                        "mase": _finite_or_none(score.mase),
                        "bias": _finite_or_none(score.bias),
                        "folds": score.folds,
                    }
                    for score in series.scores
                ],
                "points": [
                    {
                        "date": point.date.isoformat(),
                        "point": point.point,
                        "lower": point.lower,
                        "upper": point.upper,
                    }
                    for point in series.points
                ],
            }
            for series in batch.series
        ],
    }


def scenario_to_dict(record: ScenarioRecord) -> dict[str, Any]:
    result = record.result
    return {
        "id": record.id,
        "run_id": record.run_id,
        "created_at": record.created_at.isoformat(),
        "name": result.name,
        "base_units": result.base_units,
        "scenario_units": result.scenario_units,
        "delta_units": result.delta_units,
        "rules": [
            {
                "operation": rule.operation,
                "value": rule.value,
                "start_date": rule.start_date.isoformat(),
                "end_date": rule.end_date.isoformat(),
                "sku_id": rule.sku_id,
                "location_id": rule.location_id,
            }
            for rule in result.rules
        ],
        "series": [
            {
                "sku_id": series.key.sku_id,
                "location_id": series.key.location_id,
                "points": [
                    {
                        "date": point.date.isoformat(),
                        "base": point.base,
                        "scenario": point.scenario,
                        "delta": point.delta,
                    }
                    for point in series.points
                ],
            }
            for series in result.series
        ],
    }


def _finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None
