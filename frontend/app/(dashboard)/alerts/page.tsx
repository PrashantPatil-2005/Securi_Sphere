"use client";

import { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { Bell } from "lucide-react";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import { useKeyboardListNav } from "@/lib/hooks/useKeyboardListNav";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useUser } from "@/lib/hooks/useUser";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import {
  useAlertList,
  useAlertStatusMutation,
  useAlertBulkMutation,
} from "@/lib/hooks/useAlerts";
import type { AlertFilters } from "@/lib/types/alert";
import ExportMenu from "@/components/export/ExportMenu";
import TimeRangeBar from "@/components/filters/TimeRangeBar";
import { AlertInvestigationPane } from "@/components/AlertInvestigationPane";
import { AlertFilters as AlertFilterBar } from "@/components/alerts/AlertFilters";
import { AlertRow } from "@/components/alerts/AlertRow";
import { BulkActionBar } from "@/components/alerts/BulkActionBar";
import { AlertEmptyState } from "@/components/alerts/AlertEmptyState";
import { Pagination, PageSizeSelect } from "@/components/design-system/Pagination";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { Drawer } from "@/components/ui/Drawer";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { useToast } from "@/components/ui/Toast";

const PAGE_SIZES = [25, 50, 100, 500];

export default function AlertsPage() {
  return (
    <Suspense fallback={<LoadingState variant="table" rows={6} />}>
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
  const [filters, setFilters] = useState<AlertFilters>({
    status: "",
    severity: "",
    host_id: "",
    rule_name: "",
    q: "",
    mitre_technique_id: "",
  });

  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedRule = useDebounce(filters.rule_name, 400);
  const queryFilters = useMemo(
    () => ({ ...filters, q: debouncedQ, rule_name: debouncedRule }),
    [filters, debouncedQ, debouncedRule],
  );

  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !searchParams.get("selected"))
      setFilters((prev) => ({ ...prev, q }));
    const mitre = searchParams.get("mitre_technique_id");
    if (mitre) setFilters((prev) => ({ ...prev, mitre_technique_id: mitre }));
  }, [searchParams]);

  const { data: hosts = [] } = useHostsList();
  const hostNames = useMemo(
    () => Object.fromEntries(hosts.map((h) => [h.id, h.name])),
    [hosts],
  );
  const { data: user } = useUser();
  const canMutate =
    user?.role?.name === "admin" || user?.role?.name === "analyst";
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const { data, isLoading, isFetching, isError, refetch } = useAlertList({
    page,
    pageSize,
    sort,
    filters: queryFilters,
  });

  const statusMutation = useAlertStatusMutation(() => {
    queryClient.invalidateQueries({
      queryKey: ["alerts", "investigation", selectedId],
    });
  });
  const bulkMutation = useAlertBulkMutation(() => {
    setCheckedIds(new Set());
    queryClient.invalidateQueries({
      queryKey: ["alerts", "investigation", selectedId],
    });
  });

  const pageItems = useMemo(() => data?.items ?? [], [data?.items]);

  useEffect(() => {
    setActiveIndex(0);
  }, [
    page,
    pageSize,
    sort,
    queryFilters.status,
    queryFilters.severity,
    queryFilters.host_id,
    debouncedQ,
    debouncedRule,
  ]);

  const allOnPageSelected =
    pageItems.length > 0 && pageItems.every((a) => checkedIds.has(a.id));
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
              toast(
                "warning",
                `${res.not_found.length} alert(s) not found`,
              );
            }
          },
          onError: (e: Error) =>
            toast("error", "Bulk update failed", e.message),
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
        runBulk({
          status,
          ...(status === "investigating" && user?.id
            ? { assigned_to: user.id }
            : {}),
        });
      } else {
        setCheckedIds(new Set([alert.id]));
        bulkMutation.mutate(
          {
            alert_ids: [alert.id],
            status,
            ...(status === "investigating" && user?.id
              ? { assigned_to: user.id }
              : {}),
          },
          {
            onSuccess: () => toast("success", "Alert updated"),
            onError: (e: Error) =>
              toast("error", "Update failed", e.message),
          },
        );
      }
    },
    [
      pageItems,
      activeIndex,
      checkedIds,
      runBulk,
      bulkMutation,
      user?.id,
      toast,
    ],
  );

  const setStatus = useCallback(
    (id: string, status: string) =>
      statusMutation.mutate(
        { id, status },
        {
          onSuccess: () => toast("success", "Alert updated"),
          onError: (e: Error) =>
            toast("error", "Update failed", e.message),
        },
      ),
    [statusMutation, toast],
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
          if (alert)
            toggleChecked(alert.id, !checkedIds.has(alert.id));
        }
      : undefined,
    onBulkResolve: canMutate ? () => bulkFromFocus("resolved") : undefined,
    onBulkInvestigate: canMutate
      ? () => bulkFromFocus("investigating")
      : undefined,
  });

  const handleFilterChange = useCallback((next: AlertFilters) => {
    setFilters(next);
  }, []);

  const handleSortChange = useCallback((next: string) => {
    setSort(next);
  }, []);

  const handleResetPage = useCallback(() => {
    setPage(1);
  }, []);

  const hasActiveFilters = Boolean(
    filters.status ||
      filters.severity ||
      filters.host_id ||
      filters.q ||
      filters.rule_name ||
      filters.mitre_technique_id,
  );

  const totalPages = data?.total
    ? Math.ceil(data.total / pageSize)
    : 1;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            <Bell className="w-5 h-5 text-accent" />
            Alerts
          </h1>
          <p className="text-sm text-muted mt-1">
            Security alerts requiring attention
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TimeRangeBar />
          <ExportMenu
            resource="alerts"
            query={buildQuery({ sort, ...queryFilters }, queryParams)}
          />
        </div>
      </header>

      <AlertFilterBar
        filters={filters}
        sort={sort}
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
          Keyboard: j/k navigate · Enter open · Space select · i investigate · r
          resolve
        </p>
      )}

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div>
          {isLoading ? (
            <LoadingState variant="table" rows={6} />
          ) : isError ? (
            <ErrorState
              title="Failed to load alerts"
              onRetry={() => refetch()}
            />
          ) : (
            <div
              className={
                isFetching ? "opacity-70 transition-opacity" : ""
              }
            >
              {pageItems.length === 0 ? (
                <AlertEmptyState hasFilters={hasActiveFilters} />
              ) : (
                <div
                  className="data-table-wrap"
                  style={{ height: listHeight, overflowY: "auto" }}
                >
                  {pageItems.map((alert) => (
                    <AlertRow
                      key={alert.id}
                      alert={alert}
                      hostName={hostNames[alert.host_id]}
                      selected={selectedId === alert.id}
                      onClick={() => setSelectedId(alert.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between mt-4 gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted tabular-nums">
                {data?.total ?? 0} alerts
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
            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </div>
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
