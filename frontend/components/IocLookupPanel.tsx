"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface VtResult {
  ioc: string;
  backend: string;
  found?: boolean;
  malicious?: number;
  suspicious?: number;
  harmless?: number;
  reputation?: number;
  link?: string;
  message?: string;
  error?: string;
}

export function IocLookupPanel({ value }: { value: string | null | undefined }) {
  const [query, setQuery] = useState(value ?? "");
  const [submitted, setSubmitted] = useState<string | null>(value ?? null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ioc", submitted],
    queryFn: () => api<VtResult>(`/api/v1/ioc/lookup?q=${encodeURIComponent(submitted!)}`),
    enabled: !!submitted && submitted.length >= 3,
    staleTime: 300_000,
    retry: false,
  });

  return (
    <div className="p-3 rounded-lg border border-border-subtle space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">IOC lookup (VirusTotal)</p>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim().length >= 3) setSubmitted(query.trim());
        }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="IP, domain, or hash"
          className="input-siem flex-1 text-sm font-mono"
        />
        <button type="submit" className="btn-ghost text-xs">Lookup</button>
      </form>
      {isLoading && <p className="text-sm text-muted">Checking…</p>}
      {isError && <p className="text-sm text-danger">Lookup failed</p>}
      {data && data.backend === "none" && (
        <p className="text-sm text-warning">IOC enrichment disabled — set VIRUSTOTAL_API_KEY on the server.</p>
      )}
      {data && data.backend !== "none" && (
        <div className="text-sm space-y-1">
          {data.message && <p className="text-muted">{data.message}</p>}
          {data.error && <p className="text-danger">{data.error}</p>}
          {data.found && (
            <>
              <p>
                Malicious: <span className="text-danger font-semibold">{data.malicious ?? 0}</span>
                {" · "}Suspicious: {data.suspicious ?? 0}
                {" · "}Harmless: {data.harmless ?? 0}
              </p>
              {data.reputation != null && <p className="text-muted">Reputation: {data.reputation}</p>}
              {data.link && (
                <a href={data.link} target="_blank" rel="noreferrer" className="text-accent text-xs hover:underline">
                  Open in VirusTotal
                </a>
              )}
            </>
          )}
          {data.found === false && <p className="text-muted">No VirusTotal report for this IOC.</p>}
        </div>
      )}
    </div>
  );
}
