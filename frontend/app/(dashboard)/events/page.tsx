"use client";

import { useMemo, useState } from "react";
import { usePaginatedResource, useHostsList } from "@/lib/hooks/useApiQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { VirtualDataTable, type Column } from "@/components/VirtualDataTable";
import { PageHeader } from "@/components/ui/Panel";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface Event {
  id: string;
  host_id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}

const columns: Column<Event>[] = [
  {
    key: "time",
    header: "Time",
    width: "160px",
    render: (e) => <span className="text-[var(--muted)] tabular-nums">{new Date(e.timestamp).toLocaleString()}</span>,
  },
  {
    key: "type",
    header: "Type",
    width: "140px",
    render: (e) => <span className="font-mono text-xs">{e.event_type}</span>,
  },
  {
    key: "severity",
    header: "Severity",
    width: "90px",
    render: (e) => <SeverityBadge severity={e.severity} />,
  },
  {
    key: "desc",
    header: "Description",
    render: (e) => <span className="text-[var(--muted)]">{e.description}</span>,
  },
];

export default function EventsPage() {
  const { queryParams } = useTimeRange();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
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

  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedType = useDebounce(filters.event_type, 400);
  const debouncedFilters = useMemo(
    () => ({ ...filters, q: debouncedQ, event_type: debouncedType }),
    [filters, debouncedQ, debouncedType],
  );

  const { data: hosts = [] } = useHostsList();
  const { data, isLoading, isFetching } = usePaginatedResource<Event>({
    endpoint: "/api/v1/events",
    queryKey: "events",
    page,
    pageSize,
    sort,
    filters: debouncedFilters,
  });

  const exportQuery = buildQuery({ sort, ...debouncedFilters }, queryParams);

  return (
    <div>
      <PageHeader title="Events" subtitle="Security event log with server-side pagination" action={<ExportMenu resource="events" query={exportQuery} />} />
      <TimeRangeBar />
      <div className="filter-bar grid md:grid-cols-4 gap-2">
        <select value={filters.host_id} onChange={(e) => { setFilters({ ...filters, host_id: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All hosts</option>
          {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={filters.severity} onChange={(e) => { setFilters({ ...filters, severity: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All severities</option>
          {["info", "low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input placeholder="Event type" value={filters.event_type} onChange={(e) => { setFilters({ ...filters, event_type: e.target.value }); setPage(1); }} className="input-siem" />
        <input placeholder="Keyword" value={filters.q} onChange={(e) => { setFilters({ ...filters, q: e.target.value }); setPage(1); }} className="input-siem" />
        <SortSelect value={sort} onChange={(s) => { setSort(s); setPage(1); }} />
      </div>
      {isLoading ? (
        <TableSkeleton />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          <VirtualDataTable rows={data?.items ?? []} columns={columns} rowKey={(e) => e.id} />
        </div>
      )}
      <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
    </div>
  );
}
