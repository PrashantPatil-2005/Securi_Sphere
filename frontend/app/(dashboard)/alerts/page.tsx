"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { useWebSocket } from "@/lib/websocket";

interface Alert {
  id: string;
  title: string;
  severity: string;
  status: string;
  description: string | null;
  created_at: string;
  confidence?: number;
}
interface Host {
  id: string;
  name: string;
}

const STATUSES = ["open", "investigating", "resolved", "closed"];

export default function AlertsPage() {
  const { queryParams } = useTimeRange();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [hosts, setHosts] = useState<Host[]>([]);
  const [filters, setFilters] = useState({ status: "", severity: "", host_id: "", rule_name: "", q: "" });

  const load = useCallback(() => {
    const q = buildQuery({ page, page_size: pageSize, sort, ...filters }, queryParams);
    api<{ items?: Alert[]; total?: number } | Alert[]>(`/api/v1/alerts${q}`)
      .then((r) => {
        const { items, total: count } = parsePaginatedList(r);
        setAlerts(items);
        setTotal(count);
      })
      .catch(console.error);
  }, [page, pageSize, sort, filters, queryParams]);

  useEffect(() => {
    api<{ items?: Host[] } | Host[]>("/api/v1/hosts?page_size=500")
      .then((r) => setHosts(parsePaginatedList(r).items))
      .catch(console.error);
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  useWebSocket((msg) => {
    if (msg.type === "new_alert" || msg.type === "alert_resolved") load();
  });

  async function setStatus(id: string, status: string) {
    await api(`/api/v1/alerts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    load();
  }

  const inputCls = "px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm";

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Alerts</h1>
        <ExportMenu resource="alerts" query={buildQuery({ sort, ...filters }, queryParams)} />
      </div>
      <TimeRangeBar />
      <div className="flex flex-wrap gap-2 mb-4">
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className={inputCls}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} className={inputCls}>
          <option value="">All severities</option>
          {["low", "medium", "high", "critical"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={filters.host_id} onChange={(e) => setFilters({ ...filters, host_id: e.target.value })} className={inputCls}>
          <option value="">All hosts</option>
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
        <input
          placeholder="Rule name"
          value={filters.rule_name}
          onChange={(e) => setFilters({ ...filters, rule_name: e.target.value })}
          className={inputCls}
        />
        <input placeholder="Search" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} className={inputCls} />
        <SortSelect value={sort} onChange={setSort} />
      </div>
      <div className="space-y-3">
        {alerts.map((a) => (
          <div key={a.id} className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <div className="flex justify-between items-start gap-4">
              <div>
                <span className={`text-xs uppercase font-bold mr-2 severity-${a.severity}`}>{a.severity}</span>
                <span className="font-medium">{a.title}</span>
                <span className="text-xs text-gray-500 ml-2 capitalize">{a.status}</span>
                {a.confidence != null && <span className="text-xs text-gray-500 ml-2">{a.confidence.toFixed(0)}% conf</span>}
                <p className="text-sm text-gray-400 mt-1">{a.description}</p>
                <p className="text-xs text-gray-500 mt-1">{new Date(a.created_at).toLocaleString()}</p>
              </div>
              {a.status === "open" && (
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => setStatus(a.id, "investigating")}
                    className="text-xs px-2 py-1 bg-yellow-900/30 text-yellow-400 rounded"
                  >
                    Investigate
                  </button>
                  <button onClick={() => setStatus(a.id, "resolved")} className="text-xs px-2 py-1 bg-green-900/30 text-green-400 rounded">
                    Resolve
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <PaginationBar
        page={page}
        pageSize={pageSize}
        total={total}
        onPage={setPage}
        onPageSize={(s) => {
          setPageSize(s);
          setPage(1);
        }}
      />
    </div>
  );
}
