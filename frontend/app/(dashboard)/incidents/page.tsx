"use client";

import { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { AlertTriangle } from "lucide-react";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import { useKeyboardListNav } from "@/lib/hooks/useKeyboardListNav";
import { useSearchParams } from "next/navigation";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useUser } from "@/lib/hooks/useUser";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { useToast } from "@/components/ui/Toast";
import {
  useIncidentList,
  useIncidentStatusMutation,
  useIncidentBulkStatusMutation,
} from "@/lib/hooks/useIncidents";
import { IncidentFilterBar } from "@/components/incidents/IncidentFilterBar";
import { IncidentRow } from "@/components/incidents/IncidentRow";
import { IncidentInvestigationPane } from "@/components/incidents/IncidentInvestigationPane";
import { BulkActionBar } from "@/components/alerts/BulkActionBar";
import { IncidentEmptyState } from "@/components/incidents/IncidentEmptyState";
import { Pagination, PageSizeSelect } from "@/components/design-system/Pagination";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { Drawer } from "@/components/ui/Drawer";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import {
  INCIDENT_SEVERITIES,
  INCIDENT_STATUSES,
  DEFAULT_INCIDENT_FILTERS,
  type IncidentFilters,
  type IncidentResponse,
} from "@/lib/types/incident";

const PAGE_SIZES = [25, 50, 100];

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
  info: 0,
};

export default function IncidentsPage() {
  return (
    <Suspense fallback={<LoadingState variant="table" rows={6} />}>
      <IncidentsPageContent />
    </Suspense>
  );
}

function IncidentsPageContent() {
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const listHeight = useMemo(
    () =>
      typeof window !== "undefined"
        ? Math.min(640, Math.max(320, window.innerHeight - 320))
        : 480,
    [],
  );

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [selectedId, setSelectedId] = useDeepLinkedSelection();
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [activeIndex, setActiveIndex] = useState(0);
  const [filters, setFilters] = useState<IncidentFilters>(DEFAULT_INCIDENT_FILTERS);

  const debouncedQ = useDebounce(filters.q, 400);
  const queryFilters = useMemo(
    () => ({ ...filters, q: debouncedQ }),
    [filters, debouncedQ],
  );

  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !searchParams.get("selected"))
      setFilters((prev) => ({ ...prev, q }));
  }, [searchParams]);

  const { data: hosts = [] } = useHostsList();
  const hostNames = useMemo(
    () => Object.fromEntries(hosts.map((h) => [h.id, h.name])),
    [hosts],
  );
  const { data: user } = useUser();
  const canMutate = user?.role?.name === "admin" || user?.role?.name === "analyst";
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const { data, isLoading, isFetching, isError, refetch } = useIncidentList();

  const statusMutation = useIncidentStatusMutation({
    onSuccess: () => toast("success", "Incident updated"),
    onError: (e) => toast("error", "Update failed", e.message),
  });
  const bulkMutation = useIncidentBulkStatusMutation({
    onSuccess: (res) => {
      setCheckedIds(new Set());
      toast("success", `Updated ${res.updated} incident(s)`);
      if (res.failed > 0) {
        toast("warning", `${res.failed} incident(s) could not be updated`);
      }
    },
    onError: (e) => toast("error", "Bulk update failed", e.message),
  });

  /** Filter + sort + paginate entirely client-side (list is fetched once, up to 500). */
  const filtered = useMemo(() => {
    const rows = data?.items ?? [];
    const q = queryFilters.q.trim().toLowerCase();
    const matched = rows.filter((r) => {
      if (queryFilters.severity && r.severity !== queryFilters.severity) return false;
      if (queryFilters.status && r.status !== queryFilters.status) return false;
      if (queryFilters.host_id && r.host_id !== queryFilters.host_id) return false;
      if (
        q &&
        !r.title.toLowerCase().includes(q) &&
        !(r.description ?? "").toLowerCase().includes(q)
      )
        return false;
      return true;
    });

    const sorted = [...matched].sort((a, b) => {
      switch (sort) {
        case "oldest":
          return a.created_at.localeCompare(b.created_at);
        case "severity:desc":
          return (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0);
        case "severity:asc":
          return (SEVERITY_RANK[a.severity] ?? 0) - (SEVERITY_RANK[b.severity] ?? 0);
        case "title:asc":
          return a.title.localeCompare(b.title);
        default:
          return b.created_at.localeCompare(a.created_at);
      }
    });
    return sorted;
  }, [data?.items, queryFilters, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageItems = useMemo(
    () => filtered.slice((page - 1) * pageSize, page * pageSize),
    [filtered, page, pageSize],
  );

  useEffect(() => {
    setActiveIndex(0);
  }, [page, pageSize, sort, queryFilters.severity, queryFilters.status, queryFilters.host_id, debouncedQ]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const allOnPageSelected =
    pageItems.length > 0 && pageItems.every((i) => checkedIds.has(i.id));
  const someOnPageSelected = pageItems.some((i) => checkedIds.has(i.id));

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
        pageItems.forEach((i) => copy.delete(i.id));
      } else {
        pageItems.forEach((i) => copy.add(i.id));
      }
      return copy;
    });
  }, [allOnPageSelected, pageItems]);

  const runBulk = useCallback(
    (payload: { status?: string; assigned_to?: string }) => {
      const ids = Array.from(checkedIds);
      if (!ids.length || !payload.status) return;
      bulkMutation.mutate({ ids, status: payload.status });
    },
    [bulkMutation, checkedIds],
  );

  const bulkFromFocus = useCallback(
    (status: string) => {
      const incident = pageItems[activeIndex];
      if (!incident) return;
      if (checkedIds.size > 0) {
        runBulk({ status });
      } else {
        bulkMutation.mutate({ ids: [incident.id], status });
      }
    },
    [pageItems, activeIndex, checkedIds, runBulk, bulkMutation],
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
      const incident = pageItems[idx];
      if (incident) setSelectedId(incident.id);
    },
    onToggle: canMutate
      ? (idx) => {
          const incident = pageItems[idx];
          if (incident) toggleChecked(incident.id, !checkedIds.has(incident.id));
        }
      : undefined,
    onBulkResolve: canMutate ? () => bulkFromFocus("resolved") : undefined,
    onBulkInvestigate: canMutate ? () => bulkFromFocus("investigating") : undefined,
  });

  const handleFilterChange = useCallback((next: IncidentFilters) => setFilters(next), []);
  const handleSortChange = useCallback((next: string) => setSort(next), []);
  const handleResetPage = useCallback(() => setPage(1), []);

  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_INCIDENT_FILTERS);
    setPage(1);
  }, []);

  const hasActiveFilters = Boolean(
    filters.severity || filters.status || filters.host_id || filters.q,
  );

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-accent" />
            Incidents
          </h1>
          <p className="text-sm text-muted mt-1">
            Security incidents under investigation
          </p>
        </div>
      </header>

      <IncidentFilterBar
        filters={filters}
        sort={sort}
        severityOptions={INCIDENT_SEVERITIES.map((s) => ({
          value: s,
          label: s.charAt(0).toUpperCase() + s.slice(1),
        }))}
        statusOptions={INCIDENT_STATUSES.map((s) => ({
          value: s,
          label: s.charAt(0).toUpperCase() + s.slice(1),
        }))}
        hosts={hosts}
        onFilterChange={handleFilterChange}
        onSortChange={handleSortChange}
        onResetPage={handleResetPage}
      />

      {canMutate && checkedIds.size > 0 && (
        <BulkActionBar
          count={checkedIds.size}
          isPending={bulkMutation.isPending}
          onAction={runBulk}
          onClear={() => setCheckedIds(new Set())}
          onConfirm={(_, cb) => cb()}
        />
      )}

      {canMutate && pageItems.length > 0 && (
        <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
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
        <p className="text-[10px] text-muted">
          Keyboard: j/k navigate · Enter open · Space select · i investigate · r resolve
        </p>
      )}

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div>
          {isLoading ? (
            <LoadingState variant="table" rows={6} />
          ) : isError ? (
            <ErrorState title="Failed to load incidents" onRetry={() => refetch()} />
          ) : (
            <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
              {pageItems.length === 0 ? (
                <IncidentEmptyState hasFilters={hasActiveFilters} onClear={clearFilters} />
              ) : (
                <div
                  className="data-table-wrap"
                  style={{ height: listHeight, overflowY: "auto" }}
                >
                  {pageItems.map((incident: IncidentResponse) => (
                    <IncidentRow
                      key={incident.id}
                      incident={incident}
                      hostName={hostNames[incident.host_id ?? ""]}
                      selected={selectedId === incident.id}
                      onClick={() => setSelectedId(incident.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between mt-4 gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted tabular-nums">
                {filtered.length} incidents
              </span>
              <PageSizeSelect
                value={pageSize}
                onChange={(s) => {
                  setPageSize(s);
                  setPage(1);
                }}
                options={PAGE_SIZES}
              />
            </div>
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        </div>

        <div className="hidden lg:block lg:sticky lg:top-20">
          <IncidentInvestigationPane
            incidentId={selectedId}
            onStatus={setStatus}
            isUpdating={statusMutation.isPending}
          />
        </div>
      </div>

      <Drawer
        open={!!selectedId && !isDesktop}
        onClose={() => setSelectedId(null)}
        title="Incident investigation"
        side="bottom"
        className="lg:hidden"
      >
        {selectedId && (
          <IncidentInvestigationPane
            incidentId={selectedId}
            onStatus={setStatus}
            isUpdating={statusMutation.isPending}
          />
        )}
      </Drawer>
    </div>
  );
}
