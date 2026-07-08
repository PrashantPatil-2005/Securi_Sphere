"use client";

import { memo, useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { Bell } from "lucide-react";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import { useKeyboardListNav } from "@/lib/hooks/useKeyboardListNav";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { usePaginatedResource, useHostsList, useAlertStatusMutation, useAlertBulkMutation } from "@/lib/hooks/useApiQuery";
import { useUser } from "@/lib/hooks/useUser";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import TimeRangeBar from "@/components/TimeRangeBar";
import { VirtualDataTable, type Column } from "@/components/VirtualDataTable";
import { AlertInvestigationPane } from "@/components/AlertInvestigationPane";
import { PageHeader } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";
import { Drawer } from "@/components/ui/Drawer";
import { FilterBar } from "@/components/ui/FilterBar";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { useToast } from "@/components/ui/Toast";

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
  const { toast } = useToast();
  const { queryParams } = useTimeRange();
  const listHeight = useMemo(
    () => (typeof window !== "undefined" ? Math.min(640, Math.max(320, window.innerHeight - 320)) : 480),
    [],
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [selectedId, setSelectedId] = useDeepLinkedSelection();
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [activeIndex, setActiveIndex] = useState(0);
  const [filters, setFilters] = useState({ status: "", severity: "", host_id: "", rule_name: "", q: "", mitre_technique_id: "" });
  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedRule = useDebounce(filters.rule_name, 400);
  const queryFilters = { ...filters, q: debouncedQ, rule_name: debouncedRule };

  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !searchParams.get("selected")) setFilters((prev) => ({ ...prev, q }));
    const mitre = searchParams.get("mitre_technique_id");
    if (mitre) setFilters((prev) => ({ ...prev, mitre_technique_id: mitre }));
  }, [searchParams]);

  const { data: hosts = [] } = useHostsList();
  const hostNames = useMemo(() => Object.fromEntries(hosts.map((h) => [h.id, h.name])), [hosts]);
  const { data: user } = useUser();
  const canMutate = user?.role.name === "admin" || user?.role.name === "analyst";
  const isDesktop = useMediaQuery("(min-width: 1024px)");
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

  const pageItems = useMemo(() => data?.items ?? [], [data?.items]);

  useEffect(() => {
    setActiveIndex(0);
  }, [page, pageSize, sort, queryFilters.status, queryFilters.severity, queryFilters.host_id, debouncedQ, debouncedRule]);

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
      bulkMutation.mutate(
        { alert_ids: ids, ...payload },
        {
          onSuccess: (res) => {
            toast("success", `Updated ${res.updated} alert(s)`);
            if (res.not_found?.length) {
              toast("warning", `${res.not_found.length} alert(s) not found`);
            }
          },
          onError: (e: Error) => toast("error", "Bulk update failed", e.message),
        },
      );
    },
    [bulkMutation, checkedIds, toast],
  );

  const bulkFromFocus = useCallback(
    (status: string) => {
      const alert = pageItems[activeIndex];
      if (!alert) return;
      if (checkedIds.size > 0) {
        runBulk({ status, ...(status === "investigating" && user?.id ? { assigned_to: user.id } : {}) });
      } else {
        setCheckedIds(new Set([alert.id]));
        bulkMutation.mutate(
          {
            alert_ids: [alert.id],
            status,
            ...(status === "investigating" && user?.id ? { assigned_to: user.id } : {}),
          },
          {
            onSuccess: () => toast("success", "Alert updated"),
            onError: (e: Error) => toast("error", "Update failed", e.message),
          },
        );
      }
    },
    [pageItems, activeIndex, checkedIds, runBulk, bulkMutation, user?.id, toast],
  );

  const setStatus = useCallback(
    (id: string, status: string) => statusMutation.mutate({ id, status }),
    [statusMutation],
  );

  useKeyboardListNav({
    enabled: pageItems.length > 0 && isDesktop,
    itemCount: pageItems.length,
    activeIndex,
    setActiveIndex,
    onActivate: (idx) => {
      const alert = pageItems[idx];
      if (alert) setSelectedId(alert.id);
    },
    onToggle: canMutate
      ? (idx) => {
          const alert = pageItems[idx];
          if (alert) toggleChecked(alert.id, !checkedIds.has(alert.id));
        }
      : undefined,
    onBulkResolve: canMutate ? () => bulkFromFocus("resolved") : undefined,
    onBulkInvestigate: canMutate ? () => bulkFromFocus("investigating") : undefined,
  });

  const columns = useMemo((): Column<Alert>[] => {
    const cols: Column<Alert>[] = [];
    if (canMutate) {
      cols.push({
        key: "select",
        header: "",
        width: "36px",
        render: (alert) => (
          <input
            type="checkbox"
            checked={checkedIds.has(alert.id)}
            aria-label={`Select ${alert.title}`}
            onChange={(e) => toggleChecked(alert.id, e.target.checked)}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      });
    }
    cols.push(
      { key: "severity", header: "Severity", width: "100px", render: (a) => <SeverityBadge severity={a.severity} /> },
      {
        key: "title",
        header: "Alert",
        width: "2fr",
        render: (a) => (
          <div className="min-w-0">
            <p className="font-medium truncate">{a.title}</p>
            {a.description && <p className="text-xs text-muted truncate">{a.description}</p>}
          </div>
        ),
      },
      { key: "status", header: "Status", width: "110px", render: (a) => <span className="capitalize text-xs">{a.status}</span> },
      { key: "host", header: "Host", width: "120px", render: (a) => <span className="text-xs truncate">{hostNames[a.host_id] ?? "—"}</span> },
      {
        key: "time",
        header: "Created",
        width: "140px",
        render: (a) => <span className="text-xs tabular-nums text-muted">{new Date(a.created_at).toLocaleString()}</span> },
    );
    return cols;
  }, [canMutate, checkedIds, toggleChecked, hostNames]);

  const secondaryFilterCount = [filters.host_id, filters.rule_name, filters.q].filter(Boolean).length;

  return (
    <div>
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Alerts
            <HelpTooltip content="Virtualized table with keyboard nav: j/k move, Enter open, Space select, i investigate, r resolve. Bulk actions when rows are checked." />
          </span>
        }
        subtitle="Detection alerts with case workspace triage"
        action={<ExportMenu resource="alerts" query={buildQuery({ sort, ...queryFilters }, queryParams)} />}
      />
      <TimeRangeBar />
      <FilterBar
        activeCount={secondaryFilterCount}
        more={
          <>
            <Select
              label="Host"
              value={filters.host_id}
              onChange={(e) => { setFilters({ ...filters, host_id: e.target.value }); setPage(1); }}
              className="min-w-[140px]"
            >
              <option value="">All hosts</option>
              {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </Select>
            <Input label="Rule name" placeholder="Rule name" value={filters.rule_name} onChange={(e) => { setFilters({ ...filters, rule_name: e.target.value }); setPage(1); }} />
            <Input label="Search" placeholder="Search title or description" value={filters.q} onChange={(e) => { setFilters({ ...filters, q: e.target.value }); setPage(1); }} />
          </>
        }
      >
        <Select
          label="Status"
          value={filters.status}
          onChange={(e) => { setFilters({ ...filters, status: e.target.value }); setPage(1); }}
          className="min-w-[130px]"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Select
          label="Severity"
          value={filters.severity}
          onChange={(e) => { setFilters({ ...filters, severity: e.target.value }); setPage(1); }}
          className="min-w-[130px]"
        >
          <option value="">All severities</option>
          {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <div className="space-y-1.5">
          <span className="block text-body font-medium text-foreground text-sm">Sort</span>
          <SortSelect value={sort} onChange={(s) => { setSort(s); setPage(1); }} />
        </div>
      </FilterBar>

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div>
          {canMutate && checkedIds.size > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 p-3 rounded-lg border border-border-subtle bg-[var(--sidebar-hover)]">
              <span className="text-sm text-[var(--muted)]">{checkedIds.size} selected</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "investigating" })}
              >
                Investigate
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "investigating", assigned_to: user?.id })}
              >
                Assign to me
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-success"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "resolved" })}
              >
                Resolve
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={bulkMutation.isPending}
                onClick={() => runBulk({ status: "closed" })}
              >
                Close
              </Button>
              <Button type="button" variant="ghost" size="sm" className="ml-auto" onClick={() => setCheckedIds(new Set())}>
                Clear
              </Button>
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
          {isDesktop && pageItems.length > 0 && (
            <p className="mb-2 text-[10px] text-muted">
              Keyboard: j/k navigate · Enter open · Space select · i investigate · r resolve
            </p>
          )}
          {isLoading ? (
            <TableSkeleton rows={6} />
          ) : isError ? (
            <QueryError onRetry={() => refetch()} />
          ) : (
            <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
              {(data?.items ?? []).length === 0 ? (
                <EmptyState
                  title="No alerts"
                  description="Run a simulation to generate demo alerts, or adjust filters and time range."
                  icon={<Bell className="w-10 h-10 opacity-40" />}
                  action="/simulation"
                  actionLabel="Run simulation"
                />
              ) : (
                <VirtualDataTable
                  rows={pageItems}
                  columns={columns}
                  rowKey={(alert) => alert.id}
                  height={listHeight}
                  rowHeight={52}
                  activeIndex={activeIndex}
                  selectedKey={selectedId ?? undefined}
                  onRowClick={(alert) => setSelectedId(alert.id)}
                  renderMobileCard={(alert) => (
                    <MobileAlertCard
                      alert={alert}
                      hostName={hostNames[alert.host_id]}
                      selected={selectedId === alert.id}
                      checked={checkedIds.has(alert.id)}
                      showCheckbox={!!canMutate}
                      onSelect={setSelectedId}
                      onToggle={toggleChecked}
                    />
                  )}
                />
              )}
            </div>
          )}
          <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
        </div>

        <div className="hidden lg:block lg:sticky lg:top-20">
          <AlertInvestigationPane
            alertId={selectedId}
            onStatus={setStatus}
            isUpdating={statusMutation.isPending}
          />
        </div>
      </div>

      <Drawer
        open={!!selectedId && !isDesktop}
        onClose={() => setSelectedId(null)}
        title="Alert investigation"
        side="bottom"
        className="lg:hidden"
      >
        {selectedId && (
          <AlertInvestigationPane
            alertId={selectedId}
            onStatus={setStatus}
            isUpdating={statusMutation.isPending}
          />
        )}
      </Drawer>
    </div>
  );
}

const MobileAlertCard = memo(function MobileAlertCard({
  alert,
  hostName,
  selected,
  checked,
  showCheckbox,
  onSelect,
  onToggle,
}: {
  alert: Alert;
  hostName?: string;
  selected: boolean;
  checked: boolean;
  showCheckbox: boolean;
  onSelect: (id: string) => void;
  onToggle: (id: string, next: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(alert.id)}
      className={`w-full text-left ${selected ? "ring-1 ring-accent/40 rounded-md p-1 -m-1" : ""}`}
    >
      <div className="flex gap-2 items-start">
        {showCheckbox && (
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => onToggle(alert.id, e.target.checked)}
            onClick={(e) => e.stopPropagation()}
            className="mt-1"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <SeverityBadge severity={alert.severity} />
            <span className="font-medium text-sm">{alert.title}</span>
          </div>
          <p className="text-xs text-muted capitalize">{alert.status}{hostName ? ` · ${hostName}` : ""}</p>
        </div>
      </div>
    </button>
  );
});
