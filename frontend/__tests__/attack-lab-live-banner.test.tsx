import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { LiveAttackBanner } from "@/components/attack-lab/LiveAttackBanner";
import { SimulationLiveProgress } from "@/components/attack-lab/SimulationLiveProgress";

vi.mock("@/lib/theme/ThemeProvider", () => ({
  useTheme: () => ({ reducedMotion: false }),
}));

vi.mock("@/lib/telemetry", () => ({ track: vi.fn() }));

/**
 * Mirrors the real store: every message produces a NEW array reference so
 * consumers' useMemo deps invalidate.
 */
const store = { items: [] as Record<string, unknown>[] };

vi.mock("@/lib/websocket", () => ({
  useSecurityFeedStore: () => ({
    subscribe: () => () => {},
    getSnapshot: () => store.items,
    prepend: () => {},
  }),
  useFeedItems: (_subscribe: unknown, getSnapshot: () => Record<string, unknown>[]) =>
    getSnapshot(),
}));

const HOST = "11111111-1111-1111-1111-111111111111";
const OTHER_HOST = "22222222-2222-2222-2222-222222222222";
const RUN_STARTED = 1_000;

function push(event_type: string, host_id: string, _ts = RUN_STARTED + 1) {
  store.items = [
    { _type: "security_feed", _ts, host_id, event_type, description: `${event_type} on lab` },
    ...store.items,
  ];
}

function pushAlert(host_id: string, _ts = RUN_STARTED + 2) {
  store.items = [{ _type: "new_alert", _ts, host_id, title: "Brute force" }, ...store.items];
}

beforeEach(() => {
  store.items = [];
});

afterEach(() => {
  vi.useRealTimers();
});

describe("LiveAttackBanner", () => {
  const base = {
    running: true,
    hostId: HOST,
    hostName: "web-01",
    scenarioName: "Brute Force Attack",
    expectedEvents: 13,
    runStartedAt: RUN_STARTED,
  };

  it("renders nothing before any run event lands", () => {
    const { container } = render(<LiveAttackBanner {...base} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when idle and the run window has expired", () => {
    vi.useFakeTimers();
    push("ssh_login_failure", HOST);
    const { container } = render(
      <LiveAttackBanner {...base} running={false} dwellMs={1} />,
    );
    act(() => {
      vi.advanceTimersByTime(5);
    });
    expect(container).toBeEmptyDOMElement();
  });

  it("escalates the title as the kill chain advances", () => {
    push("ssh_login_failure", HOST);
    const { rerender } = render(<LiveAttackBanner {...base} />);
    expect(screen.getByText("ATTACK IN PROGRESS on web-01")).toBeInTheDocument();

    push("ssh_login_success", HOST);
    rerender(<LiveAttackBanner {...base} />);
    expect(screen.getByText("ACCESS GAINED on web-01")).toBeInTheDocument();

    push("sudo_usage", HOST);
    rerender(<LiveAttackBanner {...base} />);
    expect(screen.getByText("PRIVILEGE ESCALATION on web-01")).toBeInTheDocument();

    push("service_failure", HOST);
    rerender(<LiveAttackBanner {...base} />);
    expect(screen.getByText("IMPACT DETECTED on web-01")).toBeInTheDocument();
  });

  it("counts only events for this host inside the run window", () => {
    push("service_failure", OTHER_HOST);
    push("ssh_login_failure", HOST, RUN_STARTED - 500);
    push("ssh_login_failure", HOST);
    push("ssh_login_failure", HOST);
    render(<LiveAttackBanner {...base} />);
    expect(screen.getByText(/2\/13 events injected/)).toBeInTheDocument();
  });

  it("stays up briefly after the run and reports the outcome", () => {
    push("ssh_login_failure", HOST);
    pushAlert(HOST);
    render(<LiveAttackBanner {...base} running={false} />);
    expect(screen.getByText(/1 events injected · 1 alerts raised/)).toBeInTheDocument();
    expect(screen.getByText(/Brute Force Attack/)).toBeInTheDocument();
  });
});

describe("SimulationLiveProgress", () => {
  const base = {
    running: true,
    scenarioName: "Brute Force Attack",
    hostId: HOST,
    expectedEvents: 4,
    runStartedAt: RUN_STARTED,
  };

  it("renders nothing when no run is in flight", () => {
    const { container } = render(<SimulationLiveProgress {...base} running={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("reports live injection counts and advances to correlation", () => {
    push("ssh_login_failure", HOST);
    push("ssh_login_failure", HOST);
    const { rerender } = render(<SimulationLiveProgress {...base} />);
    expect(
      screen.getByText(/Attack unfolding live — Brute Force Attack/),
    ).toBeInTheDocument();
    expect(screen.getByText(/2\/4 events injected/)).toBeInTheDocument();
    expect(screen.getByText("Injecting events")).toBeInTheDocument();

    push("ssh_login_success", HOST);
    push("ssh_login_success", HOST);
    rerender(<SimulationLiveProgress {...base} />);
    expect(screen.getByText(/4\/4 events injected/)).toBeInTheDocument();
    expect(screen.getByText("Correlating offenses")).toBeInTheDocument();
  });

  it("shows the latest injected event so the attack reads as a story", () => {
    push("ssh_login_failure", HOST);
    render(<SimulationLiveProgress {...base} />);
    expect(screen.getByText(/latest: ssh_login_failure on lab/)).toBeInTheDocument();
  });
});
