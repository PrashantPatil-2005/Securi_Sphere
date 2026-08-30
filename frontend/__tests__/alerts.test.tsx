import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AlertRow } from "@/components/alerts/AlertRow";
import { AlertEmptyState } from "@/components/alerts/AlertEmptyState";
import { BulkActionBar } from "@/components/alerts/BulkActionBar";
import { EventDetailDrawer } from "@/components/alerts/EventDetailDrawer";
import type { Alert, AlertEvent } from "@/lib/types/alert";

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: "alert-1",
    host_id: "host-1",
    rule_id: null,
    source: null,
    mitre_technique_id: null,
    mitre_tactic: null,
    confidence: 0.92,
    severity: "high",
    title: "Multiple failed SSH attempts",
    description: "Detected 15 failed login attempts",
    status: "open",
    created_at: new Date(Date.now() - 120_000).toISOString(),
    resolved_at: null,
    resolved_by: null,
    assigned_to: null,
    feedback_label: null,
    feedback_note: null,
    feedback_at: null,
    feedback_by: null,
    ...overrides,
  };
}

function makeEvent(overrides: Partial<AlertEvent> = {}): AlertEvent {
  return {
    id: "evt-1",
    event_type: "ssh.failed_login",
    severity: "high",
    description: "Failed password for root",
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("AlertRow", () => {
  it("renders alert title and severity", () => {
    const alert = makeAlert();
    render(<AlertRow alert={alert} />);
    expect(screen.getByText("Multiple failed SSH attempts")).toBeDefined();
    expect(screen.getByText("High")).toBeDefined();
  });

  it("renders host name when provided", () => {
    const alert = makeAlert();
    render(<AlertRow alert={alert} hostName="server-01" />);
    expect(screen.getByText("server-01")).toBeDefined();
  });

  it("shows dash when no host name", () => {
    const alert = makeAlert();
    render(<AlertRow alert={alert} />);
    expect(screen.getByText("—")).toBeDefined();
  });

  it("renders confidence percentage", () => {
    const alert = makeAlert({ confidence: 0.85 });
    render(<AlertRow alert={alert} />);
    expect(screen.getByText("85%")).toBeDefined();
  });

  it("does not render confidence when null", () => {
    const alert = makeAlert({ confidence: null });
    render(<AlertRow alert={alert} />);
    expect(screen.queryByText(/%/)).toBeNull();
  });

  it("renders source in monospace when available", () => {
    const alert = makeAlert({ source: "agent" });
    render(<AlertRow alert={alert} />);
    const sourceEl = screen.getByText("agent");
    expect(sourceEl.className).toContain("font-mono");
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    const alert = makeAlert();
    render(<AlertRow alert={alert} onClick={onClick} />);
    fireEvent.click(screen.getByText("Multiple failed SSH attempts"));
    expect(onClick).toHaveBeenCalled();
  });

  it("applies selected style when selected", () => {
    const alert = makeAlert();
    const { container } = render(<AlertRow alert={alert} selected />);
    const row = container.querySelector("[role='button']");
    expect(row?.className).toContain("bg-accent/5");
  });
});

describe("AlertEmptyState", () => {
  it("shows no alerts message when no filters", () => {
    render(<AlertEmptyState hasFilters={false} />);
    expect(screen.getByText("No alerts yet")).toBeDefined();
  });

  it("shows no matches message when filters active", () => {
    render(<AlertEmptyState hasFilters={true} />);
    expect(screen.getByText("No alerts match your filters")).toBeDefined();
  });
});

describe("BulkActionBar", () => {
  it("shows selected count", () => {
    render(
      <BulkActionBar
        count={5}
        isPending={false}
        onAction={vi.fn()}
        onClear={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByText("5 selected")).toBeDefined();
  });

  it("shows all action buttons", () => {
    render(
      <BulkActionBar
        count={3}
        isPending={false}
        onAction={vi.fn()}
        onClear={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByText("Assign to me")).toBeDefined();
    expect(screen.getByText("Investigate")).toBeDefined();
    expect(screen.getByText("Resolve")).toBeDefined();
    expect(screen.getByText("Close")).toBeDefined();
    expect(screen.getByText("Clear")).toBeDefined();
  });

  it("disables buttons when pending", () => {
    render(
      <BulkActionBar
        count={2}
        isPending={true}
        onAction={vi.fn()}
        onClear={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => {
      if (btn.textContent !== "Clear") {
        expect(btn).toHaveProperty("disabled", true);
      }
    });
  });

  it("calls onClear when Clear clicked", () => {
    const onClear = vi.fn();
    render(
      <BulkActionBar
        count={1}
        isPending={false}
        onAction={vi.fn()}
        onClear={onClear}
        onConfirm={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Clear"));
    expect(onClear).toHaveBeenCalled();
  });
});

describe("EventDetailDrawer", () => {
  it("does not render when closed", () => {
    render(
      <EventDetailDrawer event={makeEvent()} open={false} onClose={vi.fn()} />,
    );
    expect(screen.queryByText("Event Details")).toBeNull();
  });

  it("renders event when open", () => {
    render(
      <EventDetailDrawer event={makeEvent()} open={true} onClose={vi.fn()} />,
    );
    expect(screen.getByText("Event Details")).toBeDefined();
    expect(screen.getAllByText("ssh.failed_login").length).toBeGreaterThan(0);
    expect(screen.getByText("High")).toBeDefined();
  });

  it("renders description when available", () => {
    const event = makeEvent({ description: "Failed password for root" });
    render(
      <EventDetailDrawer event={event} open={true} onClose={vi.fn()} />,
    );
    expect(screen.getByText("Failed password for root")).toBeDefined();
  });

  it("does not render description section when null", () => {
    const event = makeEvent({ description: null });
    render(
      <EventDetailDrawer event={event} open={true} onClose={vi.fn()} />,
    );
    expect(screen.queryByText("Failed password for root")).toBeNull();
  });

  it("calls onClose when backdrop clicked", () => {
    const onClose = vi.fn();
    render(
      <EventDetailDrawer event={makeEvent()} open={true} onClose={onClose} />,
    );
    const backdrop = document.querySelector("[aria-label='Close drawer']");
    if (backdrop) fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });
});
