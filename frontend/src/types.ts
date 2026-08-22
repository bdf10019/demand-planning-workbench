export interface RunSummary {
  id: string;
  created_at: string;
  source_name: string;
  input_sha256: string;
  horizon: number;
  accepted_rows: number;
  rejected_rows: number;
  series_count: number;
  status: "completed";
}
export interface ModelScore {
  model_name: string;
  wape: number | null;
  mase: number | null;
  bias: number | null;
  folds: number;
}

export interface ForecastPoint {
  date: string;
  point: number;
  lower: number;
  upper: number;
}

export interface ForecastSeries {
  sku_id: string;
  location_id: string;
  selected_model: string;
  warnings: string[];
  scores: ModelScore[];
  points: ForecastPoint[];
}

export interface RunDetail {
  id: string;
  created_at: string;
  source_name: string;
  input_sha256: string;
  horizon: number;
  accepted_rows: number;
  rejected_rows: Array<{ row_number: number; reason: string }>;
  warnings: string[];
  series: ForecastSeries[];
}

export type ScenarioOperation = "multiplier" | "additive" | "override";

export interface ScenarioRulePayload {
  operation: ScenarioOperation;
  value: number;
  start_date: string;
  end_date: string;
  sku_id?: string;
  location_id?: string;
}

export interface ScenarioPoint {
  date: string;
  base: number;
  scenario: number;
  delta: number;
}

export interface ScenarioDetail {
  id: string;
  run_id: string;
  created_at: string;
  name: string;
  base_units: number;
  scenario_units: number;
  delta_units: number;
  rules: ScenarioRulePayload[];
  series: Array<{
    sku_id: string;
    location_id: string;
    points: ScenarioPoint[];
  }>;
}
