"""Application service joining pure domain logic with persistence."""

from __future__ import annotations

from pathlib import Path

from demand_workbench.backtesting import ForecastEngine
from demand_workbench.database import RunRecord, ScenarioRecord, WorkbenchDatabase
from demand_workbench.domain import ScenarioRule
from demand_workbench.ingest import CsvIngestor
from demand_workbench.scenarios import ScenarioEngine


class DemandPlanningService:
    def __init__(self, database_path: str | Path) -> None:
        self.database = WorkbenchDatabase(database_path)
        self.ingestor = CsvIngestor()
        self.forecaster = ForecastEngine()
        self.scenarios = ScenarioEngine()

    def create_run(self, csv_text: str, horizon: int, source_name: str) -> RunRecord:
        ingestion = self.ingestor.parse(csv_text, source_name=Path(source_name).name)
        batch = self.forecaster.run(ingestion, horizon=horizon)
        return self.database.save_run(source_name, batch)

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.database.get_run(run_id)

    def list_runs(self, limit: int = 50) -> list[dict[str, object]]:
        return self.database.list_runs(limit)

    def create_scenario(
        self, run_id: str, name: str, rules: tuple[ScenarioRule, ...]
    ) -> ScenarioRecord:
        run = self.database.get_run(run_id)
        if run is None:
            raise KeyError(f"Forecast run was not found: {run_id}")
        result = self.scenarios.apply(run.batch, name, rules)
        return self.database.save_scenario(run_id, result)

    def get_scenario(self, scenario_id: str) -> ScenarioRecord | None:
        return self.database.get_scenario(scenario_id)
