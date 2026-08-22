import type {
  RunDetail,
  RunSummary,
  ScenarioDetail,
  ScenarioRulePayload,
} from "./types";

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the status-based fallback when the server did not return JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
export async function listRuns(): Promise<RunSummary[]> {
  return expectJson<RunSummary[]>(await fetch("/api/runs"));
}

export async function getRun(runId: string): Promise<RunDetail> {
  return expectJson<RunDetail>(await fetch(`/api/runs/${encodeURIComponent(runId)}`));
}

export async function createRun(file: File, horizon: number): Promise<RunDetail> {
  const params = new URLSearchParams({ horizon: String(horizon), source_name: file.name });
  return expectJson<RunDetail>(
    await fetch(`/api/runs/csv?${params.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      body: await file.text(),
    }),
  );
}

export async function createScenario(
  runId: string,
  name: string,
  rules: ScenarioRulePayload[],
): Promise<ScenarioDetail> {
  return expectJson<ScenarioDetail>(
    await fetch(`/api/runs/${encodeURIComponent(runId)}/scenarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, rules }),
    }),
  );
}
