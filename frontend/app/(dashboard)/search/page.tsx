"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";

interface SearchResult {
  query: string; exact: boolean;
  hosts: { id: string; name: string; hostname: string | null; status: string; ip: string | null }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  events: { id: string; event_type: string; description: string | null; severity: string }[];
  users: { id: string; email: string; full_name: string | null }[];
}

export default function SearchPage() {
  const { queryParams } = useTimeRange();
  const [q, setQ] = useState("");
  const [exact, setExact] = useState(false);
  const [results, setResults] = useState<SearchResult | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    const query = buildQuery({ q: q.trim(), exact }, queryParams);
    setResults(await api<SearchResult>(`/api/v1/search${query}`));
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Global Search</h1>
      <TimeRangeBar />
      <form onSubmit={handleSearch} className="flex flex-wrap gap-2 mb-8">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search events, hosts, alerts, IPs, users..."
          className="flex-1 min-w-[200px] px-4 py-2 bg-black/30 border border-[var(--border)] rounded" />
        <label className="flex items-center gap-2 text-sm text-gray-400 px-2">
          <input type="checkbox" checked={exact} onChange={(e) => setExact(e.target.checked)} /> Exact match
        </label>
        <button type="submit" className="px-6 py-2 bg-blue-600 rounded">Search</button>
      </form>
      {results && (
        <div className="space-y-8">
          {results.hosts.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3">Hosts ({results.hosts.length})</h2>
              {results.hosts.map((h) => (
                <div key={h.id} className="p-3 border border-[var(--border)] rounded text-sm mb-2">{h.name} · {h.status} · {h.ip || "no ip"}</div>
              ))}
            </section>
          )}
          {results.alerts.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3">Alerts ({results.alerts.length})</h2>
              {results.alerts.map((a) => (
                <div key={a.id} className="p-3 border border-[var(--border)] rounded text-sm mb-2">[{a.severity}] {a.title} ({a.status})</div>
              ))}
            </section>
          )}
          {results.events.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3">Events ({results.events.length})</h2>
              {results.events.map((ev) => (
                <div key={ev.id} className="p-3 border border-[var(--border)] rounded text-sm mb-2">{ev.event_type}: {ev.description}</div>
              ))}
            </section>
          )}
          {results.users.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3">Users ({results.users.length})</h2>
              {results.users.map((u) => (
                <div key={u.id} className="p-3 border border-[var(--border)] rounded text-sm mb-2">{u.email} · {u.full_name || ""}</div>
              ))}
            </section>
          )}
        </div>
      )}
    </div>
  );
}
