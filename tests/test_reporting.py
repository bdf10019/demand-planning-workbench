from demand_workbench.reporting import forecast_csv, verify_manifest, write_run_artifacts
from demand_workbench.service import DemandPlanningService


def test_report_manifest_detects_tampering(tmp_path, demo_csv: str) -> None:
    service = DemandPlanningService(tmp_path / "workbench.sqlite3")
    record = service.create_run(demo_csv, 7, "demo.csv")
    output_dir = tmp_path / "report"
    write_run_artifacts(record, output_dir)

    assert verify_manifest(output_dir) == (True, [])
    assert "selected_model" in forecast_csv(record)
    assert record.id in (output_dir / "report.html").read_text(encoding="utf-8")

    (output_dir / "forecast.csv").write_text("changed", encoding="utf-8")
    valid, errors = verify_manifest(output_dir)
    assert valid is False
    assert "hash does not match" in errors[0]
