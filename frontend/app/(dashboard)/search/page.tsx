"use client";

import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { PageHeader, EmptyState, Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface SiemResult {
  events: { id: string; event_type: string; severity: string; description: string | null; timestamp: string }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  total_events: number;
  total_alerts: number;
}

interface GlobalResult {
  query: string;
  hosts: { id: string; name: string; hostname: string | null; status: string; ip: string | null }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  events: { id: string; event_type: string; description: string | null; severity: string }[];
  users: { id: string; email: string; full_name: string | null }[];
}

const EXAMPLES = ["host:web01 severity:critical", "event_type:failed_login date:last_30_days", "username:root"];

export default function SearchPage() {
  const searchParams = useSearchParams();
  const { queryParams } = useTimeRange();
  const [mode, setMode] = useState<"siem" | "global">("siem");
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const debouncedQ = useDebounce(q, 400);

  useEffect(() => {
    const param = searchParams.get("q");
    if (param) {
      setQ(param);
      setSubmitted(param);
      setMode("global");
    }
  }, [searchParams]);

  const { data: siem, isLoading: siemLoading, isFetching: siemFetching } = useQuery({
    queryKey: ["search", "siem", submitted, queryParams],
    queryFn: async () => {
      const query = buildQuery({ q: submitted }, queryParams);
      return api<SiemResult>(`/api/v1/search/siem${query}`);
    },
    enabled: mode === "siem" && submitted.length > 0,
    staleTime: 60_000,
  });

  const { data: global, isLoading: globalLoading, isFetching: globalFetching } = useQuery({
    queryKey: ["search", "global", submitted, queryParams],
    queryFn: async () => {
      const query = buildQuery({ q: submitted }, queryParams);
      return api<GlobalResult>(`/api/v1/search${query}`);
    },
    enabled: mode === "global" && submitted.length > 0,
    staleTime: 60_000,
  });

  const { data: saved = [] } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api<{ id: string; name: string; query: string }[]>("/api/v1/saved-searches"),
    staleTime: 120_000,
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!debouncedQ.trim()) return;
    setSubmitted(debouncedQ.trim());
  }

  const isLoading = mode === "siem" ? siemLoading : globalLoading;
  const isFetching = mode === "siem" ? siemFetching : globalFetching;

  return (
    <div>
      <PageHeader
        title="Search"
        subtitle={mode === "siem" ? "SIEM query language — host:web01 severity:critical" : "Global search across hosts, alerts, and events"}
      />
      <TimeRangeBar />
      <div className="flex gap-2 mb-4">
        <button type="button" onClick={() => setMode("siem")} className={mode === "siem" ? "btn-primary" : "btn-ghost"}>SIEM</button>
        <button type="button" onClick={() => setMode("global")} className={mode === "global" ? "btn-primary" : "btn-ghost"}>Global</button>
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={mode === "siem" ? "host:web01 severity:critical" : "Search keyword…"}
          className="input-siem flex-1 font-mono"
        />
        <button type="submit" className="btn-primary">Run</button>
      </form>
      {mode === "siem" && (
        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => { setQ(ex); setSubmitted(ex); }} className="btn-ghost text-xs">{ex}</button>
          ))}
        </div>
      )}
      {saved.length > 0 && mode === "siem" && (
        <div className="flex flex-wrap gap-2 mb-4">
          {saved.map((s) => (
            <button key={s.id} type="button" onClick={() => { setQ(s.query); setSubmitted(s.query); }} className="btn-ghost text-xs">{s.name}</button>
          ))}
        </div>
      )}
      {isLoading && <TableSkeleton rows={4} />}
      {mode === "siem" && siem && (
        <div className={`space-y-2 ${isFetching ? "opacity-60" : ""}`}>
          <p className="text-sm text-muted">{siem.total_events} events · {siem.total_alerts} alerts</p>
          {siem.events.length === 0 && siem.alerts.length === 0 && (
            <EmptyState title="No results" description="Try broadening your query or time range." />
          )}
          {siem.events.map((ev) => (
            <div key={ev.id} className="panel p-3 text-sm font-mono">{new Date(ev.timestamp).toLocaleString()} · {ev.event_type} · {ev.description}</div>
          ))}
          {siem.alerts.map((a) => (
            <div key={a.id} className="panel p-3 text-sm">[{a.severity}] {a.title}</div>
          ))}
        </div>
      )}
      {mode === "global" && global && (
        <div className={`space-y-4 ${isFetching ? "opacity-60" : ""}`}>
          {global.hosts.length === 0 && global.alerts.length === 0 && global.events.length === 0 && (
            <EmptyState title="No results" description={`Nothing matched "${global.query}"`} />
          )}
          {global.hosts.length > 0 && (
            <Panel title={`Hosts (${global.hosts.length})`}>
              <div className="space-y-2">
                {global.hosts.map((h) => (
                  <div key={h.id} className="text-sm">{h.name} · {h.status} · {h.ip ?? "—"}</div>
                ))}
              </div>
            </Panel>
          )}
          {global.alerts.length > 0 && (
            <Panel title={`Alerts (${global.alerts.length})`}>
              <div className="space-y-2">
                {global.alerts.map((a) => (
                  <div key={a.id} className="text-sm">[{a.severity}] {a.title} · {a.status}</div>
                ))}
              </div>
            </Panel>
          )}
          {global.events.length > 0 && (
            <Panel title={`Events (${global.events.length})`}>
              <div className="space-y-2">
                {global.events.map((e) => (
                  <div key={e.id} className="text-sm font-mono">{e.event_type} · {e.description}</div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}
