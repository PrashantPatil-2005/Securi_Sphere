import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MitreDrilldown } from "@/components/mitre/MitreDrilldown";
import { MitreMatrix } from "@/components/mitre/MitreMatrix";
import { MITRE_TACTIC_ORDER } from "@/lib/types/mitre";
import type { MitreDrilldownResponse, MitreTechniqueWithCount } from "@/lib/types/mitre";

function makeDrilldown(overrides: Partial<MitreDrilldownResponse> = {}): MitreDrilldownResponse {
  return {
    technique_id: "T1078",
    tactic: "Initial Access",
    name: "Valid Accounts",
    description: "Adversaries may obtain and abuse credentials of existing accounts",
    event_count: 42,
    alert_count: 7,
    top_hosts: [
      { host_id: "h1", host_name: "srv-prod-01", event_count: 30 },
      { host_id: "h2", host_name: "srv-prod-02", event_count: 12 },
    ],
    recent_events: [
      {
        id: "e1",
        host_id: "h1",
        event_type: "ssh.failed_login",
        severity: "high",
        description: "Failed password for root",
        timestamp: new Date(Date.now() - 100_000).toISOString(),
      },
    ],
    recent_alerts: [
      {
        id: "a1",
        host_id: "h1",
        title: "Multiple failed SSH attempts",
        severity: "high",
        status: "open",
        created_at: new Date(Date.now() - 200_000).toISOString(),
      },
    ],
    ...overrides,
  };
}

function makeMatrixTechniques(): Record<string, MitreTechniqueWithCount[]> {
  return {
    "Initial Access": [
      { technique_id: "T1078", tactic: "Initial Access", name: "Valid Accounts", description: null, count: 12 },
      { technique_id: "T1566", tactic: "Initial Access", name: "Phishing", description: null, count: 0 },
    ],
    "Execution": [
      { technique_id: "T1059", tactic: "Execution", name: "Command and Scripting Interpreter", description: null, count: 3 },
    ],
  };
}

describe("MitreDrilldown", () => {
  it("shows empty state when no data", () => {
    render(<MitreDrilldown data={undefined} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("Select a technique")).toBeTruthy();
  });

  it("shows loading state", () => {
    const { container } = render(
      <MitreDrilldown data={undefined} isLoading={true} onClose={() => {}} />,
    );
    expect(screen.getByText("Loading...")).toBeTruthy();
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });

  it("renders technique ID and name", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("T1078 — Valid Accounts")).toBeTruthy();
  });

  it("renders tactic as subtitle", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("Initial Access")).toBeTruthy();
  });

  it("renders description", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("Adversaries may obtain and abuse credentials of existing accounts")).toBeTruthy();
  });

  it("renders event and alert counts", () => {
    vi.useFakeTimers();
    try {
      const d = makeDrilldown({ event_count: 42, alert_count: 7 });
      render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
      act(() => {
        vi.advanceTimersByTime(2_000);
      });
      expect(screen.getByText("42")).toBeTruthy();
      expect(screen.getByText("7")).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it("renders top hosts", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("srv-prod-01")).toBeTruthy();
    expect(screen.getByText("srv-prod-02")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
  });

  it("renders recent alerts", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("Multiple failed SSH attempts")).toBeTruthy();
    expect(screen.getByText("open")).toBeTruthy();
  });

  it("renders recent events", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("ssh.failed_login")).toBeTruthy();
  });

  it("shows no data message when zero counts", () => {
    const d = makeDrilldown({ event_count: 0, alert_count: 0, top_hosts: [], recent_events: [], recent_alerts: [] });
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    expect(screen.getByText("No matching events or alerts in the selected time range.")).toBeTruthy();
  });

  it("links to filtered events page", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    const link = screen.getByText("View all events →");
    expect(link.closest("a")?.getAttribute("href")).toBe("/events?mitre_technique_id=T1078");
  });

  it("links to filtered alerts page", () => {
    const d = makeDrilldown();
    render(<MitreDrilldown data={d} isLoading={false} onClose={() => {}} />);
    const link = screen.getByText("View all alerts →");
    expect(link.closest("a")?.getAttribute("href")).toBe("/alerts?mitre_technique_id=T1078");
  });
});

describe("MitreMatrix", () => {
  const tactics = makeMatrixTechniques();
  const coverage = { "Initial Access": 50, "Execution": 100 };

  it("renders tactic columns", () => {
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Initial Access")).toBeTruthy();
    expect(screen.getByText("Execution")).toBeTruthy();
  });

  it("renders coverage percentages", () => {
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("50%")).toBeTruthy();
    expect(screen.getByText("100%")).toBeTruthy();
  });

  it("renders technique names", () => {
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Valid Accounts")).toBeTruthy();
    expect(screen.getByText("Phishing")).toBeTruthy();
    expect(screen.getByText("Command and Scripting Interpreter")).toBeTruthy();
  });

  it("renders technique IDs", () => {
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("T1078")).toBeTruthy();
    expect(screen.getByText("T1566")).toBeTruthy();
    expect(screen.getByText("T1059")).toBeTruthy();
  });

  it("shows event count when count > 0", () => {
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("12 events")).toBeTruthy();
    expect(screen.getByText("3 events")).toBeTruthy();
  });

  it("calls onSelect when technique clicked", () => {
    const onSelect = vi.fn();
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Valid Accounts"));
    expect(onSelect).toHaveBeenCalledWith("T1078");
  });

  it("calls onSelect with null when deselecting same technique", () => {
    const onSelect = vi.fn();
    render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique="T1078"
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Valid Accounts"));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("renders tactics in MITRE_TACTIC_ORDER order", () => {
    const { container } = render(
      <MitreMatrix
        tactics={tactics}
        tacticCoverage={coverage}
        selectedTechnique={null}
        onSelect={() => {}}
      />,
    );
    const columns = container.querySelectorAll(".w-48");
    const firstColumn = columns[0];
    expect(firstColumn?.textContent).toContain("Initial Access");
    const secondColumn = columns[1];
    expect(secondColumn?.textContent).toContain("Execution");
  });
});
