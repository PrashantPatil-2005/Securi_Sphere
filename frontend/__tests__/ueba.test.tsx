import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { UebaAnomalyList } from "@/components/ueba/UebaAnomalyList";
import { UebaSummaryCards } from "@/components/ueba/UebaSummaryCards";
import { uebaMetricLabel, uebaSeverityWeight, DEFAULT_UEBA_FILTERS } from "@/lib/types/ueba";
import type { UebaAnomaly, UebaSummary } from "@/lib/types/ueba";

function makeAnomaly(overrides: Partial<UebaAnomaly> = {}): UebaAnomaly {
  return {
    id: "anom-1",
    entity_type: "host",
    entity_key: "srv-01",
    entity_label: "srv-01",
    metric: "failed_logins",
    observed_value: 47,
    baseline_mean: 3.2,
    baseline_stddev: 1.1,
    z_score: 12.5,
    severity: "critical",
    status: "open",
    description: "Failed login count 14.7x above baseline",
    context: {},
    alert_id: "alert-1",
    detected_at: new Date(Date.now() - 100_000).toISOString(),
    resolved_at: null,
    ...overrides,
  };
}

function makeSummary(overrides: Partial<UebaSummary> = {}): UebaSummary {
  return {
    open_count: 5,
    by_severity: { critical: 1, high: 2, medium: 2, low: 0 },
    enabled: true,
    z_threshold: 3.0,
    baseline_days: 30,
    ...overrides,
  };
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("uebaMetricLabel", () => {
  it("formats snake_case to Title Case", () => {
    expect(uebaMetricLabel("failed_logins")).toBe("Failed Logins");
    expect(uebaMetricLabel("auth_events")).toBe("Auth Events");
    expect(uebaMetricLabel("events_total")).toBe("Events Total");
  });
});

describe("uebaSeverityWeight", () => {
  it("returns correct weights", () => {
    expect(uebaSeverityWeight("critical")).toBe(4);
    expect(uebaSeverityWeight("high")).toBe(3);
    expect(uebaSeverityWeight("medium")).toBe(2);
    expect(uebaSeverityWeight("low")).toBe(1);
    expect(uebaSeverityWeight("unknown")).toBe(0);
  });
});

describe("DEFAULT_UEBA_FILTERS", () => {
  it("has open as default status", () => {
    expect(DEFAULT_UEBA_FILTERS.status).toBe("open");
    expect(DEFAULT_UEBA_FILTERS.severity).toBe("");
    expect(DEFAULT_UEBA_FILTERS.entity_type).toBe("");
  });
});

describe("UebaAnomalyList", () => {
  it("renders anomaly entity label", () => {
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("srv-01")).toBeTruthy();
  });

  it("renders severity badge", () => {
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("Critical")).toBeTruthy();
  });

  it("renders metric label", () => {
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText(/Failed Logins/)).toBeTruthy();
  });

  it("renders z-score and baseline", () => {
    const a = makeAnomaly({ z_score: 12.5, baseline_mean: 3.2 });
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText(/z=12\.5/)).toBeTruthy();
    expect(screen.getByText(/baseline μ=3\.2/)).toBeTruthy();
  });

  it("renders description", () => {
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("Failed login count 14.7x above baseline")).toBeTruthy();
  });

  it("renders entity type", () => {
    const a = makeAnomaly({ entity_type: "host" });
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("host")).toBeTruthy();
  });

  it("shows alert link when alert_id present", () => {
    const a = makeAnomaly({ alert_id: "alert-1" });
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    const link = screen.getByText("Alert");
    expect(link.closest("a")?.getAttribute("href")).toBe("/alerts/alert-1");
  });

  it("shows host link for host entity", () => {
    const a = makeAnomaly({ entity_type: "host", entity_key: "srv-01" });
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    const link = screen.getByText("Host");
    expect(link.closest("a")?.getAttribute("href")).toBe("/hosts/srv-01");
  });

  it("calls onDismiss when dismiss clicked", () => {
    const onDismiss = vi.fn();
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={onDismiss}
        onResolve={() => {}}
      />,
    );
    fireEvent.click(screen.getByText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith("anom-1");
  });

  it("calls onResolve when resolve clicked", () => {
    const onResolve = vi.fn();
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={onResolve}
      />,
    );
    fireEvent.click(screen.getByText("Resolve"));
    expect(onResolve).toHaveBeenCalledWith("anom-1");
  });

  it("shows anomaly count in header", () => {
    const a1 = makeAnomaly({ id: "a1" });
    const a2 = makeAnomaly({ id: "a2" });
    wrap(
      <UebaAnomalyList
        anomalies={[a1, a2]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("2 anomalies")).toBeTruthy();
  });

  it("shows singular for 1 anomaly", () => {
    const a = makeAnomaly();
    wrap(
      <UebaAnomalyList
        anomalies={[a]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("1 anomaly")).toBeTruthy();
  });

  it("shows empty state when no anomalies", () => {
    wrap(
      <UebaAnomalyList
        anomalies={[]}
        isLoading={false}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(screen.getByText("No anomalies")).toBeTruthy();
  });

  it("shows loading skeletons", () => {
    const { container } = wrap(
      <UebaAnomalyList
        anomalies={[]}
        isLoading={true}
        onDismiss={() => {}}
        onResolve={() => {}}
      />,
    );
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });
});

describe("UebaSummaryCards", () => {
  it("renders open count", () => {
    vi.useFakeTimers();
    try {
      const s = makeSummary();
      wrap(<UebaSummaryCards summary={s} isLoading={false} />);
      act(() => {
        vi.advanceTimersByTime(2_000);
      });
      expect(screen.getByText("5")).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it("renders severity counts", () => {
    vi.useFakeTimers();
    try {
      const s = makeSummary();
      wrap(<UebaSummaryCards summary={s} isLoading={false} />);
      act(() => {
        vi.advanceTimersByTime(2_000);
      });
      expect(screen.getByText("1")).toBeTruthy(); // critical
      expect(screen.getAllByText("2").length).toBe(2); // high and medium both = 2
    } finally {
      vi.useRealTimers();
    }
  });

  it("renders all four summary cards", () => {
    const s = makeSummary();
    wrap(<UebaSummaryCards summary={s} isLoading={false} />);
    expect(screen.getByText("Open anomalies")).toBeTruthy();
    expect(screen.getByText("Critical")).toBeTruthy();
    expect(screen.getByText("High")).toBeTruthy();
    expect(screen.getByText("Medium")).toBeTruthy();
  });

  it("shows loading skeletons", () => {
    const { container } = wrap(<UebaSummaryCards summary={undefined} isLoading={true} />);
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });

  it("renders nothing when no summary and not loading", () => {
    const { container } = wrap(<UebaSummaryCards summary={undefined} isLoading={false} />);
    expect(container.querySelector("[class*='grid']")).toBeNull();
  });
});
