"""SQLite persistence for reproducible forecast and scenario runs."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from demand_workbench.domain import (
    ForecastBatch,
    ForecastPoint,
    ModelScore,
    RejectedRow,
    ScenarioPoint,
    ScenarioResult,
    ScenarioRule,
    ScenarioSeries,
    SeriesForecast,
    SeriesKey,
)


@dataclass(frozen=True)
class RunRecord:
    id: str
    created_at: datetime
    source_name: str
    batch: ForecastBatch


@dataclass(frozen=True)
class ScenarioRecord:
    id: str
    run_id: str
    created_at: datetime
    result: ScenarioResult


class WorkbenchDatabase:
    """A small repository that opens one short-lived connection per operation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS forecast_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    horizon INTEGER NOT NULL CHECK (horizon BETWEEN 1 AND 90),
                    accepted_rows INTEGER NOT NULL,
                    rejected_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    series_count INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('completed'))
                );

                CREATE TABLE IF NOT EXISTS series_forecasts (
                    run_id TEXT NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
                    sku_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    selected_model TEXT NOT NULL,
                    scores_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, sku_id, location_id)
                );

                CREATE TABLE IF NOT EXISTS forecast_points (
                    run_id TEXT NOT NULL,
                    sku_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    forecast_date TEXT NOT NULL,
                    point REAL NOT NULL,
                    lower_bound REAL NOT NULL,
                    upper_bound REAL NOT NULL,
                    PRIMARY KEY (run_id, sku_id, location_id, forecast_date),
                    FOREIGN KEY (run_id, sku_id, location_id)
                        REFERENCES series_forecasts(run_id, sku_id, location_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    name TEXT NOT NULL,
                    rules_json TEXT NOT NULL,
                    base_units REAL NOT NULL,
                    scenario_units REAL NOT NULL,
                    delta_units REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenario_points (
                    scenario_id TEXT NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
                    sku_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    forecast_date TEXT NOT NULL,
                    base REAL NOT NULL,
                    scenario REAL NOT NULL,
                    PRIMARY KEY (scenario_id, sku_id, location_id, forecast_date)
                );

                CREATE INDEX IF NOT EXISTS ix_runs_created_at
                    ON forecast_runs(created_at DESC);
                CREATE INDEX IF NOT EXISTS ix_scenarios_run_id
                    ON scenarios(run_id, created_at DESC);
                """
            )

    def save_run(self, source_name: str, batch: ForecastBatch) -> RunRecord:
        created_at = datetime.now(UTC)
        run_id = f"run-{created_at:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
        rejected_json = json.dumps(
            [
                {"row_number": item.row_number, "reason": item.reason}
                for item in batch.rejected_rows
            ],
            ensure_ascii=False,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO forecast_runs (
                    id, created_at, source_name, input_sha256, horizon,
                    accepted_rows, rejected_json, warnings_json, series_count, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                (
                    run_id,
                    created_at.isoformat(),
                    Path(source_name).name,
                    batch.input_sha256,
                    batch.horizon,
                    batch.accepted_rows,
                    rejected_json,
                    json.dumps(batch.warnings, ensure_ascii=False),
                    len(batch.series),
                ),
            )
            for series in batch.series:
                connection.execute(
                    """
                    INSERT INTO series_forecasts (
                        run_id, sku_id, location_id, selected_model, scores_json, warnings_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        series.key.sku_id,
                        series.key.location_id,
                        series.selected_model,
                        self._scores_to_json(series.scores),
                        json.dumps(series.warnings, ensure_ascii=False),
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO forecast_points (
                        run_id, sku_id, location_id, forecast_date,
                        point, lower_bound, upper_bound
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            series.key.sku_id,
                            series.key.location_id,
                            point.date.isoformat(),
                            point.point,
                            point.lower,
                            point.upper,
                        )
                        for point in series.points
                    ],
                )
        return RunRecord(run_id, created_at, Path(source_name).name, batch)

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as connection:
            run_row = connection.execute(
                "SELECT * FROM forecast_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run_row is None:
                return None
            series_rows = connection.execute(
                """
                SELECT * FROM series_forecasts
                WHERE run_id = ? ORDER BY sku_id, location_id
                """,
                (run_id,),
            ).fetchall()
            forecasts: list[SeriesForecast] = []
            for series_row in series_rows:
                points = connection.execute(
                    """
                    SELECT * FROM forecast_points
                    WHERE run_id = ? AND sku_id = ? AND location_id = ?
                    ORDER BY forecast_date
                    """,
                    (run_id, series_row["sku_id"], series_row["location_id"]),
                ).fetchall()
                forecasts.append(
                    SeriesForecast(
                        key=SeriesKey(series_row["sku_id"], series_row["location_id"]),
                        selected_model=series_row["selected_model"],
                        scores=self._scores_from_json(series_row["scores_json"]),
                        warnings=tuple(json.loads(series_row["warnings_json"])),
                        points=tuple(
                            ForecastPoint(
                                date=date.fromisoformat(point["forecast_date"]),
                                point=point["point"],
                                lower=point["lower_bound"],
                                upper=point["upper_bound"],
                            )
                            for point in points
                        ),
                    )
                )
            rejected = tuple(
                RejectedRow(row_number=item["row_number"], reason=item["reason"])
                for item in json.loads(run_row["rejected_json"])
            )
            batch = ForecastBatch(
                input_sha256=run_row["input_sha256"],
                horizon=run_row["horizon"],
                series=tuple(forecasts),
                accepted_rows=run_row["accepted_rows"],
                rejected_rows=rejected,
                warnings=tuple(json.loads(run_row["warnings_json"])),
            )
            return RunRecord(
                id=run_row["id"],
                created_at=datetime.fromisoformat(run_row["created_at"]),
                source_name=run_row["source_name"],
                batch=batch,
            )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, source_name, input_sha256, horizon,
                       accepted_rows, json_array_length(rejected_json) AS rejected_rows,
                       series_count, status
                FROM forecast_runs ORDER BY created_at DESC LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_scenario(self, run_id: str, result: ScenarioResult) -> ScenarioRecord:
        created_at = datetime.now(UTC)
        scenario_id = f"scenario-{created_at:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
        rules_json = json.dumps(
            [
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
            ensure_ascii=False,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scenarios (
                    id, run_id, created_at, name, rules_json,
                    base_units, scenario_units, delta_units
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scenario_id,
                    run_id,
                    created_at.isoformat(),
                    result.name,
                    rules_json,
                    result.base_units,
                    result.scenario_units,
                    result.delta_units,
                ),
            )
            rows = [
                (
                    scenario_id,
                    series.key.sku_id,
                    series.key.location_id,
                    point.date.isoformat(),
                    point.base,
                    point.scenario,
                )
                for series in result.series
                for point in series.points
            ]
            connection.executemany(
                """
                INSERT INTO scenario_points (
                    scenario_id, sku_id, location_id, forecast_date, base, scenario
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return ScenarioRecord(scenario_id, run_id, created_at, result)

    def get_scenario(self, scenario_id: str) -> ScenarioRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
            ).fetchone()
            if row is None:
                return None
            point_rows = connection.execute(
                """
                SELECT * FROM scenario_points
                WHERE scenario_id = ? ORDER BY sku_id, location_id, forecast_date
                """,
                (scenario_id,),
            ).fetchall()

        grouped: dict[SeriesKey, list[ScenarioPoint]] = {}
        for point in point_rows:
            key = SeriesKey(point["sku_id"], point["location_id"])
            grouped.setdefault(key, []).append(
                ScenarioPoint(
                    date=date.fromisoformat(point["forecast_date"]),
                    base=point["base"],
                    scenario=point["scenario"],
                )
            )
        rules = tuple(
            ScenarioRule(
                operation=item["operation"],
                value=item["value"],
                start_date=date.fromisoformat(item["start_date"]),
                end_date=date.fromisoformat(item["end_date"]),
                sku_id=item["sku_id"],
                location_id=item["location_id"],
            )
            for item in json.loads(row["rules_json"])
        )
        result = ScenarioResult(
            name=row["name"],
            rules=rules,
            series=tuple(
                ScenarioSeries(key=key, points=tuple(points)) for key, points in grouped.items()
            ),
        )
        return ScenarioRecord(
            id=row["id"],
            run_id=row["run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            result=result,
        )

    def healthcheck(self) -> bool:
        with self._connect() as connection:
            value = connection.execute("SELECT 1").fetchone()[0]
            return bool(value == 1)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _scores_to_json(scores: tuple[ModelScore, ...]) -> str:
        payload = [
            {
                "model_name": score.model_name,
                "wape": score.wape if math.isfinite(score.wape) else None,
                "mase": score.mase if math.isfinite(score.mase) else None,
                "bias": score.bias if math.isfinite(score.bias) else None,
                "folds": score.folds,
            }
            for score in scores
        ]
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _scores_from_json(payload: str) -> tuple[ModelScore, ...]:
        return tuple(
            ModelScore(
                model_name=item["model_name"],
                wape=item["wape"] if item["wape"] is not None else math.inf,
                mase=item["mase"] if item["mase"] is not None else math.inf,
                bias=item["bias"] if item["bias"] is not None else math.inf,
                folds=item["folds"],
            )
            for item in json.loads(payload)
        )
