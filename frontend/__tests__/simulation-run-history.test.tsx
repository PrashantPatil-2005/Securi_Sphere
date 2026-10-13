import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  api: vi.fn(async (url: string) => {
    if (url.startsWith("/api/v1/simulation/runs")) {
      return {
        items: [
          {
            id: "run-1",
            run_id: "run-1",
            scenario_id: "brute_force_only",
            name: "Brute Force Attempt",
            host_id: "h1",
            host_name: "web-01",
            event_count: 10,
            alert_count: 1,
            offense_count: 1,
            created_at: "2026-01-01T00:00:00Z",
          },
          {
            id: "run-2",
            run_id: "run-2",
            scenario_id: "custom",
            name: "Custom chain",
            host_id: "h1",
            host_name: "web-01",
            event_count: 2,
            alert_count: 0,
            offense_count: 0,
            created_at: "2026-01-01T00:05:00Z",
          },
        ],
        total: 2,
      };
    }
    throw new Error(`unexpected url ${url}`);
  }),
}));

import { SimulationRunHistory } from "@/components/attack-lab/SimulationRunHistory";

function setup(overrides: Partial<Parameters<typeof SimulationRunHistory>[0]> = {}) {
  const props = {
    selectedRunId: null,
    onSelect: vi.fn(),
    onReplay: vi.fn(),
    onReset: vi.fn(),
    showPurge: true,
    onPurge: vi.fn(),
    purgePending: false,
    ...overrides,
  };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <SimulationRunHistory {...props} />
    </QueryClientProvider>,
  );
  return props;
}

describe("SimulationRunHistory", () => {
  it("renders a Replay action for presets and omits it for custom runs", async () => {
    setup();
    await waitFor(() => screen.getByText("Brute Force Attempt"));
    // Two rows: the preset row offers Replay+Reset, the custom row only Reset.
    expect(screen.getAllByRole("button", { name: /replay/i })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /reset/i })).toHaveLength(2);
  });

  it("invokes per-run callbacks without selecting the row", async () => {
    const props = setup();
    await waitFor(() => screen.getByText("Brute Force Attempt"));

    screen.getAllByRole("button", { name: /replay/i })[0].click();
    expect(props.onReplay).toHaveBeenCalledWith("run-1");
    expect(props.onSelect).not.toHaveBeenCalled();

    screen.getAllByRole("button", { name: /reset/i })[0].click();
    expect(props.onReset).toHaveBeenCalledWith("run-1");
  });

  it("shows the global purge action only when history has runs", async () => {
    const props = setup({ showPurge: true });
    await waitFor(() => screen.getByText("Brute Force Attempt"));
    screen.getByRole("button", { name: /purge all simulated data/i }).click();
    expect(props.onPurge).toHaveBeenCalledTimes(1);
  });
});
