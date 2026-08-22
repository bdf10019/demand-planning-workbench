"""Local-only FastAPI surface for the web console and automation clients."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from demand_workbench import __version__
from demand_workbench.domain import ScenarioRule
from demand_workbench.reporting import forecast_csv, scenario_csv
from demand_workbench.serialization import run_to_dict, scenario_to_dict
from demand_workbench.service import DemandPlanningService

MAX_CSV_BYTES = 5 * 1024 * 1024


class ScenarioRuleRequest(BaseModel):
    operation: Literal["multiplier", "additive", "override"]
    value: float = Field(ge=0)
    start_date: date
    end_date: date
    sku_id: str | None = Field(default=None, max_length=120)
    location_id: str | None = Field(default=None, max_length=120)


class ScenarioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rules: list[ScenarioRuleRequest] = Field(min_length=1, max_length=50)


def create_app(database_path: str | Path | None = None) -> FastAPI:
    configured_path: str | Path = (
        database_path
        if database_path is not None
        else os.getenv("DEMAND_WORKBENCH_DB", "outputs/workbench.sqlite3")
    )
    service = DemandPlanningService(configured_path)
    application = FastAPI(
        title="Demand Planning Workbench API",
        version=__version__,
        description="Traceable demand forecasting and scenario planning.",
    )
    application.state.service = service
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok" if service.database.healthcheck() else "degraded",
            "version": __version__,
            "models": [model.name for model in service.forecaster.registry.all()],
        }

    @application.get("/api/runs")
    def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, object]]:
        return service.list_runs(limit)

    @application.post("/api/runs/csv", status_code=201)
    async def create_run(
        request: Request,
        horizon: int = Query(default=14, ge=1, le=90),
        source_name: str = Query(default="sales.csv", min_length=1, max_length=160),
    ) -> dict[str, object]:
        raw = await request.body()
        if len(raw) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail="CSV input exceeds the 5 MiB API limit.")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="CSV input must be UTF-8.") from exc
        try:
            record = service.create_run(text, horizon, Path(source_name).name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return run_to_dict(record)

    @application.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        record = service.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Forecast run not found.")
        return run_to_dict(record)

    @application.get("/api/runs/{run_id}/forecast.csv")
    def export_forecast(run_id: str) -> Response:
        record = service.get_run(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Forecast run not found.")
        return Response(
            content=forecast_csv(record),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{run_id}-forecast.csv"'},
        )

    @application.post("/api/runs/{run_id}/scenarios", status_code=201)
    def create_scenario(run_id: str, payload: ScenarioRequest) -> dict[str, object]:
        rules = tuple(
            ScenarioRule(
                operation=item.operation,
                value=item.value,
                start_date=item.start_date,
                end_date=item.end_date,
                sku_id=item.sku_id,
                location_id=item.location_id,
            )
            for item in payload.rules
        )
        try:
            record = service.create_scenario(run_id, payload.name, rules)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Forecast run not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return scenario_to_dict(record)

    @application.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str) -> dict[str, object]:
        record = service.get_scenario(scenario_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return scenario_to_dict(record)

    @application.get("/api/scenarios/{scenario_id}/forecast.csv")
    def export_scenario(scenario_id: str) -> Response:
        record = service.get_scenario(scenario_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return Response(
            content=scenario_csv(record),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{scenario_id}-forecast.csv"'},
        )

    return application


app = create_app()
