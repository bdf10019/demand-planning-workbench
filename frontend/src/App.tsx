import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Database,
  Download,
  GitCompareArrows,
  Layers3,
  LoaderCircle,
  Play,
  UploadCloud,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { createRun, createScenario, getRun, listRuns } from "./api";
import type {
  ForecastPoint,
  RunDetail,
  RunSummary,
  ScenarioDetail,
  ScenarioOperation,
} from "./types";

interface ChartPoint {
  date: string;
  point: number;
  lower: number;
  upper: number;
  scenario?: number;
}

function App() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [horizon, setHorizon] = useState(14);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scenarioName, setScenarioName] = useState("Upside plan");
  const [operation, setOperation] = useState<ScenarioOperation>("multiplier");
  const [scenarioValue, setScenarioValue] = useState("1.15");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const refreshRuns = async () => {
    const nextRuns = await listRuns();
    setRuns(nextRuns);
    return nextRuns;
  };

  useEffect(() => {
    void refreshRuns().catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Could not load forecast history.");
    });
  }, []);

  useEffect(() => {
    const points = selectedRun?.series[0]?.points;
    if (points?.length) {
      setStartDate(points[0].date);
      setEndDate(points.at(-1)?.date ?? points[0].date);
    }
  }, [selectedRun]);

  const chartPoints = useMemo(
    () => aggregateForecast(selectedRun, scenario),
    [selectedRun, scenario],
  );
  const forecastUnits = chartPoints.reduce((total, point) => total + point.point, 0);
  const selectedScores = selectedRun?.series.flatMap((series) =>
    series.scores.filter((score) => score.model_name === series.selected_model),
  );
  const averageWape = selectedScores?.length
    ? selectedScores.reduce((total, score) => total + (score.wape ?? 0), 0) /
      selectedScores.length
    : null;

  const handleCreateRun = async () => {
    if (!file) {
      setError("Choose a UTF-8 CSV file first.");
      return;
    }
    setLoading(true);
    setError("");
    setScenario(null);
    try {
      const created = await createRun(file, horizon);
      setSelectedRun(created);
      await refreshRuns();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Forecast run failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRun = async (runId: string) => {
    setLoading(true);
    setError("");
    setScenario(null);
    try {
      setSelectedRun(await getRun(runId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the forecast run.");
    } finally {
      setLoading(false);
    }
  };

  const handleScenario = async () => {
    if (!selectedRun || !startDate || !endDate) return;
    const value = Number(scenarioValue);
    if (!Number.isFinite(value) || value < 0) {
      setError("Scenario value must be a non-negative number.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setScenario(
        await createScenario(selectedRun.id, scenarioName, [
          { operation, value, start_date: startDate, end_date: endDate },
        ]),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scenario calculation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Layers3 size={20} /></div>
          <div><strong>Demand</strong><span>Workbench</span></div>
        </div>
        <nav aria-label="Workspace navigation">
          <a className="nav-item active" href="#workspace"><BarChart3 size={18} />Forecast workspace</a>
          <a className="nav-item" href="#scenarios"><GitCompareArrows size={18} />Scenario lab</a>
          <a className="nav-item" href="#runs"><Database size={18} />Run history</a>
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" /> Local workspace
          <small>No cloud account or API key required.</small>
        </div>
      </aside>

      <main className="main-content" id="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">PLANNING CONTROL CENTER</p>
            <h1>Demand forecast workspace</h1>
            <p>Turn daily sales into traceable forecasts and reviewable what-if plans.</p>
          </div>
          <div className="health-pill"><CheckCircle2 size={16} /> Offline ready</div>
        </header>

        {error && <div className="error-banner" role="alert"><AlertTriangle size={18} />{error}</div>}

        <section className="upload-panel panel">
          <div>
            <p className="section-kicker">NEW FORECAST RUN</p>
            <h2>Import a daily sales contract</h2>
            <p>Required columns: date, sku_id, location_id and units.</p>
          </div>
          <label className="file-drop">
            <UploadCloud size={24} />
            <span>{file?.name ?? "Choose UTF-8 CSV"}</span>
            <input
              aria-label="Choose sales CSV"
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <label className="field compact">
            <span>Horizon</span>
            <select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={28}>28 days</option>
            </select>
          </label>
          <button className="primary-button" type="button" onClick={handleCreateRun} disabled={loading}>
            {loading ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
            Run forecast
          </button>
        </section>

        {!selectedRun ? (
          <section className="empty-state panel">
            <div className="empty-icon"><Activity size={28} /></div>
            <h2>No forecast run selected</h2>
            <p>Import the included demo CSV or choose a completed run from the history below.</p>
          </section>
        ) : (
          <>
            <section className="metric-grid" aria-label="Forecast run summary">
              <Metric label="Forecast units" value={formatNumber(forecastUnits)} hint={`${selectedRun.horizon}-day total`} />
              <Metric label="Series planned" value={String(selectedRun.series.length)} hint="SKU × location" />
              <Metric label="Selected-model WAPE" value={averageWape === null ? "n/a" : formatPercent(averageWape)} hint="rolling validation" />
              <Metric label="Rejected rows" value={String(selectedRun.rejected_rows.length)} hint={`${selectedRun.accepted_rows} accepted`} alert={selectedRun.rejected_rows.length > 0} />
            </section>

            <section className="forecast-grid">
              <article className="panel chart-panel">
                <div className="panel-heading">
                  <div><p className="section-kicker">BASELINE + SCENARIO</p><h2>Aggregate forecast</h2></div>
                  <a className="secondary-button" href={`/api/runs/${selectedRun.id}/forecast.csv`}><Download size={16} />CSV</a>
                </div>
                <ForecastChart points={chartPoints} />
                <div className="chart-legend"><span><i className="base-line" />Baseline</span><span><i className="range-box" />Prediction range</span>{scenario && <span><i className="scenario-line" />Scenario</span>}</div>
              </article>

              <article className="panel scenario-panel" id="scenarios">
                <div className="panel-heading"><div><p className="section-kicker">WHAT-IF CONTROLS</p><h2>Scenario lab</h2></div><GitCompareArrows size={22} /></div>
                <label className="field"><span>Scenario name</span><input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} /></label>
                <div className="split-fields">
                  <label className="field"><span>Operation</span><select value={operation} onChange={(event) => setOperation(event.target.value as ScenarioOperation)}><option value="multiplier">Multiplier</option><option value="additive">Add units</option><option value="override">Override units</option></select></label>
                  <label className="field"><span>Value</span><input type="number" min="0" step="0.05" value={scenarioValue} onChange={(event) => setScenarioValue(event.target.value)} /></label>
                </div>
                <div className="split-fields">
                  <label className="field"><span>From</span><input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
                  <label className="field"><span>To</span><input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
                </div>
                <button className="primary-button full" type="button" onClick={handleScenario} disabled={loading}>Compare scenario</button>
                {scenario && <div className="scenario-result"><span>Planned delta</span><strong className={scenario.delta_units >= 0 ? "positive" : "negative"}>{signedNumber(scenario.delta_units)} units</strong><small>{formatPercent(scenario.delta_units / Math.max(scenario.base_units, 1))} vs baseline</small><a href={`/api/scenarios/${scenario.id}/forecast.csv`}>Download scenario CSV <ChevronRight size={14} /></a></div>}
              </article>
            </section>

            <section className="panel performance-panel">
              <div className="panel-heading"><div><p className="section-kicker">MODEL GOVERNANCE</p><h2>Selected model evidence</h2></div><span className="hash">Input {selectedRun.input_sha256.slice(0, 12)}…</span></div>
              <div className="table-wrap"><table><thead><tr><th>Series</th><th>Selected model</th><th>WAPE</th><th>MASE</th><th>Bias</th><th>Folds</th></tr></thead><tbody>{selectedRun.series.map((series) => { const score = series.scores.find((item) => item.model_name === series.selected_model); return <tr key={`${series.sku_id}-${series.location_id}`}><td><strong>{series.sku_id}</strong><small>{series.location_id}</small></td><td><span className="model-chip">{series.selected_model}</span></td><td>{formatMetric(score?.wape)}</td><td>{formatMetric(score?.mase)}</td><td>{formatMetric(score?.bias)}</td><td>{score?.folds ?? 0}</td></tr>; })}</tbody></table></div>
            </section>
          </>
        )}

        <section className="panel history-panel" id="runs">
          <div className="panel-heading"><div><p className="section-kicker">AUDIT TRAIL</p><h2>Forecast run history</h2></div><span>{runs.length} retained locally</span></div>
          {runs.length === 0 ? <p className="muted">No forecast runs yet.</p> : <div className="run-list">{runs.map((run) => <button type="button" key={run.id} className={`run-row ${selectedRun?.id === run.id ? "selected" : ""}`} onClick={() => handleSelectRun(run.id)}><span className="run-status"><CheckCircle2 size={17} /></span><span><strong>{run.source_name}</strong><small>{new Date(run.created_at).toLocaleString()}</small></span><span><strong>{run.series_count}</strong><small>series</small></span><span><strong>{run.horizon}</strong><small>days</small></span><code>{run.input_sha256.slice(0, 8)}</code><ChevronRight size={18} /></button>)}</div>}
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value, hint, alert = false }: { label: string; value: string; hint: string; alert?: boolean }) {
  return <article className={`metric-card ${alert ? "alert" : ""}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>;
}

function ForecastChart({ points }: { points: ChartPoint[] }) {
  if (!points.length) return <div className="chart-empty">No forecast points.</div>;
  const width = 760;
  const height = 260;
  const inset = 24;
  const maximum = Math.max(...points.flatMap((point) => [point.upper, point.scenario ?? 0]), 1);
  const x = (index: number) => inset + (index / Math.max(points.length - 1, 1)) * (width - inset * 2);
  const y = (value: number) => height - inset - (value / maximum) * (height - inset * 2);
  const baseLine = points.map((point, index) => `${x(index)},${y(point.point)}`).join(" ");
  const range = [...points.map((point, index) => `${x(index)},${y(point.upper)}`), ...[...points].reverse().map((point, reverseIndex) => `${x(points.length - reverseIndex - 1)},${y(point.lower)}`)].join(" ");
  const scenarioLine = points.map((point, index) => `${x(index)},${y(point.scenario ?? point.point)}`).join(" ");
  return <div className="chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Aggregate demand forecast chart"><line x1={inset} y1={height - inset} x2={width - inset} y2={height - inset} className="axis" /><polygon points={range} className="range-area" /><polyline points={baseLine} className="forecast-line" />{points.some((point) => point.scenario !== undefined) && <polyline points={scenarioLine} className="scenario-polyline" />}</svg><div className="chart-dates"><span>{formatDate(points[0].date)}</span><span>{formatDate(points.at(-1)?.date ?? points[0].date)}</span></div></div>;
}

function aggregateForecast(run: RunDetail | null, scenario: ScenarioDetail | null): ChartPoint[] {
  if (!run) return [];
  const totals = new Map<string, ChartPoint>();
  for (const series of run.series) for (const point of series.points) {
    const current = totals.get(point.date) ?? { date: point.date, point: 0, lower: 0, upper: 0 };
    current.point += point.point;
    current.lower += point.lower;
    current.upper += point.upper;
    totals.set(point.date, current);
  }
  if (scenario) for (const series of scenario.series) for (const point of series.points) {
    const current = totals.get(point.date);
    if (current) current.scenario = (current.scenario ?? 0) + point.scenario;
  }
  return [...totals.values()].sort((left, right) => left.date.localeCompare(right.date));
}

function formatNumber(value: number): string { return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value); }
function signedNumber(value: number): string { return `${value >= 0 ? "+" : ""}${formatNumber(value)}`; }
function formatPercent(value: number): string { return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 }).format(value); }
function formatMetric(value: number | null | undefined): string { return value === null || value === undefined ? "n/a" : value.toFixed(3); }
function formatDate(value: string): string { return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`)); }

export default App;
