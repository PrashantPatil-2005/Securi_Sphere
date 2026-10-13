import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvestigationWorkspacePane } from "@/components/investigation/InvestigationWorkspacePane";
import { ApiError } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/assistant/AssistantProvider", () => ({
  useAssistant: () => ({ openWithContext: vi.fn() }),
}));
vi.mock("@/components/ui/Toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock("@/components/IocLookupPanel", () => ({ IocLookupPanel: () => null }));
vi.mock("@/lib/hooks/useUser", () => ({
  useUser: () => ({
    data: {
      id: "user-1",
      email: "analyst@test.local",
      full_name: null,
      role: { id: "r1", name: "analyst", description: null, permissions: {} },
    },
  }),
}));

const apiMock = vi.fn();
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: (...args: unknown[]) => apiMock(...args) };
});

const WORKSPACE_OK = {
  anchor: { type: "incident", id: "inc-1" },
  alert: null,
  offense: {
    id: "off-1",
    offense_number: 1392,
    host_id: "host-1",
    host_name: "test_kali",
    title: "Security activity: root_login",
    description: "Correlated activity",
    risk_level: "high",
    status: "investigating",
    event_count: 2,
    alert_count: 1,
    incident_id: "inc-1",
    timeline: [],
    related_users: [],
    alerts: [],
    events: [],
  },
  incident: {
    id: "inc-1",
    title: "Offense #1392: Security activity: root_login",
    description: "desc",
    severity: "high",
    status: "investigating",
    host_id: "host-1",
    assigned_to: null,
    assignee_email: null,
    created_at: "2026-10-11T06:23:21Z",
    updated_at: null,
    resolved_at: null,
    confidence: 0,
    first_observed: null,
    last_observed: null,
    affected_hosts: [],
    affected_users: [],
    affected_services: [],
    mitre_technique_ids: [],
    mitre_tactics: [],
    simulated: false,
    source: null,
    notes: [],
    alert_ids: [],
  },
  host: { id: "host-1", name: "test_kali", hostname: "KALI", status: "critical", ip_address: "10.0.2.15", risk_score: 73 },
  events: [],
  timelines: [],
  linked_alerts: [],
  investigation_timeline: [],
  entities: { hosts: [], accounts: [], network_ips: [] },
  mitre: { technique_ids: [], tactics: [] },
  provenance: { simulated: false, sources: [] },
  partial_errors: [],
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  apiMock.mockReset();
});

describe("InvestigationWorkspacePane states", () => {
  it("renders real incident, offense and host data on success", async () => {
    apiMock.mockResolvedValue(WORKSPACE_OK);
    wrap(<InvestigationWorkspacePane incidentId="inc-1" />);
    await waitFor(
      () => expect(screen.getByText("Offense #1392: Security activity: root_login")).toBeTruthy(),
      { timeout: 5000 },
    );
    expect(screen.getAllByText("test_kali").length).toBeGreaterThan(0);
    expect(screen.getByText("Host context")).toBeTruthy();
    expect(screen.queryByText(/Failed to load/i)).toBeNull();
    expect(apiMock).toHaveBeenCalledWith("/api/v1/investigation/workspace?incident_id=inc-1");
  });

  it("shows a not-found state for a missing incident (404)", async () => {
    apiMock.mockRejectedValue(new ApiError("Incident not found", 404));
    wrap(<InvestigationWorkspacePane incidentId="missing" />);
    await waitFor(() => expect(screen.getByText("This case is no longer available")).toBeTruthy());
    expect(screen.getByText("Browse incidents")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /retry/i })).toBeNull();
  });

  it("shows an access-denied state for 403", async () => {
    apiMock.mockRejectedValue(new ApiError("Insufficient permissions", 403));
    wrap(<InvestigationWorkspacePane incidentId="inc-1" />);
    await waitFor(() => expect(screen.getByText("You do not have access to this case")).toBeTruthy());
  });

  it("shows a backend failure state and Retry repeats the same request", { timeout: 20000 }, async () => {
    apiMock.mockRejectedValue(new ApiError("Server error", 500));
    wrap(<InvestigationWorkspacePane incidentId="inc-1" />);

    await waitFor(() => expect(screen.getByText("Case data could not be loaded")).toBeTruthy(), {
      timeout: 8000,
    });
    const attemptsBefore = apiMock.mock.calls.length;
    apiMock.mockResolvedValue(WORKSPACE_OK);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(
      () => expect(screen.getByText("Offense #1392: Security activity: root_login")).toBeTruthy(),
      { timeout: 8000 },
    );
    const attemptsAfter = apiMock.mock.calls.slice(attemptsBefore);
    expect(attemptsAfter.length).toBeGreaterThan(0);
    for (const call of attemptsAfter) {
      expect(call[0]).toBe("/api/v1/investigation/workspace?incident_id=inc-1");
    }
  });

  it("shows an empty state when the case has no linked data", async () => {
    apiMock.mockResolvedValue({
      ...WORKSPACE_OK,
      alert: null,
      offense: null,
      incident: null,
      host: null,
      events: [],
      timelines: [],
      linked_alerts: [],
    });
    wrap(<InvestigationWorkspacePane incidentId="inc-1" />);
    await waitFor(() => expect(screen.getByText("No data linked to this case")).toBeTruthy());
  });
});
