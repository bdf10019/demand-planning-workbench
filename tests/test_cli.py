import json

from demand_workbench.cli import main


def test_cli_run_and_verify(tmp_path, demo_csv: str, capsys) -> None:
    input_path = tmp_path / "demo.csv"
    input_path.write_text(demo_csv, encoding="utf-8")
    output_dir = tmp_path / "report"

    result = main(
        [
            "run",
            "--input",
            str(input_path),
            "--horizon",
            "7",
            "--database",
            str(tmp_path / "cli.sqlite3"),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["series"] == 1

    assert main(["verify-output", str(output_dir)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    assert main(["benchmark", "--input", str(input_path), "--iterations", "2"]) == 0
    benchmark = json.loads(capsys.readouterr().out)
    assert benchmark["accepted_rows"] == 56
    assert benchmark["median_ms"] > 0
