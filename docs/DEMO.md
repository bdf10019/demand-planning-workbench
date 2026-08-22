# Demonstration guide

## CLI path

1. Run `scripts/run-demo.ps1`.
2. Confirm that `outputs/demo/manifest.json` reports three files.
3. Open `outputs/demo/report.html`.
4. Run `python -m demand_workbench verify-output outputs/demo`.
5. Modify a generated CSV copy and show that verification reports a hash mismatch.

## Web path

1. Start the API with `python -m demand_workbench serve`.
2. Start the UI with `pnpm --dir frontend dev`.
3. Open `http://127.0.0.1:5173` and upload `examples/sales.csv`.
4. Explain that model evidence is selected separately for each SKU/location series.
5. Create a multiplier scenario over the forecast window and compare the orange line with baseline.
6. Download baseline and scenario CSV files.
7. Select an older run from the local audit history.

## What to emphasize

- The product is more than a forecasting function: it includes input rejection, model governance,
  persistence, scenario versioning, reports, API, UI and operational checks.
- The public-data result is intentionally reported even though accuracy is not production-ready.
- Every environment boundary is explicit: local-only API, ignored data, no credentials and no causal
  interpretation of planner overrides.
