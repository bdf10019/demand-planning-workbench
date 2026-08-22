# Architecture

## Design goals

1. Forecast logic must run without a web server, database or network connection.
2. Every persisted result must identify its input hash, selected model and validation evidence.
3. A failed row must not silently disappear, and a scenario must not mutate its baseline run.
4. The local demonstration must remain useful without cloud services, credentials or paid APIs.

## Component boundaries

| Component | Responsibility | Does not own |
|---|---|---|
| `ingest.py` | CSV contract, row rejection, duplicate aggregation, daily normalization | Model training or persistence |
| `models.py` | Forecast plugin protocol and explainable baseline models | Cross-validation or model selection |
| `metrics.py` | WAPE, MASE, Bias and residual quantile | Business-series orchestration |
| `backtesting.py` | Chronological folds, per-series selection and forecast intervals | API or SQL |
| `scenarios.py` | Ordered deterministic overlays and delta calculation | Causal claims |
| `database.py` | Transactional SQLite audit store and reconstruction | Forecast computation |
| `service.py` | One application workflow shared by all entry points | HTTP or presentation formatting |
| `api.py` / `cli.py` | Input limits, transport errors and local operations | Duplicate domain rules |
| `reporting.py` | CSV, JSON, HTML and SHA-256 manifest | Model decisions |
| `frontend/` | Planner interaction, visualization and exports | Authoritative calculation |

## Forecast workflow

Each `sku_id + location_id` series is evaluated independently. Validation folds always precede their
test windows; future observations never enter a training fold. Candidate scores are retained even when
they lose. Selection minimizes finite WAPE, then absolute Bias, then model name for deterministic ties.

When validation actuals are all zero, WAPE is deliberately non-finite instead of being reported as a
misleading zero. JSON surfaces serialize the value as `null`; SQLite reconstructs it as a non-finite
domain metric. A short series still receives a forecast, but warnings identify the missing evidence.

## SQLite schema

- `forecast_runs`: immutable run header, source basename, SHA-256, horizon and row counts.
- `series_forecasts`: selected model, all model scores and per-series warnings.
- `forecast_points`: baseline point and interval by series/date.
- `scenarios`: immutable rule set and aggregate deltas linked to one baseline run.
- `scenario_points`: baseline and adjusted value by series/date.

Writes for one run or scenario occur inside a single SQLite transaction. Foreign keys and composite
primary keys prevent orphaned or duplicate points. Runtime databases live under ignored `outputs/`.

## Deployment boundary

The CLI restricts the API server to `127.0.0.1`, `localhost` or `::1`. CORS only permits the local Vite
origins. This is a deliberate single-user portfolio boundary, not an authentication system. A production
deployment would replace SQLite with PostgreSQL, add migrations and background jobs, and enforce OIDC
claims plus tenant-aware authorization.
