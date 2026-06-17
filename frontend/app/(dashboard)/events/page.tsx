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

interface Event {
  id: string;
  host_id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}
interface Host {
  id: string;
  name: string;
}

export default function EventsPage() {
  const { queryParams } = useTimeRange();
  const [events, setEvents] = useState<Event[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [hosts, setHosts] = useState<Host[]>([]);
  const [filters, setFilters] = useState({
    severity: "",
    event_type: "",
    host_id: "",
    username: "",
    source_ip: "",
    service_name: "",
    status: "",
    q: "",
  });

  const load = useCallback(() => {
    const q = buildQuery({ page, page_size: pageSize, sort, ...filters }, queryParams);
    api<{ items?: Event[]; total?: number } | Event[]>(`/api/v1/events${q}`)
      .then((r) => {
        const { items, total: count } = parsePaginatedList(r);
        setEvents(items);
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
    if (msg.type === "new_event") load();
  });

  const exportQuery = buildQuery({ sort, ...filters }, queryParams);
  const inputCls = "px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm";

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Events</h1>
        <ExportMenu resource="events" query={exportQuery} />
      </div>
      <TimeRangeBar />
      <div className="grid md:grid-cols-4 gap-2 mb-4">
        <select value={filters.host_id} onChange={(e) => setFilters({ ...filters, host_id: e.target.value })} className={inputCls}>
          <option value="">All hosts</option>
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
        <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} className={inputCls}>
          <option value="">All severities</option>
          {["info", "low", "medium", "high", "critical"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          placeholder="Event type"
          value={filters.event_type}
          onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
          className={inputCls}
        />
        <input
          placeholder="Username"
          value={filters.username}
          onChange={(e) => setFilters({ ...filters, username: e.target.value })}
          className={inputCls}
        />
        <input
          placeholder="Source IP"
          value={filters.source_ip}
          onChange={(e) => setFilters({ ...filters, source_ip: e.target.value })}
          className={inputCls}
        />
        <input
          placeholder="Service"
          value={filters.service_name}
          onChange={(e) => setFilters({ ...filters, service_name: e.target.value })}
          className={inputCls}
        />
        <input
          placeholder="Status"
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className={inputCls}
        />
        <input placeholder="Keyword search" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} className={inputCls} />
        <SortSelect value={sort} onChange={setSort} />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-[var(--border)]">
            <th className="py-2">Time</th>
            <th className="py-2">Type</th>
            <th className="py-2">Severity</th>
            <th className="py-2">Description</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-b border-[var(--border)]/50">
              <td className="py-2 text-gray-400">{new Date(e.timestamp).toLocaleString()}</td>
              <td>{e.event_type}</td>
              <td>
                <span className={`severity-${e.severity}`}>{e.severity}</span>
              </td>
              <td className="text-gray-400 truncate max-w-md">{e.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
