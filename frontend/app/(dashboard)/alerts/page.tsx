"use client";

import { memo, useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { usePaginatedResource, useHostsList, useAlertStatusMutation, useAlertBulkMutation } from "@/lib/hooks/useApiQuery";
import { useUser } from "@/lib/hooks/useUser";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { rowKeyById } from "@/lib/rowKey";
import { cn } from "@/lib/utils/cn";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { VirtualList } from "@/components/VirtualList";
import { AlertInvestigationPane } from "@/components/AlertInvestigationPane";
import { PageHeader } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";

interface Alert {
  id: string;
  host_id: string;
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
  selected,
  checked,
  showCheckbox,
  onSelect,
  onToggle,
}: {
  alert: Alert;
  selected: boolean;
  checked: boolean;
  showCheckbox: boolean;
  onSelect: (id: string) => void;
  onToggle: (id: string, next: boolean) => void;
}) {
  return (
    <div
      className={cn(
        "alert-row w-full text-left transition-colors flex gap-3 items-start",
        selected && "ring-1 ring-accent/40 bg-accent/5",
      )}
    >
      {showCheckbox && (
        <input
          type="checkbox"
          checked={checked}
          aria-label={`Select alert ${alert.title}`}
          onChange={(e) => onToggle(alert.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          className="mt-3 shrink-0"
        />
      )}
      <button type="button" onClick={() => onSelect(alert.id)} className="flex-1 min-w-0 text-left">
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
        </div>
      </button>
    </div>
  );
});

export default function AlertsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={6} />}>
      <AlertsPageContent />
    </Suspense>
  );
}

function AlertsPageContent() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { queryParams } = useTimeRange();
  const listHeight = useMemo(
    () => (typeof window !== "undefined" ? Math.min(640, Math.max(320, window.innerHeight - 320)) : 480),
    [],
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("selected"));
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({ status: "", severity: "", host_id: "", rule_name: "", q: "" });
  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedRule = useDebounce(filters.rule_name, 400);
  const queryFilters = { ...filters, q: debouncedQ, rule_name: debouncedRule };

  useEffect(() => {
    const id = searchParams.get("selected");
    if (id) setSelectedId(id);
    const q = searchParams.get("q");
    if (q && !searchParams.get("selected")) setFilters((prev) => ({ ...prev, q }));
  }, [searchParams]);

  const { data: hosts = [] } = useHostsList();
  const { data: user } = useUser();
  const canMutate = user?.role.name === "admin" || user?.role.name === "analyst";
  const { data, isLoading, isFetching, isError, refetch } = usePaginatedResource<Alert>({
    endpoint: "/api/v1/alerts",
    queryKey: "alerts",
    page,
    pageSize,
    sort,
    filters: queryFilters,
  });
  const statusMutation = useAlertStatusMutation(() => {
    queryClient.invalidateQueries({ queryKey: ["alerts", "investigation", selectedId] });
  });
  const bulkMutation = useAlertBulkMutation(() => {
    setCheckedIds(new Set());
    queryClient.invalidateQueries({ queryKey: ["alerts", "investigation", selectedId] });
  });

  const pageItems = data?.items ?? [];
  const allOnPageSelected = pageItems.length > 0 && pageItems.every((a) => checkedIds.has(a.id));
  const someOnPageSelected = pageItems.some((a) => checkedIds.has(a.id));

  const toggleChecked = useCallback((id: string, next: boolean) => {
    setCheckedIds((prev) => {
      const copy = new Set(prev);
      if (next) copy.add(id);
      else copy.delete(id);
      return copy;
    });
  }, []);

  const toggleAllOnPage = useCallback(() => {
    setCheckedIds((prev) => {
      const copy = new Set(prev);
      if (allOnPageSelected) {
        pageItems.forEach((a) => copy.delete(a.id));
      } else {
        pageItems.forEach((a) => copy.add(a.id));
      }
      return copy;
    });
  }, [allOnPageSelected, pageItems]);

  const runBulk = useCallback(
    (payload: { status?: string; assigned_to?: string }) => {
      const ids = Array.from(checkedIds);
      if (!ids.length) return;
      bulkMutation.mutate({ alert_ids: ids, ...payload });
    },
    [bulkMutation, checkedIds],
  );

  const setStatus = useCallback(
    (id: string, status: string) => statusMutation.mutate({ id, status }),
    [statusMutation],
  );

  const renderAlert = useCallback(
    (alert: Alert) => (
      <AlertRow
        alert={alert}
        selected={selectedId === alert.id}
        checked={checkedIds.has(alert.id)}
        showCheckbox={!!canMutate}
        onSelect={setSelectedId}
        onToggle={toggleChecked}
      />
    ),
    [selectedId, checkedIds, toggleChecked, canMutate],
  );

  return (
    <div>
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Alerts
            <HelpTooltip content="Select an alert to open the investigation pane. Use bulk actions or Ask AI for triage guidance and auto-generated summaries." />
          </span>
        }
        subtitle="Detection alerts with investigation workspace"
        action={<ExportMenu resource="alerts" query={buildQuery({ sort, ...queryFilters }, queryParams)} />}
      />
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

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div>
          {canMutate && checkedIds.size > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 p-3 rounded-lg border border-border-subtle bg-[var(--sidebar-hover)]">
              <span className="text-sm text-[var(--muted)]">{checkedIds.size} selected</span>
              <button
                type="button"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "investigating", assigned_to: user?.id })}
                className="btn-ghost text-xs"
              >
                Assign to me
              </button>
              <button
                type="button"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "resolved" })}
                className="btn-ghost text-xs text-success"
              >
                Resolve
              </button>
              <button
                type="button"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "closed" })}
                className="btn-ghost text-xs"
              >
                Close
              </button>
              <button type="button" onClick={() => setCheckedIds(new Set())} className="btn-ghost text-xs ml-auto">
                Clear
              </button>
            </div>
          )}
          {canMutate && pageItems.length > 0 && (
            <label className="flex items-center gap-2 mb-2 text-xs text-[var(--muted)] cursor-pointer">
              <input
                type="checkbox"
                checked={allOnPageSelected}
                ref={(el) => {
                  if (el) el.indeterminate = someOnPageSelected && !allOnPageSelected;
                }}
                onChange={toggleAllOnPage}
              />
              Select all on page
            </label>
          )}
          {isLoading ? (
            <TableSkeleton rows={6} />
          ) : isError ? (
            <QueryError onRetry={() => refetch()} />
          ) : (
            <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
              {(data?.items ?? []).length === 0 ? (
                <EmptyState title="No alerts" description="Adjust filters or time range to see detection results." />
              ) : (
                <VirtualList
                  items={data?.items ?? []}
                  rowKey={rowKeyById}
                  renderItem={renderAlert}
                  height={listHeight}
                  estimateSize={88}
                  emptyMessage="No alerts"
                />
              )}
            </div>
          )}
          <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
        </div>

        <div className="lg:sticky lg:top-20">
          <AlertInvestigationPane
            alertId={selectedId}
            onStatus={setStatus}
            isUpdating={statusMutation.isPending}
          />
        </div>
      </div>
    </div>
  );
}
