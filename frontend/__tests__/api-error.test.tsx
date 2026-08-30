import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useState } from "react";

function DataFetcher({ url }: { url: string }) {
  const [data, setData] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async (retries = 0) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json.message);
    } catch (err: any) {
      if (retries < 1) {
        setLoading(false);
        await fetchData(retries + 1);
        return;
      }
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={() => fetchData()}>Load</button>
      {loading && <p>Loading...</p>}
      {error && <p role="alert">{error}</p>}
      {data && <p>{data}</p>}
    </div>
  );
}

describe("API error handling", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("displays error message on fetch failure", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
    globalThis.fetch = mockFetch;

    render(<DataFetcher url="http://localhost:3000/api/test" />);
    screen.getByRole("button", { name: /load/i }).click();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Network error");
    });
  });

  it("displays error message on 500 response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);
    globalThis.fetch = mockFetch;

    render(<DataFetcher url="http://localhost:3000/api/test" />);
    screen.getByRole("button", { name: /load/i }).click();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("HTTP 500");
    });
  });

  it("retries on transient failure", async () => {
    const mockFetch = vi
      .fn()
      .mockRejectedValueOnce(new Error("ECONNRESET"))
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: "Success" }),
      } as Response);
    globalThis.fetch = mockFetch;

    render(<DataFetcher url="http://localhost:3000/api/test" />);
    screen.getByRole("button", { name: /load/i }).click();

    await waitFor(() => {
      expect(screen.getByText("Success")).toBeInTheDocument();
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
