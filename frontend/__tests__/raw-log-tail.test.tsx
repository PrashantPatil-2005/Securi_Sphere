import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { RawLogTail } from "@/components/attack-lab/RawLogTail";
import type { EventListResponse } from "@/lib/types/event";

vi.mock("@/lib/theme/ThemeProvider", () => ({
  useTheme: () => ({ reducedMotion: false }),
}));

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

let seed: EventListResponse | undefined;

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
    "@tanstack/react-query",
  );
  return {
    ...actual,
    useQuery: () => ({ data: seed, isLoading: false, isError: false }),
  };
});

vi.mock("@/lib/api", () => ({ api: vi.fn() }));

const HOST = "11111111-1111-1111-1111-111111111111";

function seedEvent(id: string, raw_log: string | null, severity = "info") {
  return {
    id,
    host_id: HOST,
    event_type: "ssh_login_failure",
    severity,
    description: null,
    source: "agent",
    raw_log,
    timestamp: "2026-10-12T09:41:00Z",
  };
}

function liveEvent(id: string, raw_log: string, severity = "high", _ts = Date.now()) {
  store.items = [
    { _type: "security_feed", id, host_id: HOST, raw_log, severity, _ts },
    ...store.items,
  ];
}

beforeEach(() => {
  store.items = [];
  seed = undefined;
});

describe("RawLogTail", () => {
  it("explains an idle host instead of showing an empty box", () => {
    render(<RawLogTail hostId={HOST} hostName="web-01" running={false} />);
    expect(screen.getByText(/no recent telemetry for web-01/)).toBeInTheDocument();
  });

  it("says it is waiting once a run starts", () => {
    render(<RawLogTail hostId={HOST} hostName="web-01" running />);
    expect(screen.getByText(/waiting for telemetry from web-01/)).toBeInTheDocument();
  });

  it("renders seeded syslog lines oldest first", () => {
    seed = {
      items: [
        seedEvent("e2", "Oct 12 09:41:02 web-01 sshd[31415]: Failed password for svc_deploy"),
        seedEvent("e1", "Oct 12 09:41:01 web-01 sshd[31415]: Accepted password for root"),
      ],
      total: 2,
      page: 1,
      page_size: 30,
      next_cursor: null,
      has_more: false,
    } as EventListResponse;

    render(<RawLogTail hostId={HOST} hostName="web-01" running={false} />);

    const log = screen.getByRole("log");
    expect(log.textContent).toContain("Accepted password for root");
    expect(log.textContent).toContain("Failed password for svc_deploy");
    expect(log.textContent!.indexOf("Accepted password")).toBeLessThan(
      log.textContent!.indexOf("Failed password"),
    );
  });

  it("appends live lines after the seed and ignores other hosts", () => {
    seed = {
      items: [seedEvent("e1", "Oct 12 09:41:01 web-01 sshd: seed line")],
      total: 1,
      page: 1,
      page_size: 30,
      next_cursor: null,
      has_more: false,
    } as EventListResponse;

    liveEvent("live-1", "Oct 12 09:41:10 web-01 sshd: live line", "critical");
    store.items = [
      {
        _type: "security_feed",
        id: "other",
        host_id: "22222222-2222-2222-2222-222222222222",
        raw_log: "Oct 12 09:41:11 other-host: not ours",
      },
      ...store.items,
    ];

    render(<RawLogTail hostId={HOST} hostName="web-01" running />);

    const log = screen.getByRole("log");
    expect(log.textContent).toContain("seed line");
    expect(log.textContent).toContain("live line");
    expect(log.textContent).not.toContain("not ours");
    expect(log.textContent!.indexOf("seed line")).toBeLessThan(
      log.textContent!.indexOf("live line"),
    );
  });

  it("deduplicates a line that arrives both seeded and live", () => {
    seed = {
      items: [seedEvent("dup", "Oct 12 09:41:01 web-01 sshd: only once")],
      total: 1,
      page: 1,
      page_size: 30,
      next_cursor: null,
      has_more: false,
    } as EventListResponse;
    liveEvent("dup", "Oct 12 09:41:01 web-01 sshd: only once");

    render(<RawLogTail hostId={HOST} hostName="web-01" running={false} />);
    expect(screen.getByRole("log").textContent!.match(/only once/g)).toHaveLength(1);
  });

  it("shows a live cursor while the attack streams", () => {
    seed = {
      items: [seedEvent("e1", "Oct 12 09:41:01 web-01 sshd: line")],
      total: 1,
      page: 1,
      page_size: 30,
      next_cursor: null,
      has_more: false,
    } as EventListResponse;

    const { rerender } = render(<RawLogTail hostId={HOST} hostName="web-01" running />);
    expect(screen.getByRole("log").querySelector("[aria-hidden]")).not.toBeNull();

    rerender(<RawLogTail hostId={HOST} hostName="web-01" running={false} />);
    expect(screen.getByRole("log").querySelector("[aria-hidden]")).toBeNull();
  });
});
