"use client";

import { memo, useState } from "react";
import { usePaginatedResource, useHostsList, useAlertStatusMutation } from "@/lib/hooks/useApiQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { PageHeader } from "@/components/ui/Panel";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";

interface Alert {
  id: string;
  title: string;
  severity: string;
  status: string;
  description: string | null;
  created_at: string;
  confidence?: number;
}

const STATUSES = ["open", "investigating", "resolved", "closed"];

const AlertRow = memo(function AlertRow({
  alert,
  onStatus,
}: {
  alert: Alert;
  onStatus: (id: string, status: string) => void;
}) {
  return (
    <div className="alert-row">
      <div className="flex justify-between items-start gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <SeverityBadge severity={alert.severity} />
            <span className="font-medium text-sm">{alert.title}</span>
            <span className="text-[11px] text-[var(--muted)] capitalize">{alert.status}</span>
            {alert.confidence != null && (
              <span className="text-[11px] text-[var(--muted)]">{alert.confidence.toFixed(0)}% conf</span>
            )}
          </div>
          {alert.description && <p className="text-sm text-[var(--muted)] truncate">{alert.description}</p>}
          <p className="text-[11px] text-[var(--muted)] mt-1 tabular-nums">{new Date(alert.created_at).toLocaleString()}</p>
        </div>
        {alert.status === "open" && (
          <div className="flex gap-1 shrink-0">
            <button onClick={() => onStatus(alert.id, "investigating")} className="btn-ghost text-[11px] text-yellow-300">Investigate</button>
            <button onClick={() => onStatus(alert.id, "resolved")} className="btn-ghost text-[11px] text-green-300">Resolve</button>
          </div>
        )}
      </div>
    </div>
  );
});

export default function AlertsPage() {
  const { queryParams } = useTimeRange();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState({ status: "", severity: "", host_id: "", rule_name: "", q: "" });
  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedRule = useDebounce(filters.rule_name, 400);
  const queryFilters = { ...filters, q: debouncedQ, rule_name: debouncedRule };

  const { data: hosts = [] } = useHostsList();
  const { data, isLoading, isFetching } = usePaginatedResource<Alert>({
    endpoint: "/api/v1/alerts",
    queryKey: "alerts",
    page,
    pageSize,
    sort,
    filters: queryFilters,
  });
  const statusMutation = useAlertStatusMutation();

  const setStatus = (id: string, status: string) => statusMutation.mutate({ id, status });

  return (
    <div>
      <PageHeader title="Alerts" subtitle="Detection alerts with workflow status" action={<ExportMenu resource="alerts" query={buildQuery({ sort, ...queryFilters }, queryParams)} />} />
      <TimeRangeBar />
      <div className="filter-bar">
        <select value={filters.status} onChange={(e) => { setFilters({ ...filters, status: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filters.severity} onChange={(e) => { setFilters({ ...filters, severity: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All severities</option>
          {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filters.host_id} onChange={(e) => { setFilters({ ...filters, host_id: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All hosts</option>
          {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <input placeholder="Rule name" value={filters.rule_name} onChange={(e) => { setFilters({ ...filters, rule_name: e.target.value }); setPage(1); }} className="input-siem" />
        <input placeholder="Search" value={filters.q} onChange={(e) => { setFilters({ ...filters, q: e.target.value }); setPage(1); }} className="input-siem" />
        <SortSelect value={sort} onChange={(s) => { setSort(s); setPage(1); }} />
      </div>
      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState title="No alerts" description="Adjust filters or time range to see detection results." />
          ) : (
            (data?.items ?? []).map((a) => <AlertRow key={a.id} alert={a} onStatus={setStatus} />)
          )}
        </div>
      )}
      <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
    </div>
  );
}
