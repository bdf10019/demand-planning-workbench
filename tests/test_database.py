from datetime import date

from demand_workbench.domain import ScenarioRule
from demand_workbench.service import DemandPlanningService


def test_database_round_trip_and_scenario(tmp_path, demo_csv: str) -> None:
    service = DemandPlanningService(tmp_path / "workbench.sqlite3")
    created = service.create_run(demo_csv, 14, "demo.csv")

    loaded = service.get_run(created.id)
    assert loaded is not None
    assert loaded.batch.input_sha256 == created.batch.input_sha256
    assert loaded.batch.series[0].selected_model == "seasonal_naive_7"
    assert service.list_runs()[0]["id"] == created.id

    scenario = service.create_scenario(
        created.id,
        "Upside",
        (
            ScenarioRule(
                "multiplier",
                1.1,
                date(2026, 2, 26),
                date(2026, 3, 11),
            ),
        ),
    )
    loaded_scenario = service.get_scenario(scenario.id)
    assert loaded_scenario is not None
    assert loaded_scenario.result.scenario_units > loaded_scenario.result.base_units


def test_missing_run_returns_none(tmp_path) -> None:
    service = DemandPlanningService(tmp_path / "workbench.sqlite3")
    assert service.get_run("missing") is None
