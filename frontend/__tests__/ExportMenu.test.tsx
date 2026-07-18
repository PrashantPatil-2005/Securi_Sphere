import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ExportMenu from "@/components/ExportMenu";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  API_URL: "http://localhost:8000",
}));

const mockToast = vi.fn();
vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

describe("ExportMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
    // Mock URL.createObjectURL and revokeObjectURL
    global.URL.createObjectURL = vi.fn(() => "blob:http://localhost/test");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("renders CSV, JSON, PDF buttons", () => {
    render(<ExportMenu resource="events" query="" />);
    expect(screen.getByText("csv")).toBeInTheDocument();
    expect(screen.getByText("json")).toBeInTheDocument();
    expect(screen.getByText("pdf")).toBeInTheDocument();
  });

  it("calls fetch with correct URL for CSV export", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["test"]),
    });
    render(<ExportMenu resource="alerts" query="?severity=high" />);
    fireEvent.click(screen.getByText("csv"));
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/alerts/export?severity=high&format=csv",
      { credentials: "include" }
    );
  });

  it("shows error toast on non-ok response", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 403,
    });
    render(<ExportMenu resource="events" query="" />);
    fireEvent.click(screen.getByText("json"));
    // Wait for async
    await new Promise((r) => setTimeout(r, 0));
    expect(mockToast).toHaveBeenCalledWith("error", "Export failed", "Insufficient permissions");
  });

  it("shows server error for non-403 failures", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
    });
    render(<ExportMenu resource="events" query="" />);
    fireEvent.click(screen.getByText("pdf"));
    await new Promise((r) => setTimeout(r, 0));
    expect(mockToast).toHaveBeenCalledWith("error", "Export failed", "Server returned 500");
  });

  it("builds URL with ? separator when query has no ?", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["test"]),
    });
    render(<ExportMenu resource="hosts" query="" />);
    fireEvent.click(screen.getByText("csv"));
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/hosts/export?format=csv"),
      expect.anything()
    );
  });

  it("builds URL with & separator when query has ?", async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["test"]),
    });
    render(<ExportMenu resource="hosts" query="?host=web01" />);
    fireEvent.click(screen.getByText("csv"));
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/hosts/export?host=web01&format=csv",
      { credentials: "include" }
    );
  });
});
