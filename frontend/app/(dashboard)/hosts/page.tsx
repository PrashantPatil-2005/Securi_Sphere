"use client";

import { memo, useCallback, useMemo, useState } from "react";
import { usePaginatedResource } from "@/lib/hooks/useApiQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { VirtualDataTable, type Column } from "@/components/VirtualDataTable";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";

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

const statusTone: Record<string, string> = {
  online: "text-[var(--success)]",
  offline: "text-[var(--muted)]",
  warning: "text-[var(--warning)]",
  critical: "text-[var(--danger)]",
};

const HostActions = memo(function HostActions({ host, onEnroll }: { host: Host; onEnroll: (h: Host) => void }) {
  return (
    <button onClick={() => onEnroll(host)} className="btn-ghost text-xs">Enroll</button>
  );
});

export default function HostsPage() {
  const { queryParams } = useTimeRange();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState({ hostname: "", status: "", os_info: "", min_risk: "", max_risk: "" });
  const debouncedHostname = useDebounce(filters.hostname, 400);
  const queryFilters = useMemo(
    () => ({
      ...filters,
      hostname: debouncedHostname,
      min_risk: filters.min_risk || undefined,
      max_risk: filters.max_risk || undefined,
    }),
    [filters, debouncedHostname],
  );
  const [enrollment, setEnrollment] = useState<{ token: string; install_command: string } | null>(null);
  const [newName, setNewName] = useState("");

  const { data, isLoading, isFetching, refetch } = usePaginatedResource<Host>({
    endpoint: "/api/v1/hosts",
    queryKey: "hosts",
    page,
    pageSize,
    sort,
    filters: queryFilters,
  });

  const enroll = useCallback(async (host: Host) => {
    const token = await api<{ token: string; install_command: string }>(`/api/v1/hosts/${host.id}/enrollment-token`, { method: "POST" });
    setEnrollment(token);
  }, []);

  const columns: Column<Host>[] = useMemo(
    () => [
      { key: "name", header: "Host", width: "140px", render: (h) => <span className="font-medium">{h.name}</span> },
      {
        key: "status",
        header: "Status",
        width: "90px",
        render: (h) => <span className={`capitalize text-xs ${statusTone[h.status] || ""}`}>{h.status}</span>,
      },
      {
        key: "risk",
        header: "Risk",
        width: "70px",
        render: (h) => <span className="tabular-nums text-[var(--danger)]">{h.risk_score ?? "—"}</span>,
      },
      {
        key: "alerts",
        header: "Alerts",
        width: "70px",
        render: (h) => <span className="tabular-nums">{h.alert_count ?? 0}</span>,
      },
      {
        key: "seen",
        header: "Last seen",
        width: "160px",
        render: (h) => (
          <span className="text-[var(--muted)] text-xs tabular-nums">
            {h.last_seen ? new Date(h.last_seen).toLocaleString() : "—"}
          </span>
        ),
      },
      {
        key: "actions",
        header: "",
        width: "80px",
        render: (h) => <HostActions host={h} onEnroll={enroll} />,
      },
    ],
    [enroll],
  );

  async function addHost(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/hosts", { method: "POST", body: JSON.stringify({ name: newName }) });
    setNewName("");
    refetch();
  }

  return (
    <div>
      <PageHeader title="Hosts" subtitle="Managed endpoints and agent enrollment" action={<ExportMenu resource="hosts" query={buildQuery({ sort, ...queryFilters }, queryParams)} />} />
      <TimeRangeBar />
      <form onSubmit={addHost} className="flex gap-2 mb-4">
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New host name" required className="input-siem max-w-xs" />
        <button type="submit" className="btn-primary">Add host</button>
      </form>
      <div className="filter-bar">
        <input placeholder="Hostname" value={filters.hostname} onChange={(e) => { setFilters({ ...filters, hostname: e.target.value }); setPage(1); }} className="input-siem" />
        <select value={filters.status} onChange={(e) => { setFilters({ ...filters, status: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All statuses</option>
          {["online", "offline", "warning", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <SortSelect value={sort} onChange={(s) => { setSort(s); setPage(1); }} />
      </div>
      {isLoading ? (
        <TableSkeleton />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState title="No hosts" description="Register a host and enroll an agent to begin monitoring." />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          <VirtualDataTable rows={data?.items ?? []} columns={columns} rowKey={(h) => h.id} />
        </div>
      )}
      <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
      {enrollment && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" onClick={() => setEnrollment(null)}>
          <div className="panel max-w-lg w-full p-5" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-medium mb-2">Enrollment token</p>
            <code className="block text-xs break-all mb-3 font-mono text-[var(--muted)]">{enrollment.token}</code>
            <code className="block text-xs break-all bg-[#0a1018] p-2 rounded font-mono">{enrollment.install_command}</code>
          </div>
        </div>
      )}
    </div>
  );
}
