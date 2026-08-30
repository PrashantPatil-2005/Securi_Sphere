import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ReportsPage from "@/app/(dashboard)/reports/page";

const mockDownload = vi.fn();
vi.mock("@/lib/download", () => ({
  downloadAuthenticated: (...args: unknown[]) => mockDownload(...args),
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("ReportsPage", () => {
  it("renders page title", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Security Reports")).toBeTruthy();
  });

  it("renders subtitle", () => {
    wrap(<ReportsPage />);
    expect(
      screen.getByText(
        "Executive PDFs for leadership plus operational daily, weekly, and monthly exports",
      ),
    ).toBeTruthy();
  });

  it("renders Executive PDF section", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Executive PDF")).toBeTruthy();
  });

  it("renders Compliance Assessment section", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Compliance Assessment")).toBeTruthy();
  });

  it("renders Operational Export section", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Operational Export")).toBeTruthy();
  });

  it("renders What's Included section", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("What's Included")).toBeTruthy();
  });

  it("renders report period select", () => {
    wrap(<ReportsPage />);
    const selects = screen.getAllByLabelText("Report period");
    expect(selects.length).toBeGreaterThanOrEqual(1);
  });

  it("renders framework select", () => {
    wrap(<ReportsPage />);
    const select = screen.getByLabelText("Framework") as HTMLSelectElement;
    expect(select).toBeTruthy();
    const options = Array.from(select.options).map((o) => o.text);
    expect(options.some((t) => t.includes("SOC 2"))).toBeTruthy();
    expect(options.some((t) => t.includes("ISO"))).toBeTruthy();
  });

  it("renders download buttons", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Download executive PDF")).toBeTruthy();
    expect(screen.getByText("Download compliance PDF")).toBeTruthy();
    expect(screen.getByText("Export PDF")).toBeTruthy();
    expect(screen.getByText("Export CSV")).toBeTruthy();
  });

  it("renders what's included items", () => {
    wrap(<ReportsPage />);
    expect(screen.getByText("Host inventory and connectivity summary")).toBeTruthy();
    expect(screen.getByText("Open and resolved alerts for the period")).toBeTruthy();
    expect(
      screen.getByText("Auto-generated recommendations for leadership action items"),
    ).toBeTruthy();
  });
});
