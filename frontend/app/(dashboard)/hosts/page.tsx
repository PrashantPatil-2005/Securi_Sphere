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

interface Host {
  id: string;
  name: string;
  hostname: string | null;
  status: string;
  os_info: string | null;
  last_seen: string | null;
  risk_score: number | null;
  alert_count: number | null;
}

export default function HostsPage() {
  const { queryParams } = useTimeRange();
  const [hosts, setHosts] = useState<Host[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState({ hostname: "", status: "", os_info: "", min_risk: "", max_risk: "" });
  const [enrollment, setEnrollment] = useState<{ token: string; install_command: string } | null>(null);
  const [newName, setNewName] = useState("");

  const load = useCallback(() => {
    const q = buildQuery(
      { page, page_size: pageSize, sort, ...filters, min_risk: filters.min_risk || undefined, max_risk: filters.max_risk || undefined },
      queryParams,
    );
    api<{ items?: Host[]; total?: number } | Host[]>(`/api/v1/hosts${q}`)
      .then((r) => {
        const { items, total: count } = parsePaginatedList(r);
        setHosts(items);
        setTotal(count);
      })
      .catch(console.error);
  }, [page, pageSize, sort, filters, queryParams]);

  useEffect(() => {
    load();
  }, [load]);

  async function addHost(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/hosts", { method: "POST", body: JSON.stringify({ name: newName }) });
    setNewName("");
    load();
  }

  async function enroll(host: Host) {
    const token = await api<{ token: string; install_command: string }>(`/api/v1/hosts/${host.id}/enrollment-token`, {
      method: "POST",
    });
    setEnrollment(token);
  }

  const inputCls = "px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm";

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Hosts</h1>
        <ExportMenu resource="hosts" query={buildQuery({ sort, ...filters }, queryParams)} />
      </div>
      <TimeRangeBar />
      <form onSubmit={addHost} className="flex gap-2 mb-4">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New host name"
          required
          className={`${inputCls} flex-1 max-w-xs`}
        />
        <button type="submit" className="px-4 py-1.5 bg-blue-600 rounded text-sm">
          Add Host
        </button>
      </form>
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          placeholder="Hostname"
          value={filters.hostname}
          onChange={(e) => setFilters({ ...filters, hostname: e.target.value })}
          className={inputCls}
        />
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className={inputCls}>
          <option value="">All statuses</option>
          {["online", "offline", "warning", "critical"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          placeholder="OS"
          value={filters.os_info}
          onChange={(e) => setFilters({ ...filters, os_info: e.target.value })}
          className={inputCls}
        />
        <input
          type="number"
          placeholder="Min risk"
          value={filters.min_risk}
          onChange={(e) => setFilters({ ...filters, min_risk: e.target.value })}
          className={`${inputCls} w-24`}
        />
        <input
          type="number"
          placeholder="Max risk"
          value={filters.max_risk}
          onChange={(e) => setFilters({ ...filters, max_risk: e.target.value })}
          className={`${inputCls} w-24`}
        />
        <SortSelect value={sort} onChange={setSort} />
      </div>
      <div className="space-y-2">
        {hosts.length === 0 && (
          <p className="text-gray-500 text-sm">No hosts registered yet. Add a host above, then click Enroll to install the agent.</p>
        )}
        {hosts.map((h) => (
          <div
            key={h.id}
            className="flex items-center justify-between p-3 bg-[var(--card)] border border-[var(--border)] rounded-lg"
          >
            <div>
              <span className="font-medium">{h.name}</span>
              <span className="text-xs text-gray-500 ml-2 capitalize">{h.status}</span>
              {h.risk_score != null && <span className="text-xs text-red-400 ml-2">Risk: {h.risk_score}</span>}
              {h.alert_count != null && h.alert_count > 0 && (
                <span className="text-xs text-yellow-400 ml-2">{h.alert_count} alerts</span>
              )}
              {h.last_seen && (
                <span className="text-xs text-gray-600 ml-2">Seen {new Date(h.last_seen).toLocaleString()}</span>
              )}
            </div>
            <button onClick={() => enroll(h)} className="text-sm px-3 py-1 bg-blue-600/20 text-blue-400 rounded">
              Enroll
            </button>
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
      {enrollment && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={() => setEnrollment(null)}>
          <div
            className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-6 max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-sm font-medium mb-2">Enrollment token (shown once)</p>
            <code className="block text-xs break-all mb-3">{enrollment.token}</code>
            <code className="block text-xs break-all bg-black/30 p-2 rounded">{enrollment.install_command}</code>
          </div>
        </div>
      )}
    </div>
  );
}
