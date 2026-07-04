"use client";

import { useMemo, useState } from "react";
import { useCursorPaginatedResource, useHostsList } from "@/lib/hooks/useApiQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { rowKeyById } from "@/lib/rowKey";
import ExportMenu from "@/components/ExportMenu";
import CursorPaginationBar from "@/components/CursorPaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { VirtualDataTable, type Column } from "@/components/VirtualDataTable";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
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
  const {
    items,
    total,
    isLoading,
    isFetching,
    isError,
    refetch,
    page,
    hasMore,
    goNext,
    goPrev,
  } = useCursorPaginatedResource<Event>({
    endpoint: "/api/v1/events",
    queryKey: "events",
    pageSize,
    sort,
    filters: debouncedFilters,
  });

  const exportQuery = buildQuery({ sort, ...debouncedFilters }, queryParams);

  return (
    <div>
      <PageHeader title="Events" subtitle="Security event log with keyset pagination" action={<ExportMenu resource="events" query={exportQuery} />} />
      <TimeRangeBar />
      <div className="filter-bar grid md:grid-cols-4 gap-2">
        <select value={filters.host_id} onChange={(e) => setFilters({ ...filters, host_id: e.target.value })} className="input-siem">
          <option value="">All hosts</option>
          {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })} className="input-siem">
          <option value="">All severities</option>
          {["info", "low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input placeholder="Event type" value={filters.event_type} onChange={(e) => setFilters({ ...filters, event_type: e.target.value })} className="input-siem" />
        <input placeholder="Keyword" value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} className="input-siem" />
        <SortSelect value={sort} onChange={setSort} />
      </div>
      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title="No events" description="Adjust filters or enroll an agent to ingest events." />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          <VirtualDataTable rows={items} columns={columns} rowKey={rowKeyById} />
        </div>
      )}
      <CursorPaginationBar
        page={page}
        pageSize={pageSize}
        total={total}
        itemCount={items.length}
        hasMore={hasMore}
        onPrev={goPrev}
        onNext={goNext}
        onPageSize={setPageSize}
      />
    </div>
  );
}
