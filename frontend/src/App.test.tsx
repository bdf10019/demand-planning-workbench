import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Demand Planning Workbench", () => {
  it("renders the offline workspace and empty history", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => [] } as Response),
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: "Demand forecast workspace" })).toBeVisible();
    expect(await screen.findByText("No forecast runs yet.")).toBeVisible();
    expect(screen.getByText("No cloud account or API key required.")).toBeVisible();
  });

  it("shows an actionable message when no CSV is selected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => [] } as Response),
    );
    render(<App />);

    screen.getByRole("button", { name: "Run forecast" }).click();

    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a UTF-8 CSV file first.");
  });
});
