import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SecurityKpis } from "@/components/dashboard/sections/SecurityKpis";
import { HostRiskPanel } from "@/components/dashboard/sections/HostRiskPanel";
import { AttackTimelines } from "@/components/dashboard/sections/AttackTimelines";
import { SeverityBreakdown } from "@/components/dashboard/sections/SeverityBreakdown";

vi.mock("@/lib/websocket", () => ({
  useWsConnected: () => true,
}));

vi.mock("@/lib/hooks/useApiQuery", () => ({
  useSiemQuery: (_key: string) => ({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/lib/timeRange", () => ({
  useTimeRange: () => ({
    queryParams: { preset: "24h" },
    range: "24h",
    setPreset: vi.fn(),
    setFrom: vi.fn(),
    setTo: vi.fn(),
  }),
}));

vi.mock("@/lib/buildQuery", () => ({
  buildQuery: () => "",
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("Dashboard SecurityKpis", () => {
  it("renders grid with 6 skeleton cards while loading", () => {
    const Wrapper = createQueryWrapper();
    const { container } = render(<SecurityKpis />, { wrapper: Wrapper });
    const grid = container.querySelector(".grid");
    expect(grid).toBeTruthy();
    const cards = grid!.querySelectorAll(".kpi-card");
    expect(cards.length).toBe(6);
  });
});

describe("Dashboard HostRiskPanel", () => {
  it("renders loading state", () => {
    const Wrapper = createQueryWrapper();
    render(<HostRiskPanel />, { wrapper: Wrapper });
    expect(screen.getByRole("status")).toBeDefined();
  });
});

describe("Dashboard AttackTimelines", () => {
  it("renders loading state", () => {
    const Wrapper = createQueryWrapper();
    render(<AttackTimelines />, { wrapper: Wrapper });
    expect(screen.getByRole("status")).toBeDefined();
  });
});

describe("Dashboard SeverityBreakdown", () => {
  it("renders loading state", () => {
    const Wrapper = createQueryWrapper();
    render(<SeverityBreakdown />, { wrapper: Wrapper });
    expect(screen.getByRole("status")).toBeDefined();
  });
});
