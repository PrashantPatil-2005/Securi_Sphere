import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HostRow } from "@/components/hosts/HostRow";
import { HostEmptyState } from "@/components/hosts/HostEmptyState";
import { HostDetailHeader } from "@/components/hosts/HostDetailHeader";
import { HostSummaryCards } from "@/components/hosts/HostSummaryCards";
import { HostAlertsList } from "@/components/hosts/HostAlertsList";
import { HostOffensesList } from "@/components/hosts/HostOffensesList";
import type { HostSummary } from "@/lib/types/host";

function makeHost(overrides: Partial<HostSummary> = {}): HostSummary {
  return {
    id: "host-1",
    name: "server-prod-03",
    hostname: "server-prod-03.local",
    ip_address: "10.0.0.42",
    os_info: "Ubuntu 22.04",
    status: "online",
    enrolled: true,
    last_seen: new Date(Date.now() - 12_000).toISOString(),
    created_at: new Date(Date.now() - 86400_000).toISOString(),
    risk_score: 87,
    alert_count: 3,
    ...overrides,
  };
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("HostRow", () => {
  it("renders host name, status, risk, agent, alerts", () => {
    const h = makeHost();
    wrap(<HostRow host={h} selected={false} onClick={() => {}} />);
    expect(screen.getByText("server-prod-03")).toBeTruthy();
    expect(screen.getByText("online")).toBeTruthy();
    expect(screen.getByText("87")).toBeTruthy();
    expect(screen.getByText("Enrolled")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("renders hostname when different from name", () => {
    const h = makeHost({ hostname: "server-prod-03.local" });
    wrap(<HostRow host={h} selected={false} onClick={() => {}} />);
    expect(screen.getByText("server-prod-03.local")).toBeTruthy();
  });

  it("renders IP address", () => {
    const h = makeHost({ ip_address: "10.0.0.42" });
    wrap(<HostRow host={h} selected={false} onClick={() => {}} />);
    expect(screen.getByText("10.0.0.42")).toBeTruthy();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const h = makeHost();
    wrap(<HostRow host={h} selected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText("server-prod-03"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies selected style when selected", () => {
    const h = makeHost();
    const { container } = wrap(<HostRow host={h} selected={true} onClick={() => {}} />);
    const link = container.querySelector("a");
    expect(link?.className).toContain("border-l-accent");
  });

  it("shows Pending for unenrolled host", () => {
    const h = makeHost({ enrolled: false });
    wrap(<HostRow host={h} selected={false} onClick={() => {}} />);
    expect(screen.getByText("Pending")).toBeTruthy();
  });

  it("shows dash for null risk score", () => {
    const h = makeHost({ risk_score: null });
    wrap(<HostRow host={h} selected={false} onClick={() => {}} />);
    expect(screen.getByText("—")).toBeTruthy();
  });
});

describe("HostEmptyState", () => {
  it("shows no hosts message when no filters", () => {
    wrap(<HostEmptyState hasFilters={false} onClear={() => {}} />);
    expect(screen.getByText("No hosts")).toBeTruthy();
  });

  it("shows no matching message when filters active", () => {
    wrap(<HostEmptyState hasFilters={true} onClear={() => {}} />);
    expect(screen.getByText("No matching hosts")).toBeTruthy();
  });

  it("calls onClear when clear button clicked", () => {
    const onClear = vi.fn();
    wrap(<HostEmptyState hasFilters={true} onClear={onClear} />);
    fireEvent.click(screen.getByText("Clear filters"));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});

describe("HostDetailHeader", () => {
  it("renders host name, status, risk, last seen", () => {
    const h = makeHost();
    wrap(<HostDetailHeader host={h} />);
    expect(screen.getByText("server-prod-03")).toBeTruthy();
    expect(screen.getByText("online")).toBeTruthy();
    expect(screen.getByText("87/100")).toBeTruthy();
    expect(screen.getByText("CRITICAL")).toBeTruthy();
  });

  it("renders back link", () => {
    const h = makeHost();
    wrap(<HostDetailHeader host={h} />);
    expect(screen.getByText("Back to Hosts")).toBeTruthy();
  });

  it("renders OS info when present", () => {
    const h = makeHost({ os_info: "Ubuntu 22.04" });
    wrap(<HostDetailHeader host={h} />);
    expect(screen.getByText("Ubuntu 22.04")).toBeTruthy();
  });

  it("renders Agent Enrolled badge", () => {
    const h = makeHost({ enrolled: true });
    wrap(<HostDetailHeader host={h} />);
    expect(screen.getByText("Agent Enrolled")).toBeTruthy();
  });
});

describe("HostSummaryCards", () => {
  it("renders alert count", () => {
    wrap(<HostSummaryCards hostId="h1" alertCount={5} />);
    expect(screen.getByText("5")).toBeTruthy();
  });

  it("renders zero alert count", () => {
    wrap(<HostSummaryCards hostId="h1" alertCount={0} />);
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(1);
  });

  it("renders null alert count as zero", () => {
    wrap(<HostSummaryCards hostId="h1" alertCount={null} />);
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(1);
  });
});

describe("HostAlertsList", () => {
  it("renders alerts with title and severity", () => {
    const alerts = [
      { id: "a1", title: "Failed SSH", severity: "high", status: "open", created_at: new Date().toISOString() },
    ];
    wrap(<HostAlertsList alerts={alerts} hostId="h1" isLoading={false} />);
    expect(screen.getByText("Failed SSH")).toBeTruthy();
    expect(screen.getByText("High")).toBeTruthy();
  });

  it("shows empty state when no alerts", () => {
    wrap(<HostAlertsList alerts={[]} hostId="h1" isLoading={false} />);
    expect(screen.getByText("No alerts for this host.")).toBeTruthy();
  });

  it("shows loading state", () => {
    wrap(<HostAlertsList alerts={[]} hostId="h1" isLoading={true} />);
    expect(document.querySelector(".skeleton")).toBeTruthy();
  });
});

describe("HostOffensesList", () => {
  it("renders offenses with number and title", () => {
    const offenses = [
      { id: "o1", offense_number: 1042, title: "Account Compromise", risk_level: "critical", status: "open", created_at: new Date().toISOString() },
    ];
    wrap(<HostOffensesList offenses={offenses} hostId="h1" isLoading={false} />);
    expect(screen.getByText("#1042 — Account Compromise")).toBeTruthy();
  });

  it("shows empty state when no offenses", () => {
    wrap(<HostOffensesList offenses={[]} hostId="h1" isLoading={false} />);
    expect(screen.getByText("No offenses for this host.")).toBeTruthy();
  });
});

describe("Host types", () => {
  it("has correct status constants", async () => {
    const { HOST_STATUSES } = await import("@/lib/types/host");
    expect(HOST_STATUSES).toEqual(["inactive", "online", "offline", "warning", "critical"]);
  });

  it("has correct sort options", async () => {
    const { HOST_SORT_OPTIONS } = await import("@/lib/types/host");
    expect(HOST_SORT_OPTIONS).toHaveLength(5);
    expect(HOST_SORT_OPTIONS[0].value).toBe("newest");
  });

  it("has correct default filters", async () => {
    const { DEFAULT_HOST_FILTERS } = await import("@/lib/types/host");
    expect(DEFAULT_HOST_FILTERS.hostname).toBe("");
    expect(DEFAULT_HOST_FILTERS.status).toBe("");
  });

  it("hostRiskLevel returns correct levels", async () => {
    const { hostRiskLevel } = await import("@/lib/types/host");
    expect(hostRiskLevel(null)).toBe("none");
    expect(hostRiskLevel(10)).toBe("low");
    expect(hostRiskLevel(30)).toBe("medium");
    expect(hostRiskLevel(50)).toBe("high");
    expect(hostRiskLevel(80)).toBe("critical");
  });

  it("hostRiskColor returns correct colors", async () => {
    const { hostRiskColor } = await import("@/lib/types/host");
    expect(hostRiskColor(null)).toBe("text-muted");
    expect(hostRiskColor(10)).toBe("text-success");
    expect(hostRiskColor(30)).toBe("text-severity-medium");
    expect(hostRiskColor(50)).toBe("text-warning");
    expect(hostRiskColor(80)).toBe("text-danger");
  });

  it("hostStatusColor returns correct colors", async () => {
    const { hostStatusColor } = await import("@/lib/types/host");
    expect(hostStatusColor("online")).toBe("text-success");
    expect(hostStatusColor("offline")).toBe("text-muted");
    expect(hostStatusColor("warning")).toBe("text-warning");
    expect(hostStatusColor("critical")).toBe("text-danger");
    expect(hostStatusColor("inactive")).toBe("text-muted");
  });
});
