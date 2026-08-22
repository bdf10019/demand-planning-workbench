"""CSV, JSON, HTML and hash-manifest report generation."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any

from demand_workbench.database import RunRecord, ScenarioRecord
from demand_workbench.serialization import run_to_dict


def forecast_csv(record: RunRecord) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "run_id",
            "sku_id",
            "location_id",
            "forecast_date",
            "point",
            "lower",
            "upper",
            "selected_model",
        ]
    )
    for series in record.batch.series:
        for point in series.points:
            writer.writerow(
                [
                    record.id,
                    series.key.sku_id,
                    series.key.location_id,
                    point.date.isoformat(),
                    _number(point.point),
                    _number(point.lower),
                    _number(point.upper),
                    series.selected_model,
                ]
            )
    return output.getvalue()


def scenario_csv(record: ScenarioRecord) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ["scenario_id", "sku_id", "location_id", "forecast_date", "base", "scenario", "delta"]
    )
    for series in record.result.series:
        for point in series.points:
            writer.writerow(
                [
                    record.id,
                    series.key.sku_id,
                    series.key.location_id,
                    point.date.isoformat(),
                    _number(point.base),
                    _number(point.scenario),
                    _number(point.delta),
                ]
            )
    return output.getvalue()


def write_run_artifacts(record: RunRecord, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "forecast.csv": forecast_csv(record),
        "summary.json": json.dumps(
            run_to_dict(record), ensure_ascii=False, indent=2, allow_nan=False
        )
        + "\n",
        "report.html": _report_html(record),
    }
    manifest_files: list[dict[str, object]] = []
    for name, content in files.items():
        encoded = content.encode("utf-8")
        (output_dir / name).write_bytes(encoded)
        manifest_files.append(
            {"path": name, "sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}
        )
    manifest = {
        "run_id": record.id,
        "input_sha256": record.batch.input_sha256,
        "files": manifest_files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify_manifest(output_dir: Path) -> tuple[bool, list[str]]:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return False, ["manifest.json is missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for item in manifest.get("files", []):
        path = output_dir / item["path"]
        if not path.exists():
            errors.append(f"{item['path']} is missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            errors.append(f"{item['path']} hash does not match")
    return not errors, errors


def _report_html(record: RunRecord) -> str:
    rows = []
    for series in record.batch.series:
        selected = next(
            (score for score in series.scores if score.model_name == series.selected_model), None
        )
        wape = (
            "n/a" if selected is None or selected.wape == float("inf") else f"{selected.wape:.1%}"
        )
        total = sum(point.point for point in series.points)
        rows.append(
            "<tr>"
            f"<td>{html.escape(series.key.sku_id)}</td>"
            f"<td>{html.escape(series.key.location_id)}</td>"
            f"<td>{html.escape(series.selected_model)}</td>"
            f"<td>{wape}</td>"
            f"<td>{total:.2f}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demand forecast report</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;margin:40px;color:#182226;background:#f3f6f4}}
main{{max-width:980px;margin:auto;background:white;padding:32px;border-radius:18px}}
main{{box-shadow:0 10px 35px #18382a18}}
h1{{margin-top:0}}
.meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.card{{background:#edf5ef;padding:14px;border-radius:12px}}
table{{width:100%;border-collapse:collapse;margin-top:24px}}
th,td{{text-align:left;padding:10px;border-bottom:1px solid #d9e3dd}}
small{{color:#56645d}}
</style>
</head>
<body><main>
<h1>Demand forecast report</h1>
<p><small>Traceable planning output; forecasts are estimates,
not replenishment instructions.</small></p>
<section class="meta">
<div class="card"><strong>Run</strong><br>{html.escape(record.id)}</div>
<div class="card"><strong>Horizon</strong><br>{record.batch.horizon} days</div>
<div class="card"><strong>Series</strong><br>{len(record.batch.series)}</div>
</section>
<table><thead><tr><th>SKU</th><th>Location</th><th>Model</th>
<th>WAPE</th><th>Forecast units</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<p><small>Input SHA-256: {record.batch.input_sha256}</small></p>
</main></body></html>"""


def _number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"
