import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OffenseRow } from "@/components/offenses/OffenseRow";
import { OffenseEmptyState } from "@/components/offenses/OffenseEmptyState";
import { IncidentRow } from "@/components/incidents/IncidentRow";
import { IncidentEmptyState } from "@/components/incidents/IncidentEmptyState";
import type { OffenseSummary } from "@/lib/types/offense";
import type { IncidentSummary } from "@/lib/types/incident";

function makeOffense(overrides: Partial<OffenseSummary> = {}): OffenseSummary {
  return {
    id: "offense-1",
    offense_number: 1042,
    host_id: "host-1",
    host_name: "server-03",
    title: "Possible Account Compromise",
    description: null,
    risk_level: "critical",
    status: "open",
    event_count: 18,
    alert_count: 3,
    incident_id: null,
    related_hosts: [],
    related_users: [],
    created_at: new Date(Date.now() - 120_000).toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeIncident(overrides: Partial<IncidentSummary> = {}): IncidentSummary {
  return {
    id: "incident-1",
    title: "Critical Security Incident",
    description: "Unauthorized access detected",
    severity: "high",
    status: "investigating",
    host_id: null,
    assigned_to: null,
    created_at: new Date(Date.now() - 3600_000).toISOString(),
    resolved_at: null,
    ...overrides,
  };
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("OffenseRow", () => {
  it("renders offense number, title, host, counts", () => {
    const o = makeOffense();
    wrap(<OffenseRow offense={o} selected={false} onClick={() => {}} />);
    expect(screen.getByText("#1042")).toBeTruthy();
    expect(screen.getByText("Possible Account Compromise")).toBeTruthy();
    expect(screen.getByText("server-03")).toBeTruthy();
    expect(screen.getByText(/3 alerts/)).toBeTruthy();
    expect(screen.getByText(/18 events/)).toBeTruthy();
  });

  it("applies selected style when selected", () => {
    const o = makeOffense();
    const { container } = wrap(<OffenseRow offense={o} selected={true} onClick={() => {}} />);
    const btn = container.querySelector("button");
    expect(btn?.className).toContain("border-accent");
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const o = makeOffense();
    wrap(<OffenseRow offense={o} selected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText("Possible Account Compromise"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("shows Case badge when incident_id is set", () => {
    const o = makeOffense({ incident_id: "inc-1" });
    wrap(<OffenseRow offense={o} selected={false} onClick={() => {}} />);
    expect(screen.getByText("Case")).toBeTruthy();
  });
});

describe("OffenseEmptyState", () => {
  it("shows no offenses message when no filters", () => {
    wrap(<OffenseEmptyState hasFilters={false} onClear={() => {}} />);
    expect(screen.getByText("No offenses")).toBeTruthy();
  });

  it("shows no matching message when filters active", () => {
    wrap(<OffenseEmptyState hasFilters={true} onClear={() => {}} />);
    expect(screen.getByText("No matching offenses")).toBeTruthy();
  });
});

describe("IncidentRow", () => {
  it("renders title, severity, status", () => {
    const i = makeIncident();
    wrap(<IncidentRow incident={i} selected={false} onClick={() => {}} />);
    expect(screen.getByText("Critical Security Incident")).toBeTruthy();
  });

  it("renders description when present", () => {
    const i = makeIncident({ description: "Unauthorized access detected" });
    wrap(<IncidentRow incident={i} selected={false} onClick={() => {}} />);
    expect(screen.getByText("Unauthorized access detected")).toBeTruthy();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const i = makeIncident();
    wrap(<IncidentRow incident={i} selected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText("Critical Security Incident"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies selected style when selected", () => {
    const i = makeIncident();
    const { container } = wrap(<IncidentRow incident={i} selected={true} onClick={() => {}} />);
    const btn = container.querySelector("button");
    expect(btn?.className).toContain("border-accent");
  });
});

describe("IncidentEmptyState", () => {
  it("shows no incidents when no filters", () => {
    wrap(<IncidentEmptyState hasFilters={false} onClear={() => {}} />);
    expect(screen.getByText("No incidents")).toBeTruthy();
  });

  it("shows no matching when filters active", () => {
    wrap(<IncidentEmptyState hasFilters={true} onClear={() => {}} />);
    expect(screen.getByText("No matching incidents")).toBeTruthy();
  });
});

describe("Offense types", () => {
  it("has correct status transitions", async () => {
    const { OFFENSE_STATUSES } = await import("@/lib/types/offense");
    expect(OFFENSE_STATUSES).toEqual(["open", "investigating", "resolved"]);
  });

  it("has correct risk levels", async () => {
    const { OFFENSE_RISK_LEVELS } = await import("@/lib/types/offense");
    expect(OFFENSE_RISK_LEVELS).toEqual(["critical", "high", "medium", "low"]);
  });
});

describe("Incident types", () => {
  it("has correct statuses", async () => {
    const { INCIDENT_STATUSES } = await import("@/lib/types/incident");
    expect(INCIDENT_STATUSES).toEqual(["open", "investigating", "resolved", "closed"]);
  });

  it("has correct status transitions", async () => {
    const { INCIDENT_STATUS_TRANSITIONS } = await import("@/lib/types/incident");
    expect(INCIDENT_STATUS_TRANSITIONS.investigating).toContain("resolved");
    expect(INCIDENT_STATUS_TRANSITIONS.investigating).toContain("closed");
    expect(INCIDENT_STATUS_TRANSITIONS.closed).toEqual(["open"]);
  });

  it("has correct severities", async () => {
    const { INCIDENT_SEVERITIES } = await import("@/lib/types/incident");
    expect(INCIDENT_SEVERITIES).toEqual(["critical", "high", "medium", "low"]);
  });
});
