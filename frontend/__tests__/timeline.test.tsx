import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TimelineList } from "@/components/timeline/TimelineList";
import { TimelineFiltersBar } from "@/components/timeline/TimelineFilters";
import { TimelineDetail } from "@/components/timeline/TimelineDetail";
import { TimelineReplay } from "@/components/timeline/TimelineReplay";
import { timelineDuration, DEFAULT_TIMELINE_FILTERS } from "@/lib/types/timeline";
import type { Timeline, TimelineEvent, TimelineFilters } from "@/lib/types/timeline";

function makeTimeline(overrides: Partial<Timeline> = {}): Timeline {
  return {
    id: "tl-1",
    host_id: "host-1",
    title: "Credential stuffing attack chain",
    description: "12 sequential events from initial probe to lateral movement",
    started_at: new Date(Date.now() - 600_000).toISOString(),
    ended_at: new Date(Date.now() - 120_000).toISOString(),
    event_ids: ["evt-1", "evt-2", "evt-3"],
    mitre_techniques: ["T1078", "T1021"],
    severity: "critical",
    confidence: 87,
    status: "active",
    ...overrides,
  };
}

function makeTimelineEvent(overrides: Partial<TimelineEvent> = {}): TimelineEvent {
  return {
    id: "evt-1",
    event_type: "ssh.failed_login",
    severity: "high",
    description: "Failed password for root",
    mitre_technique_id: "T1078",
    timestamp: new Date(Date.now() - 500_000).toISOString(),
    ...overrides,
  };
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("timelineDuration", () => {
  it("formats seconds only", () => {
    const start = "2025-01-01T00:00:00Z";
    const end = "2025-01-01T00:00:45Z";
    expect(timelineDuration(start, end)).toBe("45s");
  });

  it("formats minutes and seconds", () => {
    const start = "2025-01-01T00:00:00Z";
    const end = "2025-01-01T00:02:30Z";
    expect(timelineDuration(start, end)).toBe("2m 30s");
  });

  it("formats hours and minutes", () => {
    const start = "2025-01-01T00:00:00Z";
    const end = "2025-01-01T01:15:00Z";
    expect(timelineDuration(start, end)).toBe("1h 15m");
  });
});

describe("TimelineList", () => {
  it("renders timeline title", () => {
    const tl = makeTimeline();
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("Credential stuffing attack chain")).toBeTruthy();
  });

  it("renders description when present", () => {
    const tl = makeTimeline();
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("12 sequential events from initial probe to lateral movement")).toBeTruthy();
  });

  it("renders severity badge", () => {
    const tl = makeTimeline();
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("Critical")).toBeTruthy();
  });

  it("renders MITRE technique tags", () => {
    const tl = makeTimeline({ mitre_techniques: ["T1078", "T1021"] });
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("T1078")).toBeTruthy();
    expect(screen.getByText("T1021")).toBeTruthy();
  });

  it("truncates to 3 MITRE techniques and shows overflow count", () => {
    const tl = makeTimeline({ mitre_techniques: ["T1078", "T1021", "T1059", "T1566"] });
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("+1")).toBeTruthy();
  });

  it("calls onSelect when clicked", () => {
    const onSelect = vi.fn();
    const tl = makeTimeline();
    wrap(<TimelineList timelines={[tl]} selectedId={null} onSelect={onSelect} isLoading={false} />);
    fireEvent.click(screen.getByText("Credential stuffing attack chain"));
    expect(onSelect).toHaveBeenCalledWith("tl-1");
  });

  it("applies selected style when selectedId matches", () => {
    const tl = makeTimeline();
    const { container } = wrap(
      <TimelineList timelines={[tl]} selectedId="tl-1" onSelect={() => {}} isLoading={false} />,
    );
    const buttons = container.querySelectorAll("button");
    expect(buttons[0]?.className).toContain("border-l-accent");
  });

  it("shows empty state when no timelines", () => {
    wrap(<TimelineList timelines={[]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("No attack timelines in this range.")).toBeTruthy();
  });

  it("shows loading skeletons", () => {
    const { container } = wrap(
      <TimelineList timelines={[]} selectedId={null} onSelect={() => {}} isLoading={true} />,
    );
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });

  it("shows chain count", () => {
    const tl1 = makeTimeline({ id: "tl-1" });
    const tl2 = makeTimeline({ id: "tl-2" });
    wrap(<TimelineList timelines={[tl1, tl2]} selectedId={null} onSelect={() => {}} isLoading={false} />);
    expect(screen.getByText("2 chains detected")).toBeTruthy();
  });
});

describe("TimelineFiltersBar", () => {
  it("renders search and filter selects", () => {
    const filters: TimelineFilters = { ...DEFAULT_TIMELINE_FILTERS };
    wrap(<TimelineFiltersBar filters={filters} onFiltersChange={() => {}} total={5} />);
    expect(screen.getByPlaceholderText("Search timelines...")).toBeTruthy();
    expect(screen.getByLabelText("Filter by severity")).toBeTruthy();
    expect(screen.getByLabelText("Filter by status")).toBeTruthy();
  });

  it("shows total count", () => {
    const filters: TimelineFilters = { ...DEFAULT_TIMELINE_FILTERS };
    wrap(<TimelineFiltersBar filters={filters} onFiltersChange={() => {}} total={12} />);
    expect(screen.getByText("12 timelines")).toBeTruthy();
  });

  it("shows singular for 1 timeline", () => {
    const filters: TimelineFilters = { ...DEFAULT_TIMELINE_FILTERS };
    wrap(<TimelineFiltersBar filters={filters} onFiltersChange={() => {}} total={1} />);
    expect(screen.getByText("1 timeline")).toBeTruthy();
  });

  it("shows clear button when filters active", () => {
    const filters: TimelineFilters = { ...DEFAULT_TIMELINE_FILTERS, severity: "critical" };
    wrap(<TimelineFiltersBar filters={filters} onFiltersChange={() => {}} total={0} />);
    expect(screen.getByText("Clear (1)")).toBeTruthy();
  });

  it("calls onFiltersChange with reset when clear clicked", () => {
    const onFiltersChange = vi.fn();
    const filters: TimelineFilters = { ...DEFAULT_TIMELINE_FILTERS, severity: "critical", status: "active" };
    wrap(<TimelineFiltersBar filters={filters} onFiltersChange={onFiltersChange} total={0} />);
    fireEvent.click(screen.getByText("Clear (2)"));
    expect(onFiltersChange).toHaveBeenCalledWith({ host_id: "", severity: "", status: "", search: "" });
  });
});

describe("TimelineDetail", () => {
  it("shows empty state when no timeline selected", () => {
    wrap(<TimelineDetail timeline={null} events={[]} isLoading={false} currentIndex={0} />);
    expect(screen.getByText("Select a timeline")).toBeTruthy();
  });

  it("renders timeline title and description", () => {
    const tl = makeTimeline();
    wrap(<TimelineDetail timeline={tl} events={[]} isLoading={false} currentIndex={0} />);
    expect(screen.getByText("Credential stuffing attack chain")).toBeTruthy();
  });

  it("shows event count in subtitle when no description", () => {
    const tl = makeTimeline({ description: null });
    const evt = makeTimelineEvent();
    wrap(<TimelineDetail timeline={tl} events={[evt]} isLoading={false} currentIndex={0} />);
    expect(screen.getByText("1 events in chain")).toBeTruthy();
  });

  it("renders event types", () => {
    const tl = makeTimeline();
    const evt1 = makeTimelineEvent({ id: "evt-1", event_type: "ssh.failed_login" });
    const evt2 = makeTimelineEvent({ id: "evt-2", event_type: "process.create" });
    wrap(<TimelineDetail timeline={tl} events={[evt1, evt2]} isLoading={false} currentIndex={1} />);
    expect(screen.getByText("ssh.failed_login")).toBeTruthy();
    expect(screen.getByText("process.create")).toBeTruthy();
  });

  it("shows MITRE technique tags on events", () => {
    const tl = makeTimeline();
    const evt = makeTimelineEvent({ mitre_technique_id: "T1078" });
    wrap(<TimelineDetail timeline={tl} events={[evt]} isLoading={false} currentIndex={0} />);
    expect(screen.getByText("T1078")).toBeTruthy();
  });

  it("shows no events message when empty", () => {
    const tl = makeTimeline();
    wrap(<TimelineDetail timeline={tl} events={[]} isLoading={false} currentIndex={0} />);
    expect(screen.getByText("No events in this timeline.")).toBeTruthy();
  });

  it("shows loading skeletons", () => {
    const tl = makeTimeline();
    const { container } = wrap(
      <TimelineDetail timeline={tl} events={[]} isLoading={true} currentIndex={0} />,
    );
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });
});

describe("TimelineReplay", () => {
  it("shows empty state when no events", () => {
    wrap(
      <TimelineReplay
        events={[]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByText("No events")).toBeTruthy();
  });

  it("renders play/pause button", () => {
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByLabelText("Play")).toBeTruthy();
  });

  it("shows pause label when playing", () => {
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={true}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByLabelText("Pause")).toBeTruthy();
  });

  it("calls onTogglePlay when play button clicked", () => {
    const onTogglePlay = vi.fn();
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={onTogglePlay}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    fireEvent.click(screen.getByLabelText("Play"));
    expect(onTogglePlay).toHaveBeenCalledTimes(1);
  });

  it("shows speed buttons", () => {
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByText("0.5x")).toBeTruthy();
    expect(screen.getByText("1x")).toBeTruthy();
    expect(screen.getByText("2x")).toBeTruthy();
    expect(screen.getByText("4x")).toBeTruthy();
  });

  it("calls onSpeedChange when speed button clicked", () => {
    const onSpeedChange = vi.fn();
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={onSpeedChange}
        isLoading={false}
      />,
    );
    fireEvent.click(screen.getByText("2x"));
    expect(onSpeedChange).toHaveBeenCalledWith(2);
  });

  it("shows step counter", () => {
    const evt1 = makeTimelineEvent({ id: "e1" });
    const evt2 = makeTimelineEvent({ id: "e2" });
    render(
      <TimelineReplay
        events={[evt1, evt2]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByText("Step 1 / 2")).toBeTruthy();
  });

  it("disables restart button at index 0", () => {
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByLabelText("Restart")).toBeDisabled();
  });

  it("calls onIndexChange when restart clicked", () => {
    const onIndexChange = vi.fn();
    const evt1 = makeTimelineEvent({ id: "e1" });
    const evt2 = makeTimelineEvent({ id: "e2" });
    render(
      <TimelineReplay
        events={[evt1, evt2]}
        title="Test"
        currentIndex={1}
        onIndexChange={onIndexChange}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    fireEvent.click(screen.getByLabelText("Restart"));
    expect(onIndexChange).toHaveBeenCalledWith(0);
  });

  it("shows scrubber", () => {
    const evt = makeTimelineEvent();
    render(
      <TimelineReplay
        events={[evt]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={false}
      />,
    );
    expect(screen.getByLabelText("Replay scrubber")).toBeTruthy();
  });

  it("shows loading skeletons", () => {
    const { container } = render(
      <TimelineReplay
        events={[]}
        title="Test"
        currentIndex={0}
        onIndexChange={() => {}}
        playing={false}
        onTogglePlay={() => {}}
        speed={1}
        onSpeedChange={() => {}}
        isLoading={true}
      />,
    );
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });
});
