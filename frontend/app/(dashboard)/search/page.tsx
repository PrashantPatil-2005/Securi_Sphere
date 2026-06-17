"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

interface SearchResult {
  query: string;
  hosts: { id: string; name: string; hostname: string | null; status: string }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  events: { id: string; event_type: string; description: string | null; severity: string }[];
}

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    const data = await api<SearchResult>(`/api/v1/search?q=${encodeURIComponent(q)}`);
    setResults(data);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Search</h1>
      <form onSubmit={handleSearch} className="flex gap-2 mb-8">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search hosts, alerts, events..."
          className="flex-1 px-4 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
        <button type="submit" className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded">Search</button>
      </form>
      {results && (
        <div className="space-y-8">
          <section>
            <h2 className="text-lg font-semibold mb-3">Hosts ({results.hosts.length})</h2>
            {results.hosts.map((h) => (
              <div key={h.id} className="py-2 border-b border-[var(--border)]/50 text-sm">
                {h.name} — {h.hostname || "pending"} ({h.status})
              </div>
            ))}
          </section>
          <section>
            <h2 className="text-lg font-semibold mb-3">Alerts ({results.alerts.length})</h2>
            {results.alerts.map((a) => (
              <div key={a.id} className="py-2 border-b border-[var(--border)]/50 text-sm">
                [{a.severity}] {a.title} ({a.status})
              </div>
            ))}
          </section>
          <section>
            <h2 className="text-lg font-semibold mb-3">Events ({results.events.length})</h2>
            {results.events.map((e) => (
              <div key={e.id} className="py-2 border-b border-[var(--border)]/50 text-sm">
                {e.event_type}: {e.description}
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
