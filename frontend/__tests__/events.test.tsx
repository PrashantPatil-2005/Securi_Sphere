import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EventRow } from "@/components/events/EventRow";
import { EventEmptyState } from "@/components/events/EventEmptyState";
import { EventRawJson } from "@/components/events/EventRawJson";
import { EventMetadata } from "@/components/events/EventMetadata";
import { EventRelatedObjects } from "@/components/events/EventRelatedObjects";
import type { EventSummary } from "@/lib/types/event";

function makeEvent(overrides: Partial<EventSummary> = {}): EventSummary {
  return {
    id: "evt-1",
    host_id: "host-abc-123",
    event_type: "ssh_login_failure",
    severity: "high",
    description: "Failed SSH authentication from 10.0.0.42",
    source: "sshd",
    raw_log: '{"message":"Failed password for root from 10.0.0.42 port 22 ssh2","program":"sshd"}',
    timestamp: new Date(Date.now() - 60_000).toISOString(),
    ...overrides,
  };
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("EventRow", () => {
  it("renders event type, severity, description, and timestamp", () => {
    const e = makeEvent();
    wrap(<EventRow event={e} selected={false} onClick={() => {}} />);
    expect(screen.getByText("ssh_login_failure")).toBeTruthy();
    expect(screen.getByText("Failed SSH authentication from 10.0.0.42")).toBeTruthy();
    expect(screen.getByText("sshd")).toBeTruthy();
  });

  it("renders host ID (truncated)", () => {
    const e = makeEvent({ host_id: "host-abc-123-def-456" });
    wrap(<EventRow event={e} selected={false} onClick={() => {}} />);
    expect(screen.getByText("host-abc")).toBeTruthy();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const e = makeEvent();
    wrap(<EventRow event={e} selected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText("ssh_login_failure"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies selected style when selected", () => {
    const e = makeEvent();
    const { container } = wrap(<EventRow event={e} selected={true} onClick={() => {}} />);
    const btn = container.querySelector("button");
    expect(btn?.className).toContain("border-l-accent");
  });

  it("renders without description when null", () => {
    const e = makeEvent({ description: null });
    wrap(<EventRow event={e} selected={false} onClick={() => {}} />);
    expect(screen.getByText("ssh_login_failure")).toBeTruthy();
    expect(screen.queryByText("Failed SSH")).toBeNull();
  });

  it("renders source badge when present", () => {
    const e = makeEvent({ source: "sshd" });
    wrap(<EventRow event={e} selected={false} onClick={() => {}} />);
    expect(screen.getByText("sshd")).toBeTruthy();
  });
});

describe("EventEmptyState", () => {
  it("shows no events message when no filters", () => {
    wrap(<EventEmptyState hasFilters={false} onClear={() => {}} />);
    expect(screen.getByText("No events")).toBeTruthy();
  });

  it("shows no matching message when filters active", () => {
    wrap(<EventEmptyState hasFilters={true} onClear={() => {}} />);
    expect(screen.getByText("No matching events")).toBeTruthy();
  });

  it("calls onClear when clear button clicked", () => {
    const onClear = vi.fn();
    wrap(<EventEmptyState hasFilters={true} onClear={onClear} />);
    fireEvent.click(screen.getByText("Clear filters"));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});

describe("EventRawJson", () => {
  it("renders raw log when valid JSON", () => {
    const raw = '{"key": "value", "count": 42}';
    wrap(<EventRawJson data={raw} />);
    expect(screen.getByText("root")).toBeTruthy();
    expect(screen.getByText("key")).toBeTruthy();
  });

  it("renders raw log as plain text when invalid JSON", () => {
    wrap(<EventRawJson data="not json at all" />);
    expect(screen.getByText("not json at all")).toBeTruthy();
  });

  it("renders null message when data is null", () => {
    wrap(<EventRawJson data={null} />);
    expect(screen.getByText("No raw log available")).toBeTruthy();
  });

  it("shows copy button", () => {
    wrap(<EventRawJson data='{"a":1}' />);
    expect(screen.getByText("Copy")).toBeTruthy();
  });

  it("renders nested JSON objects", () => {
    const raw = '{"outer": {"inner": "deep"}}';
    wrap(<EventRawJson data={raw} />);
    expect(screen.getByText("outer")).toBeTruthy();
    expect(screen.getByText("inner")).toBeTruthy();
    expect(screen.getByText("deep")).toBeTruthy();
  });
});

describe("EventMetadata", () => {
  it("renders event type, severity, timestamp, host ID, event ID", () => {
    const e = makeEvent();
    wrap(<EventMetadata event={e} />);
    expect(screen.getByText("ssh_login_failure")).toBeTruthy();
    expect(screen.getByText("high", { exact: false })).toBeTruthy();
    expect(screen.getByText("Event Details")).toBeTruthy();
    expect(screen.getByText("host-abc-123")).toBeTruthy();
    expect(screen.getByText("evt-1")).toBeTruthy();
  });

  it("renders source when present", () => {
    const e = makeEvent({ source: "sshd" });
    wrap(<EventMetadata event={e} />);
    expect(screen.getByText("sshd")).toBeTruthy();
  });

  it("renders description when present", () => {
    const e = makeEvent({ description: "Failed SSH auth" });
    wrap(<EventMetadata event={e} />);
    expect(screen.getByText("Failed SSH auth")).toBeTruthy();
  });
});

describe("EventRelatedObjects", () => {
  it("shows empty message when no related objects", () => {
    wrap(<EventRelatedObjects />);
    expect(screen.getByText("No related security objects found for this event.")).toBeTruthy();
  });

  it("renders related alerts", () => {
    const alerts = [
      { id: "alert-1", title: "Multiple SSH Failures", severity: "high", status: "open" },
    ];
    wrap(<EventRelatedObjects alerts={alerts} />);
    expect(screen.getByText("Related Alerts (1)")).toBeTruthy();
    expect(screen.getByText("Multiple SSH Failures")).toBeTruthy();
  });

  it("renders related offenses", () => {
    const offenses = [
      { id: "off-1", offense_number: 1042, title: "Account Compromise", risk_level: "critical", status: "open" },
    ];
    wrap(<EventRelatedObjects offenses={offenses} />);
    expect(screen.getByText("Related Offenses (1)")).toBeTruthy();
    expect(screen.getByText("#1042 — Account Compromise")).toBeTruthy();
  });

  it("renders related incidents", () => {
    const incidents = [
      { id: "inc-1", title: "Security Incident", severity: "high", status: "investigating" },
    ];
    wrap(<EventRelatedObjects incidents={incidents} />);
    expect(screen.getByText("Related Incidents (1)")).toBeTruthy();
    expect(screen.getByText("Security Incident")).toBeTruthy();
  });
});

describe("Event types", () => {
  it("has correct severity constants", async () => {
    const { EVENT_SEVERITIES } = await import("@/lib/types/event");
    expect(EVENT_SEVERITIES).toEqual(["critical", "high", "medium", "low", "info"]);
  });

  it("has correct sort options", async () => {
    const { EVENT_SORT_OPTIONS } = await import("@/lib/types/event");
    expect(EVENT_SORT_OPTIONS).toHaveLength(3);
    expect(EVENT_SORT_OPTIONS[0].value).toBe("newest");
  });

  it("has correct default filters", async () => {
    const { DEFAULT_EVENT_FILTERS } = await import("@/lib/types/event");
    expect(DEFAULT_EVENT_FILTERS.severity).toBe("");
    expect(DEFAULT_EVENT_FILTERS.event_type).toBe("");
    expect(DEFAULT_EVENT_FILTERS.host_id).toBe("");
    expect(DEFAULT_EVENT_FILTERS.q).toBe("");
  });

  it("eventHasActiveFilters returns false for defaults", async () => {
    const { eventHasActiveFilters, DEFAULT_EVENT_FILTERS } = await import("@/lib/types/event");
    expect(eventHasActiveFilters(DEFAULT_EVENT_FILTERS)).toBe(false);
  });

  it("eventHasActiveFilters returns true when filter set", async () => {
    const { eventHasActiveFilters, DEFAULT_EVENT_FILTERS } = await import("@/lib/types/event");
    expect(eventHasActiveFilters({ ...DEFAULT_EVENT_FILTERS, severity: "high" })).toBe(true);
  });

  it("eventActiveFilterCount counts active filters", async () => {
    const { eventActiveFilterCount, DEFAULT_EVENT_FILTERS } = await import("@/lib/types/event");
    expect(eventActiveFilterCount(DEFAULT_EVENT_FILTERS)).toBe(0);
    expect(eventActiveFilterCount({ ...DEFAULT_EVENT_FILTERS, severity: "high", host_id: "h1" })).toBe(2);
  });
});
