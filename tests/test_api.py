from fastapi.testclient import TestClient

from demand_workbench.api import create_app


def test_api_end_to_end(tmp_path, demo_csv: str) -> None:
    client = TestClient(create_app(tmp_path / "api.sqlite3"))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    created = client.post(
        "/api/runs/csv?horizon=7&source_name=demo.csv",
        content=demo_csv.encode(),
        headers={"Content-Type": "text/csv"},
    )
    assert created.status_code == 201
    run = created.json()
    assert run["horizon"] == 7
    assert run["series"][0]["selected_model"] == "seasonal_naive_7"

    fetched = client.get(f"/api/runs/{run['id']}")
    assert fetched.status_code == 200
    exported = client.get(f"/api/runs/{run['id']}/forecast.csv")
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]

    scenario = client.post(
        f"/api/runs/{run['id']}/scenarios",
        json={
            "name": "Upside",
            "rules": [
                {
                    "operation": "multiplier",
                    "value": 1.2,
                    "start_date": run["series"][0]["points"][0]["date"],
                    "end_date": run["series"][0]["points"][-1]["date"],
                }
            ],
        },
    )
    assert scenario.status_code == 201
    assert scenario.json()["delta_units"] > 0


def test_api_rejects_bad_csv_and_missing_ids(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "api.sqlite3"))
    assert client.post("/api/runs/csv", content=b"bad").status_code == 422
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/scenarios/missing").status_code == 404
